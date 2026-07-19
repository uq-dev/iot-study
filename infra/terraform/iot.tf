# --- IoT Thing（LEDデバイス） ---
resource "aws_iot_thing" "led_device" {
  name = var.thing_name
}

# デバイスが接続するデータプレーンエンドポイント（MQTT/Shadow用）
data "aws_iot_endpoint" "data_ats" {
  endpoint_type = "iot:Data-ATS"
}

# --- デバイス用IoTポリシー ---
# 実機（ESP32等）が証明書を使ってShadowを更新・購読するための最小権限ポリシー。
# 証明書の発行・アタッチは本たたき台のスコープ外のため、以下は雛形として用意。
resource "aws_iot_policy" "device_policy" {
  name = "${var.project_name}-device-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iot:Connect"]
        Resource = "arn:aws:iot:${var.aws_region}:*:client/${var.thing_name}"
      },
      {
        Effect = "Allow"
        Action = ["iot:Publish", "iot:Receive"]
        Resource = [
          "arn:aws:iot:${var.aws_region}:*:topic/$aws/things/${var.thing_name}/shadow/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["iot:Subscribe"]
        Resource = [
          "arn:aws:iot:${var.aws_region}:*:topicfilter/$aws/things/${var.thing_name}/shadow/*"
        ]
      }
    ]
  })
}

# --- 実機の証明書発行について ---
# 本たたき台ではデバイス個別の鍵管理（証明書発行・失効・ローテーション）は対象外です。
# 実運用時は以下のような手順・リソースを追加してください。
#
#   1. `aws iot create-keys-and-certificate --set-as-active` 等で証明書を発行
#      （またはTerraformの aws_iot_certificate リソースでCSRベースに発行）
#   2. aws_iot_thing_principal_attachment で証明書とThingを紐付け
#   3. aws_iot_policy_attachment で証明書とdevice_policyを紐付け
