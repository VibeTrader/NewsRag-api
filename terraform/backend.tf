# backend.tf
terraform {
  # Temporarily disable backend for local testing
   # backend "azurerm" {
     # Empty backend configuration - will be filled via CLI parameters
  # }
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  # Subscription ID is provided via ARM_SUBSCRIPTION_ID environment variable in pipeline
  # For local testing, either set ARM_SUBSCRIPTION_ID env var or uncomment below:
  # subscription_id = "your-subscription-id-here"
  
  # Skip automatic resource provider registration (deprecated in v5.0)
  skip_provider_registration = true
  
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}
