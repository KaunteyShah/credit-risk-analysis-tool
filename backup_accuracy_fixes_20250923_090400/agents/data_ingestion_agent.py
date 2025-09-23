"""
Data Ingestion Agent - Fetches data from Companies House and external sources.
"""
import sys
import os
from typing import Dict, Any, List, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.base_agent import BaseAgent, AgentResult
from app.utils.companies_house_client import companies_house_client, CompanyData
from app.utils.config_manager import config
from app.utils.logger import logger

class DataIngestionAgent(BaseAgent):
    """Agent responsible for ingesting data from various sources."""
    
    def __init__(self):
        super().__init__("DataIngestionAgent")
        self.ch_client = companies_house_client
        self.max_workers = config.get("processing.max_workers", 4)
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process data ingestion request.
        
        Args:
            data: Dictionary containing:
                - company_numbers: List of company numbers to fetch
                - search_queries: List of search queries for company discovery
                - include_filing_history: Boolean to include filing history
        
        Returns:
            AgentResult with ingested company data
        """
        try:
            self.log_activity("Starting data ingestion process")
            
            company_numbers = data.get("company_numbers", [])
            search_queries = data.get("search_queries", [])
            include_filing_history = data.get("include_filing_history", False)
            
            all_companies = []
            
            # Fetch companies by company numbers
            if company_numbers:
                companies_by_number = self._fetch_companies_by_numbers(company_numbers, include_filing_history)
                all_companies.extend(companies_by_number)
            
            # Search for companies by queries
            if search_queries:
                companies_by_search = self._search_companies(search_queries)
                all_companies.extend(companies_by_search)
            
            # Convert to DataFrame for easier processing
            df = self._convert_to_dataframe(all_companies)
            
            self.log_activity(f"Successfully ingested data for {len(all_companies)} companies")
            
            return self.create_result(
                success=True,
                data={
                    "companies": all_companies,
                    "dataframe": df,
                    "count": len(all_companies)
                },
                confidence=1.0,
                total_companies=len(all_companies),
                sources=["companies_house"]
            )
            
        except Exception as e:
            error_msg = f"Data ingestion failed: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
    
    def _fetch_companies_by_numbers(self, company_numbers: List[str], include_filing_history: bool = False) -> List[Dict[str, Any]]:
        """Fetch companies by their registration numbers."""
        companies = []
        
        def fetch_single_company(company_number: str) -> Optional[Dict[str, Any]]:
            try:
                company_data = self.ch_client.get_company_profile(company_number)
                if company_data:
                    result = self._company_data_to_dict(company_data)
                    
                    if include_filing_history:
                        filing_history = self.ch_client.get_company_filing_history(company_number)
                        result["filing_history"] = filing_history
                    
                    return result
            except Exception as e:
                self.log_activity(f"Error fetching company {company_number}: {str(e)}", "ERROR")
            return None
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_number = {
                executor.submit(fetch_single_company, num): num 
                for num in company_numbers
            }
            
            for future in as_completed(future_to_number):
                company_number = future_to_number[future]
                try:
                    result = future.result()
                    if result:
                        companies.append(result)
                except Exception as e:
                    self.log_activity(f"Error processing company {company_number}: {str(e)}", "ERROR")
        
        return companies
    
    def _search_companies(self, search_queries: List[str]) -> List[Dict[str, Any]]:
        """Search for companies using search queries."""
        companies = []
        
        for query in search_queries:
            try:
                search_results = self.ch_client.search_companies(query)
                for company_data in search_results:
                    companies.append(self._company_data_to_dict(company_data))
            except Exception as e:
                self.log_activity(f"Error searching for '{query}': {str(e)}", "ERROR")
        
        return companies
    
    def _company_data_to_dict(self, company_data: CompanyData) -> Dict[str, Any]:
        """Convert CompanyData object to dictionary."""
        return {
            "company_number": company_data.company_number,
            "company_name": company_data.company_name,
            "company_status": company_data.company_status,
            "company_type": company_data.company_type,
            "date_of_creation": company_data.date_of_creation,
            "sic_codes": company_data.sic_codes or [],
            "description": company_data.description,
            "turnover": company_data.turnover,
            "address": company_data.address or {},
            "officers": company_data.officers or []
        }
    
    def _convert_to_dataframe(self, companies: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert list of companies to pandas DataFrame."""
        if not companies:
            return pd.DataFrame()
        
        # Flatten the data for DataFrame
        flattened_data = []
        for company in companies:
            flat_company = company.copy()
            
            # Handle SIC codes
            flat_company["primary_sic_code"] = company["sic_codes"][0] if company["sic_codes"] else None
            flat_company["all_sic_codes"] = ",".join(company["sic_codes"]) if company["sic_codes"] else ""
            
            # Handle address
            address = company.get("address", {})
            flat_company["address_line1"] = address.get("address_line_1", "")
            flat_company["address_line2"] = address.get("address_line_2", "")
            flat_company["locality"] = address.get("locality", "")
            flat_company["postal_code"] = address.get("postal_code", "")
            flat_company["country"] = address.get("country", "")
            
            # Remove nested structures for DataFrame
            flat_company.pop("sic_codes", None)
            flat_company.pop("address", None)
            flat_company.pop("officers", None)
            
            flattened_data.append(flat_company)
        
        return pd.DataFrame(flattened_data)
    
    def fetch_sample_data(self, count: int = 10) -> AgentResult:
        """Fetch sample data for testing purposes."""
        try:
            # Use some well-known UK company numbers for testing
            sample_companies = [
                "00000006",  # MARKS AND SPENCER GROUP PLC
                "00000011",  # TESCO PLC  
                "00000013",  # SAINSBURY'S PLC
                "00000014",  # MORRISONS PLC
                "00000015",  # ASDA STORES LIMITED
            ]
            
            # Limit to requested count
            sample_companies = sample_companies[:count]
            
            data = {
                "company_numbers": sample_companies,
                "include_filing_history": False
            }
            
            return self.process(data)
            
        except Exception as e:
            error_msg = f"Failed to fetch sample data: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
