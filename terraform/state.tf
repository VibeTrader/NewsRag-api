terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"  # Replace with your state resource group name
    storage_account_name = "tfstatevraag"        # Replace with your storage account name
    container_name       = "terraform-state"     # Replace with your container name
    key                  = "newsraag-prod.tfstate"
    
    # Authentication is handled by GitHub Actions via OIDC (azure/login)
    # No need to include credentials here
  }
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.75.0"  # Use a specific version for consistency
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