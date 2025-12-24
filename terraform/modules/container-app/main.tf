# ============================================
# Azure Container App Module
# Deploys a Container App Environment and Container App
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

locals {
  resource_prefix = "${var.project_name}-${var.region.short_name}"
}

# -----------------------------------------------------
# Container App Environment (The "Cluster")
# -----------------------------------------------------
# Environment resource moved to ../container-env


# -----------------------------------------------------
# Container App (The Microservice)
# -----------------------------------------------------
resource "azurerm_container_app" "main" {
  name                         = "ca-${local.resource_prefix}-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Ingress configuration (Public HTTP)
  ingress {
    external_enabled = true
    target_port      = var.target_port
    
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    # Container definition
    container {
      name   = "api"
      image  = var.container_image
      cpu    = var.cpu
      memory = var.memory

      # Helper for env vars
      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
      
      # Liveness probe (Health check)
      liveness_probe {
        port      = var.target_port
        transport = "HTTP"
        path      = var.health_check_path
      }
      
      # Readiness probe
      readiness_probe {
        port      = var.target_port
        transport = "HTTP"
        path      = var.health_check_path
      }
    }
    
    # Scaling Rules
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas
    
    # HTTP Scaling Rule (100 concurrent requests per replica)
    custom_scale_rule {
      name             = "http-scaling"
      custom_rule_type = "http"
      metadata = {
        concurrentRequests = "100"
      }
    }
  }

  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      template[0].container[0].image,
      ingress[0].traffic_weight
    ]
  }
}
