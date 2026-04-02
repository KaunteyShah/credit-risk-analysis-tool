#!/usr/bin/env python3
"""
Database Migration Script for Azure Deployment

This script ensures the deployed database has the correct schema,
specifically adding the unique_id column that might be missing.
"""

import sqlite3
import os
import sys
import logging
from typing import Dict, Any

# Setup basic logging
logger = logging.getLogger(__name__)

def check_column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return any(col[1] == column_name for col in columns)
    except Exception as e:
        logger.error(f"Error checking column {column_name} in table {table_name}: {e}")
        return False

def add_unique_id_column(cursor: sqlite3.Cursor) -> bool:
    """Add unique_id column to companies table if it doesn't exist"""
    try:
        if not check_column_exists(cursor, 'companies', 'unique_id'):
            logger.info("Adding unique_id column to companies table...")
            
            # Add the column
            cursor.execute("ALTER TABLE companies ADD COLUMN unique_id TEXT")
            
            # Generate unique IDs for existing companies
            cursor.execute("SELECT id, company_number, company_name FROM companies WHERE unique_id IS NULL")
            companies = cursor.fetchall()
            
            for company_id, company_number, company_name in companies:
                # Generate a unique ID similar to the pattern in your data
                if company_number:
                    # Use company number if available
                    unique_id = f"{company_number[:2]}{str(company_id).zfill(8)}"
                else:
                    # Generate from company name if no number
                    name_prefix = ''.join(c.upper() for c in company_name[:2] if c.isalpha()) or 'XX'
                    unique_id = f"{name_prefix}{str(company_id).zfill(8)}"
                
                cursor.execute("UPDATE companies SET unique_id = ? WHERE id = ?", (unique_id, company_id))
            
            # Create index for better performance
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_unique_id ON companies(unique_id)")
            
            logger.info(f"✅ Added unique_id column and populated {len(companies)} records")
            return True
        else:
            logger.info("✅ unique_id column already exists")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error adding unique_id column: {e}")
        return False

def recreate_company_portal_view(cursor: sqlite3.Cursor) -> bool:
    """Recreate the company_portal_view to ensure it includes unique_id"""
    try:
        # Drop existing view
        cursor.execute("DROP VIEW IF EXISTS company_portal_view")
        
        # Recreate view with unique_id
        view_sql = """
        CREATE VIEW company_portal_view AS
        SELECT 
            -- Core company information (added unique_id)
            c.id as company_id,
            c.unique_id,
            c.company_number,
            c.company_name,
            c.status,
            c.jurisdiction,
            c.business_description,
            c.ownership_type,
            c.entity_type,
            c.parent_company,
            
            -- Financial information
            cf.sales_gbp,
            cf.employees_single_site,
            
            -- SIC code information (from company_sic_codes table)
            csc.uk_sic_2007_code,
            csc.uk_sic_2007_description,
            
            -- AI prediction information (latest prediction for each company)
            sph.predicted_sic_code,
            sph.confidence_score,
            sph.existing_sic_confidence,
            sph.ch_sic_codes,
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
                ch_sic_codes,
                prediction_timestamp,
                model_version,
                prediction_method,
                ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
            FROM sic_prediction_history
            WHERE company_id IS NOT NULL
        ) sph ON c.id = sph.company_id AND sph.rn = 1

        -- Order by company name for consistent results
        ORDER BY c.company_name
        """
        
        cursor.execute(view_sql)
        logger.info("✅ Recreated company_portal_view with unique_id")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error recreating company_portal_view: {e}")
        return False

def migrate_database(db_path: str) -> Dict[str, Any]:
    """Run database migration to ensure correct schema"""
    try:
        if not os.path.exists(db_path):
            return {
                'success': False,
                'error': f'Database file not found: {db_path}'
            }
        
        logger.info(f"🔄 Running database migration on: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        has_unique_id = check_column_exists(cursor, 'companies', 'unique_id')
        logger.info(f"Current schema - unique_id column exists: {has_unique_id}")
        
        migrations_needed = []
        
        # Add unique_id column if missing
        if not has_unique_id:
            migrations_needed.append('add_unique_id_column')
        
        # Always recreate the view to ensure it's correct
        migrations_needed.append('recreate_company_portal_view')
        
        # Run migrations
        for migration in migrations_needed:
            logger.info(f"Running migration: {migration}")
            
            if migration == 'add_unique_id_column':
                if not add_unique_id_column(cursor):
                    conn.rollback()
                    conn.close()
                    return {
                        'success': False,
                        'error': f'Failed to run migration: {migration}'
                    }
            
            elif migration == 'recreate_company_portal_view':
                if not recreate_company_portal_view(cursor):
                    conn.rollback()
                    conn.close()
                    return {
                        'success': False,
                        'error': f'Failed to run migration: {migration}'
                    }
        
        # Commit changes
        conn.commit()
        
        # Test the migration
        try:
            cursor.execute("SELECT unique_id FROM company_portal_view LIMIT 1")
            test_result = cursor.fetchone()
            if test_result:
                logger.info("✅ Migration test passed - company_portal_view with unique_id works")
            else:
                logger.warning("⚠️ Migration test: No data returned from company_portal_view")
        except Exception as test_error:
            conn.close()
            return {
                'success': False,
                'error': f'Migration test failed: {test_error}'
            }
        
        conn.close()
        
        logger.info("✅ Database migration completed successfully")
        return {
            'success': True,
            'migrations_run': migrations_needed,
            'message': f'Successfully ran {len(migrations_needed)} migrations'
        }
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Use the database path from command line or default
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/credit_risk.db'
    
    result = migrate_database(db_path)
    
    if result['success']:
        print(f"✅ {result['message']}")
        sys.exit(0)
    else:
        print(f"❌ Migration failed: {result['error']}")
        sys.exit(1)