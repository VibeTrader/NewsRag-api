# backend.tf
terraform {
  # Temporarily disable backend for local testing
   # backend "azurerm" {
     # Empty backend configuration - will be filled via CLI parameters
  # }
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.75.0"
    }
  }
}

provider "azurerm" {
  # Skip automatic resource provider registration to avoid Microsoft.TimeSeriesInsights error
  skip_provider_registration = true
  
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}