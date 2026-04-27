locals {
  name = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  api_env_content = trimspace(
    var.api_env_content != ""
    ? var.api_env_content
    : (var.api_env_file_path != "" && can(file(var.api_env_file_path)) ? file(var.api_env_file_path) : "")
  )
  has_api_env = length(local.api_env_content) > 0

  worker_env_content = trimspace(
    var.worker_env_content != ""
    ? var.worker_env_content
    : (var.worker_env_file_path != "" && can(file(var.worker_env_file_path)) ? file(var.worker_env_file_path) : "")
  )
  has_worker_env = length(local.worker_env_content) > 0

  has_custom_domains = (
    trimspace(var.hosted_zone_name) != "" &&
    trimspace(var.api_domain_name) != "" &&
    trimspace(var.web_domain_name) != ""
  )
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

data "aws_caller_identity" "current" {}

data "aws_route53_zone" "public" {
  count        = local.has_custom_domains ? 1 : 0
  name         = var.hosted_zone_name
  private_zone = false
}

resource "aws_acm_certificate" "dev" {
  count             = local.has_custom_domains ? 1 : 0
  domain_name       = "*.${var.hosted_zone_name}"
  validation_method = "DNS"

  subject_alternative_names = [var.hosted_zone_name]

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name}-shared-cert"
  })
}

resource "aws_route53_record" "cert_validation" {
  count = local.has_custom_domains ? 1 : 0

  allow_overwrite = true
  zone_id         = data.aws_route53_zone.public[0].zone_id
  name            = tolist(aws_acm_certificate.dev[0].domain_validation_options)[0].resource_record_name
  type            = tolist(aws_acm_certificate.dev[0].domain_validation_options)[0].resource_record_type
  ttl             = 60
  records         = [tolist(aws_acm_certificate.dev[0].domain_validation_options)[0].resource_record_value]
}

resource "aws_acm_certificate_validation" "dev" {
  count = local.has_custom_domains ? 1 : 0

  certificate_arn         = aws_acm_certificate.dev[0].arn
  validation_record_fqdns = [aws_route53_record.cert_validation[0].fqdn]
}

module "api_env_secret" {
  count  = local.has_api_env ? 1 : 0
  source = "../../modules/secrets_manager"

  name          = "${local.name}/api/env"
  description   = "Whatcommerce API .env for ${var.environment}"
  secret_string = local.api_env_content
  tags          = local.common_tags
}

module "worker_env_secret" {
  count  = var.worker_enabled && local.has_worker_env ? 1 : 0
  source = "../../modules/secrets_manager"

  name          = "${local.name}/worker/env"
  description   = "Whatcommerce worker .env for ${var.environment}"
  secret_string = local.worker_env_content
  tags          = local.common_tags
}

data "aws_iam_policy_document" "api_instance_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "api_instance_permissions" {
  dynamic "statement" {
    for_each = local.has_api_env ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue",
      ]
      resources = [module.api_env_secret[0].secret_arn]
    }
  }
}

data "aws_iam_policy_document" "worker_instance_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "worker_instance_permissions" {
  dynamic "statement" {
    for_each = var.worker_enabled && local.has_worker_env ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue",
      ]
      resources = [module.worker_env_secret[0].secret_arn]
    }
  }
}

resource "aws_iam_role" "api_instance" {
  name               = "${local.name}-api-instance-role"
  assume_role_policy = data.aws_iam_policy_document.api_instance_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_policy" "api_instance" {
  count  = local.has_api_env ? 1 : 0
  name   = "${local.name}-api-instance-policy"
  policy = data.aws_iam_policy_document.api_instance_permissions.json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "api_instance" {
  count      = local.has_api_env ? 1 : 0
  role       = aws_iam_role.api_instance.name
  policy_arn = aws_iam_policy.api_instance[0].arn
}

resource "aws_iam_instance_profile" "api_instance" {
  name = "${local.name}-api-instance-profile"
  role = aws_iam_role.api_instance.name
}

resource "aws_iam_role" "worker_instance" {
  count              = var.worker_enabled ? 1 : 0
  name               = "${local.name}-worker-instance-role"
  assume_role_policy = data.aws_iam_policy_document.worker_instance_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_policy" "worker_instance" {
  count  = var.worker_enabled && local.has_worker_env ? 1 : 0
  name   = "${local.name}-worker-instance-policy"
  policy = data.aws_iam_policy_document.worker_instance_permissions.json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "worker_instance" {
  count      = var.worker_enabled && local.has_worker_env ? 1 : 0
  role       = aws_iam_role.worker_instance[0].name
  policy_arn = aws_iam_policy.worker_instance[0].arn
}

resource "aws_iam_instance_profile" "worker_instance" {
  count = var.worker_enabled ? 1 : 0
  name  = "${local.name}-worker-instance-profile"
  role  = aws_iam_role.worker_instance[0].name
}

module "vpc" {
  source = "../../modules/vpc"

  name                 = local.name
  vpc_cidr             = var.vpc_cidr
  azs                  = var.azs
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  tags                 = local.common_tags
}

module "api_alb" {
  source = "../../modules/alb"

  name              = "${local.name}-api"
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  target_port       = var.api_port
  health_check_path = var.api_health_check_path
  enable_https      = local.has_custom_domains
  certificate_arn   = local.has_custom_domains ? aws_acm_certificate_validation.dev[0].certificate_arn : ""
  tags              = local.common_tags
}

resource "aws_security_group" "api" {
  name        = "${local.name}-api-sg"
  description = "Allow API traffic only from ALB"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = var.api_port
    to_port         = var.api_port
    protocol        = "tcp"
    security_groups = [module.api_alb.alb_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name}-api-sg"
  })
}

module "api_asg" {
  source = "../../modules/ec2_asg"

  name                      = "${local.name}-api"
  ami_id                    = data.aws_ami.amazon_linux_2023.id
  instance_type             = var.api_instance_type
  subnet_ids                = module.vpc.private_subnet_ids
  security_group_ids        = [aws_security_group.api.id]
  target_group_arns         = [module.api_alb.target_group_arn]
  min_size                  = var.api_min_size
  desired_capacity          = var.api_desired_capacity
  max_size                  = var.api_max_size
  iam_instance_profile_name = aws_iam_instance_profile.api_instance.name
  user_data_base64 = base64encode(templatefile("${path.module}/user_data_api.sh.tftpl", {
    api_port           = var.api_port
    aws_region         = var.aws_region
    api_env_secret_arn = local.has_api_env ? module.api_env_secret[0].secret_arn : ""
    bootstrap_mode     = var.api_bootstrap_mode
    api_repo_url       = var.api_repo_url
    api_repo_ref       = var.api_repo_ref
    api_app_subdir     = var.api_app_subdir
    api_uvicorn_app    = var.api_uvicorn_app
  }))
  tags = local.common_tags
}

resource "aws_security_group" "worker" {
  count       = var.worker_enabled ? 1 : 0
  name        = "${local.name}-worker-sg"
  description = "Whatcommerce worker security group (egress only)"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name}-worker-sg"
  })
}

module "worker_asg" {
  count  = var.worker_enabled ? 1 : 0
  source = "../../modules/ec2_asg"

  name                      = "${local.name}-worker"
  ami_id                    = data.aws_ami.amazon_linux_2023.id
  instance_type             = var.worker_instance_type
  subnet_ids                = module.vpc.private_subnet_ids
  security_group_ids        = [aws_security_group.worker[0].id]
  min_size                  = var.worker_min_size
  desired_capacity          = var.worker_desired_capacity
  max_size                  = var.worker_max_size
  iam_instance_profile_name = aws_iam_instance_profile.worker_instance[0].name
  user_data_base64 = base64encode(templatefile("${path.module}/user_data_worker.sh.tftpl", {
    aws_region            = var.aws_region
    worker_env_secret_arn = local.has_worker_env ? module.worker_env_secret[0].secret_arn : ""
    worker_repo_url       = var.worker_repo_url
    worker_repo_ref       = var.worker_repo_ref
    worker_app_subdir     = var.worker_app_subdir
    worker_start_command  = var.worker_start_command
  }))
  tags = local.common_tags
}

module "uploads_bucket" {
  source = "../../modules/s3_uploads"

  bucket_name = "${var.uploads_bucket_prefix}-${var.environment}-${var.aws_region}-${data.aws_caller_identity.current.account_id}"
  tags        = local.common_tags
}

module "web_static_site" {
  source = "../../modules/s3_static_site"

  bucket_name         = "${var.web_bucket_prefix}-${var.environment}-${var.aws_region}-${data.aws_caller_identity.current.account_id}"
  aliases             = local.has_custom_domains ? [var.web_domain_name] : []
  acm_certificate_arn = local.has_custom_domains ? aws_acm_certificate_validation.dev[0].certificate_arn : ""
  tags                = local.common_tags
}

resource "aws_route53_record" "api_alias_a" {
  count   = local.has_custom_domains ? 1 : 0
  zone_id = data.aws_route53_zone.public[0].zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = module.api_alb.alb_dns_name
    zone_id                = module.api_alb.alb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "api_alias_aaaa" {
  count   = local.has_custom_domains ? 1 : 0
  zone_id = data.aws_route53_zone.public[0].zone_id
  name    = var.api_domain_name
  type    = "AAAA"

  alias {
    name                   = module.api_alb.alb_dns_name
    zone_id                = module.api_alb.alb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "web_alias_a" {
  count   = local.has_custom_domains ? 1 : 0
  zone_id = data.aws_route53_zone.public[0].zone_id
  name    = var.web_domain_name
  type    = "A"

  alias {
    name                   = module.web_static_site.cloudfront_domain_name
    zone_id                = module.web_static_site.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "web_alias_aaaa" {
  count   = local.has_custom_domains ? 1 : 0
  zone_id = data.aws_route53_zone.public[0].zone_id
  name    = var.web_domain_name
  type    = "AAAA"

  alias {
    name                   = module.web_static_site.cloudfront_domain_name
    zone_id                = module.web_static_site.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

module "iam_ci" {
  source = "../../modules/iam_ci"

  name                        = "${local.name}-web"
  github_owner                = var.github_owner
  github_repo                 = var.github_repo
  github_branch               = var.github_deploy_branch
  s3_bucket_arn               = module.web_static_site.bucket_arn
  cloudfront_distribution_arn = module.web_static_site.cloudfront_distribution_arn
  tags                        = local.common_tags
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "api_alb_dns_name" {
  value = module.api_alb.alb_dns_name
}

output "api_asg_name" {
  value = module.api_asg.autoscaling_group_name
}

output "uploads_bucket_name" {
  value = module.uploads_bucket.bucket_name
}

output "web_bucket_name" {
  value = module.web_static_site.bucket_name
}

output "web_cloudfront_domain_name" {
  value = module.web_static_site.cloudfront_domain_name
}

output "api_url" {
  value = local.has_custom_domains ? "https://${var.api_domain_name}" : "http://${module.api_alb.alb_dns_name}"
}

output "web_url" {
  value = local.has_custom_domains ? "https://${var.web_domain_name}" : "https://${module.web_static_site.cloudfront_domain_name}"
}

output "web_cloudfront_distribution_id" {
  value = module.web_static_site.cloudfront_distribution_id
}

output "github_oidc_role_arn" {
  value = module.iam_ci.role_arn
}

output "api_env_secret_arn" {
  value     = local.has_api_env ? module.api_env_secret[0].secret_arn : ""
  sensitive = true
}

output "worker_asg_name" {
  value = var.worker_enabled ? module.worker_asg[0].autoscaling_group_name : ""
}

output "worker_env_secret_arn" {
  value     = var.worker_enabled && local.has_worker_env ? module.worker_env_secret[0].secret_arn : ""
  sensitive = true
}
