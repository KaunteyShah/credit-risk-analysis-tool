# API Requirements and Installation Guide: Demo Mode OFF

When demo mode is disabled (`DEMO_MODE=false`), the application uses **Real Fuzzy Matching** with advanced SIC code prediction capabilities. This document outlines all required APIs, dependencies, and installation requirements.

## 🔧 Core System Requirements

### 1. **Enhanced SIC Matcher Dependencies**
```bash
# Python packages (already in requirements.txt)
rapidfuzz==3.6.1          # Fast fuzzy matching library
openpyxl==3.1.2           # Excel file processing
pandas==2.2.3             # Data manipulation
numpy==1.26.4             # Numerical computing
```

### 2. **SIC Codes Database File**
- **File**: `data/SIC_codes.xlsx`
- **Contains**: 751 official SIC codes with descriptions
- **Status**: ✅ Already included in repository
- **Purpose**: Real SIC code matching and validation

### 3. **Flask Configuration**
```bash
# Environment Variables Required
FLASK_SECRET_KEY=<secure-random-key>    # ✅ Already set in Azure
DEMO_MODE=false                         # Set to disable demo mode
```

## 🌐 External APIs Required

### 1. **Companies House API** (UK Company Data)
- **Purpose**: Real company information lookup and validation
- **API Key Required**: `COMPANIES_HOUSE_API_KEY`
- **Documentation**: https://developer.company-information.service.gov.uk/
- **Usage**: Company registration validation, director information
- **Status**: ⚠️ **REQUIRED but not currently configured**

#### Installation Steps:
1. **Register at Companies House**:
   ```
   Visit: https://developer.company-information.service.gov.uk/
   Create account and generate API key
   ```

2. **Add to Azure**:
   ```bash
   az webapp config appsettings set \
     --name credit-risk-clean-app \
     --resource-group rg-credit-risk-clean \
     --settings COMPANIES_HOUSE_API_KEY="your-api-key-here"
   ```

### 2. **OpenAI API** (AI Reasoning and Analysis)
- **Purpose**: Advanced SIC code reasoning and business description analysis
- **API Key Required**: `OPENAI_API_KEY`
- **Documentation**: https://platform.openai.com/docs
- **Usage**: AI-powered SIC prediction validation and reasoning
- **Status**: ⚠️ **REQUIRED but not currently configured**

#### Installation Steps:
1. **Get OpenAI API Key**:
   ```
   Visit: https://platform.openai.com/account/api-keys
   Create and copy API key
   ```

2. **Add to Azure**:
   ```bash
   az webapp config appsettings set \
     --name credit-risk-clean-app \
     --resource-group rg-credit-risk-clean \
     --settings OPENAI_API_KEY="your-api-key-here"
   ```

### 3. **Azure Key Vault** (Secrets Management)
- **Purpose**: Secure storage for API keys and sensitive data
- **Status**: ✅ **Already configured**
- **Usage**: Automatically retrieves secrets when available

## 📊 Enhanced Features Available with Demo Mode OFF

### 1. **Advanced SIC Prediction**
- **Fuzzy Matching**: 751 real SIC codes with smart similarity scoring
- **Business Activity Extraction**: Removes corporate noise, focuses on core activities
- **Industry-Specific Boosting**: 
  - Catering/Restaurant: +15% accuracy boost
  - Retail/Supermarket: +15% accuracy boost  
  - Banking/Financial: +15% accuracy boost

### 2. **Dual Accuracy Tracking**
- **Old Accuracy**: How well current SIC code matches business description
- **New Accuracy**: Predicted SIC code accuracy with algorithm confidence
- **Validation Logic**: Conservative scoring with penalties for missing data

### 3. **Data Persistence**
- **CSV Management**: Atomic writes to prevent data corruption
- **Version History**: Maintains all prediction changes with timestamps
- **User Tracking**: Records who made predictions and when

### 4. **AI-Powered Analysis**
- **Smart Reasoning**: OpenAI integration for complex business descriptions
- **Context Understanding**: Advanced NLP for sector classification
- **Confidence Scoring**: Multi-layered validation system

## 🚀 Quick Setup Commands

### Azure Environment Setup
```bash
# 1. Set demo mode off
az webapp config appsettings set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --settings DEMO_MODE="false"

# 2. Add Companies House API key
az webapp config appsettings set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --settings COMPANIES_HOUSE_API_KEY="your-companies-house-key"

# 3. Add OpenAI API key  
az webapp config appsettings set \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean \
  --settings OPENAI_API_KEY="your-openai-key"

# 4. Restart application
az webapp restart \
  --name credit-risk-clean-app \
  --resource-group rg-credit-risk-clean
```

### Local Development Setup
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env file
DEMO_MODE=false
COMPANIES_HOUSE_API_KEY=your-companies-house-key
OPENAI_API_KEY=your-openai-key
FLASK_SECRET_KEY=your-local-secret-key

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run application
python startup.py
```

## 🔍 API Endpoints Available

### Demo Mode Toggle
- `GET /api/demo-mode-status` - Get current mode status
- `POST /api/toggle-demo-mode` - Switch between modes
  ```json
  {"demo_mode": false}
  ```

### SIC Prediction (Enhanced Mode)
- `POST /api/predict_sic` - Advanced fuzzy matching prediction
- `POST /api/predict_sic_real` - Real agent-based prediction
- `POST /api/update_sic` - Save user SIC code changes

### Data Management
- `GET /api/data` - Enhanced company data with dual accuracy
- `GET /api/companies` - Company list with SIC predictions
- `POST /api/data/reload` - Refresh data with new accuracy calculations

## ⚠️ Current Status

### ✅ Working Components
- Demo mode toggle UI and API
- Enhanced SIC matcher (when dependencies available)
- Fuzzy matching algorithms
- Data persistence system
- Flask secret key configuration

### ⚠️ Pending Configuration
- **Companies House API Key**: Required for real company data
- **OpenAI API Key**: Required for AI reasoning
- **Azure Key Vault Secrets**: Automatic retrieval when keys are added

### 🔧 Next Steps
1. **Get API Keys**: Register for Companies House and OpenAI APIs
2. **Configure Azure**: Add API keys to Azure App Service settings
3. **Test Real Mode**: Switch demo mode off and verify enhanced matching
4. **Monitor Performance**: Check logs for enhanced matcher functionality

## 📞 Support

If you encounter issues:
1. Check Azure App Service logs for initialization errors
2. Verify API keys are properly set in environment variables
3. Ensure `data/SIC_codes.xlsx` file is deployed with the application
4. Test enhanced matcher locally first before Azure deployment