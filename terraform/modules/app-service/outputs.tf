# ============================================
# Updated App Service Module Outputs
# Uses existing resource group instead of creating new one
# ============================================

output "resource_group_name" {
  description = "Name of the existing resource group being used"
  value       = var.existing_resource_group_name
}

output "resource_group_location" {
  description = "Location of the existing resource group"
  value       = var.existing_resource_group_location
}

output "app_service_name" {
  description = "Name of the App Service"
  value       = azurerm_linux_web_app.main.name
}

output "app_service_id" {
  description = "ID of the App Service"
  value       = azurerm_linux_web_app.main.id
}

output "app_service_url" {
  description = "URL of the App Service"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "app_service_hostname" {
  description = "Hostname of the App Service"
  value       = azurerm_linux_web_app.main.default_hostname
}

# NOTE: Autoscale outputs commented out for Basic tier compatibility
# Uncomment when upgrading to Standard/Premium tiers

# output "autoscale_setting_id" {
#   description = "ID of the autoscale setting"
#   value       = azurerm_monitor_autoscale_setting.main.id
# }

# output "autoscale_setting_name" {
#   description = "Name of the autoscale setting"
#   value       = azurerm_monitor_autoscale_setting.main.name
# }

output "region_info" {
  description = "Information about the region this module deployed to"
  value = {
    location   = var.region.location
    short_name = var.region.short_name
  }
}
