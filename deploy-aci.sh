#!/bin/bash
# Azure Container Instances Deployment Script
# Cost-effective alternative to App Service

set -e

# Configuration
RESOURCE_GROUP="rg-credit-risk-clean"
CONTAINER_NAME="credit-risk-aci"
ACR_NAME="creditriskregistry"
IMAGE_NAME="credit-risk-app"
TAG="latest"

echo "🚀 Deploying Credit Risk App to Azure Container Instances..."

# Build and push Docker image to Azure Container Registry
echo "📦 Building Docker image..."
docker build -t $IMAGE_NAME:$TAG .

# Tag for ACR
docker tag $IMAGE_NAME:$TAG $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG

# Push to ACR
echo "📤 Pushing to Azure Container Registry..."
az acr login --name $ACR_NAME
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG

# Deploy to Azure Container Instances
echo "🔄 Deploying to Azure Container Instances..."
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_NAME \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    DEMO_MODE=false \
    WEBSITES_PORT=8000 \
  --dns-name-label credit-risk-demo \
  --restart-policy OnFailure

echo "✅ Deployment complete!"
echo "🌐 Access your app at: http://credit-risk-demo.eastus.azurecontainer.io:8000"
echo "💰 Cost savings: ~70% compared to App Service B3"