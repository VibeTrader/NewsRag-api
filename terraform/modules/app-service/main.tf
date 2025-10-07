# ============================================
# Modified App Service Module - Uses Existing Resource Group
# Each region gets its own App Service Plan (required by Azure)
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

# Local values for this module
locals {
  resource_prefix = "${var.project_name}-${var.region.short_name}"
}

# App Service Plan (Region-specific - REQUIRED)
# Note: App Service Plans cannot be shared across regions
resource "azurerm_service_plan" "main" {
  name                = "plan-${local.resource_prefix}-${var.environment}"
  location            = var.region.location  # Each plan in its own region
  resource_group_name = var.existing_resource_group_name  # Use existing RG
  
  os_type  = "Linux"
  sku_name = var.app_service_plan_sku
  
  tags = var.common_tags
}

# App Service (Uses the regional App Service Plan)
resource "azurerm_linux_web_app" "main" {
  name                = "${local.resource_prefix}-${var.environment}"
  location            = var.region.location
  resource_group_name = var.existing_resource_group_name  # Use existing RG
  service_plan_id     = azurerm_service_plan.main.id
  
  site_config {
    # Python 3.12 application stacks
    application_stack {
      python_version = "3.11"
    }
    
    # FastAPI startup commands
    app_command_line = "python -m uvicorn api:app --host 0.0.0.0 --port 8000"
    
    # Health check configuration
    health_check_path = "/health"
    
    # Always on to keep the app warm
    always_on = true
    
    # FTP not needed for CI/CD deployments
    ftps_state = "Disabled"
    
    # HTTP to HTTPS redirect
    http2_enabled = true
  }
  
  # Application settings
  app_settings = merge(
    var.app_settings,
    {
      # Region-specific settings for telemetry identification
      DEPLOYMENT_REGION = var.region.short_name
      AZURE_REGION      = var.region.location
      
      # Shared Application Insights (all regions use same instance)
      APPINSIGHTS_INSTRUMENTATIONKEY = var.application_insights_instrumentation_key
      APPLICATIONINSIGHTS_CONNECTION_STRING = var.application_insights_connection_string
      
      # Enable detailed logging
      WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
      WEBSITES_CONTAINER_START_TIME_LIMIT = "1800"
      SCM_DO_BUILD_DURING_DEPLOYMENT      = "true"
    }
  )
  
  # Connection strings (if needed for databases)
  dynamic "connection_string" {
    for_each = var.connection_strings
    content {
      name  = connection_string.value.name
      type  = connection_string.value.type
      value = connection_string.value.value
    }
  }
  
  tags = var.common_tags
  
  lifecycle {
    ignore_changes = [
      # Ignore changes made by deployment pipelines
      app_settings["WEBSITE_RUN_FROM_PACKAGE"],
      app_settings["SCM_REPOSITORY_PATH"]
    ]
  }
}

# Auto-scaling configuration (Per App Service Plan)
# Each region scales independently based on its own metrics
resource "azurerm_monitor_autoscale_setting" "main" {
  name                = "autoscale-${local.resource_prefix}-${var.environment}"
  location            = var.region.location
  resource_group_name = var.existing_resource_group_name  # Use existing RG
  target_resource_id  = azurerm_service_plan.main.id
  
  profile {
    name = "DefaultAutoscaleProfile"
    
    capacity {
      default = 1
      minimum = var.min_instances
      maximum = var.max_instances
    }
    
    # Scale out rule - CPU > 70%
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 70
      }
      
      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "2"
        cooldown  = "PT5M"
      }
    }
    
    # Scale in rule - CPU < 30%
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 30
      }
      
      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }
    
    # Scale out rule - Memory > 80%
    rule {
      metric_trigger {
        metric_name        = "MemoryPercentage"
        metric_resource_id = azurerm_service_plan.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT10M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 80
      }
      
      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT10M"
      }
    }
    
    # Scale in rule - Memory < 40%
    rule {
      metric_trigger {
        metric_name        = "MemoryPercentage"
        metric_resource_id = azurerm_service_plan.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT10M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 40
      }
      
      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT10M"
      }
    }
  }
  
  tags = var.common_tags
}
