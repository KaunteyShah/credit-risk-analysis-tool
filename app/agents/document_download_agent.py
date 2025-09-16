"""
Document Download Agent - Downloads annual accounts and filing documents from Companies House.
"""
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import requests
from datetime import datetime
import hashlib

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.base_agent import BaseAgent, AgentResult
from app.utils.companies_house_client import companies_house_client
from app.utils.config_manager import config
from app.utils.logger import logger

@dataclass
class DocumentInfo:
    """Document information structure."""
    document_id: str
    document_type: str
    filing_date: str
    period_end_on: Optional[str]
    period_start_on: Optional[str]
    description: str
    category: str
    subcategory: str
    made_up_date: Optional[str]

@dataclass
class DownloadedDocument:
    """Downloaded document structure."""
    document_info: DocumentInfo
    content: bytes
    file_size: int
    download_timestamp: datetime
    content_hash: str

class DocumentDownloadAgent(BaseAgent):
    """Agent responsible for downloading company documents from Companies House."""
    
    def __init__(self):
        super().__init__("DocumentDownloadAgent")
        self.ch_client = companies_house_client
        self.cache_enabled = config.get("processing.enable_document_cache", True)
        self.cache_directory = config.get("processing.document_cache_dir", "data/documents")
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_directory, exist_ok=True)
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process document download request.
        
        Args:
            data: Dictionary containing:
                - company_numbers: List of company numbers
                - company_names: List of company names  
                - document_types: List of document types to download
                - latest_only: Boolean to get only latest documents
        
        Returns:
            AgentResult with downloaded documents
        """
        try:
            self.log_activity("Starting document download process")
            
            company_numbers = data.get("company_numbers", [])
            company_names = data.get("company_names", [])
            document_types = data.get("document_types", ["annual-accounts"])
            latest_only = data.get("latest_only", True)
            
            # Convert company names to numbers if needed
            if company_names and not company_numbers:
                company_numbers = self._resolve_company_names(company_names)
            
            downloaded_documents = []
            
            for company_number in company_numbers:
                try:
                    docs = self._download_company_documents(
                        company_number, document_types, latest_only
                    )
                    downloaded_documents.extend(docs)
                except Exception as e:
                    self.log_activity(f"Error downloading documents for {company_number}: {str(e)}", "ERROR")
            
            self.log_activity(f"Successfully downloaded {len(downloaded_documents)} documents")
            
            return self.create_result(
                success=True,
                data={
                    "documents": downloaded_documents,
                    "count": len(downloaded_documents),
                    "cache_enabled": self.cache_enabled
                },
                confidence=1.0,
                document_count=len(downloaded_documents)
            )
            
        except Exception as e:
            error_msg = f"Document download failed: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
    
    def download_latest_annual_accounts(self, company_identifier: str) -> Optional[DownloadedDocument]:
        """
        Download the latest annual accounts for a company.
        
        Args:
            company_identifier: Company number or name
        
        Returns:
            DownloadedDocument or None if not found
        """
        try:
            # Resolve company name to number if needed
            company_number = company_identifier
            if not company_identifier.isdigit():
                company_numbers = self._resolve_company_names([company_identifier])
                if not company_numbers:
                    return None
                company_number = company_numbers[0]
            
            # Get filing history to find annual accounts
            filing_history = self.ch_client.get_company_filing_history(company_number, limit=50)
            
            # Find latest annual accounts filing
            annual_accounts_filing = None
            for filing in filing_history:
                if self._is_annual_accounts_filing(filing):
                    annual_accounts_filing = filing
                    break
            
            if not annual_accounts_filing:
                self.log_activity(f"No annual accounts found for company {company_number}", "WARNING")
                return None
            
            # Download the document
            document_info = self._parse_filing_to_document_info(annual_accounts_filing)
            document_content = self._download_document_content(document_info.document_id)
            
            if document_content:
                return DownloadedDocument(
                    document_info=document_info,
                    content=document_content,
                    file_size=len(document_content),
                    download_timestamp=datetime.now(),
                    content_hash=hashlib.md5(document_content).hexdigest()
                )
            
            return None
            
        except Exception as e:
            self.log_activity(f"Error downloading annual accounts for {company_identifier}: {str(e)}", "ERROR")
            return None
    
    def _resolve_company_names(self, company_names: List[str]) -> List[str]:
        """Resolve company names to company numbers using search."""
        company_numbers = []
        
        for name in company_names:
            try:
                search_results = self.ch_client.search_companies(name, limit=5)
                if search_results:
                    # Take the first exact or closest match
                    best_match = search_results[0]
                    company_numbers.append(best_match.company_number)
                    self.log_activity(f"Resolved '{name}' to company number {best_match.company_number}")
                else:
                    self.log_activity(f"Could not resolve company name: {name}", "WARNING")
            except Exception as e:
                self.log_activity(f"Error resolving company name '{name}': {str(e)}", "ERROR")
        
        return company_numbers
    
    def _download_company_documents(self, company_number: str, document_types: List[str], latest_only: bool) -> List[DownloadedDocument]:
        """Download documents for a specific company."""
        documents = []
        
        try:
            # Get filing history
            filing_history = self.ch_client.get_company_filing_history(company_number, limit=100)
            
            # Filter filings by document types
            relevant_filings = []
            for filing in filing_history:
                if any(doc_type in filing.get("category", "").lower() for doc_type in document_types):
                    relevant_filings.append(filing)
                    if latest_only:
                        break  # Only get the latest
            
            # Download each relevant filing
            for filing in relevant_filings:
                try:
                    document_info = self._parse_filing_to_document_info(filing)
                    
                    # Check cache first
                    cached_content = self._get_cached_document(document_info.document_id)
                    if cached_content:
                        documents.append(DownloadedDocument(
                            document_info=document_info,
                            content=cached_content,
                            file_size=len(cached_content),
                            download_timestamp=datetime.now(),
                            content_hash=hashlib.md5(cached_content).hexdigest()
                        ))
                        continue
                    
                    # Download from API
                    content = self._download_document_content(document_info.document_id)
                    if content:
                        # Cache the document
                        if self.cache_enabled:
                            self._cache_document(document_info.document_id, content)
                        
                        documents.append(DownloadedDocument(
                            document_info=document_info,
                            content=content,
                            file_size=len(content),
                            download_timestamp=datetime.now(),
                            content_hash=hashlib.md5(content).hexdigest()
                        ))
                
                except Exception as e:
                    self.log_activity(f"Error downloading document {filing.get('transaction_id', 'unknown')}: {str(e)}", "ERROR")
        
        except Exception as e:
            self.log_activity(f"Error getting filing history for {company_number}: {str(e)}", "ERROR")
        
        return documents
    
    def _download_document_content(self, document_id: str) -> Optional[bytes]:
        """Download document content from Companies House API."""
        try:
            # Rate limiting check
            self.ch_client._rate_limit_check()
            
            url = f"{self.ch_client.base_url}/document/{document_id}/content"
            response = self.ch_client.session.get(url, stream=True)
            
            if response.status_code == 200:
                content = response.content
                self.log_activity(f"Downloaded document {document_id} ({len(content)} bytes)")
                return content
            else:
                self.log_activity(f"Failed to download document {document_id}: {response.status_code}", "ERROR")
                return None
                
        except Exception as e:
            self.log_activity(f"Error downloading document {document_id}: {str(e)}", "ERROR")
            return None
    
    def _parse_filing_to_document_info(self, filing: Dict[str, Any]) -> DocumentInfo:
        """Parse filing data to DocumentInfo object."""
        return DocumentInfo(
            document_id=filing.get("links", {}).get("document_metadata", "").split("/")[-1],
            document_type=filing.get("type", ""),
            filing_date=filing.get("date", ""),
            period_end_on=filing.get("period_end_on"),
            period_start_on=filing.get("period_start_on"),
            description=filing.get("description", ""),
            category=filing.get("category", ""),
            subcategory=filing.get("subcategory", ""),
            made_up_date=filing.get("made_up_date")
        )
    
    def _is_annual_accounts_filing(self, filing: Dict[str, Any]) -> bool:
        """Check if a filing is an annual accounts document."""
        category = filing.get("category", "").lower()
        description = filing.get("description", "").lower()
        
        return (
            "accounts" in category or
            "annual return" in description or
            "aa" in filing.get("type", "").lower()
        )
    
    def _get_cached_document(self, document_id: str) -> Optional[bytes]:
        """Get document from cache if available."""
        if not self.cache_enabled:
            return None
        
        cache_file = os.path.join(self.cache_directory, f"{document_id}.pdf")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                self.log_activity(f"Error reading cached document {document_id}: {str(e)}", "ERROR")
        
        return None
    
    def _cache_document(self, document_id: str, content: bytes) -> None:
        """Cache document content to disk."""
        if not self.cache_enabled:
            return
        
        try:
            cache_file = os.path.join(self.cache_directory, f"{document_id}.pdf")
            with open(cache_file, 'wb') as f:
                f.write(content)
            self.log_activity(f"Cached document {document_id}")
        except Exception as e:
            self.log_activity(f"Error caching document {document_id}: {str(e)}", "ERROR")
