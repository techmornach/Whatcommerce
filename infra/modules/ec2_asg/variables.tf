variable "name" {
  description = "Name prefix for ASG resources"
  type        = string
}

variable "ami_id" {
  description = "AMI ID for instances"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "subnet_ids" {
  description = "Subnet IDs for ASG"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for launch template"
  type        = list(string)
}

variable "target_group_arns" {
  description = "Target groups to attach ASG"
  type        = list(string)
  default     = []
}

variable "min_size" {
  description = "ASG minimum size"
  type        = number
  default     = 1
}

variable "desired_capacity" {
  description = "ASG desired capacity"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "ASG max size"
  type        = number
  default     = 2
}

variable "key_name" {
  description = "Optional EC2 key pair name"
  type        = string
  default     = null
}

variable "iam_instance_profile_name" {
  description = "Optional IAM instance profile name"
  type        = string
  default     = null
}

variable "user_data_base64" {
  description = "Optional base64 user data"
  type        = string
  default     = null
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
