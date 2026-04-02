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
        """Get company data by index (row position) for SIC prediction with dual-key validation"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT company_id, unique_id, company_number, company_name, business_description, 
                           '' as phone, '' as email, '' as website, '' as address_line_1, '' as city, '' as post_code, '' as country,
                           uk_sic_2007_code, uk_sic_2007_description, existing_sic_confidence
                    FROM company_portal_view
                    ORDER BY company_id
                    LIMIT 1 OFFSET ?
                """, (company_index,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],  # company_id from view
                        'unique_id': row[1],  # unique_id from view - CRITICAL for dual-key validation
                        'company_number': row[2], 
                        'company_name': row[3],  # Database field name
                        'business_description': row[4],  # Database field name
                        'uk_sic_2007_code': row[12] or '',  # From company_portal_view
                        'confidence': row[14] or 0.0,  # existing_sic_confidence from view
                        'phone': row[5],
                        'email': row[6], 
                        'website': row[7],
                        'address_line_1': row[8],
                        'city': row[9],
                        'post_code': row[10],
                        'country': row[11],
                        'existing_sic_code': row[12] or '',  # Same as uk_sic_2007_code
                        'existing_sic_description': row[13] or '',  # uk_sic_2007_description from view
                        'existing_sic_confidence': row[14] or 0.0  # existing_sic_confidence from view
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
                
                # Base query with dual-key support and existing SIC code from company_sic_codes + confidence from prediction history
                query = """
                    SELECT c.id, c.unique_id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city, c.post_code, c.country,
                           csc.uk_sic_2007_code, csc.uk_sic_2007_description,
                           sph.existing_sic_confidence
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id AND csc.is_primary = 1
                    LEFT JOIN (
                        SELECT company_id, existing_sic_confidence,
                               ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
                        FROM sic_prediction_history
                        WHERE existing_sic_confidence IS NOT NULL
                    ) sph ON c.id = sph.company_id AND sph.rn = 1
                    WHERE LOWER(c.company_name) LIKE LOWER(?)
                    LIMIT 1
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
                        'unique_id': row[1],  # DUAL-KEY: unique business identifier
                        'company_number': row[2],
                        'Company Name': row[3],  # Service expects this format (capitalized)
                        'Business Description': row[4],  # Service expects this format (capitalized)
                        'SIC Code (SIC 2007)': row[12] or '',  # Existing SIC code from company_sic_codes table
                        'Old_Accuracy': row[14] or 0.0,  # existing_sic_confidence from sic_prediction_history
                        'phone': row[5],
                        'email': row[6],
                        'website': row[7], 
                        'address_line_1': row[8],
                        'city': row[9],
                        'post_code': row[10],
                        'country': row[11],
                        'existing_sic_code': row[12] or '',  # Existing SIC code for database updates
                        'existing_sic_description': row[13] or '',  # uk_sic_2007_description from company_sic_codes table
                        'existing_sic_confidence': row[14] or 0.0  # existing_sic_confidence from sic_prediction_history
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting company by name {company_name}: {e}")
            return None
    
    def get_company_by_unique_id(self, unique_id: str) -> Optional[Dict[str, Any]]:
        """Get company data by unique_id - ROBUST: handles both unique_id and company_id for exact company lookup"""
        return self._get_company_by_identifier(unique_id)
    
    def get_company_by_company_id(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company data by company_id - ROBUST: handles both company_id and unique_id for exact company lookup"""
        return self._get_company_by_identifier(str(company_id))
    
    def _get_company_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Internal method for robust company lookup using both unique_id and company_id"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # ROBUST LOOKUP: Try both unique_id (string) and company_id (integer) to find exact company
                # Join three tables: companies + company_sic_codes (existing) + sic_prediction_history (predictions)
                query = """
                    SELECT 
                        c.id, c.company_number, c.company_name, c.business_description,
                        c.phone, c.email, c.website, c.address_line_1, c.city, c.post_code, c.country,
                        csc.uk_sic_2007_code, csc.uk_sic_2007_description, c.unique_id,
                        COALESCE(sph.existing_sic_confidence, 0.0) as existing_sic_confidence
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id AND csc.is_primary = 1
                    LEFT JOIN (
                        SELECT company_id, existing_sic_confidence,
                               ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY prediction_timestamp DESC) as rn
                        FROM sic_prediction_history
                        WHERE existing_sic_confidence IS NOT NULL
                    ) sph ON c.id = sph.company_id AND sph.rn = 1
                    WHERE c.unique_id = ? OR c.id = ?
                    LIMIT 1
                """
                
                # Try both unique_id (as string) and as integer (company_id via row ID alias)
                try:
                    company_id_int = int(identifier)
                except (ValueError, TypeError):
                    company_id_int = None
                
                cursor.execute(query, (identifier, company_id_int))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'company_number': row[1],
                        'company_name': row[2],  # Database field name
                        'business_description': row[3],  # Database field name
                        'uk_sic_2007_code': row[11] or '',  # Existing SIC code from company_sic_codes table
                        'confidence': row[14] or 0.0,  # Use existing_sic_confidence from prediction history
                        'phone': row[4],
                        'email': row[5],
                        'website': row[6], 
                        'address_line_1': row[7],
                        'city': row[8],
                        'post_code': row[9],
                        'country': row[10],
                        'existing_sic_code': row[11] or '',  # Existing SIC code for database updates
                        'existing_sic_description': row[12] or '',  # uk_sic_2007_description from company_sic_codes table
                        'unique_id': row[13] or '',  # unique_id from companies table
                        'existing_sic_confidence': row[14] or 0.0  # Add existing_sic_confidence field
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting company by identifier {identifier}: {e}")
            return None
    
    def update_company_prediction(self, unique_id: str, company_name: str, business_description: str,
                                predicted_sic_code: str, predicted_sic_description: str, 
                                confidence_score: float, existing_sic_code: str = None,
                                existing_sic_description: str = None, existing_sic_confidence: float = None,
                                model_version: str = "1.0", prediction_method: str = "AI",
                                ai_reasoning: str = None, ch_sic_codes: str = None,
                                ch_sic_description: str = None, created_by: str = "system", **kwargs) -> bool:
        """Update company with SIC prediction results and save to history using unique_id"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # 🔑 UNIQUE_ID LOOKUP: Get company data by unique_id (not row position)
                cursor.execute("""
                    SELECT id, company_name, business_description, unique_id
                    FROM companies 
                    WHERE unique_id = ?
                """, (unique_id,))
                
                company_data = cursor.fetchone()
                if not company_data:
                    logger.error(f"Company with unique_id '{unique_id}' not found")
                    return False
                
                company_id, company_name, business_description, fetched_unique_id = company_data
                
                # 🔍 DEBUG: Log business_description content
                logger.info(f"🔍 DEBUG: business_description = '{business_description}' (length: {len(business_description) if business_description else 0})")
                
                # DUAL-KEY VALIDATION: Verify both IDs exist and match
                if not company_id or not fetched_unique_id or fetched_unique_id != unique_id:
                    logger.error(f"❌ DUAL-KEY VALIDATION FAILED: company_id={company_id}, unique_id='{unique_id}' for company {company_name}")
                    return False
                
                logger.info(f"✅ DUAL-KEY VALIDATION: company_id={company_id}, unique_id='{unique_id}' for {company_name}")
                
                # Use provided sic description or get from database
                if not predicted_sic_description:
                    cursor.execute("""
                        SELECT sic_description 
                        FROM sic_codes 
                        WHERE sic_code = ?
                    """, (predicted_sic_code,))
                
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
                logger.info(f"DEBUG: predicted_sic={predicted_sic_code}, confidence={confidence_score}")
                
                # DUAL-KEY VALIDATION: Check if a prediction record already exists using both keys
                # 🔒 UPSERT APPROACH: Update existing record or insert new one - NO DUPLICATES
                # First, try to update existing record with dual-key filter
                logger.info(f"� DUAL-KEY UPSERT: Checking for existing prediction (company_id={company_id}, unique_id='{unique_id}')")
                
                # 🔧 FIX: Preserve existing CH codes when new values are empty
                # First get existing CH codes before update
                cursor.execute("SELECT ch_sic_codes, ch_sic_description FROM sic_prediction_history WHERE unique_id = ?", (unique_id,))
                existing_ch_result = cursor.fetchone()
                existing_ch_codes, existing_ch_description = existing_ch_result if existing_ch_result else (None, None)
                
                logger.info(f"🔧 CH DEBUG: incoming ch_sic_codes='{ch_sic_codes}' (type={type(ch_sic_codes)}), ch_sic_description='{ch_sic_description}' (type={type(ch_sic_description)})")
                logger.info(f"🔧 CH DEBUG: existing ch_codes='{existing_ch_codes}', ch_description='{existing_ch_description}'")
                
                # Use new CH codes if provided, otherwise preserve existing ones
                final_ch_codes = ch_sic_codes if ch_sic_codes and ch_sic_codes.strip() else existing_ch_codes
                final_ch_description = ch_sic_description if ch_sic_description and ch_sic_description.strip() else existing_ch_description
                
                logger.info(f"🔧 CH PRESERVATION: existing=({existing_ch_codes}, {existing_ch_description}) -> final=({final_ch_codes}, {final_ch_description})")
                
                # Try UPDATE first
                cursor.execute("""
                    UPDATE sic_prediction_history 
                    SET 
                        business_description = ?,
                        predicted_sic_code = ?,
                        predicted_sic_description = ?,
                        confidence_score = ?,
                        existing_sic_code = ?,
                        existing_sic_description = ?,
                        existing_sic_confidence = ?,
                        model_version = ?,
                        prediction_method = ?,
                        ai_reasoning = ?,
                        ch_sic_codes = ?,
                        ch_sic_description = ?,
                        created_by = ?,
                        prediction_timestamp = CURRENT_TIMESTAMP
                    WHERE unique_id = ?
                """, (
                    business_description, predicted_sic_code, predicted_sic_description, 
                    confidence_score, existing_sic_code, existing_sic_description,
                    existing_sic_confidence, model_version, prediction_method, ai_reasoning,
                    final_ch_codes, final_ch_description, created_by, unique_id
                ))
                
                # 🔧 FIX: Check if UPDATE affected any rows - if not, INSERT new record
                if cursor.rowcount == 0:
                    # No existing record found, INSERT new record
                    logger.info(f"📝 No existing record found, inserting new prediction for {company_name}")
                    cursor.execute("""
                        INSERT INTO sic_prediction_history (
                            company_id, company_name, unique_id, business_description,
                            predicted_sic_code, predicted_sic_description, confidence_score,
                            existing_sic_code, existing_sic_description, existing_sic_confidence,
                            model_version, prediction_method, ai_reasoning,
                            ch_sic_codes, ch_sic_description, created_by, prediction_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        company_id, company_name, unique_id, business_description,
                        predicted_sic_code, predicted_sic_description, confidence_score,
                        existing_sic_code, existing_sic_description, existing_sic_confidence,
                        model_version, prediction_method, ai_reasoning,
                        ch_sic_codes, ch_sic_description, created_by
                    ))
                    logger.info(f"✅ INSERTED new prediction record for {company_name}")
                else:
                    logger.info(f"✅ UPDATED existing prediction record for {company_name}")
                
                logger.info(f"✅ DUAL-KEY UPSERT: Successfully processed prediction for company {company_name} (ID: {company_id}, unique_id: '{unique_id}') - NO DUPLICATES GUARANTEED")
                
                # Note: Real-time CH SIC retrieval has been removed for simplicity
                # CH SIC codes are populated during agentic prediction phase
                # Approval process simply preserves existing CH codes via schema preservation
                
                conn.commit()
                logger.info(f"Successfully updated prediction for company {company_name} (unique_id: {unique_id}, id: {company_id})")
                return True
                
        except Exception as e:
            logger.error(f"Error updating company prediction for unique_id '{unique_id}': {e}")
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