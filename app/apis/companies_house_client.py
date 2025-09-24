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
from app.utils.logger import get_logger

# Set up logging
logger = get_logger(__name__)

@dataclass
class CompaniesHouseConfig:
    """Configuration for Companies House API"""
    api_key: str
    base_url: str = "https://api.companieshouse.gov.uk"
    rate_limit_delay: float = 0.6  # 600 requests per 5 minutes = 1 per 0.5s
    timeout: int = 30
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
        self.api_key = api_key or os.getenv('COMPANIES_HOUSE_API_KEY')
        if not self.api_key:
            # In production, we'll use mock client when API key is missing
            print("⚠️ Warning: Companies House API key not found. Some features will be limited.")
            self.api_key = None
            self.config = None
        else:
            self.config = CompaniesHouseConfig(api_key=self.api_key)
        
        self.session = requests.Session()
        if self.api_key:
            self.session.auth = (self.api_key, '')  # API key as username, empty password
        self.session.headers.update({
            'User-Agent': 'CreditRiskAnalyzer/2.0',
            'Accept': 'application/json'
        })
        
        self.last_request_time = 0
    
    def _rate_limit(self) -> None:
        """Implement rate limiting to respect API limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Companies House API"""
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
                    return {"error": f"API request failed: {str(e)}", "status_code": 500}
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
    
    def get_filing_history(self, company_number: str, items_per_page: int = 25) -> Dict[str, Any]:
        """
        Get company filing history
        
        Args:
            company_number: Companies House company number
            items_per_page: Number of filings to return
            
        Returns:
            Filing history data
        """
        endpoint = f"/company/{company_number}/filing-history"
        params = {"items_per_page": items_per_page}
        
        result = self._make_request(endpoint, params)
        
        if "error" not in result:
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": result["error"]}
    
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
    
    def get_enhanced_company_data(self, company_number: str) -> Dict[str, Any]:
        """
        Get comprehensive company data combining multiple API calls
        
        Args:
            company_number: Companies House company number
            
        Returns:
            Enhanced company data with profile, filings, and officers
        """
        results = {}
        
        # Get company profile
        profile_result = self.get_company_profile(company_number)
        if profile_result["success"]:
            results["profile"] = profile_result["data"]
        else:
            return {"success": False, "error": f"Failed to get company profile: {profile_result['error']}"}
        
        # Get filing history (last 10 filings)
        filing_result = self.get_filing_history(company_number, items_per_page=10)
        if filing_result["success"]:
            results["filing_history"] = filing_result["data"]
        
        # Get officers
        officers_result = self.get_officers(company_number, items_per_page=10)
        if officers_result["success"]:
            results["officers"] = officers_result["data"]
        
        return {"success": True, "data": results}

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
