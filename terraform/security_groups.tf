resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "PostgreSQL RDS"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-rds" }
}

resource "aws_security_group" "ec2_api" {
  name        = "${local.name}-ec2-api"
  description = "FastAPI EC2"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-ec2-api" }
}

resource "aws_security_group" "ec2_bridge" {
  name        = "${local.name}-ec2-wa-bridge"
  description = "whatsapp-web.js bridge EC2"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-ec2-bridge" }
}

resource "aws_security_group_rule" "rds_from_api" {
  type                     = "ingress"
  security_group_id        = aws_security_group.rds.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ec2_api.id
}

resource "aws_security_group_rule" "api_from_bridge" {
  type                     = "ingress"
  security_group_id        = aws_security_group.ec2_api.id
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ec2_bridge.id
}

resource "aws_security_group_rule" "bridge_from_api" {
  type                     = "ingress"
  security_group_id        = aws_security_group.ec2_bridge.id
  from_port                = 3001
  to_port                  = 3001
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ec2_api.id
}

resource "aws_security_group_rule" "api_ssh" {
  count                    = length(var.ssh_cidr_blocks) > 0 ? 1 : 0
  type                     = "ingress"
  security_group_id        = aws_security_group.ec2_api.id
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  cidr_blocks              = var.ssh_cidr_blocks
  description              = "SSH (prefer SSM)"
}

resource "aws_security_group_rule" "bridge_ssh" {
  count                    = length(var.ssh_cidr_blocks) > 0 ? 1 : 0
  type                     = "ingress"
  security_group_id        = aws_security_group.ec2_bridge.id
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  cidr_blocks              = var.ssh_cidr_blocks
  description              = "SSH (prefer SSM)"
}
