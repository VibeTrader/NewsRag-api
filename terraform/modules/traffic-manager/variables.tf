# ============================================
# Traffic Manager Module Variables
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
  description = "Name of the resource group for Traffic Manager"
  type        = string
}

variable "health_check_path" {
  description = "Path for health checks"
  type        = string
  default     = "/health"
}

# US App Service (existing)
variable "existing_app_service_id" {
  description = "Resource ID of existing US App Service"
  type        = string
}

variable "existing_app_service_name" {
  description = "Name of existing US App Service"
  type        = string
}

# Europe App Service
variable "europe_app_service_id" {
  description = "Resource ID of Europe App Service"
  type        = string
}

variable "europe_app_service_name" {
  description = "Name of Europe App Service"
  type        = string
}

# India App Service
variable "india_app_service_id" {
  description = "Resource ID of India App Service"
  type        = string
}

variable "india_app_service_name" {
  description = "Name of India App Service"
  type        = string
}

# Monitoring
variable "application_insights_id" {
  description = "ID of Application Insights resource"
  type        = string
  default     = null
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
