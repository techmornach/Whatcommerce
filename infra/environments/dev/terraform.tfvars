aws_region = "us-east-1"

project_name = "whatcommerce"
environment  = "dev"

vpc_cidr = "10.30.0.0/16"

azs = [
  "us-east-1a",
  "us-east-1b",
]

public_subnet_cidrs = [
  "10.30.1.0/24",
  "10.30.2.0/24",
]

private_subnet_cidrs = [
  "10.30.11.0/24",
  "10.30.12.0/24",
]

api_instance_type     = "t3.small"
api_min_size          = 1
api_desired_capacity  = 1
api_max_size          = 2
api_port              = 8000
api_health_check_path = "/health"
api_bootstrap_mode    = "real"
api_repo_url          = "https://github.com/techmornach/Whatcommerce.git"
api_repo_ref          = "main"
api_app_subdir        = "api"
api_uvicorn_app       = "app.main:app"
api_env_file_path     = "../../../api/.env"
api_env_content       = ""

worker_enabled          = true
worker_instance_type    = "t3.large"
worker_min_size         = 1
worker_desired_capacity = 1
worker_max_size         = 1
worker_repo_url         = "https://github.com/techmornach/Whatcommerce.git"
worker_repo_ref         = "main"
worker_app_subdir       = "whatsapp/whatcommerce"
worker_start_command    = "node index.mjs"
worker_env_file_path    = "../../../whatsapp/whatcommerce/.env"
worker_env_content      = ""

web_bucket_prefix     = "whatcommerce-web"
uploads_bucket_prefix = "whatcommerce-uploads"

github_owner         = "techmornach"
github_repo          = "Whatcommerce"
github_deploy_branch = "main"
