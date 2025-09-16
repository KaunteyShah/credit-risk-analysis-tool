# 🚨 Alternative Deployment Approach
## For Organizations with Restricted Azure AD Permissions

Since your organization restricts service principal creation, let's use an alternative approach:

## Option 1: Manual Azure Portal Deployment ⭐ RECOMMENDED

### Step 1: Deploy Infrastructure Manually
```bash
# Create Resource Group
az group create \
  --name rg-credit-risk-analysis-prod \
  --location "East US" \
  --tags Environment=prod Application=credit-risk-analysis

# Deploy infrastructure using Azure CLI
az deployment group create \
  --resource-group rg-credit-risk-analysis-prod \
  --template-file infra/main.bicep \
  --parameters @infra/main.parameters.json
```

### Step 2: Deploy Application Manually
```bash
# Build and deploy using Azure CLI
az webapp up \
  --sku B1 \
  --name credit-risk-analysis-app-$(openssl rand -hex 3) \
  --resource-group rg-credit-risk-analysis-prod \
  --location "East US" \
  --runtime "PYTHON:3.11"
```

## Option 2: Request IT Support 🎯

Contact your IT team to:
1. Create service principal: `github-actions-credit-risk`
2. Assign "Contributor" role to subscription
3. Provide the credentials for GitHub Actions

## Option 3: Use Azure DevOps Instead 🔄

If GitHub Actions are restricted, we can set up Azure DevOps pipelines instead.

---

## 🚀 Ready to Proceed with Manual Deployment?

I'll guide you through the manual approach step by step!
