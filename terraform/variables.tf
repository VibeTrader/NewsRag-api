# ============================================
# Variables for NewsRaag Multi-Region Fresh Deployment
# All resources created from scratch - New Azure Account
# ============================================

# Environment Configuration
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}
variable "existing_resource_group_name" {
  description = "Name of the existing resource group to deploy into"
  type        = string
  default     = "vibetrader-RAG-rg"
  
}

# App Service Configuration - Basic tier for cost-effective start
variable "app_service_plan_sku" {
  description = "SKU for App Service Plans (Basic for now, will scale later)"
  type        = string
  default     = "B1" # Basic tier - cheapest option for testing
}

variable "app_service_plan_tier" {
  description = "Tier for App Service Plans"
  type        = string
  default     = "Basic"
}

# Scaling Configuration (Basic tier has limited scaling)
# variable "min_instances" {
#   description = "Minimum number of instances for auto-scaling"
#   type        = number
#   default     = 1 # Basic tier minimum
# }

# variable "max_instances" {
#   description = "Maximum number of instances for auto-scaling"
#   type        = number
#   default     = 3 # Basic tier maximum
# }

# Application Settings (passed to all App Services)
variable "app_settings" {
  description = "Application settings for App Services"
  type        = map(string)
  default = {
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    WEBSITES_PORT                       = "8000"
    SCM_DO_BUILD_DURING_DEPLOYMENT      = "true"
    ENABLE_ORYX_BUILD                   = "true"
    
    # Python specific
    PYTHON_VERSION = "3.12"
    
    # Application specific
    ENVIRONMENT = "production"
    
    # Health check
    HEALTH_CHECK_ENABLED = "true"
    
    # FastAPI specific
    API_HOST = "0.0.0.0"
    API_PORT = "8000"
    
    # You can add your application-specific settings here:
    # OPENAI_BASE_URL = "https://your-azure-endpoint.openai.azure.com"
    # AZURE_OPENAI_API_VERSION = "2024-02-01"
    # AZURE_OPENAI_DEPLOYMENT = "your-deployment-name"
    # AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "your-embedding-deployment"
    # AZURE_OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
    # EMBEDDING_DIMENSION = "3072"
    # QDRANT_URL = "your-qdrant-url"
    # QDRANT_COLLECTION_NAME = "news_articles"
    # VECTOR_BACKEND = "qdrant"
    # LLM_CLEANING_ENABLED = "true"
    # LLM_TOKEN_LIMIT_PER_REQUEST = "4000"
  }
  sensitive = false # Set to true if you add sensitive values
}

# Health Check Configuration
variable "health_check_path" {
  description = "Health check endpoint path"
  type        = string
  default     = "/health" # Your FastAPI app has this endpoint
}

# Monitoring and Alerting
variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = "haripriyaveluchamy@aity.dev" # Updated with your actual email
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts (optional)"
  type        = string
  default     = "https://hooks.slack.com/services/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"
  sensitive   = true
}

# Custom Domain (optional for future use)
variable "custom_domain" {
  description = "Custom domain name (optional for future use)"
  type        = string
  default     = ""
}

# SSL Certificate (optional for future use)  
variable "ssl_certificate_name" {
  description = "Name of SSL certificate in Key Vault (optional for future use)"
  type        = string
  default     = ""
}

# Log Analytics Workspace Configuration
variable "log_retention_days" {
  description = "Log retention in days for Log Analytics workspace"
  type        = number
  default     = 30 # Standard retention for cost optimization
}

# Monitoring Configuration
variable "enable_plan_metrics" {
  description = "Enable App Service Plan level metrics (CPU/Memory percentage). Only works with Standard+ tiers. Set to true when upgrading from Basic."
  type        = bool
  default     = false # Set to true when you upgrade to Standard/Premium
}

# Azure Front Door Configuration
variable "frontdoor_sku" {
  description = "SKU for Azure Front Door (Standard_AzureFrontDoor or Premium_AzureFrontDoor)"
  type        = string
  default     = "Standard_AzureFrontDoor" # ~$10/mo, use Premium for WAF (~$35/mo)
  
  validation {
    condition     = contains(["Standard_AzureFrontDoor", "Premium_AzureFrontDoor"], var.frontdoor_sku)
    error_message = "SKU must be either Standard_AzureFrontDoor or Premium_AzureFrontDoor"
  }
}
