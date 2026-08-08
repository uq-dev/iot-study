#!/usr/bin/env python3
"""
debug_ir_rx.py - 赤外線受信 (SPS-442-1 -> GPIO 27) リアルタイムデバッグツール

電気信号レベルでの状態変化(HIGH/LOW)と、パルス幅(μs)をリアルタイムに画面表示します。
"""
import sys
import time
import pigpio

GPIO_RX = 27  # 受信ピン (GPIO 27)

def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("エラー: pigpiod デーモンが起動していません。'sudo systemctl start pigpiod' を実行してください。")
        sys.exit(1)

    print("==========================================")
    print(f" 赤外線受信デバッグモード (GPIO {GPIO_RX})")
    print("==========================================")
    print("SPS-442-1 の配線:")
    print("  ・1番ピン (左)  : GND")
    print("  ・2番ピン (中央): GPIO 27  (信号出力)")
    print("  ・3番ピン (右)  : 5V       (電源)")
    print("------------------------------------------")

    # 初期状態の確認
    pi.set_mode(GPIO_RX, pigpio.INPUT)
    pi.set_pull_up_down(GPIO_RX, pigpio.PUD_UP) # 内蔵プルアップ
    
    current_level = pi.read(GPIO_RX)
    print(f"現在のピン初期状態: {'HIGH (1)' if current_level == 1 else 'LOW (0)'}")
    if current_level == 0:
        print("⚠️ 警告: ピンが常時 LOW(0) になっています。配線ミスまたは短絡の可能性があります。")
    else:
        print("✅ 待機状態正常 (HIGH: 赤外線未検知)")
    print("------------------------------------------")
    print("リモコンのボタンを押してください... (終了するには Ctrl+C)\n")

    last_tick = None
    event_count = 0

    def rx_callback(gpio, level, tick):
        nonlocal last_tick, event_count
        event_count += 1
        
        level_str = "LOW  (0 - 赤外線ON)" if level == 0 else "HIGH (1 - 赤外線OFF)"
        
        if last_tick is not None:
            pulse_width = pigpio.tickDiff(last_tick, tick)
            print(f"[{event_count:03d}] 状態変化 -> {level_str} | 継続パルス幅: {pulse_width:>6} μs")
        else:
            print(f"[{event_count:03d}] 初回エッジ検知 -> {level_str}")
        
        last_tick = tick

    # すべてのエッジ変化(0->1, 1->0)を監視
    cb = pi.callback(GPIO_RX, pigpio.EITHER_EDGE, rx_callback)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n------------------------------------------")
        print(f"デバッグ終了。検出イベント総数: {event_count} 回")
        cb.cancel()
        pi.stop()

if __name__ == "__main__":
    main()
