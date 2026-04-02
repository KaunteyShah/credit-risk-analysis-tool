# GitHub Actions Deployment Guide

## Working Deployment Configuration (Tested September 26, 2025)

This document provides the **proven working approach** for deploying the Credit Risk Analysis Flask application to Azure App Service via GitHub Actions.

## Key Success Factors

### 1. **Use Kudu ZIP API (NOT azure/webapps-deploy@v2)**
- The official `azure/webapps-deploy@v2` action has known issues
- Direct Kudu ZIP API deployment via curl works reliably
- Uses publish profile authentication (secure and reliable)

### 2. **Critical Post-Deployment Manual Step**
After GitHub Actions deployment, **always run this command manually**:
```bash
az webapp config set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"
```

### 3. **Clean Deployment Package**
Exclude these directories/files from deployment ZIP:
- `.venv/*` (virtual environment)
- `*__pycache__*` (Python cache)
- `*.git*` (Git files)  
- `*logs/*` (log files)
- `*.pyc` (compiled Python)

## Working GitHub Actions Workflow

### Essential Environment Variables
```yaml
env:
  AZURE_RESOURCE_GROUP: rg-credit-risk-clean
  AZURE_LOCATION: ukwest
  PYTHON_VERSION: '3.11'
  APP_SERVICE_NAME: credit-risk-clean-app
```

### Key Deployment Step (Working)
```yaml
- name: Deploy using Kudu ZIP API
  run: |
    echo "🚀 Deploying using Kudu ZIP API (PROVEN WORKING METHOD)"
    
    # Create clean deployment package
    zip -r deploy.zip . \
      -x "*.git*" "*.github*" "*node_modules*" "*.DS_Store*" \
         "*__pycache__*" "*.pyc" "*.venv*" ".venv/*" "*logs/*" "*deploy.zip*"
    
    # Extract credentials from publish profile
    PROFILE_XML='${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}'
    USERNAME=$(echo "$PROFILE_XML" | grep 'publishMethod="ZipDeploy"' | sed 's/.*userName="\([^"]*\)".*/\1/')
    PASSWORD=$(echo "$PROFILE_XML" | grep 'publishMethod="ZipDeploy"' | sed 's/.*userPWD="\([^"]*\)".*/\1/')
    
    # Deploy via Kudu ZIP API
    curl -X POST \
      -u "$USERNAME:$PASSWORD" \
      --data-binary @deploy.zip \
      -H "Content-Type: application/zip" \
      "https://${{ env.APP_SERVICE_NAME }}.scm.azurewebsites.net/api/zipdeploy?isAsync=true"
    
    echo "✅ Deployment completed"
    echo "⚠️  MANUAL STEP REQUIRED:"
    echo "   az webapp config set --name ${{ env.APP_SERVICE_NAME }} --resource-group ${{ env.AZURE_RESOURCE_GROUP }} --startup-file 'gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application'"
```

## Required GitHub Secrets

### AZURE_WEBAPP_PUBLISH_PROFILE
1. **Get Publish Profile**:
   ```bash
   az webapp deployment list-publishing-profiles \
     --name credit-risk-clean-app \
     --resource-group rg-credit-risk-clean \
     --xml
   ```

2. **Add to GitHub Secrets**:
   - Go to Repository → Settings → Secrets and variables → Actions
   - Add new secret: `AZURE_WEBAPP_PUBLISH_PROFILE`
   - Paste the entire XML content

## Post-Deployment Checklist

### 1. Set Startup Command (CRITICAL)
```bash
az webapp config set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"
```

### 2. Enable Application Logging
```bash
az webapp log config \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --application-logging filesystem
```

### 3. Verify Deployment
```bash
# Check startup command
az webapp config show \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --query "appCommandLine"

# Test HTTP response
curl -I https://credit-risk-clean-app.azurewebsites.net

# Check logs
az webapp log tail \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

## Common Issues and Solutions

### Issue: "Container couldn't be started"
**Cause**: Wrong startup command (using `main:app` instead of `startup:application`)
**Solution**: Run the manual startup command above

### Issue: "Package deployment using ZIP Deploy failed"  
**Cause**: Using `azure/webapps-deploy@v2` action
**Solution**: Use Kudu ZIP API method shown above

### Issue: "Another deployment is in progress"
**Cause**: Large deployment package or concurrent deployments
**Solution**: 
- Wait for current deployment to finish
- Use clean deployment package (exclude .venv)
- Use concurrency control in workflow

### Issue: Application takes too long to start
**Cause**: Insufficient resources
**Solution**: Ensure B3 tier (7GB RAM, 2 vCPUs)

## Workflow Optimization

### Concurrency Control
```yaml
concurrency:
  group: azure-deployment-${{ github.ref }}
  cancel-in-progress: false
```

### Deployment Timing
- Package creation: ~30 seconds
- Kudu deployment: ~2-3 minutes
- Container startup: ~3-5 minutes (ML libraries loading)
- Total deployment time: ~6-8 minutes

## Manual Deployment Alternative

If GitHub Actions fails, use manual deployment:

```bash
# 1. Create clean package locally
zip -r deploy.zip . \
  -x "*.git*" "*__pycache__*" "*.DS_Store*" \
     "*node_modules*" "*.pyc" "*.venv*" \
     ".venv/*" "*logs/*" "*deploy.zip*"

# 2. Deploy via Azure CLI
az webapp deploy \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --src-path deploy.zip \
  --type zip

# 3. Set startup command
az webapp config set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"

# 4. Restart app
az webapp restart \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

## Testing Deployment

### Success Indicators
- ✅ GitHub Actions workflow completes without errors
- ✅ HTTP 200 response from application URL
- ✅ `Server: gunicorn` header in response
- ✅ HTML content returned (not error page)
- ✅ Container logs show successful startup
- ✅ Startup command set to `startup:application`

### Verification Commands
```bash
# Quick health check
curl -I https://credit-risk-clean-app.azurewebsites.net

# Detailed response check  
curl -s https://credit-risk-clean-app.azurewebsites.net | head -10

# Configuration verification
az webapp config show \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --query "{startupFile: appCommandLine, pythonVersion: linuxFxVersion}"
```

## Troubleshooting Resources

1. **GitHub Actions Logs**: Check workflow run details
2. **Azure App Service Logs**: `az webapp log tail`  
3. **Kudu Console**: `https://credit-risk-clean-app.scm.azurewebsites.net`
4. **Azure Portal**: App Service → Deployment Center
5. **This Repository**: See `docs/AZURE_DEPLOYMENT_TROUBLESHOOTING.md`

---
*Last Updated: September 26, 2025*  
*Status: Production-tested and working*