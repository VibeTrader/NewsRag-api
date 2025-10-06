# ============================================
# App Service Module Outputs
# ============================================

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.region.name
}

output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.region.id
}

output "app_service_plan_name" {
  description = "Name of the App Service Plan"
  value       = azurerm_service_plan.main.name
}

output "app_service_plan_id" {
  description = "ID of the App Service Plan"
  value       = azurerm_service_plan.main.id
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

output "autoscale_setting_id" {
  description = "ID of the autoscale setting"
  value       = azurerm_monitor_autoscale_setting.main.id
}
