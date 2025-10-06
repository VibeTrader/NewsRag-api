# ============================================
# Production Environment Configuration - Using Existing vibetrader-RAG-rg
# Updated with actual app settings from current deployment
# ============================================

# Environment configuration
environment = "prod"

# App Service tier configuration
app_service_plan_sku  = "B1"    # Basic tier for cost-effective start
app_service_plan_tier = "Basic"

# Scaling configuration (Basic tier limits)
min_instances = 1
max_instances = 2

# Health check endpoint 
health_check_path = "/health"

# Alert configuration
alert_email = "haripriyaveluchamy@aity.dev"
slack_webhook_url = "https://hooks.slack.com/services/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"  # Add your Slack webhook URL if you have one

# Log Analytics retention
log_retention_days = 30

# Complete Application Settings (from your current deployment)
app_settings = {
  # ============================================
  # Azure Platform Settings (automatically managed by Terraform)
  # ============================================
  WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
  WEBSITES_PORT                       = "8000"
  SCM_DO_BUILD_DURING_DEPLOYMENT      = "true"
  ENABLE_ORYX_BUILD                   = "true"
  
  # Python configuration
  PYTHON_VERSION     = "3.12"
  PYTHONUNBUFFERED   = "1"
  PORT               = "8000"
  
  # Application environment
  ENVIRONMENT = "production"
  
  # FastAPI/Uvicorn startup command
  STARTUP_COMMAND = "python -m uvicorn api:app --host 0.0.0.0 --port 8000"
  
  # FastAPI specific
  API_HOST = "0.0.0.0"
  API_PORT = "8000"
  
  # Health check
  HEALTH_CHECK_ENABLED = "true"
  
  # ============================================
  # Your Application-Specific Settings
  # ============================================
  
  # Azure OpenAI Configuration
  # IMPORTANT: Replace these with your actual values
  AZURE_OPENAI_API_VERSION         = "2024-02-01"                    # Replace with your version
  AZURE_OPENAI_DEPLOYMENT          = "your-deployment-name"          # Replace with your deployment
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "your-embedding-deployment"    # Replace with your embedding deployment
  AZURE_OPENAI_EMBEDDING_MODEL     = "text-embedding-3-large"        # Replace if different
  OPENAI_BASE_URL                  = "https://your-endpoint.openai.azure.com"  # Replace with your endpoint
  
  # Embedding Configuration
  EMBEDDING_DIMENSION = "3072"  # Adjust based on your embedding model
  
  # Qdrant Vector Database Configuration  
  # IMPORTANT: Replace these with your actual values
  QDRANT_COLLECTION_NAME = "news_articles"           # Replace if different
  QDRANT_URL            = "your-qdrant-url"          # Replace with your Qdrant URL
  
  # Azure Blob Storage Configuration
  # IMPORTANT: Replace these with your actual values
  AZ_ACCOUNT_NAME    = "your-storage-account"        # Replace with your storage account
  AZ_CONTAINER_NAME  = "your-container-name"         # Replace with your container
  
  # Cache Configuration
  CACHE_TTL           = "3600"      # Adjust as needed
  SUMMARY_CACHE_SIZE  = "1000"      # Adjust as needed
  SUMMARY_CACHE_TTL   = "3600"      # Adjust as needed
  
  # Article Processing Configuration
  DEFAULT_ARTICLE_LIMIT     = "50"       # Adjust as needed
  MAX_ARTICLE_CONTENT_CHARS = "10000"    # Adjust as needed
  MAX_CHUNK_SIZE           = "1000"      # Adjust as needed
  
  # Langfuse Configuration (if using)
  # IMPORTANT: Replace these with your actual values or remove if not using
  LANGFUSE_HOST = "your-langfuse-host"    # Replace or remove
  
  # ============================================
  # Note: The following will be auto-populated by Terraform:
  # - APPINSIGHTS_INSTRUMENTATIONKEY (from shared Application Insights)
  # - APPLICATIONINSIGHTS_CONNECTION_STRING (from shared Application Insights) 
  # - DEPLOYMENT_REGION (us/eu/in - added automatically per region)
  # - AZURE_REGION (region location - added automatically per region)
  # ============================================
}

# ============================================
# SENSITIVE SETTINGS - ADD MANUALLY AFTER DEPLOYMENT
# ============================================
# The following settings contain secrets and should be added manually 
# through Azure Portal or Azure CLI after Terraform deployment:
#
# 1. OPENAI_API_KEY - Your OpenAI/Azure OpenAI API key
# 2. QDRANT_API_KEY - Your Qdrant API key (if required)
# 3. AZ_BLOB_ACCESS_KEY - Your Azure Blob Storage access key
# 4. LANGFUSE_PUBLIC_KEY - Your Langfuse public key (if using)
# 5. LANGFUSE_SECRET_KEY - Your Langfuse secret key (if using)
#
# To add these manually after deployment:
# az webapp config appsettings set \
#   --resource-group vibetrader-RAG-rg \
#   --name newsraag-us-prod \
#   --settings OPENAI_API_KEY="your-key-here"
#
# Repeat for all 3 regions (newsraag-us-prod, newsraag-eu-prod, newsraag-in-prod)
# ============================================
