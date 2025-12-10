# ============================================
# Monitoring Module Outputs - Per-Region Alerts
# ============================================

output "action_group_id" {
  description = "ID of the action group (existing or newly created)"
  value       = local.action_group_id
}

output "action_group_name" {
  description = "Name of the action group"
  value       = var.use_existing_action_group ? var.existing_action_group_name : (length(azurerm_monitor_action_group.main) > 0 ? azurerm_monitor_action_group.main[0].name : "")
}

# App Service Alert IDs (Per-region)
output "response_time_alert_ids" {
  description = "IDs of response time alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_response_time : k => v.id }
}

output "error_5xx_alert_ids" {
  description = "IDs of 5xx error alerts by region"
  value       = { for k, v in azurerm_monitor_metric_alert.high_error_rate : k => v.id }
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

# Summary of active alerts
output "active_alerts_count" {
  description = "Number of active monitoring alerts"
  value = {
    app_service_alerts  = length(var.app_services) * 3 # 3 alerts per region
    availability_alerts = 1
    plan_alerts         = var.enable_plan_metrics ? length(var.app_service_plans) * 2 : 0
    total               = length(var.app_services) * 3 + 1 + (var.enable_plan_metrics ? length(var.app_service_plans) * 2 : 0)
  }
}
