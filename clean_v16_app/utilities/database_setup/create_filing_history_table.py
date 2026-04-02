#!/usr/bin/env python3
"""
Database table creation script for company_filing_history_accounts
Creates the new table for storing Companies House filing history data

This script creates a NEW table and does NOT modify existing tables or workflows.
"""

import sqlite3
import os
from datetime import datetime
from app_modules.utils.logger import get_logger

logger = get_logger(__name__)

def create_filing_history_table():
    """
    Create the company_filing_history_accounts table for storing Companies House filing data
    
    Table Design:
    - Stores historical filing data (append-only)
    - Links to companies table via unique_id (foreign key)
    - Stores complete JSON structure from Companies House API
    - Supports time-series analysis with timestamp grouping
    """
    
    # Database path - use same path as DatabaseConnection class
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'credit_risk.db')
    
    # Table schema based on Companies House JSON structure + business fields
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS company_filing_history_accounts (
        -- Primary key
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Business identification fields (links to companies table)
        unique_id TEXT NOT NULL,  -- Foreign key to companies.unique_id
        company_registration_number TEXT NOT NULL,  -- Company number from Companies House
        company_name TEXT NOT NULL,  -- Company name at time of filing
        company_address TEXT,  -- Company address at time of filing
        
        -- Companies House API JSON fields (from filing history response)
        transaction_id TEXT,  -- Unique filing transaction ID
        barcode TEXT,  -- Document barcode
        type TEXT,  -- Filing type code (e.g., "AA" for Annual Accounts)
        filing_date TEXT,  -- Date when filing was submitted (YYYY-MM-DD)
        category TEXT,  -- Filing category ("accounts" or "annual-return")
        description TEXT,  -- Human-readable filing description
        made_up_date TEXT,  -- Financial year end date (from description_values)
        pages INTEGER,  -- Number of pages in the document
        action_date TEXT,  -- Date when accounts were made up (YYYY-MM-DD)
        paper_filed BOOLEAN,  -- Whether filed on paper (true/false)
        
        -- Document access links
        document_link TEXT,  -- URL to download the actual document
        api_link TEXT,  -- Companies House API self-link
        
        -- Metadata
        data_ingestion_timestamp DATETIME NOT NULL,  -- When this record was created
        api_response_raw TEXT,  -- Complete JSON response (for debugging)
        
        -- Indexes for performance
        FOREIGN KEY (unique_id) REFERENCES companies(unique_id),
        
        -- Ensure we don't duplicate the same filing for the same company
        UNIQUE(unique_id, transaction_id)
    );
    """
    
    # Create indexes for performance
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_filing_history_unique_id ON company_filing_history_accounts(unique_id);",
        "CREATE INDEX IF NOT EXISTS idx_filing_history_timestamp ON company_filing_history_accounts(data_ingestion_timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_filing_history_filing_date ON company_filing_history_accounts(filing_date);",
        "CREATE INDEX IF NOT EXISTS idx_filing_history_category ON company_filing_history_accounts(category);",
        "CREATE INDEX IF NOT EXISTS idx_filing_history_latest ON company_filing_history_accounts(unique_id, data_ingestion_timestamp DESC);"
    ]
    
    try:
        print("=" * 80)
        print("📊 CREATING COMPANY FILING HISTORY TABLE")
        print("=" * 80)
        print(f"Database: {db_path}")
        print("Table: company_filing_history_accounts")
        print()
        
        # Connect to database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create the main table
            print("🏗️  Creating table schema...")
            cursor.execute(create_table_sql)
            
            # Create indexes
            print("📈 Creating performance indexes...")
            for idx_sql in create_indexes_sql:
                cursor.execute(idx_sql)
            
            conn.commit()
            
            # Verify table creation
            cursor.execute("PRAGMA table_info(company_filing_history_accounts);")
            columns = cursor.fetchall()
            
            print("✅ Table created successfully!")
            print(f"   Columns: {len(columns)}")
            print()
            
            print("📋 Table Schema:")
            print("-" * 60)
            for col in columns:
                col_id, name, data_type, not_null, default, pk = col
                pk_marker = " (PK)" if pk else ""
                not_null_marker = " NOT NULL" if not_null else ""
                print(f"   {name:<25} {data_type:<10} {not_null_marker}{pk_marker}")
            
            print()
            
            # Check indexes
            cursor.execute("PRAGMA index_list(company_filing_history_accounts);")
            indexes = cursor.fetchall()
            
            print("🔍 Indexes Created:")
            print("-" * 40)
            for idx in indexes:
                print(f"   • {idx[1]}")  # idx[1] is the index name
            
            print()
            print("🎯 Table Purpose:")
            print("-" * 30)
            print("   • Store Companies House filing history (accounts & annual returns)")
            print("   • Link to companies table via unique_id")
            print("   • Support historical data analysis")
            print("   • Enable latest filing queries with timestamp grouping")
            print("   • Integrate with data_ingestion_agent workflow")
            print()
            
            print("✅ Database table creation completed successfully!")
            
    except Exception as e:
        logger.error(f"Error creating filing history table: {e}")
        print(f"❌ Error: {e}")
        raise

def verify_table_structure():
    """Verify the table was created correctly and show usage examples"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'credit_risk.db')
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            print("=" * 80)
            print("🔍 TABLE VERIFICATION & USAGE EXAMPLES")
            print("=" * 80)
            
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='company_filing_history_accounts';
            """)
            
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("✅ Table exists: company_filing_history_accounts")
                
                # Show sample queries for future use
                print()
                print("📖 SAMPLE QUERIES FOR INTEGRATION:")
                print("-" * 50)
                
                print("1️⃣  Insert new filing record:")
                print("""
INSERT INTO company_filing_history_accounts (
    unique_id, company_registration_number, company_name, company_address,
    transaction_id, barcode, type, filing_date, category, description,
    made_up_date, pages, action_date, paper_filed, document_link, api_link,
    data_ingestion_timestamp, api_response_raw
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
""")
                
                print("2️⃣  Get latest filing for a company:")
                print("""
SELECT * FROM company_filing_history_accounts 
WHERE unique_id = ? 
ORDER BY data_ingestion_timestamp DESC 
LIMIT 1;
""")
                
                print("3️⃣  Get latest filings for company portal view:")
                print("""
SELECT 
    cfha.unique_id,
    cfha.filing_date,
    cfha.category,
    cfha.description,
    cfha.document_link
FROM company_filing_history_accounts cfha
INNER JOIN (
    SELECT unique_id, MAX(data_ingestion_timestamp) as latest_timestamp
    FROM company_filing_history_accounts
    GROUP BY unique_id
) latest ON cfha.unique_id = latest.unique_id 
         AND cfha.data_ingestion_timestamp = latest.latest_timestamp;
""")
                
                print("4️⃣  JOIN with companies table:")
                print("""
SELECT 
    c.company_name,
    c.company_number,
    cfha.filing_date,
    cfha.category,
    cfha.document_link
FROM companies c
LEFT JOIN (
    SELECT * FROM company_filing_history_accounts cfha1
    WHERE cfha1.data_ingestion_timestamp = (
        SELECT MAX(cfha2.data_ingestion_timestamp)
        FROM company_filing_history_accounts cfha2
        WHERE cfha2.unique_id = cfha1.unique_id
    )
) cfha ON c.unique_id = cfha.unique_id;
""")
                
                print()
                print("✅ Table verification completed!")
                
            else:
                print("❌ Table does not exist!")
                
    except Exception as e:
        logger.error(f"Error verifying table: {e}")
        print(f"❌ Verification error: {e}")

if __name__ == "__main__":
    # Create the table
    create_filing_history_table()
    
    # Verify it was created correctly
    verify_table_structure()
    
    print()
    print("🚀 NEXT STEPS:")
    print("=" * 30)
    print("1. ✅ Database table created")
    print("2. ⏳ Create database operations (insert/update functions)")
    print("3. ⏳ Integrate with data_ingestion_agent")
    print("4. ⏳ Update company_portal_view (with permission)")
    print("5. ⏳ Add filing data to UI modal (with permission)")