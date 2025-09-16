# Azure Infrastructure Deployment Plan
# Credit Risk Analysis - Production Deployment

## Resource Group: rg-credit-risk-analysis-prod
## Region: UK West (preferred region for EY UK)

## Required Azure Resources:
1. **Resource Group** - Container for all resources
2. **Azure Databricks Workspace** - Data processing and analytics
3. **Azure App Service** - Web application hosting
4. **Azure App Service Plan** - Compute resources for the app
5. **Azure Key Vault** - Secure storage for API keys
6. **Azure Container Registry** - Store Docker images (optional)
7. **Azure Application Insights** - Monitoring and telemetry

## Cost Optimization:
- App Service Plan: B1 (Basic) for development, P1V2 (Premium) for production
- Databricks: Standard tier with auto-scaling cluster
- Key Vault: Standard tier
- Application Insights: Pay-as-you-go

## Estimated Monthly Cost: $150-300 USD (depending on usage)
