variable "project_name" {
  description = "リソース名のプレフィックスとして使用"
  type        = string
  default     = "led-iot"
}

variable "aws_region" {
  description = "デプロイ先AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "環境名（APIステージ名としても使用）"
  type        = string
  default     = "dev"
}

variable "thing_name" {
  description = "AWS IoT Thing名（制御対象のLEDデバイス）"
  type        = string
  default     = "led-device-01"
}

variable "sam_stack_name" {
  description = "backend/sam/samconfig.toml の stack_name と合わせるSAM(CloudFormation)スタック名"
  type        = string
  default     = "led-iot-backend"
}
