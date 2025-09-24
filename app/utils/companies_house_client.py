"""
Companies House API client for fetching company data.
"""
import requests
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import sys
import os

# Add the parent directory to sys.path to import utils

from ..utils.config_manager import config
from ..utils.logger import logger
from app.utils.centralized_logging import get_logger
logger = get_logger(__name__)

@dataclass
class CompanyData:
    """Company data structure."""
    company_number: str
    company_name: str
    company_status: str
    company_type: str
    date_of_creation: Optional[str] = None
    sic_codes: Optional[List[str]] = None
    description: Optional[str] = None
    turnover: Optional[float] = None
    address: Optional[Dict[str, str]] = None
    officers: Optional[List[Dict[str, Any]]] = None

class CompaniesHouseClient:
    """Client for interacting with Companies House API."""
    
    def __init__(self):
        self.config = config.get_api_config("companies_house")
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get("base_url", "https://api.company-information.service.gov.uk")
        self.rate_limit = self.config.get("rate_limit", 600)
        
        if not self.api_key:
            logger.warning("Companies House API key not configured")
        
        self.session = requests.Session()
        self.session.auth = (self.api_key, '')
        self.last_request_time = 0
    
    def _rate_limit_check(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60 / (self.rate_limit / 5)  # 5-minute window
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_company_profile(self, company_number: str) -> Optional[CompanyData]:
        """
        Get company profile data from Companies House.
        
        Args:
            company_number: The company registration number
        
        Returns:
            CompanyData object or None if not found
        """
        try:
            self._rate_limit_check()
            
            url = f"{self.base_url}/company/{company_number}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_company_data(data)
            elif response.status_code == 404:
                logger.warning(f"Company {company_number} not found")
                return None
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching company {company_number}: {str(e)}")
            return None
    
    def search_companies(self, query: str, limit: int = 20) -> List[CompanyData]:
        """
        Search for companies by name or other criteria.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of CompanyData objects
        """
        try:
            self._rate_limit_check()
            
            url = f"{self.base_url}/search/companies"
            params = {"q": query, "items_per_page": limit}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                companies = []
                for item in data.get("items", []):
                    company_data = self._parse_search_result(item)
                    if company_data:
                        companies.append(company_data)
                return companies
            else:
                logger.error(f"Search API error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching companies: {str(e)}")
            return []
    
    def get_company_filing_history(self, company_number: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get company filing history.
        
        Args:
            company_number: The company registration number
            limit: Maximum number of filings to retrieve
        
        Returns:
            List of filing data
        """
        try:
            self._rate_limit_check()
            
            url = f"{self.base_url}/company/{company_number}/filing-history"
            params = {"items_per_page": limit}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            else:
                logger.error(f"Filing history API error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching filing history for {company_number}: {str(e)}")
            return []
    
    def _parse_company_data(self, data: Dict[str, Any]) -> CompanyData:
        """Parse API response into CompanyData object."""
        return CompanyData(
            company_number=data.get("company_number", ""),
            company_name=data.get("company_name", ""),
            company_status=data.get("company_status", ""),
            company_type=data.get("type", ""),
            date_of_creation=data.get("date_of_creation"),
            sic_codes=data.get("sic_codes", []),
            description=data.get("description"),
            address=data.get("registered_office_address", {})
        )
    
    def _parse_search_result(self, data: Dict[str, Any]) -> CompanyData:
        """Parse search result into CompanyData object."""
        return CompanyData(
            company_number=data.get("company_number", ""),
            company_name=data.get("title", ""),
            company_status=data.get("company_status", ""),
            company_type=data.get("company_type", ""),
            date_of_creation=data.get("date_of_creation"),
            description=data.get("description"),
            address=data.get("address", {})
        )

# Global client instance
companies_house_client = CompaniesHouseClient()
