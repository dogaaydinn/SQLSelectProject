# Production Environment Outputs

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "database_subnet_ids" {
  description = "Database subnet IDs"
  value       = module.vpc.database_subnet_ids
}

# EKS Outputs
output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_version" {
  description = "EKS cluster version"
  value       = module.eks.cluster_version
}

output "eks_oidc_provider_arn" {
  description = "EKS OIDC provider ARN"
  value       = module.eks.oidc_provider_arn
}

output "configure_kubectl" {
  description = "Configure kubectl command"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

# RDS Outputs
output "rds_primary_endpoint" {
  description = "RDS primary (writer) endpoint"
  value       = module.rds.primary_endpoint
  sensitive   = true
}

output "rds_replica_endpoints" {
  description = "RDS read replica endpoints"
  value       = module.rds.replica_endpoints
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.database_name
}

# Redis Outputs
output "redis_primary_endpoint" {
  description = "Redis primary endpoint (writes)"
  value       = module.elasticache.primary_endpoint_address
  sensitive   = true
}

output "redis_reader_endpoint" {
  description = "Redis reader endpoint (reads)"
  value       = module.elasticache.reader_endpoint_address
  sensitive   = true
}

# Connection Strings (for application configuration)
output "postgres_write_connection" {
  description = "PostgreSQL write connection string"
  value       = "postgresql://${var.db_master_username}:${var.db_master_password}@${module.rds.primary_address}:5432/${module.rds.database_name}?sslmode=require"
  sensitive   = true
}

output "postgres_read_connections" {
  description = "PostgreSQL read replica connection strings"
  value       = [for addr in module.rds.replica_addresses : "postgresql://${var.db_master_username}:${var.db_master_password}@${addr}:5432/${module.rds.database_name}?sslmode=require"]
  sensitive   = true
}

output "redis_write_connection" {
  description = "Redis write connection string"
  value       = "rediss://:${var.redis_auth_token}@${module.elasticache.primary_endpoint_address}:6379/0?ssl_cert_reqs=required"
  sensitive   = true
}

output "redis_read_connection" {
  description = "Redis read connection string"
  value       = "rediss://:${var.redis_auth_token}@${module.elasticache.reader_endpoint_address}:6379/0?ssl_cert_reqs=required"
  sensitive   = true
}

# Deployment Information
output "deployment_info" {
  description = "Production deployment information"
  value = {
    region              = var.aws_region
    environment         = var.environment
    eks_cluster         = module.eks.cluster_name
    eks_version         = module.eks.cluster_version
    rds_instance_class  = var.rds_instance_class
    redis_node_type     = var.redis_node_type
    high_availability   = "enabled"
    read_replicas       = "2"
    encryption          = "enabled"
    multi_az            = "enabled"
  }
}
