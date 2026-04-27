variable "name" {
  description = "Name prefix for CI IAM resources"
  type        = string
}

variable "github_owner" {
  description = "GitHub org or user that owns the repo"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "github_branch" {
  description = "Branch allowed to assume role"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 bucket ARN for web deploy"
  type        = string
}

variable "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN for cache invalidation"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
