"""
SQLite-based company repository that uses proper database field names.
Implements the same interface as FileCompanyRepository but reads from SQLite database.
"""
import logging
import sqlite3
from typing import Dict, Any, Optional, List
import pandas as pd

from app_modules.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
from app_modules.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class SQLiteCompanyRepository(CompanyRepositoryInterface):
    """
    SQLite implementation of company repository using proper database field names.
    """
    
    def __init__(self):
        self.db_connection = DatabaseConnection()
        self._data_loaded = True  # SQLite is always "loaded"
        
    def is_data_loaded(self) -> bool:
        """Check if data is loaded (always True for SQLite)"""
        return self._data_loaded
    
    def get_companies_count(self) -> int:
        """Get total number of companies"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM companies")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting companies count: {e}")
            return 0
    
    def get_company_by_index(self, company_index: int) -> Optional[Dict[str, Any]]:
        """Get company by index (row position)"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city, 
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total, 
                           c.sales_gbp
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
                        'company_name': row[2],
                        'business_description': row[3] or '',
                        'phone': row[4] or '',
                        'email': row[5] or '',
                        'website': row[6] or '',
                        'address_line_1': row[7] or '',
                        'city': row[8] or '',
                        'post_code': row[9] or '',
                        'country': row[10] or '',
                        'uk_sic_2007_code': row[11] or '',
                        'employees_total': row[12],
                        'sales_gbp': row[13],
                        'confidence': 0.0  # Default value for compatibility
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting company by index {company_index}: {e}")
            return None
    
    def get_companies_paginated(self, page: int, limit: int, 
                               country: Optional[str] = None, 
                               search: Optional[str] = None) -> Dict[str, Any]:
        """Get paginated companies with filters"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                where_conditions = []
                params = []
                
                if country and country != 'all':
                    where_conditions.append("c.country = ?")
                    params.append(country)
                    
                if search:
                    where_conditions.append("c.company_name LIKE ?")
                    params.append(f"%{search}%")
                
                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                
                # Get total count
                count_query = f"""
                    SELECT COUNT(*) 
                    FROM companies c 
                    {where_clause}
                """
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Get paginated data
                offset = (page - 1) * limit
                data_query = f"""
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    {where_clause}
                    ORDER BY c.id
                    LIMIT ? OFFSET ?
                """
                cursor.execute(data_query, params + [limit, offset])
                rows = cursor.fetchall()
                
                # Format data with proper database field names
                records = []
                for idx, row in enumerate(rows):
                    record = {
                        '_index': offset + idx,  # Original index for compatibility
                        'company_name': row[2] or '',
                        'country': row[10] or '',
                        'employees_total': row[12],
                        'sales_gbp': row[13],
                        'uk_sic_2007_code': row[11] or '',
                        'confidence': 0.0,  # Default for compatibility
                        'business_description': row[3] or '',
                        'phone': row[4] or '',
                        'email': row[5] or '',
                        'website': row[6] or '',
                        'address_line_1': row[7] or '',
                        'city': row[8] or '',
                        'post_code': row[9] or ''
                    }
                    records.append(record)
                
                return {
                    'data': records,
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'total_pages': (total + limit - 1) // limit
                }
                
        except Exception as e:
            logger.error(f"Error getting paginated companies: {e}")
            return {'data': [], 'total': 0, 'page': page, 'limit': limit, 'total_pages': 0}
    
    def get_all_companies(self) -> pd.DataFrame:
        """Get all companies as DataFrame for compatibility with existing service code"""
        try:
            with self.db_connection.get_connection() as conn:
                query = """
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    ORDER BY c.id
                """
                df = pd.read_sql_query(query, conn)
                
                # Rename columns to match expected database field names
                df.rename(columns={
                    'id': 'id',
                    'company_number': 'company_number',
                    'company_name': 'company_name',
                    'business_description': 'business_description',
                    'phone': 'phone',
                    'email': 'email',
                    'website': 'website',
                    'address_line_1': 'address_line_1',
                    'city': 'city',
                    'post_code': 'post_code',
                    'country': 'country',
                    'uk_sic_2007_code': 'uk_sic_2007_code',
                    'employees_total': 'employees_total',
                    'sales_gbp': 'sales_gbp'
                }, inplace=True)
                
                # Add compatibility columns
                df['confidence'] = 0.0
                
                return df
                
        except Exception as e:
            logger.error(f"Error getting all companies: {e}")
            return pd.DataFrame()
    
    def refresh_data(self):
        """Refresh data (no-op for SQLite)"""
        pass
    
    def get_countries(self) -> List[str]:
        """Get list of unique countries"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT country FROM companies WHERE country IS NOT NULL ORDER BY country")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting countries: {e}")
            return []

    def get_company_by_name(self, company_name: str, 
                           registration_number: Optional[str] = None,
                           sic_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get company data by name with optional filtering"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                where_conditions = ["c.company_name LIKE ?"]
                params = [f"%{company_name}%"]
                
                if registration_number:
                    where_conditions.append("c.company_number = ?")
                    params.append(registration_number)
                    
                if sic_code:
                    where_conditions.append("csc.uk_sic_2007_code = ?")
                    params.append(sic_code)
                
                query = f"""
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE {' AND '.join(where_conditions)}
                    LIMIT 1
                """
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'company_number': row[1],
                        'company_name': row[2],
                        'business_description': row[3] or '',
                        'phone': row[4] or '',
                        'email': row[5] or '',
                        'website': row[6] or '',
                        'address_line_1': row[7] or '',
                        'city': row[8] or '',
                        'post_code': row[9] or '',
                        'country': row[10] or '',
                        'uk_sic_2007_code': row[11] or '',
                        'employees_total': row[12],
                        'sales_gbp': row[13],
                        'confidence': 0.0
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting company by name {company_name}: {e}")
            return None

    def load_company_data(self) -> bool:
        """Load company data (always returns True for SQLite)"""
        return True

    def get_company_by_registration(self, registration: str) -> Optional[Dict[str, Any]]:
        """Get company by registration number"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE c.company_number = ?
                """, (registration,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'company_number': row[1],
                        'company_name': row[2],
                        'business_description': row[3] or '',
                        'phone': row[4] or '',
                        'email': row[5] or '',
                        'website': row[6] or '',
                        'address_line_1': row[7] or '',
                        'city': row[8] or '',
                        'post_code': row[9] or '',
                        'country': row[10] or '',
                        'uk_sic_2007_code': row[11] or '',
                        'employees_total': row[12],
                        'sales_gbp': row[13],
                        'confidence': 0.0
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting company by registration {registration}: {e}")
            return None

    def get_companies_by_sic_code(self, sic_code: str) -> pd.DataFrame:
        """Get companies by SIC code"""
        try:
            with self.db_connection.get_connection() as conn:
                query = """
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE csc.uk_sic_2007_code = ?
                    ORDER BY c.id
                """
                return pd.read_sql_query(query, conn, params=[sic_code])
        except Exception as e:
            logger.error(f"Error getting companies by SIC code {sic_code}: {e}")
            return pd.DataFrame()

    def search_companies_by_name(self, name_query: str) -> pd.DataFrame:
        """Search companies by name"""
        try:
            with self.db_connection.get_connection() as conn:
                query = """
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE c.company_name LIKE ?
                    ORDER BY c.id
                """
                return pd.read_sql_query(query, conn, params=[f"%{name_query}%"])
        except Exception as e:
            logger.error(f"Error searching companies by name {name_query}: {e}")
            return pd.DataFrame()

    def update_company_sic_prediction(self, registration: str, sic_code: str, 
                                    confidence: float, algorithm: str) -> bool:
        """Update company SIC prediction"""
        # For now, return True as we have separate SIC prediction repositories
        logger.info(f"SIC prediction update for {registration} -> {sic_code} (confidence: {confidence})")
        return True

    def update_company_revenue(self, registration: str, revenue: float) -> bool:
        """Update company revenue"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE companies SET sales_gbp = ? WHERE company_number = ?
                """, (revenue, registration))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating revenue for {registration}: {e}")
            return False

    def get_companies_requiring_sic_prediction(self) -> pd.DataFrame:
        """Get companies needing SIC prediction"""
        try:
            with self.db_connection.get_connection() as conn:
                query = """
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE csc.uk_sic_2007_code IS NULL OR csc.uk_sic_2007_code = ''
                    ORDER BY c.id
                """
                return pd.read_sql_query(query, conn)
        except Exception as e:
            logger.error(f"Error getting companies requiring SIC prediction: {e}")
            return pd.DataFrame()

    def get_revenue_statistics(self) -> Dict[str, Any]:
        """Get revenue statistics"""
        try:
            with self.db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as count,
                        AVG(sales_gbp) as mean,
                        MIN(sales_gbp) as min,
                        MAX(sales_gbp) as max
                    FROM companies 
                    WHERE sales_gbp IS NOT NULL
                """)
                row = cursor.fetchone()
                if row:
                    return {
                        'count': row[0],
                        'mean': row[1] or 0,
                        'median': row[1] or 0,  # Simplified
                        'min': row[2] or 0,
                        'max': row[3] or 0
                    }
                return {'count': 0, 'mean': 0, 'median': 0, 'min': 0, 'max': 0}
        except Exception as e:
            logger.error(f"Error getting revenue statistics: {e}")
            return {'count': 0, 'mean': 0, 'median': 0, 'min': 0, 'max': 0}

    def get_companies_by_revenue_range(self, min_revenue: float, max_revenue: float) -> pd.DataFrame:
        """Get companies by revenue range"""
        try:
            with self.db_connection.get_connection() as conn:
                query = """
                    SELECT c.id, c.company_number, c.company_name, c.business_description,
                           c.phone, c.email, c.website, c.address_line_1, c.city,
                           c.post_code, c.country, csc.uk_sic_2007_code, c.employees_total,
                           c.sales_gbp
                    FROM companies c
                    LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE c.sales_gbp BETWEEN ? AND ?
                    ORDER BY c.id
                """
                return pd.read_sql_query(query, conn, params=[min_revenue, max_revenue])
        except Exception as e:
            logger.error(f"Error getting companies by revenue range: {e}")
            return pd.DataFrame()

    def get_data_status(self) -> Dict[str, Any]:
        """Get data status"""
        try:
            companies_count = self.get_companies_count()
            return {
                'loaded': True,
                'count': companies_count,
                'source': 'sqlite',
                'status': 'ready'
            }
        except Exception as e:
            logger.error(f"Error getting data status: {e}")
            return {'loaded': False, 'count': 0, 'source': 'sqlite', 'status': 'error'}