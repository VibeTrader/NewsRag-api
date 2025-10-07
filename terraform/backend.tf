# backend.tf
terraform {
  backend "azurerm" {
    # Empty backend configuration - will be filled via CLI parameters
  }
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.75.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}