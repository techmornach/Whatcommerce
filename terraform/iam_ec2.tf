data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api" {
  name               = "${local.name}-ec2-api-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = { Name = "${local.name}-ec2-api-role" }
}

resource "aws_iam_role" "bridge" {
  name               = "${local.name}-ec2-bridge-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = { Name = "${local.name}-ec2-bridge-role" }
}

resource "aws_iam_role_policy_attachment" "api_ssm" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "bridge_ssm" {
  role       = aws_iam_role.bridge.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "api_db_secret" {
  name = "${local.name}-api-db-secret-read"
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.db.arn
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = aws_ssm_parameter.internal_secret.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "bridge_internal_ssm" {
  name = "${local.name}-bridge-internal-ssm"
  role = aws_iam_role.bridge.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter"]
      Resource = aws_ssm_parameter.internal_secret.arn
    }]
  })
}

resource "aws_iam_instance_profile" "api" {
  name = "${local.name}-ec2-api-profile"
  role = aws_iam_role.api.name
}

resource "aws_iam_instance_profile" "bridge" {
  name = "${local.name}-ec2-bridge-profile"
  role = aws_iam_role.bridge.name
}
