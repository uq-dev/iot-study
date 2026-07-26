"""機器状態更新Lambda

リクエストで指定された機器の新しい状態をAWS IoT Device Shadowのdesiredステートに更新する。
"""
import json
import os

import boto3

IOT_DATA_ENDPOINT = os.environ["IOT_DATA_ENDPOINT"]
THING_NAME = os.environ["THING_NAME"]

iot_data = boto3.client("iot-data", endpoint_url=f"https://{IOT_DATA_ENDPOINT}")

VALID_POWERS = {"ON", "OFF"}
VALID_MODES = {"COOL", "HEAT", "DRY", "FAN"}
VALID_LIGHT_MODES = {"FULL", "WARM", "ECO"}


def handler(event, _context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"message": "リクエストボディが不正なJSONです"})

    desired = {}

    # エアコン状態のパースとバリデーション
    if "aircon" in body and isinstance(body["aircon"], dict):
        aircon_req = body["aircon"]
        aircon_desired = {}

        if "power" in aircon_req:
            power = str(aircon_req["power"]).upper()
            if power not in VALID_POWERS:
                return _response(400, {"message": "aircon.power には 'ON' または 'OFF' を指定してください"})
            aircon_desired["power"] = power

        if "temp" in aircon_req:
            try:
                temp = int(aircon_req["temp"])
                if not (18 <= temp <= 30):
                    raise ValueError
                aircon_desired["temp"] = temp
            except (ValueError, TypeError):
                return _response(400, {"message": "aircon.temp には 18 から 30 の整数を指定してください"})

        if "mode" in aircon_req:
            mode = str(aircon_req["mode"]).upper()
            if mode not in VALID_MODES:
                return _response(400, {"message": f"aircon.mode には {VALID_MODES} のいずれかを指定してください"})
            aircon_desired["mode"] = mode

        if aircon_desired:
            desired["aircon"] = aircon_desired

    # シーリングライト状態のパースとバリデーション
    if "light" in body and isinstance(body["light"], dict):
        light_req = body["light"]
        light_desired = {}

        if "power" in light_req:
            power = str(light_req["power"]).upper()
            if power not in VALID_POWERS:
                return _response(400, {"message": "light.power には 'ON' または 'OFF' を指定してください"})
            light_desired["power"] = power

        if "mode" in light_req:
            mode = str(light_req["mode"]).upper()
            if mode not in VALID_LIGHT_MODES:
                return _response(400, {"message": f"light.mode には {VALID_LIGHT_MODES} のいずれかを指定してください"})
            light_desired["mode"] = mode

        if light_desired:
            desired["light"] = light_desired

    if not desired:
        return _response(400, {"message": "更新するパラメータ（aircon または light）を指定してください"})

    shadow_payload = {"state": {"desired": desired}}

    try:
        iot_data.update_thing_shadow(
            thingName=THING_NAME,
            payload=json.dumps(shadow_payload).encode("utf-8"),
        )
    except Exception as exc:  # noqa: BLE001
        return _response(500, {"message": f"内部エラー: {exc}"})

    return _response(200, desired)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
