# ============================================
# Traffic Manager Module - Global Load Balancing
# ============================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

# Traffic Manager Profile
resource "azurerm_traffic_manager_profile" "main" {
  name                   = "tm-${var.project_name}-${var.environment}"
  resource_group_name    = var.resource_group_name
  traffic_routing_method = "Geographic"
  
  dns_config {
    relative_name = "${var.project_name}-global-${var.environment}"
    ttl           = 30
  }
  
  monitor_config {
    protocol                     = "HTTPS"
    port                         = 443
    path                         = var.health_check_path
    interval_in_seconds         = 30
    timeout_in_seconds          = 10
    tolerated_number_of_failures = 3
  }
  
  tags = var.common_tags
}

# US Endpoint (existing app service)
resource "azurerm_traffic_manager_azure_endpoint" "us" {
  name               = "endpoint-us-${var.environment}"
  profile_id         = azurerm_traffic_manager_profile.main.id
  target_resource_id = var.existing_app_service_id
  weight             = 100
  priority           = 1
  
  # Geographic mapping for US endpoint
  geo_mappings = [
    "US", "CA", "MX", "BZ", "CR", "SV", "GT", "HN", "NI", "PA"
  ]
}

# Europe Endpoint
resource "azurerm_traffic_manager_azure_endpoint" "europe" {
  name               = "endpoint-eu-${var.environment}"
  profile_id         = azurerm_traffic_manager_profile.main.id
  target_resource_id = var.europe_app_service_id
  weight             = 100
  priority           = 2
  
  # Geographic mapping for Europe + Asia Pacific
  geo_mappings = [
    # Europe & Middle East
    "JO", "AE", "SA", "EG", "LB", "SY", "IQ", "IR", "TR", 
    "GR", "IT", "FR", "DE", "GB", "ES", "PT", "NL", "BE",
    "CH", "AT", "PL", "CZ", "HU", "RO", "BG", "HR", "SI",
    "SK", "EE", "LV", "LT", "FI", "SE", "NO", "DK", "IS",
    "IE", "MT", "CY", "LU", "MC", "AD", "SM", "VA", "LI",
    # Asia Pacific (from deleted India endpoint)
    "IN", "LK", "BD", "NP", "PK", "AF", "MY", "SG", "ID",
    "TH", "VN", "KH", "LA", "MM", "PH", "BN", "TL"
  ]
}