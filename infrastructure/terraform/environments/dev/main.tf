# Development Environment Infrastructure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration (uncomment and configure for remote state)
  # backend "s3" {
  #   bucket         = "sqlselect-terraform-state-dev"
  #   key            = "dev/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-state-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      CostCenter  = "Engineering"
    }
  }
}

locals {
  cluster_name = "${var.project_name}-${var.environment}-eks"
}

# ============================================
# VPC
# ============================================

module "vpc" {
  source = "../../modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  cluster_name = local.cluster_name

  public_subnet_cidrs   = var.public_subnet_cidrs
  private_subnet_cidrs  = var.private_subnet_cidrs
  database_subnet_cidrs = var.database_subnet_cidrs

  enable_nat_gateway = true
  single_nat_gateway = true  # Cost optimization for dev
  enable_flow_logs   = false # Disabled for dev

  tags = var.tags
}

# ============================================
# EKS CLUSTER
# ============================================

module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.cluster_name
  cluster_version    = var.eks_cluster_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids

  cluster_endpoint_public_access       = true
  cluster_endpoint_public_access_cidrs = var.allowed_cidr_blocks

  # General node group - smaller for dev
  general_instance_types = ["t3.large"]
  general_desired_size   = 2
  general_min_size       = 1
  general_max_size       = 3
  general_capacity_type  = "SPOT" # Cost optimization for dev

  # GPU node group - minimal for dev
  enable_gpu_nodes     = true
  gpu_instance_types   = ["g4dn.xlarge"]
  gpu_desired_size     = 1
  gpu_min_size         = 0  # Can scale to 0 in dev
  gpu_max_size         = 2
  gpu_capacity_type    = "SPOT" # Cost optimization for dev

  enable_irsa = true

  tags = var.tags

  depends_on = [module.vpc]
}

# ============================================
# RDS POSTGRESQL
# ============================================

module "rds" {
  source = "../../modules/rds"

  identifier           = "${var.project_name}-${var.environment}-db"
  vpc_id               = module.vpc.vpc_id
  vpc_cidr             = module.vpc.vpc_cidr
  database_subnet_ids  = module.vpc.database_subnet_ids

  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  database_name   = var.database_name
  master_username = var.db_master_username
  master_password = var.db_master_password

  # Dev optimizations
  multi_az                 = false # Single AZ for dev
  create_read_replicas     = false # No replicas for dev
  backup_retention_period  = 7     # 7 days for dev
  deletion_protection      = false # Allow deletion in dev
  skip_final_snapshot      = true  # No final snapshot for dev

  # Smaller storage for dev
  allocated_storage     = 50
  max_allocated_storage = 200

  # Monitoring
  monitoring_interval          = 60
  performance_insights_enabled = true

  # Alarms
  create_cloudwatch_alarms = false # Disabled for dev

  tags = var.tags

  depends_on = [module.vpc]
}

# ============================================
# ELASTICACHE REDIS
# ============================================

module "elasticache" {
  source = "../../modules/elasticache"

  cluster_name       = "${var.project_name}-${var.environment}-redis"
  vpc_id             = module.vpc.vpc_id
  vpc_cidr           = module.vpc.vpc_cidr
  private_subnet_ids = module.vpc.private_subnet_ids

  engine_version = var.redis_engine_version
  node_type      = var.redis_node_type

  # Dev configuration - smaller cluster
  cluster_mode_enabled       = false
  num_cache_nodes            = 2
  automatic_failover_enabled = true
  multi_az_enabled           = false # Single AZ for dev

  # Security
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = var.redis_auth_token

  # Backup
  snapshot_retention_limit = 3 # 3 days for dev

  # Alarms
  create_cloudwatch_alarms = false # Disabled for dev

  tags = var.tags

  depends_on = [module.vpc]
}
