# -----------------------------------------------------
# Main Terraform configuration for multiregion NewsRAG AP
# -----------------------------------------------------

# Local values for consistent naming
locals {
  project_name = "newsrag-api"
  environment  = var.environment

  # Define all regions
  all_regions = {
    us      = { location = "East US", short_name = "us" }
    uk      = { location = "UK South", short_name = "uk" }
    # india   = { location = "Central India", short_name = "in" }
  }

  # Select regions based on environment
  # Prod: US and UK
  # Dev: US only (minimal cost)
  regions = var.environment == "prod" ? local.all_regions : {
    us     = local.all_regions.us
  }

  # Common tags
  common_tags = {
    Environment = var.environment
    Application = "NewsRAG API"
    Terraform   = "true"
  }
}

# ============================================
# Resource Group Logic
# ============================================

# Core Infrastructure RG (Networking, Env, Monitoring)
data "azurerm_resource_group" "core" {
  name = var.existing_resource_group_name
}

# Service RG (Where the App runs)
# If service_resource_group_name is provided, use it. Otherwise use core.
locals {
  service_rg_name = var.service_resource_group_name != "" ? var.service_resource_group_name : var.existing_resource_group_name
  
  # Tags Strategy
  # Base tags applied to all resources. Service tag is injected per resource.
  base_tags = {
    "created-by"   = var.created_by
    "created-date" = var.created_date
    "environment"  = var.environment
    "project"      = "newsrag-api"
    "Terraform"    = "true"
  }
}

data "azurerm_resource_group" "service" {
  name = local.service_rg_name
}

# Use existing resource group
data "azurerm_resource_group" "existing" {
  name = var.existing_resource_group_name
}

# Azure Container Registry (Shared for all images)
# Basic SKU is sufficient for < 10GB images
resource "azurerm_container_registry" "acr" {
  name                = "acr${replace(local.project_name, "-", "")}${var.environment}" # Must be globally unique, alphanumeric
  resource_group_name = data.azurerm_resource_group.core.name
  location            = data.azurerm_resource_group.core.location
  sku                 = "Basic"
  admin_enabled       = true # Enable admin user for easy CI/CD access

  tags = merge(local.base_tags, { service = "apiacrimage" })
}

# Shared Log Analytics Workspace (Required for Container Apps Environment)
resource "azurerm_log_analytics_workspace" "shared" {
  # count               = var.environment == "prod" ? 1 : 0 # Always need one for ACA Environment
  name                = "logs-${local.project_name}-shared-${local.environment}"
  location            = data.azurerm_resource_group.core.location
  resource_group_name = data.azurerm_resource_group.core.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  
  tags = merge(local.base_tags, { service = "logging" })
}

# Shared Application Insights (PROD ONLY)
resource "azurerm_application_insights" "shared" {
  count               = var.environment == "prod" ? 1 : 0
  name                = "insights-${local.project_name}-shared-${local.environment}"
  location            = data.azurerm_resource_group.core.location
  resource_group_name = data.azurerm_resource_group.core.name
  workspace_id        = azurerm_log_analytics_workspace.shared.id
  application_type    = "web"
  
  tags = merge(local.base_tags, { service = "logging" })
}

# ============================================
# Container App Environment (Shared / Core)
# ============================================
module "container_env" {
  source = "./modules/container-env"

  project_name               = local.project_name
  environment                = local.environment
  location                   = data.azurerm_resource_group.core.location
  resource_group_name        = data.azurerm_resource_group.core.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.shared.id
  
  tags = merge(local.base_tags, { service = "compute" })
}

# ============================================
# Container Apps (Microservices)
# ============================================
# Deploy Container Apps for all regions using for_each
module "container_apps" {
  source = "./modules/container-app"
  
  # Loop through all regions
  for_each = local.regions
  
  project_name        = local.project_name
  environment         = local.environment
  
  # Deploy to the Service Resource Group
  resource_group_name = data.azurerm_resource_group.service.name
  region              = each.value.location
  
  # Connect to the Shared Environment (in Core RG)
  container_app_environment_id = module.container_env.id

  container_image     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
  target_port         = 80
  
  # ... scaling config ...
  cpu           = var.cpu
  memory        = var.memory
  min_replicas  = var.min_replicas
  max_replicas  = var.max_replicas
  
  env_vars = merge(
    var.app_settings,
    {
      DEPLOYMENT_REGION = each.value.short_name
      AZURE_REGION      = each.value.location
      
      # Inject Secrets from Terraform Variables
      OPENAI_API_KEY = var.openai_api_key
      QDRANT_API_KEY = var.qdrant_api_key
      
      # Inject External Service Config from Terraform Variables
      AZURE_OPENAI_API_VERSION          = var.azure_openai_api_version
      AZURE_OPENAI_DEPLOYMENT           = var.azure_openai_deployment
      AZURE_OPENAI_EMBEDDING_DEPLOYMENT = var.azure_openai_embedding_deployment
      AZURE_OPENAI_EMBEDDING_MODEL      = var.azure_openai_embedding_model
      OPENAI_BASE_URL                   = var.openai_base_url
      QDRANT_URL                        = var.qdrant_url
      QDRANT_COLLECTION_NAME            = var.qdrant_collection_name
    },
    var.environment == "prod" ? {
      APPINSIGHTS_INSTRUMENTATIONKEY        = azurerm_application_insights.shared[0].instrumentation_key
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.shared[0].connection_string
    } : {}
  )
  
  health_check_path = var.health_check_path
  
  common_tags = merge(local.base_tags, { service = "api" })
}

# Azure Front Door for global CDN and load balancing (PROD ONLY)
module "front_door" {
  source = "./modules/front-door"
  count  = var.environment == "prod" ? 1 : 0
  
  project_name        = local.project_name
  environment         = local.environment
  resource_group_name = data.azurerm_resource_group.existing.name
  
  # SKU: Standard_AzureFrontDoor (~$10/mo) or Premium_AzureFrontDoor (~$35/mo with WAF)
  frontdoor_sku = var.frontdoor_sku
  
  # Pass all app service hostnames
  us_app_service_hostname    = module.container_apps["us"].container_app_fqdn
  eu_app_service_hostname    = module.container_apps["uk"].container_app_fqdn
  # india_app_service_hostname = try(module.container_apps["india"].container_app_fqdn, null)
  
  # Health check configuration
  health_check_path = var.health_check_path
  
  # Optional custom domain (leave empty if not using)
  custom_domain = var.custom_domain
  
  common_tags = merge(local.base_tags, { service = "cdn" })

}

# Enhanced monitoring for multi-region setup (PROD ONLY)
# module "monitoring" {
#   source = "./modules/monitoring"
#   count  = var.environment == "prod" ? 1 : 0  # Only create monitoring in prod
#   
#   project_name         = local.project_name
#   environment          = local.environment
#   resource_group_name  = data.azurerm_resource_group.existing.name
#   location             = data.azurerm_resource_group.existing.location
#   
#   # Use shared Application Insights
#   application_insights_id = azurerm_application_insights.shared[0].id
#   
#   # API hostname for availability tests (Front Door)
#   api_hostname = module.front_door[0].frontdoor_endpoint_hostname
#   
#   # Use existing action group from Vibetrader_CoreProduction
#   use_existing_action_group  = var.use_existing_action_group
#   existing_action_group_name = var.existing_action_group_name
#   existing_action_group_rg   = var.existing_action_group_rg
#   
#   # Alert configuration (only used if not using existing action group)
#   alert_email       = var.alert_email
#   slack_webhook_url = var.slack_webhook_url
#   
#   common_tags = local.common_tags
# }
