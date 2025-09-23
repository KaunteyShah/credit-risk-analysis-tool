# Databricks Integration Setup Guide

## 🚀 Quick Start

### Step 1: Install Databricks Dependencies
```bash
source .venv/bin/activate
pip install -r requirements-databricks.txt
```

### Step 2: Configure Environment
1. Copy the environment template:
   ```bash
   cp .env.template .env
   ```

2. Edit `.env` with your Databricks workspace details:
   ```bash
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
   DATABRICKS_TOKEN=your-personal-access-token
   DATABRICKS_CLUSTER_ID=your-cluster-id
   ```

### Step 3: Run Setup Script
```bash
python setup_databricks.py
```

### Step 4: Launch Application
```bash
streamlit run streamlit_app_langgraph_viz.py --server.port 8503
```

## 📋 Prerequisites

### Databricks Workspace Requirements
- Active Databricks workspace (AWS, Azure, or GCP)
- Personal access token with appropriate permissions
- Running cluster or SQL warehouse
- Unity Catalog enabled (recommended)

### Permissions Required
- `CAN MANAGE` on the catalog (for creating schemas and tables)
- `CAN USE` on compute resources
- `CAN READ` and `CAN MODIFY` on data

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABRICKS_HOST` | Workspace URL | Yes | - |
| `DATABRICKS_TOKEN` | Personal access token | Yes | - |
| `DATABRICKS_CLUSTER_ID` | Cluster ID for compute | No | - |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse ID | No | - |
| `DATABRICKS_CATALOG` | Unity Catalog name | No | `credit_risk` |
| `DATABRICKS_SCHEMA` | Schema name | No | `default` |
| `UNITY_CATALOG_ENABLED` | Use Unity Catalog | No | `true` |

### Data Configuration
- **Primary Data Source**: `Sample_data2.csv` (UK companies dataset)
- **Tables Created**: `credit_risk.default.companies`
- **Data Format**: Delta Lake tables
- **Schema**: Includes all Sample_data2.csv columns plus SIC prediction columns
- **Backup**: Falls back to Sample_data2.csv if Delta tables unavailable

## 🗄️ Database Schema

### Companies Table Structure (Based on Sample_data2.csv)
```sql
CREATE TABLE credit_risk.default.companies (
    company_name STRING,
    registration_number STRING,
    duns_number STRING,
    address_line_1 STRING,
    address_line_2 STRING,
    address_line_3 STRING,
    city STRING,
    post_code STRING,
    country STRING,
    phone STRING,
    company_email STRING,
    website STRING,
    sales_usd STRING,
    pre_tax_profit_usd STRING,
    assets_usd STRING,
    employees_single_site STRING,
    employees_total STRING,
    business_description STRING,
    ownership_type STRING,
    entity_type STRING,
    parent_company STRING,
    parent_country_region STRING,
    global_ultimate_company STRING,
    global_ultimate_country_region STRING,
    us_8_digit_sic_code STRING,
    us_8_digit_sic_description STRING,
    us_sic_1987_code STRING,
    us_sic_1987_description STRING,
    naics_2022_code STRING,
    naics_2022_description STRING,
    uk_sic_2007_code STRING,
    uk_sic_2007_description STRING,
    anzsic_2006_code STRING,
    anzsic_2006_description STRING,
    -- Added for ML predictions
    predicted_sic STRING,
    prediction_confidence DOUBLE,
    created_at DATE,
    updated_at DATE
) USING DELTA;
```

## 🔍 Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify `DATABRICKS_HOST` format: `https://workspace.cloud.databricks.com`
   - Check personal access token validity
   - Ensure network connectivity to Databricks

2. **Permission Errors**
   - Verify token has required permissions
   - Check catalog and schema access rights
   - Ensure cluster/warehouse is running

3. **Table Not Found**
   - Run setup script: `python setup_databricks.py`
   - Check Unity Catalog configuration
   - Verify catalog and schema names

4. **Import Errors**
   - Install dependencies: `pip install -r requirements-databricks.txt`
   - Check Python environment activation
   - Verify package versions compatibility

### Debug Mode
Set environment variable for detailed logging:
```bash
export LOG_LEVEL=DEBUG
export DATABRICKS_LOG_LEVEL=DEBUG
```

## 🎯 Features Enabled

### Data Operations
- ✅ Delta Lake tables for ACID transactions
- ✅ Real-time SIC prediction updates
- ✅ Batch operations for data processing
- ✅ Automatic fallback to CSV for development

### MLflow Integration
- ✅ Model tracking and versioning
- ✅ Experiment management
- ✅ Model registry for SIC predictions
- ✅ Performance metrics logging

### Streamlit Features
- ✅ Cached data loading for performance
- ✅ Real-time data updates
- ✅ Databricks connection status
- ✅ Data management controls

## 🚀 Production Deployment

### For Databricks Notebooks
1. Upload code to Databricks workspace
2. Set environment variables in cluster configuration
3. Run setup script in notebook
4. Launch Streamlit app

### For Databricks Apps
1. Package application as Databricks App
2. Configure app-level environment variables
3. Deploy through Databricks Apps interface

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Databricks logs in the workspace
3. Verify all prerequisites are met
4. Test connection with simple Spark commands
