import argparse
import json
import subprocess
import time
import os
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder

# 定数設定
GPIO_PIN = 22
CODES_FILE = "codes.json"
THING_NAME = "mimic-pi"

def execute_irrp(code_id):
    """
    irrp.pyを使用して赤外線信号を送信する
    """
    try:
        print(f"Executing irrp.py for code: {code_id}")
        # スクリプトの実行ディレクトリを基準にirrp.pyのパスを指定
        script_dir = os.path.dirname(os.path.abspath(__file__))
        irrp_path = os.path.join(script_dir, "irrp.py")
        codes_path = os.path.join(script_dir, CODES_FILE)
        
        subprocess.run(["python3", irrp_path, "-p", f"-g{GPIO_PIN}", "-f", codes_path, code_id], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute irrp.py: {e}")

def on_shadow_delta(topic, payload, dup, qos, retain, **kwargs):
    """
    Device ShadowのDeltaを受信したときのコールバック
    """
    print(f"Received Shadow Delta on {topic}")
    try:
        data = json.loads(payload)
        state = data.get("state", {})
        
        reported_state = {}
        
        # シーリングライトの状態変化をチェック
        if "light" in state and "power" in state["light"]:
            power = state["light"]["power"]
            if power == "ON":
                execute_irrp("light:on")
            elif power == "OFF":
                execute_irrp("light:off")
            
            if "light" not in reported_state:
                reported_state["light"] = {}
            reported_state["light"]["power"] = power
            
            # modeの差分があればそのままreportedに流す
            if "mode" in state["light"]:
                reported_state["light"]["mode"] = state["light"]["mode"]
            
        # エアコンの状態変化をチェック
        if "aircon" in state and "power" in state["aircon"]:
            power = state["aircon"]["power"]
            if power == "ON":
                execute_irrp("rayair:on")
            elif power == "OFF":
                execute_irrp("rayair:off")
            
            if "aircon" not in reported_state:
                reported_state["aircon"] = {}
            reported_state["aircon"]["power"] = power
            
            # tempやmodeの差分があればそのままreportedに流す
            if "temp" in state["aircon"]:
                reported_state["aircon"]["temp"] = state["aircon"]["temp"]
            if "mode" in state["aircon"]:
                reported_state["aircon"]["mode"] = state["aircon"]["mode"]
            
        # 状態が更新されたらIoT Coreに報告する
        if reported_state:
            update_shadow_reported(reported_state)
            
    except Exception as e:
        print(f"Error processing delta: {e}")

def update_shadow_reported(reported_state):
    """
    処理完了後、現在の状態(reported)を更新してDeltaを解消する
    """
    global mqtt_connection
    topic = f"$aws/things/{THING_NAME}/shadow/update"
    payload = json.dumps({"state": {"reported": reported_state}})
    print(f"Updating Shadow Reported: {payload}")
    mqtt_connection.publish(
        topic=topic,
        payload=payload,
        qos=mqtt.QoS.AT_LEAST_ONCE
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Edge IoT Shadow Client")
    parser.add_argument('--endpoint', required=True, help="AWS IoT Core Endpoint URL (e.g. xxxxxxx-ats.iot.ap-northeast-1.amazonaws.com)")
    parser.add_argument('--cert', required=True, help="Path to device certificate (e.g. mimic-pi.cert.pem)")
    parser.add_argument('--key', required=True, help="Path to private key (e.g. mimic-pi.private.key)")
    parser.add_argument('--root-ca', required=True, help="Path to Root CA certificate (e.g. root-CA.crt)")
    parser.add_argument('--client-id', default="mimic-pi-client", help="Client ID for MQTT connection")
    
    args = parser.parse_args()

    # MQTT接続の初期化
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=args.endpoint,
        cert_filepath=args.cert,
        pri_key_filepath=args.key,
        client_bootstrap=client_bootstrap,
        ca_filepath=args.root_ca,
        client_id=args.client_id,
        clean_session=False,
        keep_alive_secs=30)

    print(f"Connecting to {args.endpoint} with client ID '{args.client_id}'...")
    connect_future = mqtt_connection.connect()
    connect_future.result()
    print("Connected!")

    # Deltaトピックのサブスクライブ
    delta_topic = f"$aws/things/{THING_NAME}/shadow/update/delta"
    print(f"Subscribing to {delta_topic}...")
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=delta_topic,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_shadow_delta)
    subscribe_future.result()
    print("Subscribed. Waiting for commands...")

    try:
        # メインスレッドを待機させ続ける
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Disconnecting...")
        disconnect_future = mqtt_connection.disconnect()
        disconnect_future.result()
        print("Disconnected!")
