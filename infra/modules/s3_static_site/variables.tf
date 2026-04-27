variable "bucket_name" {
  description = "Name for static web S3 bucket"
  type        = string
}

variable "aliases" {
  description = "Optional custom domain aliases for CloudFront"
  type        = list(string)
  default     = []
}

variable "acm_certificate_arn" {
  description = "Optional ACM certificate ARN for CloudFront (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
