# ElastiCache Module Variables

variable "cluster_name" {
  description = "ElastiCache cluster name"
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

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

# Engine Configuration
variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r7g.large"
}

variable "parameter_group_family" {
  description = "Redis parameter group family"
  type        = string
  default     = "redis7"
}

# Cluster Mode Configuration
variable "cluster_mode_enabled" {
  description = "Enable Redis cluster mode (sharding)"
  type        = bool
  default     = false
}

variable "num_cache_nodes" {
  description = "Number of cache nodes (for non-cluster mode)"
  type        = number
  default     = 3
}

variable "num_node_groups" {
  description = "Number of node groups/shards (for cluster mode)"
  type        = number
  default     = 3
}

variable "replicas_per_node_group" {
  description = "Number of replica nodes per shard (for cluster mode)"
  type        = number
  default     = 2
}

# High Availability
variable "automatic_failover_enabled" {
  description = "Enable automatic failover"
  type        = bool
  default     = true
}

variable "multi_az_enabled" {
  description = "Enable Multi-AZ"
  type        = bool
  default     = true
}

# Security
variable "at_rest_encryption_enabled" {
  description = "Enable encryption at rest"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Enable encryption in transit"
  type        = bool
  default     = true
}

variable "auth_token_enabled" {
  description = "Enable Redis AUTH"
  type        = bool
  default     = true
}

variable "auth_token" {
  description = "AUTH token for Redis (min 16 chars, max 128 chars)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption at rest"
  type        = string
  default     = ""
}

# Backup and Maintenance
variable "snapshot_retention_limit" {
  description = "Number of days to retain snapshots (0 disables)"
  type        = number
  default     = 7
}

variable "snapshot_window" {
  description = "Daily snapshot time window"
  type        = string
  default     = "03:00-05:00"
}

variable "maintenance_window" {
  description = "Weekly maintenance window"
  type        = string
  default     = "sun:05:00-sun:07:00"
}

variable "final_snapshot_identifier" {
  description = "Final snapshot name on deletion"
  type        = string
  default     = ""
}

variable "notification_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
  default     = ""
}

# Performance Parameters
variable "maxmemory_policy" {
  description = "Redis maxmemory eviction policy"
  type        = string
  default     = "allkeys-lru"
  validation {
    condition     = contains(["volatile-lru", "allkeys-lru", "volatile-lfu", "allkeys-lfu", "volatile-random", "allkeys-random", "volatile-ttl", "noeviction"], var.maxmemory_policy)
    error_message = "Invalid maxmemory policy"
  }
}

variable "timeout" {
  description = "Client idle timeout in seconds"
  type        = string
  default     = "300"
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
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
  default     = 75
}

variable "memory_alarm_threshold" {
  description = "Memory utilization alarm threshold percentage"
  type        = number
  default     = 90
}

variable "evictions_alarm_threshold" {
  description = "Number of evictions before alarm"
  type        = number
  default     = 1000
}

# Other Settings
variable "auto_minor_version_upgrade" {
  description = "Enable auto minor version upgrades"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
