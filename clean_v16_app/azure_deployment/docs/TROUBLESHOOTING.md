# Troubleshooting Guide

## Overview

This guide covers common deployment issues and their solutions for the Credit Risk Analysis application on Azure.

---

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [Storage Connection Problems](#storage-connection-problems)
3. [Web App Startup Failures](#web-app-startup-failures)
4. [Database Access Issues](#database-access-issues)
5. [Vector Search Problems](#vector-search-problems)
6. [PDF Processing Errors](#pdf-processing-errors)
7. [Performance Issues](#performance-issues)
8. [Cost and Billing Issues](#cost-and-billing-issues)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Emergency Procedures](#emergency-procedures)

---

## Authentication Issues

### Issue 1: "Authentication Failed" when running deployment scripts

**Symptoms:**
```bash
ERROR: Please run 'az login' to setup account.
```

**Solution:**
```bash
# Login to Azure
az login

# Verify authentication
az account show

# Set correct subscription if needed
az account set --subscription "Visual Studio Enterprise"
```

**Common Causes:**
- Azure CLI token expired (valid for 90 days)
- Wrong subscription selected
- Multiple Azure accounts configured

---

### Issue 2: Web App cannot access storage account

**Symptoms:**
```
ConnectionError: Failed to connect to storage account
Status Code: 403 Forbidden
```

**Solution:**
```bash
# Check if web app has correct connection string
az webapp config appsettings list \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --query "[?name=='AZURE_STORAGE_CONNECTION_STRING']"

# Update connection string if needed
CONN_STRING=$(az storage account show-connection-string \
  --name creditriskstorageacc \
  --resource-group rg-credit-risk-clean \
  --output tsv)

az webapp config appsettings set \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --settings AZURE_STORAGE_CONNECTION_STRING="$CONN_STRING"

# Restart web app
az webapp restart \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean
```

**Common Causes:**
- Connection string not set
- Storage account keys rotated
- Firewall rules blocking access

---

### Issue 3: Azure OpenAI authentication fails

**Symptoms:**
```
OpenAIError: Unauthorized (401)
Message: Access denied due to invalid subscription key
```

**Solution:**
```bash
# Verify OpenAI endpoint
az cognitiveservices account show \
  --name data-risk-modernisation-OAI \
  --resource-group rg-credit-risk-clean

# Get API key
API_KEY=$(az cognitiveservices account keys list \
  --name data-risk-modernisation-OAI \
  --resource-group rg-credit-risk-clean \
  --query "key1" -o tsv)

# Update web app settings
az webapp config appsettings set \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --settings AZURE_OPENAI_API_KEY="$API_KEY"
```

**Common Causes:**
- API key expired or rotated
- Wrong endpoint URL
- Deployment name mismatch

---

## Storage Connection Problems

### Issue 4: File share not mounting

**Symptoms:**
```
Error: Failed to mount file share: credit-risk-db
Mount path: /home/data
```

**Solution:**
```bash
# Check if file share exists
az storage share show \
  --name credit-risk-db \
  --account-name creditriskstorageacc

# Check web app storage mounts
az webapp config storage-account list \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean

# Re-add storage mount
az webapp config storage-account add \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --custom-id MainDatabase \
  --storage-type AzureFiles \
  --share-name credit-risk-db \
  --account-name creditriskstorageacc \
  --mount-path /home/data \
  --access-key $(az storage account keys list \
    --account-name creditriskstorageacc \
    --query "[0].value" -o tsv)
```

**Common Causes:**
- Storage mount not configured
- Access key incorrect
- File share deleted

---

### Issue 5: Blob storage connection timeout

**Symptoms:**
```
BlobStorageError: Connection timeout after 30 seconds
Container: credit-risk-documents
```

**Solution:**
```bash
# Check blob container exists
az storage container show \
  --name credit-risk-documents \
  --account-name creditriskstorageacc

# Test connectivity from web app
az webapp ssh --name credit-risk-final --resource-group rg-credit-risk-clean
# Inside SSH session:
curl -I https://creditriskstorageacc.blob.core.windows.net/credit-risk-documents/

# Check network rules
az storage account show \
  --name creditriskstorageacc \
  --query "networkRuleSet"
```

**Common Causes:**
- Network firewall blocking access
- Storage account in different region (high latency)
- Temporary Azure service issue

---

### Issue 6: Database file locked or corrupted

**Symptoms:**
```
sqlite3.OperationalError: database is locked
OR
sqlite3.DatabaseError: database disk image is malformed
```

**Solution for Locked Database:**
```bash
# Check current connections
az webapp log tail --name credit-risk-final --resource-group rg-credit-risk-clean

# Restart web app to clear locks
az webapp restart --name credit-risk-final --resource-group rg-credit-risk-clean

# If lock persists, check for zombie processes
az webapp ssh --name credit-risk-final --resource-group rg-credit-risk-clean
ps aux | grep python
kill -9 <PID>  # Kill zombie processes
```

**Solution for Corrupted Database:**
```bash
# 1. Stop the web app
az webapp stop --name credit-risk-final --resource-group rg-credit-risk-clean

# 2. Download corrupted database for analysis
az storage file download \
  --share-name credit-risk-db \
  --path credit_risk.db \
  --dest ./corrupted_db.db \
  --account-name creditriskstorageacc

# 3. Try to repair (on local machine)
sqlite3 corrupted_db.db "PRAGMA integrity_check;"
sqlite3 corrupted_db.db ".recover" | sqlite3 repaired_db.db

# 4. If repair fails, restore from backup
az storage file download \
  --share-name credit-risk-db \
  --path backups/credit_risk_backup_$(date +%Y%m%d).db \
  --dest ./credit_risk.db \
  --account-name creditriskstorageacc

# 5. Upload restored database
az storage file upload \
  --share-name credit-risk-db \
  --source ./credit_risk.db \
  --account-name creditriskstorageacc

# 6. Start the web app
az webapp start --name credit-risk-final --resource-group rg-credit-risk-clean
```

**Common Causes:**
- Multiple processes accessing database without proper locking
- Abrupt shutdown during write operation
- Storage system failure

---

## Web App Startup Failures

### Issue 7: Web app fails to start

**Symptoms:**
```
Application Error: An error occurred in the application and your page could not be served.
```

**Diagnosis:**
```bash
# View application logs
az webapp log tail \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean

# Download full logs
az webapp log download \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --log-file webapp_logs.zip

# Check startup command
az webapp config show \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --query "appCommandLine"
```

**Common Solutions:**

**Solution A: Missing environment variables**
```bash
# Check required settings
az webapp config appsettings list \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean

# Add missing settings
az webapp config appsettings set \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --settings \
    FLASK_APP=main.py \
    FLASK_ENV=production \
    WEBSITES_PORT=5002
```

**Solution B: Python version mismatch**
```bash
# Check Python version
az webapp config show \
  --name credit-risk-final \
  --query "linuxFxVersion"

# Update if needed (Python 3.11)
az webapp config set \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --linux-fx-version "PYTHON|3.11"
```

**Solution C: Dependency installation failed**
```bash
# Enable build logs
az webapp config appsettings set \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true ENABLE_ORYX_BUILD=true

# Redeploy to trigger fresh build
./scripts/3_deploy_webapp.sh
```

---

### Issue 8: Import errors or missing modules

**Symptoms:**
```python
ModuleNotFoundError: No module named 'langgraph'
ImportError: cannot import name 'CreditRiskWorkflow'
```

**Solution:**
```bash
# Check installed packages
az webapp ssh --name credit-risk-final --resource-group rg-credit-risk-clean
pip list

# Install missing packages
pip install langgraph langchain-core

# Or update requirements.txt and redeploy
echo "langgraph==0.2.0" >> requirements.txt
./scripts/3_deploy_webapp.sh
```

**Common Causes:**
- Package not in requirements.txt
- Version conflict
- Build process failed silently

---

### Issue 9: Port binding errors

**Symptoms:**
```
OSError: [Errno 98] Address already in use
```

**Solution:**
```bash
# Check configured port
az webapp config appsettings list \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --query "[?name=='WEBSITES_PORT'].value"

# Should be 5002, update if needed
az webapp config appsettings set \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --settings WEBSITES_PORT=5002

# Check startup.py binds to correct port
az webapp ssh --name credit-risk-final
cat app_modules/scripts/startup.py | grep port
```

**Common Causes:**
- Wrong port in WEBSITES_PORT
- Application hardcoded to port 5000
- Multiple processes trying to bind

---

## Database Access Issues

### Issue 10: "No such table" errors

**Symptoms:**
```sql
sqlite3.OperationalError: no such table: companies
```

**Solution:**
```bash
# Verify database exists
az storage file list \
  --share-name credit-risk-db \
  --account-name creditriskstorageacc

# Download and inspect database
az storage file download \
  --share-name credit-risk-db \
  --path credit_risk.db \
  --dest ./credit_risk.db \
  --account-name creditriskstorageacc

# Check tables
sqlite3 credit_risk.db ".tables"
sqlite3 credit_risk.db ".schema companies"

# If tables are missing, restore from backup or recreate schema
```

**Common Causes:**
- Wrong database file path
- Empty database uploaded
- Schema migration not run

---

### Issue 11: Vector database not found

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/home/vector_data/vector_database.db'
```

**Solution:**
```bash
# Check if vector database exists
az storage file list \
  --share-name credit-risk-vector-db \
  --account-name creditriskstorageacc

# If missing, upload it
az storage file upload \
  --share-name credit-risk-vector-db \
  --source ./vector_database.db \
  --account-name creditriskstorageacc

# Verify mount path in web app
az webapp config storage-account list \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --query "[?customId=='VectorDatabase'].mountPath"
```

**Common Causes:**
- Vector database not uploaded
- Storage mount not configured
- Wrong path in environment variables

---

## Vector Search Problems

### Issue 12: Vector search returns no results

**Symptoms:**
```python
VectorSearchError: No matching documents found
Query: "financial statements"
```

**Diagnosis:**
```bash
# Check vector database size and content
az storage file show \
  --share-name credit-risk-vector-db \
  --path vector_database.db \
  --account-name creditriskstorageacc \
  --query "properties.contentLength"

# Download and inspect
az storage file download \
  --share-name credit-risk-vector-db \
  --path vector_database.db \
  --dest ./vector_database.db

sqlite3 vector_database.db "SELECT COUNT(*) FROM embeddings;"
sqlite3 vector_database.db "SELECT * FROM embeddings LIMIT 5;"
```

**Solutions:**

**Solution A: Embeddings table is empty**
```bash
# Regenerate embeddings
curl -X POST https://credit-risk-final.azurewebsites.net/api/admin/regenerate-vectors \
  -H "Content-Type: application/json"
```

**Solution B: Similarity threshold too high**
```bash
# Lower threshold in settings
az webapp config appsettings set \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --settings VECTOR_SEARCH_SIMILARITY_THRESHOLD=0.5
```

**Solution C: Wrong embedding model**
```bash
# Verify embedding model matches
az webapp config appsettings list \
  --name credit-risk-final \
  --query "[?name=='EMBEDDING_MODEL'].value"

# Should be: text-embedding-3-large (3072 dimensions)
```

---

## PDF Processing Errors

### Issue 13: Cannot download PDFs from Companies House

**Symptoms:**
```
CompaniesHouseError: HTTP 401 Unauthorized
Failed to download financial documents
```

**Solution:**
```bash
# Check API key
az webapp config appsettings list \
  --name credit-risk-final \
  --query "[?name=='COMPANIES_HOUSE_API_KEY'].value"

# Test API key manually
curl -u YOUR_API_KEY: https://api.company-information.service.gov.uk/company/00000006

# Update if invalid
az webapp config appsettings set \
  --name credit-risk-final \
  --settings COMPANIES_HOUSE_API_KEY="your_new_key"
```

**Common Causes:**
- API key expired
- Rate limit exceeded (600 requests/5 minutes)
- Companies House API outage

---

### Issue 14: PDF upload to blob storage fails

**Symptoms:**
```
BlobStorageError: Failed to upload PDF
Container: credit-risk-documents
Status: 403 Forbidden
```

**Solution:**
```bash
# Check container exists and is accessible
az storage container show \
  --name credit-risk-documents \
  --account-name creditriskstorageacc

# Check storage account permissions
az storage account show \
  --name creditriskstorageacc \
  --query "allowBlobPublicAccess"

# Verify connection string in app
az webapp config appsettings list \
  --name credit-risk-final \
  --query "[?name=='AZURE_STORAGE_CONNECTION_STRING']"

# Test upload manually
az storage blob upload \
  --container-name credit-risk-documents \
  --file test.pdf \
  --name test.pdf \
  --account-name creditriskstorageacc
```

---

## Performance Issues

### Issue 15: Slow API response times

**Symptoms:**
```
Request took 15.3 seconds
Expected: < 2 seconds
```

**Diagnosis:**
```bash
# Check Application Insights for slow requests
az monitor app-insights metrics show \
  --app credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --metric requests/duration

# Check CPU and memory usage
az webapp show \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --query "siteConfig"
```

**Solutions:**

**Solution A: Scale up (more CPU/RAM)**
```bash
# Upgrade to higher tier
az appservice plan update \
  --name credit-risk-final-plan \
  --resource-group rg-credit-risk-clean \
  --sku P1V2
```

**Solution B: Increase worker count**
```bash
az webapp config appsettings set \
  --name credit-risk-final \
  --settings \
    WEB_CONCURRENCY=4 \
    GUNICORN_WORKERS=4
```

**Solution C: Enable caching**
```bash
az webapp config appsettings set \
  --name credit-risk-final \
  --settings \
    ENABLE_CACHING=true \
    CACHE_DEFAULT_TIMEOUT=300
```

---

### Issue 16: High database latency

**Symptoms:**
```
Database query took 5.2 seconds
Query: SELECT * FROM companies WHERE...
```

**Solution:**
```bash
# Check database file size
az storage file show \
  --share-name credit-risk-db \
  --path credit_risk.db \
  --query "properties.contentLength"

# Vacuum database to optimize
sqlite3 credit_risk.db "VACUUM;"
sqlite3 credit_risk.db "ANALYZE;"

# Rebuild indexes
sqlite3 credit_risk.db "REINDEX;"

# Upload optimized database
az storage file upload \
  --share-name credit-risk-db \
  --source ./credit_risk.db \
  --account-name creditriskstorageacc
```

---

## Cost and Billing Issues

### Issue 17: Unexpected high costs

**Diagnosis:**
```bash
# View cost breakdown
az costmanagement query \
  --type Usage \
  --dataset-filter "{\"and\":[{\"dimensions\":{\"name\":\"ResourceGroup\",\"operator\":\"In\",\"values\":[\"rg-credit-risk-clean\"]}}]}" \
  --timeframe MonthToDate

# Check for unused resources
az resource list \
  --resource-group rg-credit-risk-clean \
  --query "[].{Name:name, Type:type, Location:location}"
```

**Solution:**
```bash
# Clean up unused resources
./scripts/cleanup_unused_resources.sh --dry-run  # Review first
./scripts/cleanup_unused_resources.sh  # Execute

# Scale down if possible
az appservice plan update \
  --name credit-risk-final-plan \
  --sku B2  # Downgrade from B3
```

---

## Monitoring and Logging

### Issue 18: Cannot view application logs

**Solution:**
```bash
# Enable application logging
az webapp log config \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean \
  --application-logging true \
  --level information

# Stream logs
az webapp log tail \
  --name credit-risk-final \
  --resource-group rg-credit-risk-clean

# Download logs
az webapp log download \
  --name credit-risk-final \
  --log-file logs.zip
```

---

## Emergency Procedures

### Emergency 1: Complete Application Outage

**Immediate Actions:**
1. Check Azure service health
2. Verify web app is running
3. Check recent deployments/changes
4. Restart web app
5. Escalate if not resolved in 15 minutes

```bash
# Quick recovery commands
az webapp restart --name credit-risk-final --resource-group rg-credit-risk-clean
az webapp log tail --name credit-risk-final --resource-group rg-credit-risk-clean
```

---

### Emergency 2: Data Corruption

**Immediate Actions:**
1. Stop web app immediately
2. Isolate corrupted database
3. Restore from latest backup
4. Verify data integrity
5. Resume service

```bash
# Emergency restore procedure in DISASTER_RECOVERY.md
```

---

## Quick Reference Commands

### Health Checks
```bash
# Web app health
curl https://credit-risk-final.azurewebsites.net/api/modular/health

# Check all services
az webapp show --name credit-risk-final --query "state"
az storage account show --name creditriskstorageacc --query "statusOfPrimary"
az cognitiveservices account show --name data-risk-modernisation-OAI --query "properties.provisioningState"
```

### Restart Services
```bash
# Web app
az webapp restart --name credit-risk-final --resource-group rg-credit-risk-clean

# SQLite Browser (if using)
az container restart --name sqlite-browser --resource-group rg-credit-risk-clean
```

### View Logs
```bash
# Application logs (live)
az webapp log tail --name credit-risk-final

# Download all logs
az webapp log download --name credit-risk-final --log-file logs_$(date +%Y%m%d).zip
```

---

## Getting Help

### Internal Resources
1. Check `azure_deployment/docs/` for detailed documentation
2. Review deployment scripts in `azure_deployment/scripts/`
3. Check Azure Portal for resource status

### External Resources
1. Azure Support Portal: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade
2. Azure Status: https://status.azure.com/
3. Stack Overflow: Tag `azure-web-app-service`

### Escalation Path
1. Check this troubleshooting guide
2. Review application logs
3. Check Azure service health
4. Contact Azure Support (if infrastructure issue)
5. Engage development team (if application issue)
