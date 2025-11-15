# RDS Module Variables

variable "identifier" {
  description = "RDS instance identifier"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block for security group"
  type        = string
}

variable "database_subnet_ids" {
  description = "Database subnet IDs"
  type        = list(string)
}

# Engine Configuration
variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.1"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.xlarge"
}

variable "parameter_group_family" {
  description = "PostgreSQL parameter group family"
  type        = string
  default     = "postgres16"
}

# Storage Configuration
variable "allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum allocated storage for autoscaling"
  type        = number
  default     = 1000
}

variable "iops" {
  description = "Provisioned IOPS for gp3 storage"
  type        = number
  default     = 3000
}

variable "storage_throughput" {
  description = "Storage throughput in MB/s for gp3"
  type        = number
  default     = 125
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
  default     = ""
}

# Database Configuration
variable "database_name" {
  description = "Initial database name"
  type        = string
}

variable "master_username" {
  description = "Master username"
  type        = string
  sensitive   = true
}

variable "master_password" {
  description = "Master password"
  type        = string
  sensitive   = true
}

# High Availability
variable "multi_az" {
  description = "Enable Multi-AZ for primary"
  type        = bool
  default     = true
}

# Read Replicas
variable "create_read_replicas" {
  description = "Create read replicas"
  type        = bool
  default     = true
}

variable "read_replica_count" {
  description = "Number of read replicas"
  type        = number
  default     = 2
}

variable "replica_instance_class" {
  description = "Instance class for replicas (defaults to primary instance class if empty)"
  type        = string
  default     = ""
}

variable "replica_multi_az" {
  description = "Enable Multi-AZ for replicas"
  type        = bool
  default     = false
}

# Backup Configuration
variable "backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

variable "backup_window" {
  description = "Preferred backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on deletion"
  type        = bool
  default     = false
}

# Monitoring
variable "enabled_cloudwatch_logs_exports" {
  description = "CloudWatch log types to export"
  type        = list(string)
  default     = ["postgresql", "upgrade"]
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0, 1, 5, 10, 15, 30, 60)"
  type        = number
  default     = 60
}

variable "performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "Performance Insights retention period in days"
  type        = number
  default     = 7
}

# CloudWatch Alarms
variable "create_cloudwatch_alarms" {
  description = "Create CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications"
  type        = string
  default     = ""
}

variable "cpu_alarm_threshold" {
  description = "CPU utilization alarm threshold percentage"
  type        = number
  default     = 80
}

variable "connections_alarm_threshold" {
  description = "Database connections alarm threshold"
  type        = number
  default     = 80
}

variable "storage_alarm_threshold_bytes" {
  description = "Free storage space alarm threshold in bytes"
  type        = number
  default     = 10737418240  # 10 GB
}

# Other Settings
variable "auto_minor_version_upgrade" {
  description = "Enable auto minor version upgrades"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

# Performance Tuning Parameters
variable "max_connections" {
  description = "Maximum number of database connections"
  type        = string
  default     = "200"
}

variable "shared_buffers" {
  description = "Shared buffers in KB"
  type        = string
  default     = "{DBInstanceClassMemory/4096}"
}

variable "effective_cache_size" {
  description = "Effective cache size in KB"
  type        = string
  default     = "{DBInstanceClassMemory*3/4096}"
}

variable "maintenance_work_mem" {
  description = "Maintenance work memory in KB"
  type        = string
  default     = "{DBInstanceClassMemory/16384}"
}

variable "work_mem" {
  description = "Work memory in KB"
  type        = string
  default     = "4096"
}

variable "log_min_duration_statement" {
  description = "Log statements slower than this in ms (-1 disables)"
  type        = string
  default     = "1000"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
