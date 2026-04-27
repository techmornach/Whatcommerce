variable "name" {
  description = "Name prefix for ALB resources"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "target_port" {
  description = "Target group port"
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "Health check path for target group"
  type        = string
  default     = "/health"
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN for HTTPS listener"
  type        = string
  default     = ""
}

variable "enable_https" {
  description = "Whether to enable HTTPS listener and HTTP->HTTPS redirect"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
