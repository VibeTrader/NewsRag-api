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
  location            = data.azurerm_resource_group.main.location
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
  location            = data.azurerm_resource_group.main.location
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
    us      = { location = "East US", short_name = "us" }
    europe  = { location = "North Europe", short_name = "eu" }
    india   = { location = "Central India", short_name = "in" }
  }
  
  source = "./modules/app-service"
  
  # Required parameters matching module variables
  project_name                              = "newsraag"
  environment                               = var.environment
  existing_resource_group_name              = data.azurerm_resource_group.main.name
  existing_resource_group_location          = data.azurerm_resource_group.main.location
  
  # Region object as expected by module
  region = {
    location   = each.value.location
    short_name = each.value.short_name
  }
  
  # App service plan config
  app_service_plan_sku  = var.app_service_plan_sku
  app_service_plan_tier = var.app_service_plan_tier
  
  # Autoscaling settings
  min_instances = var.min_instances
  max_instances = var.max_instances
  
  # App settings
  app_settings = var.app_settings
  
  # Application Insights integration
  application_insights_id                   = azurerm_application_insights.shared.id
  application_insights_instrumentation_key = azurerm_application_insights.shared.instrumentation_key
  application_insights_connection_string   = azurerm_application_insights.shared.connection_string
  
  # Common tags
  common_tags = {
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