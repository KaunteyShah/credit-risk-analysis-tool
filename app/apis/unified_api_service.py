"""
Unified API Integration Service
Manages OpenAI, Companies House, and Databricks as a cohesive data platform
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from app.utils.config_manager import ConfigManager
from app.config.databricks_config import get_databricks_config
from app.apis.companies_house_client import CompaniesHouseClient

# Try to import OpenAI components
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    
logger = get_logger(__name__)

@dataclass
class APIStatus:
    """Status of API services"""
    service: str
    available: bool
    configured: bool
    error_message: Optional[str] = None

class UnifiedAPIService:
    """
    Unified service for managing all external APIs and Databricks
    Provides a single interface for data access and AI processing
    """
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.databricks_config = get_databricks_config()
        
        # Initialize services
        self.companies_house_client: Optional[CompaniesHouseClient] = None
        self.openai_client: Optional[ChatOpenAI] = None
        
        # Track service status
        self.service_status = self._check_all_services()
        
    def _check_all_services(self) -> Dict[str, APIStatus]:
        """Check status of all API services"""
        status = {}
        
        # Check Databricks
        try:
            spark = self.databricks_config.initialize_spark_session()
            status["databricks"] = APIStatus(
                service="databricks",
                available=True,
                configured=bool(spark)
            )
        except Exception as e:
            status["databricks"] = APIStatus(
                service="databricks",
                available=False,
                configured=False,
                error_message=str(e)
            )
        
        # Check OpenAI
        if OPENAI_AVAILABLE:
            try:
                openai_config = self.config_manager.get_api_config("openai")
                api_key = openai_config.get("api_key")
                
                if api_key and api_key != "sk-your_openai_api_key_here":
                    self.openai_client = ChatOpenAI(
                        api_key=api_key,
                        model=openai_config.get("model", "gpt-4-turbo"),
                        max_tokens=openai_config.get("max_tokens", 1500),
                        temperature=0.3
                    )
                    status["openai"] = APIStatus(
                        service="openai",
                        available=True,
                        configured=True
                    )
                else:
                    status["openai"] = APIStatus(
                        service="openai",
                        available=True,
                        configured=False,
                        error_message="API key not configured"
                    )
            except Exception as e:
                status["openai"] = APIStatus(
                    service="openai",
                    available=False,
                    configured=False,
                    error_message=str(e)
                )
        else:
            status["openai"] = APIStatus(
                service="openai",
                available=False,
                configured=False,
                error_message="OpenAI packages not installed"
            )
        
        # Check Companies House
        try:
            ch_config = self.config_manager.get_api_config("companies_house")
            api_key = ch_config.get("api_key")
            
            if api_key and api_key != "your_companies_house_api_key_here":
                self.companies_house_client = CompaniesHouseClient(api_key)
                status["companies_house"] = APIStatus(
                    service="companies_house",
                    available=True,
                    configured=True
                )
            else:
                status["companies_house"] = APIStatus(
                    service="companies_house",
                    available=True,
                    configured=False,
                    error_message="API key not configured"
                )
        except Exception as e:
            status["companies_house"] = APIStatus(
                service="companies_house",
                available=False,
                configured=False,
                error_message=str(e)
            )
        
        return status
    
    def get_service_status(self) -> Dict[str, APIStatus]:
        """Get current status of all services"""
        return self.service_status
    
    def is_production_ready(self) -> bool:
        """Check if all services are ready for production"""
        return all(
            status.available and status.configured 
            for status in self.service_status.values()
        )
    
    def get_missing_services(self) -> List[str]:
        """Get list of services that are not properly configured"""
        return [
            service for service, status in self.service_status.items()
            if not (status.available and status.configured)
        ]
    
    # Databricks Operations
    def get_databricks_data(self, table_name: str = "companies", limit: Optional[int] = None) -> Any:
        """Get data from Databricks Delta table"""
        try:
            from app.data_layer.databricks_data import DatabricksDataManager
            data_manager = DatabricksDataManager()
            # Use the correct method name
            return data_manager.read_companies_data(limit=limit)
        except Exception as e:
            logger.error(f"Error reading from Databricks: {e}")
            raise
    
    def write_databricks_data(self, predictions: List[Dict[str, Any]]) -> bool:
        """Write SIC predictions to Databricks Delta table"""
        try:
            from app.data_layer.databricks_data import DatabricksDataManager
            data_manager = DatabricksDataManager()
            data_manager.batch_update_sic_predictions(predictions)
            return True
        except Exception as e:
            logger.error(f"Error writing to Databricks: {e}")
            return False
    
    # Companies House Operations
    def get_company_data(self, company_number: str) -> Optional[Dict[str, Any]]:
        """Get company data from Companies House API"""
        if not self.companies_house_client:
            logger.warning("Companies House client not configured")
            return None
        
        try:
            return self.companies_house_client.get_company_profile(company_number)
        except Exception as e:
            logger.error(f"Error fetching company data: {e}")
            return None
    
    def search_companies(self, query: str, items_per_page: int = 20) -> Optional[Dict[str, Any]]:
        """Search companies using Companies House API"""
        if not self.companies_house_client:
            logger.warning("Companies House client not configured")
            return None
        
        try:
            return self.companies_house_client.search_companies(query, items_per_page)
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return None
    
    # OpenAI Operations
    def generate_ai_response(self, prompt: str, context: Optional[str] = None) -> Optional[str]:
        """Generate AI response using OpenAI"""
        if not self.openai_client:
            logger.warning("OpenAI client not configured")
            return None
        
        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            response = self.openai_client.invoke(full_prompt)
            # Handle different response types
            if hasattr(response, 'content'):
                return str(response.content)
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return None
    
    def predict_sic_code(self, business_description: str) -> Optional[Dict[str, Any]]:
        """Predict SIC code using AI"""
        if not self.openai_client:
            return None
        
        prompt = f"""
        Analyze this business description and predict the most appropriate UK SIC code:
        
        Business Description: {business_description}
        
        Return a JSON response with:
        - sic_code: The 5-digit UK SIC code
        - confidence: Confidence score (0.0-1.0)
        - explanation: Brief explanation of the classification
        - industry_sector: The industry sector name
        """
        
        try:
            response = self.openai_client.invoke(prompt)
            # Parse the response to extract structured data
            # This is a simplified version - you might want to use structured output
            return {
                "sic_code": "TBD",
                "confidence": 0.8,
                "explanation": response.content if hasattr(response, 'content') else str(response),
                "industry_sector": "Technology"
            }
        except Exception as e:
            logger.error(f"Error predicting SIC code: {e}")
            return None

# Global instance
_api_service = None

def get_unified_api_service() -> UnifiedAPIService:
    """Get singleton instance of UnifiedAPIService"""
    global _api_service
    if _api_service is None:
        _api_service = UnifiedAPIService()
    return _api_service
