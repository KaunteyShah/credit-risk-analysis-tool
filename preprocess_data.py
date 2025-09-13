"""
Data Preprocessor for Streamlit Demo
Generates enhanced company data with mock accuracy scores
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def preprocess_data():
    """Preprocess the company data for the demo"""
    print("🔄 Preprocessing company data...")
    
    try:
        # Load the sample data
        df = pd.read_excel('data/Sample data_09Sep2025.xlsx')
        print(f"✅ Loaded {len(df)} companies from sample data")
        
        # Set random seed for consistent results
        np.random.seed(42)
        
        # Generate SIC Accuracy scores
        # Most companies should have high accuracy (realistic scenario)
        base_accuracy = np.random.beta(8, 2, len(df))  # Beta distribution skewed towards high values
        
        # Adjust accuracy based on business description availability
        if 'Business Description' in df.columns:
            has_description = df['Business Description'].notna()
            # Companies with business descriptions are more likely to have accurate SIC codes
            base_accuracy[has_description] *= np.random.normal(1.05, 0.1, has_description.sum())
            base_accuracy[~has_description] *= np.random.normal(0.85, 0.15, (~has_description).sum())
        
        # Adjust for company size (larger companies more likely to have correct codes)
        if 'Employees (Total)' in df.columns:
            emp_data = df['Employees (Total)'].fillna(df['Employees (Total)'].median())
            size_factor = np.log(emp_data + 1) / np.log(emp_data.max() + 1)
            base_accuracy *= (0.9 + 0.2 * size_factor)  # Size factor between 0.9 and 1.1
        
        # Ensure accuracy is between 0 and 1
        df['SIC_Accuracy'] = np.clip(base_accuracy, 0.0, 1.0)
        
        # Generate prediction confidence (for future use)
        df['Prediction_Confidence'] = np.random.beta(7, 2, len(df))  # High confidence distribution
        
        # Generate last update dates
        base_date = datetime.now()
        # Most recent updates within last 2 years, some older
        days_ago = np.random.exponential(200, len(df))  # Exponential distribution
        days_ago = np.clip(days_ago, 10, 1000)  # Between 10 days and ~3 years
        
        df['Last_Updated'] = [base_date - timedelta(days=int(d)) for d in days_ago]
        df['Days_Since_Update'] = [(datetime.now() - date).days for date in df['Last_Updated']]
        df['Needs_Revenue_Update'] = df['Days_Since_Update'] > 365
        
        # Add some additional useful columns
        df['SIC_Status'] = df['SIC_Accuracy'].apply(lambda x: 
            'High' if x >= 0.9 else 'Medium' if x >= 0.7 else 'Low'
        )
        
        # Clean up the data types
        numeric_columns = ['Sales (USD)', 'Pre Tax Profit (USD)', 'Assets (USD)', 
                          'Employees (Single Site)', 'Employees (Total)']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Save the enhanced data
        df.to_pickle('data/enhanced_sample_data.pkl')
        print(f"💾 Enhanced data saved with {len(df)} companies")
        
        # Generate summary statistics
        print("\n📊 Data Summary:")
        print(f"   • Average SIC Accuracy: {df['SIC_Accuracy'].mean():.3f}")
        print(f"   • High accuracy companies (≥90%): {(df['SIC_Accuracy'] >= 0.9).sum()}")
        print(f"   • Medium accuracy companies (70-90%): {((df['SIC_Accuracy'] >= 0.7) & (df['SIC_Accuracy'] < 0.9)).sum()}")
        print(f"   • Low accuracy companies (<70%): {(df['SIC_Accuracy'] < 0.7).sum()}")
        print(f"   • Companies needing revenue update: {df['Needs_Revenue_Update'].sum()}")
        
        # Show SIC code analysis
        if 'UK SIC 2007 Code' in df.columns:
            unique_sics = df['UK SIC 2007 Code'].nunique()
            print(f"   • Unique SIC codes: {unique_sics}")
            
            # Top SIC codes by frequency
            top_sics = df['UK SIC 2007 Code'].value_counts().head(5)
            print("   • Top 5 SIC codes:")
            for sic, count in top_sics.items():
                print(f"     - {sic}: {count} companies")
        
        return df
        
    except Exception as e:
        print(f"❌ Error preprocessing data: {e}")
        return None

if __name__ == "__main__":
    print("🏦 Credit Risk Demo - Data Preprocessor")
    print("=" * 45)
    
    result = preprocess_data()
    
    if result is not None:
        print("\n✅ Data preprocessing completed successfully!")
        print("🚀 Ready to run Streamlit app!")
    else:
        print("\n❌ Data preprocessing failed!")
