"""LED状態取得Lambda

AWS IoT Device ShadowのreportedステートからLEDの現在状態を取得して返す。
"""
import json
import os

import boto3

IOT_DATA_ENDPOINT = os.environ["IOT_DATA_ENDPOINT"]
THING_NAME = os.environ["THING_NAME"]

iot_data = boto3.client("iot-data", endpoint_url=f"https://{IOT_DATA_ENDPOINT}")


def handler(event, context):
    try:
        response = iot_data.get_thing_shadow(thingName=THING_NAME)
        payload = json.loads(response["payload"].read())
        state = payload.get("state", {}).get("reported", {}).get("led", "OFF")
    except iot_data.exceptions.ResourceNotFoundException:
        # Shadowがまだ存在しない（デバイス未接続等）場合はOFF扱いとする
        state = "OFF"
    except Exception as exc:  # noqa: BLE001
        return _response(500, {"message": f"内部エラー: {exc}"})

    return _response(200, {"state": state})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
