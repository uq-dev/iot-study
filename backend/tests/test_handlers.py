"""Lambdaハンドラーの単体テスト

boto3のクライアントをモックして、Lambdaハンドラーの動作を検証します。
"""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# テスト用にモックの環境変数を設定
os.environ["IOT_DATA_ENDPOINT"] = "mock-iot-endpoint.amazonaws.com"
os.environ["THING_NAME"] = "mock-device-01"
os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-1"

# パスを追加してインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lambda"))

# 一度インポートしておく
import get_appliance_state.handler as get_handler
import set_appliance_state.handler as set_handler


class MockPayload:
    def __init__(self, data):
        self.data = data

    def read(self):
        return json.dumps(self.data).encode("utf-8")


class DummyResourceNotFoundException(BaseException):
    pass


class TestHandlers(unittest.TestCase):

    def test_get_appliance_state_success(self):
        mock_iot = MagicMock()
        mock_iot.get_thing_shadow.return_value = {"payload": MockPayload({
            "state": {
                "reported": {
                    "aircon": {"power": "ON", "temp": 24, "mode": "COOL"},
                    "light": {"power": "ON", "mode": "WARM"}
                }
            }
        })}

        with patch("get_appliance_state.handler.iot_data", mock_iot):
            response = get_handler.handler({}, {})
            self.assertEqual(response["statusCode"], 200)
            body = json.loads(response["body"])
            self.assertEqual(body["aircon"]["power"], "ON")
            self.assertEqual(body["aircon"]["temp"], 24)
            self.assertEqual(body["light"]["mode"], "WARM")
            mock_iot.get_thing_shadow.assert_called_once_with(thingName="mock-device-01")

    def test_get_appliance_state_not_found(self):
        mock_iot = MagicMock()
        mock_iot.exceptions.ResourceNotFoundException = DummyResourceNotFoundException
        mock_iot.get_thing_shadow.side_effect = DummyResourceNotFoundException("Not Found")

        with patch("get_appliance_state.handler.iot_data", mock_iot):
            response = get_handler.handler({}, {})
            self.assertEqual(response["statusCode"], 200)
            body = json.loads(response["body"])
            # デフォルト値が返ること
            self.assertEqual(body["aircon"]["power"], "OFF")
            self.assertEqual(body["aircon"]["temp"], 26)
            self.assertEqual(body["light"]["power"], "OFF")

    def test_set_appliance_state_success(self):
        mock_iot = MagicMock()
        req_body = {
            "aircon": {"temp": 22, "mode": "HEAT"},
            "light": {"power": "ON", "mode": "ECO"}
        }

        with patch("set_appliance_state.handler.iot_data", mock_iot):
            response = set_handler.handler({"body": json.dumps(req_body)}, {})
            self.assertEqual(response["statusCode"], 200)
            body = json.loads(response["body"])
            self.assertEqual(body["aircon"]["temp"], 22)
            self.assertEqual(body["aircon"]["mode"], "HEAT")
            self.assertEqual(body["light"]["power"], "ON")

            mock_iot.update_thing_shadow.assert_called_once()
            args, kwargs = mock_iot.update_thing_shadow.call_args
            self.assertEqual(kwargs["thingName"], "mock-device-01")

            sent_payload = json.loads(kwargs["payload"].decode("utf-8"))
            self.assertEqual(sent_payload["state"]["desired"]["aircon"]["temp"], 22)
            self.assertEqual(sent_payload["state"]["desired"]["light"]["mode"], "ECO")

    def test_set_appliance_state_invalid(self):
        mock_iot = MagicMock()
        req_body = {
            "aircon": {"temp": 17}
        }

        with patch("set_appliance_state.handler.iot_data", mock_iot):
            response = set_handler.handler({"body": json.dumps(req_body)}, {})
            self.assertEqual(response["statusCode"], 400)
            body = json.loads(response["body"])
            self.assertIn("18 から 30 の整数", body["message"])
            mock_iot.update_thing_shadow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
