# RDS Module Outputs

output "primary_endpoint" {
  description = "Primary RDS instance endpoint"
  value       = aws_db_instance.primary.endpoint
}

output "primary_address" {
  description = "Primary RDS instance address"
  value       = aws_db_instance.primary.address
}

output "primary_arn" {
  description = "Primary RDS instance ARN"
  value       = aws_db_instance.primary.arn
}

output "primary_id" {
  description = "Primary RDS instance ID"
  value       = aws_db_instance.primary.id
}

output "replica_endpoints" {
  description = "Read replica endpoints"
  value       = var.create_read_replicas ? aws_db_instance.replica[*].endpoint : []
}

output "replica_addresses" {
  description = "Read replica addresses"
  value       = var.create_read_replicas ? aws_db_instance.replica[*].address : []
}

output "replica_ids" {
  description = "Read replica IDs"
  value       = var.create_read_replicas ? aws_db_instance.replica[*].id : []
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.primary.db_name
}

output "master_username" {
  description = "Master username"
  value       = aws_db_instance.primary.username
  sensitive   = true
}

output "port" {
  description = "Database port"
  value       = aws_db_instance.primary.port
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.rds.id
}

output "db_subnet_group_name" {
  description = "DB subnet group name"
  value       = aws_db_subnet_group.main.name
}

output "parameter_group_name" {
  description = "DB parameter group name"
  value       = aws_db_parameter_group.main.name
}

output "monitoring_role_arn" {
  description = "Enhanced monitoring IAM role ARN"
  value       = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null
}
