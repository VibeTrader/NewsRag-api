# ============================================
# Monitoring Module Variables
# Compatible with Basic, Standard, and Premium tiers
# ============================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "application_insights_id" {
  description = "ID of Application Insights resource"
  type        = string
}

variable "app_services" {
  description = "Map of app services to monitor"
  type = map(object({
    id     = string
    name   = string
    region = string
  }))
}

variable "app_service_plans" {
  description = "Map of app service plans to monitor (Standard+ tiers only)"
  type = map(object({
    id   = string
    name = string
  }))
  default = {}
}

variable "enable_plan_metrics" {
  description = "Enable App Service Plan level metrics (only works with Standard+ tiers)"
  type        = bool
  default     = false # Set to true when upgrading to Standard+
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

# Customizable thresholds
variable "response_time_threshold" {
  description = "Response time threshold in seconds"
  type        = number
  default     = 5
}

variable "memory_threshold_bytes" {
  description = "Memory threshold in bytes"
  type        = number
  default     = 1610612736 # 1.5GB - adjust based on your tier
}

variable "request_spike_threshold" {
  description = "Request spike threshold per 10 minutes"
  type        = number
  default     = 1000
}

variable "error_5xx_threshold" {
  description = "5xx error threshold per 5 minutes"
  type        = number
  default     = 10
}

variable "error_4xx_threshold" {
  description = "4xx error threshold per 15 minutes"
  type        = number
  default     = 50
}