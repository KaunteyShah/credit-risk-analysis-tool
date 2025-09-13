# 🏦 Credit Risk Analysis Demo

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)
[![Databricks](https://img.shields.io/badge/Databricks-FF3621?style=for-the-badge&logo=databricks&logoColor=white)](https://databricks.com/)

> **Multi-Agent AI System for SIC Code Validation & Revenue Verification**

A sophisticated Streamlit application demonstrating AI-powered credit risk analysis through automated SIC code validation, accuracy assessment, and revenue data verification using multi-agent orchestration.

## 🎯 **Project Overview**

This demo showcases a production-ready interface for financial institutions to:
- **Validate SIC codes** using AI-powered business description analysis
- **Assess accuracy** with color-coded visual indicators
- **Orchestrate multiple AI agents** for comprehensive data processing
- **Track revenue updates** and data freshness
- **Filter and analyze** company data efficiently

### 🌟 **Key Features**

- **🎨 Professional UI**: Collapsible panels with responsive design
- **🤖 LangGraph Agent Flows**: Vertical agent orchestration visualization
- **🎯 Smart Filtering**: Quick accuracy categories (High/Medium/Low)
- **📊 Color-Coded Accuracy**: Visual SIC code accuracy assessment
- **⚡ Real-time Controls**: Interactive buttons with status indicators
- **📈 Analytics Dashboard**: Summary metrics and data insights

## 🚀 **Quick Start**

### Prerequisites

- **Python 3.12+**
- **Git** (for cloning)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/credit-risk-analysis-demo.git
cd credit-risk-analysis-demo

# Install dependencies
pip install streamlit plotly pandas numpy openpyxl

# Generate enhanced data (first time only)
python preprocess_data.py

# Launch the application
streamlit run streamlit_app.py --server.port 8501
```

### Using the Quick Launcher

```bash
# Make launcher executable
chmod +x run_app.sh

# Launch with one command
./run_app.sh
```

The application will open at: **http://localhost:8501**

## 📊 **Current Dataset**

- **509 Companies** with comprehensive business data
- **149 Unique SIC Codes** from UK SIC 2007 classification
- **Enhanced Mock Accuracy Scores** using realistic beta distributions
- **Geographic Coverage**: UK, USA, Australia, Canada
- **Website Coverage**: 92.9% of companies have website data

### Data Structure
```
📁 data/
├── Sample data_09Sep2025.xlsx     # Original company data
├── SIC_codes.xlsx                 # Official UK SIC 2007 codes
└── enhanced_sample_data.pkl       # Processed data with accuracy scores
```

## 🎮 **Using the Demo**

### 📋 **Panel Controls**
- **Top Panel**: Company data analysis with filtering
- **Bottom Panel**: Agent orchestration and system status
- **Collapsible Design**: Toggle panels on/off via sidebar

### 🔍 **Smart Filtering**
- **🔴 Low Accuracy** (<70%): Companies needing immediate attention
- **🟡 Medium Accuracy** (70-90%): Companies that could be improved
- **🟢 High Accuracy** (≥90%): Companies with excellent classification
- **Custom Filters**: Employee count, country, revenue update status

### 🤖 **Agent Orchestration**
- **SIC Prediction Flow**: 5-agent workflow for business classification
- **Revenue Update Flow**: 4-agent pipeline for data refresh
- **Live Status Tracking**: Professional Red/Orange/Green indicators
- **Interactive Controls**: Start/stop agent workflows

### 📊 **Data Table Features**
- **Column Selection**: Choose which fields to display
- **Color-Coded Accuracy**: Visual assessment of SIC code quality
- **Action Buttons**: Individual and batch operations
- **Pagination**: Efficient navigation through large datasets

## 🏗️ **Architecture**

### Phase 1: UI Foundation (Current)
```
streamlit_app.py          # Main Streamlit application
preprocess_data.py        # Data enhancement pipeline
run_app.sh               # Application launcher
├── 📊 Data Layer
│   ├── Company data loading
│   ├── SIC codes reference
│   └── Enhanced accuracy scoring
├── 🎨 UI Layer
│   ├── Collapsible panels
│   ├── Interactive filtering
│   └── Professional styling
└── 🤖 Mock Agent Layer
    ├── LangGraph-style visualization
    ├── Status tracking
    └── Workflow simulation
```

### Future Phases
- **Phase 2**: Real agent integration with LangGraph
- **Phase 3**: Databricks deployment and scaling
- **Phase 4**: Advanced analytics and predictive modeling
- **Phase 5**: Enterprise integration and automation

## 🔧 **Configuration**

### Customizing Data Sources
```python
# In preprocess_data.py
COMPANY_DATA_PATH = "data/Sample data_09Sep2025.xlsx"
SIC_CODES_PATH = "data/SIC_codes.xlsx"
OUTPUT_PATH = "enhanced_sample_data.pkl"
```

### Adjusting Accuracy Thresholds
```python
# In streamlit_app.py
HIGH_ACCURACY_THRESHOLD = 0.9    # 90%+
MEDIUM_ACCURACY_THRESHOLD = 0.7  # 70%+
# Below 70% = Low accuracy
```

## 📈 **Business Value**

### Risk Management
- **Visual Risk Assessment**: Immediately identify companies with poor SIC classification
- **Portfolio Analysis**: Track accuracy distribution across business units
- **Compliance Monitoring**: Ensure regulatory classification requirements

### Operational Efficiency
- **Automated Workflows**: Multi-agent processing reduces manual effort
- **Quick Filtering**: Focus on high-priority companies needing attention
- **Batch Operations**: Process multiple companies simultaneously

### Data Quality
- **Accuracy Tracking**: Monitor and improve classification quality over time
- **Revenue Validation**: Keep financial data current and accurate
- **Audit Trails**: Track changes and updates for compliance

## 🛠️ **Development**

### Project Structure
```
credit-risk-analysis-demo/
├── streamlit_app.py              # Main application
├── preprocess_data.py            # Data processing
├── run_app.sh                   # Launcher script
├── data/                        # Data files
├── docs/                        # Documentation
└── requirements.txt             # Python dependencies
```

## 📝 **Changelog**

### Phase 1.0 (Current)
- ✅ Complete UI foundation with collapsible panels
- ✅ LangGraph-style agent visualization
- ✅ Color-coded SIC accuracy assessment
- ✅ Quick filtering by accuracy categories
- ✅ Professional table with action buttons
- ✅ Enhanced data processing pipeline

### Planned (Phase 2.0)
- 🔄 Real agent integration with LangGraph
- 🔄 Live SIC prediction using ML models
- 🔄 Companies House API integration
- 🔄 Website content scraping and analysis

## 🤝 **Contributing**

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🎯 **Built for Databricks**

This demo is designed to showcase the potential of deploying AI-powered financial analysis on the Databricks platform, demonstrating:
- **Scalable data processing** with Delta Lake
- **ML model deployment** with MLflow
- **Interactive analytics** with Databricks Apps
- **Enterprise security** with Unity Catalog

**Ready to revolutionize credit risk analysis with AI! 🏦✨**
3. **Sector Classification Agent** - Suggests correct sector codes using business descriptions
4. **Turnover Estimation Agent** - Proposes turnover corrections using alternative data
5. **Confidence Scoring Agent** - Calculates confidence levels for suggestions
6. **Human Review Interface** - Workflow for analyst approval/rejection

### Data Sources
- Companies House API
- Business websites and social media
- External agency databases
- Public financial reports
- Alternative data sources

## Project Structure
```
├── config/              # Configuration files
├── src/                 # Source code
│   ├── agents/         # Individual agent implementations
│   └── utils/          # Utility functions
├── notebooks/          # Databricks notebooks
├── data/              # Sample and processed data
└── tests/             # Test files
```

## Getting Started
1. Configure API keys in `config/api_config.yaml`
2. Set up Databricks environment
3. Run the main orchestration notebook
4. Review suggestions in the analyst interface

## Features
- Real-time anomaly detection
- AI-powered correction suggestions
- Confidence scoring
- Human-in-the-loop workflow
- Comprehensive audit trail
