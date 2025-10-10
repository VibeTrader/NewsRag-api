# ============================================
# Monitoring Module Outputs
# ============================================

output "action_group_id" {
  description = "ID of the action group"
  value       = azurerm_monitor_action_group.main.id
}

output "action_group_name" {
  description = "Name of the action group"
  value       = azurerm_monitor_action_group.main.name
}

# App Service Alert IDs
output "response_time_alert_ids" {
  description = "IDs of response time alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_response_time : k => v.id }
}

output "error_5xx_alert_ids" {
  description = "IDs of 5xx error alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_error_rate : k => v.id }
}

output "error_4xx_alert_ids" {
  description = "IDs of 4xx error alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_client_error_rate : k => v.id }
}

output "memory_alert_ids" {
  description = "IDs of memory alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_memory : k => v.id }
}

output "connection_alert_ids" {
  description = "IDs of connection alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_connections : k => v.id }
}

output "request_spike_alert_ids" {
  description = "IDs of request spike alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.request_spike : k => v.id }
}

# App Service Plan Alert IDs (Standard+ only)
output "cpu_plan_alert_ids" {
  description = "IDs of CPU plan alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_cpu_plan : k => v.id }
}

output "memory_plan_alert_ids" {
  description = "IDs of memory plan alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_memory_plan : k => v.id }
}

# Application Insights Alert IDs
output "availability_alert_id" {
  description = "ID of the availability alert"
  value       = azurerm_monitor_metric_alert.availability.id
}

output "exception_alert_id" {
  description = "ID of the exception rate alert"
  value       = azurerm_monitor_metric_alert.high_exception_rate.id
}

output "dependency_failure_alert_id" {
  description = "ID of the dependency failure alert"
  value       = azurerm_monitor_metric_alert.dependency_failures.id
}