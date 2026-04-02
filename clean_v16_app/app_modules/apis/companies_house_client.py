"""
Companies House API Client - Phase 2 Integration

Real API integration for fetching live company data, replacing mock data
with actual company information from the official Companies House API.
"""
import os
import time
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from app_modules.utils.logger import get_logger
from app_modules.utils.config_manager import ConfigManager

# Set up logging
logger = get_logger(__name__)

@dataclass
class CompaniesHouseConfig:
    """Configuration for Companies House API"""
    api_key: str
    base_url: str = "https://api.companieshouse.gov.uk"
    rate_limit_delay: float = 0.6  # 600 requests per 5 minutes = 1 per 0.5s
    timeout: int = 15  # Reduced from 30s to prevent UI hangs
    max_retries: int = 3

class CompaniesHouseClient:
    """
    Real Companies House API client for Phase 2
    
    Provides methods to fetch:
    - Company profile information
    - Filing history
    - Officers information
    - Charges information
    - Company search results
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # Initialize config manager
        self.config_manager = ConfigManager()
        
        # Try to get API key from multiple sources
        if api_key:
            self.api_key = api_key
        else:
            # Try config manager first (includes Key Vault)
            try:
                ch_config = self.config_manager.get_api_config("companies_house")
                self.api_key = ch_config.get("api_key")
            except Exception:
                pass
                
            # Fallback to environment variable
            if not self.api_key:
                self.api_key = os.getenv('COMPANIES_HOUSE_API_KEY')
                
            # Final fallback to Key Vault function
            if not self.api_key:
                try:
                    from app_modules.utils.config_manager import get_secret_or_env
                    self.api_key = get_secret_or_env('COMPANIES_HOUSE_API_KEY')
                except ImportError:
                    pass
        
        if not self.api_key or self.api_key == "your_companies_house_api_key_here":
            # In production, we'll use mock client when API key is missing
            logger.warning("⚠️ Companies House API key not found. Some features will be limited.")
            self.api_key = None
            self.config = None
        else:
            self.config = CompaniesHouseConfig(api_key=self.api_key)
            logger.info("✅ Companies House API client initialized with real API key")
        
        self.session = requests.Session()
        if self.api_key:
            self.session.auth = (self.api_key, '')  # API key as username, empty password
        self.session.headers.update({
            'User-Agent': 'CreditRiskAnalyzer/2.0',
            'Accept': 'application/json'
        })
        
        self.last_request_time = 0
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
        if not self.config:
            return
            
        current_time = time.time()
        if hasattr(self, '_last_request_time'):
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.config.rate_limit_delay:
                time.sleep(self.config.rate_limit_delay - time_since_last)
        self._last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Companies House API"""
        if not self.config:
            return {"error": "API not configured", "status_code": 500}
            
        self._rate_limit()
        
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url, 
                    params=params,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return {"error": "Company not found", "status_code": 404}
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    time.sleep(2 ** attempt)
                    continue
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    logger.error(f"All {self.config.max_retries} API request attempts failed: {str(e)}")
                    return {"error": f"API request failed after {self.config.max_retries} attempts: {str(e)}", "status_code": 500}
                else:
                    logger.warning(f"API request attempt {attempt + 1} failed: {str(e)}, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                time.sleep(2 ** attempt)
        
        return {"error": "Max retries exceeded", "status_code": 500}
    
    def get_company_profile(self, company_number: str) -> Dict[str, Any]:
        """
        Get company profile information
        
        Args:
            company_number: Companies House company number
            
        Returns:
            Company profile data or error information
        """
        endpoint = f"/company/{company_number}"
        result = self._make_request(endpoint)
        
        if "error" not in result:
            # Transform to match our expected format
            transformed = self._transform_company_profile(result)
            return {"success": True, "data": transformed}
        else:
            return {"success": False, "error": result["error"]}
    
    def _transform_company_profile(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Companies House API data to our format"""
        sic_codes = api_data.get('sic_codes', [])
        
        return {
            "CompanyNumber": api_data.get('company_number', ''),
            "CompanyName": api_data.get('company_name', ''),
            "CompanyStatus": api_data.get('company_status', ''),
            "CompanyType": api_data.get('type', ''),
            "DateOfCreation": api_data.get('date_of_creation', ''),
            "RegisteredOfficeAddress": api_data.get('registered_office_address', {}),
            "SICCode.SicText_1": sic_codes[0] if sic_codes else '',
            "SICCode.SicText_2": sic_codes[1] if len(sic_codes) > 1 else '',
            "SICCode.SicText_3": sic_codes[2] if len(sic_codes) > 2 else '',
            "SICCode.SicText_4": sic_codes[3] if len(sic_codes) > 3 else '',
            "Accounts": api_data.get('accounts', {}),
            "Returns": api_data.get('annual_return', {}),
            "Mortgages": api_data.get('has_charges', False),
            "api_last_updated": datetime.now().isoformat(),
            "data_source": "companies_house_api"
        }
    
    def get_filing_history(self, company_number: str, items_per_page: int = 25, 
                          category: Optional[str] = None, start_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Get company filing history
        
        Args:
            company_number: Companies House company number
            items_per_page: Number of filings to return (max 100)
            category: Filter by filing categories (comma-separated). 
                     Examples: "accounts", "annual-return", "incorporation", "confirmation-statement"
            start_index: The index into the entire result set that this page starts
            
        Returns:
            Filing history data including items, total_count, and pagination info
        """
        endpoint = f"/company/{company_number}/filing-history"
        params = {"items_per_page": min(items_per_page, 100)}  # API max is 100
        
        if category:
            params["category"] = category
        if start_index is not None:
            params["start_index"] = start_index
        
        result = self._make_request(endpoint, params)
        
        if "error" not in result:
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": result["error"]}
    
    def get_company_filing_history(self, company_number: str, items_per_page: int = 25, 
                                  category: Optional[str] = None, start_index: Optional[int] = None) -> Dict[str, Any]:
        """Alias for get_filing_history for backwards compatibility with agents"""
        return self.get_filing_history(company_number, items_per_page, category, start_index)
    
    def get_officers(self, company_number: str, items_per_page: int = 35) -> Dict[str, Any]:
        """
        Get company officers information
        
        Args:
            company_number: Companies House company number
            items_per_page: Number of officers to return
            
        Returns:
            Officers data
        """
        endpoint = f"/company/{company_number}/officers"
        params = {"items_per_page": items_per_page}
        
        result = self._make_request(endpoint, params)
        
        if "error" not in result:
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": result["error"]}
    
    def search_companies(self, query: str, items_per_page: int = 20) -> Dict[str, Any]:
        """
        Search for companies by name
        
        Args:
            query: Search term
            items_per_page: Number of results to return
            
        Returns:
            Search results
        """
        endpoint = "/search/companies"
        params = {
            "q": query,
            "items_per_page": items_per_page
        }
        
        result = self._make_request(endpoint, params)
        
        if "error" not in result:
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": result["error"]}
    
    def get_latest_financial_filing(self, company_number: str) -> Dict[str, Any]:
        """
        Get the most recent financial filing (accounts or annual return) for credit risk analysis
        
        Args:
            company_number: Companies House company number
            
        Returns:
            Latest financial filing with full JSON structure
        """
        # Get just the latest financial filing
        result = self.get_filing_history(
            company_number, 
            items_per_page=1,  # Just get the most recent one
            category="accounts,annual-return"
        )
        
        if result["success"]:
            filings = result["data"].get("items", [])
            
            if filings:
                latest_filing = filings[0]
                return {
                    "success": True,
                    "data": {
                        "latest_filing": latest_filing,
                        "filing_type": latest_filing.get("category"),
                        "filing_date": latest_filing.get("date"),
                        "description": latest_filing.get("description"),
                        "raw_api_response": result["data"]  # Complete API response
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "No financial filings found for this company"
                }
        else:
            return {"success": False, "error": result["error"]}

    def get_financial_filings(self, company_number: str, items_per_page: int = 50) -> Dict[str, Any]:
        """
        Get financial filings (accounts and annual returns) for credit risk analysis
        
        Args:
            company_number: Companies House company number
            items_per_page: Number of filings to return (default 50 to get good history)
            
        Returns:
            Financial filing history focused on accounts and annual returns
        """
        # Get accounts and annual returns only
        result = self.get_filing_history(
            company_number, 
            items_per_page=items_per_page,
            category="accounts,annual-return"
        )
        
        if result["success"]:
            # Parse and categorize the filings
            filings = result["data"].get("items", [])
            
            accounts_filings = []
            annual_return_filings = []
            
            for filing in filings:
                if filing.get("category") == "accounts":
                    accounts_filings.append(filing)
                elif filing.get("category") == "annual-return":
                    annual_return_filings.append(filing)
            
            return {
                "success": True,
                "data": {
                    "total_financial_filings": len(filings),
                    "accounts_count": len(accounts_filings),
                    "annual_returns_count": len(annual_return_filings),
                    "accounts_filings": accounts_filings,
                    "annual_return_filings": annual_return_filings,
                    "raw_data": result["data"]  # Keep original response for reference
                }
            }
        else:
            return {"success": False, "error": result["error"]}

    def get_enhanced_company_data(self, company_number: str) -> Dict[str, Any]:
        """
        Get comprehensive company data combining multiple API calls
        
        Args:
            company_number: Companies House company number
            
        Returns:
            Enhanced company data with profile, financial filings, and officers
        """
        results = {}
        
        # Get company profile
        profile_result = self.get_company_profile(company_number)
        if profile_result["success"]:
            results["profile"] = profile_result["data"]
        else:
            return {"success": False, "error": f"Failed to get company profile: {profile_result['error']}"}
        
        # Get financial filings (accounts and annual returns only)
        financial_result = self.get_financial_filings(company_number, items_per_page=25)
        if financial_result["success"]:
            results["financial_filings"] = financial_result["data"]
        
        # Get officers
        officers_result = self.get_officers(company_number, items_per_page=10)
        if officers_result["success"]:
            results["officers"] = officers_result["data"]
        
        return {"success": True, "data": results}
    
    # Enhanced Methods for SIC Code Application
    def get_company_by_number(self, company_number: str) -> Optional[Dict[str, Any]]:
        """
        Get company data directly using company number - returns normalized format with fallback
        
        Args:
            company_number: Company registration number
            
        Returns:
            Company data with SIC codes in standard format, or None
        """
        try:
            raw_data = self.get_company_profile(company_number)
            # Check if API call was successful
            if raw_data.get("success"):
                normalized_data = self._normalize_company_data(raw_data)
                if normalized_data:
                    return normalized_data
            
            # Fallback to mock data for known companies when API fails
            logger.warning(f"API failed for company {company_number}, attempting fallback to mock data")
            return self._fallback_to_mock_data(company_number)
            
        except Exception as e:
            logger.error(f"Error fetching company by number {company_number}: {e}")
            # Fallback to mock data on exception
            logger.info(f"Attempting fallback to mock data for company {company_number}")
            return self._fallback_to_mock_data(company_number)
    
    def get_company_by_name_and_address(self, company_name: str, 
                                      address: Optional[str] = None,
                                      status: str = "active") -> Optional[Dict[str, Any]]:
        """
        Search by exact company name and status, filter by address if multiple results
        
        Args:
            company_name: Exact company name to search for
            address: Address to match if multiple companies found
            status: Company status (default: "active")
            
        Returns:
            Company data with SIC codes in standard format, or None
        """
        if not self.config:
            logger.warning("Companies House client not configured")
            return None
        
        try:
            # Search by exact company name using direct API call
            search_endpoint = "/search/companies"
            params = {"q": company_name}
            
            response_data = self._make_request(search_endpoint, params)
            
            if "error" in response_data:
                logger.error(f"Search API error: {response_data['error']}")
                return None
            
            # Filter by company status and exact name match
            matching_companies = []
            for item in response_data.get('items', []):
                # Check exact name match and status
                if (item.get('title', '').upper() == company_name.upper() and 
                    item.get('company_status') == status):
                    matching_companies.append(item)
            
            if not matching_companies:
                logger.warning(f"No companies found with exact name '{company_name}' and status '{status}'")
                return None
            
            # If only one company found, get full details
            if len(matching_companies) == 1:
                company_number = matching_companies[0].get('company_number')
                return self.get_company_by_number(company_number) if company_number else None
            
            # Multiple companies found - filter by address if provided
            if address and len(matching_companies) > 1:
                logger.info(f"Found {len(matching_companies)} companies with name '{company_name}', filtering by address")
                
                for company in matching_companies:
                    if self._address_matches(address, company):
                        company_number = company.get('company_number')
                        return self.get_company_by_number(company_number) if company_number else None
                
                logger.warning(f"No address match found among {len(matching_companies)} companies")
                return None
            
            # Multiple companies but no address provided - return first one
            logger.warning(f"Found {len(matching_companies)} companies, returning first match (no address filter)")
            company_number = matching_companies[0].get('company_number')
            return self.get_company_by_number(company_number) if company_number else None
            
        except Exception as e:
            logger.error(f"Error searching company by name: {e}")
            return None
    
    def _normalize_company_data(self, company_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize company data to standard format regardless of source (real API or mock)
        
        Args:
            company_data: Raw company data from either real API or mock client
            
        Returns:
            Normalized company data or None if invalid
        """
        if not company_data:
            return None
            
        # Handle the wrapper structure from our clients
        if company_data.get('success') and 'data' in company_data:
            actual_data = company_data['data']
        else:
            actual_data = company_data
            
        # If data is already in standard API format (real Companies House API)
        if 'company_name' in actual_data:
            return actual_data
            
        # If data is in our custom format (from mock or transformed API)
        if 'CompanyName' in actual_data:
            # Convert SIC codes from our custom format to standard format
            sic_codes = []
            for i in range(1, 5):
                sic_key = f'SICCode.SicText_{i}'
                if actual_data.get(sic_key):
                    sic_codes.append(actual_data[sic_key])
            
            # Convert to standard Companies House API format
            return {
                'company_name': actual_data.get('CompanyName'),
                'company_number': actual_data.get('CompanyNumber'),
                'company_status': actual_data.get('CompanyStatus'),
                'type': actual_data.get('CompanyType'),
                'date_of_creation': actual_data.get('DateOfCreation'),
                'registered_office_address': actual_data.get('RegisteredOfficeAddress', {}),
                'sic_codes': sic_codes,
                'accounts': actual_data.get('Accounts', {}),
                'data_source': actual_data.get('data_source', 'unknown')
            }
            
        return actual_data
    
    def _address_matches(self, database_address: str, search_result: Dict[str, Any]) -> bool:
        """
        Simple address matching - check if key components match
        
        Args:
            database_address: Address from your database
            search_result: Company search result from API
            
        Returns:
            True if addresses match, False otherwise
        """
        if not database_address:
            return False
        
        # Get address from search result
        api_address = search_result.get('address', {})
        address_snippet = search_result.get('address_snippet', '')
        
        # Combine address components
        api_components = [
            api_address.get('premises', ''),
            api_address.get('address_line_1', ''),
            api_address.get('locality', ''),
            api_address.get('postal_code', ''),
            address_snippet
        ]
        
        api_address_full = ' '.join([comp for comp in api_components if comp]).lower()
        database_address_lower = database_address.lower()
        
        # Simple matching - check if key components are present
        db_words = set(database_address_lower.split())
        api_words = set(api_address_full.split())
        
        # Count matching words (at least 2 should match for address matching)
        matching_words = len(db_words.intersection(api_words))
        return matching_words >= 2
    
    def _fallback_to_mock_data(self, company_number: str) -> Optional[Dict[str, Any]]:
        """
        Fallback to mock data when real API fails
        
        Args:
            company_number: Company registration number
            
        Returns:
            Mock company data or None if not available
        """
        # Create a temporary mock client for fallback
        mock_client = MockCompaniesHouseClient()
        
        # Known test companies that have mock data
        known_companies = {
            "07020023": "BDO SERVICES LIMITED",
            "02273744": "BDO PENSION TRUSTEES LIMITED"
        }
        
        if company_number in known_companies:
            logger.info(f"Using fallback mock data for {known_companies[company_number]} ({company_number})")
            try:
                mock_result = mock_client.get_company_by_number(company_number)
                if mock_result:
                    # Add fallback indicator to data source
                    mock_result['data_source'] = 'fallback_mock_api'
                    mock_result['fallback_reason'] = 'api_unavailable'
                return mock_result
            except Exception as e:
                logger.error(f"Even fallback mock data failed for {company_number}: {e}")
                
        logger.warning(f"No fallback mock data available for company {company_number}")
        return None

class MockCompaniesHouseClient:
    """
    Mock client for development without API key
    Returns realistic mock data for testing
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.mock_data = True
    
    def get_company_profile(self, company_number: str) -> Dict[str, Any]:
        """Mock company profile data"""
        mock_profile = {
            "CompanyNumber": company_number,
            "CompanyName": f"Mock Company {company_number}",
            "CompanyStatus": "active",
            "CompanyType": "ltd",
            "DateOfCreation": "2020-01-15",
            "RegisteredOfficeAddress": {
                "address_line_1": "123 Mock Street",
                "locality": "London",
                "postal_code": "SW1A 1AA"
            },
            "SICCode.SicText_1": "62012 - Business and domestic software development",
            "SICCode.SicText_2": "",
            "SICCode.SicText_3": "",
            "SICCode.SicText_4": "",
            "Accounts": {"next_due": "2024-12-31"},
            "Returns": {"next_due": "2024-11-30"},
            "Mortgages": False,
            "api_last_updated": datetime.now().isoformat(),
            "data_source": "mock_api"
        }
        
        return {"success": True, "data": mock_profile}
    
    def get_enhanced_company_data(self, company_number: str) -> Dict[str, Any]:
        """Mock enhanced company data"""
        profile_result = self.get_company_profile(company_number)
        
        return {
            "success": True,
            "data": {
                "profile": profile_result["data"],
                "filing_history": {"items": []},
                "officers": {"items": []}
            }
        }
    
    # Enhanced Methods for SIC Code Application (Mock versions)
    def get_company_by_number(self, company_number: str) -> Optional[Dict[str, Any]]:
        """Mock version of get_company_by_number - returns normalized format"""
        try:
            raw_data = self.get_company_profile(company_number)
            return self._normalize_company_data(raw_data)
        except Exception as e:
            logger.error(f"Mock error fetching company by number {company_number}: {e}")
            return None
    
    def get_company_by_name_and_address(self, company_name: str, 
                                      address: Optional[str] = None,
                                      status: str = "active") -> Optional[Dict[str, Any]]:
        """Mock version - return mock data for known company names"""
        # Mock data for testing
        if "BDO SERVICES" in company_name.upper():
            return self.get_company_by_number("07020023")
        elif "BDO PENSION" in company_name.upper():
            return self.get_company_by_number("02273744")
        else:
            logger.warning(f"Mock client: No data for company '{company_name}'")
            return None
    
    def _normalize_company_data(self, company_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize mock company data to standard format"""
        if not company_data:
            return None
            
        # Handle the wrapper structure
        if company_data.get('success') and 'data' in company_data:
            actual_data = company_data['data']
        else:
            actual_data = company_data
            
        # Convert from mock format to standard format
        if 'CompanyName' in actual_data:
            # Extract SIC codes from mock format
            sic_codes = []
            sic_text = actual_data.get('SICCode.SicText_1', '')
            if sic_text:
                # Extract just the SIC code number from "62012 - Description"
                sic_code = sic_text.split(' - ')[0].strip()
                if sic_code:
                    sic_codes.append(sic_code)
            
            # Convert to standard format
            return {
                'company_name': actual_data.get('CompanyName'),
                'company_number': actual_data.get('CompanyNumber'),
                'company_status': actual_data.get('CompanyStatus'),
                'type': actual_data.get('CompanyType'),
                'date_of_creation': actual_data.get('DateOfCreation'),
                'registered_office_address': actual_data.get('RegisteredOfficeAddress', {}),
                'sic_codes': sic_codes,
                'accounts': actual_data.get('Accounts', {}),
                'data_source': 'mock_api'
            }
            
        return actual_data
    
    def _address_matches(self, database_address: str, search_result: Dict[str, Any]) -> bool:
        """Mock address matching - always return True for simplicity"""
        return True
    
    def get_latest_financial_filing(self, company_number: str) -> Dict[str, Any]:
        """Mock latest financial filing - return the most recent one"""
        latest_mock_filing = {
            "category": "accounts",
            "date": "2024-01-15",
            "description": "Annual accounts made up to 31 December 2023",
            "type": "AA",
            "barcode": "X9ABC123",
            "transaction_id": "MzAyNDQyOTc5N2FkaXF6a2N4",
            "action_date": "2024-01-15",
            "paper_filed": False,
            "links": {
                "self": f"/company/{company_number}/filing-history/MzAyNDQyOTc5N2FkaXF6a2N4",
                "document_metadata": f"https://frontend-doc-api.companieshouse.gov.uk/document/X9ABC123/content"
            }
        }
        
        return {
            "success": True,
            "data": {
                "latest_filing": latest_mock_filing,
                "filing_type": latest_mock_filing.get("category"),
                "filing_date": latest_mock_filing.get("date"),
                "description": latest_mock_filing.get("description"),
                "raw_api_response": {
                    "items_per_page": 1,
                    "start_index": 0,
                    "total_count": 1,
                    "items": [latest_mock_filing]
                }
            }
        }

    def get_financial_filings(self, company_number: str, items_per_page: int = 50) -> Dict[str, Any]:
        """Mock financial filings - return realistic accounts and annual returns"""
        mock_financial_items = [
            {
                "category": "accounts",
                "date": "2024-01-15",
                "description": "Annual accounts made up to 31 December 2023",
                "type": "AA",
                "barcode": "X9ABC123",
                "transaction_id": "MzAyNDQyOTc5N2FkaXF6a2N4"
            },
            {
                "category": "annual-return",
                "date": "2023-06-15", 
                "description": "Annual return made up to 15 June 2023",
                "type": "AR01",
                "barcode": "X8DEF456", 
                "transaction_id": "MzAxNDQyOTc5N2FkaXF6a2N4"
            },
            {
                "category": "accounts",
                "date": "2023-01-20",
                "description": "Annual accounts made up to 31 December 2022", 
                "type": "AA",
                "barcode": "X7GHI789",
                "transaction_id": "MzAwNDQyOTc5N2FkaXF6a2N4"
            },
            {
                "category": "annual-return",
                "date": "2022-06-15",
                "description": "Annual return made up to 15 June 2022",
                "type": "AR01", 
                "barcode": "X6JKL012",
                "transaction_id": "MzAwNDQyOTc5N2FkaXF6a2N4"
            }
        ]
        
        accounts_filings = [f for f in mock_financial_items if f["category"] == "accounts"]
        annual_return_filings = [f for f in mock_financial_items if f["category"] == "annual-return"]
        
        return {
            "success": True,
            "data": {
                "total_financial_filings": len(mock_financial_items),
                "accounts_count": len(accounts_filings),
                "annual_returns_count": len(annual_return_filings),
                "accounts_filings": accounts_filings,
                "annual_return_filings": annual_return_filings,
                "raw_data": {
                    "items_per_page": items_per_page,
                    "total_count": len(mock_financial_items),
                    "items": mock_financial_items
                }
            }
        }

    def get_company_filing_history(self, company_number: str, items_per_page: int = 25, 
                                  category: Optional[str] = None, start_index: Optional[int] = None) -> Dict[str, Any]:
        """Mock filing history - return realistic mock data"""
        mock_items = [
            {
                "category": "accounts",
                "date": "2023-12-31",
                "description": "Annual accounts made up to 31 December 2023",
                "type": "AA",
                "barcode": "X9ABC123",
                "transaction_id": "MzAyNDQyOTc5N2FkaXF6a2N4"
            },
            {
                "category": "confirmation-statement", 
                "date": "2023-06-15",
                "description": "Confirmation statement made on 15 June 2023",
                "type": "CS01",
                "barcode": "X8DEF456",
                "transaction_id": "MzAxNDQyOTc5N2FkaXF6a2N4"
            }
        ] if not category else [item for item in mock_items if item["category"] == category]
        
        start_idx = start_index or 0
        end_idx = start_idx + items_per_page
        
        return {
            "success": True,
            "data": {
                "items_per_page": items_per_page,
                "start_index": start_idx,
                "total_count": len(mock_items),
                "items": mock_items[start_idx:end_idx]
            }
        }
    
    def search_companies(self, query: str, items_per_page: int = 20) -> Dict[str, Any]:
        """Mock company search - return mock results for known queries"""
        mock_items = []
        
        # Return mock data for specific queries
        if "BDO" in query.upper():
            mock_items = [
                {
                    "company_number": "07020023",
                    "title": "BDO SERVICES LIMITED",
                    "company_status": "active",
                    "address_snippet": "55 Baker Street, London, W1U 7EU"
                },
                {
                    "company_number": "02273744", 
                    "title": "BDO PENSION TRUSTEES LIMITED",
                    "company_status": "active",
                    "address_snippet": "55 Baker Street, London, W1U 7EU"
                }
            ]
        
        return {
            "success": True,
            "data": {
                "items_per_page": items_per_page,
                "total_results": len(mock_items),
                "items": mock_items
            }
        }

# Factory function to create appropriate client
def create_companies_house_client(api_key: Optional[str] = None):
    """
    Create Companies House client - real or mock based on API key availability
    
    Args:
        api_key: Optional API key, will check environment if not provided
        
    Returns:
        CompaniesHouseClient or MockCompaniesHouseClient
    """
    api_key = api_key or os.getenv('COMPANIES_HOUSE_API_KEY')
    
    if api_key:
        return CompaniesHouseClient(api_key)
    else:
        logger.warning("No Companies House API key found. Using mock client.")
        return MockCompaniesHouseClient()

# Example usage
if __name__ == "__main__":
    # Test the client
    client = create_companies_house_client()
    
    # Test with a real company number
    test_company = "09876543"  # Replace with actual company number
    
    result = client.get_enhanced_company_data(test_company)
    
    if result["success"]:
        logger.info("Company data retrieved successfully")
        logger.debug(json.dumps(result["data"]["profile"], indent=2))
    else:
        logger.error(f"Error: {result['error']}")
