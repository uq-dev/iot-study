"""LED状態更新Lambda

リクエストで指定されたstate("ON"/"OFF")をAWS IoT Device Shadowの
desiredステートとして更新する。実際の物理LED制御はデバイス側が
shadowのdeltaを購読して行う想定（本たたき台では対象外）。
"""
import json
import os

import boto3

IOT_DATA_ENDPOINT = os.environ["IOT_DATA_ENDPOINT"]
THING_NAME = os.environ["THING_NAME"]

iot_data = boto3.client("iot-data", endpoint_url=f"https://{IOT_DATA_ENDPOINT}")

VALID_STATES = {"ON", "OFF"}


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"message": "リクエストボディが不正なJSONです"})

    state = str(body.get("state", "")).upper()
    if state not in VALID_STATES:
        return _response(400, {"message": "state には 'ON' または 'OFF' を指定してください"})

    shadow_payload = {"state": {"desired": {"led": state}}}

    try:
        iot_data.update_thing_shadow(
            thingName=THING_NAME,
            payload=json.dumps(shadow_payload).encode("utf-8"),
        )
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
