"""
Migration: Add ch_sic_description column to sic_prediction_history table

This migration adds a new column to store the description of Companies House SIC codes
for the agentic SIC prediction system.
"""

import sqlite3
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def upgrade(db_path: str) -> Dict[str, Any]:
    """
    Add ch_sic_description column to sic_prediction_history table
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Dict containing migration results
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if column already exists
            cursor.execute("PRAGMA table_info(sic_prediction_history)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'ch_sic_description' not in columns:
                logger.info("Adding ch_sic_description column to sic_prediction_history table")
                
                # Add the new column
                cursor.execute("""
                    ALTER TABLE sic_prediction_history 
                    ADD COLUMN ch_sic_description TEXT
                """)
                
                logger.info("✅ Successfully added ch_sic_description column")
                return {
                    'success': True,
                    'message': 'Added ch_sic_description column to sic_prediction_history table',
                    'changes_made': ['Added ch_sic_description column']
                }
            else:
                logger.info("ch_sic_description column already exists, skipping migration")
                return {
                    'success': True,
                    'message': 'ch_sic_description column already exists',
                    'changes_made': []
                }
                
    except Exception as e:
        logger.error(f"Error in migration: {e}")
        return {
            'success': False,
            'message': f'Migration failed: {str(e)}',
            'changes_made': []
        }

def downgrade(db_path: str) -> Dict[str, Any]:
    """
    Remove ch_sic_description column from sic_prediction_history table
    
    Note: SQLite doesn't support DROP COLUMN directly, so this would require
    recreating the table. For simplicity, we'll just log this limitation.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Dict containing migration results
    """
    logger.warning("SQLite doesn't support DROP COLUMN. Manual table recreation required for downgrade.")
    return {
        'success': False,
        'message': 'SQLite downgrade not supported - manual intervention required',
        'changes_made': []
    }

if __name__ == "__main__":
    # For testing purposes
    import os
    
    # Test database path
    test_db_path = os.path.join(os.path.dirname(__file__), "../../../database.db")
    
    if os.path.exists(test_db_path):
        result = upgrade(test_db_path)
        print(f"Migration result: {result}")
    else:
        print("Database file not found for testing")