# ============================================
# Monitoring Module - Multi-Region Alerts and Dashboards
# Compatible with Basic, Standard, and Premium tiers
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

# Action Group for alerts (Email + Slack)
resource "azurerm_monitor_action_group" "main" {
  name                = "ag-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  short_name          = "newsrag"
  
  # Email notifications
  email_receiver {
    name          = "admin-email"
    email_address = var.alert_email
  }
  
  # Slack webhook notifications (if provided)
  dynamic "webhook_receiver" {
    for_each = var.slack_webhook_url != "" ? [1] : []
    content {
      name                    = "slack-alerts"
      service_uri             = var.slack_webhook_url
      use_common_alert_schema = true
    }
  }
  
  tags = var.common_tags
}

# ============================================
# Core App Service Alerts (All Tiers)
# ============================================

# HTTP Response Time Alerts
resource "azurerm_monitor_metric_alert" "high_response_time" {
  for_each = var.app_services
  
  name                = "alert-response-time-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High HTTP response time alert for ${each.key} region"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "HttpResponseTime"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 5 # 5 seconds

  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# HTTP 5xx Error Rate Alerts
resource "azurerm_monitor_metric_alert" "high_error_rate" {
  for_each = var.app_services
  
  name                = "alert-error-rate-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High 5xx error rate alert for ${each.key} region"
  severity            = 1 # Critical
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10 # More than 10 5xx errors in 5 minutes
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# HTTP 4xx Error Rate Alerts
resource "azurerm_monitor_metric_alert" "high_client_error_rate" {
  for_each = var.app_services
  
  name                = "alert-client-errors-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High 4xx error rate alert for ${each.key} region"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http4xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 50 # More than 50 4xx errors in 15 minutes
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Request Count Spike Alert
resource "azurerm_monitor_metric_alert" "request_spike" {
  for_each = var.app_services
  
  name                = "alert-request-spike-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "Unusual request spike alert for ${each.key} region"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT10M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Requests"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 1000 # More than 1000 requests in 10 minutes
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Memory Usage Alert (works for all tiers)
resource "azurerm_monitor_metric_alert" "high_memory" {
  for_each = var.app_services
  
  name                = "alert-memory-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High memory working set usage alert for ${each.key} region"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "MemoryWorkingSet"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 1610612736 # 1.5GB in bytes (adjust based on your tier)
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Connection Count Alert
resource "azurerm_monitor_metric_alert" "high_connections" {
  for_each = var.app_services
  
  name                = "alert-connections-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High connection count alert for ${each.key} region"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT10M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "AppConnections"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 100 # More than 100 concurrent connections
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# ============================================
# App Service Plan Alerts (Standard+ Tiers Only)
# These will be ignored on Basic tier
# ============================================

# CPU Percentage Alert for App Service Plan (Standard+)
resource "azurerm_monitor_metric_alert" "high_cpu_plan" {
  for_each = var.app_service_plans # This should be passed from main.tf
  
  name                = "alert-plan-cpu-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High CPU percentage alert for ${each.key} app service plan"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true
  enabled             = var.enable_plan_metrics # Control via variable
  
  criteria {
    metric_namespace = "Microsoft.Web/serverfarms"
    metric_name      = "CpuPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80 # 80% CPU
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Memory Percentage Alert for App Service Plan (Standard+)
resource "azurerm_monitor_metric_alert" "high_memory_plan" {
  for_each = var.app_service_plans
  
  name                = "alert-plan-memory-${each.key}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [each.value.id]
  description         = "High memory percentage alert for ${each.key} app service plan"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true
  enabled             = var.enable_plan_metrics
  
  criteria {
    metric_namespace = "Microsoft.Web/serverfarms"
    metric_name      = "MemoryPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 85 # 85% memory
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# ============================================
# Application Insights Alerts (Global)
# ============================================

# Availability Alert
resource "azurerm_monitor_metric_alert" "availability" {
  name                = "alert-availability-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [var.application_insights_id]
  description         = "Low availability alert for global endpoint"
  severity            = 1 # Critical
  frequency           = "PT1M"
  window_size         = "PT5M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "availabilityResults/availabilityPercentage"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 95 # Less than 95% availability
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Exception Rate Alert
resource "azurerm_monitor_metric_alert" "high_exception_rate" {
  name                = "alert-exceptions-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [var.application_insights_id]
  description         = "High exception rate alert"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT10M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "exceptions/count"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 20 # More than 20 exceptions in 10 minutes
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# Dependency Failure Alert
resource "azurerm_monitor_metric_alert" "dependency_failures" {
  name                = "alert-dependencies-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [var.application_insights_id]
  description         = "High dependency failure rate alert"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT10M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "dependencies/failed"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10 # More than 10 dependency failures in 10 minutes
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}