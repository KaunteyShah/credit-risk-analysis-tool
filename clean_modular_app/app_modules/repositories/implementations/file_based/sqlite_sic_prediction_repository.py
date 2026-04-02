"""
SQLite-based repository imple                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'company_number': row[1], 
                        'Company Name': row[2],  # Service expects this format
                        'Business Description': row[3],  # Service expects this format
                        'SIC Code (SIC 2007)': row[11] or '',  # Existing SIC code from company_sic_codes table
                        'Old_Accuracy': 0.0,  # Service expects this field (but we don't use it)
                        'phone': row[4],
                        'email': row[5], 
                        'website': row[6],
                        'address_line_1': row[7],
                        'city': row[8],
                        'post_code': row[9],
                        'country': row[10],
                        'existing_sic_code': row[11] or '',  # Existing SIC code for database updates
                        'existing_sic_description': row[12] or ''  # uk_sic_2007_description from company_sic_codes table prediction operations
"""
from typing import Dict, Any, Optional
import sqlite3
import logging
from app_modules.repositories.interfaces.sic_prediction_repository_interface import SICPredictionRepositoryInterface
from app_modules.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SQLiteSICPredictionRepository(SICPredictionRepositoryInterface):
    """SQLite implementation of SIC prediction repository"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        
    def get_company_by_index(self, company_index: int) -> Optional[Dict[str, Any]]:
        """Get company data by index (row position) for SIC prediction"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.id, c.company_number, c.company_name, c.business_description, 
                           c.phone, c.email, c.website, c.address_line_1, c.city, c.post_code, c.country,
                           csc.uk_sic_2007_code, csc.uk_sic_2007_description
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    ORDER BY c.id
                    LIMIT 1 OFFSET ?
                """, (company_index,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'company_number': row[1], 
                        'Company Name': row[2],  # Service expects this format
                        'Business Description': row[3],  # Service expects this format
                        'SIC Code (SIC 2007)': row[11] or '',  # Existing SIC code from company_sic_codes table
                        'Old_Accuracy': 0.0,  # Service expects this field (but we don't use it)
                        'phone': row[4],
                        'email': row[5], 
                        'website': row[6],
                        'address_line_1': row[7],
                        'city': row[8],
                        'post_code': row[9],
                        'country': row[10],
                        'existing_sic_code': row[11] or '',  # Existing SIC code for database updates
                        'existing_sic_description': row[12] or ''  # Existing SIC description for database updates
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting company by index {company_index}: {e}")
            return None
    
    def get_company_by_name(self, company_name: str, 
                           registration_number: Optional[str] = None,
                           sic_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get company data by name for SIC prediction"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Base query with existing SIC code
                query = """
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city, c.post_code, c.country,
                           csc.uk_sic_2007_code, csc.uk_sic_2007_description
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE c.company_name LIKE ?
                """
                params = [f"%{company_name}%"]
                
                # Add additional filters if provided
                if registration_number:
                    query += " AND c.company_number = ?"
                    params.append(registration_number)
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'company_number': row[1],
                        'Company Name': row[2],  # Service expects this format
                        'Business Description': row[3],  # Service expects this format
                        'SIC Code (SIC 2007)': row[11] or '',  # Existing SIC code from company_sic_codes table
                        'Old_Accuracy': 0.0,  # Service expects this field (but we don't use it)
                        'phone': row[4],
                        'email': row[5],
                        'website': row[6], 
                        'address_line_1': row[7],
                        'city': row[8],
                        'post_code': row[9],
                        'country': row[10],
                        'existing_sic_code': row[11] or '',  # Existing SIC code for database updates
                        'existing_sic_description': row[12] or ''  # uk_sic_2007_description from company_sic_codes table
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting company by name {company_name}: {e}")
            return None
    
    def update_company_prediction(self, company_index: int, predicted_sic: str, 
                                confidence: float, new_accuracy: float) -> bool:
        """Update company with SIC prediction results and save to history"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # First get the company data by index (row position)
                cursor.execute("""
                    SELECT id, company_name, business_description 
                    FROM companies 
                    ORDER BY id
                    LIMIT 1 OFFSET ?
                """, (company_index,))
                
                company_data = cursor.fetchone()
                if not company_data:
                    logger.error(f"Company with index {company_index} not found")
                    return False
                
                company_id, company_name, business_description = company_data
                
                # Get SIC description
                cursor.execute("""
                    SELECT sic_description 
                    FROM sic_codes 
                    WHERE sic_code = ?
                """, (predicted_sic,))
                
                sic_data = cursor.fetchone()
                sic_description = sic_data[0] if sic_data else "Unknown"
                
                # Get existing SIC code from company_sic_codes table
                cursor.execute("""
                    SELECT uk_sic_2007_code, uk_sic_2007_description 
                    FROM company_sic_codes 
                    WHERE company_id = ?
                """, (company_id,))
                
                existing_sic_data = cursor.fetchone()
                existing_sic_code = existing_sic_data[0] if existing_sic_data else None
                existing_sic_description = existing_sic_data[1] if existing_sic_data else None
                
                # Debug logging for existing SIC data
                logger.info(f"DEBUG: existing_sic_code={existing_sic_code}, existing_sic_description={existing_sic_description}")
                logger.info(f"DEBUG: company_id={company_id}, company_name={company_name}")
                logger.info(f"DEBUG: predicted_sic={predicted_sic}, confidence={confidence}")
                
                # Insert into prediction history with existing SIC data
                cursor.execute("""
                    INSERT INTO sic_prediction_history 
                    (company_id, company_name, business_description, predicted_sic_code, 
                     predicted_sic_description, confidence_score, existing_sic_code,
                     existing_sic_description, model_version, prediction_method, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id, company_name, business_description, predicted_sic,
                    sic_description, confidence, existing_sic_code, existing_sic_description,
                    '1.0', 'AI', 'user_approval'
                ))
                
                # Note: We no longer update the companies table with accuracy/confidence values
                # We also don't store new_accuracy as it was a CSV-file concept
                # All prediction data is stored in sic_prediction_history table only
                
                conn.commit()
                logger.info(f"Successfully updated prediction for company {company_name} (index: {company_index}, id: {company_id})")
                return True
                
        except Exception as e:
            logger.error(f"Error updating company prediction for {company_index}: {e}")
            return False
    
    def get_companies_count(self) -> int:
        """Get total count of companies"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM companies")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting companies count: {e}")
            return 0
    
    def load_company_data(self) -> bool:
        """Load company data if not already loaded"""
        try:
            # For SQLite, the data is already loaded in the database
            # Just verify the connection is working
            count = self.get_companies_count()
            logger.info(f"SQLite database loaded with {count} companies")
            return count > 0
        except Exception as e:
            logger.error(f"Error loading company data: {e}")
            return False
            return 0