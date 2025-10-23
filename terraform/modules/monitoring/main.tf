# ============================================
# Monitoring Module - Essential Alerts Only (Basic Tier Compatible)
# Simplified to avoid metric compatibility issues
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

# Shared Action Group for all environments (use count to create only once)
resource "azurerm_monitor_action_group" "main" {
  name                = "ag-${var.project_name}-global"
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
# Environment-Level App Service Alerts (Monitor ALL apps per environment)
# ============================================

# HTTP Response Time Alert - Environment Level
resource "azurerm_monitor_metric_alert" "high_response_time" {
  name                = "alert-response-time-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [for app in var.app_services : app.id]
  description         = "High HTTP response time alert for all ${var.environment} apps"
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

# HTTP 5xx Error Rate Alert - Environment Level
resource "azurerm_monitor_metric_alert" "high_error_rate" {
  name                = "alert-error-rate-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [for app in var.app_services : app.id]
  description         = "High 5xx error rate alert for all ${var.environment} apps"
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

# Request Count Spike Alert - Environment Level
resource "azurerm_monitor_metric_alert" "request_spike" {
  name                = "alert-request-spike-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [for app in var.app_services : app.id]
  description         = "Unusual request spike alert for all ${var.environment} apps"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT15M"
  auto_mitigate       = true
  
  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Requests"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 1000 # More than 1000 requests in 15 minutes
  }
  
  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
  
  tags = var.common_tags
}

# ============================================
# Application Insights Alerts (Essential Only)
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

# ============================================
# App Service Plan Alerts (Standard+ Tiers Only)
# These will be ignored on Basic tier
# ============================================

# CPU Percentage Alert for App Service Plan (Standard+) - Environment Level
resource "azurerm_monitor_metric_alert" "high_cpu_plan" {
  count = var.enable_plan_metrics ? 1 : 0
  
  name                = "alert-plan-cpu-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [for plan in var.app_service_plans : plan.id]
  description         = "High CPU percentage alert for ${var.environment} app service plan"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true
  
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

# Memory Percentage Alert for App Service Plan (Standard+) - Environment Level
resource "azurerm_monitor_metric_alert" "high_memory_plan" {
  count = var.enable_plan_metrics ? 1 : 0
  
  name                = "alert-plan-memory-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [for plan in var.app_service_plans : plan.id]
  description         = "High memory percentage alert for ${var.environment} app service plan"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  auto_mitigate       = true
  
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