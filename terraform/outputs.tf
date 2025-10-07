# ============================================
# Refactored Outputs for NewsRag Multi-Region Deployment
# Uses for_each loops for cleaner code
# ============================================

# Existing Resource Group
output "existing_resource_group_name" {
  description = "Name of the existing resource group being used"
  value       = data.azurerm_resource_group.existing.name
}

output "existing_resource_group_location" {
  description = "Location of the existing resource group"
  value       = data.azurerm_resource_group.existing.location
}

# Shared Resources
output "shared_log_analytics_workspace_name" {
  description = "Name of the shared Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.shared.name
}

output "shared_application_insights_name" {
  description = "Name of the shared Application Insights resource"
  value       = azurerm_application_insights.shared.name
}

output "shared_application_insights_instrumentation_key" {
  description = "Shared Application Insights instrumentation key"
  value       = azurerm_application_insights.shared.instrumentation_key
  sensitive   = true
}

output "shared_application_insights_connection_string" {
  description = "Shared Application Insights connection string"
  value       = azurerm_application_insights.shared.connection_string
  sensitive   = true
}

# Traffic Manager
output "traffic_manager_fqdn" {
  description = "FQDN of the Traffic Manager endpoint - Your main global URL"
  value       = module.traffic_manager.fqdn
}

output "traffic_manager_url" {
  description = "Complete URL of the Traffic Manager endpoint"
  value       = "https://${module.traffic_manager.fqdn}"
}

# Dynamic outputs for all regions using for_each
output "app_services" {
  description = "Details of all deployed app services by region"
  value = {
    for region_key, region_config in local.regions : region_key => {
      app_service_plan_name = module.app_services[region_key].app_service_plan_name
      app_service_name      = module.app_services[region_key].app_service_name
      app_service_url       = module.app_services[region_key].app_service_url
      location              = region_config.location
      short_name            = region_config.short_name
    }
  }
}

# Individual region outputs for backward compatibility
output "us_app_service_name" {
  description = "Name of US App Service"
  value       = module.app_services["us"].app_service_name
}

output "us_app_service_url" {
  description = "URL of US App Service"
  value       = module.app_services["us"].app_service_url
}

output "europe_app_service_name" {
  description = "Name of Europe App Service"
  value       = module.app_services["europe"].app_service_name
}

output "europe_app_service_url" {
  description = "URL of Europe App Service"
  value       = module.app_services["europe"].app_service_url
}

output "india_app_service_name" {
  description = "Name of India App Service"
  value       = module.app_services["india"].app_service_name
}

output "india_app_service_url" {
  description = "URL of India App Service"
  value       = module.app_services["india"].app_service_url
}

# Monitoring
output "action_group_name" {
  description = "Name of the action group for alerts"
  value       = module.monitoring.action_group_name
}

output "monitoring_summary" {
  description = "Summary of monitoring setup"
  value       = module.monitoring.monitoring_summary
  sensitive   = true
}

# Resource Summary (Dynamic)
output "resources_created" {
  description = "Summary of all resources created"
  value = {
    shared_resources = {
      log_analytics_workspace = azurerm_log_analytics_workspace.shared.name
      application_insights     = azurerm_application_insights.shared.name
      traffic_manager         = module.traffic_manager.profile_name
    }
    
    # Dynamic region resources
    regions = {
      for region_key, region_config in local.regions : region_key => {
        app_service_plan = module.app_services[region_key].app_service_plan_name
        web_app          = module.app_services[region_key].app_service_name
        location         = region_config.location
      }
    }
  }
}

# Complete Deployment Summary (Dynamic)
output "deployment_summary" {
  description = "Complete summary of your multi-region deployment using existing RG"
  value = {
    environment               = var.environment
    existing_resource_group   = data.azurerm_resource_group.existing.name
    traffic_manager_url       = "https://${module.traffic_manager.fqdn}"
    shared_application_insights = azurerm_application_insights.shared.name
    
    # Dynamic regions deployed
    regions_deployed = {
      for region_key, region_config in local.regions : region_key => {
        app_service_plan = module.app_services[region_key].app_service_plan_name
        web_app         = module.app_services[region_key].app_service_name
        url             = module.app_services[region_key].app_service_url
        location        = region_config.location
      }
    }
    
    app_service_tier     = var.app_service_plan_sku
    monitoring_enabled   = true
    alerts_configured    = true
    health_checks_enabled = true
  }
}

# Quick Access URLs (Dynamic)
output "quick_urls" {
  description = "Quick access URLs for testing"
  value = merge(
    {
      "🌍 Global (Traffic Manager)" = "https://${module.traffic_manager.fqdn}"
    },
    # Dynamic region URLs
    {
      for region_key, region_config in local.regions : 
      "${region_key == "us" ? "🇺🇸" : region_key == "europe" ? "🇪🇺" : "🇮🇳"} ${title(region_key)} Direct" => module.app_services[region_key].app_service_url
    },
    {
      "Health Checks:" = "Add ${var.health_check_path} to any URL above"
    }
  )
}

# Auto-scaling Configuration Summary (Dynamic)
output "autoscaling_summary" {
  description = "Auto-scaling configuration for each region"
  value = {
    for region_key, region_config in local.regions : "${region_key}_region" => {
      app_service_plan = module.app_services[region_key].app_service_plan_name
      location        = region_config.location
      min_instances   = var.min_instances
      max_instances   = var.max_instances
      scaling_triggers = "CPU > 70% (scale out), CPU < 30% (scale in), Memory > 80% (scale out), Memory < 40% (scale in)"
    }
  }
}

# Regions Configuration (for reference)
output "regions_config" {
  description = "Configuration of all deployed regions"
  value = local.regions
}

# Easy-to-read region URLs
output "region_urls_formatted" {
  description = "Formatted list of all region URLs for easy copying"
  value = concat([
    "🌍 Global: https://${module.traffic_manager.fqdn}"
  ], [
    for region_key, region_config in local.regions :
    "${region_key == "us" ? "🇺🇸" : region_key == "europe" ? "🇪🇺" : "🇮🇳"} ${title(region_key)} (${region_config.location}): ${module.app_services[region_key].app_service_url}"
  ])
}
