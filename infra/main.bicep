// Azure Infrastructure for Credit Risk Analysis
// Creates all required Azure resources

@description('Environment name (dev, staging, prod)')
param environmentName string = 'prod'

@description('Application name')
param applicationName string = 'credit-risk-analysis'

@description('Azure region for deployment')
param location string = resourceGroup().location

@description('kauntey.shah@uk.ey.com')
param adminEmail string

@description('External Databricks workspace URL (e.g., https://your-workspace.cloud.databricks.com)')
param databricksWorkspaceUrl string = ''

@description('Databricks username for authentication')
param databricksUsername string = ''

@description('Databricks password for authentication')
@secure()
param databricksPassword string = ''

// Variables
var resourcePrefix = '${applicationName}-${environmentName}'
var resourceToken = substring(uniqueString(resourceGroup().id), 0, 6)
var shortPrefix = 'cra${environmentName}' // Shorter prefix for resources with strict naming

// Resource Group is created outside of this template

// Key Vault for storing secrets
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${shortPrefix}kv${resourceToken}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []  // Will be updated after App Service is created
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
  tags: {
    Environment: environmentName
    Application: applicationName
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resourcePrefix}-ai-${resourceToken}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: 30
  }
  tags: {
    Environment: environmentName
    Application: applicationName
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${resourcePrefix}-asp-${resourceToken}'
  location: location
  sku: {
    name: environmentName == 'prod' ? 'P1V2' : 'B1'
    tier: environmentName == 'prod' ? 'PremiumV2' : 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
  tags: {
    Environment: environmentName
    Application: applicationName
  }
}

// App Service
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: '${resourcePrefix}-app-${resourceToken}'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'python -m streamlit run app/core/streamlit_app_langgraph_viz.py --server.port=8000 --server.address=0.0.0.0'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'AZURE_KEY_VAULT_URL'
          value: keyVault.properties.vaultUri
        }
        {
          name: 'ENVIRONMENT'
          value: environmentName
        }
        {
          name: 'DATABRICKS_WORKSPACE_URL'
          value: databricksWorkspaceUrl
        }
        {
          name: 'DATABRICKS_USERNAME_SECRET_NAME'
          value: 'databricks-username'
        }
        {
          name: 'DATABRICKS_PASSWORD_SECRET_NAME'
          value: 'databricks-password'
        }
      ]
    }
    httpsOnly: true
    clientAffinityEnabled: false
  }
  tags: {
    Environment: environmentName
    Application: applicationName
  }
}

// Azure Databricks Workspace - REMOVED (Using existing external workspace)
// resource databricksWorkspace 'Microsoft.Databricks/workspaces@2023-02-01' = {
//   name: '${resourcePrefix}-dbw-${resourceToken}'
//   location: location
//   sku: {
//     name: 'premium'
//   }
//   properties: {
//     managedResourceGroupId: subscriptionResourceId('Microsoft.Resources/resourceGroups', '${resourcePrefix}-dbw-managed-rg-${resourceToken}')
//     parameters: {
//       enableNoPublicIp: {
//         value: false
//       }
//       // Premium tier features
//       requireInfrastructureEncryption: {
//         value: false
//       }
//       storageAccountName: {
//         value: ''
//       }
//       storageAccountSkuName: {
//         value: 'Standard_GRS'
//       }
//     }
//     // Enable public network access for ease of use (can be restricted later)
//     publicNetworkAccess: 'Enabled'
//     // Required for premium workspaces
//     requiredNsgRules: 'AllRules'
//   }
//   tags: {
//     Environment: environmentName
//     Application: applicationName
//   }
// }

// Container Registry (Optional - for custom Docker images)
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${replace(resourcePrefix, '-', '')}acr${resourceToken}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
  tags: {
    Environment: environmentName
    Application: applicationName
  }
}

// Key Vault Access Policy - configured after App Service is created
resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  parent: keyVault
  name: 'add'
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: appService.identity.principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}

// Databricks Credentials Secrets (if provided)
resource databricksUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (databricksUsername != '') {
  parent: keyVault
  name: 'databricks-username'
  properties: {
    value: databricksUsername
    contentType: 'Databricks Username'
  }
  dependsOn: [
    keyVaultAccessPolicy
  ]
}

resource databricksPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (databricksPassword != '') {
  parent: keyVault
  name: 'databricks-password'
  properties: {
    value: databricksPassword
    contentType: 'Databricks Password'
  }
  dependsOn: [
    keyVaultAccessPolicy
  ]
}

// Outputs
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
// databricksWorkspaceUrl removed - using external workspace
output keyVaultName string = keyVault.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output applicationInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output resourceGroupName string = resourceGroup().name
