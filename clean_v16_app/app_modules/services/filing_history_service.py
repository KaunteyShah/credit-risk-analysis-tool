"""
Service for managing Companies House filing history data integration
Coordinates between Companies House API client and filing history repository
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from app_modules.apis.companies_house_client import create_companies_house_client
from app_modules.repositories.implementations.file_based.sqlite_filing_history_repository import SQLiteFilingHistoryRepository
from app_modules.database.connection import DatabaseConnection
from app_modules.utils.logger import get_logger

logger = get_logger(__name__)


class FilingHistoryService:
    """Service for managing Companies House filing history operations"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.repository = SQLiteFilingHistoryRepository(db_connection)
        self.companies_house_client = create_companies_house_client()
        
    def fetch_and_store_latest_filing(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch latest filing from Companies House API and store in database
        
        Args:
            company_data: Company information with unique_id, company_number, company_name, etc.
            
        Returns:
            Result dictionary with success/error information
        """
        try:
            unique_id = company_data.get('unique_id')
            company_number = company_data.get('company_number')
            company_name = company_data.get('company_name', '')
            
            if not unique_id or not company_number:
                return {
                    'success': False,
                    'error': 'Missing required company identifiers (unique_id or company_number)'
                }
            
            logger.info(f"📄 Fetching latest filing for {company_name} ({company_number})")
            
            # Fetch latest financial filing from Companies House API
            api_result = self.companies_house_client.get_latest_financial_filing(company_number)
            
            if not api_result.get('success'):
                error_msg = api_result.get('error', 'Unknown API error')
                logger.warning(f"⚠️  API failed for {company_number}: {error_msg}")
                return {
                    'success': False,
                    'error': f'Companies House API failed: {error_msg}',
                    'company_number': company_number
                }
            
            # Extract filing data from API response
            api_data = api_result.get('data', {})
            latest_filing = api_data.get('latest_filing', {})
            
            if not latest_filing:
                logger.warning(f"⚠️  No filing data returned for {company_number}")
                return {
                    'success': False,
                    'error': 'No filing data available from Companies House',
                    'company_number': company_number
                }
            
            # Check if this filing already exists
            transaction_id = latest_filing.get('transaction_id')
            if transaction_id and self.repository.check_filing_exists(unique_id, transaction_id):
                logger.info(f"📋 Filing already exists for {company_number}: {transaction_id}")
                return {
                    'success': True,
                    'action': 'skipped_existing',
                    'transaction_id': transaction_id,
                    'company_number': company_number
                }
            
            # Prepare filing data for database insertion
            filing_data = {
                'unique_id': unique_id,
                'company_registration_number': company_number,
                'company_name': company_name,
                'company_address': self._extract_company_address(company_data),
                'filing_details': latest_filing,
                'raw_api_response': api_result
            }
            
            # Insert into database
            if self.repository.insert_filing_record(filing_data):
                logger.info(f"✅ Successfully stored filing for {company_number}: {transaction_id}")
                return {
                    'success': True,
                    'action': 'inserted',
                    'transaction_id': transaction_id,
                    'filing_date': latest_filing.get('date'),
                    'filing_category': latest_filing.get('category'),
                    'company_number': company_number
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to store filing in database',
                    'company_number': company_number
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing filing for {company_data.get('company_number', 'unknown')}: {e}")
            return {
                'success': False,
                'error': f'Processing error: {str(e)}',
                'company_number': company_data.get('company_number', 'unknown')
            }
    
    def process_companies_batch(self, companies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of companies for filing history updates
        
        Args:
            companies: List of company data dictionaries
            
        Returns:
            Batch processing results with statistics
        """
        results = {
            'total_processed': 0,
            'successful_inserts': 0,
            'skipped_existing': 0,
            'api_failures': 0,
            'database_failures': 0,
            'processing_errors': 0,
            'details': []
        }
        
        logger.info(f"📊 Processing {len(companies)} companies for filing history updates")
        
        for company in companies:
            company_number = company.get('company_number', 'unknown')
            
            try:
                result = self.fetch_and_store_latest_filing(company)
                results['total_processed'] += 1
                results['details'].append(result)
                
                if result['success']:
                    action = result.get('action', 'unknown')
                    if action == 'inserted':
                        results['successful_inserts'] += 1
                    elif action == 'skipped_existing':
                        results['skipped_existing'] += 1
                else:
                    error_msg = result.get('error', '')
                    if 'API failed' in error_msg:
                        results['api_failures'] += 1
                    elif 'database' in error_msg.lower():
                        results['database_failures'] += 1
                    else:
                        results['processing_errors'] += 1
                        
            except Exception as e:
                logger.error(f"❌ Batch processing error for {company_number}: {e}")
                results['total_processed'] += 1
                results['processing_errors'] += 1
                results['details'].append({
                    'success': False,
                    'error': f'Batch processing error: {str(e)}',
                    'company_number': company_number
                })
        
        # Log summary
        logger.info(f"📈 Batch processing complete:")
        logger.info(f"   Total: {results['total_processed']}")
        logger.info(f"   ✅ Inserted: {results['successful_inserts']}")
        logger.info(f"   📋 Skipped: {results['skipped_existing']}")
        logger.info(f"   ⚠️  API failures: {results['api_failures']}")
        logger.info(f"   💾 DB failures: {results['database_failures']}")
        logger.info(f"   ❌ Processing errors: {results['processing_errors']}")
        
        return results
    
    def get_company_filing_summary(self, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        Get filing summary for a specific company (for UI display)
        
        Args:
            unique_id: Company unique identifier
            
        Returns:
            Filing summary data or None
        """
        try:
            latest_filing = self.repository.get_latest_filing_by_unique_id(unique_id)
            
            if not latest_filing:
                return None
            
            return {
                'filing_date': latest_filing.get('filing_date'),
                'category': latest_filing.get('category'),
                'description': latest_filing.get('description'),
                'made_up_date': latest_filing.get('made_up_date'),
                'pages': latest_filing.get('pages'),
                'document_link': latest_filing.get('document_link'),
                'days_since_filing': self._calculate_days_since_filing(latest_filing.get('filing_date')),
                'compliance_status': self._assess_compliance_status(latest_filing.get('filing_date'))
            }
            
        except Exception as e:
            logger.error(f"Error getting filing summary for {unique_id}: {e}")
            return None
    
    def get_companies_needing_filing_updates(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        """
        Get companies that need filing history updates
        
        Args:
            days_threshold: Days since last check
            
        Returns:
            List of companies needing updates
        """
        return self.repository.get_companies_without_recent_filings(days_threshold)
    
    def _extract_company_address(self, company_data: Dict[str, Any]) -> str:
        """Extract and format company address from company data"""
        address_parts = [
            company_data.get('address_line_1', ''),
            company_data.get('city', ''),
            company_data.get('post_code', ''),
            company_data.get('country', '')
        ]
        
        # Filter out empty parts and join
        address = ', '.join([part for part in address_parts if part])
        return address if address else 'Address not available'
    
    def _calculate_days_since_filing(self, filing_date: str) -> Optional[int]:
        """Calculate days since filing date"""
        if not filing_date:
            return None
        
        try:
            filing_dt = datetime.strptime(filing_date, '%Y-%m-%d')
            current_dt = datetime.now()
            return (current_dt - filing_dt).days
        except Exception:
            return None
    
    def _assess_compliance_status(self, filing_date: str) -> str:
        """Assess compliance status based on filing date"""
        days_since = self._calculate_days_since_filing(filing_date)
        
        if days_since is None:
            return 'unknown'
        elif days_since <= 365:
            return 'good'
        elif days_since <= 548:  # 18 months - extended deadline
            return 'acceptable'
        else:
            return 'overdue'
    
    def get_filing_statistics(self) -> Dict[str, Any]:
        """Get overall filing statistics for monitoring"""
        try:
            all_filings = self.repository.get_all_latest_filings_for_portal()
            
            total_companies = len(all_filings)
            good_compliance = sum(1 for f in all_filings if self._assess_compliance_status(f.get('filing_date')) == 'good')
            acceptable_compliance = sum(1 for f in all_filings if self._assess_compliance_status(f.get('filing_date')) == 'acceptable')
            overdue_compliance = sum(1 for f in all_filings if self._assess_compliance_status(f.get('filing_date')) == 'overdue')
            
            return {
                'total_companies_with_filings': total_companies,
                'good_compliance': good_compliance,
                'acceptable_compliance': acceptable_compliance,
                'overdue_compliance': overdue_compliance,
                'compliance_percentage': (good_compliance / total_companies * 100) if total_companies > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting filing statistics: {e}")
            return {
                'total_companies_with_filings': 0,
                'good_compliance': 0,
                'acceptable_compliance': 0,
                'overdue_compliance': 0,
                'compliance_percentage': 0
            }