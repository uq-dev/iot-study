#!/usr/bin/env python3
"""AWS IoT Core Device Shadow 同期エージェント

AWS IoT CoreにMQTT接続し、エアコンとシーリングライトのdesiredステートのdelta(差分)を監視します。
差分を検知すると ir_control.py を呼び出して物理的に赤外線信号を送信し、
送信完了後にreportedステートを更新します。
"""
import json
import os
import sys
import time

from awscrt import mqtt
from awsiot import mqtt_connection_builder
from ir_control import transmit_code

# 環境変数から設定を取得
ENDPOINT = os.environ.get("IOT_ENDPOINT")
THING_NAME = os.environ.get("THING_NAME")
CERT_PATH = os.environ.get("CERT_PATH")
KEY_PATH = os.environ.get("KEY_PATH")
ROOT_CA_PATH = os.environ.get("ROOT_CA_PATH")

if not all([ENDPOINT, THING_NAME, CERT_PATH, KEY_PATH, ROOT_CA_PATH]):
    print("エラー: 必要な環境変数が設定されていません。")
    print("IOT_ENDPOINT, THING_NAME, CERT_PATH, KEY_PATH, ROOT_CA_PATH を設定してください。")
    sys.exit(1)

# シャドウトピック定義
SHADOW_UPDATE_TOPIC = f"$aws/things/{THING_NAME}/shadow/update"
SHADOW_DELTA_TOPIC = f"$aws/things/{THING_NAME}/shadow/update/delta"

# グローバルな状態管理（reportedのローカルキャッシュ）
local_reported = {
    "aircon": {"power": "OFF", "temp": 26, "mode": "COOL"},
    "light": {"power": "OFF", "mode": "FULL"}
}


def on_connection_interrupted(connection, error, **kwargs):
    print(f"接続中断: {error}")


def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(f"接続再開: return_code={return_code}, session_present={session_present}")


def on_delta_received(topic, payload, dup, qos, retain, **kwargs):
    """Shadowのdelta(不一致状態)を受信したときの処理"""
    try:
        delta_data = json.loads(payload.decode('utf-8'))
        print(f"\n[Delta受信] 受信データ: {json.dumps(delta_data, indent=2)}")

        state_delta = delta_data.get("state", {})

        # desiredの更新要求を抽出
        aircon_delta = state_delta.get("aircon")
        light_delta = state_delta.get("light")

        update_payload = {"state": {"reported": {}}}

        # 1. エアコンの制御処理
        if aircon_delta:
            # 変化のある値、または現在のキャッシュ値を用いて送信コマンドを決定
            power = aircon_delta.get("power", local_reported["aircon"]["power"])
            temp = aircon_delta.get("temp", local_reported["aircon"]["temp"])
            mode = aircon_delta.get("mode", local_reported["aircon"]["mode"])

            print(f"-> エアコン要求: power={power}, temp={temp}, mode={mode}")

            success = False
            if power == "OFF":
                success = transmit_code("aircon:off")
            else:
                # 例: "aircon:cool_26", "aircon:heat_24" などの特定パターンのコード
                code_name = f"aircon:{mode.lower()}_{temp}"
                print(f"  赤外線コード [{code_name}] を送信中...")
                success = transmit_code(code_name)

                if not success:
                    # 特定コードがない場合のフォールバック（エアコンON汎用）
                    print(f"  警告: [{code_name}] が見つからないため、汎用ON [aircon:on] を試行します。")
                    success = transmit_code("aircon:on")

            if success:
                # 状態キャッシュを更新し、reportedへ反映
                local_reported["aircon"]["power"] = power
                local_reported["aircon"]["temp"] = temp
                local_reported["aircon"]["mode"] = mode
                update_payload["state"]["reported"]["aircon"] = local_reported["aircon"]
            else:
                print("  エラー: エアコンの赤外線送信に失敗したため、Shadowの状態は更新しません。")

        # 2. シーリングライトの制御処理
        if light_delta:
            power = light_delta.get("power", local_reported["light"]["power"])
            mode = light_delta.get("mode", local_reported["light"]["mode"])

            print(f"-> シーリングライト要求: power={power}, mode={mode}")

            success = False
            if power == "OFF":
                success = transmit_code("light:off")
            else:
                # モードに応じた赤外線コードの送信 (Panasonic全灯/調光/常夜灯)
                code_name = f"light:{mode.lower()}"
                print(f"  赤外線コード [{code_name}] を送信中...")
                success = transmit_code(code_name)

            if success:
                local_reported["light"]["power"] = power
                local_reported["light"]["mode"] = mode
                update_payload["state"]["reported"]["light"] = local_reported["light"]
            else:
                print("  エラー: ライトの赤外線送信に失敗したため、Shadowの状態は更新しません。")

        # reportedステートをIoT Coreに返してShadowを同期
        if update_payload["state"]["reported"]:
            print(f"[Shadow更新] reportedを送信中: {json.dumps(update_payload)}")
            mqtt_connection.publish(
                topic=SHADOW_UPDATE_TOPIC,
                payload=json.dumps(update_payload),
                qos=mqtt.QoS.AT_LEAST_ONCE
            )

    except Exception as e:  # noqa: BLE001
        print(f"デルタ処理中にエラーが発生しました: {e}")


# MQTT接続の構築
print(f"AWS IoT Core に接続中... エンドポイント: {ENDPOINT}")
mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=ENDPOINT,
    cert_filepath=CERT_PATH,
    pri_key_filepath=KEY_PATH,
    ca_filepath=ROOT_CA_PATH,
    client_id=f"{THING_NAME}-agent",
    clean_session=False,
    keep_alive_secs=30,
    on_connection_interrupted=on_connection_interrupted,
    on_connection_resumed=on_connection_resumed
)

connect_future = mqtt_connection.connect()
connect_future.result()  # 接続完了を待つ
print("接続成功！")

# デルタトピックのサブスクライブ
print(f"Shadowデルタを購読中: {SHADOW_DELTA_TOPIC}")
subscribe_future, _ = mqtt_connection.subscribe(
    topic=SHADOW_DELTA_TOPIC,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=on_delta_received
)
subscribe_future.result()

# メインループ
try:
    print("エージェントが起動しました。終了するには Ctrl+C を押してください。")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nエージェントを終了します...")
finally:
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("切断完了。")
