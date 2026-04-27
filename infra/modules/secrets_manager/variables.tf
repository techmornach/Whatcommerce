variable "name" {
  description = "Secret name"
  type        = string
}

variable "description" {
  description = "Secret description"
  type        = string
  default     = "Managed by Terraform"
}

variable "secret_string" {
  description = "Secret value string"
  type        = string
  sensitive   = true
}

variable "recovery_window_in_days" {
  description = "Recovery window in days for secret deletion"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
