#!/usr/bin/env python3
"""
ir_control.py - 最新 Raspberry Pi OS (lgpio) 対応 赤外線学習・送信スクリプト
リーダーパルス判定による環境ノイズ完全除去 & 精密1フレーム抽出
"""
import json
import os
import sys
import time

try:
    import lgpio
except ImportError:
    print("エラー: lgpio ライブラリが見つかりません。")
    print("  sudo apt update && sudo apt install -y python3-lgpio を実行してください。")
    sys.exit(1)

# GPIO ピン設定
GPIO_TX = 17  # 送信ピン
GPIO_RX = 27  # 受信ピン

# パラメータ
FREQ = 38000           # 38kHz
DUTY_CYCLE = 0.33      # 33%
MIN_LEADER_US = 1500   # リーダーパルス判定 (1.5ms以上の長パルスが来るまで待機)
MIN_PULSE_US = 150     # 微細ノイズ除去 (150μs未満を除外)
FRAME_GAP_US = 10000   # 10msの無信号で1フレーム終了

# --- ノイズ誤検知対策のパラメータ ---
ARM_WARMUP_S = 0.3     # gpio_claim_alert直後の過渡的なエッジを無視するウォームアップ時間
MIN_VALID_PULSES = 16  # これ未満は「誤検知(ノイズ)」とみなして破棄する
                        # (一般的なリモコンは1フレームあたり数十パルス程度になることが多い)
RECORD_ATTEMPTS = 3    # ノイズ誤検知時に自動リトライする回数

CODES_FILE = os.path.join(os.path.dirname(__file__), "codes.json")


def _try_record_once(h, timeout_s=15.0):
    """1回分の受信試行。成功時は (True, raw_pulses)、失敗時は (False, raw_pulses) を返す。

    戻り値の frame_completed が False の場合（＝本物の無信号ギャップを検出できずに
    タイムアウトした場合）は、たとえパルス数が MIN_VALID_PULSES を超えていても
    「誤検知の可能性が高い」として呼び出し側で破棄すること。
    """
    raw_pulses = []
    last_ns = None
    got_leader = False
    frame_completed = False

    # gpio_claim_alert / callback登録直後は、ピンの入力モード切り替えに伴う
    # 電気的な過渡変化でエッジが発生することがある。
    # このウォームアップ時間内のエッジは「本物の信号」として扱わないようにする。
    warmup_until_ns = time.perf_counter_ns() + int(ARM_WARMUP_S * 1_000_000_000)

    def callback(chip, gpio, level, timestamp):
        nonlocal last_ns, raw_pulses, got_leader, frame_completed
        now_ns = time.perf_counter_ns()

        if frame_completed:
            return

        # ウォームアップ中のエッジは基準時刻の更新だけ行い、信号としては扱わない
        if now_ns < warmup_until_ns:
            last_ns = now_ns
            return

        if last_ns is not None:
            diff_us = (now_ns - last_ns) // 1000  # ns -> μs

            if not got_leader:
                if diff_us >= MIN_LEADER_US:
                    got_leader = True
                    raw_pulses.append(diff_us)
            else:
                if diff_us > FRAME_GAP_US and len(raw_pulses) >= 10:
                    frame_completed = True
                    return

                if diff_us >= MIN_PULSE_US:
                    raw_pulses.append(diff_us)

        last_ns = now_ns

    lgpio.gpio_claim_alert(h, GPIO_RX, lgpio.BOTH_EDGES, lgpio.SET_PULL_UP)
    cb_handle = lgpio.callback(h, GPIO_RX, lgpio.BOTH_EDGES, callback)

    start_time = time.time()
    dots = 0

    # ウォームアップ時間はメッセージ表示だけして待つ
    time.sleep(ARM_WARMUP_S)

    # 本物の信号(リーダーパルス)が来るのを待つ
    while not got_leader:
        time.sleep(0.2)
        dots += 1
        print(f"\rリモコンのボタン押し待ち{'.' * (dots % 4)}   ", end="", flush=True)
        if time.time() - start_time > timeout_s:
            print("\n❌ タイムアウトしました。リモコンのボタンが押されませんでした。")
            cb_handle.cancel()
            return False, raw_pulses

    print("\n⚡ 信号(リーダー候補)を検知しました！データ抽出中...")

    # 1フレーム完了待ち (最大1.5秒)
    rec_start = time.time()
    while not frame_completed and (time.time() - rec_start < 1.5):
        time.sleep(0.02)
        print(f"\r  └ 取得パルス数: {len(raw_pulses)} 個", end="", flush=True)

    cb_handle.cancel()
    print()

    # --- 検証: 本当に無信号ギャップ(FRAME_GAP)を検出してフレームが終わったか ---
    if not frame_completed:
        print(f"⚠️ フレームの終端(無信号区間)を検出できませんでした（パルス数: {len(raw_pulses)}）。")
        print("   環境ノイズを誤検知した可能性があります。")
        return False, raw_pulses

    # --- 検証: パルス数が実用的な範囲か ---
    if len(raw_pulses) < MIN_VALID_PULSES:
        print(f"⚠️ パルス数が少なすぎます（{len(raw_pulses)} 個 < {MIN_VALID_PULSES} 個）。")
        print("   ノイズを誤検知した可能性が高いため破棄します。")
        return False, raw_pulses

    return True, raw_pulses


def record_code(key_name):
    """リーダーパルス(1.5ms以上)を検知してから、1フレーム(約60~140パルス)を精確に抽出して保存する。

    環境ノイズによる誤検知を防ぐため、
      1) ピン設定直後の過渡的なエッジを無視するウォームアップ時間を設ける
      2) 無信号ギャップ(FRAME_GAP)を検出できた場合のみ「フレーム完了」とみなす
      3) パルス数が少なすぎる場合は破棄する
    を行い、失敗時は自動的に再試行する。
    """
    h = lgpio.gpiochip_open(0)

    print(f"[{key_name}] のリモコン信号を学習します...")
    print("SPS-442-1 (GPIO 27) に向けてリモコンのボタンを1回押してください。")
    print(f"（準備のため {ARM_WARMUP_S:.1f} 秒お待ちください）")

    raw_pulses = None
    for attempt in range(1, RECORD_ATTEMPTS + 1):
        if attempt > 1:
            print(f"\n🔁 再試行 {attempt}/{RECORD_ATTEMPTS} 回目。もう一度ボタンを押してください。")
        ok, pulses = _try_record_once(h)
        if ok:
            raw_pulses = pulses
            break
        raw_pulses = None

    lgpio.gpiochip_close(h)

    if raw_pulses is None:
        print(f"\n❌ {RECORD_ATTEMPTS}回試行しましたが、有効な信号を取得できませんでした。")
        print("   ・受信モジュール(GPIO27)の配線を確認してください")
        print("   ・リモコンを受信モジュールに数cm程度まで近づけてください")
        print("   ・周囲の強い光源(直射日光・インバータ照明)から離してください")
        sys.exit(1)

    print(f"\n✅ 精密1フレーム抽出完了 (合計: {len(raw_pulses)} パルス)")

    # 保存
    codes = {}
    if os.path.exists(CODES_FILE):
        try:
            with open(CODES_FILE, "r") as f:
                codes = json.load(f)
        except Exception:
            codes = {}

    codes[key_name] = raw_pulses

    with open(CODES_FILE, "w") as f:
        json.dump(codes, f, indent=2)

    print(f"🎉 成功: [{key_name}] の精密波形 ({len(raw_pulses)} パルス) を保存しました！")


def _precise_wait(target_perf_counter):
    """time.sleepの誤差を補正しつつ指定時刻まで待つ。
    大部分はsleepでCPUを解放し、最後の短い区間だけビジーウェイトして精度を確保する。
    """
    remaining = target_perf_counter - time.perf_counter()
    if remaining > 0.002:
        time.sleep(remaining - 0.001)
    while time.perf_counter() < target_perf_counter:
        pass


def transmit_code(key_name):
    """codes.json からパルスデータを読み込み送信する。

    38kHzキャリアの生成は、Pythonループでgpio_write/sleepを手動で切り替える方式では
    タイミング精度が全く足りない(実測で数kHz程度にしかならない)ため、
    lgpioが提供するハードウェア支援PWM機能(tx_pwm)を使用する。
    """
    if not os.path.exists(CODES_FILE):
        print(f"エラー: {CODES_FILE} が見つかりません。先に学習を行ってください。")
        return False

    with open(CODES_FILE, "r") as f:
        codes = json.load(f)

    if key_name not in codes:
        print(f"エラー: キー [{key_name}] は登録されていません。")
        return False

    pulses = codes[key_name]

    h = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(h, GPIO_TX, 0)

    print(f"[{key_name}] の赤外線パルス ({len(pulses)} 個) を送信中...")

    try:
        for i, pulse_us in enumerate(pulses):
            duration_s = pulse_us / 1_000_000.0
            t_end = time.perf_counter() + duration_s

            if i % 2 == 0:
                # MARK: 38kHz キャリア出力 (DUTY 33%)
                lgpio.tx_pwm(h, GPIO_TX, FREQ, DUTY_CYCLE * 100, 0, 0)
                _precise_wait(t_end)
                # 消灯 (DUTY 0%)
                lgpio.tx_pwm(h, GPIO_TX, FREQ, 0, 0, 0)
            else:
                # SPACE: 消灯のまま待機
                _precise_wait(t_end)
    finally:
        # 終了処理: DUTYを0にして出力OFFにする
        lgpio.tx_pwm(h, GPIO_TX, FREQ, 0, 0, 0)
        lgpio.gpio_write(h, GPIO_TX, 0)
        lgpio.gpiochip_close(h)

    print(f"🎉 成功: [{key_name}] を送信しました。")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用法:")
        print("  学習: python3 ir_control.py record <キー名>")
        print("  送信: python3 ir_control.py play <キー名>")
        print("例:")
        print("  python3 ir_control.py record light_on")
        print("  python3 ir_control.py play light_on")
        sys.exit(1)

    mode_arg = sys.argv[1]
    name_arg = sys.argv[2]

    if mode_arg == "record":
        record_code(name_arg)
    elif mode_arg == "play":
        transmit_code(name_arg)
    else:
        print(f"不明なモード: {mode_arg}")
        sys.exit(1)
