#!/bin/bash

# Clean API-only deployment script
# Deploys only the FastAPI service to Azure App Service

set -e

# Configuration
RESOURCE_GROUP="ragvector"
LOCATION="eastus"
APP_NAME="newsragnarok-api"
PLAN_NAME="newsragnarok-api-plan"

echo "🚀 Deploying NewsRagnarok API to Azure App Service"
echo "=================================================="

# Step 1: Create App Service Plan
echo "📋 Creating App Service Plan..."
az appservice plan create \
  --name $PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku B1 \
  --is-linux \
  --output none 2>/dev/null || echo "Plan already exists"

# Step 2: Create Web App
echo "🌐 Creating Web App..."
az webapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan $PLAN_NAME \
  --runtime "PYTHON:3.11" \
  --deployment-local-git \
  --output none 2>/dev/null || echo "Web app already exists"

# Step 3: Set environment variables
echo "🔧 Setting environment variables..."
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    QDRANT_URL="$(grep QDRANT_URL .env | cut -d'=' -f2)" \
    QDRANT_API_KEY="$(grep QDRANT_API_KEY .env | cut -d'=' -f2)" \
    REDIS_HOST="$(grep REDIS_HOST .env | cut -d'=' -f2)" \
    REDIS_PASSWORD="$(grep REDIS_PASSWORD .env | cut -d'=' -f2)" \
    AZ_ACCOUNT_NAME="$(grep AZ_ACCOUNT_NAME .env | cut -d'=' -f2)" \
    AZ_BLOB_ACCESS_KEY="$(grep AZ_BLOB_ACCESS_KEY .env | cut -d'=' -f2)" \
    AZ_CONTAINER_NAME="$(grep AZ_CONTAINER_NAME .env | cut -d'=' -f2)" \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Step 4: Configure startup command
echo "⚙️ Configuring startup command..."
az webapp config set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "python -m uvicorn api:app --host 0.0.0.0 --port 8000"

# Step 5: Create deployment package
echo "📦 Creating deployment package..."
# Create zip file with only API files
zip -r deploy.zip . -x "*.sh" "*.md" "*.txt" "*.yml" "*.json" ".git/*" "__pycache__/*" "*.pyc"

# Step 6: Deploy code
echo "📤 Deploying code..."
az webapp deployment source config-zip \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --src deploy.zip

# Step 7: Get URL
echo "🔗 Getting app URL..."
APP_URL=$(az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "defaultHostName" -o tsv)

echo ""
echo "✅ API Deployment completed successfully!"
echo "🌐 API URL: https://$APP_URL"
echo ""
echo "🧪 Testing API..."
echo "Health check: https://$APP_URL/health"
echo "Search test: https://$APP_URL/search"
echo ""
echo "📋 Useful commands:"
echo "  View logs: az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo "  Restart: az webapp restart --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo "  Scale: az appservice plan update --name $PLAN_NAME --resource-group $RESOURCE_GROUP --sku S1"
echo ""
echo "💡 API Benefits:"
echo "  ✅ Clean API-only deployment"
echo "  ✅ Lightweight (~200MB total)"
echo "  ✅ Fast deployments"
echo "  ✅ Easy scaling"
echo "  ✅ Built-in monitoring"

# Cleanup
rm -f deploy.zip
