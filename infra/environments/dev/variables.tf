variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "whatcommerce"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR for dev"
  type        = string
  default     = "10.30.0.0/16"
}

variable "azs" {
  description = "AZs for dev deployment"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.30.1.0/24", "10.30.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.30.11.0/24", "10.30.12.0/24"]
}

variable "api_instance_type" {
  description = "API EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "api_min_size" {
  description = "API ASG minimum size"
  type        = number
  default     = 1
}

variable "api_desired_capacity" {
  description = "API ASG desired capacity"
  type        = number
  default     = 1
}

variable "api_max_size" {
  description = "API ASG max size"
  type        = number
  default     = 2
}

variable "api_port" {
  description = "API service port"
  type        = number
  default     = 8000
}

variable "api_health_check_path" {
  description = "API health check path"
  type        = string
  default     = "/health"
}

variable "api_bootstrap_mode" {
  description = "API bootstrap mode: stub or real"
  type        = string
  default     = "stub"
}

variable "api_repo_url" {
  description = "Git repository URL for API source checkout in real bootstrap mode"
  type        = string
  default     = ""
}

variable "api_repo_ref" {
  description = "Git branch/tag/ref for API checkout in real bootstrap mode"
  type        = string
  default     = "main"
}

variable "api_app_subdir" {
  description = "Subdirectory containing API app (relative to repo root)"
  type        = string
  default     = "api"
}

variable "api_uvicorn_app" {
  description = "Uvicorn import path, e.g. app.main:app"
  type        = string
  default     = "app.main:app"
}

variable "api_env_file_path" {
  description = "Local path to API .env file to store in Secrets Manager"
  type        = string
  default     = ""
}

variable "api_env_content" {
  description = "Raw API .env content (optional alternative to file path)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "web_bucket_prefix" {
  description = "Prefix for web static S3 bucket name"
  type        = string
  default     = "whatcommerce-web"
}

variable "uploads_bucket_prefix" {
  description = "Prefix for uploads S3 bucket name"
  type        = string
  default     = "whatcommerce-uploads"
}

variable "github_owner" {
  description = "GitHub organization/user that owns the repository"
  type        = string
  default     = "techmornach"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "Whatcommerce"
}

variable "github_deploy_branch" {
  description = "Branch allowed for OIDC deploy role (dev web deploy)"
  type        = string
  default     = "main"
}

variable "worker_enabled" {
  description = "Whether to provision whatcommerce worker ASG"
  type        = bool
  default     = true
}

variable "worker_instance_type" {
  description = "Worker EC2 instance type"
  type        = string
  default     = "t3.large"
}

variable "worker_min_size" {
  description = "Worker ASG minimum size"
  type        = number
  default     = 1
}

variable "worker_desired_capacity" {
  description = "Worker ASG desired capacity"
  type        = number
  default     = 1
}

variable "worker_max_size" {
  description = "Worker ASG max size"
  type        = number
  default     = 1
}

variable "worker_repo_url" {
  description = "Git repository URL for worker checkout"
  type        = string
  default     = "https://github.com/techmornach/Whatcommerce.git"
}

variable "worker_repo_ref" {
  description = "Git branch/tag/ref for worker checkout"
  type        = string
  default     = "main"
}

variable "worker_app_subdir" {
  description = "Subdirectory containing worker app (relative to repo root)"
  type        = string
  default     = "whatsapp/whatcommerce"
}

variable "worker_start_command" {
  description = "Shell command used to start worker service"
  type        = string
  default     = "node index.mjs"
}

variable "worker_env_file_path" {
  description = "Local path to worker .env file to store in Secrets Manager"
  type        = string
  default     = ""
}

variable "worker_env_content" {
  description = "Raw worker .env content (optional alternative to file path)"
  type        = string
  default     = ""
  sensitive   = true
}
