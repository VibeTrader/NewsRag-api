# ============================================
# Monitoring Module Outputs - Essential Alerts Only
# ============================================

output "action_group_id" {
  description = "ID of the action group"
  value       = azurerm_monitor_action_group.main.id
}

output "action_group_name" {
  description = "Name of the action group"
  value       = azurerm_monitor_action_group.main.name
}

# App Service Alert IDs (Environment-level)
output "response_time_alert_id" {
  description = "ID of environment-level response time alert"
  value       = azurerm_monitor_metric_alert.high_response_time.id
}

output "error_5xx_alert_id" {
  description = "ID of environment-level 5xx error alert"
  value       = azurerm_monitor_metric_alert.high_error_rate.id
}

output "request_spike_alert_id" {
  description = "ID of environment-level request spike alert"
  value       = azurerm_monitor_metric_alert.request_spike.id
}

# App Service Plan Alert IDs (Standard+ only, environment-level)
output "cpu_plan_alert_id" {
  description = "ID of environment-level CPU plan alert"
  value       = var.enable_plan_metrics ? azurerm_monitor_metric_alert.high_cpu_plan[0].id : null
}

output "memory_plan_alert_id" {
  description = "ID of environment-level memory plan alert"
  value       = var.enable_plan_metrics ? azurerm_monitor_metric_alert.high_memory_plan[0].id : null
}

# Application Insights Alert IDs
output "availability_alert_id" {
  description = "ID of the availability alert"
  value       = azurerm_monitor_metric_alert.availability.id
}

# Summary of active alerts
output "active_alerts_count" {
  description = "Number of active monitoring alerts"
  value = {
    app_service_alerts = 3  # 3 environment-level alerts (response_time, error_rate, request_spike)
    availability_alerts = 1
    plan_alerts = var.enable_plan_metrics ? 2 : 0  # 2 plan alerts when enabled (cpu, memory)
    total = 3 + 1 + (var.enable_plan_metrics ? 2 : 0)
  }
}