#!/usr/bin/env python3
"""赤外線送信・受信(学習)ユーティリティ

pigpioライブラリを使用して、赤外線リモコン信号のパルス幅をJSON形式で記録し、
GPIOピンを通じて変調(38kHz)送信します。
"""
import json
import sys
import time

import pigpio

# GPIOピン設定
GPIO_TX = 17  # 送信ピン
GPIO_RX = 18  # 受信ピン

# 記録・再生パラメータ
GLITCH = 100     # ノイズとみなす短いパルス幅(μs)
FREQ = 38000     # 搬送波周波数(38kHz)
CODES_FILE = "codes.json"


def record_code(key_name):
    """赤外線信号を受信・学習して codes.json に保存する"""
    pi = pigpio.pi()
    if not pi.connected:
        print("エラー: pigpiod デーモンが起動していません。'sudo systemctl start pigpiod' を実行してください。")
        sys.exit(1)

    pi.set_mode(GPIO_RX, pigpio.INPUT)

    # パルス受信のためのコールバック処理
    fetching = []
    last_tick = None

    def rx_callback(gpio, level, tick):
        nonlocal last_tick
        if last_tick is not None:
            diff = pigpio.tickDiff(last_tick, tick)
            fetching.append(diff)
        last_tick = tick

    print(f"[{key_name}] のリモコン信号を学習します...")
    print("リモコンをレシーバーに向けて、ボタンを1回押してください。")

    cb = pi.callback(GPIO_RX, pigpio.EITHER_EDGE, rx_callback)

    # 信号が来るのを待つ
    start_time = time.time()
    while len(fetching) == 0:
        time.sleep(0.1)
        if time.time() - start_time > 15:
            cb.cancel()
            pi.stop()
            print("タイムアウトしました。信号が受信されませんでした。")
            sys.exit(1)

    # 信号の終わりを検知（一定時間変化がないこと）
    last_len = 0
    while True:
        time.sleep(0.2)
        if len(fetching) == last_len and len(fetching) > 0:
            break
        last_len = len(fetching)

    cb.cancel()

    # パルスのクリーンアップと正規化
    # グリッチ(ノイズ)の除去
    cleaned_pulses = [p for p in fetching if p > GLITCH]

    if len(cleaned_pulses) < 4:
        print("警告: 受信したパルスが少なすぎます。学習をやり直してください。")
        pi.stop()
        sys.exit(1)

    # 保存ファイルの読み込み
    try:
        with open(CODES_FILE, "r") as f:
            codes = json.load(f)
    except FileNotFoundError:
        codes = {}

    codes[key_name] = cleaned_pulses

    with open(CODES_FILE, "w") as f:
        json.dump(codes, f, indent=2)

    print(f"成功: [{key_name}] を学習し {CODES_FILE} に保存しました。({len(cleaned_pulses)} パルス)")
    pi.stop()


def transmit_code(key_name):
    """codes.json からパルスデータを読み込み、赤外線LEDから送信する"""
    try:
        with open(CODES_FILE, "r") as f:
            codes = json.load(f)
    except FileNotFoundError:
        print(f"エラー: {CODES_FILE} が見つかりません。先に学習を行ってください。")
        return False

    if key_name not in codes:
        print(f"エラー: キー [{key_name}] は登録されていません。")
        return False

    pulses = codes[key_name]

    pi = pigpio.pi()
    if not pi.connected:
        print("エラー: pigpiod デーモンが起動していません。")
        return False

    pi.set_mode(GPIO_TX, pigpio.OUTPUT)

    # キャリア変調パルスの構築 (38kHz)
    modulated_pulses = []
    for i, pulse_len in enumerate(pulses):
        if i % 2 == 0:
            # マーク: 38kHzのパルスに細分化
            cycles = int(pulse_len * FREQ / 1000000.0)
            for _ in range(cycles):
                modulated_pulses.append(pigpio.pulse(1 << GPIO_TX, 0, 9))
                modulated_pulses.append(pigpio.pulse(0, 1 << GPIO_TX, 17))
        else:
            # スペース: 単一の消灯パルス
            modulated_pulses.append(pigpio.pulse(0, 1 << GPIO_TX, pulse_len))

    pi.wave_clear()
    pi.wave_add_generic(modulated_pulses)
    try:
        final_wave_id = pi.wave_create()
        pi.wave_send_once(final_wave_id)
        while pi.wave_tx_busy():
            time.sleep(0.05)
        pi.wave_delete(final_wave_id)
        print(f"成功: [{key_name}] の赤外線信号を送信しました。")
        success = True
    except Exception as e:
        print(f"送信エラー: {e}")
        success = False
    finally:
        pi.stop()

    return success


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用法:")
        print("  学習: python3 ir_control.py record <キー名>")
        print("  送信: python3 ir_control.py play <キー名>")
        print("例:")
        print("  python3 ir_control.py record light:full")
        print("  python3 ir_control.py play light:full")
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
