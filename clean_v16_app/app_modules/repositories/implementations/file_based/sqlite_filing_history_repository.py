"""
SQLite-based repository implementation for Companies House filing history operations
"""
from typing import Dict, Any, Optional, List
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from app_modules.repositories.interfaces.filing_history_repository_interface import FilingHistoryRepositoryInterface
from app_modules.database.connection import DatabaseConnection
from app_modules.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteFilingHistoryRepository(FilingHistoryRepositoryInterface):
    """SQLite implementation of filing history repository"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        
    def insert_filing_record(self, filing_data: Dict[str, Any]) -> bool:
        """
        Insert a new filing history record
        
        Args:
            filing_data: Complete filing information including API response
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Extract data from the filing_data structure
                unique_id = filing_data.get('unique_id')
                company_registration_number = filing_data.get('company_registration_number')
                company_name = filing_data.get('company_name')
                company_address = filing_data.get('company_address', '')
                
                # Extract filing details from Companies House API response
                filing_details = filing_data.get('filing_details', {})
                
                # Extract document ID from document metadata URL
                document_metadata_url = filing_details.get('links', {}).get('document_metadata')
                document_id = None
                if document_metadata_url:
                    import re
                    # Extract document ID from URL like: https://document-api.company-information.service.gov.uk/document/ABC123
                    match = re.search(r'/document/([^/]+)$', document_metadata_url)
                    if match:
                        document_id = match.group(1)
                
                insert_sql = """
                INSERT INTO company_filing_history_accounts (
                    unique_id, company_registration_number, company_name, company_address,
                    transaction_id, barcode, type, filing_date, category, description,
                    made_up_date, pages, action_date, paper_filed, document_link, api_link,
                    data_ingestion_timestamp, api_response_raw, document_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                # Prepare values for insertion
                values = (
                    unique_id,
                    company_registration_number,
                    company_name,
                    company_address,
                    filing_details.get('transaction_id'),
                    filing_details.get('barcode'),
                    filing_details.get('type'),
                    filing_details.get('date'),  # filing_date
                    filing_details.get('category'),
                    filing_details.get('description'),
                    filing_details.get('description_values', {}).get('made_up_date'),
                    filing_details.get('pages'),
                    filing_details.get('action_date'),
                    filing_details.get('paper_filed'),
                    document_metadata_url,  # still store the full URL for reference
                    filing_details.get('links', {}).get('self'),
                    datetime.now().isoformat(),
                    json.dumps(filing_data.get('raw_api_response', {})),
                    document_id  # extracted document ID
                )
                
                cursor.execute(insert_sql, values)
                conn.commit()
                
                logger.info(f"✅ Inserted filing record for company {unique_id}: {filing_details.get('transaction_id')}")
                return True
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Filing record already exists for {unique_id}: {filing_details.get('transaction_id')}")
            else:
                logger.error(f"Integrity error inserting filing record: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inserting filing record: {e}")
            return False
    
    def get_latest_filing_by_unique_id(self, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent filing record for a company by unique_id
        
        Args:
            unique_id: Company unique identifier
            
        Returns:
            Latest filing record or None
        """
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    id, unique_id, company_registration_number, company_name, company_address,
                    transaction_id, barcode, type, filing_date, category, description,
                    made_up_date, pages, action_date, paper_filed, document_link, api_link,
                    data_ingestion_timestamp, api_response_raw
                FROM company_filing_history_accounts
                WHERE unique_id = ?
                ORDER BY data_ingestion_timestamp DESC
                LIMIT 1
                """
                
                cursor.execute(query, (unique_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest filing for {unique_id}: {e}")
            return None
    
    def get_filing_history_by_unique_id(self, unique_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get filing history for a company by unique_id
        
        Args:
            unique_id: Company unique identifier
            limit: Maximum number of records to return
            
        Returns:
            List of filing records (most recent first)
        """
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    id, unique_id, company_registration_number, company_name, company_address,
                    transaction_id, barcode, type, filing_date, category, description,
                    made_up_date, pages, action_date, paper_filed, document_link, api_link,
                    data_ingestion_timestamp, api_response_raw
                FROM company_filing_history_accounts
                WHERE unique_id = ?
                ORDER BY data_ingestion_timestamp DESC
                LIMIT ?
                """
                
                cursor.execute(query, (unique_id, limit))
                rows = cursor.fetchall()
                
                return [self._row_to_dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting filing history for {unique_id}: {e}")
            return []
    
    def check_filing_exists(self, unique_id: str, transaction_id: str) -> bool:
        """
        Check if a specific filing already exists
        
        Args:
            unique_id: Company unique identifier
            transaction_id: Filing transaction ID from Companies House
            
        Returns:
            True if filing exists, False otherwise
        """
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT COUNT(*) FROM company_filing_history_accounts
                WHERE unique_id = ? AND transaction_id = ?
                """
                
                cursor.execute(query, (unique_id, transaction_id))
                count = cursor.fetchone()[0]
                
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking filing exists: {e}")
            return False
    
    def get_companies_without_recent_filings(self, days_threshold: int = 365) -> List[Dict[str, Any]]:
        """
        Get companies that don't have recent filing data
        
        Args:
            days_threshold: Number of days to consider as "recent"
            
        Returns:
            List of companies needing filing updates
        """
        try:
            threshold_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
            
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT DISTINCT c.unique_id, c.company_number, c.company_name
                FROM companies c
                LEFT JOIN company_filing_history_accounts cfha ON c.unique_id = cfha.unique_id
                WHERE cfha.unique_id IS NULL 
                   OR cfha.data_ingestion_timestamp < ?
                ORDER BY c.company_name
                """
                
                cursor.execute(query, (threshold_date,))
                rows = cursor.fetchall()
                
                return [
                    {
                        'unique_id': row[0],
                        'company_number': row[1],
                        'company_name': row[2]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting companies without recent filings: {e}")
            return []
    
    def get_all_latest_filings_for_portal(self) -> List[Dict[str, Any]]:
        """
        Get latest filing for each company (for company portal view)
        
        Returns:
            List of latest filings grouped by unique_id
        """
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    cfha.unique_id,
                    cfha.filing_date,
                    cfha.category,
                    cfha.description,
                    cfha.document_link,
                    cfha.made_up_date,
                    cfha.pages,
                    cfha.data_ingestion_timestamp
                FROM company_filing_history_accounts cfha
                INNER JOIN (
                    SELECT unique_id, MAX(data_ingestion_timestamp) as latest_timestamp
                    FROM company_filing_history_accounts
                    GROUP BY unique_id
                ) latest ON cfha.unique_id = latest.unique_id 
                         AND cfha.data_ingestion_timestamp = latest.latest_timestamp
                ORDER BY cfha.filing_date DESC
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                return [
                    {
                        'unique_id': row[0],
                        'filing_date': row[1],
                        'category': row[2],
                        'description': row[3],
                        'document_link': row[4],
                        'made_up_date': row[5],
                        'pages': row[6],
                        'data_ingestion_timestamp': row[7]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting latest filings for portal: {e}")
            return []
    
    def update_filing_record(self, unique_id: str, transaction_id: str, 
                           updated_data: Dict[str, Any]) -> bool:
        """
        Update an existing filing record
        
        Args:
            unique_id: Company unique identifier
            transaction_id: Filing transaction ID
            updated_data: Updated filing information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically based on provided fields
                update_fields = []
                values = []
                
                for field, value in updated_data.items():
                    if field not in ['unique_id', 'transaction_id']:  # Don't update key fields
                        update_fields.append(f"{field} = ?")
                        values.append(value)
                
                if not update_fields:
                    logger.warning("No valid fields to update")
                    return False
                
                # Add WHERE clause parameters
                values.extend([unique_id, transaction_id])
                
                query = f"""
                UPDATE company_filing_history_accounts 
                SET {', '.join(update_fields)}
                WHERE unique_id = ? AND transaction_id = ?
                """
                
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ Updated filing record for {unique_id}: {transaction_id}")
                    return True
                else:
                    logger.warning(f"No filing record found to update: {unique_id}, {transaction_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating filing record: {e}")
            return False
    
    def delete_old_filings(self, days_to_keep: int = 730) -> int:
        """
        Clean up old filing records (optional maintenance)
        
        Args:
            days_to_keep: Number of days of history to retain
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Keep at least one record per company, even if old
                query = """
                DELETE FROM company_filing_history_accounts
                WHERE data_ingestion_timestamp < ?
                  AND id NOT IN (
                      SELECT id FROM (
                          SELECT id, ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY data_ingestion_timestamp DESC) as rn
                          FROM company_filing_history_accounts
                      ) ranked
                      WHERE ranked.rn = 1
                  )
                """
                
                cursor.execute(query, (cutoff_date,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"🗑️  Deleted {deleted_count} old filing records (keeping records newer than {days_to_keep} days)")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error deleting old filings: {e}")
            return 0
    
    def update_extracted_revenue(self, unique_id: str, transaction_id: str, 
                               extracted_revenue: str) -> bool:
        """
        Update the extracted_revenue field for a specific filing record
        
        Args:
            unique_id: Company unique identifier
            transaction_id: Filing transaction ID
            extracted_revenue: The extracted revenue value to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                UPDATE company_filing_history_accounts 
                SET extracted_revenue = ?
                WHERE unique_id = ? AND transaction_id = ?
                """
                
                cursor.execute(query, (extracted_revenue, unique_id, transaction_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"✅ Updated extracted revenue for company {unique_id}, transaction {transaction_id}: {extracted_revenue}")
                    return True
                else:
                    logger.warning(f"⚠️ No filing record found for company {unique_id}, transaction {transaction_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating extracted revenue: {e}")
            return False

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        if not row:
            return {}
        
        # Updated to include extracted_revenue field (column 19)
        return {
            'id': row[0],
            'unique_id': row[1],
            'company_registration_number': row[2],
            'company_name': row[3],
            'company_address': row[4],
            'transaction_id': row[5],
            'barcode': row[6],
            'type': row[7],
            'filing_date': row[8],
            'category': row[9],
            'description': row[10],
            'made_up_date': row[11],
            'pages': row[12],
            'action_date': row[13],
            'paper_filed': row[14],
            'document_link': row[15],
            'api_link': row[16],
            'data_ingestion_timestamp': row[17],
            'api_response_raw': row[18],
            'extracted_revenue': row[19] if len(row) > 19 else None
        }