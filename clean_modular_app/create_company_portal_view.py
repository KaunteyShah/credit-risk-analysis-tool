#!/usr/bin/env python3
"""
Comprehensive Company Portal View Creator

Creates a unified view combining data from multiple tables for the credit risk portal:
- companies: Core company information
- company_financials: Financial data (sales_usd, employees_single_site)  
- company_sic_codes: SIC classification data (uk_sic_2007_code, uk_sic_2007_description)
- sic_prediction_history: AI prediction data (predicted_sic_code, confidence_score, existing_sic_confidence)

This view will be used for portal integration and provides a single point of access
to all relevant company data.
"""

import sqlite3
import os
from datetime import datetime

def create_company_portal_view():
    """
    Create or recreate the company_portal_view in the database.
    
    This view combines:
    - Companies: company_number, company_name, status, jurisdiction, business_description, ownership_type, entity_type, parent_company
    - Company Financials: sales_usd, employees_single_site
    - Company SIC Codes: uk_sic_2007_code, uk_sic_2007_description
    - SIC Prediction History: predicted_sic_code, confidence_score, existing_sic_confidence
    
    Returns:
        bool: True if successful, False otherwise
    """
    db_path = 'data/credit_risk.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Creating comprehensive company portal view...")
        
        # Drop existing view if it exists
        cursor.execute("DROP VIEW IF EXISTS company_portal_view")
        
        # Create the comprehensive view with LEFT JOINs to include all companies
        # even if they don't have financial data, SIC codes, or prediction history
        view_sql = """
        CREATE VIEW company_portal_view AS
        SELECT 
            -- Core company information
            c.id as company_id,
            c.company_number,
            c.company_name,
            c.status,
            c.jurisdiction,
            c.business_description,
            c.ownership_type,
            c.entity_type,
            c.parent_company,
            
            -- Financial information
            cf.sales_usd,
            cf.employees_single_site,
            
            -- SIC code information (from company_sic_codes table)
            csc.uk_sic_2007_code,
            csc.uk_sic_2007_description,
            
            -- AI prediction information (latest prediction for each company)
            sph.predicted_sic_code,
            sph.confidence_score,
            sph.existing_sic_confidence,
            sph.prediction_timestamp,
            sph.model_version,
            sph.prediction_method,
            
            -- Metadata
            c.created_at as company_created_at,
            c.updated_at as company_updated_at
            
        FROM companies c
        
        -- Left join with financial data (1:1 relationship)
        LEFT JOIN company_financials cf ON c.id = cf.company_id
        
        -- Left join with SIC codes (1:1 relationship, get primary SIC code)
        LEFT JOIN company_sic_codes csc ON c.id = csc.company_id AND csc.is_primary = 1
        
        -- Left join with prediction history (get most recent prediction for each company)
        LEFT JOIN (
            SELECT 
                company_id,
                predicted_sic_code,
                confidence_score,
                existing_sic_confidence,
                prediction_timestamp,
                model_version,
                prediction_method,
                ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
            FROM sic_prediction_history
            WHERE company_id IS NOT NULL
        ) sph ON c.id = sph.company_id AND sph.rn = 1
        
        -- Order by company name for consistent results
        ORDER BY c.company_name;
        """
        
        cursor.execute(view_sql)
        conn.commit()
        
        print("✅ Successfully created company_portal_view")
        
        # Verify the view was created and get sample data
        print("\n🔍 Verifying view creation...")
        cursor.execute("SELECT COUNT(*) FROM company_portal_view")
        total_records = cursor.fetchone()[0]
        print(f"✅ View contains {total_records} company records")
        
        # Show sample of available data
        cursor.execute("""
            SELECT 
                company_name,
                company_number,
                status,
                jurisdiction,
                CASE WHEN sales_usd IS NOT NULL THEN 'Yes' ELSE 'No' END as has_financial_data,
                CASE WHEN uk_sic_2007_code IS NOT NULL THEN 'Yes' ELSE 'No' END as has_sic_data,
                CASE WHEN predicted_sic_code IS NOT NULL THEN 'Yes' ELSE 'No' END as has_predictions
            FROM company_portal_view 
            LIMIT 5
        """)
        
        sample_data = cursor.fetchall()
        if sample_data:
            print("\n📊 Sample view data:")
            print("Company Name | Number | Status | Jurisdiction | Financials | SIC Codes | Predictions")
            print("-" * 90)
            for row in sample_data:
                print(f"{row[0][:20]:<20} | {str(row[1])[:8]:<8} | {row[2]:<8} | {row[3]:<12} | {row[4]:<10} | {row[5]:<9} | {row[6]}")
        
        # Show column information
        cursor.execute("PRAGMA table_info(company_portal_view)")
        columns = cursor.fetchall()
        print(f"\n📋 View contains {len(columns)} columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        print(f"\n🎉 Company portal view created successfully at {datetime.now()}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating view: {str(e)}")
        return False

def verify_view_data():
    """
    Verify the view data and show statistics about data availability.
    """
    db_path = 'data/credit_risk.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📈 Data Availability Statistics:")
        
        # Total records
        cursor.execute("SELECT COUNT(*) FROM company_portal_view")
        total = cursor.fetchone()[0]
        print(f"Total companies: {total}")
        
        # Financial data availability
        cursor.execute("SELECT COUNT(*) FROM company_portal_view WHERE sales_usd IS NOT NULL")
        with_financials = cursor.fetchone()[0]
        print(f"Companies with financial data: {with_financials} ({with_financials/total*100:.1f}%)")
        
        # SIC code availability
        cursor.execute("SELECT COUNT(*) FROM company_portal_view WHERE uk_sic_2007_code IS NOT NULL")
        with_sic = cursor.fetchone()[0]
        print(f"Companies with SIC codes: {with_sic} ({with_sic/total*100:.1f}%)")
        
        # Prediction data availability
        cursor.execute("SELECT COUNT(*) FROM company_portal_view WHERE predicted_sic_code IS NOT NULL")
        with_predictions = cursor.fetchone()[0]
        print(f"Companies with AI predictions: {with_predictions} ({with_predictions/total*100:.1f}%)")
        
        # Old accuracy data availability
        cursor.execute("SELECT COUNT(*) FROM company_portal_view WHERE old_accuracy IS NOT NULL")
        with_old_accuracy = cursor.fetchone()[0]
        print(f"Companies with old_accuracy: {with_old_accuracy} ({with_old_accuracy/total*100:.1f}%)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error verifying view data: {str(e)}")

def show_view_schema():
    """
    Display the complete schema of the company_portal_view.
    """
    db_path = 'data/credit_risk.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🏗️  Complete View Schema:")
        print("=" * 60)
        
        # Get the view creation SQL
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='company_portal_view'")
        view_sql = cursor.fetchone()
        if view_sql:
            print("VIEW DEFINITION:")
            print(view_sql[0])
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing view schema: {str(e)}")

def test_view_queries():
    """
    Test common queries that will be used in the portal.
    """
    db_path = 'data/credit_risk.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🧪 Testing common portal queries...")
        
        # Test 1: Companies with high sales
        cursor.execute("""
            SELECT company_name, sales_usd, jurisdiction
            FROM company_portal_view 
            WHERE sales_usd > 1000000 
            ORDER BY sales_usd DESC 
            LIMIT 3
        """)
        high_sales = cursor.fetchall()
        print(f"\n✅ Companies with sales > $1M: {len(high_sales)} found")
        
        # Test 2: Companies with predictions
        cursor.execute("""
            SELECT company_name, uk_sic_2007_code, predicted_sic_code, confidence_score
            FROM company_portal_view 
            WHERE predicted_sic_code IS NOT NULL 
            LIMIT 3
        """)
        with_predictions = cursor.fetchall()
        print(f"✅ Companies with AI predictions: {len(with_predictions)} found")
        
        # Test 3: Companies by jurisdiction
        cursor.execute("""
            SELECT jurisdiction, COUNT(*) as company_count
            FROM company_portal_view 
            WHERE jurisdiction IS NOT NULL
            GROUP BY jurisdiction 
            ORDER BY company_count DESC 
            LIMIT 5
        """)
        by_jurisdiction = cursor.fetchall()
        print(f"✅ Companies grouped by jurisdiction: {len(by_jurisdiction)} jurisdictions found")
        
        conn.close()
        print("✅ All test queries executed successfully")
        
    except Exception as e:
        print(f"❌ Error testing view queries: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Company Portal View Creation...")
    print("=" * 60)
    
    # Create the view
    success = create_company_portal_view()
    
    if success:
        # Verify the data
        verify_view_data()
        
        # Show schema
        show_view_schema()
        
        # Test queries
        test_view_queries()
        
        print("\n" + "=" * 60)
        print("🎉 Company Portal View Setup Complete!")
        print("The view 'company_portal_view' is ready for portal integration.")
        print("\nView includes all requested fields:")
        print("✅ Company: company_number, company_name, status, jurisdiction, business_description, ownership_type, entity_type, parent_company")
        print("✅ Financials: sales_usd, employees_single_site") 
        print("✅ SIC Codes: uk_sic_2007_code, uk_sic_2007_description")
        print("✅ Predictions: predicted_sic_code, confidence_score, existing_sic_confidence")
        print("✅ Additional: old_accuracy, prediction metadata")
    else:
        print("💥 View creation failed. Please check the error messages above.")