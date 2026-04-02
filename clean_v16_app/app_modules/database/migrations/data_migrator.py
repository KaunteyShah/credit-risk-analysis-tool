"""
Data Migration Framework for Phase 2: CSV/Excel to SQLite Migration
Handles parsing and migrating company data and SIC codes to database.
"""

import pandas as pd
import sqlite3
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict

from ..connection import db_connection
from ..models import Company, SICCode, CompanySICCode, CompanyFinancial
from . import migration_manager


class DataMigrator:
    """
    Comprehensive data migration system for CSV and Excel data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db_connection
        self.migration_manager = migration_manager
        
        # Field mappings from CSV to database schema (matching models.py Company fields)
        self.company_field_mapping = {
            # Core identification fields
            'Company Name': 'company_name',
            'Registration number': 'company_number',
            'Country': 'jurisdiction',  # Country maps to jurisdiction
            
            # Address fields
            'Address Line 1': 'address_line_1',
            'Address Line 2': 'address_line_2', 
            'Address Line 3': 'address_line_3',
            'City': 'city',
            'Post Code': 'post_code',
            
            # Contact information
            'Phone': 'phone',
            'Company Email': 'email',
            'Website': 'website',
            
            # Business information
            'Business Description': 'business_description',
            
            # Detailed SIC code fields (now go to separate company_sic_codes table)
            'US 8-Digit SIC Code': 'us_8_digit_sic_code',
            'US 8-Digit SIC Description': 'us_8_digit_sic_description',
            'US SIC 1987 Code': 'us_sic_1987_code',
            'US SIC 1987 Description': 'us_sic_1987_description',
            'UK SIC 2007 Code': 'uk_sic_2007_code',
            'UK SIC 2007 Description': 'uk_sic_2007_description',
            'NAICS 2022 Code': 'naics_2022_code',
            'NAICS 2022 Description': 'naics_2022_description',
            'ANZSIC 2006 Code': 'anzsic_2006_code',
            'ANZSIC 2006 Description': 'anzsic_2006_description',
            
            # Additional CSV fields
            'D-U-N-S® Number': 'duns_number',
            'Ownership Type': 'ownership_type',
            'Entity Type': 'entity_type',
            'Parent Company': 'parent_company',
            'Parent Country/Region': 'parent_country',  # Map to parent_country
            'Global Ultimate Company': 'global_ultimate_company',
            'Global Ultimate Country/Region': 'global_ultimate_country'  # Map to global_ultimate_country
        }
        
        # Financial field mappings (matching Sample_data2.csv exactly)
        self.financial_field_mapping = {
            'Sales (GBP)': 'sales_gbp',
            'Pre Tax Profit (USD)': 'pre_tax_profit_usd',
            'Assets (USD)': 'assets_usd',
            'Employees (Total)': 'employees_total',
            'Employees (Single Site)': 'employees_single_site'
        }
        
        # SIC code field mappings
        self.sic_field_mapping = {
            'US 8-Digit SIC Code': 'us_8_digit_sic_code',
            'US 8-Digit SIC Description': 'us_8_digit_sic_description',
            'US SIC 1987 Code': 'us_sic_1987_code',
            'US SIC 1987 Description': 'us_sic_1987_description',
            'UK SIC 2007 Code': 'uk_sic_2007_code',
            'UK SIC 2007 Description': 'uk_sic_2007_description',
            'NAICS 2022 Code': 'naics_2022_code',
            'NAICS 2022 Description': 'naics_2022_description',
            'ANZSIC 2006 Code': 'anzsic_2006_code',
            'ANZSIC 2006 Description': 'anzsic_2006_description'
        }
    
    def run_full_migration(self) -> Dict[str, Any]:
        """
        Execute complete data migration from CSV/Excel to SQLite.
        
        Returns:
            Migration results summary
        """
        self.logger.info("🚀 Starting Phase 2: Full Data Migration")
        
        migration_results = {
            'start_time': datetime.now(),
            'success': False,
            'companies_migrated': 0,
            'sic_codes_migrated': 0,
            'company_sic_relationships': 0,
            'financial_records': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Step 1: Ensure database schema is ready
            self._ensure_schema_ready()
            
            # Step 2: Migrate SIC codes first (foreign key dependency)
            sic_results = self.migrate_sic_codes_from_excel('data/SIC_codes.xlsx')
            migration_results.update(sic_results)
            
            # Step 3: Migrate company data from CSV
            company_results = self.migrate_companies_from_csv('data/Sample_data2.csv')
            migration_results.update(company_results)
            
            # Step 4: SIC codes are already in companies table, no separate relationships needed
            
            # Step 5: Validate migration integrity
            validation_results = self.validate_migration()
            migration_results.update(validation_results)
            
            migration_results['success'] = True
            migration_results['end_time'] = datetime.now()
            
            self.logger.info("✅ Phase 2 Migration completed successfully")
            self.logger.info(f"📊 Results: {migration_results['companies_migrated']} companies, "
                           f"{migration_results['sic_codes_migrated']} SIC codes, "
                           f"{migration_results['company_sic_relationships']} relationships")
            
            return migration_results
            
        except Exception as e:
            migration_results['success'] = False
            migration_results['errors'].append(str(e))
            migration_results['end_time'] = datetime.now()
            
            self.logger.error(f"❌ Migration failed: {e}")
            return migration_results
    
    def _ensure_schema_ready(self):
        """Ensure database schema is properly set up."""
        if not self.migration_manager.is_migration_applied('001_create_tables'):
            self.logger.info("Applying database schema migration...")
            success = self.migration_manager.apply_all_migrations()
            if not success:
                raise RuntimeError("Failed to apply database schema migrations")
    
    def migrate_sic_codes_from_excel(self, excel_path: str) -> Dict[str, Any]:
        """
        Migrate SIC codes from Excel file to SQLite database.
        
        Args:
            excel_path: Path to SIC codes Excel file
            
        Returns:
            Migration results for SIC codes
        """
        self.logger.info(f"📊 Migrating SIC codes from {excel_path}")
        
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"SIC codes file not found: {excel_path}")
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_path)
            self.logger.info(f"Found {len(df)} SIC codes in Excel file")
            
            # Parse SIC codes with hierarchical structure
            sic_codes = self._parse_sic_codes_from_excel(df)
            
            # Batch insert SIC codes
            inserted_count = self._batch_insert_sic_codes(sic_codes)
            
            self.logger.info(f"✅ Successfully migrated {inserted_count} SIC codes")
            return {'sic_codes_migrated': inserted_count}
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate SIC codes: {e}")
            raise
    
    def _parse_sic_codes_from_excel(self, df: pd.DataFrame) -> List[SICCode]:
        """Parse SIC codes from Excel data into SICCode objects."""
        sic_codes = []
        
        # Assuming first column is code, second is description
        code_column = df.columns[0]
        description_column = df.columns[1]
        
        for index, row in df.iterrows():
            code = str(row[code_column]).strip()
            description = str(row[description_column]).strip()
            
            # Skip invalid entries
            if pd.isna(code) or pd.isna(description) or code == 'nan' or description == 'nan':
                continue
            
            # Parse hierarchical structure from code
            section, division, group_code, class_code = self._parse_sic_hierarchy(code)
            
            sic_code = SICCode(
                sic_code=code,
                sic_description=description,
                section=section,
                division=division,
                group_code=group_code,
                class_code=class_code,
                created_at=datetime.now()
            )
            
            sic_codes.append(sic_code)
        
        self.logger.info(f"Parsed {len(sic_codes)} valid SIC codes")
        return sic_codes
    
    def _parse_sic_hierarchy(self, sic_code: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse SIC code hierarchical structure."""
        # UK SIC 2007 structure: Section(Letter) + Division(2) + Group(3) + Class(4+)
        if len(sic_code) >= 4:
            # For numeric codes, derive hierarchy
            if sic_code.isdigit():
                section = sic_code[0] if len(sic_code) >= 1 else None
                division = sic_code[:2] if len(sic_code) >= 2 else None
                group_code = sic_code[:3] if len(sic_code) >= 3 else None
                class_code = sic_code if len(sic_code) >= 4 else None
            else:
                # Mixed alphanumeric codes
                section = sic_code[0] if sic_code[0].isalpha() else None
                division = sic_code[1:3] if len(sic_code) >= 3 else None
                group_code = sic_code[1:4] if len(sic_code) >= 4 else None
                class_code = sic_code
        else:
            section = division = group_code = class_code = None
        
        return section, division, group_code, class_code
    
    def _batch_insert_sic_codes(self, sic_codes: List[SICCode]) -> int:
        """Batch insert SIC codes into database."""
        query = """
        INSERT OR IGNORE INTO sic_codes (
            sic_code, sic_description, section, division, group_code, class_code, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for sic_code in sic_codes:
            params_list.append((
                sic_code.sic_code,
                sic_code.sic_description,
                sic_code.section,
                sic_code.division,
                sic_code.group_code,
                sic_code.class_code,
                sic_code.created_at
            ))
        
        inserted_count = self.db.execute_many(query, params_list)
        return inserted_count
    
    def migrate_companies_from_csv(self, csv_path: str) -> Dict[str, Any]:
        """
        Migrate company data from CSV file to SQLite database.
        
        Args:
            csv_path: Path to companies CSV file
            
        Returns:
            Migration results for companies
        """
        self.logger.info(f"🏢 Migrating companies from {csv_path}")
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Companies CSV file not found: {csv_path}")
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            self.logger.info(f"Found {len(df)} companies in CSV file")
            
            # Parse companies and financial data
            companies, financial_records = self._parse_companies_from_csv(df)
            
            # Batch insert companies
            companies_inserted = self._batch_insert_companies(companies)
            
            # Batch insert SIC data to separate table
            sic_records_inserted = self._batch_insert_company_sic_codes(df)
            
            # Batch insert financial records
            financials_inserted = self._batch_insert_financial_records(financial_records)
            
            self.logger.info(f"✅ Successfully migrated {companies_inserted} companies and {financials_inserted} financial records")
            return {
                'companies_migrated': companies_inserted,
                'financial_records': financials_inserted
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to migrate companies: {e}")
            raise
    
    def _parse_companies_from_csv(self, df: pd.DataFrame) -> Tuple[List[Company], List[CompanyFinancial]]:
        """Parse company and financial data from CSV."""
        companies = []
        financial_records = []
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            row_index = idx
            
            # Parse company data
            company_data = {}
            for csv_field, db_field in self.company_field_mapping.items():
                if csv_field in df.columns:
                    value = row[csv_field]
                    # Check if value is not null/nan
                    if pd.notna(value):
                        str_value = str(value).strip()
                        if str_value and str_value.lower() not in ['nan', 'null', 'none', '']:
                            cleaned_value = self._clean_string_value(str_value)
                            if cleaned_value:
                                company_data[db_field] = cleaned_value
            
            # Set defaults and metadata
            company_data.update({
                'status': 'Active',  # Default status
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            
            company = Company(**company_data)
            companies.append(company)
            
            # Parse financial data
            financial_data: Dict[str, Any] = {'company_id': row_index + 1}
            has_financial_data = False
            
            for csv_field, db_field in self.financial_field_mapping.items():
                if csv_field in df.columns:
                    value = row[csv_field]
                    if pd.notna(value):
                        str_value = str(value).strip()
                        if str_value and str_value.lower() not in ['nan', 'null', 'none', '']:
                            # Clean and convert financial values
                            if db_field in ['employees_total', 'employees_single_site']:
                                try:
                                    cleaned_value = int(float(str_value.replace(',', '')))
                                    financial_data[db_field] = cleaned_value
                                    has_financial_data = True
                                except (ValueError, TypeError):
                                    pass
                            else:
                                cleaned_value = self._clean_financial_value(str_value)
                                if cleaned_value is not None:
                                    financial_data[db_field] = cleaned_value
                                    has_financial_data = True
            
            # Add financial metadata
            if has_financial_data:
                financial_data.update({
                    'financial_year': '2023',  # Default year
                    'currency_original': 'USD',
                    'data_source': 'CSV_IMPORT',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
                
                financial = CompanyFinancial(**financial_data)
                financial_records.append(financial)
        
        self.logger.info(f"Parsed {len(companies)} companies and {len(financial_records)} financial records")
        return companies, financial_records
    
    def _batch_insert_company_sic_codes(self, df: pd.DataFrame) -> int:
        """Batch insert SIC codes into separate company_sic_codes table."""
        query = """
        INSERT INTO company_sic_codes (
            company_id, company_name,
            us_8_digit_sic_code, us_8_digit_sic_description,
            us_sic_1987_code, us_sic_1987_description,
            uk_sic_2007_code, uk_sic_2007_description,
            naics_2022_code, naics_2022_description,
            anzsic_2006_code, anzsic_2006_description,
            is_primary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for idx in range(len(df)):
            row = df.iloc[idx]
            company_id = idx + 1
            company_name = str(row.get('Company Name', '')).strip()
            
            # Extract SIC data
            sic_data = {}
            for csv_field, db_field in self.sic_field_mapping.items():
                if csv_field in df.columns:
                    value = row[csv_field]
                    if pd.notna(value):
                        cleaned_value = str(value).strip()
                        if cleaned_value and cleaned_value.lower() not in ['nan', 'null', 'none', '']:
                            sic_data[db_field] = cleaned_value
            
            # Only insert if we have SIC data
            if sic_data:
                params_list.append((
                    company_id,
                    company_name,
                    sic_data.get('us_8_digit_sic_code', None),
                    sic_data.get('us_8_digit_sic_description', None),
                    sic_data.get('us_sic_1987_code', None),
                    sic_data.get('us_sic_1987_description', None),
                    sic_data.get('uk_sic_2007_code', None),
                    sic_data.get('uk_sic_2007_description', None),
                    sic_data.get('naics_2022_code', None),
                    sic_data.get('naics_2022_description', None),
                    sic_data.get('anzsic_2006_code', None),
                    sic_data.get('anzsic_2006_description', None),
                    True,  # is_primary
                    datetime.now()
                ))
        
        if params_list:
            inserted_count = self.db.execute_many(query, params_list)
            self.logger.info(f"✅ Inserted {inserted_count} SIC records into company_sic_codes table")
            return inserted_count
        return 0
    
    def _clean_string_value(self, value: str) -> Optional[str]:
        """Clean and normalize string values."""
        if not value or value.lower() in ['nan', 'null', 'none', '']:
            return None
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', str(value).strip())
        return cleaned if cleaned else None
    
    def _clean_financial_value(self, value: str) -> Optional[float]:
        """Clean and convert financial values to float."""
        if not value or value.lower() in ['nan', 'null', 'none', '', '0']:
            return None
        
        # Remove commas, currency symbols, and whitespace
        cleaned = re.sub(r'[,$£€¥]', '', str(value).strip())
        cleaned = re.sub(r'\s+', '', cleaned)
        
        try:
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _batch_insert_companies(self, companies: List[Company]) -> int:
        """Batch insert companies into database matching comprehensive schema."""
        query = """
        INSERT INTO companies (
            company_name, company_number, status, jurisdiction,
            address_line_1, address_line_2, address_line_3, city, post_code,
            phone, email, website, business_description,
            duns_number, ownership_type, entity_type, parent_company, parent_country,
            global_ultimate_company, global_ultimate_country,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for company in companies:            
            params_list.append((
                getattr(company, 'company_name', None),
                getattr(company, 'company_number', None),
                getattr(company, 'status', 'Active'),  # Default status
                getattr(company, 'jurisdiction', None),
                getattr(company, 'address_line_1', None),
                getattr(company, 'address_line_2', None),
                getattr(company, 'address_line_3', None),
                getattr(company, 'city', None),
                getattr(company, 'post_code', None),
                getattr(company, 'phone', None),
                getattr(company, 'email', None),
                getattr(company, 'website', None),
                getattr(company, 'business_description', None),
                getattr(company, 'duns_number', None),
                getattr(company, 'ownership_type', None),
                getattr(company, 'entity_type', None),
                getattr(company, 'parent_company', None),
                getattr(company, 'parent_country', None),
                getattr(company, 'global_ultimate_company', None),
                getattr(company, 'global_ultimate_country', None),
                getattr(company, 'created_at', datetime.now()),
                getattr(company, 'updated_at', datetime.now())
            ))
        
        inserted_count = self.db.execute_many(query, params_list)
        return inserted_count
    
    def _batch_insert_financial_records(self, financial_records: List[CompanyFinancial]) -> int:
        """Batch insert financial records into database."""
        query = """
        INSERT INTO company_financials (
            company_id, sales_gbp, pre_tax_profit_usd, assets_usd, 
            employees_single_site, employees_total, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for i, financial in enumerate(financial_records):
            params_list.append((
                i + 1,  # company_id based on insertion order
                getattr(financial, 'sales_gbp', None),
                getattr(financial, 'pre_tax_profit_usd', None),
                getattr(financial, 'assets_usd', None),
                getattr(financial, 'employees_single_site', None),
                getattr(financial, 'employees_total', None),
                getattr(financial, 'created_at', datetime.now()),
                getattr(financial, 'updated_at', datetime.now())
            ))
        
        inserted_count = self.db.execute_many(query, params_list)
        return inserted_count
    
    def create_company_sic_relationships(self, csv_path: str) -> Dict[str, Any]:
        """Create company-SIC code relationships from CSV data."""
        self.logger.info("🔗 Creating company-SIC code relationships")
        
        try:
            df = pd.read_csv(csv_path)
            relationships_created = 0
            
            for index, row in df.iterrows():
                company_id = index + 1
                
                # Extract SIC codes from various columns
                sic_mappings = [
                    ('UK SIC 2007 Code', 'current'),
                    ('US SIC 1987 Code', 'historical'),
                    ('NAICS 2022 Code', 'historical')
                ]
                
                for sic_column, sic_type in sic_mappings:
                    if sic_column in row:
                        sic_code = str(row[sic_column]).strip()
                        if sic_code and sic_code.lower() not in ['nan', 'null', 'none']:
                            # Check if SIC code exists in database
                            if self._sic_code_exists(sic_code):
                                self._insert_company_sic_relationship(
                                    company_id, sic_code, sic_type, 
                                    is_primary=(sic_column == 'UK SIC 2007 Code')
                                )
                                relationships_created += 1
            
            self.logger.info(f"✅ Created {relationships_created} company-SIC relationships")
            return {'company_sic_relationships': relationships_created}
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create SIC relationships: {e}")
            raise
    
    def _sic_code_exists(self, sic_code: str) -> bool:
        """Check if SIC code exists in database."""
        query = "SELECT COUNT(*) as count FROM sic_codes WHERE sic_code = ?"
        result = self.db.execute_query(query, (sic_code,))
        return result[0]['count'] > 0
    
    def _insert_company_sic_relationship(self, company_id: int, sic_code: str, sic_type: str, is_primary: bool = False):
        """Insert company-SIC code relationship."""
        # Get SIC code ID
        query = "SELECT id FROM sic_codes WHERE sic_code = ?"
        result = self.db.execute_query(query, (sic_code,))
        
        if result:
            sic_code_id = result[0]['id']
            
            # Insert relationship
            insert_query = """
            INSERT OR IGNORE INTO company_sic_codes (
                company_id, sic_code_id, is_primary, created_at
            ) VALUES (?, ?, ?, ?)
            """
            self.db.execute_update(insert_query, (company_id, sic_code_id, is_primary, datetime.now()))
    
    def validate_migration(self) -> Dict[str, Any]:
        """Validate the migration integrity and completeness."""
        self.logger.info("🔍 Validating migration integrity...")
        
        validation_results = {
            'companies_count': 0,
            'sic_codes_count': 0,
            'relationships_count': 0,
            'financial_records_count': 0,
            'validation_errors': []
        }
        
        try:
            # Count records in each table
            validation_results['companies_count'] = self._get_table_count('companies')
            validation_results['sic_codes_count'] = self._get_table_count('sic_codes')
            validation_results['relationships_count'] = self._get_table_count('company_sic_codes')
            validation_results['financial_records_count'] = self._get_table_count('company_financials')
            
            # Validate foreign key relationships
            orphaned_relationships = self._check_orphaned_relationships()
            if orphaned_relationships:
                validation_results['validation_errors'].append(f"Found {orphaned_relationships} orphaned SIC relationships")
            
            # Validate data integrity
            companies_without_sic = self._check_companies_without_sic()
            if companies_without_sic > 0:
                validation_results['validation_errors'].append(f"Found {companies_without_sic} companies without SIC codes")
            
            self.logger.info(f"✅ Migration validation completed")
            self.logger.info(f"📊 Records: {validation_results['companies_count']} companies, "
                           f"{validation_results['sic_codes_count']} SIC codes, "
                           f"{validation_results['relationships_count']} relationships")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"❌ Validation failed: {e}")
            validation_results['validation_errors'].append(str(e))
            return validation_results
    
    def _get_table_count(self, table_name: str) -> int:
        """Get count of records in a table."""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.db.execute_query(query)
        return result[0]['count'] if result else 0
    
    def _check_orphaned_relationships(self) -> int:
        """Check for orphaned company-SIC relationships."""
        query = """
        SELECT COUNT(*) as count FROM company_sic_codes csc
        LEFT JOIN companies c ON csc.company_id = c.id
        LEFT JOIN sic_codes sc ON csc.sic_code_id = sc.id
        WHERE c.id IS NULL OR sc.id IS NULL
        """
        result = self.db.execute_query(query)
        return result[0]['count'] if result else 0
    
    def _check_companies_without_sic(self) -> int:
        """Check companies without any SIC code assignments."""
        query = """
        SELECT COUNT(*) as count FROM companies c
        LEFT JOIN company_sic_codes csc ON c.id = csc.company_id
        WHERE csc.id IS NULL
        """
        result = self.db.execute_query(query)
        return result[0]['count'] if result else 0


# Global data migrator instance
data_migrator = DataMigrator()