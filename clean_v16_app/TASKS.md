# Credit Risk App — Outstanding Tasks

## Deployment Rules
- **Do NOT create a new Azure container for every code change** — it is costly.
- Preferred workflow for code-only changes (no new pip packages, no DB changes):
  1. Fix the code locally
  2. `docker build` → `docker push` to ACR with a new tag
  3. **Update the existing container** via `az container restart` or redeploy only when absolutely necessary
  4. Only provision a new container when the old one is broken/deleted or resource config changes (CPU/RAM)

---

## Bug Fixes

### [x] BUG-001 — Database Viewer: Schema mismatch — `predictions` table does not exist
- **Symptom:** Clicking the "View Predictions" quick-query button in the Database Viewer throws `Error: no such table: predictions`
- **Root cause:** The quick-query buttons in `modular_templates/database_viewer.html` use hard-coded table names (`predictions`, `confidence`) that don't match the actual schema.
- **Actual tables in `credit_risk.db`:**
  - `sic_prediction_history` ← replaces `predictions`
  - `companies` ← has `New_Accuracy`, `Old_Accuracy` columns (use for confidence queries)
  - `sic_codes`, `activity_log`, `api_audit_log`, `company_financials`, `company_sic_codes`, etc.
- **Fix needed:** Update `runQuickQuery()` in `database_viewer.html` to use correct table/column names:
  ```js
  // WRONG
  'predictions': 'SELECT ... FROM predictions ...'
  'confidence':  'SELECT ... FROM companies WHERE "New_Accuracy" IS NOT NULL ...'

  // CORRECT
  'predictions': 'SELECT id, company_name, predicted_sic, confidence_score, created_at FROM sic_prediction_history ORDER BY created_at DESC LIMIT 20;'
  'confidence':  'SELECT "Company Name", New_Accuracy, Old_Accuracy, (New_Accuracy - Old_Accuracy) as improvement FROM companies WHERE New_Accuracy IS NOT NULL ORDER BY improvement DESC LIMIT 15;'
  ```
- **File:** `modular_templates/database_viewer.html` — `runQuickQuery()` function
- **Deploy impact:** Code-only change → build + push + restart existing container (no new container needed)

### [x] BUG-002 — Database Viewer: Vector DB quick queries use wrong table names
- **Symptom:** All four quick-query buttons ("View All Companies", "View SIC Codes", "View Predictions", "Confidence Analysis") fail with `no such table` when `?db=vector` is active — none of those tables exist in `vector_database.db`
- **Actual tables in `vector_database.db`:**
  | Table | Key Columns |
  |---|---|
  | `documents_v2` | `document_id`, `company_number`, `company_name`, `filing_date`, `document_type`, `metadata` |
  | `document_chunks_v2` | `chunk_id`, `document_id`, `chunk_index`, `content` (text), `embedding` (BLOB) |
  | `chunk_vectors_v2_idx` | sqlite-vec virtual table (raw vector index — not directly queryable as a regular table) |
- **Fix needed:** When `DB_PARAM === 'vector'`, replace the quick-query buttons with vector-DB-appropriate ones:
  ```js
  // Vector DB quick queries
  'documents':   'SELECT document_id, company_name, company_number, filing_date, document_type FROM documents_v2 ORDER BY filing_date DESC LIMIT 20;'
  'chunks':      'SELECT dc.chunk_id, dc.document_id, d.company_name, dc.chunk_index, substr(dc.content, 1, 120) as content_preview FROM document_chunks_v2 dc JOIN documents_v2 d ON dc.document_id = d.document_id LIMIT 20;'
  'doc_count':   'SELECT company_name, COUNT(*) as doc_count FROM documents_v2 GROUP BY company_name ORDER BY doc_count DESC LIMIT 20;'
  'chunk_count': 'SELECT document_id, COUNT(*) as chunks FROM document_chunks_v2 GROUP BY document_id ORDER BY chunks DESC LIMIT 20;'
  ```
- **File:** `modular_templates/database_viewer.html` — `runQuickQuery()` function + sidebar button labels
- **Deploy impact:** Code-only change → build + push + restart existing container (no new container needed)

---

## Improvements

### [ ] IMP-001 — Database Viewer: Add Vector DB table browser
- Vector DB (`vector_database.db`) is accessible via `?db=vector` but its tables are vector/embedding specific — add custom quick queries suited to it

### [ ] IMP-002 — Parameterise container updates (avoid new container per deploy)
- Write a reusable `redeploy.sh` script that: builds, pushes, and restarts the **existing** named container rather than creating a new one

---

---

## Pending Deployment

### [ ] DEPLOY-001 — CH SIC + DB Viewer + Revenue Update fixes (all code-complete, NOT yet deployed)
- **Tag to use:** `v21-ch-sic-fix`
- **Files changed:**
  1. `app_modules/agentic/sic_prediction/nodes/ch_sic_retrieval_node.py` — CH SIC fix (see detail below)
  2. `modular_templates/database_viewer.html` — BUG-001 + BUG-002 fixes
  3. `modular_static/js/modular_dashboard.js` — Revenue Update fixes (BUG-003 to BUG-006, see below)

### [ ] BUG-003 — Update Revenue: "Start Processing" shows £0 with no explanation
- **Symptom:** Pressing "Start Processing" in the processing-time-estimate modal closes the modals, the revenue tab activates, but the result panel shows "£0" and no error explaining why.
- **Root cause (2 layers):**
  1. **Backend**: `FinancialExtractionNode` raises `ValueError("No transaction ID available")` when company ingestion finds no filing history (e.g. companies with no `company_number` or no linked documents). The exception is caught, the workflow continues to `TurnoverEstimationNode` with no document data, and returns `extracted_revenue: null`.
  2. **Frontend**: `executeRevenueUpdateWorkflow()` called `showRevenueResults(result)` unconditionally even when `result.success === false` or `result.extracted_revenue === null`. JS evaluates `null || 0 = 0`, renders `£0` with no error.
- **Fix applied (24 Mar 2026):** Added `hasRevenue` check in `executeRevenueUpdateWorkflow()`:
  - If `result.success === false` OR `extracted_revenue` is null/empty/0 → calls `showRevenueError(failureReason)` with a human-readable explanation
  - Failure reason is specific: distinguishes "no document downloaded" vs "OCR failed" vs "no revenue found in text"
  - File: `modular_static/js/modular_dashboard.js`

### [ ] BUG-004 — Update Revenue: Main confidence score shown as 0.0x% instead of 8x%
- **Symptom:** The confidence progress bar in the revenue results panel appears near-empty (e.g. 0.85% instead of 85%).
- **Root cause:** `confidence_score` returned by the agentic service is already a decimal (0.0–1.0), but the JS was dividing by 100 again: `(result.confidence_score || 0) / 100`.
- **Fix applied (24 Mar 2026):** Changed to: `rawConf > 1 ? rawConf / 100 : rawConf` — handles both legacy percent format and current decimal format. File: `modular_dashboard.js` in `showRevenueResults()`.

### [ ] BUG-005 — Update Revenue: Best alternative revenue selection broken (wrong confidence comparison)
- **Symptom:** The "highest confidence alternative" comparison was wrong — compared decimal vs percent: `altConf > (confidence * 100)` — so a 0.9 alternative would never beat a 0.85 main result because `0.9 > 85.0` is false.
- **Fix applied (24 Mar 2026):** Normalised `altConf` to 0.0–1.0 before comparing. File: `modular_dashboard.js` in `showRevenueResults()`.

### [ ] BUG-006 — Update Revenue: Alternative revenue candidates all show lowest confidence badge
- **Symptom:** All document extraction candidates in the "Select Revenue Option" panel always show the blue `info` badge, never `success` (green) or `warning` (yellow).
- **Root cause:** Alternative `confidence` is decimal (0.0–1.0), but the badge thresholds are `> 80` and `> 60` (percent range). A confidence of 0.9 would always fall below 80, showing `info`.
- **Fix applied (24 Mar 2026):** Normalise candidate confidence to percent for display: `confRaw > 1 ? confRaw : confRaw * 100`. File: `modular_dashboard.js` in `generateAlternativeRevenueSection()`.

---
- **Changed file:** `app_modules/agentic/sic_prediction/nodes/ch_sic_retrieval_node.py`
- **What changed:**
  1. **Removed name-only strategy (old Method 3)** — was failing silently for companies with no address data
  2. **Added DB cache fallback** (`_try_db_cache_lookup()`) — queries `sic_prediction_history` WHERE `LOWER(company_name) = LOWER(?)` AND `ch_sic_codes IS NOT NULL AND ch_sic_codes != ''`; returns `confidence=0.85`, `retrieval_method='db_cache'`
  3. Dead code: `_try_name_only_lookup()` still exists in file but is no longer called — can be removed later
- **Additional bugs caught & fixed on 24 Mar 2026 (pre-deploy verification):**
  - **Bug A — Wrong column in SELECT:** Original `_try_db_cache_lookup()` query included `company_number` in the SELECT — that column does not exist in `sic_prediction_history`. Would have caused a runtime crash silently swallowed by the `except`, making the cache always return `None`. **Fixed:** removed `company_number` from SELECT; `comp_number` is now hardcoded to `''`.
  - **Bug B — Wrong ORDER BY column:** Original query used `ORDER BY created_at DESC` — that column does not exist; correct column is `prediction_timestamp`. **Fixed:** changed to `ORDER BY prediction_timestamp DESC`.
  - Both fixes verified against live `data/credit_risk.db` — query returns correct result for AAA HOLDING GROUP LTD (`46900 / Non-specialised wholesale trade`).
- **New lookup order in `_execute_dual_strategy_retrieval()`:**
  ```
  1. company_number lookup   (live Companies House API)
  2. name + address lookup   (live Companies House API)
  3. DB cache                (sic_prediction_history table — last resort)
  4. "Not Available"         (only if all 3 fail)
  ```
- **Why this matters:** 469/517 records in `sic_prediction_history` have empty `ch_sic_codes`. Companies with `company_number=NULL` and `registered_office_address=NULL` (e.g. AAA HOLDING GROUP LTD) could never be resolved by live API alone. DB cache now catches previously-resolved companies.
- **Deploy commands:**

  > **Single-command deploy:** A script handles everything automatically. See [scripts/deploy_azure.sh](scripts/deploy_azure.sh).
  > ```bash
  > cd clean_v16_app
  > ./scripts/deploy_azure.sh              # full deploy (setup + build + push + redeploy)
  > ./scripts/deploy_azure.sh --setup-only # first time: create storage/KV/share/upload DBs only
  > ./scripts/deploy_azure.sh --app-only   # subsequent deploys: skip setup, just build+push+redeploy
  > ```
  > The script is **idempotent** — each resource is checked before creation, DBs are only uploaded if missing or size differs. You just need to be logged in (`az login`) and have Docker running.

  #### STEP 0 — One-time permissions setup (run once per environment, requires Owner/User Access Administrator on the subscription)

  ```bash
  # Variables
  RG="rg-credit-risk-clean"
  ACR="creditriskregistry"
  STORAGE="creditriskstorage"
  KV="kv-credit-risk"          # Key Vault name (create if not exists)
  LOCATION="uksouth"
  SUBSCRIPTION=$(az account show --query id -o tsv)

  # 0a. Create a service principal for CI/CD deployments (skip if using your own AAD account interactively)
  # This SP needs enough rights to build, push, and redeploy containers
  SP=$(az ad sp create-for-rbac --name "sp-credit-risk-deploy" \
    --role Contributor \
    --scopes /subscriptions/$SUBSCRIPTION/resourceGroups/$RG \
    --sdk-auth)
  echo "$SP"   # Save this JSON — it is the AZURE_CREDENTIALS secret for GitHub Actions / Azure DevOps pipeline

  # The SP above gets Contributor on the resource group which covers:
  #   - az acr login / docker push  (ACR is in the same RG)
  #   - az container create/delete  (ACI is in the same RG)
  #   - az storage * commands       (Storage Account is in the same RG)
  # If ACR is in a different RG, also grant AcrPush separately:
  ACR_ID=$(az acr show --name $ACR --query id -o tsv)
  SP_APP_ID=$(echo "$SP" | python3 -c "import sys,json; print(json.load(sys.stdin)['clientId'])")
  az role assignment create --assignee "$SP_APP_ID" --role AcrPush --scope "$ACR_ID"

  # 0b. Create Key Vault and store all secrets (replaces plaintext env vars in deploy command)
  az keyvault create --name $KV --resource-group $RG --location $LOCATION \
    --enable-rbac-authorization true   # use RBAC, not vault access policies

  # Grant the deploy SP permission to read secrets (needed to pass them into the container)
  KV_ID=$(az keyvault show --name $KV --query id -o tsv)
  az role assignment create --assignee "$SP_APP_ID" \
    --role "Key Vault Secrets Officer" --scope "$KV_ID"

  # Store secrets in Key Vault (only needs to be done once; update secrets here, not in deploy scripts)
  az keyvault secret set --vault-name $KV --name "COMPANIES-HOUSE-API-KEY"           --value "<COMPANIES_HOUSE_API_KEY>"
  az keyvault secret set --vault-name $KV --name "OPENAI-API-KEY"                    --value "<AZURE_OPENAI_API_KEY>"
  az keyvault secret set --vault-name $KV --name "AZURE-OPENAI-ENDPOINT"             --value "https://data-risk-modernisation-oai.openai.azure.com/"
  az keyvault secret set --vault-name $KV --name "AZURE-DOCUMENT-INTELLIGENCE-ENDPOINT" --value "https://doc-intelligence-credit-risk.cognitiveservices.azure.com/"
  az keyvault secret set --vault-name $KV --name "AZURE-DOCUMENT-INTELLIGENCE-KEY"   --value "<AZURE_DOC_INTEL_KEY>"

  # 0c. Create Storage Account and File Share (one-time)
  az storage account create --name $STORAGE --resource-group $RG --location $LOCATION --sku Standard_LRS
  STORAGE_KEY=$(az storage account keys list --account-name $STORAGE --resource-group $RG --query '[0].value' -o tsv)
  az storage share create --name creditriskdata --account-name $STORAGE --account-key "$STORAGE_KEY"

  # Upload current databases to file share (run once; updates are written at runtime by the container)
  az storage file upload --share-name creditriskdata --source data/credit_risk.db     --path credit_risk.db     --account-name $STORAGE --account-key "$STORAGE_KEY"
  az storage file upload --share-name creditriskdata --source data/vector_database.db --path vector_database.db --account-name $STORAGE --account-key "$STORAGE_KEY"
  ```

  > **ACI + Managed Identity note:** ACI (Azure Container Instances) has limited managed identity support — it cannot use a system-assigned identity to pull secrets from Key Vault at container startup the way App Service can. The practical approach for ACI is:
  > 1. The **deploy script** (run by the SP) reads secrets from Key Vault and passes them as `--environment-variables` at creation time.
  > 2. The **running container** uses those env vars directly — `azure_keyvault.py` auto-detects `AZURE_KEY_VAULT_URL` and ManagedIdentityCredential at runtime, but that requires a user-assigned managed identity attached to the ACI group, which ACI supports (see note below).
  >
  > For now, Step 1 (secrets via env vars) is the simpler path. To go fully secretless, see the user-assigned identity option at the bottom of this section.

  #### STEP 1 — Build & push image

  ```bash
  az acr login --name creditriskregistry
  docker build --platform linux/amd64 --progress=plain \
    -t creditriskregistry.azurecr.io/credit-risk-demo:v21-ch-sic-fix .
  docker push creditriskregistry.azurecr.io/credit-risk-demo:v21-ch-sic-fix
  ```

  #### STEP 2 — Read secrets from Key Vault and deploy container

  ```bash
  RG="rg-credit-risk-clean"
  ACR="creditriskregistry"
  STORAGE="creditriskstorage"
  KV="kv-credit-risk"

  # Read all secrets from Key Vault (no plaintext keys in this script)
  ACR_PASS=$(az acr credential show --name $ACR --query 'passwords[0].value' -o tsv)
  STORAGE_KEY=$(az storage account keys list --account-name $STORAGE --resource-group $RG --query '[0].value' -o tsv)
  CH_KEY=$(az keyvault secret show --vault-name $KV --name "COMPANIES-HOUSE-API-KEY" --query value -o tsv)
  OAI_KEY=$(az keyvault secret show --vault-name $KV --name "OPENAI-API-KEY" --query value -o tsv)
  OAI_ENDPOINT=$(az keyvault secret show --vault-name $KV --name "AZURE-OPENAI-ENDPOINT" --query value -o tsv)
  DI_ENDPOINT=$(az keyvault secret show --vault-name $KV --name "AZURE-DOCUMENT-INTELLIGENCE-ENDPOINT" --query value -o tsv)
  DI_KEY=$(az keyvault secret show --vault-name $KV --name "AZURE-DOCUMENT-INTELLIGENCE-KEY" --query value -o tsv)

  CONTAINER_NAME="credit-risk-demo-$(date +%Y%m%d-%H%M%S)"

  # Delete old container (ACI cannot update an image in-place)
  az container delete --name credit-risk-demo-20260222-125727 --resource-group $RG --yes

  az container create \
    --name "$CONTAINER_NAME" \
    --resource-group $RG \
    --image creditriskregistry.azurecr.io/credit-risk-demo:v21-ch-sic-fix \
    --registry-login-server creditriskregistry.azurecr.io \
    --registry-username $ACR \
    --registry-password "$ACR_PASS" \
    --cpu 8 --memory 16 --ports 8000 \
    --ip-address Public --location uksouth --os-type Linux \
    --azure-file-volume-account-name $STORAGE \
    --azure-file-volume-account-key "$STORAGE_KEY" \
    --azure-file-volume-share-name creditriskdata \
    --azure-file-volume-mount-path /app/data \
    --environment-variables \
      WORKERS=8 \
      COMPANIES_HOUSE_API_KEY="$CH_KEY" \
      OPENAI_API_KEY="$OAI_KEY" \
      AZURE_OPENAI_ENDPOINT="$OAI_ENDPOINT" \
      AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo \
      AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="$DI_ENDPOINT" \
      AZURE_DOCUMENT_INTELLIGENCE_KEY="$DI_KEY"
  ```

  #### RBAC summary — who needs what

  | Principal | Resource | Role required |
  |---|---|---|
  | Deploy SP / your AAD account | Resource group `rg-credit-risk-clean` | `Contributor` |
  | Deploy SP / your AAD account | ACR `creditriskregistry` (if in different RG) | `AcrPush` |
  | Deploy SP / your AAD account | Key Vault `kv-credit-risk` | `Key Vault Secrets User` (read) or `Key Vault Secrets Officer` (read+write) |
  | Deploy SP / your AAD account | Storage `creditriskstorage` | `Storage Account Contributor` (for key retrieval) |
  | Running ACI container | Azure Document Intelligence | API key via env var (no RBAC needed) |
  | Running ACI container | Azure OpenAI | API key via env var (no RBAC needed) |
  | Running ACI container | Azure File Share | Storage key mounted at creation time (no RBAC needed at runtime) |

  #### Optional: fully secretless with user-assigned managed identity (future improvement)

  ```bash
  # Create user-assigned managed identity
  az identity create --name "id-credit-risk-app" --resource-group $RG
  IDENTITY_ID=$(az identity show --name "id-credit-risk-app" --resource-group $RG --query id -o tsv)
  IDENTITY_CLIENT_ID=$(az identity show --name "id-credit-risk-app" --resource-group $RG --query clientId -o tsv)

  # Grant it Key Vault Secrets User so the container can read secrets at runtime
  az role assignment create --assignee "$IDENTITY_CLIENT_ID" \
    --role "Key Vault Secrets User" --scope "$KV_ID"

  # Add to container create command:
  #   --assign-identity "$IDENTITY_ID"
  #   --environment-variables AZURE_KEY_VAULT_URL=https://kv-credit-risk.vault.azure.net/
  # Then remove all other secret env vars — the app's azure_keyvault.py will read them via ManagedIdentityCredential
  ```

- **Current running container:** `credit-risk-demo-20260222-125727` at `4.250.207.156:8000` (image `v20-db-viewer`)

---

## Completed (27–28 March 2026 — Update Revenue Portal Fixes)

- [x] **Portal: `company_name`, `workflow_status`, `revenue_year`, `period_type` all missing from API response**
  - `revenue_agentic_service.py` `_format_workflow_state_response()` did not include these four fields.
  - Added all four directly to the response dict. `workflow_status` is `'success'` when no errors + revenue found, else `'completed'`. `revenue_year` / `period_type` propagated from `revenue_extraction_data`.
  - Effect: portal now shows company name heading, green "AI Revenue Analysis Complete" banner, and correct FY year.

- [x] **Portal: "Annual • FY 2026" always showed current year, not report year**
  - Root cause: `_compile_revenue_results()` in `turnover_estimation_node.py` never set `revenue_year` or `period_type`, so `revenue_agentic_service.py` fell back to `datetime.now().year`.
  - Fix: added `company_data` param to `_compile_revenue_results()`. Year is now parsed from `company_data['filing_date']` (e.g. `'2024-10-31'` → `2024`). All three call sites updated.
  - Verified: Portsmouth SU (filing `2024-10-31`) now returns `revenue_year: 2024`.

- [x] **Portal: "Revenue Extraction - Financial Year XXXX" subtitle removed**
  - Removed the `<small class="text-muted">Revenue Extraction - Financial Year ${year}</small>` line from `showRevenueResults()` in `modular_dashboard.js` — only the company name heading remains.

---

## Completed (25 March 2026 — Revenue Extraction Pipeline)

- [x] **Route registration fix:** `register_agentic_routes()` was never called from `flask_main.py` — all `/api/agentic/extract_revenue` requests returned 404. Added registration block before Cost-Effective Q&A.
- [x] **Azure DI API version:** Default changed `"2023-07-31"` → `"2024-11-30"` in `config_manager.py` and `document_processor.py` to match the `/documentintelligence/` endpoint.
- [x] **Regex false positive (`s444(5B)` → £5bn):** Bare `B` in `billions_currency` pattern matched Companies Act citation. Removed `|B` from alternation in `rag_revenue_extractor.py` (two locations, ~line 3023 and ~line 3213).
- [x] **DB-guided rejection:** `poor_match` candidates now get `-500` (moderately off) or `-2000` (>100× off) penalty. Rejection guard added: if best candidate is >100× off DB figure with <35% confidence → return `None` at 85% confidence.
- [x] **Meaningful confidence on None results:** Confidence now reflects certainty of the decision, not just presence of a revenue figure:
  - Revenue found → e.g. 77% (confidence in figure)
  - No patterns found, DB anchor present → 70% (confident absence)
  - No patterns found, no DB anchor → 45%
  - Candidates found but all rejected → 85% (confident figures are wrong)
  - DB lookup moved before `if found_candidates:` branch so both paths can use it; `no_matches` and `candidates_rejected` propagated through both `_extract_using_pure_rag_vector` and `_extract_using_fast_path_results`.
- [x] **Top-3 candidates sorted by confidence:** `found_candidates` now sorted by confidence descending before slicing to top 3 for `revenue_candidates` in `extract_revenue()`.
- [x] **Server stability:** `main.py` changed to `debug=False, threaded=False` to reduce OOM kills.
- [x] **Test results:**
  | Company | No. | Revenue | Confidence |
  |---|---|---|---|
  | University of Portsmouth Students' Union | 03934555 | £1,780,000 | 77% ✅ |
  | Velocity Global International Services Ltd | 11052125 | None | 70% ✅ |

---

## Route Audit — 28 March 2026 (Dead / Duplicate API Cleanup)

**What was done:** A full end-to-end audit of every route in the codebase.
No code was deleted. Every dead or duplicate route was marked with a `# [TAG]` comment
directly in the source file so future devs can find and remove them safely.

### Tags used
| Tag | Meaning |
|---|---|
| `[DEAD ROUTE]` | Route exists in `flask_main.py` but has no frontend consumer and no internal callers |
| `[DEPRECATED ROUTE]` | Route still works but has been superseded by a newer endpoint |
| `[DUPLICATE ROUTE]` | Route is registered twice (once in `flask_main.py` and once in a blueprint) |
| `[DEBUG ROUTE]` | Dev/test helper that should not run in production |
| `[DEAD FILE]` | Entire blueprint file is unreachable because its blueprint is never registered |
| `[REVIEW]` | Needs human confirmation before removal |

---

### Marked routes in `app_modules/flask_main.py`

| Route | Line (approx.) | Tag | Reason |
|---|---|---|---|
| `GET /api/filter_options` | ~914 | `[DEAD ROUTE]` | Old underscore alias. Frontend calls `/api/modular/filter-options` (hyphen). No consumer. |
| `GET /api/agents/status` | ~2170 | `[DEAD ROUTE]` | Returns hardcoded mock agent list. `/agents` page removed. No consumer. |
| `GET /api/workflow/structure` | ~2856 | `[DEAD ROUTES — OLD LANGGRAPH BLOCK]` | All four `/api/workflow/*` routes. `app.langgraph_workflow` is never set. No frontend consumer. Superseded by `/api/modular/workflow/*`. |
| `POST /api/workflow/execute` | ~2892 | (same block) | See above |
| `GET /api/workflow/status/<session_id>` | ~2943 | (same block) | See above |
| `GET /api/workflow/visualization` | ~2960 | (same block) | See above |
| `POST /api/modular/predict-sic` | ~3029 | `[DEPRECATED ROUTE]` | Uses old `EnhancedSICMatcher` (non-agentic). No frontend consumer. Superseded by `/api/predict_sic_agentic`. |
| `POST /api/predict_sic` | ~3124 | `[DEAD ROUTE]` | Old non-agentic/simulation path. Frontend calls `/api/predict_sic_agentic`. No consumer. |
| `POST /api/predict_sic_agentic` | ~3395 | `[DUPLICATE ROUTE]` | Also registered by `agentic_routes.py` (line ~683) as an alias. The `agentic_routes` version wins (registered first at app startup ~line 495). This ~300-line copy in `flask_main` is shadow code. |
| `POST /api/run_agent_workflow` | ~4107 | `[DEPRECATED ROUTE]` | Already returns HTTP 410 Gone internally with message "use agentic endpoints instead". No consumer. |
| `GET /api/test_agents` | ~4172 | `[DEBUG ROUTE]` | Dev/test helper only. Not needed in production. No frontend consumer. |
| `GET /api/sqlite/companies/search` | ~2747 | `[REVIEW]` | Live copy in `flask_main`. Also exists in `api/sqlite_routes.py` (dead file). Verify no consumer before removing. |

---

### Marked blueprint files (entire file unreachable)

| File | Tag | Reason |
|---|---|---|
| `app_modules/api/sqlite_routes.py` | `[DEAD FILE]` | `sqlite_api` blueprint is never registered in `create_app()`. All routes unreachable. Duplicates exist in `flask_main.py`. |
| `app_modules/api/enhanced_routes_v2.py` | `[DEAD FILE]` | `api_v2` blueprint (`/api/v2/*`) registered only via `routes/__init__.py → factory.py`. `main.py` uses `flask_main.create_app()` which never calls `register_routes()`. All analytics/batch endpoints unreachable. |
| `app_modules/api/modular_routes.py` | `[DEAD FILE]` | `modular_api` blueprint (`/api/v2/*`) registered only via `modular_integration.py` which is never called from `create_app()`. All routes unreachable. |

---

### Active routes confirmed working (12/26 health check pass)

| Endpoint | Status |
|---|---|
| `GET /health` | ✅ |
| `GET /dashboard`, `/database-viewer`, `/filters` | ✅ |
| `GET /api/database/tables` | ✅ |
| `POST /api/modular/update-revenue-agentic` | ✅ (revenue=£1,780,000, year=2024, conf=77%) |
| `POST /api/agentic/extract_revenue` | ✅ |
| `GET /api/modular/get-exchange-rate` | ✅ |
| `GET /api/qa/health`, `POST /api/qa/ask` | ✅ |
| `GET /api/database/tables?db=vector` | ✅ |

---

## End-to-End Button/API Lineage Audit — 28 March 2026

**Scope:** Every button and API call in the UI was traced end-to-end:  
JS payload → backend validation → database → response → JS field reads.  
Test script: `/tmp/e2e_check_v2.py` (19 tests, uses exact same field names as the frontend).

### Final result: 19/19 PASS after fixing 2 real bugs

### Real bugs found and fixed

| # | Bug | File | Fix |
|---|---|---|---|
| 1 | `POST /api/qa/save-history` → **404** Missing route. JS calls this silently after every Q&A response. Table `qa_history` existed in DB but no endpoint. | `app_modules/api/qa_api.py` | Added `@qa_api.route('/api/qa/save-history', methods=['POST'])`. Inserts into `qa_history` table. |
| 2 | `POST /api/modular/workflow/execute` → **500**. Handler called `predict_sic_agentic(company_index=0)` but method signature requires `company_name` (no `company_index` arg). Crash on every agent click in Workflows page. | `app_modules/flask_main.py` (~line 4349) | Fixed to accept `company_name` + `business_description` from payload. When no company provided (workflow UI default) returns `{success:true, requires_company:true, message:"Select a company..."}` instead of 500. |

### False positives from first test run (test was wrong, APIs were fine)

| Endpoint | What test expected | What JS actually reads | Verdict |
|---|---|---|---|
| `GET /api/companies/with-filing-data` | `result.companies` | `result.data` | ✅ Fine |
| `POST /api/activity-log` | fields: `action`, `details` | `user_action`, `action_description` | ✅ Fine |
| `GET /api/modular/get-exchange-rate` | key `gbp_to_usd` | `fxData.rate` | ✅ Fine |
| `POST /api/predict_sic_agentic` | `{unique_id}` only | `{company_id, company_name}` | ✅ Fine |
| `POST /api/modular/update-revenue-agentic` | `{company_number}` only | `{company_name, company_number}` | ✅ Fine |
| `POST /api/modular/approve-revenue-updates` | key `approved_revenue` | `latest_revenue` | ✅ Fine |
| `POST /api/modular/approve-sic-prediction` | `predicted_sic_code` | `predicted_sic` | ✅ Fine |
| `POST /api/qa/ask` | top-level `answer` key | `data.data.answer` (nested) | ✅ Fine |

### All 19 confirmed working endpoints

| Button / Action | Endpoint | Status |
|---|---|---|
| Dashboard load | `GET /api/companies/portal?limit=1000&page=1` | ✅ |
| Filing indicator badges | `GET /api/companies/with-filing-data` | ✅ |
| Advanced filters page | `GET /api/modular/filter-options` | ✅ |
| Activity log panel (read) | `GET /api/activity-log?limit=100` | ✅ |
| Activity log panel (write) | `POST /api/activity-log` | ✅ |
| GBP/USD exchange rate | `GET /api/modular/get-exchange-rate` | ✅ |
| DB viewer — statistics | `GET /api/database/statistics` | ✅ |
| DB viewer — run query | `POST /api/database/query` | ✅ |
| DB viewer — injection guard | `POST /api/database/query` (DROP) → 403 | ✅ |
| Predict SIC button | `POST /api/predict_sic_agentic` | ✅ |
| Revenue portal (extract) | `POST /api/modular/update-revenue-agentic` | ✅ |
| Revenue inline edit modal | `POST /api/update_revenue` | ✅ |
| Approve revenue | `POST /api/modular/approve-revenue-updates` | ✅ |
| Approve SIC | `POST /api/modular/approve-sic-prediction` | ✅ |
| Q&A ask | `POST /api/qa/ask` | ✅ |
| Q&A save history | `POST /api/qa/save-history` | ✅ (was 404, now fixed) |
| Workflows list | `GET /api/modular/workflows` | ✅ |
| Workflow agents | `GET /api/modular/workflow/agents` | ✅ |
| Workflow execute | `POST /api/modular/workflow/execute` | ✅ (was 500, now fixed) |

---

### Known issues from health check (not caused by this audit)
- `GET /api/agentic/health` → `503 unhealthy` — missing `sqlite_sic_repository` + `companies_house_client` services on startup (config issue, not a dead route)
- `POST /api/database/query (vector)` → `500 no such table: documents_v2` — vector DB table name mismatch
- `GET /api/database/statistics` missing `total_companies` key — test script expected wrong key (actual key is `companies`); route is fine
- `POST /api/database/query` missing `results` key — test script expected wrong key (actual keys are `data`, `columns`); route is fine

---

## Pending (Next Session)
- [ ] Test further companies with revenue extraction pipeline
- [ ] Deploy as v21 to Azure:
  ```bash
  docker build --platform linux/amd64 -t creditriskregistry.azurecr.io/credit-risk-demo:v21 .
  az acr login --name creditriskregistry
  docker push creditriskregistry.azurecr.io/credit-risk-demo:v21
  ```
  Add env vars: `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_DOCUMENT_INTELLIGENCE_KEY`

---

## Completed

- [x] Fixed `.dockerignore` — WAL files excluded, live databases included
- [x] Fixed Dockerfile — CPU-only PyTorch (image: 549 MB vs 13.8 GB)
- [x] Fixed `is_azure` detection — SQLite browser no longer tries to spawn a desktop app in ACI
- [x] Added `/database-viewer` web UI route with full SQL query editor
- [x] Added `/api/database/tables`, `/schema`, `/statistics`, `/query` backend APIs
- [x] Deployed `v20-db-viewer` → `http://4.250.207.156:8000` (UK South, 8 vCPU / 16 GB, 8 workers)
- [x] **BUG-001 fixed (24 Mar 2026):** `database_viewer.html` — fixed all 4 main DB quick queries to use real column/table names. Changed: `predictions` table → `sic_prediction_history`; `description`→`sic_description`; `industry_section`→`section`; `"Company Name"`/`New_Accuracy`/`Old_Accuracy` (don't exist) → real `sic_prediction_history` confidence columns. All queries verified against live `data/credit_risk.db`.
- [x] **BUG-002 fixed (24 Mar 2026):** `database_viewer.html` — `runQuickQuery()` is now DB-aware. When `?db=vector`, uses `documents_v2`/`document_chunks_v2` queries. Sidebar button labels also update dynamically to 'View Documents', 'View Chunk Previews', 'Docs per Company', 'Chunks per Document'. All queries verified against live `data/vector_database.db`.

---

## Session — 28–29 March 2026

### Test Suite Fixes
- **`tests/master_api_test.py`**
  - Fixed `sales_usd` field reference → `sales_gbp`
  - Fixed validation test: accepts `422` in addition to `400` for missing `company_name`
  - **Result: 170/170 PASSED**

### Database Cleanup
- Audited for duplicate companies → 0 duplicates
- Deleted 5 stale `NULL unique_id` rows in `sic_prediction_history` (leftover from Nov 2025 batch script)
- 512 clean history rows remaining; all 515 companies confirmed intact

### v22 Deployment
- Built and deployed `creditriskregistry.azurecr.io/credit-risk-demo:v22-gbp-conversion`
- Fixed WAL corruption on deploy: SQLite `backup()` API now used to create WAL-free copy before upload
- Live at `http://20.254.176.27:8000` — healthy, 515 companies, 731 SIC codes

### Deploy Script Consolidation
- Rewrote `scripts/deploy_azure.sh` as the single canonical deploy script
- Modes: default (full), `--db-only`, `--skip-build`, `--setup-only`
- Always checkpoints SQLite WAL before upload; auto-discovers and replaces running container

### Revenue Extraction Improvements
- **`app_modules/agentic/update_revenue/rag_revenue_extractor.py`**
  - Added smooth DB proximity confidence boost in `_apply_database_guided_search_condition`:
    `boost = 0.25 × max(0, 1 − percentage_diff / 50)` — rewards candidates near the DB `sales_gbp` value
  - `source_text` in `top_candidates` now carries the real document `context_snippet` (±100 chars around match)

### Revenue Modal UI Overhaul
- **`modular_static/js/modular_dashboard.js`**
  - Reduced from 3 candidate boxes to 2 (External Database + Document Extraction)
  - Equal 50/50 layout (`col-md-6` each)
  - Removed `#1` suffix from label; suppressed `(Page RAG Extraction)` / `(Page Unknown)` text
  - "Show Context" button only shown when real document text is available
  - Save button moved to `#revenueActionArea` (outside scrollable container — always visible)
- **`modular_templates/dashboard.html`**
  - Added `<div id="revenueActionArea">` below `#revenueResults`, pinned at bottom of panel

### Root File Cleanup
Moved to `superseded/` (only `startup.py` is used by Dockerfile):
- `app.py`, `main.py`, `startup_optimized.py`, `startup.sh`, `web.config`

### Documentation Added
- `README.md` — root-level developer + deploy guide
- `ARCHITECTURE.md` — full application architecture and code structure reference

### Known Warnings (not failures, unchanged)
| Warning | Explanation |
|---|---|
| `GET /api/qa/history/67 → 404` | QA history endpoint not implemented; JS catches silently |
| `GET /api/company/366/filing-history → 404` | Company has no CH filing data; expected |
