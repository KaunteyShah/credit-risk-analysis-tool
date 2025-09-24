"""
Databricks Setup Script
Run this script to initialize your Databricks environment for the Credit Risk Analysis Tool
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent

from config.databricks_config import initialize_databricks, get_databricks_config
from data_layer.databricks_data import get_data_manager

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

def check_environment():
    """Check if environment is properly configured"""
    logger.info("🔍 Checking environment configuration...")
    
    config = get_databricks_config()
    
    # Check if running in Databricks
    if config.is_databricks_environment:
        logger.info("✅ Running in Databricks environment")
        return True
    
    # Check local environment variables
    required_vars = ['DATABRICKS_HOST', 'DATABRICKS_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        logger.info("📋 Please create a .env file based on .env.template")
        return False
    
    logger.info("✅ Environment configuration looks good")
    return True

def setup_databricks_connection():
    """Initialize Databricks connection"""
    logger.info("🔗 Setting up Databricks connection...")
    
    try:
        config = initialize_databricks()
        logger.info("✅ Databricks connection established")
        return config
    except Exception as e:
        logger.error(f"❌ Failed to connect to Databricks: {str(e)}")
        return None

def setup_data_layer():
    """Setup Delta tables and data layer"""
    logger.info("🗄️ Setting up data layer...")
    
    try:
        data_manager = get_data_manager()
        
        # Create schema
        data_manager.create_credit_risk_schema()
        
        # Create companies table
        data_manager.create_companies_table()
        
        # Load sample data if available
        sample_data_path = "data/Sample_data2.csv"
        if os.path.exists(sample_data_path):
            logger.info(f"📊 Loading sample data from {sample_data_path}")
            data_manager.load_sample_data_to_delta(sample_data_path)
        else:
            logger.warning(f"⚠️ Sample data file not found: {sample_data_path}")
            logger.info("💡 Please ensure Sample_data2.csv is in the data/ directory")
        
        logger.info("✅ Data layer setup complete")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to setup data layer: {str(e)}")
        return False

def verify_setup():
    """Verify the setup is working"""
    logger.info("🧪 Verifying setup...")
    
    try:
        data_manager = get_data_manager()
        
        # Try to read data
        df = data_manager.read_companies_data(limit=5)
        logger.info(f"✅ Successfully read {len(df)} rows from companies table")
        
        # Get table info
        table_info = data_manager.get_table_info("companies")
        if table_info:
            logger.info("✅ Table information retrieved successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup verification failed: {str(e)}")
        return False

def main():
    """Main setup function"""
    logger.info("🚀 Starting Databricks setup for Credit Risk Analysis Tool")
    logger.info("=" * 60)
    
    # Step 1: Check environment
    if not check_environment():
        logger.error("❌ Environment check failed. Please fix configuration issues.")
        sys.exit(1)
    
    # Step 2: Setup Databricks connection
    config = setup_databricks_connection()
    if not config:
        logger.error("❌ Databricks connection failed. Please check your credentials.")
        sys.exit(1)
    
    # Step 3: Setup data layer
    if not setup_data_layer():
        logger.error("❌ Data layer setup failed.")
        sys.exit(1)
    
    # Step 4: Verify setup
    if not verify_setup():
        logger.error("❌ Setup verification failed.")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎉 Databricks setup completed successfully!")
    logger.info("✨ You can now run the Streamlit app with Databricks integration")
    logger.info("📝 Run: streamlit run streamlit_app_langgraph_viz.py")

if __name__ == "__main__":
    main()
