variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "Region configuration"
  type = object({
    location   = string
    short_name = string
  })
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "container_app_environment_id" {
  description = "ID of the Container App Environment"
  type        = string
}

variable "container_image" {
  description = "Container image to deploy"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/aci-helloworld"
}

# ============================================
# REGISTRY AUTHENTICATION VARIABLES
# ============================================
variable "registry_server" {
  description = "ACR login server (e.g., myregistry.azurecr.io)"
  type        = string
  default     = ""
}

variable "registry_username" {
  description = "ACR admin username"
  type        = string
  default     = ""
}

variable "registry_password" {
  description = "ACR admin password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "target_port" {
  description = "Port exposed by the container"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "CPU cores (e.g. 0.25, 0.5, 1.0)"
  type        = number
  default     = 0.5
}

variable "memory" {
  description = "Memory in Gi (e.g. 0.5Gi, 1.0Gi)"
  type        = string
  default     = "1.0Gi"
}

variable "min_replicas" {
  description = "Minimum replicas (Set to 0 for Dev serverless)"
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = "Maximum replicas"
  type        = number
  default     = 3
}

variable "env_vars" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/health"
}

variable "common_tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}
