# ============================================
# Outputs for Azure Front Door Module
# ============================================

output "frontdoor_id" {
  description = "ID of the Front Door profile"
  value       = azurerm_cdn_frontdoor_profile.main.id
}

output "frontdoor_endpoint_hostname" {
  description = "Hostname of the Front Door endpoint (your global URL)"
  value       = azurerm_cdn_frontdoor_endpoint.main.host_name
}

output "frontdoor_endpoint_url" {
  description = "Full HTTPS URL of the Front Door endpoint"
  value       = "https://${azurerm_cdn_frontdoor_endpoint.main.host_name}"
}

output "frontdoor_name" {
  description = "Name of the Front Door profile"
  value       = azurerm_cdn_frontdoor_profile.main.name
}

output "waf_policy_id" {
  description = "ID of the WAF policy (if Premium tier)"
  value       = var.frontdoor_sku == "Premium_AzureFrontDoor" ? azurerm_cdn_frontdoor_firewall_policy.main[0].id : null
}
