# ============================================
# Monitoring Module - PROD ONLY
# Per-region alerts (Azure limitation for App Services)
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# ============================================
# Action Group Configuration
# Option 1: Use existing action group from another resource group
# Option 2: Create new action group (if use_existing_action_group = false)
# ============================================

# Data source to reference existing action group
data "azurerm_monitor_action_group" "existing" {
  count               = var.use_existing_action_group ? 1 : 0
  name                = var.existing_action_group_name
  resource_group_name = var.existing_action_group_rg
}

# Create new action group only if not using existing
resource "azurerm_monitor_action_group" "main" {
  count               = var.use_existing_action_group ? 0 : 1
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

# Local to get the action group ID (either existing or newly created)
locals {
  action_group_id = var.use_existing_action_group ? data.azurerm_monitor_action_group.existing[0].id : azurerm_monitor_action_group.main[0].id
}

# ============================================
# App Service Alerts (Per-Region)
# Note: Azure does NOT support multi-resource alerts for App Services
# ============================================

# HTTP Response Time Alerts
# App Service specific alerts removed. 
# We rely on Application Insights alerts for Error Rates, Response Times, and Availability.


# ============================================
# Custom Application Insights Alerts
# For API Key Expiry, Service Failures, etc.
# ============================================

# Alert: Critical API Errors (Authentication/Configuration)
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "critical_api_error" {
  name                = "alert-critical-api-error-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "CRITICAL: API authentication or configuration error detected - API key may be expired!"
  severity            = 0 # Critical
  enabled             = true

  scopes = [var.application_insights_id]

  evaluation_frequency = "PT5M" # Check every 5 minutes
  window_duration      = "PT5M" # Look at last 5 minutes

  criteria {
    query = <<-QUERY
      customEvents
      | where name in ("critical_api_error", "critical_search_error", "critical_summarize_error")
      | where customDimensions.category in ("authentication", "configuration")
      | summarize count() by bin(timestamp, 5m)
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0 # Alert on ANY critical error

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [local.action_group_id]
  }

  tags = var.common_tags
}


# Alert: Startup Critical Errors
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "startup_error" {
  name                = "alert-startup-error-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "CRITICAL: Application started with configuration issues - services may be unavailable!"
  severity            = 0 # Critical
  enabled             = true

  scopes = [var.application_insights_id]

  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"

  criteria {
    query = <<-QUERY
      customEvents
      | where name == "startup_critical_error"
      | summarize count() by bin(timestamp, 5m)
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [local.action_group_id]
  }

  tags = var.common_tags
}

# Alert: Embedding Service Failures (Azure OpenAI down)
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "embedding_failures" {
  name                = "alert-embedding-failures-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "HIGH: Multiple embedding generation failures - Azure OpenAI may be having issues"
  severity            = 1 # High
  enabled             = true

  scopes = [var.application_insights_id]

  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-QUERY
      exceptions
      | where type contains "EmbeddingError" or 
              (customDimensions.service == "azure_openai" and customDimensions.operation == "embedding")
      | summarize count() by bin(timestamp, 15m)
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 5 # More than 5 failures in 15 minutes

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [local.action_group_id]
  }

  tags = var.common_tags
}


# Alert: Qdrant Database Failures
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "qdrant_failures" {
  name                = "alert-qdrant-failures-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "HIGH: Multiple Qdrant database failures - database may be unreachable"
  severity            = 1 # High
  enabled             = true

  scopes = [var.application_insights_id]

  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-QUERY
      exceptions
      | where type contains "QdrantError" or customDimensions.service == "qdrant"
      | summarize count() by bin(timestamp, 15m)
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 5

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [local.action_group_id]
  }

  tags = var.common_tags
}

# NOTE: Search failures alert removed due to KQL type issues.
# Can be added manually in Azure Portal if needed.

# Alert: Rate Limiting Issues
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "rate_limit_alert" {
  name                = "alert-rate-limit-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "WARNING: Rate limiting detected - may need to increase Azure OpenAI quota"
  severity            = 2 # Warning
  enabled             = true

  scopes = [var.application_insights_id]

  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-QUERY
      customEvents
      | where name contains "critical" and customDimensions.category == "rate_limit"
      | union (
        requests
        | where resultCode == 429
      )
      | summarize count() by bin(timestamp, 15m)
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 3 # More than 3 rate limit errors

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [local.action_group_id]
  }

  tags = var.common_tags
}

# Alert: No Search Results Pattern (Potential Data Issue)
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "no_results_pattern" {
  name                = "alert-no-results-pattern-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "INFO: Unusually high number of 'no results' responses - check if data ingestion is working"
  severity            = 3 # Info
  enabled             = true

  scopes = [var.application_insights_id]

  evaluation_frequency = "PT15M"
  window_duration      = "PT1H"

  criteria {
    query = <<-QUERY
      customEvents
      | where name in ("search_no_results", "summary_no_results")
      | summarize count() by bin(timestamp, 1h)
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 50 # More than 50 no-result queries in an hour

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [local.action_group_id]
  }

  tags = var.common_tags
}


# ============================================
# Availability Tests (Synthetic Monitoring)
# CRITICAL: Detects when your API is down
# ============================================

resource "azurerm_application_insights_standard_web_test" "health_check" {
  name                    = "webtest-health-${var.project_name}-${var.environment}"
  resource_group_name     = var.resource_group_name
  location                = var.location
  application_insights_id = var.application_insights_id

  geo_locations = ["us-tx-sn1-azr", "us-il-ch1-azr", "emea-nl-ams-azr"]

  frequency     = 300 # Check every 5 minutes
  timeout       = 30
  enabled       = true
  retry_enabled = true

  request {
    url = "https://${var.api_hostname}/health/simple"

    header {
      name  = "Accept"
      value = "application/json"
    }
  }

  validation_rules {
    expected_status_code = 200

    content {
      content_match      = "healthy"
      ignore_case        = true
      pass_if_text_found = true
    }
  }

  tags = var.common_tags
}

# Alert when availability test fails
resource "azurerm_monitor_metric_alert" "availability_test_failed" {
  name                = "alert-site-down-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [var.application_insights_id]
  description         = "CRITICAL: API health check is failing from multiple locations!"
  severity            = 0 # Critical
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "availabilityResults/availabilityPercentage"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 90
  }

  action {
    action_group_id = local.action_group_id
  }

  tags = var.common_tags
}



# ============================================
# Response Time Degradation Alert
# ============================================

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "response_time_degradation" {
  name                = "alert-response-degradation-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "WARNING: API response times have significantly increased"
  severity            = 2
  enabled             = true

  scopes = [var.application_insights_id]

  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-QUERY
      requests
      | where timestamp > ago(15m)
      | where name contains "/search" or name contains "/summarize"
      | summarize P95 = percentile(duration, 95) by bin(timestamp, 5m)
      | where P95 > 10000  // P95 > 10 seconds is bad
    QUERY

    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 2
      number_of_evaluation_periods             = 3
    }
  }

  action {
    action_groups = [local.action_group_id]
  }

  tags = var.common_tags
}
