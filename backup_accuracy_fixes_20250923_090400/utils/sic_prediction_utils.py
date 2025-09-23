"""
Utility functions for SIC prediction in Streamlit app
"""
import sys
import os
import pandas as pd
from typing import Dict, Any, List, Optional
import streamlit as st

# Add the parent directory to sys.path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.sector_classification_agent import SectorClassificationAgent

class SICPredictionManager:
    """Manager class for SIC predictions in Streamlit app"""
    
    def __init__(self):
        self.agent = SectorClassificationAgent()
        
    def predict_for_company(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict SIC code for a single company
        
        Args:
            company_data: Company data dictionary
            
        Returns:
            Prediction result dictionary
        """
        result = self.agent.predict_single_company(company_data)
        if result is None:
            return {"success": False, "error": "No prediction returned from agent"}
        return result
    
    def predict_for_dataframe_row(self, df: pd.DataFrame, row_index: int) -> Dict[str, Any]:
        """
        Predict SIC code for a specific row in the dataframe
        
        Args:
            df: The dataframe containing company data
            row_index: Index of the row to predict
            
        Returns:
            Prediction result dictionary
        """
        if row_index >= len(df):
            return {"success": False, "error": "Invalid row index"}
        
        row_data = df.iloc[row_index].to_dict()
        return self.predict_for_company(row_data)
    
    def update_dataframe_with_prediction(self, df: pd.DataFrame, row_index: int, prediction: Dict[str, Any]) -> pd.DataFrame:
        """
        Update dataframe with prediction results
        
        Args:
            df: The dataframe to update
            row_index: Index of the row to update
            prediction: Prediction result dictionary
            
        Returns:
            Updated dataframe
        """
        if not prediction.get("success"):
            return df
        
        # Add predicted SIC columns if they don't exist
        if 'Predicted SIC Code' not in df.columns:
            df['Predicted SIC Code'] = ''
        if 'Predicted SIC Description' not in df.columns:
            df['Predicted SIC Description'] = ''
        if 'Prediction Confidence' not in df.columns:
            df['Prediction Confidence'] = 0.0
        if 'Prediction Status' not in df.columns:
            df['Prediction Status'] = ''
        
        # Update the specific row
        df.at[row_index, 'Predicted SIC Code'] = prediction.get('predicted_sic', '')
        df.at[row_index, 'Predicted SIC Description'] = prediction.get('predicted_description', '')
        df.at[row_index, 'Prediction Confidence'] = prediction.get('confidence', 0.0)
        df.at[row_index, 'Prediction Status'] = 'Predicted'
        
        return df
    
    def apply_prediction_to_original(self, df: pd.DataFrame, row_index: int, prediction: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply the predicted SIC code to the original SIC code column
        
        Args:
            df: The dataframe to update
            row_index: Index of the row to update
            prediction: Prediction result dictionary
            
        Returns:
            Updated dataframe
        """
        if not prediction.get("success"):
            return df
        
        # Update the original SIC code column
        if 'UK SIC 2007 Code' in df.columns:
            df.at[row_index, 'UK SIC 2007 Code'] = prediction.get('predicted_sic', '')
        
        # Update status
        if 'Prediction Status' in df.columns:
            df.at[row_index, 'Prediction Status'] = 'Applied'
        
        return df

# Global instance for use in Streamlit
@st.cache_resource
def get_sic_prediction_manager():
    """Get cached SIC prediction manager instance"""
    return SICPredictionManager()

def display_prediction_result(prediction: Dict[str, Any]):
    """
    Display prediction result in Streamlit
    
    Args:
        prediction: Prediction result dictionary
    """
    if prediction.get("success"):
        st.success("🎯 SIC Prediction Completed!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Prediction Details:**")
            st.write(f"**Predicted SIC:** {prediction.get('predicted_sic')}")
            st.write(f"**Description:** {prediction.get('predicted_description')}")
            st.write(f"**Confidence:** {prediction.get('confidence', 0):.1%}")
        
        with col2:
            st.markdown("**Analysis:**")
            st.write(f"**Keywords Matched:** {', '.join(prediction.get('keywords_matched', []))}")
            if prediction.get('current_sic'):
                st.write(f"**Current SIC:** {prediction.get('current_sic')}")
        
        # Show reasoning
        with st.expander("🧠 Reasoning", expanded=False):
            st.write(prediction.get('reasoning', 'No reasoning provided'))
            st.write(f"**Business Description:** {prediction.get('business_description', '')}")
    
    else:
        st.error(f"❌ Prediction Failed: {prediction.get('error', 'Unknown error')}")

def batch_predict_visible_companies(df: pd.DataFrame, visible_indices: List[int]) -> Dict[str, Any]:
    """
    Predict SIC codes for multiple visible companies
    
    Args:
        df: The dataframe containing company data
        visible_indices: List of indices for visible companies
        
    Returns:
        Batch prediction results
    """
    manager = get_sic_prediction_manager()
    results = {
        "predictions": [],
        "successful": 0,
        "failed": 0
    }
    
    for idx in visible_indices:
        prediction = manager.predict_for_dataframe_row(df, idx)
        results["predictions"].append({
            "index": idx,
            "prediction": prediction
        })
        
        if prediction.get("success"):
            results["successful"] += 1
        else:
            results["failed"] += 1
    
    return results
