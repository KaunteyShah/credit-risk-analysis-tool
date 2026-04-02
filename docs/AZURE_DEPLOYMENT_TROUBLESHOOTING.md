# Azure App Service Deployment Troubleshooting Guide

## Overview
This document provides comprehensive troubleshooting steps for deploying the Credit Risk Analysis Flask application to Azure App Service, based on resolved production issues.

## Common Deployment Issues & Solutions

### 1. Container Startup Failures (HTTP 503/504 Errors)

#### **Problem**: Container exits with "Unable to locate module or package"
```
Container credit-risk-clean-app_0_xxx couldn't be started
Site's appCommandLine: gunicorn --bind=0.0.0.0:8000 --timeout 600 main:app
[ERROR] Exception in worker process
ModuleNotFoundError: No module named 'main'
```

#### **Root Cause**: Wrong WSGI target in startup command
- Azure was using `main:app` instead of `startup:application`
- Configuration was reverting to cached/default values

#### **Solution**:
1. **Force update startup command via Azure CLI**:
   ```bash
   az webapp config set \
     --name credit-risk-clean-app \
     --resource-group rg-credit-risk-clean \
     --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"
   ```

2. **Verify the configuration**:
   ```bash
   az webapp config show \
     --name credit-risk-clean-app \
     --resource-group rg-credit-risk-clean \
     --query "appCommandLine"
   ```

3. **Restart the app**:
   ```bash
   az webapp restart \
     --name credit-risk-clean-app \
     --resource-group rg-credit-risk-clean
   ```

### 2. Memory Constraints (High CPU/Memory Usage)

#### **Problem**: Application fails to start due to insufficient memory
```
High CPU Usage 86.9%
Container didn't respond to HTTP pings on port: 8000
```

#### **Root Cause**: B1 tier (1.75GB RAM) insufficient for ML application startup

#### **Solution**:
1. **Upgrade to B3 tier** (7GB RAM, 2 vCPUs):
   ```bash
   az appservice plan update \
     --name your-app-service-plan \
     --resource-group rg-credit-risk-clean \
     --sku B3
   ```

2. **Verify the upgrade**:
   ```bash
   az webapp show \
     --name credit-risk-clean-app \
     --resource-group rg-credit-risk-clean \
     --query "appServicePlanId"
   ```

### 3. GitHub Actions Deployment Issues

#### **Problem**: `azure/webapps-deploy@v2` action fails
```
Error: Package deployment using ZIP Deploy failed
```

#### **Root Cause**: Known issues with the official Azure deployment action

#### **Solution**: Use Kudu ZIP API deployment instead
```yaml
- name: Deploy to Azure App Service
  run: |
    az webapp deploy \
      --name credit-risk-clean-app \
      --resource-group rg-credit-risk-clean \
      --src-path deploy.zip \
      --type zip
```

### 4. Large Deployment Packages

#### **Problem**: Deployment timeout due to large package size
```
Another deployment is in progress. Please wait...
```

#### **Solution**: Create clean deployment package
```bash
# Create deployment package excluding unnecessary files
zip -r deploy.zip . \
  -x "*.git*" "*__pycache__*" "*.DS_Store*" \
     "*node_modules*" "*.pyc" "*.venv*" \
     ".venv/*" "*logs/*" "*deploy.zip*"
```

## File Structure Requirements

### Essential Files for Deployment
```
/
├── startup.py              # WSGI entry point (CRITICAL)
├── main.py                 # Application factory
├── requirements.txt        # Dependencies
├── app/                    # Main application package
│   ├── __init__.py
│   ├── flask_main.py      # Flask app creation
│   ├── agents/            # ML agents
│   ├── utils/             # Utilities
│   └── templates/         # HTML templates
├── data/                  # Data files
└── config/               # Configuration files
```

### Critical File: `startup.py`
```python
import sys
import os
import logging

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from main import create_application
    
    # Create the Flask application
    application = create_application()
    
    if __name__ == "__main__":
        application.run(host='0.0.0.0', port=8000)
        
except Exception as e:
    logging.error(f"Failed to create application: {str(e)}")
    raise
```

## Deployment Verification Steps

### 1. Pre-Deployment Checks
```bash
# Test local startup
python3 startup.py

# Verify import paths
python3 -c "from startup import application; print('SUCCESS: Application imported')"

# Check requirements
pip install -r requirements.txt
```

### 2. Post-Deployment Verification
```bash
# Check HTTP response
curl -I http://credit-risk-clean-app.azurewebsites.net

# Verify startup command
az webapp config show \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --query "appCommandLine"

# Check application logs
az webapp log tail \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

### 3. Success Indicators
- ✅ HTTP 200 response
- ✅ `Server: gunicorn` header present
- ✅ HTML content returned
- ✅ No container restart loops
- ✅ Startup command shows `startup:application`

## Resource Requirements

### Recommended Configuration
- **Tier**: B3 (7GB RAM, 2 vCPUs) minimum
- **Python Version**: 3.11
- **Startup Timeout**: 600 seconds
- **Workers**: 1 (for memory efficiency)
- **Logging**: Application logging enabled

### Command Templates
```bash
# Set startup command
az webapp config set \
  --name <APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"

# Enable logging
az webapp log config \
  --name <APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --application-logging filesystem

# Deploy package
az webapp deploy \
  --name <APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --src-path deploy.zip \
  --type zip
```

## Prevention Checklist

### Before Deployment
- [ ] Verify `startup.py` exists and imports correctly
- [ ] Test application locally
- [ ] Ensure B3 tier or higher
- [ ] Create clean deployment package
- [ ] Set correct startup command

### After Deployment
- [ ] Verify HTTP 200 response
- [ ] Check container logs for errors
- [ ] Confirm startup command configuration
- [ ] Test application functionality
- [ ] Monitor memory/CPU usage

## Emergency Recovery Steps

If deployment fails:

1. **Immediate Actions**:
   ```bash
   # Restart the app
   az webapp restart --name <APP_NAME> --resource-group <RESOURCE_GROUP>
   
   # Check logs
   az webapp log tail --name <APP_NAME> --resource-group <RESOURCE_GROUP>
   ```

2. **Configuration Reset**:
   ```bash
   # Reset startup command
   az webapp config set \
     --name <APP_NAME> \
     --resource-group <RESOURCE_GROUP> \
     --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"
   ```

3. **Rollback Strategy**:
   - Keep previous working deployment ZIP
   - Use Azure deployment slots for zero-downtime rollback
   - Have backup of working configuration

## Contact Information

For deployment issues:
- Check this document first
- Review Azure App Service logs
- Verify GitHub Actions workflow logs
- Confirm resource tier and configuration

---
*Last Updated: September 26, 2025*
*Based on: Production deployment troubleshooting session*