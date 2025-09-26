# Azure Configuration Quick Reference

## Deployment Commands Cheat Sheet

### Essential Commands (Copy-Paste Ready)

#### Set Correct Startup Command
```bash
az webapp config set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"
```

#### Enable Application Logging
```bash
az webapp log config \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --application-logging filesystem
```

#### Deploy Package
```bash
az webapp deploy \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --src-path deploy.zip \
  --type zip
```

#### Restart Application
```bash
az webapp restart \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

### Verification Commands

#### Check Startup Configuration
```bash
az webapp config show \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --query "appCommandLine"
```

#### Test Application Response
```bash
curl -I https://credit-risk-clean-app.azurewebsites.net
```

#### View Live Logs
```bash
az webapp log tail \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

#### Check App Service Plan Tier
```bash
az appservice plan show \
  --name <your-app-service-plan> \
  --resource-group rg-credit-risk-clean \
  --query "sku"
```

## Configuration Values

### Working Configuration
| Setting | Value | Purpose |
|---------|--------|---------|
| **Startup Command** | `gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application` | WSGI entry point |
| **Python Version** | 3.11 | Runtime version |
| **App Service Tier** | B3 (7GB RAM, 2 vCPUs) | Sufficient for ML workloads |
| **Port** | 8000 | Gunicorn binding port |
| **Timeout** | 600 seconds | Startup timeout |
| **Workers** | 1 | Memory-efficient for B3 tier |
| **WSGI Target** | `startup:application` | Entry point module:object |

### Environment Variables (Optional)
```bash
WEBSITES_PORT=8000
WEBSITES_CONTAINER_START_TIME_LIMIT=900
PYTHON_VERSION=3.11
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
```

## Resource Requirements

### Minimum Requirements
- **Tier**: B3 (Basic 3)
- **RAM**: 7GB
- **vCPUs**: 2
- **Storage**: 10GB
- **Python**: 3.11

### Scaling Configuration
```bash
# Upgrade to B3 if needed
az appservice plan update \
  --name <your-app-service-plan> \
  --resource-group rg-credit-risk-clean \
  --sku B3
```

## File Structure Validation

### Required Files Checklist
- [ ] `startup.py` - WSGI entry point
- [ ] `main.py` - Application factory
- [ ] `requirements.txt` - Python dependencies  
- [ ] `app/__init__.py` - Main package
- [ ] `app/flask_main.py` - Flask application
- [ ] `app/agents/` - ML agent modules
- [ ] `data/` - Data files and configurations

### startup.py Template
```python
import sys
import os
import logging

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from main import create_application
    application = create_application()
    
    if __name__ == "__main__":
        application.run(host='0.0.0.0', port=8000)
        
except Exception as e:
    logging.error(f"Failed to create application: {str(e)}")
    raise
```

## Clean Deployment Package

### Create Deployment ZIP
```bash
zip -r deploy.zip . \
  -x "*.git*" "*__pycache__*" "*.DS_Store*" \
     "*node_modules*" "*.pyc" "*.venv*" \
     ".venv/*" "*logs/*" "*deploy.zip*"
```

### What to Include
- ✅ Application source code (`app/`)
- ✅ Configuration files (`config/`)
- ✅ Data files (`data/`)
- ✅ Templates and static files
- ✅ `startup.py` and `main.py`
- ✅ `requirements.txt`

### What to Exclude
- ❌ `.venv/` (virtual environment)
- ❌ `__pycache__/` (Python cache)
- ❌ `.git/` (Git repository)
- ❌ `logs/` (log files)
- ❌ `*.pyc` (compiled Python files)
- ❌ `.DS_Store` (macOS files)

## Troubleshooting Shortcuts

### Container Won't Start
```bash
# Check current startup command
az webapp config show \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --query "appCommandLine"

# Fix startup command
az webapp config set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"

# Restart
az webapp restart \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

### High Memory Usage
```bash
# Check current tier
az appservice plan show \
  --name <plan-name> \
  --resource-group rg-credit-risk-clean \
  --query "sku.name"

# Upgrade to B3 if needed
az appservice plan update \
  --name <plan-name> \
  --resource-group rg-credit-risk-clean \
  --sku B3
```

### Deployment Fails
```bash
# Manual deployment
az webapp deploy \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --src-path deploy.zip \
  --type zip

# Check deployment status
az webapp deployment list \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

## Success Verification Checklist

### Immediate Checks (30 seconds)
- [ ] `curl -I https://credit-risk-clean-app.azurewebsites.net` returns 200
- [ ] Response headers show `Server: gunicorn`
- [ ] No immediate error pages

### Configuration Checks (1 minute)  
- [ ] Startup command correctly set to `startup:application`
- [ ] Application logging enabled
- [ ] B3 tier or higher configured

### Functional Checks (2-3 minutes)
- [ ] Application homepage loads properly
- [ ] No container restart loops in logs
- [ ] Memory usage under 80% after startup
- [ ] All static files loading correctly

### Health Check Commands
```bash
# All-in-one health check
echo "=== Configuration Check ===" && \
az webapp config show --name credit-risk-clean-app --resource-group rg-credit-risk-clean --query "appCommandLine" && \
echo "=== HTTP Check ===" && \
curl -I https://credit-risk-clean-app.azurewebsites.net && \
echo "=== Deployment Status ===" && \
az webapp show --name credit-risk-clean-app --resource-group rg-credit-risk-clean --query "state"
```

## Emergency Recovery

### Quick Fix (If App is Down)
```bash
# 1. Restart immediately
az webapp restart --name credit-risk-clean-app --resource-group rg-credit-risk-clean

# 2. Fix startup command
az webapp config set --name credit-risk-clean-app --resource-group rg-credit-risk-clean --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"

# 3. Wait 2-3 minutes for startup
sleep 180

# 4. Test
curl -I https://credit-risk-clean-app.azurewebsites.net
```

### Rollback Strategy
1. Keep previous working `deploy.zip`
2. Deploy previous package: `az webapp deploy --src-path deploy-backup.zip`
3. Verify startup command after rollback
4. Test functionality

---
*Quick Reference - September 26, 2025*  
*Keep this handy for future deployments*