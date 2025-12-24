output "container_app_id" {
  value = azurerm_container_app.main.id
}

output "container_app_name" {
  value = azurerm_container_app.main.name
}

output "container_app_fqdn" {
  value = azurerm_container_app.main.latest_revision_fqdn
}

# Output removed (Environment created in separate module)
