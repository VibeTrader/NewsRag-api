# ============================================
# Azure Front Door Module - Global CDN & Load Balancing
# Replaces Traffic Manager with proper HTTPS/SSL support
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

# Azure Front Door Profile (Premium tier for best features)
resource "azurerm_cdn_frontdoor_profile" "main" {
  name                = "fd-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  sku_name           = var.frontdoor_sku # "Premium_AzureFrontDoor" or "Standard_AzureFrontDoor"
  
  tags = var.common_tags
}

# Front Door Endpoint (this is your global URL)
resource "azurerm_cdn_frontdoor_endpoint" "main" {
  name                     = "${var.project_name}-${var.environment}-global"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  
  tags = var.common_tags
}

# Origin Group - Groups all your regional App Services
resource "azurerm_cdn_frontdoor_origin_group" "main" {
  name                     = "${var.project_name}-origins"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  
  # Load balancing settings
  load_balancing {
    additional_latency_in_milliseconds = 50
    sample_size                        = 4
    successful_samples_required        = 3
  }
  
  # Health probe configuration
  health_probe {
    interval_in_seconds = 30
    path                = var.health_check_path
    protocol            = "Https"
    request_type        = "GET"
  }
}

# US Origin
resource "azurerm_cdn_frontdoor_origin" "us" {
  name                          = "us-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  
  enabled                        = true
  host_name                      = var.us_app_service_hostname
  http_port                      = 80
  https_port                     = 443
  origin_host_header            = var.us_app_service_hostname
  priority                       = 1
  weight                         = 1000
  
  certificate_name_check_enabled = true
}

# EU Origin
resource "azurerm_cdn_frontdoor_origin" "eu" {
  name                          = "eu-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  
  enabled                        = true
  host_name                      = var.eu_app_service_hostname
  http_port                      = 80
  https_port                     = 443
  origin_host_header            = var.eu_app_service_hostname
  priority                       = 1
  weight                         = 1000
  
  certificate_name_check_enabled = true
}

# India Origin
# Only create the India origin if the variable is set at plan time (workaround for count limitation)
resource "azurerm_cdn_frontdoor_origin" "india" {
  count = var.environment == "prod" ? 1 : 0
  name                          = "india-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id

  enabled                        = true
  host_name                      = var.india_app_service_hostname
  http_port                      = 80
  https_port                     = 443
  origin_host_header              = var.india_app_service_hostname
  priority                       = 1
  weight                         = 1000

  certificate_name_check_enabled = true
}

# Front Door Route - Routes traffic to origin group
resource "azurerm_cdn_frontdoor_route" "main" {
  name                          = "default-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.main.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.main.id
  cdn_frontdoor_origin_ids      = compact([
    azurerm_cdn_frontdoor_origin.us.id,
    azurerm_cdn_frontdoor_origin.eu.id,
    # Only include India origin if it exists
    length(azurerm_cdn_frontdoor_origin.india) > 0 ? azurerm_cdn_frontdoor_origin.india[0].id : null
  ])
  
  enabled = true
  
  forwarding_protocol    = "HttpsOnly"
  https_redirect_enabled = true
  patterns_to_match      = ["/*"]
  supported_protocols    = ["Http", "Https"]
  
  cdn_frontdoor_custom_domain_ids = []
  link_to_default_domain         = true
}

# Optional: Custom Domain (uncomment when you have a domain)
# resource "azurerm_cdn_frontdoor_custom_domain" "main" {
#   name                     = replace(var.custom_domain, ".", "-")
#   cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
#   host_name               = var.custom_domain
#   
#   tls {
#     certificate_type    = "ManagedCertificate"
#     minimum_tls_version = "TLS12"
#   }
# }

# Optional: WAF Policy (Premium tier only)
resource "azurerm_cdn_frontdoor_firewall_policy" "main" {
  count = var.frontdoor_sku == "Premium_AzureFrontDoor" ? 1 : 0
  
  name                              = "waf${var.project_name}${var.environment}"
  resource_group_name               = var.resource_group_name
  sku_name                          = var.frontdoor_sku
  enabled                           = true
  mode                              = "Prevention"
  custom_block_response_status_code = 403
  
  # Managed rule sets
  managed_rule {
    type    = "DefaultRuleSet"
    version = "1.0"
    action  = "Block"
  }
  
  managed_rule {
    type    = "Microsoft_BotManagerRuleSet"
    version = "1.0"
    action  = "Block"
  }
  
  tags = var.common_tags
}

# Optional: Security Policy (Premium tier only)
resource "azurerm_cdn_frontdoor_security_policy" "main" {
  count = var.frontdoor_sku == "Premium_AzureFrontDoor" ? 1 : 0
  
  name                     = "security-policy"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.main.id
  
  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.main[0].id
      
      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.main.id
        }
        patterns_to_match = ["/*"]
      }
    }
  }
}
