# GitHub Secrets Setup for Azure Deployment

## Required Secret: AZURE_CREDENTIALS

To deploy your Credit Risk Analysis app to Azure via GitHub Actions, you need to configure the `AZURE_CREDENTIALS` secret.

### 1. Create Azure Service Principal

Run this command in Azure CLI to create a service principal:

```bash
az ad sp create-for-rbac --name "credit-risk-github-actions" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/rg-credit-risk-clean \
  --sdk-auth
```

This will output JSON like:
```json
{
  "clientId": "12345678-1234-1234-1234-123456789012",
  "clientSecret": "your-client-secret-here",
  "subscriptionId": "87654321-4321-4321-4321-210987654321",
  "tenantId": "abcdef12-3456-7890-abcd-ef1234567890"
}
```

### 2. Add Secret to GitHub Repository

1. Go to your GitHub repository: `https://github.com/KaunteyShah/credit-risk-analysis-tool`
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `AZURE_CREDENTIALS`
5. Value: Paste the entire JSON output from step 1
6. Click **Add secret**

### 3. Verify Your Azure Resources

Ensure these resources exist in your Azure subscription:

- **Resource Group**: `rg-credit-risk-clean` (UK West)
- **App Service**: `credit-risk-clean-app` (or update the name in the workflow file)
- **App Service Plan**: B3 tier or higher (recommended for ML workloads)

### 4. Test Deployment

Once the secret is configured:

1. Push to the `main` branch
2. Check **Actions** tab in GitHub to monitor deployment
3. The workflow will authenticate with Azure using the service principal
4. Your app will be deployed to `https://credit-risk-clean-app.azurewebsites.net`

## Troubleshooting

### Authentication Errors
- Verify the service principal has `Contributor` role on the resource group
- Check that all JSON fields (clientId, clientSecret, tenantId) are correct
- Ensure the subscription ID matches your Azure subscription

### Deployment Errors
- Check App Service logs: `az webapp log tail --name credit-risk-clean-app --resource-group rg-credit-risk-clean`
- Verify the App Service plan has sufficient resources (B3 or higher recommended)
- Ensure Python 3.11 runtime is configured on the App Service

## Security Notes

- The service principal only has access to the specified resource group
- Rotate the client secret periodically for security
- Never commit Azure credentials to your repository - always use GitHub Secrets