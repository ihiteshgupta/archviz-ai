#!/bin/bash
# ArchViz AI - Azure Deployment Script
# Usage: ./deploy.sh [environment] [location]
# Example: ./deploy.sh prod eastus

set -e

# Configuration
ENVIRONMENT=${1:-dev}
LOCATION=${2:-eastus}
BASE_NAME="archvizai"

echo "=========================================="
echo "  ArchViz AI - Azure Deployment"
echo "=========================================="
echo ""
echo "  Environment: $ENVIRONMENT"
echo "  Location: $LOCATION"
echo ""

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found."
    echo "   Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check jq
if ! command -v jq &> /dev/null; then
    echo "❌ jq not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq
    else
        sudo apt-get install -y jq
    fi
fi

# Check logged in
if ! az account show &> /dev/null; then
    echo "🔐 Please log in to Azure..."
    az login
fi

# Show current subscription
echo "📋 Current subscription:"
az account show --query "{Name:name, ID:id}" -o table
echo ""
read -p "Continue with this subscription? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Run 'az account set --subscription <id>' to change subscription"
    exit 1
fi

# Deploy infrastructure
echo ""
echo "🏗️  Deploying Azure infrastructure..."
echo "   This may take 5-10 minutes..."
echo ""

DEPLOYMENT_OUTPUT=$(az deployment sub create \
    --location "$LOCATION" \
    --template-file main.bicep \
    --parameters environment="$ENVIRONMENT" location="$LOCATION" baseName="$BASE_NAME" \
    --query "properties.outputs" \
    -o json)

# Extract outputs
RG_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.resourceGroupName.value')
ACR_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.acrName.value')
ACR_LOGIN_SERVER=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.acrLoginServer.value')
OPENAI_ENDPOINT=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.openAiEndpoint.value')
STORAGE_ACCOUNT=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.storageAccountName.value')
API_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.containerAppUrl.value')
WEBAPP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.staticWebAppUrl.value')
WEBAPP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.staticWebAppName.value')

echo ""
echo "✅ Infrastructure deployed!"
echo ""
echo "📝 Resource Summary:"
echo "   Resource Group:    $RG_NAME"
echo "   Container Registry: $ACR_NAME"
echo "   OpenAI Endpoint:   $OPENAI_ENDPOINT"
echo "   Storage Account:   $STORAGE_ACCOUNT"
echo "   API URL:           $API_URL"
echo "   Web App URL:       $WEBAPP_URL"
echo ""

# Get secrets
echo "🔑 Retrieving credentials..."

OPENAI_NAME=$(az cognitiveservices account list -g "$RG_NAME" --query "[?kind=='OpenAI'].name" -o tsv)
OPENAI_KEY=$(az cognitiveservices account keys list \
    --resource-group "$RG_NAME" \
    --name "$OPENAI_NAME" \
    --query "key1" -o tsv)

STORAGE_KEY=$(az storage account keys list \
    --resource-group "$RG_NAME" \
    --account-name "$STORAGE_ACCOUNT" \
    --query "[0].value" -o tsv)

STORAGE_CONN=$(az storage account show-connection-string \
    --resource-group "$RG_NAME" \
    --name "$STORAGE_ACCOUNT" \
    --query "connectionString" -o tsv)

SWA_TOKEN=$(az staticwebapp secrets list \
    --name "$WEBAPP_NAME" \
    --resource-group "$RG_NAME" \
    --query "properties.apiKey" -o tsv 2>/dev/null || echo "")

# Create .env file
ENV_FILE="../.env"
echo ""
echo "📄 Creating $ENV_FILE..."
cat > "$ENV_FILE" << EOF
# ArchViz AI - Azure Configuration
# Generated on $(date)

# =============================================================================
# Azure OpenAI
# =============================================================================
AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY=$OPENAI_KEY
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4o
AZURE_OPENAI_GPT4V_DEPLOYMENT=gpt-4o
AZURE_OPENAI_DALLE_DEPLOYMENT=dall-e-3

# =============================================================================
# Azure Storage
# =============================================================================
AZURE_STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT
AZURE_STORAGE_ACCOUNT_KEY=$STORAGE_KEY
AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONN

# Container names
AZURE_UPLOADS_CONTAINER=uploads
AZURE_RENDERS_CONTAINER=renders
AZURE_TEXTURES_CONTAINER=textures
AZURE_MODELS_CONTAINER=models

# =============================================================================
# Azure Container Registry
# =============================================================================
ACR_NAME=$ACR_NAME
ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER

# =============================================================================
# API URLs
# =============================================================================
API_URL=$API_URL
NEXT_PUBLIC_API_URL=$API_URL
EOF

echo "✅ Environment file created!"

# Build and push Docker image
echo ""
read -p "Build and push Docker image to ACR? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🐳 Building and pushing Docker image..."

    # Login to ACR
    az acr login --name "$ACR_NAME"

    # Build image
    cd ..
    docker build -t "$ACR_LOGIN_SERVER/archviz-api:latest" .

    # Push image
    docker push "$ACR_LOGIN_SERVER/archviz-api:latest"

    # Update Container App
    echo ""
    echo "🚀 Updating Container App with new image..."
    az containerapp update \
        --name "ca-${BASE_NAME}${ENVIRONMENT}-api" \
        --resource-group "$RG_NAME" \
        --image "$ACR_LOGIN_SERVER/archviz-api:latest"

    echo "✅ API deployed!"
    cd infra
fi

# GitHub Actions setup
echo ""
echo "=========================================="
echo "  GitHub Actions Setup"
echo "=========================================="
echo ""
echo "To enable CI/CD, add these secrets to your GitHub repository:"
echo ""
echo "1. AZURE_CREDENTIALS:"
echo "   Run: az ad sp create-for-rbac --name archviz-ai-deploy --role contributor \\"
echo "        --scopes /subscriptions/\$(az account show --query id -o tsv)/resourceGroups/$RG_NAME \\"
echo "        --sdk-auth"
echo ""
echo "2. AZURE_STATIC_WEB_APPS_API_TOKEN:"
if [ -n "$SWA_TOKEN" ]; then
    echo "   $SWA_TOKEN"
else
    echo "   Run: az staticwebapp secrets list --name $WEBAPP_NAME -g $RG_NAME"
fi
echo ""
echo "3. Add these repository variables:"
echo "   ACR_NAME: $ACR_NAME"
echo "   API_URL: $API_URL"
echo ""

# Summary
echo "=========================================="
echo "  Deployment Complete! 🎉"
echo "=========================================="
echo ""
echo "URLs:"
echo "  API:      $API_URL"
echo "  Frontend: $WEBAPP_URL"
echo "  Docs:     $API_URL/docs"
echo ""
echo "Next steps:"
echo "  1. Copy .env to your project root"
echo "  2. Run 'npm run dev' for local development"
echo "  3. Set up GitHub Actions secrets for CI/CD"
echo "  4. Push to main branch to trigger deployment"
echo ""
