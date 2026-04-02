# Deployment Process Documentation Summary

## Overview

This document provides a complete summary of the deployment process, troubleshooting steps, and configuration for the Credit Risk Analysis Flask application on Azure App Service.

## 📁 Documentation Structure

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[AZURE_DEPLOYMENT_TROUBLESHOOTING.md](AZURE_DEPLOYMENT_TROUBLESHOOTING.md)** | Complete troubleshooting guide | When deployment fails or containers won't start |
| **[GITHUB_ACTIONS_DEPLOYMENT_GUIDE.md](GITHUB_ACTIONS_DEPLOYMENT_GUIDE.md)** | CI/CD pipeline configuration | Setting up automated deployments |
| **[AZURE_CONFIG_QUICK_REFERENCE.md](AZURE_CONFIG_QUICK_REFERENCE.md)** | Copy-paste commands and configs | Quick fixes and verification |

## 🎯 Key Success Factors (Never Forget These)

### 1. **Correct Startup Command** (Most Critical)
```bash
# ALWAYS run this after deployment
az webapp config set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"
```

**Why Critical**: Azure often reverts to `main:app` which causes import errors. Always use `startup:application`.

### 2. **Use Kudu ZIP API (Not azure/webapps-deploy@v2)**
```bash
# Working deployment method
az webapp deploy \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --src-path deploy.zip \
  --type zip
```

**Why Critical**: The official GitHub Action has known issues. Direct Kudu API works reliably.

### 3. **B3 Tier Minimum** 
```bash
# Ensure sufficient resources
az appservice plan update \
  --name <plan-name> \
  --resource-group rg-credit-risk-clean \
  --sku B3
```

**Why Critical**: ML application needs 7GB RAM for startup. B1 (1.75GB) causes memory failures.

### 4. **Clean Deployment Package**
```bash
# Exclude virtual environment and cache
zip -r deploy.zip . \
  -x "*.git*" "*__pycache__*" "*.venv*" ".venv/*" "*logs/*"
```

**Why Critical**: Including .venv causes deployment timeouts and conflicts.

## 🚨 Emergency Recovery Process

If the application is down, follow these steps in order:

### Step 1: Quick Restart (30 seconds)
```bash
az webapp restart \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

### Step 2: Fix Startup Command (30 seconds)
```bash
az webapp config set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 startup:application"
```

### Step 3: Wait and Verify (3 minutes)
```bash
# Wait for startup (ML libraries take time)
sleep 180

# Test application
curl -I https://credit-risk-clean-app.azurewebsites.net
```

### Step 4: Check Logs if Still Failing
```bash
az webapp log tail \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

## 📋 Pre-Deployment Checklist

Before any deployment:

- [ ] **startup.py exists** and imports correctly
- [ ] **Test locally**: `python startup.py` works
- [ ] **Clean package**: No .venv or __pycache__ included  
- [ ] **B3 tier**: Sufficient memory for ML workloads
- [ ] **Backup**: Keep previous working deploy.zip

## 📋 Post-Deployment Checklist

After every deployment:

- [ ] **Set startup command**: Run the critical command above
- [ ] **Test HTTP**: `curl -I https://credit-risk-clean-app.azurewebsites.net`
- [ ] **Verify config**: Check appCommandLine shows `startup:application`
- [ ] **Wait for startup**: Allow 3-5 minutes for ML libraries to load
- [ ] **Check logs**: Ensure no errors in application logs

## 🔧 Common Failure Patterns

### Pattern 1: Import Errors
**Symptoms**: "No module named 'main'" in logs
**Root Cause**: Wrong startup command (`main:app` instead of `startup:application`)  
**Solution**: Run the critical startup command

### Pattern 2: Memory Issues  
**Symptoms**: High CPU usage, container exits, HTTP 504
**Root Cause**: Insufficient memory (B1 tier only has 1.75GB)
**Solution**: Upgrade to B3 tier (7GB RAM)

### Pattern 3: Deployment Timeouts
**Symptoms**: "Another deployment in progress", large ZIP files
**Root Cause**: Including .venv folder in deployment package
**Solution**: Create clean package excluding virtual environment

### Pattern 4: Configuration Reversion
**Symptoms**: Startup command reverts to `main:app` after deployment
**Root Cause**: Azure caching or default configuration override
**Solution**: Always manually set startup command after deployment

## 🎯 Success Indicators

### Immediate (30 seconds)
- ✅ HTTP 200 response
- ✅ `Server: gunicorn` header
- ✅ HTML content (not error page)

### Configuration (1 minute)
- ✅ Startup command shows `startup:application`
- ✅ Application logging enabled
- ✅ B3 tier active

### Functional (3-5 minutes)
- ✅ Homepage loads completely
- ✅ No container restart loops
- ✅ Memory usage stable under 80%

## 🔄 Maintenance Schedule

### Weekly
- [ ] Check application logs for errors
- [ ] Verify HTTP response time acceptable
- [ ] Confirm no memory/CPU issues

### Monthly  
- [ ] Update dependencies if needed
- [ ] Review and test backup deployment process
- [ ] Verify all documentation still accurate

### Before Major Changes
- [ ] Create backup deployment ZIP
- [ ] Test changes locally first
- [ ] Plan rollback strategy
- [ ] Document any new issues encountered

## 📞 Support Resources

### When Things Go Wrong
1. **Check this documentation first** - Most issues are covered
2. **Review Azure App Service logs** - `az webapp log tail`
3. **Verify configuration** - Use quick reference commands
4. **Test locally** - Ensure code works before deployment
5. **GitHub Actions logs** - Check CI/CD pipeline issues

### Escalation Path
1. **Immediate**: Use emergency recovery process
2. **Investigation**: Check troubleshooting guide
3. **Configuration**: Use quick reference commands
4. **Deployment**: Follow GitHub Actions guide

---

## 🎉 Final Notes

This documentation captures the **complete working solution** tested and verified on September 26, 2025. The application is now successfully deployed and running at https://credit-risk-clean-app.azurewebsites.net.

**Key Lesson Learned**: The main issues were configuration-related, not code-related. The application code was working correctly; Azure was just using the wrong startup command and insufficient resources.

**Future Deployments**: Always follow the post-deployment checklist, especially setting the correct startup command. This single step resolves 90% of deployment issues.

---
*Complete Documentation Package - September 26, 2025*  
*Status: Production-tested and verified working*