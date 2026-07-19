# Lambda関数・IAMロール・API Gateway本体(ルーティング/統合)はAWS SAM
# (backend/sam/template.yaml, backend/sam/openapi.yaml) 側で管理する。
# ここではSAMがデプロイしたREST APIに対して、APIキーと使用量プランのみを
# Terraformで管理する。

# --- SAMでデプロイ済みのCloudFormationスタックを参照 ---
data "aws_cloudformation_stack" "backend" {
  name = var.sam_stack_name
}

# --- APIキー ---
resource "aws_api_gateway_api_key" "this" {
  name = "${var.project_name}-key"
}

# --- 使用量プラン（SAM側のAPI ID・ステージに紐付け） ---
resource "aws_api_gateway_usage_plan" "this" {
  name = "${var.project_name}-usage-plan"

  api_stages {
    api_id = data.aws_cloudformation_stack.backend.outputs["ApiId"]
    stage  = var.environment
  }
}

resource "aws_api_gateway_usage_plan_key" "this" {
  key_id        = aws_api_gateway_api_key.this.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.this.id
}
