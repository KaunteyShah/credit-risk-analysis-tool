"""
Data Analysis Script for Credit Risk Demo
Analyzes the sample company data and SIC codes reference data
"""
import pandas as pd
import numpy as np
import sys
import os

def analyze_sample_data():
    """Analyze the sample company data"""
    try:
        print("=== SAMPLE DATA ANALYSIS ===")
        df = pd.read_excel('data/Sample data_09Sep2025.xlsx')
        
        print(f"Dataset Shape: {df.shape[0]} companies, {df.shape[1]} columns")
        
        # Key columns for our analysis
        key_columns = [
            'Company Name', 'UK SIC 2007 Code', 'UK SIC 2007 Description',
            'Website', 'Business Description', 'Sales (USD)', 'Employees (Total)',
            'City', 'Country'
        ]
        
        print("\n📊 Key Columns for Analysis:")
        for col in key_columns:
            if col in df.columns:
                print(f"✅ {col}")
            else:
                print(f"❌ {col} - NOT FOUND")
        
        # UK SIC Code Analysis
        print("\n🎯 UK SIC 2007 Code Analysis:")
        sic_col = 'UK SIC 2007 Code'
        if sic_col in df.columns:
            print(f"   • Total unique SIC codes: {df[sic_col].nunique()}")
            print(f"   • Missing values: {df[sic_col].isna().sum()}")
            
            # Top 10 most common SIC codes
            top_sics = df[sic_col].value_counts().head(10)
            print(f"\n   📈 Top 10 SIC codes:")
            for sic, count in top_sics.items():
                desc = df[df[sic_col] == sic]['UK SIC 2007 Description'].iloc[0]
                print(f"      {sic}: {count} companies - {desc}")
        
        # Company size distribution
        print("\n💼 Company Size Analysis:")
        if 'Employees (Total)' in df.columns:
            emp_stats = df['Employees (Total)'].describe()
            print(f"   • Employee range: {emp_stats['min']:.0f} - {emp_stats['max']:.0f}")
            print(f"   • Median employees: {emp_stats['50%']:.0f}")
            
        # Website availability
        if 'Website' in df.columns:
            websites_available = df['Website'].notna().sum()
            print(f"   • Companies with websites: {websites_available}/{len(df)} ({websites_available/len(df)*100:.1f}%)")
        
        return df
        
    except Exception as e:
        print(f"Error analyzing sample data: {e}")
        return None

def analyze_sic_codes():
    """Analyze the SIC codes reference data"""
    try:
        print("\n=== SIC CODES REFERENCE ANALYSIS ===")
        df = pd.read_excel('data/SIC_codes.xlsx')
        
        print(f"SIC Reference Shape: {df.shape[0]} codes, {df.shape[1]} columns")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Clean up column names - take first column as SIC code, second as description
        df.columns = ['SIC_Code', 'Description']
        
        print(f"\n📋 SIC Code Structure:")
        print(f"   • Total SIC codes: {len(df)}")
        
        # Analyze code structure
        df['SIC_Code_Str'] = df['SIC_Code'].astype(str)
        df['Code_Length'] = df['SIC_Code_Str'].str.len()
        
        code_lengths = df['Code_Length'].value_counts().sort_index()
        print(f"   • Code length distribution:")
        for length, count in code_lengths.items():
            print(f"     - {length} digits: {count} codes")
        
        # Sample codes by length
        print(f"\n   📝 Sample codes by category:")
        for length in sorted(df['Code_Length'].unique()):
            sample_codes = df[df['Code_Length'] == length].head(3)
            print(f"     {length}-digit codes:")
            for _, row in sample_codes.iterrows():
                print(f"       {row['SIC_Code']}: {row['Description'][:60]}...")
        
        return df
        
    except Exception as e:
        print(f"Error analyzing SIC codes: {e}")
        return None

def cross_reference_analysis(sample_df, sic_df):
    """Cross-reference sample data with SIC codes"""
    if sample_df is None or sic_df is None:
        return
    
    print("\n=== CROSS REFERENCE ANALYSIS ===")
    
    # Clean SIC reference data - make a copy first
    sic_ref = sic_df.copy()
    sic_ref.columns = ['SIC_Code', 'Description']
    sic_ref['SIC_Code'] = sic_ref['SIC_Code'].astype(str).str.strip()
    
    # Get sample SIC codes
    sample_sics = set(sample_df['UK SIC 2007 Code'].astype(str).unique())
    reference_sics = set(sic_ref['SIC_Code'].unique())
    
    # Find matches and mismatches
    matched_codes = sample_sics.intersection(reference_sics)
    unmatched_codes = sample_sics - reference_sics
    
    print(f"🔍 SIC Code Validation:")
    print(f"   • Sample codes in reference: {len(matched_codes)}/{len(sample_sics)} ({len(matched_codes)/len(sample_sics)*100:.1f}%)")
    print(f"   • Unmatched codes: {len(unmatched_codes)}")
    
    if unmatched_codes:
        print(f"   ❌ Codes not found in reference:")
        for code in sorted(list(unmatched_codes))[:10]:  # Show first 10
            companies = sample_df[sample_df['UK SIC 2007 Code'].astype(str) == code]['Company Name'].tolist()
            print(f"      {code}: {len(companies)} companies (e.g., {companies[0] if companies else 'N/A'})")

def generate_mock_accuracy_data(sample_df):
    """Generate mock accuracy data for demonstration"""
    if sample_df is None:
        return None
    
    print("\n=== GENERATING MOCK ACCURACY DATA ===")
    
    # Create a copy for mock data
    mock_df = sample_df.copy()
    
    # Generate mock accuracy scores based on various factors
    np.random.seed(42)  # For consistent results
    
    # Base accuracy (most codes are correct)
    base_accuracy = np.random.normal(0.92, 0.15, len(mock_df))
    
    # Adjust accuracy based on business description length
    if 'Business Description' in mock_df.columns:
        desc_lengths = mock_df['Business Description'].fillna('').str.len()
        # Longer descriptions typically lead to better accuracy
        desc_factor = np.clip(desc_lengths / desc_lengths.max(), 0.5, 1.0)
        base_accuracy *= desc_factor
    
    # Adjust for company size (larger companies more likely to have correct codes)
    if 'Employees (Total)' in mock_df.columns:
        emp_factor = np.clip(mock_df['Employees (Total)'].fillna(0) / 1000, 0.7, 1.2)
        base_accuracy *= emp_factor
    
    # Ensure accuracy is between 0 and 1
    mock_df['SIC_Accuracy'] = np.clip(base_accuracy, 0.0, 1.0)
    
    # Generate prediction confidence (for future predict button)
    mock_df['Prediction_Confidence'] = np.random.normal(0.85, 0.1, len(mock_df))
    mock_df['Prediction_Confidence'] = np.clip(mock_df['Prediction_Confidence'], 0.0, 1.0)
    
    # Generate last update dates (for revenue update button)
    from datetime import datetime, timedelta
    base_date = datetime.now()
    days_ago = np.random.randint(30, 800, len(mock_df))  # 30 days to 2+ years ago
    mock_df['Last_Updated'] = [base_date - timedelta(days=int(d)) for d in days_ago]
    
    # Flag for data freshness (>365 days = needs update)
    mock_df['Needs_Revenue_Update'] = (datetime.now() - mock_df['Last_Updated']).dt.days > 365
    
    print(f"✅ Generated mock data for {len(mock_df)} companies")
    print(f"   • Average SIC accuracy: {mock_df['SIC_Accuracy'].mean():.3f}")
    print(f"   • Companies with <90% accuracy: {(mock_df['SIC_Accuracy'] < 0.9).sum()}")
    print(f"   • Companies needing revenue update: {mock_df['Needs_Revenue_Update'].sum()}")
    
    return mock_df

if __name__ == "__main__":
    print("🔍 CREDIT RISK DATA ANALYSIS")
    print("=" * 50)
    
    # Analyze both datasets
    sample_data = analyze_sample_data()
    sic_data = analyze_sic_codes()
    
    # Cross reference
    cross_reference_analysis(sample_data, sic_data)
    
    # Generate mock data for UI demo
    mock_data = generate_mock_accuracy_data(sample_data)
    
    if mock_data is not None:
        # Save enhanced data for UI
        mock_data.to_pickle('data/enhanced_sample_data.pkl')
        print(f"\n💾 Enhanced data saved to 'data/enhanced_sample_data.pkl'")
    
    print("\n" + "=" * 50)
    print("🎯 READY FOR UI DEVELOPMENT")
