#!/usr/bin/env bash
# =============================================================================
# Credit Risk App — Azure Deploy Script  (THE single deploy script — do not create others)
#
# Usage:
#   ./scripts/deploy_azure.sh                  # full deploy: build → push → upload DB → redeploy
#   ./scripts/deploy_azure.sh --db-only        # re-upload DB + restart container (no rebuild)
#   ./scripts/deploy_azure.sh --skip-build     # push existing local image, upload DB, redeploy
#   ./scripts/deploy_azure.sh --setup-only     # one-time infrastructure setup only
#
# Requirements:
#   - az CLI logged in:  az login
#   - docker running
#   - run from repo root: cd clean_v16_app && ./scripts/deploy_azure.sh
#
# The script automatically:
#   - Generates a timestamped image tag (e.g. v-20260329-115400)
#   - Checkpoints the SQLite DB (flushes WAL) before upload to avoid corruption
#   - Discovers and deletes the currently running container by name prefix
#   - Waits for the new container to become healthy and prints the URL
# =============================================================================
set -euo pipefail

# ── Configuration (update these if infrastructure changes) ────────────────────
RG="rg-credit-risk-clean"
ACR="creditriskregistry"
STORAGE="creditriskstorageacc"
KV="kv-creditrisk-ey"
SHARE="credit-risk-db"
LOCATION="ukwest"
CONTAINER_PREFIX="credit-risk-demo"

# Single timestamp used by both IMAGE_TAG and NEW_CONTAINER so they always match
# Override with:  TAG=v23-my-feature ./scripts/deploy_azure.sh
_TS="$(date +%Y%m%d-%H%M%S)"
IMAGE_TAG="${TAG:-v-${_TS}}"
IMAGE="${ACR}.azurecr.io/credit-risk-demo:${IMAGE_TAG}"
NEW_CONTAINER="${CONTAINER_PREFIX}-${_TS}"

# ── Parse flags ───────────────────────────────────────────────────────────────
SKIP_SETUP=false
SKIP_BUILD=false
DB_ONLY=false
for arg in "$@"; do
  case $arg in
    --setup-only)  SKIP_BUILD=true; DB_ONLY=false ;;
    --skip-build)  SKIP_BUILD=true ;;
    --db-only)     DB_ONLY=true; SKIP_BUILD=true ;;
    --app-only)    SKIP_SETUP=true ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
info()  { echo ""; echo "▶  $*"; }
ok()    { echo "   ✅ $*"; }
skip()  { echo "   ⏭  $* (already exists, skipping)"; }
warn()  { echo "   ⚠️  $*"; }
die()   { echo ""; echo "❌  FATAL: $*"; exit 1; }

check_login() {
  az account show --query id -o tsv > /dev/null 2>&1 || die "Not logged in to Azure CLI. Run: az login"
  SUBSCRIPTION=$(az account show --query id -o tsv)
  ok "Logged in. Subscription: $SUBSCRIPTION"
}

# ── Pre-deploy DB validation ──────────────────────────────────────────────────
# Creates a clean VACUUM INTO copy in DELETE journal mode that is safe for
# Azure File Share (SMB). WAL mode is incompatible with SMB network mounts
# and causes "database disk image is malformed" errors.
validate_and_prepare_db() {
  local src="$1" out="$2" label="$3"
  info "Validating and preparing ${label} for upload..."

  python3 - <<PYEOF
import sqlite3, os, sys

src = "${src}"
out = "${out}"
label = "${label}"

if not os.path.exists(src):
    print(f"  ❌ FATAL: {src} not found — aborting deploy")
    sys.exit(1)

# 1) Flush any pending WAL on the source
con = sqlite3.connect(src)
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()

# 2) VACUUM INTO: rewrites every page — cleanest possible copy
if os.path.exists(out):
    os.remove(out)
con = sqlite3.connect(src)
con.execute(f"VACUUM INTO '{out}'")
con.close()

# 3) Switch copy to DELETE journal mode so SMB mounts work safely
con = sqlite3.connect(out)
mode = con.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
con.close()

# 4) Verify header bytes: write_version must be 1 (DELETE/rollback), not 2 (WAL)
with open(out, "rb") as f:
    hdr = f.read(100)
wv, rv = hdr[18], hdr[19]

# 5) Integrity check + basic row counts
con = sqlite3.connect(out)
integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
con.close()

size_kb = os.path.getsize(out) // 1024

print(f"  journal_mode  : {mode}  (write_ver={wv}, read_ver={rv})")
print(f"  integrity     : {integrity}")
print(f"  size          : {size_kb} KB")
print(f"  output        : {out}")

errors = []
if mode != "delete":
    errors.append(f"journal_mode is '{mode}', expected 'delete'")
if wv != 1 or rv != 1:
    errors.append(f"header write/read version is {wv}/{rv}, expected 1/1 (not WAL mode)")
if integrity != "ok":
    errors.append(f"integrity_check: {integrity}")
if size_kb < 100:
    errors.append(f"suspiciously small file: {size_kb} KB")

if errors:
    for e in errors:
        print(f"  ❌ {e}")
    sys.exit(1)

print(f"  ✅ {label} ready for upload")
PYEOF
}

resource_exists() {
  # Usage: resource_exists <az show command...>
  "$@" > /dev/null 2>&1
}

# =============================================================================
# PHASE 1 — One-time infrastructure setup (idempotent)
# =============================================================================
setup_infrastructure() {
  info "PHASE 1: Infrastructure setup (idempotent — safe to re-run)"

  # ── Storage Account ─────────────────────────────────────────────────────────
  info "Storage account: ${STORAGE}"
  if resource_exists az storage account show --name "$STORAGE" --resource-group "$RG"; then
    skip "Storage account ${STORAGE}"
  else
    az storage account create \
      --name "$STORAGE" \
      --resource-group "$RG" \
      --location "$LOCATION" \
      --sku Standard_LRS \
      --kind StorageV2 \
      --output none
    ok "Created storage account ${STORAGE}"
  fi
  STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE" --resource-group "$RG" \
    --query '[0].value' -o tsv)

  # ── File Share ──────────────────────────────────────────────────────────────
  # Single share holds both credit_risk.db and vector_database.db, mounted at /app/data
  # (ACI supports only one --azure-file-volume per mount path)
  info "File share: ${SHARE} (holds both DBs, mounts at /app/data)"
  if resource_exists az storage share show --name "$SHARE" \
      --account-name "$STORAGE" --account-key "$STORAGE_KEY"; then
    skip "File share ${SHARE}"
  else
    az storage share create \
      --name "$SHARE" \
      --account-name "$STORAGE" \
      --account-key "$STORAGE_KEY" \
      --output none
    ok "Created file share ${SHARE}"
  fi

  # ── Upload databases ─────────────────────────────────────────────────────────
  info "Uploading databases to file share"

  validate_and_prepare_db "data/credit_risk.db" "/tmp/credit_risk_upload.db" "credit_risk.db" \
    || die "credit_risk.db validation failed — fix the database before deploying"
  az storage file upload \
    --share-name "$SHARE" --source /tmp/credit_risk_upload.db --path credit_risk.db \
    --account-name "$STORAGE" --account-key "$STORAGE_KEY" \
    --output none
  ok "Uploaded credit_risk.db (clean, WAL-free, DELETE mode)"
  rm -f /tmp/credit_risk_upload.db

  VEC_LOCAL="data/vector_database.db"
  if [[ -f "$VEC_LOCAL" ]]; then
    validate_and_prepare_db "$VEC_LOCAL" "/tmp/vector_db_upload.db" "vector_database.db" \
      || die "vector_database.db validation failed — fix the database before deploying"
    az storage file upload \
      --share-name "$SHARE" --source /tmp/vector_db_upload.db --path vector_database.db \
      --account-name "$STORAGE" --account-key "$STORAGE_KEY" \
      --output none
    ok "Uploaded vector_database.db (clean, WAL-free, DELETE mode)"
    rm -f /tmp/vector_db_upload.db
  fi

  # ── Key Vault ───────────────────────────────────────────────────────────────
  info "Key Vault: ${KV}"
  if resource_exists az keyvault show --name "$KV" --resource-group "$RG"; then
    skip "Key Vault ${KV}"
  else
    az keyvault create \
      --name "$KV" \
      --resource-group "$RG" \
      --location "$LOCATION" \
      --enable-rbac-authorization true \
      --output none
    ok "Created Key Vault ${KV}"
    warn "IMPORTANT: Grant yourself 'Key Vault Secrets Officer' to store secrets:"
    warn "  az role assignment create --assignee <your-email-or-sp-id> \\"
    warn "    --role 'Key Vault Secrets Officer' \\"
    warn "    --scope $(az keyvault show --name $KV --resource-group $RG --query id -o tsv)"
  fi

  # ── Secrets (idempotent set — safe to re-run to rotate values) ──────────────
  info "Key Vault secrets"
  KV_ID=$(az keyvault show --name "$KV" --resource-group "$RG" --query id -o tsv)

  # Check if caller has rights to write secrets before trying
  if ! az keyvault secret list --vault-name "$KV" --output none 2>/dev/null; then
    warn "Cannot read Key Vault secrets — you may need to assign yourself 'Key Vault Secrets Officer':"
    warn "  az role assignment create --assignee \$(az ad signed-in-user show --query id -o tsv) \\"
    warn "    --role 'Key Vault Secrets Officer' --scope ${KV_ID}"
    warn "Skipping secret setup — re-run after granting access."
  else
    # Load from .env if present, otherwise prompt
    load_secret() {
      local name="$1" env_key="$2"
      local val
      # Try .env file first
      if [[ -f .env ]]; then
        val=$(grep "^${env_key}=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")
      fi
      if [[ -z "${val:-}" ]]; then
        # Try current environment
        val="${!env_key:-}"
      fi
      if [[ -z "${val:-}" ]]; then
        warn "Secret ${name}: not found in .env or environment. Set manually:"
        warn "  az keyvault secret set --vault-name ${KV} --name ${name} --value '<value>'"
        return
      fi
      az keyvault secret set --vault-name "$KV" --name "$name" --value "$val" --output none
      ok "Secret set: ${name}"
    }

    load_secret "COMPANIES-HOUSE-API-KEY"               "COMPANIES_HOUSE_API_KEY"
    load_secret "OPENAI-API-KEY"                         "OPENAI_API_KEY"
    load_secret "AZURE-OPENAI-ENDPOINT"                  "AZURE_OPENAI_ENDPOINT"
    load_secret "AZURE-OPENAI-DEPLOYMENT-NAME"           "AZURE_OPENAI_DEPLOYMENT_NAME"
    load_secret "AZURE-DOCUMENT-INTELLIGENCE-ENDPOINT"   "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
    load_secret "AZURE-DOCUMENT-INTELLIGENCE-KEY"        "AZURE_DOCUMENT_INTELLIGENCE_KEY"
  fi

  ok "Infrastructure setup complete"
}

# =============================================================================
# PHASE 2 — Build, push and redeploy (runs on every deploy)
# =============================================================================
deploy_app() {
  info "PHASE 2: Deploy"

  # ── Read secrets from Key Vault ──────────────────────────────────────────────
  info "Reading secrets from Key Vault: ${KV}"
  read_secret() {
    az keyvault secret show --vault-name "$KV" --name "$1" --query value -o tsv 2>/dev/null \
      || { warn "Could not read secret $1 from Key Vault — falling back to .env" >&2; grep "^${2}=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' || echo ""; }
  }
  CH_KEY=$(read_secret       "COMPANIES-HOUSE-API-KEY"             "COMPANIES_HOUSE_API_KEY")
  OAI_KEY=$(read_secret      "OPENAI-API-KEY"                       "OPENAI_API_KEY")
  OAI_ENDPOINT=$(read_secret "AZURE-OPENAI-ENDPOINT"                "AZURE_OPENAI_ENDPOINT")
  OAI_DEPLOY=$(read_secret   "AZURE-OPENAI-DEPLOYMENT-NAME"         "AZURE_OPENAI_DEPLOYMENT_NAME")
  DI_ENDPOINT=$(read_secret  "AZURE-DOCUMENT-INTELLIGENCE-ENDPOINT" "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
  DI_KEY=$(read_secret       "AZURE-DOCUMENT-INTELLIGENCE-KEY"      "AZURE_DOCUMENT_INTELLIGENCE_KEY")
  OAI_DEPLOY="${OAI_DEPLOY:-gpt-35-turbo}"

  ACR_PASS=$(az acr credential show --name "$ACR" --query 'passwords[0].value' -o tsv)
  STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE" --resource-group "$RG" --query '[0].value' -o tsv)

  # ── Build image first (does not touch file share) ───────────────────────────
  if ! $SKIP_BUILD; then
    info "Building image: ${IMAGE}"
    docker build --platform linux/amd64 -t "$IMAGE" .
    ok "Build complete"
  else
    info "Skipping build (--skip-build)"
  fi

  # ── Push ─────────────────────────────────────────────────────────────────────
  info "Pushing to ACR: ${IMAGE}"
  az acr login --name "$ACR"
  docker push "$IMAGE"
  ok "Push complete"

  # ── Delete ALL old containers BEFORE uploading DBs to the file share ─────────
  # CRITICAL: old container must be stopped first so it has no open SMB connection
  # to the file share — concurrent writes corrupt the SQLite DB on Azure Files.
  while IFS= read -r c; do
    [[ -z "$c" ]] && continue
    info "Deleting old container: ${c}"
    az container delete --name "$c" --resource-group "$RG" --yes --output none
    ok "Deleted ${c}"
  done < <(az container list --resource-group "$RG" \
    --query "[?starts_with(name,'${CONTAINER_PREFIX}')].name" -o tsv 2>/dev/null || true)

  # Give ACI time to fully release all SMB file handles before we touch the share
  info "Waiting 15s for SMB file handles to release..."
  sleep 15

  # ── Upload DBs — now safe, no container has the file share open ─────────────
  # Run VACUUM INTO + DELETE mode on each DB before upload.
  # This ensures: no WAL header, all pages rewritten, integrity verified.
  validate_and_prepare_db "data/credit_risk.db" "/tmp/credit_risk_upload.db" "credit_risk.db" \
    || die "credit_risk.db validation failed — deploy aborted"

  az storage file upload \
    --share-name "$SHARE" --source /tmp/credit_risk_upload.db --path credit_risk.db \
    --account-name "$STORAGE" --account-key "$STORAGE_KEY" \
    --output none
  rm -f /tmp/credit_risk_upload.db

  # Delete any stale WAL/SHM files left by the previous container run
  az storage file delete --share-name "$SHARE" --path "credit_risk.db-wal" \
    --account-name "$STORAGE" --account-key "$STORAGE_KEY" --output none 2>/dev/null || true
  az storage file delete --share-name "$SHARE" --path "credit_risk.db-shm" \
    --account-name "$STORAGE" --account-key "$STORAGE_KEY" --output none 2>/dev/null || true
  ok "credit_risk.db uploaded (VACUUM'd, DELETE mode, no WAL/SHM)"

  validate_and_prepare_db "data/vector_database.db" "/tmp/vector_db_upload2.db" "vector_database.db" \
    || die "vector_database.db validation failed — deploy aborted"

  az storage file upload \
    --share-name "$SHARE" --source /tmp/vector_db_upload2.db --path vector_database.db \
    --account-name "$STORAGE" --account-key "$STORAGE_KEY" \
    --output none
  rm -f /tmp/vector_db_upload2.db

  az storage file delete --share-name "$SHARE" --path "vector_database.db-wal" \
    --account-name "$STORAGE" --account-key "$STORAGE_KEY" --output none 2>/dev/null || true
  az storage file delete --share-name "$SHARE" --path "vector_database.db-shm" \
    --account-name "$STORAGE" --account-key "$STORAGE_KEY" --output none 2>/dev/null || true
  ok "vector_database.db uploaded (VACUUM'd, DELETE mode, no WAL/SHM)"

  # ── If --db-only: exit here (no new container needed) ───────────────────────
  if $DB_ONLY; then
    warn "No running container to restart (--db-only with no existing container)"
    return
  fi

  # ── Create new container ─────────────────────────────────────────────────────
  info "Creating container: ${NEW_CONTAINER}"
  az container create \
    --name "$NEW_CONTAINER" \
    --resource-group "$RG" \
    --image "$IMAGE" \
    --registry-login-server "${ACR}.azurecr.io" \
    --registry-username "$ACR" \
    --registry-password "$ACR_PASS" \
    --cpu 8 --memory 16 --ports 8000 \
    --ip-address Public --location "$LOCATION" --os-type Linux \
    --azure-file-volume-account-name "$STORAGE" \
    --azure-file-volume-account-key  "$STORAGE_KEY" \
    --azure-file-volume-share-name   "$SHARE" \
    --azure-file-volume-mount-path   /app/data \
    --environment-variables \
      WORKERS=8 \
      GUNICORN_TIMEOUT=900 \
      COMPANIES_HOUSE_API_KEY="$CH_KEY" \
      OPENAI_API_KEY="$OAI_KEY" \
      AZURE_OPENAI_ENDPOINT="$OAI_ENDPOINT" \
      AZURE_OPENAI_DEPLOYMENT_NAME="$OAI_DEPLOY" \
      AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="$DI_ENDPOINT" \
      AZURE_DOCUMENT_INTELLIGENCE_KEY="$DI_KEY" \
    --output none

  PUBLIC_IP=$(az container show --name "$NEW_CONTAINER" --resource-group "$RG" \
    --query 'ipAddress.ip' -o tsv 2>/dev/null || echo "pending")

  ok "Container created: ${NEW_CONTAINER} @ ${PUBLIC_IP}"

  # ── Health check ─────────────────────────────────────────────────────────────
  sleep 30
  health_check "$PUBLIC_IP" "$NEW_CONTAINER"
}

# ── Wait for healthy status ────────────────────────────────────────────────────
health_check() {
  local ip="$1" name="$2"
  info "Waiting for health check at http://${ip}:8000/health ..."
  local STATUS="unreachable"
  # Up to 12 attempts × 20s = 240s, giving WAL recovery + DB mount plenty of time
  for i in $(seq 1 12); do
    STATUS=$(curl -s --max-time 8 "http://${ip}:8000/health" 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null \
      || echo "unreachable")
    if [[ "$STATUS" == "healthy" ]]; then
      ok "Health check passed! (attempt ${i})"
      break
    fi
    warn "Attempt ${i}/12: status=${STATUS} — waiting 20s..."
    sleep 20
  done

  # ── Deep DB validation: verify companies portal and SIC prediction actually work
  if [[ "$STATUS" == "healthy" ]]; then
    info "Deep validation: checking database and SIC prediction..."

    # Check companies portal returns data (tests company_portal_view + all joins)
    PORTAL_ERR=$(curl -s --max-time 15 "http://${ip}:8000/api/companies/portal?page=1&limit=5" 2>/dev/null \
      | python3 -c "
import sys,json
d=json.load(sys.stdin)
err=d.get('error','')
total=d.get('total') or 0
cnt=len(d.get('data') or [])
if err: print('ERROR:'+str(err))
elif cnt==0: print('ERROR:no_data_returned')
else: print('OK:total='+str(total)+',data='+str(cnt))
" 2>/dev/null || echo "ERROR:curl_failed")

    if [[ "$PORTAL_ERR" == OK* ]]; then
      ok "Database portal check: ${PORTAL_ERR}"
    else
      warn "Database portal check FAILED: ${PORTAL_ERR}"
      warn "The app is up but company data may not load. Check logs:"
      warn "  az container logs --name ${name} --resource-group ${RG}"
      STATUS="degraded_db"
    fi

    # Check SIC prediction returns a real code (not 82990 fallback)
    SIC_CHECK=$(curl -s --max-time 30 -X POST "http://${ip}:8000/api/predict_sic_agentic" \
      -H "Content-Type: application/json" \
      -d '{"company_name":"TESCO PLC","business_description":"Grocery supermarket retail food stores"}' 2>/dev/null \
      | python3 -c "
import sys,json
d=json.load(sys.stdin)
sic=d.get('predicted_sic_code','')
method=d.get('prediction_method','')
conf=d.get('confidence_score',0)
if method=='intelligent_fallback' or sic=='82990':
    print('WARN:fallback sic='+str(sic)+' method='+str(method))
else:
    print('OK:sic='+str(sic)+' method='+str(method)+' conf='+str(conf))
" 2>/dev/null || echo "ERROR:curl_failed")

    if [[ "$SIC_CHECK" == OK* ]]; then
      ok "SIC prediction check: ${SIC_CHECK}"
    else
      warn "SIC prediction check: ${SIC_CHECK}"
    fi
  fi

  echo ""
  echo "============================================================"
  if [[ "$STATUS" == "healthy" ]]; then
    echo "  ✅  Deploy complete"
  else
    echo "  ⚠️  Deploy complete but health is ${STATUS} — check logs:"
    echo "       az container logs --name ${name} --resource-group ${RG}"
  fi
  echo "  Container : ${name}"
  echo "  URL       : http://${ip}:8000"
  echo "  Dashboard : http://${ip}:8000/dashboard"
  echo "  Health    : http://${ip}:8000/health  [${STATUS}]"
  echo "============================================================"
}

# =============================================================================
# Main
# =============================================================================
echo "============================================================"
echo "  Credit Risk App — Azure Deploy"
echo "  Image tag : ${IMAGE_TAG}"
echo "  RG        : ${RG}"
echo "============================================================"

check_login

$SKIP_SETUP || setup_infrastructure
$DB_ONLY && deploy_app || { $SKIP_SETUP || true; deploy_app; }
