"""
Company Data Ingestion Node

LangGraph workflow node for intelligent company data retrieval and filing information.
Implements dual-methodology company lookup using existing Companies House client:
1. Direct company number lookup (when available)
2. Name + address search and filtering (fallback method)

Reuses existing infrastructure:
- CompaniesHouseClient.get_company_profile()
- CompaniesHouseClient.get_company_by_name_and_address() 
- FilingHistoryService for transaction_id retrieval
- SQLite repository integration
"""

import logging
from typing import Dict, Any, Optional, Tuple, cast
from datetime import datetime

from ..revenue_workflow_state import RevenueWorkflowState, CompanyFilingData, WorkflowDecision
from ....apis.companies_house_client import CompaniesHouseClient
from ....repositories.interfaces.filing_history_repository_interface import FilingHistoryRepositoryInterface
from ....utils.logger import get_logger

logger = get_logger(__name__)

class CompanyDataIngestionNode:
    """
    Intelligent company data ingestion with dual lookup methodology.
    
    Workflow Steps:
    1. Analyze input data to determine best lookup strategy
    2. Execute primary lookup method (company_number or name+address)
    3. Validate company identification confidence
    4. Fetch latest financial filing and transaction_id
    5. Store filing history if new data available
    
    Reuses Existing Components:
    - CompaniesHouseClient (90% existing methods)
    - FilingHistoryRepositoryInterface (100% existing logic)
    - Database integration (100% existing schemas)
    """
    
    def __init__(self, companies_house_client: Optional[CompaniesHouseClient] = None,
                 filing_service: Optional[FilingHistoryRepositoryInterface] = None):
        """
        Initialize with existing service dependencies.
        
        Args:
            companies_house_client: Existing CH client instance
            filing_service: Existing filing history repository
        """
        self.ch_client = companies_house_client or CompaniesHouseClient()
        self.filing_service = filing_service
        self.logger = logger.getChild(self.__class__.__name__)
        
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute company data ingestion workflow node.
        
        Args:
            state: Current revenue workflow state
            
        Returns:
            Updated workflow state with company and filing data
        """
        start_time = datetime.now()
        self.logger.info("🏢 Starting company data ingestion")
        
        try:
            # Extract company information from state
            self.logger.info(f"🔍 DEBUG: Input state keys: {list(state.keys())}")
            
            # Check both locations for compatibility with LangGraph and sequential workflows
            company_data = state.get('company_filing_data', {})
            if not company_data:
                # Sequential workflow format - data is at root level
                company_name = state.get('company_name', '')
                company_number = state.get('company_number')
                unique_id = state.get('unique_id', '')
                self.logger.info(f"🔍 DEBUG: Sequential format - name: {company_name}, number: {company_number}, unique_id: {unique_id}")
                
                # ✅ CRITICAL FIX: Initialize company_data with root state values for sequential workflow
                company_data = {
                    'company_name': company_name,
                    'company_number': company_number,
                    'unique_id': unique_id
                }
            else:
                # LangGraph workflow format - data is nested
                company_name = company_data.get('company_name', '')
                company_number = company_data.get('company_number')
                unique_id = company_data.get('unique_id', '')
                self.logger.info(f"🔍 DEBUG: LangGraph format - name: {company_name}, number: {company_number}, unique_id: {unique_id}")
            
            if not company_name:
                raise ValueError("Company name is required for data ingestion")
            
            # Determine and execute lookup strategy
            lookup_result = self._execute_dual_lookup_strategy(
                company_name, company_number, unique_id
            )
            
            # Update company filing data with lookup results
            updated_company_data = self._update_company_data(company_data, lookup_result)
            
            # DIRECT DATABASE LOOKUP for transaction_id - bypassing complex filing service
            company_number = updated_company_data.get('company_number')
            self.logger.info(f"🔍 DEBUG: updated_company_data keys: {list(updated_company_data.keys())}")
            self.logger.info(f"🔍 DEBUG: company_number from updated_company_data: {company_number}")
            if company_number:
                try:
                    from ....database.connection import DatabaseConnection
                    db_conn = DatabaseConnection()
                    
                    query = """
                    SELECT transaction_id, filing_date, category, description, unique_id, document_id
                    FROM company_filing_history_accounts 
                    WHERE company_registration_number = ? 
                    ORDER BY filing_date DESC 
                    LIMIT 1
                    """
                    
                    result = db_conn.execute_query(query, (company_number,))
                    if result and len(result) > 0:
                        row = result[0]
                        # Directly add transaction_id and document_id to updated_company_data
                        updated_company_data['transaction_id'] = row[0]
                        updated_company_data['filing_date'] = row[1]
                        updated_company_data['filing_category'] = row[2]
                        updated_company_data['filing_description'] = row[3]
                        updated_company_data['unique_id'] = row[4]
                        updated_company_data['document_id'] = row[5]  # ✅ CRITICAL FIX: Include document_id
                        
                        self.logger.info(f"✅ DIRECT DB: Found transaction_id {row[0]} and document_id {row[5]} for {company_name}")
                        
                        filing_result = {
                            'success': True,
                            'source': 'direct_database_lookup',
                            'transaction_id': row[0],
                            'filing_date': row[1],
                            'filing_category': row[2],
                            'filing_description': row[3]
                        }
                    else:
                        self.logger.warning(f"⚠️ DIRECT DB: No filing history found for company_number {company_number}")
                        filing_result = {'success': False, 'error': 'No filing history found'}
                        
                except Exception as db_error:
                    self.logger.error(f"❌ DIRECT DB: Database lookup failed: {str(db_error)}")
                    filing_result = {'success': False, 'error': str(db_error)}
            else:
                filing_result = {'success': False, 'error': 'No company number available'}
            
            # Merge filing information
            final_company_data = self._merge_filing_data(updated_company_data, filing_result)
            
            # Record workflow decision
            decision = {
                'decision_point': "company_data_ingestion",
                'decision_type': "routing",
                'decision_result': final_company_data.get('lookup_method', 'unknown'),
                'confidence': final_company_data.get('lookup_confidence', 0.0),
                'reasoning': f"Used {final_company_data.get('lookup_method')} lookup method",
                'timestamp': datetime.now().isoformat()
            }
            
            # Update workflow state
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create updated state safely
            updated_state = dict(state)
            updated_state['company_filing_data'] = final_company_data
            
            # ✅ CRITICAL FIX: Promote transaction_id and document_id to root state level
            # This ensures subsequent workflow nodes can access these essential identifiers
            if 'transaction_id' in final_company_data:
                updated_state['transaction_id'] = final_company_data['transaction_id']
                self.logger.info(f"🔄 Promoted transaction_id to root state: {final_company_data['transaction_id']}")
            
            # Also promote company identifiers for workflow consistency
            if 'company_number' in final_company_data:
                updated_state['company_number'] = final_company_data['company_number']
            if 'company_name' in final_company_data:
                updated_state['company_name'] = final_company_data['company_name']
            
            # Add document_id if available (though it should be generated from transaction_id)
            if 'document_id' in final_company_data:
                updated_state['document_id'] = final_company_data['document_id']
                self.logger.info(f"🔄 Promoted document_id to root state: {final_company_data['document_id']}")
            
            if 'workflow_decisions' not in updated_state:
                updated_state['workflow_decisions'] = []
            updated_state['workflow_decisions'].append(decision)
            
            if 'node_execution_times' not in updated_state:
                updated_state['node_execution_times'] = {}
            updated_state['node_execution_times']['company_data_ingestion'] = execution_time
            
            if 'node_confidence_scores' not in updated_state:
                updated_state['node_confidence_scores'] = {}
            updated_state['node_confidence_scores']['company_data_ingestion'] = final_company_data.get('lookup_confidence', 0.0)
            
            updated_state['current_node'] = 'financial_extraction'
            
            self.logger.info(f"✅ Company data ingestion completed in {execution_time:.2f}s")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ Company data ingestion failed: {str(e)}")
            
            # Add error to state safely
            updated_state = dict(state)
            if 'errors' not in updated_state:
                updated_state['errors'] = []
            updated_state['errors'].append(f"Company data ingestion failed: {str(e)}")
            updated_state['current_node'] = 'error_handling'
            
            execution_time = (datetime.now() - start_time).total_seconds()
            if 'node_execution_times' not in updated_state:
                updated_state['node_execution_times'] = {}
            updated_state['node_execution_times']['company_data_ingestion'] = execution_time
            
            return updated_state
    
    def _execute_dual_lookup_strategy(self, company_name: str, 
                                    company_number: Optional[str],
                                    unique_id: str) -> Dict[str, Any]:
        """
        Execute dual lookup methodology using existing CH client methods.
        
        Strategy:
        1. If company_number available → Direct lookup (Method 1)
        2. Otherwise → Name + address search and filtering (Method 2)
        
        Args:
            company_name: Company name for lookup
            company_number: Optional Companies House number
            unique_id: Database unique identifier
            
        Returns:
            Lookup result with company data and confidence score
        """
        if company_number:
            return self._lookup_by_company_number(company_number, unique_id)
        else:
            return self._lookup_by_name_and_address(company_name, unique_id)
    
    def _lookup_by_company_number(self, company_number: str, unique_id: str) -> Dict[str, Any]:
        """
        Method 1: Direct company number lookup (REUSE 100% existing method).
        
        Uses: CompaniesHouseClient.get_company_profile()
        """
        self.logger.info(f"🔍 Method 1: Looking up company by number: {company_number}")
        
        try:
            # Use existing method - handle both dictionary and CompanyData object returns
            result = self.ch_client.get_company_profile(company_number)
            
            # Handle CompanyData object (from utils client)
            if hasattr(result, 'company_number'):
                # CompanyData dataclass object - convert to our format
                sic_codes = getattr(result, 'sic_codes', []) or []
                company_data = {
                    'CompanyNumber': getattr(result, 'company_number', ''),
                    'CompanyName': getattr(result, 'company_name', ''),
                    'CompanyStatus': getattr(result, 'company_status', ''),
                    'CompanyType': getattr(result, 'company_type', ''),
                    'DateOfCreation': getattr(result, 'date_of_creation', ''),
                    'SICCode.SicText_1': sic_codes[0] if sic_codes and len(sic_codes) > 0 else '',
                    'unique_id': unique_id,
                    'data_source': 'companies_house_dataclass'
                }
                return {
                    'success': True,
                    'lookup_method': 'company_number',
                    'lookup_confidence': 0.95,
                    'company_data': company_data,
                    'validation_notes': ['Direct company number lookup successful (dataclass)']
                }
            
            # Handle dictionary response (from apis client)
            elif isinstance(result, dict) and result.get('success', False):
                company_data = result.get('data', {})
                # Ensure unique_id is included for database updates
                company_data['unique_id'] = unique_id
                return {
                    'success': True,
                    'lookup_method': 'company_number',
                    'lookup_confidence': 0.95,  # High confidence for direct lookup
                    'company_data': company_data,
                    'validation_notes': ['Direct company number lookup successful (dict)']
                }
            else:
                error_msg = 'Company number lookup failed'
                if isinstance(result, dict):
                    error_msg = result.get('error', error_msg)
                return {
                    'success': False,
                    'lookup_method': 'company_number',
                    'lookup_confidence': 0.0,
                    'error': error_msg,
                    'validation_notes': ['Company number lookup failed']
                }
                
        except Exception as e:
            self.logger.error(f"Company number lookup error: {str(e)}")
            return {
                'success': False,
                'lookup_method': 'company_number',
                'lookup_confidence': 0.0,
                'error': str(e),
                'validation_notes': ['Company number lookup exception']
            }
    
    def _lookup_by_name_and_address(self, company_name: str, unique_id: str) -> Dict[str, Any]:
        """
        Method 2: Name + address search and filtering (REUSE 90% existing method).
        
        Uses: CompaniesHouseClient.get_company_by_name_and_address()
        Note: Address matching will be implemented based on available data
        """
        self.logger.info(f"🔍 Method 2: Looking up company by name: {company_name}")
        
        try:
            # For now, we'll use name-only search
            # Address matching can be enhanced based on available address data
            result = self.ch_client.search_companies(company_name, items_per_page=10)
            
            if result.get('success', False) and result.get('data', {}).get('items'):
                companies = result.get('data', {}).get('items', [])
                
                # Find best match (can be enhanced with address matching)
                best_match = self._find_best_company_match(companies, company_name)
                
                if best_match:
                    return {
                        'success': True,
                        'lookup_method': 'name_address',
                        'lookup_confidence': best_match.get('confidence', 0.7),
                        'company_data': best_match.get('company_data', {}),
                        'validation_notes': [f"Found match with {best_match.get('confidence', 0):.0%} confidence"]
                    }
                else:
                    return {
                        'success': False,
                        'lookup_method': 'name_address',
                        'lookup_confidence': 0.0,
                        'error': 'No suitable company match found',
                        'validation_notes': ['No company match found in search results']
                    }
            else:
                return {
                    'success': False,
                    'lookup_method': 'name_address', 
                    'lookup_confidence': 0.0,
                    'error': 'Company search returned no results',
                    'validation_notes': ['Company search returned empty results']
                }
                
        except Exception as e:
            self.logger.error(f"Name/address lookup error: {str(e)}")
            return {
                'success': False,
                'lookup_method': 'name_address',
                'lookup_confidence': 0.0,
                'error': str(e),
                'validation_notes': ['Name/address lookup exception']
            }
    
    def _find_best_company_match(self, companies: list, target_name: str) -> Optional[Dict[str, Any]]:
        """
        Find best company match from search results.
        
        Can be enhanced with address matching and other criteria.
        """
        if not companies:
            return None
        
        # Simple name matching for now - can be enhanced
        target_lower = target_name.lower().strip()
        
        best_match = None
        best_confidence = 0.0
        
        for company in companies:
            company_name = company.get('title', '').lower().strip()
            
            # Simple confidence scoring (can be enhanced)
            if target_lower == company_name:
                confidence = 0.9  # Exact match
            elif target_lower in company_name or company_name in target_lower:
                confidence = 0.7  # Partial match
            else:
                confidence = 0.3  # Weak match
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = {
                    'confidence': confidence,
                    'company_data': company
                }
        
        return best_match if best_confidence >= 0.6 else None
    
    def _update_company_data(self, existing_data: Dict[str, Any], 
                           lookup_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update company data with lookup results."""
        updated_data = dict(existing_data)
        
        self.logger.info(f"🔍 DEBUG: lookup_result keys: {list(lookup_result.keys())}")
        self.logger.info(f"🔍 DEBUG: lookup_result success: {lookup_result.get('success')}")
        
        if lookup_result.get('success'):
            company_data = lookup_result.get('company_data', {})
            self.logger.info(f"🔍 DEBUG: company_data keys: {list(company_data.keys())}")
            
            # Use existing company_number from input, or from API response (both lowercase and API format)
            updated_data['company_number'] = (existing_data.get('company_number') or 
                                            company_data.get('company_number') or 
                                            company_data.get('CompanyNumber'))
            updated_data['company_name'] = (company_data.get('CompanyName') or 
                                          company_data.get('title') or 
                                          existing_data.get('company_name'))
            updated_data['company_address'] = company_data.get('address_snippet', existing_data.get('company_address'))
            updated_data['lookup_method'] = lookup_result.get('lookup_method')
            updated_data['lookup_confidence'] = lookup_result.get('lookup_confidence', 0.0)
            updated_data['api_response_raw'] = lookup_result
            
            self.logger.info(f"🔍 DEBUG: updated company_number: {updated_data.get('company_number')}")
        else:
            updated_data['lookup_method'] = lookup_result.get('lookup_method')
            updated_data['lookup_confidence'] = 0.0
            updated_data['api_response_raw'] = lookup_result
        
        return updated_data
    
    def _fetch_filing_information(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch latest account filing information with smart update logic.
        
        Strategy:
        1. Fetch filing metadata from Companies House API using company registration number
        2. Filter for account filing information specifically  
        3. Get the latest account filing's transaction_id
        4. Compare with our database - if same, use existing; if different, update records
        5. Return transaction_id for PDF document fetching
        
        This ensures we always have the most current filing data.
        """
        company_number = company_data.get('company_number')
        company_name = company_data.get('company_name', '')
        
        self.logger.info(f"🔍 FILING INFO: Starting account filing lookup for {company_name} (number: {company_number})")
        
        if not company_number:
            self.logger.warning(f"❌ FILING INFO: No company number available for {company_name}")
            return {
                'success': False,
                'error': 'No company number available for filing lookup'
            }
        
        try:
            # Step 1: Fetch filing metadata from Companies House API  
            self.logger.info(f"📊 Fetching latest account filing metadata from Companies House for {company_name}")
            
            filing_result = self.ch_client.get_company_filing_history(
                company_number, 
                items_per_page=50,  # Get more items to ensure we find account filings
                category="accounts"  # Filter for account filings only
            )
            
            if not filing_result or not filing_result.get('success'):
                error_msg = 'Filing lookup failed'
                if filing_result:
                    error_msg = filing_result.get('error', error_msg)
                self.logger.error(f"❌ Companies House API call failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Step 2: Extract account filings and get the latest one
            items = filing_result.get('data', {}).get('items', [])
            account_filings = [item for item in items if item.get('category') == 'accounts']
            
            if not account_filings:
                self.logger.warning(f"❌ No account filings found for {company_name}")
                return {
                    'success': False,
                    'error': 'No account filings found for this company'
                }
            
            latest_account_filing = account_filings[0]  # Items are sorted by date, latest first
            latest_transaction_id = latest_account_filing.get('transaction_id')
            
            self.logger.info(f"📋 Latest account filing transaction_id: {latest_transaction_id}")
            
            # Step 3: Compare with existing database record
            try:
                from ....database.connection import DatabaseConnection
                db_conn = DatabaseConnection()
                
                query = """
                SELECT transaction_id, filing_date 
                FROM company_filing_history_accounts 
                WHERE company_registration_number = ? 
                ORDER BY filing_date DESC 
                LIMIT 1
                """
                
                result = db_conn.execute_query(query, (company_number,))
                existing_transaction_id = None
                
                if result and len(result) > 0:
                    existing_transaction_id = result[0][0]
                    self.logger.info(f"📊 Existing transaction_id in database: {existing_transaction_id}")
                
                # Step 4: Compare and update if necessary
                if existing_transaction_id != latest_transaction_id:
                    self.logger.info(f"🔄 Transaction ID changed! Old: {existing_transaction_id}, New: {latest_transaction_id}")
                    
                    # Update or insert the database with new filing information
                    if existing_transaction_id:
                        # Update existing record
                        update_query = """
                        UPDATE company_filing_history_accounts 
                        SET transaction_id = ?, filing_date = ?, category = ?, description_text = ?
                        WHERE company_registration_number = ?
                        """
                        db_conn.execute_query(update_query, (
                            latest_transaction_id,
                            latest_account_filing.get('date'),
                            latest_account_filing.get('category'),
                            latest_account_filing.get('description'),
                            company_number
                        ))
                        self.logger.info(f"✅ Database record updated with latest filing metadata")
                    else:
                        # Insert new record (company not in database yet)
                        insert_query = """
                        INSERT INTO company_filing_history_accounts 
                        (company_name, company_registration_number, transaction_id, filing_date, category, description_text)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """
                        db_conn.execute_query(insert_query, (
                            company_name,
                            company_number,
                            latest_transaction_id,
                            latest_account_filing.get('date'),
                            latest_account_filing.get('category'),
                            latest_account_filing.get('description')
                        ))
                        self.logger.info(f"✅ New database record created with latest filing metadata")
                else:
                    self.logger.info(f"✅ Database is up to date, using existing transaction_id: {existing_transaction_id}")
                    
            except Exception as db_e:
                self.logger.warning(f"Database comparison failed: {str(db_e)}, proceeding with API data")
            
            # Step 5: Return the transaction_id for document fetching
            return {
                'success': True,
                'source': 'companies_house_api_accounts',
                'filing_data': latest_account_filing,
                'transaction_id': latest_transaction_id,
                'filing_date': latest_account_filing.get('date'),
                'filing_category': latest_account_filing.get('category'),
                'filing_description': latest_account_filing.get('description'),
                'raw_filing_response': filing_result,
                'updated_database': existing_transaction_id != latest_transaction_id
            }
                
        except Exception as e:
            self.logger.error(f"Filing information fetch error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _merge_filing_data(self, company_data: Dict[str, Any], 
                          filing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Merge filing information into company data."""
        merged_data = dict(company_data)
        
        if filing_result.get('success'):
            merged_data['transaction_id'] = filing_result.get('transaction_id')
            merged_data['filing_date'] = filing_result.get('filing_date')
            merged_data['filing_category'] = filing_result.get('filing_category')
            merged_data['filing_description'] = filing_result.get('filing_description')
            
            # Update API response to include filing data
            if 'api_response_raw' in merged_data and merged_data['api_response_raw']:
                if isinstance(merged_data['api_response_raw'], dict):
                    merged_data['api_response_raw']['filing_data'] = filing_result
        
        return merged_data