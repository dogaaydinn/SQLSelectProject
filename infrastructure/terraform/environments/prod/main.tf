# Production Environment Infrastructure
# Enterprise-grade configuration with high availability

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for remote state
  # backend "s3" {
  #   bucket         = "sqlselect-terraform-state-prod"
  #   key            = "prod/terraform.tfstate"
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
      CostCenter  = "Production"
      Compliance  = "SOC2"
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

  enable_nat_gateway        = true
  single_nat_gateway        = false # High availability - NAT per AZ
  enable_flow_logs          = true  # Security compliance
  flow_logs_retention_days  = 90    # 90 days for compliance

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

  cluster_endpoint_public_access       = var.cluster_endpoint_public_access
  cluster_endpoint_public_access_cidrs = var.allowed_cidr_blocks

  cluster_log_types           = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  cluster_log_retention_days  = 90 # Compliance requirement

  # General node group - production sizing
  general_instance_types = ["t3.xlarge", "t3.2xlarge"]
  general_desired_size   = 6
  general_min_size       = 3
  general_max_size       = 20
  general_capacity_type  = "ON_DEMAND" # Stability for production

  # GPU node group - CUDA analytics workloads
  enable_gpu_nodes     = true
  gpu_instance_types   = ["g4dn.2xlarge", "g4dn.4xlarge"] # Tesla T4 with more memory
  gpu_desired_size     = 3
  gpu_min_size         = 2  # Always available
  gpu_max_size         = 10
  gpu_capacity_type    = "ON_DEMAND" # Stability for production

  enable_irsa = true
  kms_key_arn = var.kms_key_arn  # Secrets encryption

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

  # Production high availability
  multi_az                 = true  # Multi-AZ failover
  create_read_replicas     = true  # Read replicas for read scaling
  read_replica_count       = 2     # 2 read replicas
  replica_instance_class   = "db.r6g.large" # Can be smaller than primary
  replica_multi_az         = false # Cost optimization

  # Production backup strategy
  backup_retention_period  = 30    # 30 days
  deletion_protection      = true  # Prevent accidental deletion
  skip_final_snapshot      = false # Final snapshot required

  # Production storage
  allocated_storage     = 500
  max_allocated_storage = 3000
  iops                  = 5000
  storage_throughput    = 250

  kms_key_arn = var.kms_key_arn # Encryption at rest

  # Enhanced monitoring
  monitoring_interval                   = 60
  performance_insights_enabled          = true
  performance_insights_retention_period = 31  # 31 days

  # CloudWatch alarms
  create_cloudwatch_alarms      = true
  alarm_sns_topic_arn           = var.alarm_sns_topic_arn
  cpu_alarm_threshold           = 75
  connections_alarm_threshold   = 150
  storage_alarm_threshold_bytes = 53687091200  # 50 GB

  # Performance tuning
  max_connections         = "500"
  log_min_duration_statement = "500"  # Log queries > 500ms

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

  # Production cluster configuration
  cluster_mode_enabled       = false  # Can enable for sharding if needed
  num_cache_nodes            = 3      # Primary + 2 replicas
  automatic_failover_enabled = true
  multi_az_enabled           = true   # High availability

  # Security - production requirements
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = var.redis_auth_token
  kms_key_arn                = var.kms_key_arn

  # Production backup
  snapshot_retention_limit = 14  # 14 days

  # CloudWatch alarms
  create_cloudwatch_alarms  = true
  alarm_sns_topic_arn       = var.alarm_sns_topic_arn
  cpu_alarm_threshold       = 70
  memory_alarm_threshold    = 85
  evictions_alarm_threshold = 100

  # Performance tuning
  maxmemory_policy = "allkeys-lru"  # Evict least recently used keys

  tags = var.tags

  depends_on = [module.vpc]
}
