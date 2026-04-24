data "aws_ssm_parameter" "al2023_x86" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

locals {
  api_private_ip    = cidrhost(aws_subnet.private_app.cidr_block, local.api_private_ip_hostnum)
  bridge_private_ip = cidrhost(aws_subnet.private_app.cidr_block, local.bridge_private_ip_hostnum)
  ec2_bootstrap_depends_on = concat(
    [aws_route_table_association.private_app],
    var.enable_nat_gateway ? [aws_nat_gateway.main[0]] : [],
  )
}

resource "aws_instance" "api" {
  ami                         = data.aws_ssm_parameter.al2023_x86.value
  instance_type               = var.api_instance_type
  subnet_id                   = aws_subnet.private_app.id
  private_ip                  = local.api_private_ip
  vpc_security_group_ids      = [aws_security_group.ec2_api.id]
  iam_instance_profile        = aws_iam_instance_profile.api.name
  associate_public_ip_address = false

  key_name = length(var.key_name) > 0 ? var.key_name : null

  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = base64encode(templatefile("${path.module}/templates/api_user_data.sh.tftpl", {
    aws_region          = var.aws_region
    internal_param_name = aws_ssm_parameter.internal_secret.name
    bridge_base_url     = "http://${local.bridge_private_ip}:3001"
    db_secret_arn       = aws_secretsmanager_secret.db.arn
    default_tenant_id   = "${var.project_name}-${var.environment}"
  }))

  depends_on = concat(
    local.ec2_bootstrap_depends_on,
    [aws_db_instance.main, aws_secretsmanager_secret_version.db],
  )

  tags = {
    Name = "${local.name}-ec2-api"
    Role = "api"
  }
}

resource "aws_instance" "wa_bridge" {
  ami                         = data.aws_ssm_parameter.al2023_x86.value
  instance_type               = var.bridge_instance_type
  subnet_id                   = aws_subnet.private_app.id
  private_ip                  = local.bridge_private_ip
  vpc_security_group_ids      = [aws_security_group.ec2_bridge.id]
  iam_instance_profile        = aws_iam_instance_profile.bridge.name
  associate_public_ip_address = false

  key_name = length(var.key_name) > 0 ? var.key_name : null

  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size           = 50
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = base64encode(templatefile("${path.module}/templates/bridge_user_data.sh.tftpl", {
    aws_region          = var.aws_region
    internal_param_name = aws_ssm_parameter.internal_secret.name
    api_base_url        = "http://${local.api_private_ip}:8000"
    default_tenant_id   = "${var.project_name}-${var.environment}"
  }))

  depends_on = local.ec2_bootstrap_depends_on

  tags = {
    Name = "${local.name}-ec2-wa-bridge"
    Role = "wa-bridge"
  }
}
