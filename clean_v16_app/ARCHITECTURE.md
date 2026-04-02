# Architecture — Credit Risk Analysis Tool

> **Purpose of this document:** Comprehensive codebase walkthrough for handover. Covers system overview, all modules, agentic workflows, data model, API catalogue, frontend, and Azure infrastructure.

---

## 1. System Overview

The Credit Risk Analysis Tool is a Flask web application that:

1. Fetches UK company filing data from the **Companies House API**.
2. Downloads annual report PDFs and chunks them into vector embeddings stored in a local SQLite vector database.
3. **Extracts revenue (turnover)** from those documents using a 3-node LangGraph RAG workflow.
4. **Predicts SIC codes** for companies using a 5-node LangGraph multi-agent AI reasoning workflow.
5. Presents everything through a browser-based dashboard backed by a REST API.

All data (company info, financials, predictions, history) lives in two SQLite files that are volume-mounted from Azure File Share in production, meaning data persists across container restarts.

---

## 2. Repository Layout

```
clean_v16_app/
│
├── startup.py                      # WSGI entry point — Gunicorn reads this
├── Dockerfile                      # Multi-stage; CMD: gunicorn startup:app -b 0.0.0.0:8000
├── requirements.txt
│
├── app_modules/                    # All application Python (see §4)
│   └── flask_main.py               # App factory: create_app()
│
├── modular_templates/              # Jinja2 HTML templates — served by main_routes
├── modular_static/                 # Frontend assets
│   ├── js/modular_dashboard.js     # Single JS file ~7300 lines — all dashboard logic
│   └── css/
│
├── data/                           # SQLite databases (mounted from Azure File Share in prod)
│   ├── credit_risk.db              # ← main application database
│   └── vector_database.db          # ← document embeddings for RAG
│
├── tests/
│   └── master_api_test.py          # 170-test integration suite (NOT pytest format)
│
├── scripts/
│   └── deploy_azure.sh             # Single canonical deploy script
│
├── azure_deployment/               # Azure-specific docs and config
│   └── README.md                   # Detailed deploy guide
│
├── batch/                          # Offline one-shot scripts (SIC confidence calculator)
├── config/                         # Database schema JSON
├── logs/                           # Runtime logs (not committed)
└── superseded/                     # Archived/replaced files for reference — NOT deployed
```

---

## 3. Entry Point & Startup

### `startup.py`

The only Python file at the root used at runtime. Does three things:

1. Calls `create_app()` from `app_modules/flask_main.py` and assigns the result to `app`.
2. Exposes `app` at module level so Gunicorn can import it (`gunicorn startup:app`).
3. Has an `if __name__ == "__main__"` block for local dev (`python3 startup.py`).

### `Dockerfile`

```dockerfile
# Multi-stage build (builder stage installs deps, runtime stage is lean)
CMD ["gunicorn", "startup:app", "--bind", "0.0.0.0:8000", ...]
```

Key build choices:
- CPU-only PyTorch (avoids ~2 GB GPU layers)
- Non-root user `appuser`
- Mounts `data/` from Azure File Share at `/app/data` in production

---

## 4. `app_modules/` — Application Code

### 4.1 `flask_main.py` — App Factory

`create_app()` is the central bootstrap function. It:

1. Creates the Flask app and configures it from `app_modules/config/app_config.py`.
2. Sets up CORS, logging, and middleware.
3. Registers all blueprints (QA API, vectorisation API, SQLite routes, etc.).
4. Registers every route inline (all `@app.route` decorators live in `flask_main.py` itself — ~4600 lines).

Because so many routes are registered inside `create_app()`, there is intentional coupling. New routes should continue to be added in `flask_main.py` unless they become a logical unit large enough to justify a new blueprint file.

---

### 4.2 `agentic/` — LangGraph Workflows

Two fully separate LangGraph `StateGraph` pipelines.

#### 4.2.1 SIC Code Prediction Workflow

**Entry:** `POST /api/predict_sic_agentic` or `POST /api/modular/predict-sic`  
**Orchestrated by:** `agentic/sic_prediction/sic_service.py` → `workflow_builder.py`

```
data_ingestion
    │
    ▼
ch_sic_retrieval          ← Companies House live SIC lookup via API
    │
    ▼  (conditional)
ai_prediction             ← GPT-4o predicts SIC from company name + description
    │
    ├─ [reflection enabled] ─► reflection_evaluation   ← evaluates confidence; may loop
    │                                │
    │                                ▼ (conditional)
    │                          reasoning_generation    ← produces human-readable explanation
    │
    └─ [reflection disabled] ─────────────────────────►
                                                        workflow_finalizer → END
```

**Nodes:**

| File | Node name | What it does |
|---|---|---|
| `data_ingestion_node.py` | `data_ingestion` | Loads company record from DB, enriches context |
| `ch_sic_retrieval_node.py` | `ch_sic_retrieval` | Calls Companies House API to get current SIC codes |
| `ai_prediction_node.py` | `ai_prediction` | Sends full prompt to Azure OpenAI; returns predicted SIC + confidence |
| `reflection_node.py` | `reflection_evaluation` | Self-evaluates prediction; loops if confidence below threshold |
| `reasoning_generator_node.py` | `reasoning_generation` | Generates structured explanation for the UI |

**State:** `workflow_state.py::AgenticWorkflowState` (TypedDict)

---

#### 4.2.2 Revenue Extraction Workflow

**Entry:** `POST /api/modular/update-revenue-agentic`  
**Pre-check:** `GET /api/vectorization/revenue-precheck/<company_number>`  
**Orchestrated by:** `agentic/update_revenue/revenue_agentic_service.py`

```
START
  │
  ▼
company_data_ingestion    ← loads company + existing financials from DB
  │
  ▼
financial_extraction      ← Azure Document Intelligence parses PDF fields
  │
  ▼
turnover_estimation       ← RAG vector search + LLM to identify best revenue figure
  │
  ▼
END
```

**Nodes:**

| File | Node name | What it does |
|---|---|---|
| `company_data_ingestion_node.py` | `company_data_ingestion` | Fetches company record, existing `sales_gbp`, filing URL |
| `financial_extraction_node.py` | `financial_extraction` | Calls Azure Document Intelligence on PDF; extracts key financials |
| `turnover_estimation_node.py` | `turnover_estimation` | Calls `rag_revenue_extractor.py`; returns primary + alternative candidates |

**Core extractor:** `agentic/update_revenue/rag_revenue_extractor.py`

The revenue extractor is the most complex component (~3700 lines). Key methods:

- `extract_revenue()` — main entry point; orchestrates the pipeline below.
- `_search_vector_database()` — embeds a query (using `all-MiniLM-L6-v2`) and retrieves the top-k semantically similar chunks.
- `_apply_database_guided_search_condition()` — retrieves existing `sales_gbp` from the DB and applies a **proximity confidence boost**: candidates within ±50% of the known value receive up to +0.25 confidence boost, decaying linearly. Formula: `boost = 0.25 × max(0.0, 1.0 − (percentage_diff / 50.0))`.
- `_extract_revenue_amounts()` — regex-based numeric extraction from chunk text.
- `_score_candidates()` — weights pattern quality, semantic similarity, page position, and proximity boost.
- `top_candidates` assembly — the final ranked list; `source_text` is set to `context_snippet` (real document text, not synthetic labels like `"Pattern: X"`).

**State:** `revenue_workflow_state.py::RevenueWorkflowState` (TypedDict)

---

### 4.3 `agents/` — Standalone Agents (Legacy)

Individual agent classes that pre-date the LangGraph integration. Still used for the non-agentic workflow (`/api/run_agent_workflow`) and QA.

| File | Purpose |
|---|---|
| `base_agent.py` | Base class with logging, error handling |
| `orchestrator.py` | Coordinates multiple agents in a pipeline |
| `data_ingestion_agent.py` | Fetches company data |
| `document_download_agent.py` | Downloads PDFs from Companies House |
| `rag_document_agent.py` | RAG queries over downloaded documents |
| `smart_financial_extraction_agent.py` | Pattern-based financials from text |
| `turnover_estimation_agent.py` | Turnover estimation from extracted text |
| `ai_reasoning_agent.py` | Wrapper over Azure OpenAI for reasoning tasks |

---

### 4.4 `api/` — Flask Blueprint Modules

These are registered as blueprints in `flask_main.py`:

| File | Prefix | Purpose |
|---|---|---|
| `qa_api.py` | `/api/qa/` | Ask a question about a document; save Q&A history |
| `vectorization_api.py` | `/api/vectorization/` | Check vectorisation status; revenue precheck |
| `simple_sqlite_routes.py` | `/api/sqlite/` | Health check, counts (lightweight diagnostics) |
| `sqlite_routes.py` | `/api/sqlite/` | Full company/SIC browse API, advanced search |
| `modular_routes.py` | — | Older modular API (partially superseded by flask_main routes) |
| `enhanced_routes_v2.py` | — | V2 analytics/search API |

---

### 4.5 `apis/` — External API Clients

| File | Purpose |
|---|---|
| `companies_house_client.py` | Companies House REST API — search, profile, filing history |
| `unified_api_service.py` | Unified wrapper that may call multiple external APIs |
| `web_scraper.py` | Fallback scraper for financial data not in Companies House |

---

### 4.6 `config/`

| File | Purpose |
|---|---|
| `app_config.py` | All configuration (`AppConfig` class) — reads env vars, provides defaults |
| `api_config.yaml` | YAML config read at startup for API keys, timeouts, endpoints |
| `databricks_config.py` | (Legacy remnant) Databricks connection config — not used in current deploy |

---

### 4.7 `database/`

| File | Purpose |
|---|---|
| `connection.py` | SQLite connection pool; `get_connection()` returns thread-local connections |
| `models.py` | Table definitions (companies, financials, SIC history, etc.) and schema init |
| `vector_connection.py` | Separate connection to `vector_database.db`; loads `sqlite-vec` extension |
| `optimized_vector_db.py` | Batch upsert, HNSW index operations for the vector DB |

---

### 4.8 `rag/`

`optimized_rag_engine.py` — Standalone RAG engine used by the Q&A feature. Separate from the revenue extractor's built-in vector search.

---

### 4.9 `services/`

High-level business service layer called from route handlers:

| File/Folder | Purpose |
|---|---|
| `company_service.py` | CRUD for companies, enrichment, financials lookup |
| `filing_history_service.py` | Fetch + store Companies House filing history |
| `sic_service.py` | SIC code lookup, prediction invocation, approval, history |
| `update_revenue_service.py` | Revenue extraction invocation and approval |
| `qa/` | Q&A session management |
| `embedding/` | Document embedding pipeline (chunking → vector store) |

---

### 4.10 `routes/`

| File | Purpose |
|---|---|
| `main_routes.py` | HTML page routes (dashboard, database viewer, etc.) |
| `api_routes.py` | Thin shim API routes |

> Note: most routes are defined directly in `flask_main.py`, not here. `main_routes.py` handles template rendering.

---

### 4.11 `utils/`

| File | Purpose |
|---|---|
| `logger.py` | Structured logger; writes to `logs/` |
| `input_validation.py` | Validation helpers for API inputs — used at all external boundaries |
| `simulation.py` | Demo-mode data generator (not used in production) |

---

## 5. Database Schema

### `data/credit_risk.db`

| Table | Key columns | Notes |
|---|---|---|
| `companies` | `id`, `company_name`, `company_number`, `unique_id`, `sic_code`, `status` | Master company record |
| `company_financials` | `company_id`, `sales_gbp`, `profit_gbp`, `year`, `period_type`, `currency_raw` | One row per financial year |
| `company_sic_codes` | `sic_code`, `sic_description`, `sic_division` | SIC lookup (UK 2007 classification) |
| `sic_prediction_history` | `company_id`, `predicted_sic`, `confidence`, `source`, `status`, `created_at` | Every prediction run |
| `filing_history` | `company_id`, `filing_date`, `description`, `document_url`, `filing_type` | Companies House filings |
| `qa_history` | `company_id`, `question`, `answer`, `source_doc`, `created_at` | Q&A question/answer log |
| `activity_log` | `action`, `company_id`, `user`, `timestamp`, `details` | User action audit trail |
| `api_audit_log` | `endpoint`, `method`, `status_code`, `response_time_ms`, `timestamp` | API call metrics |

### `data/vector_database.db`

Managed by `sqlite-vec` extension. Contains:

- `document_chunks` — raw text chunks with company/document metadata.
- `chunk_embeddings` (vec table) — HNSW-indexed float32 vectors (384-dim, `all-MiniLM-L6-v2`).

---

## 6. Frontend Architecture

### `modular_static/js/modular_dashboard.js` (~7300 lines)

Single vanilla-JS file. No build step. Key sections:

| Approx lines | Component | Description |
|---|---|---|
| 1–500 | Initialisation | jQuery ready, globals, DataTable init |
| 500–1000 | Filter panel | Industry/status/financial filters; `applyFilters()` |
| 1000–2000 | Companies table | Pagination, sorting, row expand; calls `/api/companies/portal` |
| 2000–3000 | Company detail panel | Filing history, financials chart; calls `/api/company/<id>/details` |
| 3000–4000 | SIC prediction UI | `runSICPrediction()`, approval flow, history table |
| 4000–5500 | Revenue extraction UI | `runRevenueUpdate()`, `showRevenueResults()`, `generateAlternativeRevenueSection()`, approval |
| 5500–6500 | Q&A UI | `askQuestion()`, history display |
| 6500–7300 | Utilities | Toast notifications, modals, helpers |

### Revenue modal layout (post March-2026 changes)

```
┌── Revenue Update Modal ─────────────────────────────────────────┐
│  ┌──────────────────────────┐  ┌─────────────────────────────┐  │
│  │  Agentic RAG Estimate    │  │  Document Extraction        │  │
│  │  (primary LLM result)    │  │  (top RAG candidate)        │  │
│  └──────────────────────────┘  └─────────────────────────────┘  │
│  ─────────────────────────────────────────────────────────────   │  ← #revenueActionArea (outside scroll)
│  [ Save Revenue Update ]                                         │
└──────────────────────────────────────────────────────────────────┘
```

The Save button lives in `#revenueActionArea` (inserted into `dashboard.html` outside the scrollable results div) so it is always visible regardless of result height.

### `modular_templates/dashboard.html`

Jinja2 template. Notable divs:

| ID | Purpose |
|---|---|
| `#companiesTable` | DataTable container |
| `#companyDetailPanel` | Sliding detail panel |
| `#sicModal` | SIC prediction Bootstrap modal |
| `#revenueModal` | Revenue extraction Bootstrap modal |
| `#revenueResults` | Scrollable results container inside modal |
| `#revenueActionArea` | Save button host (outside scroll, always visible) |
| `#qaModal` | Q&A Bootstrap modal |

---

## 7. API Endpoint Catalogue

### Core pages (HTML)

| Route | Template | Purpose |
|---|---|---|
| `GET /` | `dashboard.html` | Redirect → `/modular-dashboard` |
| `GET /modular-dashboard` | `dashboard.html` | Main dashboard |
| `GET /database-viewer` | `database_viewer.html` | Raw DB browser |
| `GET /health` | (JSON) | Server health check |

### Companies API

| Route | Method | Purpose |
|---|---|---|
| `/api/companies` | GET | Full company list (paginated, with filters) |
| `/api/companies/portal` | GET | Dashboard portal view (search, sort, paginate) |
| `/api/company/<id>/details` | GET | Full company detail incl. financials |
| `/api/company/<id>/filing-history` | GET | Cached filing history |
| `/api/company/<id>/update-filing-history` | POST | Refresh from Companies House |

### SIC prediction

| Route | Method | Purpose |
|---|---|---|
| `/api/predict_sic_agentic` | POST | Run LangGraph SIC workflow |
| `/api/modular/predict-sic` | POST | Alias (used by modular dashboard JS) |
| `/api/modular/approve-sic-prediction` | POST | Persist approved SIC to DB |
| `/api/calculate_sic_confidence` | POST | Standalone confidence calculation |
| `/api/sic-confidence/existing/<id>` | GET | Historical confidence for a company |
| `/api/sic-confidence/batch-calculate` | POST | Batch recalculate across companies |

### Revenue extraction

| Route | Method | Purpose |
|---|---|---|
| `/api/vectorization/revenue-precheck/<company_number>` | GET | Check if docs are vectorised; return candidates |
| `/api/modular/update-revenue-agentic` | POST | Run LangGraph revenue workflow |
| `/api/modular/approve-revenue-updates` | POST | Persist approved revenue to DB |
| `/api/modular/get-exchange-rate` | GET | FX rate lookup (GBP base) |
| `/api/update_revenue` | POST | Legacy non-agentic revenue update |

### Q&A

| Route | Method | Purpose |
|---|---|---|
| `/api/qa/ask` | POST | Ask a question about a company's document |
| `/api/qa/save-history` | POST | Persist Q&A to DB |
| `/api/qa/stats` | GET | Q&A usage statistics |

### Vectorisation

| Route | Method | Purpose |
|---|---|---|
| `/api/vectorization/check/<company_number>` | GET | Is this company vectorised? |
| `/api/vectorization/stats` | GET | Vector DB stats |

### Database viewer

| Route | Method | Purpose |
|---|---|---|
| `/api/database/tables` | GET | List all tables |
| `/api/database/schema/<table>` | GET | Column schema for a table |
| `/api/database/statistics` | GET | Row counts per table |
| `/api/database/query` | POST | Safe read-only SQL query execution |

### Diagnostics & utilities

| Route | Method | Purpose |
|---|---|---|
| `/api/modular/health` | GET | Agentic system health |
| `/api/modular/stats` | GET | Runtime stats |
| `/api/filter_options` | GET | Available filter values (industries, statuses) |
| `/api/activity-log` | GET / POST | Read or write activity log entries |
| `/api/agents/status` | GET | Agent system status |

---

## 8. Azure Infrastructure

### Container Instances

| Resource | Value |
|---|---|
| Container name | `credit-risk-demo-v22` |
| Resource group | `rg-credit-risk-clean` |
| Public IP | `20.254.176.27` |
| Port | `8000` |
| CPU / RAM | 2 vCPU / 4 GB |
| Location | UK South |

### Container Registry (ACR)

| Resource | Value |
|---|---|
| Registry | `creditriskregistry.azurecr.io` |
| Image tag convention | `credit-risk-demo:v{N}-{descriptor}` |
| Latest deployed | `v22-gbp-conversion` |

### Storage (Azure File Share)

| Resource | Value |
|---|---|
| Storage account | `creditriskstore` / `creditriskstorage` |
| File share | `credit-risk-db` |
| Mount point | `/app/data` inside container |
| Contents | `credit_risk.db`, `vector_database.db` |

Databases persist across container restarts because they are stored on the file share, not inside the container image.

### Key Vault

Secrets stored in Azure Key Vault and injected as environment variables at container startup.

### Key environment variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | GPT-4o deployment name |
| `COMPANIES_HOUSE_API_KEY` | Companies House API key |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Azure DI endpoint |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | Azure DI key |
| `PORT` | Server port (default 8000 in Dockerfile) |

---

## 9. Deploy Process

All deployment is via a single script:

```bash
./scripts/deploy_azure.sh
```

What the script does:
1. Checkpoints the SQLite WAL file to prevent data corruption on upload.
2. Builds and pushes a new Docker image to ACR with the next version tag.
3. Deletes the current Azure Container Instance.
4. Creates a new ACI pulling the new image, with all environment variables and the File Share mount.
5. Waits for the container to become healthy.
6. Prints the public URL.

For detailed Azure setup and first-time deployment, see [azure_deployment/README.md](azure_deployment/README.md).

---

## 10. Test Suite

**File:** `tests/master_api_test.py`  
**Format:** Custom test runner (not pytest). Run as a plain Python script against a live server.

```bash
# Terminal 1 — start server
PORT=5002 python3 startup.py

# Terminal 2 — run tests
python3 tests/master_api_test.py
```

Expected result: **170/170 PASSED — 0 FAILED**

Test coverage areas:
- Server health and page routes
- Filter options API
- Companies portal (pagination, sorting, search)
- SIC prediction end-to-end (predict → approve → DB verify)
- Revenue extraction end-to-end (precheck → extract → approve → DB verify)
- Q&A flow
- Database viewer APIs
- Input validation boundaries (malicious inputs → 400/403)
- JS ↔ backend contract audit
- Regression guards for known past bugs

---

## 11. Known Constraints & Design Decisions

| Constraint | Reason |
|---|---|
| SQLite (not PostgreSQL) | Simplicity; files mount from Azure File Share; no connection pool needed at current scale |
| Single `flask_main.py` for most routes | Keeps all route logic easy to find; blueprints only for well-defined sub-systems |
| CPU-only PyTorch in Docker | Embedding model (`all-MiniLM-L6-v2`) works fine on CPU; GPU adds 2 GB to image for no benefit |
| No `pytest` for master_api_test | Test suite predates pytest adoption; it drives a live server and verifies HTTP responses |
| Single canonical deploy script | Enforces consistent WAL checkpoint + image tagging; prevents accidental partial deploys |
| `superseded/` folder | Files are kept (not deleted) to allow audit/reference without cluttering the active codebase |
| GBP-first revenue | All stored values are in GBP; USD/EUR only converted for display if `$`/`€` appears in original text |
