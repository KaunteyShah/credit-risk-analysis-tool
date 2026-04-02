"""
Concrete repository implementations for database operations.
Implements the repository interfaces with SQLite-specific logic.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..connection import db_connection
from ..models import Company, SICCode, CompanySICCode, CompanyFinancial, APIAuditLog, SICPredictionHistory
from . import (
    ICompanyRepository, ISICCodeRepository, ICompanySICCodeRepository,
    ICompanyFinancialRepository, IAPIAuditLogRepository, ISICPredictionHistoryRepository
)


class CompanyRepository(ICompanyRepository):
    """
    SQLite implementation of Company repository.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create(self, entity: Company) -> Optional[int]:
        """Create a new company."""
        query = """
        INSERT INTO companies (
            company_number, company_name, status, incorporation_date, dissolution_date,
            company_type, jurisdiction, registered_office_address, accounts_next_due_date,
            accounts_last_made_up_date, confirmation_statement_next_due_date,
            confirmation_statement_last_made_up_date, can_file,
            has_been_liquidated, has_charges, has_insolvency_history,
            undeliverable_registered_office_address, date_of_creation,
            date_of_cessation, etag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            entity.company_number, entity.company_name, entity.status,
            entity.incorporation_date, entity.dissolution_date, entity.company_type,
            entity.jurisdiction, entity.registered_office_address,
            entity.accounts_next_due_date, entity.accounts_last_made_up_date,
            entity.confirmation_statement_next_due_date,
            entity.confirmation_statement_last_made_up_date,
            entity.can_file, entity.has_been_liquidated, entity.has_charges,
            entity.has_insolvency_history, entity.undeliverable_registered_office_address,
            entity.date_of_creation, entity.date_of_cessation, entity.etag
        )
        
        try:
            return db_connection.get_last_insert_id(query, params)
        except Exception as e:
            self.logger.error(f"Failed to create company: {e}")
            return None
    
    def get_by_id(self, entity_id: int) -> Optional[Company]:
        """Get company by ID."""
        query = "SELECT * FROM companies WHERE id = ?"
        try:
            results = db_connection.execute_query(query, (entity_id,))
            if results:
                return Company.from_dict(dict(results[0]))
            return None
        except Exception as e:
            self.logger.error(f"Failed to get company by ID {entity_id}: {e}")
            return None
    
    def get_by_company_number(self, company_number: str) -> Optional[Company]:
        """Get company by company number."""
        query = "SELECT * FROM companies WHERE company_number = ?"
        try:
            results = db_connection.execute_query(query, (company_number,))
            if results:
                return Company.from_dict(dict(results[0]))
            return None
        except Exception as e:
            self.logger.error(f"Failed to get company by number {company_number}: {e}")
            return None
    
    def search_by_name(self, name: str, limit: Optional[int] = None) -> List[Company]:
        """Search companies by name pattern."""
        query = "SELECT * FROM companies WHERE company_name LIKE ? ORDER BY company_name"
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results = db_connection.execute_query(query, (f"%{name}%",))
            return [Company.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to search companies by name {name}: {e}")
            return []
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[Company]:
        """Get companies by status."""
        query = "SELECT * FROM companies WHERE status = ? ORDER BY company_name"
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results = db_connection.execute_query(query, (status,))
            return [Company.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to get companies by status {status}: {e}")
            return []
    
    def get_companies_with_sic_codes(self, company_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Get companies with their associated SIC codes."""
        query = """
        SELECT c.*, sc.sic_code, sc.sic_description, csc.is_primary
        FROM companies c
        LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
        LEFT JOIN sic_codes sc ON csc.sic_code_id = sc.id
        """
        
        params = None
        if company_ids:
            placeholders = ','.join('?' for _ in company_ids)
            query += f" WHERE c.id IN ({placeholders})"
            params = tuple(company_ids)
        
        query += " ORDER BY c.company_name, csc.is_primary DESC"
        
        try:
            results = db_connection.execute_query(query, params)
            return [dict(row) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to get companies with SIC codes: {e}")
            return []
    
    def search_companies(self, filters: Dict[str, Any], limit: Optional[int] = None, offset: Optional[int] = None) -> List[Company]:
        """Advanced search with multiple filters."""
        where_clauses = []
        params = []
        
        if filters.get('name'):
            where_clauses.append("company_name LIKE ?")
            params.append(f"%{filters['name']}%")
        
        if filters.get('status'):
            where_clauses.append("status = ?")
            params.append(filters['status'])
        
        if filters.get('company_type'):
            where_clauses.append("company_type = ?")
            params.append(filters['company_type'])
        
        if filters.get('jurisdiction'):
            where_clauses.append("jurisdiction = ?")
            params.append(filters['jurisdiction'])
        
        query = "SELECT * FROM companies"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY company_name"
        
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        try:
            results = db_connection.execute_query(query, tuple(params))
            return [Company.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to search companies with filters {filters}: {e}")
            return []
    
    def update(self, entity_id: int, updates: Dict[str, Any]) -> bool:
        """Update company by ID with provided data."""
        if not updates:
            return True
        
        # Build dynamic UPDATE query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if hasattr(Company, key):  # Validate field exists
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        query = f"UPDATE companies SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(entity_id)
        
        try:
            rows_affected = db_connection.execute_update(query, tuple(params))
            return rows_affected > 0
        except Exception as e:
            self.logger.error(f"Failed to update company {entity_id}: {e}")
            return False
    
    def delete(self, entity_id: int) -> bool:
        """Delete company by ID."""
        query = "DELETE FROM companies WHERE id = ?"
        try:
            rows_affected = db_connection.execute_update(query, (entity_id,))
            return rows_affected > 0
        except Exception as e:
            self.logger.error(f"Failed to delete company {entity_id}: {e}")
            return False
    
    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Company]:
        """List all companies with optional pagination."""
        query = "SELECT * FROM companies ORDER BY company_name"
        
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        try:
            results = db_connection.execute_query(query)
            return [Company.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to list companies: {e}")
            return []
    
    def count(self) -> int:
        """Get total count of companies."""
        query = "SELECT COUNT(*) as count FROM companies"
        try:
            result = db_connection.execute_query(query)
            return result[0]['count'] if result else 0
        except Exception as e:
            self.logger.error(f"Failed to count companies: {e}")
            return 0

    def advanced_search(self, criteria: Dict, limit: int = 20, offset: int = 0) -> List[Company]:
        """Perform advanced search with multiple criteria."""
        try:
            query_parts = ["SELECT * FROM companies WHERE 1=1"]
            params = []
            
            # Text search across multiple fields
            if 'search' in criteria:
                search_term = f"%{criteria['search']}%"
                query_parts.append("""
                    AND (company_name LIKE ? OR company_number LIKE ? OR 
                         company_number LIKE ? OR jurisdiction LIKE ?)
                """)
                params.extend([search_term, search_term, search_term, search_term])
            
            # Country filter
            if 'country' in criteria:
                query_parts.append("AND jurisdiction = ?")
                params.append(criteria['country'])
            
            # Add pagination
            query_parts.append("ORDER BY company_name LIMIT ? OFFSET ?")
            params.extend([limit, offset])
            
            query = " ".join(query_parts)
            results = db_connection.execute_query(query, tuple(params))
            
            companies = []
            for row in results:
                company = Company(
                    id=row[0],
                    company_name=row[2] if len(row) > 2 else None,  # company_name is column 2
                    company_number=row[1] if len(row) > 1 else None,  # company_number is column 1
                    status=row[3] if len(row) > 3 else None,
                    company_type=row[6] if len(row) > 6 else None,  # company_type is column 6
                    jurisdiction=row[7] if len(row) > 7 else None  # jurisdiction is column 7
                )
                companies.append(company)
            
            return companies
            
        except Exception as e:
            self.logger.error(f"Advanced search failed: {e}")
            return []

    def count_advanced_search(self, criteria: Dict) -> int:
        """Count results for advanced search criteria."""
        try:
            query_parts = ["SELECT COUNT(*) FROM companies WHERE 1=1"]
            params = []
            
            # Apply same filters as advanced_search but for counting
            if 'search' in criteria:
                search_term = f"%{criteria['search']}%"
                query_parts.append("""
                    AND (company_name LIKE ? OR company_number LIKE ? OR 
                         company_number LIKE ? OR jurisdiction LIKE ?)
                """)
                params.extend([search_term, search_term, search_term, search_term])
            
            if 'country' in criteria:
                query_parts.append("AND jurisdiction = ?")
                params.append(criteria['country'])
            
            query = " ".join(query_parts)
            result = db_connection.execute_query(query, tuple(params))
            
            return result[0][0] if result else 0
            
        except Exception as e:
            self.logger.error(f"Failed to count advanced search results: {e}")
            return 0

    def search_companies(self, filters: Dict, limit: int = 20, offset: int = 0) -> List[Company]:
        """Search companies with basic filters."""
        try:
            query_parts = ["SELECT * FROM companies WHERE 1=1"]
            params = []
            
            if 'name' in filters:
                query_parts.append("AND name LIKE ?")
                params.append(f"%{filters['name']}%")
            
            if 'status' in filters:
                query_parts.append("AND company_status = ?")
                params.append(filters['status'])
            
            if 'company_type' in filters:
                query_parts.append("AND company_type = ?")
                params.append(filters['company_type'])
            
            if 'jurisdiction' in filters:
                query_parts.append("AND jurisdiction = ?")
                params.append(filters['jurisdiction'])
            
            query_parts.append("ORDER BY company_name LIMIT ? OFFSET ?")
            params.extend([limit, offset])
            
            query = " ".join(query_parts)
            results = db_connection.execute_query(query, tuple(params))
            
            companies = []
            for row in results:
                company = Company(
                    id=row[0],
                    company_name=row[1] if len(row) > 1 else None,
                    company_number=row[2] if len(row) > 2 else None,
                    status=row[3] if len(row) > 3 else None,
                    company_type=row[4] if len(row) > 4 else None,
                    jurisdiction=row[5] if len(row) > 5 else None
                )
                companies.append(company)
            
            return companies
            
        except Exception as e:
            self.logger.error(f"Search companies failed: {e}")
            return []


class SICCodeRepository(ISICCodeRepository):
    """
    SQLite implementation of SIC Code repository.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create(self, entity: SICCode) -> Optional[int]:
        """Create a new SIC code."""
        query = """
        INSERT INTO sic_codes (
            sic_code, sic_description, section, division, group_code, class_code
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        params = (
            entity.sic_code, entity.sic_description, entity.section,
            entity.division, entity.group_code, entity.class_code
        )
        
        try:
            return db_connection.get_last_insert_id(query, params)
        except Exception as e:
            self.logger.error(f"Failed to create SIC code: {e}")
            return None
    
    def get_by_id(self, entity_id: int) -> Optional[SICCode]:
        """Get SIC code by ID."""
        query = "SELECT * FROM sic_codes WHERE id = ?"
        try:
            results = db_connection.execute_query(query, (entity_id,))
            if results:
                return SICCode.from_dict(dict(results[0]))
            return None
        except Exception as e:
            self.logger.error(f"Failed to get SIC code by ID {entity_id}: {e}")
            return None
    
    def get_by_sic_code(self, sic_code: str) -> Optional[SICCode]:
        """Get SIC code by SIC code value."""
        query = "SELECT * FROM sic_codes WHERE sic_code = ?"
        try:
            results = db_connection.execute_query(query, (sic_code,))
            if results:
                return SICCode.from_dict(dict(results[0]))
            return None
        except Exception as e:
            self.logger.error(f"Failed to get SIC code by code {sic_code}: {e}")
            return None
    
    def search_by_description(self, description: str, limit: Optional[int] = None) -> List[SICCode]:
        """Search SIC codes by description pattern."""
        query = "SELECT * FROM sic_codes WHERE sic_description LIKE ? ORDER BY sic_code"
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results = db_connection.execute_query(query, (f"%{description}%",))
            return [SICCode.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to search SIC codes by description {description}: {e}")
            return []
    
    def get_by_section(self, section: str, limit: Optional[int] = None) -> List[SICCode]:
        """Get SIC codes by section."""
        query = "SELECT * FROM sic_codes WHERE section = ? ORDER BY sic_code"
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results = db_connection.execute_query(query, (section,))
            return [SICCode.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to get SIC codes by section {section}: {e}")
            return []
    
    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[SICCode]:
        """List all SIC codes with optional pagination."""
        query = "SELECT * FROM sic_codes ORDER BY sic_code"
        
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        try:
            results = db_connection.execute_query(query)
            return [SICCode.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to list SIC codes: {e}")
            return []
    
    def update(self, entity_id: int, updates: Dict[str, Any]) -> bool:
        """Update SIC code by ID with provided data."""
        if not updates:
            return True
        
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if hasattr(SICCode, key):
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return True
        
        params.append(entity_id)
        query = f"UPDATE sic_codes SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        try:
            affected_rows = db_connection.execute_update(query, tuple(params))
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to update SIC code {entity_id}: {e}")
            return False
    
    def delete(self, entity_id: int) -> bool:
        """Delete SIC code by ID."""
        query = "DELETE FROM sic_codes WHERE id = ?"
        try:
            affected_rows = db_connection.execute_update(query, (entity_id,))
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to delete SIC code {entity_id}: {e}")
            return False
    
    def count(self) -> int:
        """Get total count of SIC codes."""
        query = "SELECT COUNT(*) FROM sic_codes"
        try:
            results = db_connection.execute_query(query)
            return results[0][0] if results else 0
        except Exception as e:
            self.logger.error(f"Failed to count SIC codes: {e}")
            return 0

    def get_hierarchical_structure(self) -> Dict[str, Any]:
        """Get SIC codes organized by hierarchical structure."""
        try:
            results = db_connection.execute_query("""
                SELECT section, division, group_code, class_code, sic_code, sic_description
                FROM sic_codes 
                ORDER BY section, division, group_code, class_code, sic_code
            """)
            
            structure = {}
            for row in results:
                section, division, group_code, class_code, sic_code, description = row
                
                if section not in structure:
                    structure[section] = {}
                if division and division not in structure[section]:
                    structure[section][division] = {}
                if group_code and group_code not in structure[section][division]:
                    structure[section][division][group_code] = {}
                if class_code and class_code not in structure[section][division][group_code]:
                    structure[section][division][group_code][class_code] = []
                
                if class_code:
                    structure[section][division][group_code][class_code].append({
                        'sic_code': sic_code,
                        'description': description
                    })
            
            return structure
        except Exception as e:
            self.logger.error(f"Failed to get hierarchical structure: {e}")
            return {}


class CompanySICCodeRepository(ICompanySICCodeRepository):
    """
    SQLite implementation of Company-SIC Code relationship repository.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create(self, entity: CompanySICCode) -> Optional[int]:
        """Create a new company-SIC code relationship."""
        query = """
        INSERT INTO company_sic_codes (company_id, sic_code_id, is_primary)
        VALUES (?, ?, ?)
        """
        
        params = (entity.company_id, entity.sic_code_id, entity.is_primary)
        
        try:
            return db_connection.get_last_insert_id(query, params)
        except Exception as e:
            self.logger.error(f"Failed to create company-SIC relationship: {e}")
            return None
    
    def get_by_id(self, entity_id: int) -> Optional[CompanySICCode]:
        """Get company-SIC relationship by ID."""
        query = "SELECT * FROM company_sic_codes WHERE id = ?"
        try:
            results = db_connection.execute_query(query, (entity_id,))
            if results:
                return CompanySICCode.from_dict(dict(results[0]))
            return None
        except Exception as e:
            self.logger.error(f"Failed to get company-SIC relationship by ID {entity_id}: {e}")
            return None
    
    def get_by_company_id(self, company_id: int) -> List[CompanySICCode]:
        """Get all SIC code relationships for a company."""
        query = "SELECT * FROM company_sic_codes WHERE company_id = ? ORDER BY is_primary DESC, id"
        try:
            results = db_connection.execute_query(query, (company_id,))
            return [CompanySICCode.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to get SIC relationships for company {company_id}: {e}")
            return []
    
    def get_by_sic_code_id(self, sic_code_id: int) -> List[CompanySICCode]:
        """Get all company relationships for a SIC code."""
        query = "SELECT * FROM company_sic_codes WHERE sic_code_id = ? ORDER BY id"
        try:
            results = db_connection.execute_query(query, (sic_code_id,))
            return [CompanySICCode.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to get company relationships for SIC code {sic_code_id}: {e}")
            return []
    
    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[CompanySICCode]:
        """List all company-SIC relationships with optional pagination."""
        query = "SELECT * FROM company_sic_codes ORDER BY company_id, is_primary DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        try:
            results = db_connection.execute_query(query)
            return [CompanySICCode.from_dict(dict(row)) for row in results]
        except Exception as e:
            self.logger.error(f"Failed to list company-SIC relationships: {e}")
            return []
    
    def update(self, entity_id: int, updates: Dict[str, Any]) -> bool:
        """Update company-SIC relationship by ID."""
        if not updates:
            return True
        
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if hasattr(CompanySICCode, key):
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return True
        
        params.append(entity_id)
        query = f"UPDATE company_sic_codes SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            affected_rows = db_connection.execute_update(query, tuple(params))
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to update company-SIC relationship {entity_id}: {e}")
            return False
    
    def delete(self, entity_id: int) -> bool:
        """Delete company-SIC relationship by ID."""
        query = "DELETE FROM company_sic_codes WHERE id = ?"
        try:
            affected_rows = db_connection.execute_update(query, (entity_id,))
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to delete company-SIC relationship {entity_id}: {e}")
            return False
    
    def count(self) -> int:
        """Get total count of company-SIC relationships."""
        query = "SELECT COUNT(*) FROM company_sic_codes"
        try:
            results = db_connection.execute_query(query)
            return results[0][0] if results else 0
        except Exception as e:
            self.logger.error(f"Failed to count company-SIC relationships: {e}")
            return 0

    def add_sic_to_company(self, company_id: int, sic_code_id: int, is_primary: bool = False) -> Optional[int]:
        """Associate a SIC code with a company."""
        try:
            # Check if relationship already exists
            existing_query = "SELECT id FROM company_sic_codes WHERE company_id = ? AND sic_code_id = ?"
            existing = db_connection.execute_query(existing_query, (company_id, sic_code_id))
            
            if existing:
                self.logger.info(f"SIC relationship already exists: company {company_id}, SIC {sic_code_id}")
                return existing[0][0]
            
            # Create new relationship
            relationship = CompanySICCode(
                company_id=company_id,
                sic_code_id=sic_code_id,
                is_primary=is_primary
            )
            return self.create(relationship)
            
        except Exception as e:
            self.logger.error(f"Failed to add SIC to company: {e}")
            return None

    def remove_sic_from_company(self, company_id: int, sic_code_id: int) -> bool:
        """Remove SIC code association from company."""
        try:
            query = "DELETE FROM company_sic_codes WHERE company_id = ? AND sic_code_id = ?"
            affected_rows = db_connection.execute_update(query, (company_id, sic_code_id))
            return affected_rows > 0
        except Exception as e:
            self.logger.error(f"Failed to remove SIC from company: {e}")
            return False

    def set_primary_sic(self, company_id: int, sic_code_id: int) -> bool:
        """Set a SIC code as primary for a company."""
        try:
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, set all SICs for this company as non-primary
                cursor.execute(
                    "UPDATE company_sic_codes SET is_primary = FALSE WHERE company_id = ?",
                    (company_id,)
                )
                
                # Then set the specified SIC as primary
                cursor.execute(
                    "UPDATE company_sic_codes SET is_primary = TRUE WHERE company_id = ? AND sic_code_id = ?",
                    (company_id, sic_code_id)
                )
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to set primary SIC: {e}")
            return False

# Create repository instances
company_repository = CompanyRepository()