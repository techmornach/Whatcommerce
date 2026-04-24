variable "aws_region" {
  type        = string
  description = "AWS region for all resources."
  default     = "eu-west-1"
}

variable "project_name" {
  type        = string
  description = "Prefix for resource names."
  default     = "whatcommerce"
}

variable "environment" {
  type        = string
  description = "Environment label (e.g. dev, staging, prod)."
  default     = "dev"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC IPv4 CIDR."
  default     = "10.20.0.0/16"
}

variable "api_instance_type" {
  type        = string
  description = "EC2 instance type for FastAPI."
  default     = "t3.small"
}

variable "bridge_instance_type" {
  type        = string
  description = "EC2 instance type for whatsapp-web.js + Chromium (needs RAM/CPU)."
  default     = "t3.medium"
}

variable "db_name" {
  type        = string
  description = "Initial PostgreSQL database name."
  default     = "whatcommerce"
}

variable "db_username" {
  type        = string
  description = "RDS master username."
  default     = "whatcommerce"
}

variable "db_instance_class" {
  type        = string
  description = "RDS instance class."
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type        = number
  description = "RDS allocated storage (GiB)."
  default     = 20
}

variable "enable_nat_gateway" {
  type        = bool
  description = "NAT gateway for private subnet egress (WhatsApp, OpenAI, package updates)."
  default     = true
}

variable "ssh_cidr_blocks" {
  type        = list(string)
  description = "Optional CIDRs allowed to SSH to instances on port 22 (usually empty; use SSM)."
  default     = []
}

variable "key_name" {
  type        = string
  description = "Optional EC2 key pair name for SSH (leave empty to rely on SSM only)."
  default     = ""
}
