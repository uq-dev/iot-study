"""機器状態取得Lambda

AWS IoT Device Shadowのreportedステートからエアコンとシーリングライトの現在状態を取得して返す。
"""
import json
import os

import boto3

IOT_DATA_ENDPOINT = os.environ["IOT_DATA_ENDPOINT"]
THING_NAME = os.environ["THING_NAME"]

iot_data = boto3.client("iot-data", endpoint_url=f"https://{IOT_DATA_ENDPOINT}")

DEFAULT_STATE = {
    "aircon": {
        "power": "OFF",
        "temp": 26,
        "mode": "COOL"
    },
    "light": {
        "power": "OFF",
        "mode": "FULL"
    }
}


def handler(event, _context):
    try:
        response = iot_data.get_thing_shadow(thingName=THING_NAME)
        payload = json.loads(response["payload"].read())
        reported = payload.get("state", {}).get("reported", {})

        # デフォルト状態とreported状態をディープマージ
        state = {
            "aircon": {
                "power": reported.get("aircon", {}).get("power", DEFAULT_STATE["aircon"]["power"]),
                "temp": int(reported.get("aircon", {}).get("temp", DEFAULT_STATE["aircon"]["temp"])),
                "mode": reported.get("aircon", {}).get("mode", DEFAULT_STATE["aircon"]["mode"]),
            },
            "light": {
                "power": reported.get("light", {}).get("power", DEFAULT_STATE["light"]["power"]),
                "mode": reported.get("light", {}).get("mode", DEFAULT_STATE["light"]["mode"]),
            }
        }
    except iot_data.exceptions.ResourceNotFoundException:
        # Shadowがまだ存在しない場合はデフォルトを返す
        state = DEFAULT_STATE
    except Exception as exc:  # noqa: BLE001
        return _response(500, {"message": f"内部エラー: {exc}"})

    return _response(200, state)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
