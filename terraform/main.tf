# ============================================
# Refactored Terraform Configuration for NewsRaag Multi-Region Deployment  
# Uses existing vibetrader-RAG-rg resource group with for_each loops
# ============================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Data sources
data "azurerm_client_config" "current" {}

# Use existing resource group instead of creating new one
data "azurerm_resource_group" "existing" {
  name = "vibetrader-RAG-rg"
}

# Local values for consistent naming
locals {
  project_name = "newsraag"
  environment  = var.environment
  
  # Define all regions in one place
  regions = {
    us = {
      location      = "East US"
      short_name    = "us"
    }
    europe = {
      location      = "West Europe"
      short_name    = "eu"
    }
    india = {
      location      = "South India"
      short_name    = "in"
    }
  }
  
  # Tags applied to all resources
  common_tags = {
    Environment = var.environment
    Project     = local.project_name
    ManagedBy   = "Terraform"
    Owner       = "NewsRaag-Team"
    DeployedAt  = timestamp()
  }
}

# Shared Log Analytics Workspace for all regions
resource "azurerm_log_analytics_workspace" "shared" {
  name                = "logs-${local.project_name}-shared-${local.environment}"
  location            = data.azurerm_resource_group.existing.location
  resource_group_name = data.azurerm_resource_group.existing.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  
  tags = local.common_tags
}

# Shared Application Insights for all 3 regions
resource "azurerm_application_insights" "shared" {
  name                = "insights-${local.project_name}-shared-${local.environment}"
  location            = data.azurerm_resource_group.existing.location
  resource_group_name = data.azurerm_resource_group.existing.name
  workspace_id        = azurerm_log_analytics_workspace.shared.id
  application_type    = "web"
  
  tags = local.common_tags
}

# Deploy App Services for all regions using for_each
module "app_services" {
  source = "./modules/app-service"
  
  # Loop through all regions
  for_each = local.regions
  
  project_name     = local.project_name
  environment      = local.environment
  region           = each.value  # Pass the region object (location, short_name)
  
  # Use existing resource group
  existing_resource_group_name     = data.azurerm_resource_group.existing.name
  existing_resource_group_location = data.azurerm_resource_group.existing.location
  
  # App Service configuration - Basic tier
  app_service_plan_sku  = var.app_service_plan_sku
  app_service_plan_tier = var.app_service_plan_tier
  min_instances         = var.min_instances
  max_instances         = var.max_instances
  
  # Use shared Application Insights
  application_insights_id                = azurerm_application_insights.shared.id
  application_insights_instrumentation_key = azurerm_application_insights.shared.instrumentation_key
  application_insights_connection_string = azurerm_application_insights.shared.connection_string
  
  # Application configuration
  app_settings = var.app_settings
  
  common_tags = local.common_tags
}

# Traffic Manager for global load balancing
module "traffic_manager" {
  source = "./modules/traffic-manager"
  
  project_name         = local.project_name
  environment          = local.environment
  resource_group_name  = data.azurerm_resource_group.existing.name
  
  # Pass all app service endpoints dynamically
  existing_app_service_id   = module.app_services["us"].app_service_id
  existing_app_service_name = module.app_services["us"].app_service_name
  
  europe_app_service_id   = module.app_services["europe"].app_service_id
  europe_app_service_name = module.app_services["europe"].app_service_name
  
  india_app_service_id   = module.app_services["india"].app_service_id
  india_app_service_name = module.app_services["india"].app_service_name
  
  # Health check configuration
  health_check_path = var.health_check_path
  
  # Use shared Application Insights for availability tests
  application_insights_id = azurerm_application_insights.shared.id
  
  common_tags = local.common_tags
}

# Enhanced monitoring for multi-region setup
module "monitoring" {
  source = "./modules/monitoring"
  
  project_name         = local.project_name
  environment          = local.environment
  resource_group_name  = data.azurerm_resource_group.existing.name
  
  # Use shared Application Insights
  application_insights_id = azurerm_application_insights.shared.id
  
  # Build app_services map dynamically from for_each results
  app_services = {
    for region_key, region_config in local.regions : region_key => {
      id     = module.app_services[region_key].app_service_id
      name   = module.app_services[region_key].app_service_name
      region = region_key
    }
  }
  
  # Alert configuration
  alert_email       = var.alert_email
  slack_webhook_url = var.slack_webhook_url
  
  common_tags = local.common_tags
}
