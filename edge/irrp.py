from irrp import IRRP

JSON_PATH = "code_irrp.json"
POST_TIME = 130 # 信号が終了したと判断する時間（単位はms）
RECV_PIN = 27   # ラズパイに接続した赤外線受信モジュールのGPIOピン番号

ir = IRRP(file=JSON_PATH, post=POST_TIME, no_confirm=True)

ir.Record(GPIO=RECV_PIN, ID="ac:16")
ir.stop()