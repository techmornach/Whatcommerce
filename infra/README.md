# Whatcommerce Terraform bootstrap

## Structure
- `modules/vpc`: reusable VPC module (public/private subnets, IGW, NAT, routes)
- `modules/alb`: application load balancer + target group + listener
- `modules/ec2_asg`: launch template + autoscaling group
- `modules/s3_static_site`: private S3 + CloudFront (OAC) for web hosting
- `modules/s3_uploads`: private S3 bucket for image/media uploads
- `modules/iam_ci`: GitHub OIDC deploy role + least privilege web deploy policy
- `modules/secrets_manager`: reusable AWS Secrets Manager secret wrapper
- `environments/dev`: active environment scaffold (us-east-1)
- `environments/staging`: placeholder
- `environments/prod`: placeholder

## Quick start (dev)
1. Ensure AWS credentials are configured for your account.
2. From `infra/environments/dev`:
   - `terraform init`
   - `terraform plan -var-file=terraform.tfvars`
   - `terraform apply -var-file=terraform.tfvars`

Note: dev API user-data supports two modes:
- `api_bootstrap_mode = "stub"`: health-only FastAPI stub (`/health` on `:8000`)
- `api_bootstrap_mode = "real"`: clones repo + installs API deps + runs `uvicorn`

For real mode, set at least:
- `api_repo_url` (e.g. your GitHub repo URL)
- `api_repo_ref` (branch/tag)
- `api_env_file_path` or `api_env_content` so Terraform can store env in Secrets Manager

Worker mode (WhatsApp bridge):
- `worker_enabled = true`
- `worker_repo_url` + `worker_repo_ref`
- `worker_env_file_path` or `worker_env_content` (stored in Secrets Manager)

Custom domains (optional):
- `hosted_zone_name` (e.g. `play.jaraflytech.com`)
- `api_domain_name` (e.g. `api.play.jaraflytech.com`)
- `web_domain_name` (e.g. `whatcommerce.play.jaraflytech.com`)
- Terraform provisions ACM + Route53 aliases for API (ALB) and Web (CloudFront)

Clone-friendly setup:
- copy `infra/environments/dev/secrets.auto.tfvars.example` to `secrets.auto.tfvars`
- set `api_env_file_path` and `worker_env_file_path` to your local `.env` files
- keep `secrets.auto.tfvars` uncommitted (already gitignored)

## GitHub Actions deploy wiring (dev)
After apply, set these in your GitHub repository:
- Secret: `AWS_ROLE_ARN_DEV` -> output `github_oidc_role_arn`
- Variable: `AWS_REGION_DEV` -> `us-east-1` (or your env region)
- Variable: `WEB_BUCKET_DEV` -> output `web_bucket_name`
- Variable: `WEB_CLOUDFRONT_DISTRIBUTION_ID_DEV` -> output `web_cloudfront_distribution_id`
- Variable: `WEB_CLOUDFRONT_DOMAIN_DEV` -> output `web_cloudfront_domain_name` (optional, used to print final site URL in workflow summary)
- Variable: `WORKER_ASG_NAME_DEV` -> output `worker_asg_name`
- Variable: `NEXT_PUBLIC_API_URL_DEV` -> output `api_url` (recommended)

Workflow:
- `.github/workflows/deploy-dev.yml` deploys both web and worker in one run.

## Next modules to add
- `worker_asg` wiring for whatcommerce worker service
- optional `route53_acm` if custom domains are required
