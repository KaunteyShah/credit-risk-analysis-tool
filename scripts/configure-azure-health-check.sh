#!/bin/bash
# Azure App Service Health Check Configuration Script
# Run this script to configure health check monitoring for your Azure App Service

# Configuration variables
RESOURCE_GROUP="rg-credit-risk-analysis-prod-ukwest"
APP_NAME="credit-risk-analysis-prod-app-25h2ya"
HEALTH_PATH="/health"

echo "🏥 Configuring Azure App Service Health Check..."

# Configure health check path
echo "📍 Setting health check path to: $HEALTH_PATH"
az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --health-check-path "$HEALTH_PATH"

# Configure health check settings
echo "⚙️ Configuring health check parameters..."
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings \
    WEBSITE_HEALTHCHECK_MAXPINGFAILURES=3 \
    WEBSITE_HEALTHCHECK_MAXUNHEALTHYWORKERPERCENT=75 \
    WEBSITE_HTTPLOGGING_RETENTION_DAYS=7

# Restart app to apply changes
echo "🔄 Restarting app to apply health check configuration..."
az webapp restart \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME"

echo "✅ Health check configuration complete!"
echo "🌐 Health check URL: https://$APP_NAME.azurewebsites.net$HEALTH_PATH"
echo "📊 Monitor health in Azure Portal: App Service > Health check"