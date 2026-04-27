# Production plan (AWS + Terraform + GitHub Actions)

## 1) Goals
- Deploy `api` and `whatcommerce` workers on AWS with autoscaling.
- Keep compute in private subnets; expose only through load balancers.
- Host web frontend on S3 + CloudFront.
- Store uploaded images on S3.
- Support `dev`, `staging`, and `prod` environments.
- Use one IaC approach (Terraform) and one CI/CD path (GitHub Actions).

## 2) Target region
- Primary region: `us-east-1` (N. Virginia, US East).

## 3) Target architecture

### Network (per environment)
- 1 VPC
- 2 public subnets (multi-AZ)
- 2 private app subnets (multi-AZ)
- 1 internet gateway
- NAT gateway(s) for private subnet egress
- Route tables:
  - Public subnets -> Internet Gateway
  - Private subnets -> NAT Gateway

### Compute
- `api` service on EC2 Auto Scaling Group behind an Application Load Balancer (ALB).
- `whatcommerce` worker on EC2 Auto Scaling Group (private subnet).  
  - If webhook/public ingress is needed, put it behind a separate ALB.
- Launch templates for both services.

### Storage + CDN
- `web` static build -> S3 bucket -> CloudFront distribution.
- `images` uploads -> dedicated S3 bucket.

### Security baseline
- Least-privilege IAM roles for EC2 and GitHub Actions.
- Security groups:
  - ALB accepts `80/443` from internet
  - App instances accept traffic only from ALB SG
- S3 bucket encryption enabled.
- CloudFront HTTPS only.
- Secrets in AWS SSM Parameter Store or Secrets Manager (not in repo).

## 4) Terraform structure
- `infra/environments/dev`
- `infra/environments/staging`
- `infra/environments/prod`
- `infra/modules/vpc`
- `infra/modules/alb`
- `infra/modules/ec2_asg`
- `infra/modules/s3_static_site`
- `infra/modules/s3_uploads`
- `infra/modules/iam_ci`

## 5) CI/CD (GitHub Actions)
- Web pipeline:
  - Build Next.js static output
  - Sync to S3 web bucket
  - Invalidate CloudFront cache
- API/worker pipeline:
  - Build artifact/image
  - Deploy to ASG instances (rolling strategy)
- Environment promotion:
  - `dev` on push to `develop`
  - `staging` on push to `staging`
  - `prod` on release/manual approval

## 6) Rollout phases
- Phase 1: VPC + subnets + NAT + security groups.
- Phase 2: S3 (web + images) + CloudFront.
- Phase 3: API ASG + ALB.
- Phase 4: Whatcommerce ASG + connectivity.
- Phase 5: GitHub Actions + environment secrets + deployment workflows.
- Phase 6: Monitoring, alarms, logs, and backup hardening.

## 7) Start now (first implementation steps)
- [ ] Create `infra/` Terraform root with `dev/staging/prod`.
- [ ] Implement shared `vpc` module for `us-east-1`.
- [ ] Provision S3 buckets (`web`, `images`) and CloudFront for `dev`.
- [ ] Deploy API ASG + ALB for `dev`.
- [ ] Add first GitHub Actions workflow for `dev` web deploy.