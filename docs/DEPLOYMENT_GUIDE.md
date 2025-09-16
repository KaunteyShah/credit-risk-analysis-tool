# 🚀 Azure Deployment Guide
## Credit Risk Analysis - Step-by-Step Setup

### Prerequisites Checklist ✅

Before we begin, you'll need:

1. **Azure Subscription** with sufficient permissions
2. **GitHub Account** with repository access
3. **API Keys** (we'll configure these as secrets)
4. **Azure CLI** installed locally (for initial setup)

---

## 📋 **STEP-BY-STEP PROCESS**

### **Step 1: Azure Service Principal Setup**

I need you to create an Azure service principal for GitHub Actions:

```bash
# Login to Azure CLI
az login

# Create service principal
az ad sp create-for-rbac \
  --name "github-actions-credit-risk" \
  --role "Contributor" \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID \
  --sdk-auth
```

**📝 Copy the JSON output** - you'll need this for GitHub secrets!

### **Step 2: GitHub Repository Secrets**

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AZURE_CREDENTIALS` | JSON from Step 1 | Azure service principal credentials |
| `ADMIN_EMAIL` | your-email@example.com | Your email for notifications |
| `OPENAI_API_KEY` | sk-your-key | OpenAI API key (optional initially) |
| `COMPANIES_HOUSE_API_KEY` | your-key | Companies House API key (optional initially) |

### **Step 3: Update Configuration Files**

Update these files with your specific values:

1. **`infra/main.parameters.json`**:
   ```json
   {
     "parameters": {
       "adminEmail": {
         "value": "YOUR_EMAIL_HERE"
       },
       "location": {
         "value": "East US"  // or your preferred region
       }
     }
   }
   ```

### **Step 4: Deploy Infrastructure**

Commit and push your changes to trigger the GitHub Actions workflow:

```bash
git add .
git commit -m "Configure Azure deployment"
git push origin main
```

**🎯 This will automatically:**
- Create Azure Resource Group
- Deploy Databricks workspace
- Create App Service and Key Vault
- Deploy your application

### **Step 5: Databricks Configuration** 

After deployment, you'll need to manually configure Databricks:

1. **Access your Databricks workspace** (URL provided in deployment output)
2. **Generate Personal Access Token**:
   - User Settings → Developer → Access Tokens → Generate New Token
3. **Create a compute cluster**:
   - Compute → Create Cluster
   - Runtime: 13.3 LTS (includes Apache Spark 3.4.1, Scala 2.12)
   - Node type: Standard_DS3_v2 (for cost optimization)
4. **Upload sample data**:
   - Data → Create Table → Upload File
   - Upload `data/Sample_data2.csv`

### **Step 6: Update GitHub Secrets with Databricks Info**

Add these additional secrets:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `DATABRICKS_TOKEN` | dapi123... | From Databricks User Settings |
| `DATABRICKS_CLUSTER_ID` | 1234-567890-abcde | From Databricks Compute page |

### **Step 7: Redeploy Application**

Trigger a new deployment to update with Databricks credentials:

```bash
git commit --allow-empty -m "Update Databricks configuration"
git push origin main
```

---

## 🎯 **WHAT YOU NEED TO PROVIDE ME:**

### **Immediate Actions Required:**

1. **Your Azure Subscription ID**
   ```bash
   az account show --query id --output tsv
   ```

2. **Your preferred Azure region** (e.g., "East US", "West Europe")

3. **Your email address** for notifications

4. **Your OpenAI API key** (if you have one)

5. **Your Companies House API key** (if you have one)

### **After Deployment:**

6. **Databricks Personal Access Token** (generated after workspace creation)

7. **Databricks Cluster ID** (created after workspace setup)

---

## 📊 **Expected Results:**

After successful deployment, you'll have:

- ✅ **Azure Resource Group**: `rg-credit-risk-analysis-prod`
- ✅ **Azure App Service**: Hosting your Streamlit application
- ✅ **Azure Databricks**: Data processing workspace
- ✅ **Azure Key Vault**: Secure secret storage
- ✅ **Application Insights**: Monitoring and telemetry
- ✅ **GitHub Actions**: Automated CI/CD pipeline

## 🚀 **Ready to Start?**

Please provide me with the information listed above, and I'll help you configure the deployment!
