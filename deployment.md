# Whatcommerce Deployment Guide

This guide explains how to deploy Whatcommerce after cloning the repo.

It covers:

- AWS infrastructure provisioning with Terraform
- GitHub Actions deployment for web + worker
- Domain setup (`api.<zone>` and `whatcommerce.<zone>`)
- Verification, updates, and teardown

## 1) Deployment architecture (dev environment)

`infra/environments/dev` provisions:

- VPC + public/private subnets + NAT
- ALB for API
- API EC2 Auto Scaling Group
- Worker EC2 Auto Scaling Group (WhatsApp bridge)
- RDS PostgreSQL
- S3 uploads bucket
- S3 + CloudFront static hosting for web
- Route53 + ACM (if custom domain variables are set)
- GitHub OIDC IAM role for CI deploy
- Secrets Manager for API and worker `.env` content

## 2) Prerequisites

- AWS account access with permission to create IAM/VPC/EC2/ALB/RDS/S3/CloudFront/Route53/ACM/Secrets
- Terraform >= 1.5
- AWS CLI configured locally
- GitHub repository admin access (to set repo variables/secrets)
- A Route53 hosted zone (for custom domains), e.g. `play.jaraflytech.com`

Validate tools:

```bash
terraform version
aws --version
git --version
```

## 3) Prepare runtime env files

Terraform pushes your local env files into AWS Secrets Manager.

Create and confirm:

- `api/.env`
- `whatsapp/whatcommerce/.env`

Minimum important values:

### `api/.env`

- `INTERNAL_API_KEY` (must match worker)
- `CORS_ORIGINS` (include your web domain)
- `BOOTSTRAP_ADMIN=1` + bootstrap credentials (first deploy convenience)
- `PAYSTACK_SECRET_KEY` (if using billing)
- `OPENAI_API_KEY` (if using AI features)

### `whatsapp/whatcommerce/.env`

- `INTERNAL_API_KEY` (same value as API)
- `WHATCOMMERCE_API_BASE` (Terraform injects this at boot in AWS)
- `DISPATCH_PORT=3001`

## 4) Configure Terraform variables

From repo root:

```bash
cd infra/environments/dev
cp terraform.tfvars.example terraform.tfvars
cp secrets.auto.tfvars.example secrets.auto.tfvars
```

Update `terraform.tfvars` for your repo/account, especially:

- `api_bootstrap_mode = "real"`
- `api_repo_url`, `api_repo_ref`
- `worker_repo_url`, `worker_repo_ref`
- `api_env_file_path`
- `worker_env_file_path`
- `hosted_zone_name`, `api_domain_name`, `web_domain_name` (if using custom domains)

`secrets.auto.tfvars` should point to your local env files and remain uncommitted.

## 5) Provision infrastructure

```bash
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Capture outputs after apply (you will need them for GitHub):

- `github_oidc_role_arn`
- `web_bucket_name`
- `web_cloudfront_distribution_id`
- `web_cloudfront_domain_name`
- `worker_asg_name`
- `api_url`

## 6) Configure GitHub Actions deploy inputs

In your GitHub repo settings, add:

### Secret

- `AWS_ROLE_ARN_DEV` = Terraform output `github_oidc_role_arn`

### Variables

- `AWS_REGION_DEV` (example: `us-east-1`)
- `WEB_BUCKET_DEV` = `web_bucket_name`
- `WEB_CLOUDFRONT_DISTRIBUTION_ID_DEV` = `web_cloudfront_distribution_id`
- `WEB_CLOUDFRONT_DOMAIN_DEV` = `web_cloudfront_domain_name` (optional but recommended)
- `WORKER_ASG_NAME_DEV` = `worker_asg_name`
- `NEXT_PUBLIC_API_URL_DEV` = `api_url`

## 7) Deploy application code

The workflow `.github/workflows/deploy-dev.yml` deploys both web and worker.

Trigger options:

- Push to `main` with changes under `web/**`, `whatsapp/**`, or the workflow file
- Or run it manually from **Actions** with `workflow_dispatch`

What it does:

- Builds static web with `NEXT_PUBLIC_API_URL_DEV`
- Syncs `web/out` to S3
- Invalidates CloudFront
- Starts worker ASG instance refresh
- Waits for refresh success and prints links/summary

## 8) Verify deployment

1. Open web domain:
   - `https://whatcommerce.<your-zone>`
2. Check API health:
   - `https://api.<your-zone>/health`
3. Admin login:
   - `https://whatcommerce.<your-zone>/admin/login`
4. Verify bridge status from admin settings:
   - should move from `init` to `qr`/`ready`
5. If using WhatsApp bridge, scan QR and confirm `bot_connected = true`

## 9) Updating deployments

### Web-only changes

Push to `main`; workflow rebuilds and redeploys static web automatically.

### Worker behavior changes

Push to `main`; workflow triggers worker ASG instance refresh.

### API/env/infra changes

Apply Terraform again:

```bash
cd infra/environments/dev
terraform apply -var-file=terraform.tfvars
```

If API launch template changed, start API refresh manually:

```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name <api_asg_name> \
  --preferences '{"MinHealthyPercentage":50,"InstanceWarmup":120}'
```

## 10) Rollback strategy

- **Web rollback**: re-run deploy workflow from an older commit or manually sync older build output to S3 + invalidate CloudFront.
- **Worker rollback**: revert commit and redeploy; ASG refresh replaces instances.
- **Infra rollback**: revert Terraform changes and apply again.
- **Emergency**: cancel stuck worker refresh:

```bash
aws autoscaling cancel-instance-refresh \
  --auto-scaling-group-name <worker_asg_name>
```

## 11) Teardown (destroy dev environment)

Use `.github/workflows/destroy-dev.yml` from Actions.

Input required:

- `confirm = destroy-dev`

The workflow:

- validates confirmation
- authenticates via OIDC
- runs `terraform destroy -auto-approve` in `infra/environments/dev`

## 12) Common deployment issues

- **`Missing required repository variable` in Actions**
  - Add all required vars listed in section 6.

- **`AutoScalingGroup name not found - null`**
  - `WORKER_ASG_NAME_DEV` is missing/invalid.

- **API `502 Bad Gateway`**
  - API bootstrap failed on instance; check EC2 console output and systemd logs.
  - Re-apply infra if user-data/env changes were made.

- **CORS login errors**
  - Ensure deployed web origin is present in `CORS_ORIGINS` in `api/.env`, then re-apply infra and refresh API.

- **Worker stuck at "Starting WhatsApp client..."**
  - Usually browser/session startup issue.
  - Ensure `.wwebjs` runtime artifacts are not committed, then refresh worker ASG.

## 13) Security notes

- Never commit real `.env` files, `secrets.auto.tfvars`, or credential material.
- Rotate `INTERNAL_API_KEY`, JWT `SECRET_KEY`, and provider keys per environment.
- Restrict who can trigger destroy workflow.
- Consider separate `staging` and `prod` environments before production traffic.

## 14) Related docs

- `SETUP.md` for local development
- `infra/README.md` for Terraform module overview
- `README.md` for project quick start
