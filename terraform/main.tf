# -----------------------------------------------------
# Main Terraform configuration for multiregion NewsRAG API
# -----------------------------------------------------

# Local values for consistent naming
locals {
  project_name = "newsraag"
  environment  = var.environment
  
  # Define all regions
  regions = {
    us      = { location = "East US", short_name = "us" }
    europe  = { location = "North Europe", short_name = "eu" }
    india   = { location = "Central India", short_name = "in" }
  }
  
  # Common tags
  common_tags = {
    Environment = var.environment
    Application = "NewsRAG API"
    Terraform   = "true"
  }
}

# Use existing resource group
data "azurerm_resource_group" "existing" {
  name = var.existing_resource_group_name
}

# Shared Log Analytics Workspace for all regions
resource "azurerm_log_analytics_workspace" "shared" {
  name                = "logs-${local.project_name}-shared-${local.environment}"
  location            = data.azurerm_resource_group.existing.location
  resource_group_name = data.azurerm_resource_group.existing.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  
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
  # min_instances         = var.min_instances
  # max_instances         = var.max_instances
  
  # Use shared Application Insights
  application_insights_id                   = azurerm_application_insights.shared.id
  application_insights_instrumentation_key = azurerm_application_insights.shared.instrumentation_key
  application_insights_connection_string   = azurerm_application_insights.shared.connection_string
  
  # Application configuration
  app_settings = var.app_settings
  
  common_tags = local.common_tags
}

# Azure Front Door for global CDN and load balancing
module "front_door" {
  source = "./modules/front-door"
  
  project_name        = local.project_name
  environment         = local.environment
  resource_group_name = data.azurerm_resource_group.existing.name
  
  # SKU: Standard_AzureFrontDoor (~$10/mo) or Premium_AzureFrontDoor (~$35/mo with WAF)
  frontdoor_sku = var.frontdoor_sku
  
  # Pass all app service hostnames
  us_app_service_hostname    = module.app_services["us"].app_service_hostname
  eu_app_service_hostname    = module.app_services["europe"].app_service_hostname
  india_app_service_hostname = module.app_services["india"].app_service_hostname
  
  # Health check configuration
  health_check_path = var.health_check_path
  
  # Optional custom domain (leave empty if not using)
  custom_domain = var.custom_domain
  
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
  
  # Build app_service_plans map for Standard+ tier monitoring
  app_service_plans = {
    for region_key, region_config in local.regions : region_key => {
      id   = module.app_services[region_key].app_service_plan_id
      name = module.app_services[region_key].app_service_plan_name
    }
  }
  
  # Enable plan metrics when using Standard+ tiers (set via variable)
  enable_plan_metrics = var.enable_plan_metrics
  
  # Alert configuration
  alert_email       = var.alert_email
  slack_webhook_url = var.slack_webhook_url
  
  common_tags = local.common_tags
}