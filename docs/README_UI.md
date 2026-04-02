# Credit Risk Analysis Demo - Phase 1 UI

## 🎯 Overview

This is **Phase 1** of the Credit Risk Analysis Demo, featuring a comprehensive Streamlit UI with:

- **Collapsible Top/Bottom Panels** for flexible screen real estate
- **Company Data Table** with advanced filtering and column selection
- **SIC Code Accuracy Analysis** with color-coded indicators
- **Mock Agent Orchestration** visualization
- **Revenue Update Tracking** for data freshness

## 🏗️ Architecture

### Panel Structure
- **Top Panel**: Company data analysis with filtering sidebar
- **Bottom Panel**: Agent orchestration and system status
- **Both panels** are resizable and collapsible

### Key Features
1. **SIC Accuracy Column**: Color-coded accuracy scores (Green >90%, Yellow 70-90%, Red <70%)
2. **Predict Button**: Placeholder for future multi-agent SIC prediction
3. **Update Revenue Button**: Placeholder for Companies House integration
4. **Advanced Filtering**: By employee count, accuracy, country, SIC code
5. **Live Agent Visualization**: Interactive agent flow diagrams

## 📊 Data Structure

### Company Data (509 companies)
- **UK SIC 2007 Code**: Primary focus for accuracy assessment
- **Business Description**: Used for validation
- **Website**: Available for 92.9% of companies
- **Sales, Employees**: Company size metrics
- **Enhanced fields**: SIC_Accuracy, Last_Updated, Needs_Revenue_Update

### SIC Codes Reference (751 codes)
- **Official UK SIC 2007 codes** from Companies House
- **Hierarchical structure**: 4-digit, 5-digit sections
- **Cross-referenced** with company data for validation

## 🚀 Getting Started

### Prerequisites
```bash
# Python 3.12+ recommended
python3 --version

# Virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows
```

### Installation
```bash
# Install required packages
pip install pandas openpyxl streamlit streamlit-aggrid plotly numpy

# Or use the automated installer
python preprocess_data.py  # Generates enhanced data
```

### Running the Application
```bash
# Method 1: Direct Streamlit
streamlit run streamlit_app.py

# Method 2: Using launcher script
./run_app.sh

# Method 3: Manual with custom port
streamlit run streamlit_app.py --server.port 8501
```

The application will open at: `http://localhost:8501`

## 🎮 Using the Demo

### 1. Filtering Companies
- **Left Sidebar**: Access all filter controls
- **Employee Range**: Slider for company size
- **SIC Accuracy**: Minimum accuracy threshold
- **Country/SIC Code**: Dropdown filters
- **Revenue Update**: Show only companies needing updates

### 2. Table Interaction
- **Column Selection**: Choose which columns to display
- **Pagination**: Navigate through large datasets
- **Sorting**: Click column headers (planned)
- **Action Buttons**: Predict SIC and Update Revenue (placeholders)

### 3. Agent Visualization
- **SIC Prediction Flow**: 5-agent workflow diagram
- **Revenue Update Flow**: 4-agent workflow (placeholder)
- **Live Status**: Real-time agent activity (mock)

### 4. Analytics
- **Summary Metrics**: Company count, accuracy averages
- **Distribution Charts**: SIC accuracy histogram
- **Country Analysis**: Company distribution by location

## 📈 Data Insights

### Current Dataset Statistics
- **509 Companies** across multiple industries
- **149 Unique SIC Codes** with varying accuracy
- **Average SIC Accuracy**: 85.2%
- **Distribution**:
  - High accuracy (≥90%): 211 companies (41%)
  - Medium accuracy (70-90%): 228 companies (45%)
  - Low accuracy (<70%): 70 companies (14%)

### SIC Code Analysis
- **Most Common**: 7010 (Activities of head offices) - 72 companies
- **Education Sector**: Strong representation (8531, 85421)
- **Business Services**: Many companies in 8299 category

## 🔄 Phase 2 Roadmap

### Planned Enhancements
1. **Real Agent Integration**:
   - LangGraph-based visual workflows
   - Actual SIC prediction algorithms
   - Companies House API integration

2. **Advanced UI Features**:
   - Interactive agent debugging
   - Real-time message passing visualization
   - Confidence score tracking

3. **Data Processing**:
   - Website content scraping (1000 words)
   - Live SIC prediction with ML models
   - Revenue data validation

4. **Databricks Migration**:
   - Databricks Apps deployment
   - Unity Catalog integration
   - MLflow experiment tracking
   - Delta Lake storage

## 🛠️ Technical Details

### Architecture Components
```
streamlit_app.py          # Main UI application
preprocess_data.py        # Data enhancement script
run_app.sh               # Application launcher
data/
├── Sample data_09Sep2025.xlsx    # Original company data
├── SIC_codes.xlsx               # Official SIC codes
└── enhanced_sample_data.pkl     # Processed data with accuracy scores
```

### Key Libraries
- **Streamlit**: Web interface framework
- **Plotly**: Interactive visualizations
- **Pandas**: Data manipulation
- **NumPy**: Numerical computations

### Mock Data Generation
- **SIC Accuracy**: Beta distribution (skewed high)
- **Update Dates**: Exponential distribution (realistic aging)
- **Confidence Scores**: Realistic ML-style confidence levels

## 🐛 Known Limitations (Phase 1)

1. **Mock Data**: All accuracy scores and predictions are simulated
2. **Static Agents**: Agent flows are visualized but not functional
3. **No API Integration**: Companies House and website scraping not implemented
4. **Limited Interactivity**: Buttons are placeholders
5. **Basic Filtering**: Advanced search not yet implemented

## 🎯 Success Criteria

### Phase 1 Achievements ✅
- ✅ Collapsible panel layout
- ✅ Advanced data filtering
- ✅ Color-coded SIC accuracy
- ✅ Interactive visualizations
- ✅ Mock agent workflow diagrams
- ✅ Responsive design
- ✅ Real data integration (509 companies)

### Ready for Phase 2
- 🔄 Agent system integration points identified
- 🔄 UI framework established
- 🔄 Data pipeline tested
- 🔄 Visualization patterns proven

## 📞 Support & Development

### Future Databricks Integration
- **Streamlit Apps**: Native Databricks deployment
- **Data Sources**: Unity Catalog, Delta Lake
- **Compute**: Databricks clusters for agent processing
- **Security**: Databricks security model integration

### Development Notes
- **Modular Design**: Easy to add real agent functionality
- **State Management**: Streamlit session state for complex workflows
- **Performance**: Caching optimized for large datasets
- **Scalability**: Ready for distributed processing

---

🏦 **Credit Risk Analysis Demo** - Building the future of AI-powered financial analysis with Databricks!
