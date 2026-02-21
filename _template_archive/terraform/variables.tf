# Terraform variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "energy-platform"
}

variable "region" {
  description = "Cloud provider region"
  type        = string
  default     = "us-west-2"
}

# Storage configuration
variable "storage_tier" {
  description = "Storage tier for data lakes"
  type        = string
  default     = "standard"
}

variable "storage_retention_days" {
  description = "Data retention period in days"
  type        = number
  default     = 90
}

# Database configuration
variable "database_instance_class" {
  description = "Database instance class/size"
  type        = string
  default     = "db.t3.small"
}

variable "database_allocated_storage" {
  description = "Database allocated storage in GB"
  type        = number
  default     = 20
}

# Compute configuration
variable "container_cpu" {
  description = "CPU units for container (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "container_memory" {
  description = "Memory for container in MB"
  type        = number
  default     = 2048
}

# Databricks configuration (if using)
variable "databricks_workspace_sku" {
  description = "Databricks workspace SKU"
  type        = string
  default     = "standard"
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Tags
variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "energy-platform"
    ManagedBy   = "terraform"
    Environment = "dev"
  }
}
