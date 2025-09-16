# Credit Risk Analysis - Production Application

A production-ready, Databricks-compliant multi-agent system for credit risk analysis with advanced SIC code prediction and LangGraph workflow visualization.

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or 3.12
- Git

### Option 1: Automated Setup (Recommended)

**For macOS/Linux:**
```bash
git clone https://github.com/KaunteyShah/credit-risk-analysis-tool.git
cd credit-risk-analysis-tool
./start.sh
```

**For Windows:**
```cmd
git clone https://github.com/KaunteyShah/credit-risk-analysis-tool.git
cd credit-risk-analysis-tool
start.bat
```

### Option 2: Manual Setup

1. **Clone the repository:**
```bash
git clone https://github.com/KaunteyShah/credit-risk-analysis-tool.git
cd credit-risk-analysis-tool
```

2. **Create and activate virtual environment:**
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Verify setup (optional but recommended):**
```bash
python verify_setup.py
```

5. **Run the application:**
```bash
python main.py
```

6. **Access the app:**
Open your browser and go to http://localhost:8000

### 📁 Essential Files Included
- ✅ `data/Sample_data2.csv` - Sample company data (509 companies)
- ✅ `data/SIC_codes.xlsx` - SIC classification codes
- ✅ `requirements.txt` - All Python dependencies
- ✅ `main.py` - Application entry point
- ✅ `verify_setup.py` - Setup verification script
- ✅ `start.sh` / `start.bat` - Automated setup scripts
- ✅ Complete `app/` folder structure

## 🔧 Troubleshooting

### Common Issues

**"Python not found"**
- Install Python 3.11+ from https://python.org
- Make sure Python is added to your PATH

**"Module not found" errors**
- Ensure virtual environment is activated
- Run: `pip install -r requirements.txt`

**"Data file not found" errors**
- Verify you're in the correct directory
- Check that `data/` folder contains CSV and Excel files
- Run verification: `python verify_setup.py`

**Port 8000 already in use**
- Close other applications using port 8000
- Or kill existing processes: `pkill -f streamlit`

**Permission denied (macOS/Linux)**
- Make start script executable: `chmod +x start.sh`

### Getting Help
- Run verification script: `python verify_setup.py`
- Check all required files are present
- Ensure Python 3.11+ is installed

## 🏗️ Architecture

```
app/
├── core/                    # Core application modules
│   ├── streamlit_app_langgraph_viz.py  # Main Streamlit application
│   └── phase2_integration.py           # LangGraph orchestration
├── agents/                  # Multi-agent system
│   ├── base_agent.py       # Base agent class
│   ├── sector_classification_agent.py  # SIC prediction agent
│   ├── data_ingestion_agent.py
│   ├── document_download_agent.py
│   ├── rag_agent.py
│   ├── anomaly_detection_agent.py
│   ├── smart_financial_extraction_agent.py
│   ├── turnover_estimation_agent.py
│   └── multi_agent_orchestrator.py
├── apis/                   # External API integrations
│   ├── companies_house_api.py
│   └── financial_data_api.py
├── utils/                  # Utility modules
│   ├── config_manager.py
│   ├── logger.py
│   ├── data_mapper.py
│   └── sic_prediction_utils.py
├── config/                 # Configuration management
│   └── databricks_config.py
├── data_layer/            # Data access layer
│   └── databricks_data.py
└── workflows/             # Workflow definitions
    └── credit_risk_workflow.py
```

## ✨ Features

### 🎯 SIC Prediction System
- **Real-time SIC code prediction** using AI-powered business description analysis
- **Batch processing** for multiple companies
- **Confidence scoring** and validation
- **25+ real UK SIC mappings** with industry expertise

### 📊 LangGraph Visualization  
- **Professional workflow visualization** with enhanced styling
- **Multi-agent orchestration** display
- **Interactive node exploration** 
- **Conditional flow representation**

### 🏢 Databricks Integration
- **Delta Lake** support for data storage
- **Unity Catalog** integration
- **MLflow** for model tracking
- **Auto-detection** of Databricks environment

### 📈 Analytics Dashboard
- **Interactive data tables** with filtering
- **Real-time performance metrics**
- **Batch operation monitoring** 
- **Export capabilities**

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Databricks Runtime (optional, auto-detected)
- Access to Companies House API (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Credit_Risk
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
# Create .env file with your API keys (optional)
echo "COMPANIES_HOUSE_API_KEY=your_key_here" > .env
```

4. **Run the application**
```bash
streamlit run app/core/streamlit_app_langgraph_viz.py
```

## 🔧 Configuration

### Environment Variables
```bash
# Optional API keys
COMPANIES_HOUSE_API_KEY=your_companies_house_key
OPENAI_API_KEY=your_openai_key

# Databricks configuration (auto-detected if running on Databricks)
DATABRICKS_HOST=your_databricks_host
DATABRICKS_TOKEN=your_databricks_token
```

### Databricks Setup
The application automatically detects Databricks environment. For external connections:

```python
from app.config.databricks_config import get_databricks_config

config = get_databricks_config()
spark = config.get_spark_session()
```

## 📊 Data Sources

### Primary Data
- **Sample_data2.csv**: 509 UK companies with full business intelligence
- **Columns**: Company Number, Name, Address, SIC codes, Status, Incorporation Date

### Supported Formats
- CSV files with company data
- Delta tables (Databricks)
- JSON export/import

## 🤖 Agent System

### Available Agents
1. **SectorClassificationAgent** - SIC code prediction and validation
2. **DataIngestionAgent** - Data loading and preprocessing
3. **DocumentDownloadAgent** - Document retrieval
4. **RAGAgent** - Retrieval-augmented generation
5. **AnomalyDetectionAgent** - Outlier detection
6. **SmartFinancialExtractionAgent** - Financial data extraction
7. **TurnoverEstimationAgent** - Revenue estimation
8. **MultiAgentOrchestrator** - Workflow coordination

### Agent Architecture
```python
from app.agents.base_agent import BaseAgent, AgentResult

class CustomAgent(BaseAgent):
    def process(self, data: Dict[str, Any]) -> AgentResult:
        # Your agent logic here
        return AgentResult(
            agent_name=self.name,
            timestamp=datetime.now(),
            success=True,
            data=processed_data
        )
```

## 🔄 Workflows

### SIC Prediction Workflow
1. **Input**: Company business description
2. **Processing**: AI-powered industry classification
3. **Validation**: Confidence scoring and verification
4. **Output**: SIC code with metadata

### Batch Processing
```python
# Process multiple companies
results = batch_predict_visible_companies(companies_df)
```

## 📈 Performance

### Optimization Features
- **Lazy loading** of large datasets
- **Caching** for repeated operations
- **Batch processing** for efficiency
- **Memory management** for large files

### Monitoring
- **Real-time metrics** in dashboard
- **Error tracking** and logging
- **Performance profiling** available

## 🔒 Security

### Data Protection
- **No sensitive data** stored in code
- **Environment variable** based configuration
- **Secure API key** management
- **Access control** via Databricks permissions

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Code formatting
black app/

# Linting
flake8 app/
```

## 📚 API Reference

### SIC Prediction
```python
from app.agents.sector_classification_agent import SectorClassificationAgent

agent = SectorClassificationAgent()
result = agent.predict_sic_code("Software development company")
```

### Data Operations
```python
from app.data_layer.databricks_data import DatabricksDataLayer

data_layer = DatabricksDataLayer()
df = data_layer.read_delta_table("companies")
```

## 🚀 Deployment

### Databricks Deployment
1. Upload the `app/` directory to Databricks workspace
2. Install requirements via cluster libraries
3. Run as Databricks notebook or job

### Standalone Deployment
```bash
# Production server
streamlit run app/core/streamlit_app_langgraph_viz.py --server.port 8501
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the documentation in `/docs`
- Review the example notebooks in `/examples`

---

**Built with ❤️ for enterprise credit risk analysis**
