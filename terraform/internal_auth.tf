resource "random_password" "internal_service" {
  length  = 48
  special = false
}

resource "aws_ssm_parameter" "internal_secret" {
  name        = "/${local.name}/INTERNAL_SECRET"
  description = "Shared secret for FastAPI <-> wa-bridge on private IPs"
  type        = "SecureString"
  value       = random_password.internal_service.result

  tags = { Name = "${local.name}-internal-secret" }
}
