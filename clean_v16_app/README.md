# Credit Risk Analysis Tool

A Flask-based web application for analysing UK company credit risk. It connects to the Companies House API to retrieve filing history, extracts revenue figures from annual reports using RAG (Retrieval-Augmented Generation), and predicts SIC codes using a multi-agent LangGraph workflow backed by Azure OpenAI.

**Live deployment:** `http://20.254.176.27:8000`  
**Architecture details:** See [ARCHITECTURE.md](ARCHITECTURE.md)  
**Change log:** See [TASKS.md](TASKS.md)  
**Azure deploy guide:** See [azure_deployment/README.md](azure_deployment/README.md)

---

## Quick Start — Local Development

### Prerequisites
- Python 3.11+
- Virtual environment (`.venv` already present in the repo)

### 1. Activate the virtual environment
```bash
cd clean_v16_app
source .venv/bin/activate
```

### 2. Set environment variables
Copy `.env.example` to `.env` (or set manually):
```bash
OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT_NAME=...
COMPANIES_HOUSE_API_KEY=...
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
```

### 3. Start the server
```bash
PORT=5002 python3 startup.py
```
App available at `http://localhost:5002`

### 4. Run all tests
The test suite requires the server to be running first:
```bash
python3 tests/master_api_test.py
```
Expected: **170/170 PASSED — 0 FAILED**

---

## Deploy to Azure

> Always use the single canonical deploy script. Do not create alternative deploy scripts.

```bash
./scripts/deploy_azure.sh
```

For full options and a step-by-step walkthrough, see [azure_deployment/README.md](azure_deployment/README.md).

---

## Project Layout

```
clean_v16_app/
├── startup.py                  # WSGI entry point (Dockerfile CMD calls this)
├── Dockerfile                  # Multi-stage build — CPU-only PyTorch, non-root user
├── requirements.txt            # Python dependencies
├── .env                        # Local secrets (never committed)
│
├── app_modules/                # All application Python code
│   ├── flask_main.py           # Flask app factory — registers all blueprints & routes
│   ├── agentic/                # LangGraph multi-agent workflows
│   │   ├── sic_prediction/     # 5-agent SIC code prediction workflow
│   │   └── update_revenue/     # RAG-based revenue extraction workflow
│   ├── agents/                 # Individual agent implementations
│   ├── api/                    # Flask route blueprints
│   ├── apis/                   # External API clients (Companies House, web scraper)
│   ├── config/                 # App configuration, API keys, DB config
│   ├── core/                   # Core business logic
│   ├── database/               # SQLite connection, models, vector DB
│   ├── rag/                    # RAG engine (vector similarity search)
│   ├── routes/                 # Main/API Flask routes
│   ├── services/               # Business services (SIC, revenue, filing history, QA)
│   └── utils/                  # Logging, input validation, helpers
│
├── modular_templates/          # Jinja2 HTML templates (dashboard, database viewer, etc.)
├── modular_static/             # CSS, JS, images (frontend assets)
│   ├── js/modular_dashboard.js # Main frontend JS (~7000 lines)
│   └── css/                    # Stylesheets
│
├── data/                       # SQLite databases (mounted from Azure File Share in prod)
│   ├── credit_risk.db          # Main application database
│   └── vector_database.db      # Vector embeddings for RAG
│
├── tests/
│   └── master_api_test.py      # Full integration test suite (170 tests)
│
├── scripts/
│   └── deploy_azure.sh         # Single canonical Azure deploy script
│
├── azure_deployment/
│   └── README.md               # Detailed Azure deployment guide
│
├── batch/                      # Offline batch processing scripts
├── config/                     # Database schema definitions
├── logs/                       # Application logs (runtime, not committed)
└── superseded/                 # Archived/replaced files — kept for reference
```

---

## Key Technologies

| Layer | Technology |
|---|---|
| Web framework | Flask 3.x + Gunicorn |
| AI orchestration | LangGraph (multi-agent workflows) |
| LLM | Azure OpenAI (GPT-4o) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector search | sqlite-vec (SQLite extension) |
| Document processing | Azure Document Intelligence |
| External data | Companies House API |
| Database | SQLite (local dev) + Azure File Share mount (production) |
| Container | Docker → Azure Container Registry → Azure Container Instances |
| Secrets | Azure Key Vault |

---

## Database

The app uses two SQLite databases:

| Database | File | Contents |
|---|---|---|
| Main | `data/credit_risk.db` | 515 companies, financials, SIC history, predictions, QA history, activity log |
| Vector | `data/vector_database.db` | Document embeddings for RAG (annual report chunks) |

In production both files are mounted from Azure File Share `credit-risk-db` at `/app/data`.

### Key tables in `credit_risk.db`

| Table | Purpose |
|---|---|
| `companies` | Master company records (name, number, SIC, unique_id, status) |
| `company_financials` | Revenue (`sales_gbp`), profit, year, period type |
| `sic_prediction_history` | All SIC prediction runs with confidence scores |
| `company_sic_codes` | SIC code lookup / mapping |
| `qa_history` | Q&A questions and answers per company/document |
| `activity_log` | User action audit trail |
| `api_audit_log` | External API call log |

---

## Testing

```bash
# Start the server first (in one terminal)
PORT=5002 python3 startup.py

# Run tests (in another terminal)
python3 tests/master_api_test.py
```

The test suite covers:
- Server health checks
- All page routes (HTML)
- Filter options API
- Companies portal (pagination, sorting, search)
- Full SIC prediction flow (predict → approve → DB verify)
- Full revenue extraction flow (precheck → extract → approve → DB verify)
- Q&A flow
- Database viewer APIs
- Input validation (bad inputs → 400/403)
- JS ↔ backend payload contract audit
- Regression guards for previously fixed bugs
