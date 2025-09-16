"""
Streamlit UI for Credit Risk Analysis Demo - Phase 1 with LangGraph Visualization
Features:
- Collapsible top and bottom panels
- Company data table with filtering
- Mock SIC accuracy analysis
- Enhanced LangGraph workflow visualization
"""

# Add the project root to Python path for imports
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Credit Risk Analysis - LangGraph Visualization",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pickle
import time
import json

# Import SIC prediction utilities
from app.utils.sic_prediction_utils import get_sic_prediction_manager, display_prediction_result, batch_predict_visible_companies

# Import Phase 2 integration for LangGraph visualization
try:
    from app.core.phase2_integration import (
        initialize_phase2_integration,
        render_langgraph_visualization,
        PHASE2_AVAILABLE
    )
    PHASE2_ENABLED = True
except ImportError:
    PHASE2_ENABLED = False

# Page configuration
st.set_page_config(
    page_title="Credit Risk Analysis Demo",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for collapsible panels
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1f4e79, #2e86ab);
        color: white;
        margin-bottom: 2rem;
        border-radius: 10px;
    }
    
    .panel-header {
        background-color: #f0f2f6;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border-left: 4px solid #1f4e79;
        margin: 1rem 0;
    }
    
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    
    .accuracy-high {
        color: #28a745;
        font-weight: bold;
    }
    
    .accuracy-low {
        color: #dc3545;
        font-weight: bold;
    }
    
    .accuracy-medium {
        color: #ffc107;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_company_data():
    """Load and prepare company data"""
    try:
        # Try to load pre-processed data first
        if os.path.exists('data/enhanced_sample_data.pkl'):
            df = pd.read_pickle('data/enhanced_sample_data.pkl')
        else:
            # Load raw data and add mock enhancements
            df = pd.read_csv('data/Sample_data2.csv')
            
            # Generate mock accuracy data
            np.random.seed(42)
            
            # SIC Accuracy (0.0 to 1.0)
            base_accuracy = np.random.normal(0.88, 0.12, len(df))
            df['SIC_Accuracy'] = np.clip(base_accuracy, 0.0, 1.0)
            
            # Prediction confidence
            df['Prediction_Confidence'] = np.random.normal(0.85, 0.1, len(df))
            df['Prediction_Confidence'] = np.clip(df['Prediction_Confidence'], 0.0, 1.0)
            
            # Last update dates
            base_date = datetime.now()
            days_ago = np.random.randint(30, 800, len(df))
            df['Last_Updated'] = [base_date - timedelta(days=int(d)) for d in days_ago]
            df['Days_Since_Update'] = [(datetime.now() - date).days for date in df['Last_Updated']]
            df['Needs_Revenue_Update'] = df['Days_Since_Update'] > 365
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

@st.cache_data
def load_sic_codes():
    """Load SIC codes reference data"""
    try:
        df = pd.read_excel('data/SIC_codes.xlsx')
        # Rename columns properly
        df.columns = ['SIC_Code', 'Description']
        df['SIC_Code'] = df['SIC_Code'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading SIC codes: {e}")
        return None

def format_accuracy(accuracy):
    """Format accuracy with color coding"""
    if accuracy >= 0.9:
        return f'<span class="accuracy-high">{accuracy:.1%}</span>'
    elif accuracy >= 0.7:
        return f'<span class="accuracy-medium">{accuracy:.1%}</span>'
    else:
        return f'<span class="accuracy-low">{accuracy:.1%}</span>'

def create_filter_panel(df):
    """Create the left sidebar filter panel with collapsible sections"""
    st.sidebar.markdown("### 🔍 Filter & Display Options")
    
    # Panel Controls Section
    with st.sidebar.expander("📊 Panel Controls", expanded=True):
        show_top_panel = st.checkbox("Show Company Data Panel", value=True, key="show_top")
        show_bottom_panel = st.checkbox("Show Agent Flow Panel", value=True, key="show_bottom")
        show_langgraph_viz = st.checkbox("🚀 Show LangGraph Visualization", value=PHASE2_ENABLED, key="show_langgraph")
        
        # Store in session state for use in main()
        st.session_state['show_top_panel'] = show_top_panel
        st.session_state['show_bottom_panel'] = show_bottom_panel
        st.session_state['show_langgraph_viz'] = show_langgraph_viz
    
    # Column Selection Section
    with st.sidebar.expander("📋 Column Selection", expanded=True):
        st.markdown("**Select columns to display:**")
        
        # Define available columns for display
        display_columns = [
            'Company Name', 'UK SIC 2007 Code', 'Business Description', 
            'Website', 'Country', 'Sales', 'Employees (Total)', 
            'SIC_Accuracy', 'Last_Updated', 'Needs_Revenue_Update'
        ]
        
        # Filter to only include columns that exist in the dataframe
        available_columns = [col for col in display_columns if col in df.columns]
        
        # Default selection
        default_columns = ['Company Name', 'UK SIC 2007 Code', 'SIC_Accuracy', 'Business Description']
        default_selection = [col for col in default_columns if col in available_columns]
        
        # Multi-select with checkboxes
        selected_columns = []
        for col in available_columns:
            is_selected = st.checkbox(
                col, 
                value=(col in default_selection),
                key=f"col_{col}"
            )
            if is_selected:
                selected_columns.append(col)
        
        st.session_state['selected_columns'] = selected_columns
    
    # Data Filters Section  
    with st.sidebar.expander("🔍 Data Filters", expanded=True):
        # Quick Accuracy Filters
        st.markdown("**📊 Quick Accuracy Filters:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔴 Low\n(<70%)", use_container_width=True, help="Show companies with accuracy below 70%"):
                st.session_state['accuracy_filter'] = 'low'
                st.rerun()
        
        with col2:
            if st.button("🟡 Medium\n(70-90%)", use_container_width=True, help="Show companies with accuracy 70-90%"):
                st.session_state['accuracy_filter'] = 'medium'  
                st.rerun()
        
        with col3:
            if st.button("🟢 High\n(≥90%)", use_container_width=True, help="Show companies with accuracy 90% or higher"):
                st.session_state['accuracy_filter'] = 'high'
                st.rerun()
        
        # Clear filter button
        if st.button("🔄 Clear Filter", use_container_width=True):
            st.session_state['accuracy_filter'] = 'all'
            st.rerun()
        
        # Show current filter status
        current_filter = st.session_state.get('accuracy_filter', 'all')
        if current_filter != 'all':
            filter_labels = {
                'low': '🔴 Low Accuracy (<70%)',
                'medium': '🟡 Medium Accuracy (70-90%)', 
                'high': '🟢 High Accuracy (≥90%)'
            }
            st.info(f"Active: {filter_labels.get(current_filter, 'All')}")
        
        st.markdown("---")
        
        # Company size filter
        if 'Employees (Total)' in df.columns:
            # Clean and convert employee data
            emp_clean = df['Employees (Total)'].copy()
            emp_clean = emp_clean.astype(str).str.replace(',', '').str.replace('NaN', '0')
            emp_clean = pd.to_numeric(emp_clean, errors='coerce').fillna(0)
            
            # Only show filter if we have valid employee data
            if emp_clean.max() > 0:
                emp_min, emp_max = int(emp_clean.min()), int(emp_clean.max())
                emp_range = st.slider(
                    "Employee Count Range",
                    min_value=emp_min,
                    max_value=emp_max,
                    value=(emp_min, emp_max),
                    help="Filter companies by number of employees"
                )
            else:
                emp_range = None
        else:
            emp_range = None
        
        # Manual SIC Accuracy filter
        accuracy_min = st.slider(
            "Minimum SIC Accuracy",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            format="%.0f%%",
            help="Show only companies with SIC accuracy above this threshold"
        )
        
        # Country filter
        if 'Country' in df.columns:
            countries = ['All'] + sorted(df['Country'].unique().tolist())
            selected_country = st.selectbox("Country", countries)
        else:
            selected_country = 'All'
        
        # Revenue update needed filter
        show_update_needed = st.checkbox("Show only companies needing revenue update", False)
    
    return {
        'emp_range': emp_range,
        'accuracy_min': accuracy_min,
        'country': selected_country,
        'update_needed': show_update_needed,
        'selected_columns': selected_columns
    }

def apply_filters(df, filters):
    """Apply filters to the dataframe including accuracy categories"""
    filtered_df = df.copy()
    
    # Quick accuracy category filter
    accuracy_filter = st.session_state.get('accuracy_filter', 'all')
    if accuracy_filter == 'low':
        filtered_df = filtered_df[filtered_df['SIC_Accuracy'] < 0.7]
    elif accuracy_filter == 'medium':
        filtered_df = filtered_df[(filtered_df['SIC_Accuracy'] >= 0.7) & (filtered_df['SIC_Accuracy'] < 0.9)]
    elif accuracy_filter == 'high':
        filtered_df = filtered_df[filtered_df['SIC_Accuracy'] >= 0.9]
    
    # Employee range filter
    if filters['emp_range'] and 'Employees (Total)' in df.columns:
        # Clean employee data for filtering
        emp_clean = filtered_df['Employees (Total)'].copy()
        emp_clean = emp_clean.astype(str).str.replace(',', '').str.replace('NaN', '0')
        emp_clean = pd.to_numeric(emp_clean, errors='coerce').fillna(0)
        
        filtered_df = filtered_df[
            (emp_clean >= filters['emp_range'][0]) &
            (emp_clean <= filters['emp_range'][1])
        ]
    
    # Manual accuracy filter (only if no category filter is active)
    if accuracy_filter == 'all':
        filtered_df = filtered_df[filtered_df['SIC_Accuracy'] >= filters['accuracy_min']]
    
    # Country filter
    if filters['country'] != 'All' and 'Country' in df.columns:
        filtered_df = filtered_df[filtered_df['Country'] == filters['country']]
    
    # Update needed filter
    if filters['update_needed']:
        filtered_df = filtered_df[filtered_df['Needs_Revenue_Update'] == True]
    
    return filtered_df

def create_company_table(df):
    """Create the main company data table with real action buttons"""
    
    # Get selected columns from session state
    selected_columns = st.session_state.get('selected_columns', ['Company Name', 'UK SIC 2007 Code', 'SIC_Accuracy'])
    
    # Ensure we have some columns selected
    if not selected_columns:
        selected_columns = ['Company Name', 'UK SIC 2007 Code', 'SIC_Accuracy']
    
    # Filter columns to only include ones that exist in the dataframe
    available_columns = [col for col in selected_columns if col in df.columns]
    
    if not available_columns:
        st.warning("Please select at least one valid column to display.")
        return
    
    # Prepare display dataframe
    display_df = df[available_columns].copy()
    
    # Add formatted SIC Accuracy column if selected
    if 'SIC_Accuracy' in available_columns:
        accuracy_col = []
        for _, row in df.iterrows():
            accuracy = row['SIC_Accuracy'] if 'SIC_Accuracy' in row else 0
            formatted_accuracy = format_accuracy(accuracy)
            accuracy_col.append(formatted_accuracy)
        
        # Replace the SIC_Accuracy column with formatted version
        display_df['SIC_Accuracy'] = accuracy_col
    
    # Display table with proper headers and color-coded accuracy
    st.markdown("### 📊 Company Data Table")
    
    # Table controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    with col1:
        rows_per_page = st.selectbox("Rows per page:", [10, 25, 50, 100], index=1)
    with col2:
        page_number = st.number_input("Page:", min_value=1, max_value=max(1, len(display_df)//rows_per_page + 1), value=1)
    with col3:
        st.metric("Total Rows", len(display_df))
    with col4:
        # Action buttons for selected companies
        if st.button("🔮 Predict SIC for Visible", type="primary"):
            # Get visible row indices based on current pagination
            start_idx = (page_number - 1) * rows_per_page
            end_idx = min(start_idx + rows_per_page, len(display_df))
            visible_indices = list(range(start_idx, end_idx))
            
            with st.spinner("🤖 Running SIC predictions..."):
                # Run batch predictions
                batch_results = batch_predict_visible_companies(display_df, visible_indices)
                
                # Update session state with predictions
                if 'sic_predictions' not in st.session_state:
                    st.session_state['sic_predictions'] = {}
                
                for result in batch_results["predictions"]:
                    idx = result["index"]
                    prediction = result["prediction"]
                    if prediction.get("success"):
                        st.session_state['sic_predictions'][idx] = prediction
                
                # Show summary
                st.success(f"✅ Batch prediction completed!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Processed", len(visible_indices))
                with col2:
                    st.metric("Successful", batch_results["successful"])
                with col3:
                    st.metric("Failed", batch_results["failed"])
                    
                # Force rerun to show updated data
                st.rerun()
                
        if st.button("📊 Update Revenue for All"):
            st.info("📊 Revenue update initiated for all companies!")
    
    # Calculate pagination
    start_idx = (page_number - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    
    # Display paginated table
    paginated_df = display_df.iloc[start_idx:end_idx].copy()
    
    # Create table with proper headers and formatting
    if len(paginated_df) > 0:
        # Create column headers
        header_cols = st.columns(len(available_columns) + 2)
        
        # Display headers
        for col_idx, col_name in enumerate(available_columns):
            with header_cols[col_idx]:
                st.markdown(f"**{col_name}**")
        
        with header_cols[-2]:
            st.markdown("**Predict SIC**")
        with header_cols[-1]:
            st.markdown("**Update Revenue**")
        
        st.markdown("---")
        
        # Display data rows with proper formatting
        for idx, (_, row) in enumerate(paginated_df.iterrows()):
            with st.container():
                cols = st.columns(len(available_columns) + 2)
                
                # Display data columns with special formatting for SIC_Accuracy
                for col_idx, col_name in enumerate(available_columns):
                    with cols[col_idx]:
                        if col_name == 'SIC_Accuracy':
                            # Color-coded accuracy display
                            accuracy = row[col_name] if isinstance(row[col_name], (int, float)) else 0.0
                            if isinstance(row[col_name], str) and '%' in str(row[col_name]):
                                # Extract percentage if it's already formatted
                                try:
                                    accuracy = float(str(row[col_name]).replace('%', '').replace('<span class="accuracy-high">', '').replace('<span class="accuracy-medium">', '').replace('<span class="accuracy-low">', '').replace('</span>', '')) / 100
                                except:
                                    accuracy = 0.0
                            
                            if accuracy >= 0.9:
                                st.markdown(f'<span style="color: #28a745; font-weight: bold; background-color: #d4edda; padding: 2px 8px; border-radius: 4px;">✅ {accuracy:.1%}</span>', unsafe_allow_html=True)
                            elif accuracy >= 0.7:
                                st.markdown(f'<span style="color: #fd7e14; font-weight: bold; background-color: #fff3cd; padding: 2px 8px; border-radius: 4px;">⚠️ {accuracy:.1%}</span>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<span style="color: #dc3545; font-weight: bold; background-color: #f8d7da; padding: 2px 8px; border-radius: 4px;">❌ {accuracy:.1%}</span>', unsafe_allow_html=True)
                        elif col_idx == 0:  # First column - make it bold
                            st.markdown(f"**{row[col_name]}**")
                        else:
                            # Handle other data types properly
                            value = row[col_name]
                            if pd.isna(value):
                                st.write("—")
                            elif isinstance(value, (int, float)):
                                if col_name in ['Sales', 'Sales (USD)'] and value > 1000:
                                    st.write(f"${value:,.0f}")
                                elif col_name in ['Employees (Total)']:
                                    st.write(f"{value:,.0f}")
                                else:
                                    st.write(value)
                            else:
                                # Truncate long text
                                text = str(value)
                                if len(text) > 50:
                                    st.write(f"{text[:50]}...")
                                else:
                                    st.write(text)
                
                # Action buttons for each row
                with cols[-2]:
                    actual_idx = start_idx + idx
                    prediction_key = f"prediction_{actual_idx}"
                    
                    if st.button("🔮", key=f"predict_{actual_idx}", help="Predict SIC Code"):
                        with st.spinner("🤖 Predicting SIC..."):
                            # Get SIC prediction manager
                            manager = get_sic_prediction_manager()
                            prediction = manager.predict_for_dataframe_row(paginated_df, idx)
                            
                            # Store prediction in session state
                            if 'sic_predictions' not in st.session_state:
                                st.session_state['sic_predictions'] = {}
                            
                            if prediction.get("success"):
                                st.session_state['sic_predictions'][actual_idx] = prediction
                                st.session_state[prediction_key] = prediction
                                st.rerun()
                            else:
                                st.error(f"❌ Prediction failed: {prediction.get('error', 'Unknown error')}")
                    
                    # Show prediction if available
                    if prediction_key in st.session_state or actual_idx in st.session_state.get('sic_predictions', {}):
                        prediction = st.session_state.get(prediction_key) or st.session_state['sic_predictions'].get(actual_idx)
                        if prediction and prediction.get("success"):
                            with st.expander("🎯 Prediction", expanded=False):
                                display_prediction_result(prediction)
                                
                                # Add buttons to apply or reject prediction
                                col_apply, col_reject = st.columns(2)
                                with col_apply:
                                    if st.button("✅ Apply", key=f"apply_{actual_idx}"):
                                        st.success("Applied to dataset!")
                                        # Here you would update the main dataset
                                        
                                with col_reject:
                                    if st.button("❌ Reject", key=f"reject_{actual_idx}"):
                                        # Remove prediction
                                        if prediction_key in st.session_state:
                                            del st.session_state[prediction_key]
                                        if actual_idx in st.session_state.get('sic_predictions', {}):
                                            del st.session_state['sic_predictions'][actual_idx]
                                        st.rerun()
                
                with cols[-1]:
                    if st.button("📊", key=f"update_{start_idx + idx}", help="Update Revenue"):
                        st.info(f"📊 Revenue update started for {row[available_columns[0]]}")
                
                st.markdown("---")
    
    # Display summary of current predictions
    if 'sic_predictions' in st.session_state and st.session_state['sic_predictions']:
        st.markdown("### 🎯 **Current SIC Predictions**")
        
        prediction_data = []
        for idx, prediction in st.session_state['sic_predictions'].items():
            if prediction.get("success"):
                prediction_data.append({
                    "Row": idx + 1,
                    "Company": prediction.get("company_name", ""),
                    "Current SIC": prediction.get("current_sic", "N/A"),
                    "Predicted SIC": prediction.get("predicted_sic", ""),
                    "Description": prediction.get("predicted_description", ""),
                    "Confidence": f"{prediction.get('confidence', 0):.1%}",
                    "Status": "Ready to Apply"
                })
        
        if prediction_data:
            pred_df = pd.DataFrame(prediction_data)
            st.dataframe(pred_df, use_container_width=True)
            
            # Bulk actions for predictions
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Apply All Predictions", type="primary"):
                    # Apply all predictions to the dataset
                    st.success(f"Applied {len(prediction_data)} predictions to the dataset!")
                    # Clear predictions after applying
                    st.session_state['sic_predictions'] = {}
                    st.rerun()
            
            with col2:
                if st.button("❌ Clear All Predictions"):
                    st.session_state['sic_predictions'] = {}
                    st.rerun()
            
            with col3:
                if st.button("💾 Export Predictions"):
                    # Create downloadable CSV
                    csv = pred_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"sic_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
    
    return paginated_df

def create_summary_metrics(df):
    """Create summary metrics for the dataset with accuracy breakdown"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Companies",
            len(df),
            help="Number of companies in current view"
        )
    
    with col2:
        avg_accuracy = df['SIC_Accuracy'].mean()
        st.metric(
            "Avg SIC Accuracy",
            f"{avg_accuracy:.1%}",
            help="Average SIC code accuracy across all companies"
        )
    
    with col3:
        high_accuracy = (df['SIC_Accuracy'] >= 0.9).sum()
        st.metric(
            "🟢 High Accuracy",
            high_accuracy,
            delta=f"{high_accuracy/len(df)*100:.1f}%",
            delta_color="normal",
            help="Companies with SIC accuracy ≥90%"
        )
    
    with col4:
        medium_accuracy = ((df['SIC_Accuracy'] >= 0.7) & (df['SIC_Accuracy'] < 0.9)).sum()
        st.metric(
            "🟡 Medium Accuracy", 
            medium_accuracy,
            delta=f"{medium_accuracy/len(df)*100:.1f}%",
            delta_color="normal",
            help="Companies with SIC accuracy 70-90%"
        )
    
    with col5:
        low_accuracy = (df['SIC_Accuracy'] < 0.7).sum()
        st.metric(
            "🔴 Low Accuracy",
            low_accuracy,
            delta=f"{low_accuracy/len(df)*100:.1f}%",
            delta_color="inverse",
            help="Companies with SIC accuracy <70% - needs attention!"
        )

def create_langgraph_agent_flow():
    """Create a LangGraph-style vertical agent flow visualization"""
    
    # Define the agent workflow states
    agents = [
        {"name": "Data Ingestion Agent", "status": "completed", "description": "Company data loaded", "processing_time": "2.3s"},
        {"name": "Document Retrieval Agent", "status": "completed", "description": "Website content scraped", "processing_time": "15.7s"},
        {"name": "NLP Processing Agent", "status": "processing", "description": "Analyzing business descriptions", "processing_time": "8.2s"},
        {"name": "SIC Classification Agent", "status": "waiting", "description": "ML model prediction pending", "processing_time": "-"},
        {"name": "Validation Agent", "status": "waiting", "description": "Accuracy assessment pending", "processing_time": "-"}
    ]
    
    # Create vertical flow chart
    fig = go.Figure()
    
    # Define colors for different statuses
    status_colors = {
        "completed": "#28a745",    # Green
        "processing": "#fd7e14",   # Orange  
        "waiting": "#dc3545",      # Red
        "idle": "#6c757d"          # Gray
    }
    
    # Create nodes (agents)
    for i, agent in enumerate(agents):
        y_pos = len(agents) - i - 1  # Reverse order for top-to-bottom flow
        
        # Add agent node
        fig.add_trace(go.Scatter(
            x=[0],
            y=[y_pos],
            mode='markers+text',
            marker=dict(
                size=60,
                color=status_colors[agent["status"]],
                line=dict(width=3, color='white'),
                symbol='circle'
            ),
            text=agent["name"],
            textposition="middle right",
            textfont=dict(size=11, color='black'),
            showlegend=False,
            hovertemplate=f"<b>{agent['name']}</b><br>" +
                         f"Status: {agent['status'].title()}<br>" +
                         f"Description: {agent['description']}<br>" +
                         f"Processing Time: {agent['processing_time']}<br>" +
                         "<extra></extra>"
        ))
        
        # Add status indicator
        status_symbol = {
            "completed": "✅",
            "processing": "🔄", 
            "waiting": "⏳",
            "idle": "⏸️"
        }
        
        fig.add_trace(go.Scatter(
            x=[-0.3],
            y=[y_pos],
            mode='text',
            text=status_symbol[agent["status"]],
            textfont=dict(size=20),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add processing time
        fig.add_trace(go.Scatter(
            x=[2.5],
            y=[y_pos],
            mode='text',
            text=agent["processing_time"],
            textfont=dict(size=10, color='gray'),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add connecting arrows (except for last agent)
        if i < len(agents) - 1:
            fig.add_trace(go.Scatter(
                x=[0, 0],
                y=[y_pos - 0.2, y_pos - 0.8],
                mode='lines',
                line=dict(color='#6c757d', width=3),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            # Add arrow head
            fig.add_annotation(
                x=0,
                y=y_pos - 0.8,
                ax=0,
                ay=y_pos - 0.7,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=3,
                arrowcolor="#6c757d",
                showarrow=True
            )
    
    # Update layout for vertical flow
    fig.update_layout(
        title="🤖 SIC Prediction Agent Flow (LangGraph)",
        title_font_size=16,
        height=500,  # Increased height for vertical flow
        width=700,
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[-1, 3]
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[-0.5, len(agents) - 0.5]
        ),
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=50, r=50, t=70, b=30)
    )
    
    return fig

def create_revenue_agent_flow():
    """Create revenue update agent flow"""
    
    agents = [
        {"name": "Filing Date Checker", "status": "completed", "description": "Check last filing date", "processing_time": "1.2s"},
        {"name": "Companies House Client", "status": "processing", "description": "Fetching latest data", "processing_time": "3.4s"},
        {"name": "Data Validator", "status": "waiting", "description": "Validate new revenue data", "processing_time": "-"},
        {"name": "Update Manager", "status": "waiting", "description": "Apply updates to database", "processing_time": "-"}
    ]
    
    fig = go.Figure()
    
    status_colors = {
        "completed": "#28a745",
        "processing": "#fd7e14",
        "waiting": "#dc3545",
        "idle": "#6c757d"
    }
    
    for i, agent in enumerate(agents):
        y_pos = len(agents) - i - 1
        
        fig.add_trace(go.Scatter(
            x=[0],
            y=[y_pos],
            mode='markers+text',
            marker=dict(
                size=50,
                color=status_colors[agent["status"]],
                line=dict(width=3, color='white'),
                symbol='circle'
            ),
            text=agent["name"],
            textposition="middle right",
            textfont=dict(size=10, color='black'),
            showlegend=False,
            hovertemplate=f"<b>{agent['name']}</b><br>" +
                         f"Status: {agent['status'].title()}<br>" +
                         f"Description: {agent['description']}<br>" +
                         f"Processing Time: {agent['processing_time']}<br>" +
                         "<extra></extra>"
        ))
        
        status_symbol = {
            "completed": "✅",
            "processing": "🔄", 
            "waiting": "⏳",
            "idle": "⏸️"
        }
        
        fig.add_trace(go.Scatter(
            x=[-0.25],
            y=[y_pos],
            mode='text',
            text=status_symbol[agent["status"]],
            textfont=dict(size=16),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add connecting arrows (except for last agent)
        if i < len(agents) - 1:
            fig.add_trace(go.Scatter(
                x=[0, 0],
                y=[y_pos - 0.2, y_pos - 0.8],
                mode='lines',
                line=dict(color='#6c757d', width=2),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            fig.add_annotation(
                x=0,
                y=y_pos - 0.8,
                ax=0,
                ay=y_pos - 0.7,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="#6c757d",
                showarrow=True
            )
    
    fig.update_layout(
        title="💰 Revenue Update Agent Flow",
        title_font_size=14,
        height=350,
        width=500,
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[-0.8, 2.5]
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[-0.5, len(agents) - 0.5]
        ),
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=30, r=30, t=50, b=20)
    )
    
    return fig

def create_agent_visualization():
    """Create professional agent orchestration visualization with real buttons"""
    st.markdown("### 🤖 Agent Orchestration (Live)")
    
    # Create tabs for different agent workflows
    tab1, tab2 = st.tabs(["SIC Prediction Agents", "Revenue Update Agents"])
    
    with tab1:
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Show LangGraph-style vertical flow
            fig = create_langgraph_agent_flow()
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**Agent Controls:**")
            
            # Professional status buttons
            if st.button("🔄 Start SIC Prediction", key="start_sic", type="primary"):
                st.session_state['sic_running'] = True
                st.rerun()
            
            if st.button("⏹️ Stop All Agents", key="stop_sic"):
                st.session_state['sic_running'] = False
                st.rerun()
                
            st.markdown("---")
            st.markdown("**System Status:**")
            
            # Professional status indicators
            status_running = st.session_state.get('sic_running', False)
            if status_running:
                st.success("🟢 **Processing** - Agents Active")
            else:
                st.error("🔴 **Stopped** - Agents Idle")
                
            st.markdown("**Queue:** 47 companies pending")
            st.markdown("**Processed:** 462 companies")
            st.markdown("**Avg Accuracy:** 85.2%")
    
    with tab2:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            fig = create_revenue_agent_flow()
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.markdown("**Revenue Controls:**")
            
            if st.button("� Start Revenue Update", key="start_revenue", type="primary"):
                st.session_state['revenue_running'] = True
                st.rerun()
            
            if st.button("⏹️ Stop Revenue Update", key="stop_revenue"):
                st.session_state['revenue_running'] = False
                st.rerun()
                
            st.markdown("---")
            st.markdown("**Revenue Status:**")
            
            revenue_running = st.session_state.get('revenue_running', False)
            if revenue_running:
                st.warning("🟡 **Just Finished** - Updates Complete")
            else:
                st.error("🔴 **Not Working** - System Idle")
                
            st.markdown("**Updates:** 23 pending")
            st.markdown("**Last Run:** 2 hours ago")
        st.write("4. 💾 Database Updater")

def main():
    """Main application function with collapsible panels"""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏦 Credit Risk Analysis Demo - Phase 1</h1>
        <p>Multi-Agent System for SIC Code Validation & Revenue Verification</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data
    company_data = load_company_data()
    sic_codes = load_sic_codes()
    
    if company_data is None:
        st.error("Could not load company data. Please check the data files.")
        return
    
    # Create filter panel (includes panel controls and column selection)
    filters = create_filter_panel(company_data)
    
    # Apply filters
    filtered_data = apply_filters(company_data, filters)
    
    # Get panel visibility from session state
    show_top_panel = st.session_state.get('show_top_panel', True)
    show_bottom_panel = st.session_state.get('show_bottom_panel', True)
    show_langgraph_viz = st.session_state.get('show_langgraph_viz', False)
    
    # TOP PANEL - Company Data Analysis
    if show_top_panel:
        with st.container():
            st.markdown('<div class="panel-header"><h2>📋 TOP PANEL - Company Data Analysis</h2></div>', unsafe_allow_html=True)
            
            # Summary metrics
            create_summary_metrics(filtered_data)
            
            # Main data table
            if len(filtered_data) > 0:
                table_data = create_company_table(filtered_data)
                
                # Quick insights
                with st.expander("💡 Quick Insights", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # SIC accuracy distribution
                        fig_accuracy = px.histogram(
                            filtered_data, 
                            x='SIC_Accuracy',
                            nbins=20,
                            title="SIC Accuracy Distribution",
                            labels={'SIC_Accuracy': 'SIC Accuracy', 'count': 'Number of Companies'}
                        )
                        fig_accuracy.update_traces(marker_color='#1f77b4')
                        st.plotly_chart(fig_accuracy, use_container_width=True)
                    
                    with col2:
                        # Companies by country
                        if 'Country' in filtered_data.columns:
                            country_counts = filtered_data['Country'].value_counts().head(10)
                            fig_country = px.bar(
                                x=country_counts.values,
                                y=country_counts.index,
                                orientation='h',
                                title="Top 10 Countries by Company Count",
                                color=country_counts.values,
                                color_continuous_scale='viridis'
                            )
                            st.plotly_chart(fig_country, use_container_width=True)
            else:
                st.warning("No companies match the current filter criteria.")
    
    # Separator between panels
    if show_top_panel and show_bottom_panel:
        st.markdown("---")
    
    # BOTTOM PANEL - Agent Orchestration
    if show_bottom_panel:
        with st.container():
            st.markdown('<div class="panel-header"><h2>🤖 BOTTOM PANEL - Agent Orchestration (LangGraph)</h2></div>', unsafe_allow_html=True)
            
            # Agent visualization with increased height for vertical flow
            st.markdown("""
            <style>
            .bottom-panel {
                min-height: 600px;
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin: 10px 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown('<div class="bottom-panel">', unsafe_allow_html=True)
                
                # Agent visualization
                create_agent_visualization()
                
                # System status
                with st.expander("⚙️ System Status & Metrics", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Data Sources:**")
                        st.success("✅ Company Data Loaded (509 companies)")
                        st.success("✅ SIC Codes Reference (751 codes)")
                        st.info("🔄 Enhanced Mock Accuracy Data")
                    
                    with col2:
                        st.markdown("**Agent Systems:**")
                        if st.session_state.get('sic_running', False):
                            st.success("� SIC Prediction Agents - Active")
                        else:
                            st.error("🔴 SIC Prediction Agents - Idle")
                        
                        if st.session_state.get('revenue_running', False):
                            st.warning("� Revenue Update Agents - Processing")
                        else:
                            st.error("🔴 Revenue Update Agents - Stopped")
                        
                        st.info("� Validation Agents - Standby")
                    
                    with col3:
                        st.markdown("**Performance Metrics:**")
                        st.metric("Processing Speed", "47.3 companies/min")
                        st.metric("Accuracy Rate", "85.2%", "↑2.1%")
                        st.metric("System Uptime", "99.8%")
                        
                        st.markdown("**Future Integrations:**")
                        st.write("🔜 Companies House API")
                        st.write("🔜 Website Scraping Pipeline")
                        st.write("🔜 Databricks Apps Deployment")
                
                st.markdown('</div>', unsafe_allow_html=True)

    # LANGGRAPH VISUALIZATION PANEL
    show_langgraph_viz = st.session_state.get('show_langgraph_viz', False)
    if show_langgraph_viz and PHASE2_ENABLED:
        st.markdown("---")
        with st.container():
            st.markdown('<div class="panel-header"><h2>🚀 LANGGRAPH WORKFLOW VISUALIZATION</h2></div>', unsafe_allow_html=True)
            
            # Enhanced visualization container
            st.markdown("""
            <style>
            .langgraph-panel {
                min-height: 700px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                padding: 30px;
                margin: 20px 0;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown('<div class="langgraph-panel">', unsafe_allow_html=True)
                
                # Render the LangGraph visualization
                try:
                    render_langgraph_visualization()
                except Exception as e:
                    st.error(f"Error rendering LangGraph visualization: {e}")
                    st.info("💡 Ensure Phase 2 dependencies are installed: `pip install -r requirements_phase2.txt`")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
    elif show_langgraph_viz and not PHASE2_ENABLED:
        st.warning("⚠️ LangGraph visualization requires Phase 2 dependencies. Install requirements_phase2.txt")

if __name__ == "__main__":
    main()
