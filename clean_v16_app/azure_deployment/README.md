# Azure Deployment — Credit Risk Analysis App

**Last updated:** 29 March 2026
**Live URL:** http://20.254.176.27:8000
**Current container:** `credit-risk-demo-v22` · resource group `rg-credit-risk-clean`

> **One script does everything.** Always use `scripts/deploy_azure.sh` from the repo root.
> Do not create new deploy scripts — update that file if anything needs to change.

---

## Quick Reference

| Scenario | Command |
|---|---|
| Code change (most common) | `./scripts/deploy_azure.sh` |
| Named release | `TAG=v23-my-feature ./scripts/deploy_azure.sh` |
| DB data update only (no code change) | `./scripts/deploy_azure.sh --db-only` |
| Skip Docker build (image already built) | `./scripts/deploy_azure.sh --skip-build` |
| First-time infrastructure setup | `./scripts/deploy_azure.sh --setup-only` |

---

## Prerequisites (install once)

```bash
# 1. Azure CLI
brew install azure-cli        # macOS
# Windows/Linux: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli

# 2. Docker Desktop — must be running
# https://www.docker.com/products/docker-desktop

# 3. Log in to Azure
az login

# Confirm you are on the right subscription
az account show --query "{name:name, id:id}" -o table
# Expected: Visual Studio Enterprise Subscription (EY)
```

---

## Full Deploy Walkthrough

```bash
# 1. Go to the app root (not this folder)
cd /path/to/clean_v16_app

# 2. Run
./scripts/deploy_azure.sh
```

What the script does automatically, in order:

1. Verifies Azure CLI login
2. Ensures all infrastructure exists (storage account, file share, Key Vault)
3. Reads API secrets from Key Vault
4. Checkpoints the local SQLite DB (flushes WAL) and uploads a clean copy
5. Builds the Docker image for `linux/amd64`
6. Logs in to ACR and pushes the image
7. Finds and deletes the currently running container
8. Creates a new container with the new image
9. Waits up to 75 seconds, runs a health check, and prints the live URL

---

## Azure Infrastructure

| Resource | Name | Purpose |
|---|---|---|
| Resource Group | `rg-credit-risk-clean` | All resources live here |
| Container Registry | `creditriskregistry` | Docker image storage |
| Storage Account | `creditriskstorageacc` | Hosts file shares |
| File Share | `credit-risk-db` | Mounted at `/app/data` in the container |
| Key Vault | `kv-creditrisk-ey` | API keys (read at deploy time) |
| Container | `credit-risk-demo-YYYYMMDD-HHmmss` | Auto-named with timestamp |
| Container size | 8 vCPU / 16 GB RAM | Port 8000 |
| Region | `ukwest` | UK West |

---

## Secrets in Key Vault

The deploy script reads these automatically. To update a secret:

```bash
az keyvault secret set \
  --vault-name kv-creditrisk-ey \
  --name OPENAI-API-KEY \
  --value "<new-value>"
```

| Key Vault Secret | Maps to Container Env Var |
|---|---|
| `COMPANIES-HOUSE-API-KEY` | `COMPANIES_HOUSE_API_KEY` |
| `OPENAI-API-KEY` | `OPENAI_API_KEY` |
| `AZURE-OPENAI-ENDPOINT` | `AZURE_OPENAI_ENDPOINT` |
| `AZURE-OPENAI-DEPLOYMENT-NAME` | `AZURE_OPENAI_DEPLOYMENT_NAME` |
| `AZURE-DOCUMENT-INTELLIGENCE-ENDPOINT` | `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` |
| `AZURE-DOCUMENT-INTELLIGENCE-KEY` | `AZURE_DOCUMENT_INTELLIGENCE_KEY` |

If you don't have Key Vault access, the script falls back to a `.env` file in the repo root (not committed to git). Format:

```
COMPANIES_HOUSE_API_KEY=xxxx
OPENAI_API_KEY=xxxx
...
```

---

## Database

`data/credit_risk.db` is stored on the Azure File Share (`credit-risk-db`) and
mounted into the container at `/app/data/credit_risk.db`. It persists across all
container restarts and redeployments.

**Never upload the DB file manually.** Always go through the deploy script,
which runs `PRAGMA wal_checkpoint(TRUNCATE)` and makes a clean WAL-free backup
before uploading. Uploading a DB with an active WAL causes a
`database disk image is malformed` error in the container.

To push local DB changes to Azure without rebuilding the image:

```bash
./scripts/deploy_azure.sh --db-only
```

---

## Checking the Live App

```bash
# Health check
curl http://20.254.176.27:8000/health

# Open in browser
open http://20.254.176.27:8000/dashboard

# Container logs
az container logs \
  --name credit-risk-demo-v22 \
  --resource-group rg-credit-risk-clean

# List all containers (find the current one)
az container list \
  --resource-group rg-credit-risk-clean \
  --query "[].{name:name, ip:ipAddress.ip, status:instanceView.state}" \
  -o table

# List all Docker images in ACR
az acr repository show-tags \
  --name creditriskregistry \
  --repository credit-risk-demo \
  --orderby time_desc -o table
```

---

## Image Naming

Images are auto-tagged: `v-YYYYMMDD-HHmmss`

For a named release:

```bash
TAG=v23-my-feature ./scripts/deploy_azure.sh
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `unable to open database file` | DB WAL not flushed before upload | Use `./scripts/deploy_azure.sh` — it checkpoints automatically |
| `database disk image is malformed` | Same as above | Same fix |
| `authentication required` pushing Docker | ACR token expired | Script runs `az acr login` — or run it manually |
| `status: degraded` on health check | Secret missing or storage mount issue | Check `az container logs` |
| `Resource group not found` | Wrong subscription | Run `az account show` and `az login` |
| Container created but IP shows `pending` | Normal — takes ~30s | Wait; script polls automatically |
