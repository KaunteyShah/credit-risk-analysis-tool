# SIC Confidence Management API Guide

## 🎯 Solution Overview

The SIC Confidence Management API provides **automatic existing SIC confidence calculation** when new companies are added to the system. This solves the problem of requiring manual intervention to calculate confidence scores.

## 📋 Key Features

- **Automatic Integration**: When you add a company with existing SIC code, confidence is calculated immediately
- **Batch Processing**: Calculate confidence for all companies needing it
- **Individual Calculation**: Calculate confidence for specific companies
- **Real-time Feedback**: Get confidence scores instantly with detailed workflow steps

## 🔧 API Endpoints

### 1. Add Company with Automatic SIC Confidence

**Endpoint**: `POST /api/add_company_with_sic`

**Purpose**: Add a new company and automatically calculate existing SIC confidence in one step.

**Request**:
```json
{
    "company_name": "AI Innovations Ltd",
    "business_description": "Artificial intelligence software development and machine learning consulting services",
    "existing_sic_code": "62020",
    "existing_sic_description": "Computer programming activities",
    "company_number": "AI123456"
}
```

**Response**:
```json
{
    "success": true,
    "message": "Company AI Innovations Ltd added with automatic SIC confidence calculation",
    "company_id": 510,
    "company_name": "AI Innovations Ltd",
    "existing_sic_code": "62020",
    "existing_sic_confidence": 75.0,
    "existing_ai_reasoning": "Business description analysis: 12 words provide good detail. Fuzzy matching with SIC description 'Computer programming activities' using token sort method: 88.5% similarity. High text similarity indicates strong alignment between business activities and SIC classification.",
    "existing_sic_confidence_category": "Good",
    "existing_sic_calculation_timestamp": "2025-10-04T10:03:18.311857",
    "confidence_calculation": "automatic",
    "workflow_steps": [
        {"step": 1, "status": "completed", "message": "Added company: AI Innovations Ltd"},
        {"step": 2, "status": "completed", "message": "Added SIC code: 62020"},
        {"step": 3, "status": "completed", "message": "Calculated confidence: 75.0%"},
        {"step": 4, "status": "completed", "message": "Generated AI reasoning for SIC classification"},
        {"step": 5, "status": "completed", "message": "Company ready for SIC predictions"}
    ]
}
```

### 2. Calculate SIC Confidence for Specific Company

**Endpoint**: `POST /api/calculate_sic_confidence`

**Purpose**: Calculate existing SIC confidence for a specific company.

**Request**:
```json
{
    "company_id": 510
}
```

**Response**:
```json
{
    "success": true,
    "message": "Successfully calculated confidence for AI Innovations Ltd",
    "company_id": 510,
    "company_name": "AI Innovations Ltd",
    "existing_sic_code": "62020",
    "existing_sic_confidence": 75.0,
    "existing_ai_reasoning": "Business description analysis: 12 words provide good detail. Fuzzy matching with SIC description 'Computer programming activities' using token sort method: 88.5% similarity. High text similarity indicates strong alignment between business activities and SIC classification.",
    "existing_sic_confidence_category": "Good",
    "existing_sic_calculation_timestamp": "2025-10-04T10:03:18.311857"
}
```

### 3. Batch Calculate SIC Confidence

**Endpoint**: `POST /api/calculate_sic_confidence`

**Purpose**: Calculate confidence for all companies that need it.

**Request**:
```json
{}
```

**Response**:
```json
{
    "success": true,
    "message": "Successfully processed 1 out of 1 companies",
    "total": 1,
    "processed": 1,
    "success_count": 1,
    "failed_count": 0
}
```

## 🧠 **Enhanced SIC Confidence Analysis Fields**

All endpoints now include comprehensive analysis with the following fields:

- **`existing_sic_confidence`**: Numerical confidence score (0-100)
- **`existing_ai_reasoning`**: Detailed explanation (max 200 words) of confidence calculation
- **`existing_sic_confidence_category`**: Categorized confidence level
- **`existing_sic_calculation_timestamp`**: When the confidence was calculated

### 📊 **Confidence Categories**
- **Excellent**: 85-100% confidence 
- **Good**: 70-84% confidence
- **Fair**: 50-69% confidence  
- **Very Poor**: 0-49% confidence

**Example Response with All Enhanced Fields**:
```json
{
    "success": true,
    "company_id": 515,
    "company_name": "Test Enhanced Company",
    "existing_sic_code": "62020",
    "existing_sic_confidence": 75.0,
    "existing_ai_reasoning": "Business description analysis: 7 words provide adequate detail. No SIC description available for fuzzy matching, using keyword analysis. Identified sector keywords for: software, professional industries. Strong keyword alignment with business activities.",
    "existing_sic_confidence_category": "Good",
    "existing_sic_calculation_timestamp": "2025-10-04T10:03:18.311857",
    "message": "Successfully calculated confidence for Test Enhanced Company"
}
```

## ⚡ Quick Test Examples

### Test 1: Add Company with Auto-Confidence
```bash
curl -X POST http://localhost:5002/api/add_company_with_sic \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Tech Solutions Ltd",
    "business_description": "Software consulting and development",
    "existing_sic_code": "62020",
    "existing_sic_description": "Computer programming activities",
    "company_number": "TECH123"
  }'
```

### Test 2: Calculate for Specific Company
```bash
curl -X POST http://localhost:5002/api/calculate_sic_confidence \
  -H "Content-Type: application/json" \
  -d '{"company_id": 510}'
```

### Test 3: Batch Process All Companies
```bash
curl -X POST http://localhost:5002/api/calculate_sic_confidence \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 🔍 How It Works

1. **Company Addition**: When you call `/api/add_company_with_sic`, the system:
   - Adds company to `companies` table
   - Adds SIC code to `company_sic_codes` table
   - Automatically triggers confidence calculation using `SICConfidenceService`

2. **Confidence Calculation**: Uses the same methodology as `auto_sic_confidence_calculator.py`:
   - **Fuzzy Matching**: Compares business description with SIC code description
   - **Sector Analysis**: Analyzes sector keywords and themes
   - **Scoring**: Combines fuzzy match score with sector analysis
   - **Storage**: Stores result in `sic_prediction_history.existing_sic_confidence`

3. **Database Integration**: Results are automatically stored in the consolidated table structure

## 📊 Confidence Methodology

The confidence calculation uses:
- **FuzzyWuzzy** for text similarity matching
- **Sector keyword analysis** for industry alignment
- **Combined scoring** (70% fuzzy match + 30% sector analysis)
- **TEXT data types** for proper fuzzy matching with SIC codes

## ✅ Production Benefits

- **No Manual Intervention**: Companies get confidence scores immediately upon addition
- **Consistent Methodology**: Uses the same proven calculation as batch processing
- **Real-time Integration**: No need to run separate scripts
- **API-First**: Easy to integrate with existing workflows and UIs

## 🎯 Use Cases

1. **New Company Onboarding**: Add companies with immediate confidence assessment
2. **Batch Processing**: Calculate confidence for multiple companies at once
3. **Data Quality**: Re-calculate confidence for existing companies
4. **Integration**: Use in workflows, dashboards, and other systems

## 🔧 Technical Details

- **Service**: `app_modules/services/sic_confidence_service.py`
- **Database**: SQLite with consolidated `sic_prediction_history` table
- **Storage**: Confidence stored in `existing_sic_confidence` column
- **Dependencies**: Inherits all functionality from `auto_sic_confidence_calculator.py`