# ============================================
# Modified App Service Module Variables
# Now supports existing resource group
# ============================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "Region configuration object"
  type = object({
    location   = string
    short_name = string
  })
}

# New variables for existing resource group
variable "existing_resource_group_name" {
  description = "Name of existing resource group to use"
  type        = string
}

variable "existing_resource_group_location" {
  description = "Location of existing resource group"
  type        = string
}

variable "app_service_plan_sku" {
  description = "SKU for the App Service Plan"
  type        = string
}

variable "app_service_plan_tier" {
  description = "Tier for the App Service Plan"
  type        = string
}

# variable "min_instances" {
#   description = "Minimum number of instances"
#   type        = number
# }

# variable "max_instances" {
#   description = "Maximum number of instances"
#   type        = number
# }

variable "app_settings" {
  description = "Application settings"
  type        = map(string)
  default     = {}
}

variable "connection_strings" {
  description = "Connection strings for the app service"
  type = list(object({
    name  = string
    type  = string
    value = string
  }))
  default = []
}

variable "application_insights_id" {
  description = "ID of shared Application Insights resource"
  type        = string
  default     = null
}

variable "application_insights_instrumentation_key" {
  description = "Shared Application Insights instrumentation key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "application_insights_connection_string" {
  description = "Shared Application Insights connection string"
  type        = string
  default     = ""
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
