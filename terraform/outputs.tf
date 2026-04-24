output "vpc_id" {
  value       = aws_vpc.main.id
  description = "VPC ID."
}

output "private_app_subnet_id" {
  value       = aws_subnet.private_app.id
  description = "Private subnet where API and wa-bridge EC2 run."
}

output "api_private_ip" {
  value       = aws_instance.api.private_ip
  description = "Fixed private IP of the FastAPI instance."
}

output "wa_bridge_private_ip" {
  value       = aws_instance.wa_bridge.private_ip
  description = "Fixed private IP of the whatsapp-web.js bridge instance."
}

output "rds_endpoint" {
  value       = aws_db_instance.main.address
  description = "RDS hostname (private)."
}

output "rds_port" {
  value = aws_db_instance.main.port
}

output "db_credentials_secret_arn" {
  value       = aws_secretsmanager_secret.db.arn
  description = "Secrets Manager ARN holding RDS username/password/host/dbname JSON."
}

output "internal_secret_ssm_parameter" {
  value       = aws_ssm_parameter.internal_secret.name
  description = "SSM SecureString name for INTERNAL_SECRET (API and bridge read at boot)."
}

output "ssm_session_hint" {
  value       = "Use AWS Systems Manager Session Manager to reach instances (no SSH required)."
  description = "Operator hint."
}
