output "endpoint" {
  description = "RDS endpoint hostname"
  value       = aws_db_instance.this.address
}

output "port" {
  description = "RDS endpoint port"
  value       = aws_db_instance.this.port
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.this.db_name
}

output "username" {
  description = "Master username"
  value       = aws_db_instance.this.username
}

output "security_group_id" {
  description = "Database security group ID"
  value       = aws_security_group.db.id
}
