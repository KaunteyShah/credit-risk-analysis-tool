# 🔐 GitHub Actions Setup Guide

## 📋 **Required GitHub Secrets**

You need to add these secrets to your GitHub repository:

### **Step 1: Create Azure Credentials Secret**

Since we can't create a service principal, we'll use your current login. Run this command to get your credentials:

```bash
az ad signed-in-user show --query objectId --output tsv
```

Then create a JSON credential like this:

```json
{
  "clientId": "YOUR_CLIENT_ID",
  "clientSecret": "YOUR_CLIENT_SECRET", 
  "subscriptionId": "c09f5850-099b-4458-ac6d-f31d69f68ae7",
  "tenantId": "5b973f99-77df-4beb-b27d-aa0c70b8482c"
}
```

## 🚨 **TEMPORARY WORKAROUND** 

Since service principal creation is restricted, let's use an alternative approach:

### **Option 1: Request IT Support** ⭐ RECOMMENDED

Contact your EY IT team to:
1. Create service principal: `github-actions-credit-risk`
2. Assign "Contributor" role to subscription: `c09f5850-099b-4458-ac6d-f31d69f68ae7`
3. Provide the credentials for GitHub Actions

### **Option 2: Use Azure DevOps** 

We can set up Azure DevOps pipelines instead, which might have fewer restrictions.

### **Option 3: Manual Deployment with GitHub** 

For now, let's proceed with manual deployment triggered by GitHub Actions.

---

## 🎯 **Immediate Action Required**

Please add these GitHub repository secrets (Settings → Secrets and variables → Actions):

| Secret Name | Value | Required |
|-------------|-------|----------|
| `AZURE_SUBSCRIPTION_ID` | `c09f5850-099b-4458-ac6d-f31d69f68ae7` | ✅ Yes |
| `AZURE_TENANT_ID` | `5b973f99-77df-4beb-b27d-aa0c70b8482c` | ✅ Yes |
| `OPENAI_API_KEY` | `sk-your-openai-key` | 🔄 Optional |
| `COMPANIES_HOUSE_API_KEY` | `your-companies-house-key` | 🔄 Optional |
| `DATABRICKS_TOKEN` | `dapi-your-databricks-token` | 🔄 After setup |

---

## 🚀 **Ready to proceed?**

1. Add the secrets above to GitHub
2. Push your code to trigger the workflow
3. Monitor the deployment in GitHub Actions

The infrastructure is already deployed, so the workflow will just deploy your application!
