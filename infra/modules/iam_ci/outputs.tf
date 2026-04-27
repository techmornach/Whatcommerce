output "role_arn" {
  description = "IAM role ARN for GitHub OIDC"
  value       = aws_iam_role.this.arn
}

output "role_name" {
  description = "IAM role name for GitHub OIDC"
  value       = aws_iam_role.this.name
}

output "policy_arn" {
  description = "IAM policy ARN for web deploy permissions"
  value       = aws_iam_policy.deploy_web.arn
}
