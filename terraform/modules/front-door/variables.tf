# ============================================
# Variables for Azure Front Door Module
# ============================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "frontdoor_sku" {
  description = "SKU for Azure Front Door (Standard_AzureFrontDoor or Premium_AzureFrontDoor)"
  type        = string
  default     = "Standard_AzureFrontDoor"
  
  validation {
    condition     = contains(["Standard_AzureFrontDoor", "Premium_AzureFrontDoor"], var.frontdoor_sku)
    error_message = "SKU must be either Standard_AzureFrontDoor or Premium_AzureFrontDoor"
  }
}

variable "us_app_service_hostname" {
  description = "Hostname of US App Service"
  type        = string
}

variable "eu_app_service_hostname" {
  description = "Hostname of EU App Service"
  type        = string
}

variable "india_app_service_hostname" {
  description = "Hostname of India App Service"
  type        = string
  default     = ""
}

variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health"
}

variable "custom_domain" {
  description = "Custom domain name (optional)"
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
