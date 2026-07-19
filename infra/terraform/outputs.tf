output "api_base_url" {
  description = "フロントエンドから呼び出すAPIのベースURL（SAMスタックのApiBaseUrl出力をそのまま参照）"
  value       = data.aws_cloudformation_stack.backend.outputs["ApiBaseUrl"]
}

output "api_key_value" {
  description = "APIキーの値（config.jsのapiKeyに設定）。`terraform output -raw api_key_value` で表示"
  value       = aws_api_gateway_api_key.this.value
  sensitive   = true
}

output "cloudfront_domain_name" {
  description = "フロントエンド配信用CloudFrontドメイン名"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_bucket_name" {
  description = "フロントエンド静的ファイルのアップロード先S3バケット名"
  value       = aws_s3_bucket.frontend.bucket
}

output "iot_data_endpoint" {
  description = "AWS IoT Coreデータプレーンエンドポイント（デバイス側MQTT接続先）"
  value       = data.aws_iot_endpoint.data_ats.endpoint_address
}
