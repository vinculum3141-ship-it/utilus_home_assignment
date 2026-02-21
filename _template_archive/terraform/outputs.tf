# Terraform outputs

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "region" {
  description = "Deployment region"
  value       = var.region
}

# Storage outputs
output "storage_info" {
  description = "Storage configuration information"
  value = {
    tier           = var.storage_tier
    retention_days = var.storage_retention_days
  }
}

# Database outputs
# output "database_endpoint" {
#   description = "Database connection endpoint"
#   value       = aws_db_instance.main.endpoint
#   sensitive   = true
# }

# Application outputs
# output "api_endpoint" {
#   description = "API endpoint URL"
#   value       = aws_lb.main.dns_name
# }

# Monitoring outputs
# output "monitoring_dashboard_url" {
#   description = "Monitoring dashboard URL"
#   value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.region}"
# }

# Batch orchestration outputs
output "batch_job_hooks" {
  description = "Placeholder for batch job orchestration endpoints"
  value = {
    # Examples of what could be exposed:
    # job_scheduler_url = "https://airflow.example.com"
    # step_function_arn = aws_sfn_state_machine.batch_pipeline.arn
    # databricks_job_id = databricks_job.batch_pipeline.id
    # cloud_scheduler_id = google_cloud_scheduler_job.batch_pipeline.id
    info = "Configure actual batch orchestration resources here"
  }
}

output "batch_job_trigger_info" {
  description = "Information for triggering batch jobs"
  value = {
    cli_command    = "energy-platform run-batch"
    api_endpoint   = "/batch/trigger"
    schedule_info  = "Configure cron schedule in orchestration service"
    retry_policy   = "Configure retry logic in orchestration service"
  }
}

output "deployment_timestamp" {
  description = "Timestamp of deployment"
  value       = timestamp()
}
