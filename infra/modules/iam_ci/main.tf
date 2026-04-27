locals {
  tags = merge(var.tags, { Module = "iam_ci" })
  asg_arns = [
    for n in var.autoscaling_group_names :
    "arn:aws:autoscaling:${var.aws_region}:${data.aws_caller_identity.current.account_id}:autoScalingGroup:*:autoScalingGroupName/${n}"
  ]
}

data "aws_caller_identity" "current" {}

data "tls_certificate" "github_oidc" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  thumbprint_list = [data.tls_certificate.github_oidc.certificates[0].sha1_fingerprint]

  tags = merge(local.tags, {
    Name = "${var.name}-github-oidc"
  })
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_owner}/${var.github_repo}:ref:refs/heads/${var.github_branch}"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-github-oidc-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = merge(local.tags, {
    Name = "${var.name}-github-oidc-role"
  })
}

data "aws_iam_policy_document" "deploy_web" {
  statement {
    sid    = "S3BucketList"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [var.s3_bucket_arn]
  }

  statement {
    sid    = "S3ObjectRW"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${var.s3_bucket_arn}/*"]
  }

  statement {
    sid    = "CloudFrontInvalidation"
    effect = "Allow"
    actions = [
      "cloudfront:CreateInvalidation",
      "cloudfront:GetInvalidation",
    ]
    resources = [var.cloudfront_distribution_arn]
  }

  statement {
    sid    = "AutoScalingRead"
    effect = "Allow"
    actions = [
      "autoscaling:DescribeAutoScalingGroups",
      "autoscaling:DescribeInstanceRefreshes",
    ]
    resources = ["*"]
  }

  dynamic "statement" {
    for_each = length(local.asg_arns) > 0 ? [1] : []
    content {
      sid    = "AutoScalingRefresh"
      effect = "Allow"
      actions = [
        "autoscaling:StartInstanceRefresh",
        "autoscaling:CancelInstanceRefresh",
      ]
      resources = local.asg_arns
    }
  }
}

resource "aws_iam_policy" "deploy_web" {
  name   = "${var.name}-deploy-web-policy"
  policy = data.aws_iam_policy_document.deploy_web.json

  tags = merge(local.tags, {
    Name = "${var.name}-deploy-web-policy"
  })
}

resource "aws_iam_role_policy_attachment" "deploy_web" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.deploy_web.arn
}
