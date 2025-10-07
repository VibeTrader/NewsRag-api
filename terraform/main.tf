# -----------------------------------------------------
# Main Terraform configuration for multi-region NewsRAG API
# -----------------------------------------------------

# Use existing resource group
data "azurerm_resource_group" "main" {
  name = var.existing_resource_group_name
}

# Shared Log Analytics workspace
resource "azurerm_log_analytics_workspace" "shared" {
  name                = "logs-newsraag-shared-${var.environment}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = "East US"  # Central location for logs
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  
  tags = {
    Environment = var.environment
    Application = "NewsRAG API"
    Terraform   = "true"
  }
}

# Shared Application Insights instance
resource "azurerm_application_insights" "shared" {
  name                = "insights-newsraag-shared-${var.environment}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = "East US"  # Central location for insights
  workspace_id        = azurerm_log_analytics_workspace.shared.id
  application_type    = "web"
  
  tags = {
    Environment = var.environment
    Application = "NewsRAG API"
    Terraform   = "true"
  }
}

# Multi-region app services with for_each
module "app_services" {
  for_each = {
    us      = { location = "East US", location_code = "us" }
    europe  = { location = "North Europe", location_code = "eu" }
    india   = { location = "Central India", location_code = "in" }
  }
  
  source = "./modules/app-service"
  
  # Common parameters
  name                  = "newsraag-${each.value.location_code}"
  location              = each.value.location
  environment           = var.environment
  resource_group_name   = data.azurerm_resource_group.main.name
  app_insights_key      = azurerm_application_insights.shared.instrumentation_key
  app_insights_conn_str = azurerm_application_insights.shared.connection_string
  
  # App service plan config
  app_service_plan_sku  = var.app_service_plan_sku
  app_service_plan_tier = var.app_service_plan_tier
  
  # Autoscaling settings
  min_instances         = var.min_instances
  max_instances         = var.max_instances
  
  # App settings from variables
  app_settings          = var.app_settings
  health_check_path     = var.health_check_path
  
  # Tags
  tags = {
    Environment = var.environment
    Region      = each.key
    Application = "NewsRAG API"
    Terraform   = "true"
  }
}

# Traffic Manager for global routing
module "traffic_manager" {
  source = "./modules/traffic-manager"
  
  name                = "newsraag"
  environment         = var.environment
  resource_group_name = data.azurerm_resource_group.main.name
  
  # App service endpoints
  endpoints = {
    us = {
      name         = "endpoint-us-${var.environment}"
      target_id    = module.app_services["us"].app_service_id
      priority     = 1
      weight       = 100
      location     = "East US"
    },
    europe = {
      name         = "endpoint-eu-${var.environment}"
      target_id    = module.app_services["europe"].app_service_id
      priority     = 2
      weight       = 100
      location     = "North Europe"
    },
    india = {
      name         = "endpoint-in-${var.environment}"
      target_id    = module.app_services["india"].app_service_id
      priority     = 3
      weight       = 100
      location     = "Central India"
    }
  }
  
  # Tags
  tags = {
    Environment = var.environment
    Application = "NewsRAG API"
    Terraform   = "true"
  }
}

# Monitoring alerts
module "monitoring" {
  source = "./modules/monitoring"
  
  name                     = "newsraag"
  environment              = var.environment
  resource_group_name      = data.azurerm_resource_group.main.name
  app_insights_id          = azurerm_application_insights.shared.id
  alert_email              = var.alert_email
  slack_webhook_url        = var.slack_webhook_url
}

