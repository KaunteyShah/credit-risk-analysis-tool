"""
Databricks-Aware Streamlit Utilities
Helper functions for Streamlit apps running with Databricks integration
"""

import streamlit as st
import pandas as pd
import logging
from typing import Optional, Dict, Any
from data_layer.databricks_data import get_data_manager
from config.databricks_config import get_databricks_config

logger = get_logger(__name__)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_companies_data_cached(limit: Optional[int] = None) -> pd.DataFrame:
    """Load companies data with caching"""
    try:
        data_manager = get_data_manager()
        return data_manager.read_companies_data(limit=limit)
    except Exception as e:
        logger.error(f"Failed to load companies data: {str(e)}")
        st.error(f"Failed to load data: {str(e)}")
        return pd.DataFrame()

def update_company_sic_prediction(company_id: int, predicted_sic: str, confidence: float) -> bool:
    """Update SIC prediction for a company"""
    try:
        data_manager = get_data_manager()
        data_manager.update_sic_prediction(company_id, predicted_sic, confidence)
        
        # Clear the cache to reflect changes
        load_companies_data_cached.clear()
        
        return True
    except Exception as e:
        logger.error(f"Failed to update SIC prediction: {str(e)}")
        st.error(f"Failed to update prediction: {str(e)}")
        return False

def batch_update_sic_predictions(predictions: list) -> bool:
    """Batch update SIC predictions"""
    try:
        data_manager = get_data_manager()
        data_manager.batch_update_sic_predictions(predictions)
        
        # Clear the cache to reflect changes
        load_companies_data_cached.clear()
        
        return True
    except Exception as e:
        logger.error(f"Failed to batch update SIC predictions: {str(e)}")
        st.error(f"Failed to batch update predictions: {str(e)}")
        return False

def display_databricks_info():
    """Display Databricks connection information"""
    config = get_databricks_config()
    
    with st.expander("🔗 Databricks Connection Info", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Environment:**")
            if config.is_databricks_environment:
                st.success("Running in Databricks")
            else:
                st.info("Local development with Databricks Connect")
            
            st.write("**Configuration:**")
            catalog, schema = config.get_catalog_schema()
            st.write(f"- Catalog: `{catalog}`")
            st.write(f"- Schema: `{schema}`")
            st.write(f"- Unity Catalog: {'✅' if config.config['unity_catalog_enabled'] else '❌'}")
        
        with col2:
            st.write("**Data Sources:**")
            try:
                data_manager = get_data_manager()
                table_info = data_manager.get_table_info("companies")
                if table_info:
                    st.success("Companies table accessible")
                    table_name = table_info.get("table_name", "Unknown")
                    st.write(f"- Table: `{table_name}`")
                else:
                    st.warning("Companies table not found")
            except Exception as e:
                st.error(f"Error accessing table: {str(e)}")

def display_data_management_controls():
    """Display data management controls for Databricks"""
    st.subheader("📊 Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Data Cache"):
            load_companies_data_cached.clear()
            st.success("Data cache cleared!")
            st.rerun()
    
    with col2:
        if st.button("📋 Show Table Info"):
            try:
                data_manager = get_data_manager()
                table_info = data_manager.get_table_info("companies")
                st.json(table_info)
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with col3:
        if st.button("📈 Data Statistics"):
            try:
                df = load_companies_data_cached()
                if not df.empty:
                    st.write(f"**Total Records:** {len(df)}")
                    st.write(f"**Columns:** {len(df.columns)}")
                    
                    # Show prediction statistics
                    if 'predicted_sic' in df.columns:
                        predicted_count = df['predicted_sic'].notna().sum()
                        st.write(f"**Predicted SIC Codes:** {predicted_count}/{len(df)}")
                else:
                    st.warning("No data available")
            except Exception as e:
                st.error(f"Error: {str(e)}")

def ensure_databricks_connection():
    """Ensure Databricks connection is established"""
    try:
        config = get_databricks_config()
        if not config.workspace_client:
            config.initialize_workspace_client()
        
        data_manager = get_data_manager()
        if not data_manager.spark:
            data_manager.initialize()
        
        return True
    except Exception as e:
        st.error(f"Failed to establish Databricks connection: {str(e)}")
        st.info("Please check your Databricks configuration and credentials.")
        return False
