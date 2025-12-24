# ============================================
# Terraform Outputs
# ============================================

output "existing_resource_group_name" {
  value = var.existing_resource_group_name
}

# ACR Outputs (Needed for CI/CD Login)
output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  value = azurerm_container_registry.acr.admin_username
  sensitive = true
}

output "acr_admin_password" {
  value = azurerm_container_registry.acr.admin_password
  sensitive = true
}

output "acr_name" {
    value = azurerm_container_registry.acr.name
}

# Container App Names (Dynamic based on region)
output "container_app_names" {
  value = {
    for k, v in module.container_apps : k => v.container_app_name
  }
}

output "front_door_hostname" {
  value = length(module.front_door) > 0 ? module.front_door[0].frontdoor_endpoint_hostname : null
}
