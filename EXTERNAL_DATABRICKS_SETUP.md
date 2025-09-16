# 🔗 **External Databricks Setup Guide**

## ✅ **Azure Databricks Workspace Removed**

Your infrastructure has been updated to connect to your existing Databricks workspace instead of creating a new Azure Databricks workspace.

## 📋 **Required Configuration**

### **1. Update Parameters File**

Edit `/infra/main.parameters.json`:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName": {
      "value": "prod"
    },
    "applicationName": {
      "value": "credit-risk-analysis"
    },
    "location": {
      "value": "UK West"
    },
    "adminEmail": {
      "value": "kauntey.shah@uk.ey.com"
    },
    "databricksWorkspaceUrl": {
      "value": "YOUR_DATABRICKS_WORKSPACE_URL"
    }
  }
}
```

### **2. Set GitHub Repository Secrets**

Add these secrets in your GitHub repository:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `DATABRICKS_WORKSPACE_URL` | Your Databricks workspace URL | `https://your-workspace.cloud.databricks.com` |
| `DATABRICKS_TOKEN` | Personal Access Token | `dapi-1234567890abcdef...` |

### **3. Generate Databricks Personal Access Token**

1. **Login to your Databricks workspace**
2. **Click your profile** (top-right corner)
3. **Select "User Settings"**
4. **Go to "Access Tokens"** tab
5. **Click "Generate New Token"**
6. **Set description**: "Credit Risk Analysis App"
7. **Set lifetime**: 90 days (or longer)
8. **Copy the token** - you won't see it again!

## 🔧 **Infrastructure Changes Made**

### **Removed:**
- ❌ Azure Databricks workspace resource
- ❌ Managed resource group for Databricks
- ❌ Databricks-specific networking rules

### **Added:**
- ✅ External Databricks workspace URL parameter
- ✅ Databricks token storage in Key Vault
- ✅ App Service environment variables for Databricks connection
- ✅ GitHub Actions integration with external workspace

### **Updated App Service Settings:**
```bash
DATABRICKS_WORKSPACE_URL="your-workspace-url"
DATABRICKS_TOKEN_SECRET_NAME="databricks-token"
AZURE_KEY_VAULT_URL="https://your-keyvault.vault.azure.net/"
```

## 🚀 **Deployment Steps**

### **Step 1: Update Configuration**
```bash
# 1. Update the parameters file with your Databricks workspace URL
nano infra/main.parameters.json

# 2. Deploy the updated infrastructure
az deployment group create \
  --resource-group rg-credit-risk-analysis-prod-ukwest \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json \
  --parameters databricksToken="YOUR_DATABRICKS_TOKEN"
```

### **Step 2: Configure GitHub Secrets**
1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add the required secrets (listed above)

### **Step 3: Deploy via GitHub Actions**
```bash
# Push your changes to trigger deployment
git add .
git commit -m "Configure external Databricks workspace"
git push origin main
```

## 🔍 **Verification**

After deployment, verify the connection:

1. **Check App Service Configuration:**
   ```bash
   az webapp config appsettings list \
     --name credit-risk-analysis-prod-app-25h2ya \
     --resource-group rg-credit-risk-analysis-prod-ukwest
   ```

2. **Test Databricks Connection:**
   - Your app will retrieve the token from Key Vault
   - Use the Databricks REST API to verify connectivity
   - Check application logs for any connection issues

## 💡 **Next Steps**

1. **Provide your Databricks workspace details**
2. **Generate and securely store your access token**
3. **Update the parameters file**
4. **Deploy the updated infrastructure**
5. **Configure GitHub repository secrets**
6. **Test the application**

## 🆘 **Troubleshooting**

### **Common Issues:**
- **Token expired**: Generate a new token with longer lifetime
- **Workspace URL incorrect**: Ensure it includes https:// and correct domain
- **Permission denied**: Verify token has required permissions
- **Network issues**: Check if workspace allows external connections

### **Support:**
If you need help with any of these steps, please provide:
- Your Databricks workspace URL
- Preferred authentication method
- Any error messages you encounter
