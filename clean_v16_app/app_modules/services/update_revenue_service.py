"""
Service for agentic revenue extraction workflow
Bridges the agentic revenue extraction system with the Flask API
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from app_modules.utils.logger import get_logger

# Import agentic components
try:
    from app_modules.agentic.update_revenue.revenue_agentic_service import AgenticRevenueService
    from app_modules.database.connection import DatabaseConnection
    from app_modules.repositories.implementations.file_based.sqlite_filing_history_repository import SQLiteFilingHistoryRepository
    AGENTIC_COMPONENTS_AVAILABLE = True
except ImportError as e:
    AGENTIC_COMPONENTS_AVAILABLE = False
    import traceback
    traceback.print_exc()

logger = get_logger(__name__)


class UpdateRevenueService:
    """Service layer bridge for agentic revenue extraction workflow"""
    
    def __init__(self, container=None):
        """Initialize the service with dependency injection container"""
        self.container = container
        self._agentic_service = None
        self._filing_repository = None
        
        # Initialize components if available
        if AGENTIC_COMPONENTS_AVAILABLE:
            try:
                # Initialize database connection
                db_connection = DatabaseConnection()
                
                # Initialize filing repository
                self._filing_repository = SQLiteFilingHistoryRepository(db_connection)
                
                # Initialize required services for agentic workflow
                from app_modules.apis.companies_house_client import CompaniesHouseClient
                
                # Initialize agentic service with services container
                services_container = {
                    'database_connection': db_connection,
                    'filing_repository': self._filing_repository,
                    'filing_history_repository': self._filing_repository,  # Same as filing_repository
                    'companies_house_client': CompaniesHouseClient(),
                    # Optional/Mock services - these can be None for pure RAG approach
                    'document_download_agent': None,
                    'rag_document_agent': None,
                    'smart_financial_extraction_agent': None,
                    'turnover_estimation_agent': None
                }
                self._agentic_service = AgenticRevenueService(services_container)
                
                logger.info("✅ UpdateRevenueService initialized with agentic components")
            except Exception as e:
                logger.error(f"❌ Failed to initialize agentic components: {e}")
                logger.exception("Full error details:")
                self._agentic_service = None
        else:
            logger.warning("⚠️ Agentic components not available - service will return mock responses")
    
    def update_revenue_agentic(self, 
                                company_name: str, 
                                company_number: Optional[str] = None,
                                transaction_id: str = '',
                                progress_callback: Optional[Callable[[str, float], None]] = None) -> Dict[str, Any]:
        """
        Execute agentic revenue extraction workflow for a company
        
        Args:
            company_name: Name of the company
            company_number: Optional company registration number
            transaction_id: Optional Companies House transaction ID for direct document access
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dict containing workflow results and extracted revenue data
        """
        start_time = datetime.now()
        
        try:
            if not AGENTIC_COMPONENTS_AVAILABLE or not self._agentic_service:
                return self._mock_agentic_response(company_name, company_number)
            
            # Default progress callback if not provided
            if progress_callback is None:
                progress_callback = self._default_progress_callback
            
            # Create wrapper to convert dict callback to (str, float) format
            def wrapped_progress_callback(progress_data):
                if isinstance(progress_data, dict):
                    message = progress_data.get('message', 'Processing...')
                    percentage = progress_data.get('progress', 0)
                    progress_callback(message, percentage)
                else:
                    progress_callback(str(progress_data), 0)
            
            logger.info(f"🚀 Starting agentic revenue extraction for: {company_name}")
            
            # Execute the agentic workflow
            result = self._agentic_service.extract_revenue_agentic(
                company_name=company_name,
                company_number=company_number or "",
                transaction_id=transaction_id or "",
                progress_callback=wrapped_progress_callback
            )
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Enhance result with service metadata
            enhanced_result = {
                **result,
                "service_metadata": {
                    "execution_time_seconds": execution_time,
                    "service_version": "1.0.0",
                    "timestamp": datetime.now().isoformat(),
                    "agentic_components_available": True
                }
            }
            
            logger.info(f"✅ Agentic revenue extraction completed in {execution_time:.2f}s")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"❌ Agentic revenue extraction failed: {e}")
            import traceback
            traceback.print_exc()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": False,
                "error": str(e),
                "company_name": company_name,
                "company_number": company_number,
                "service_metadata": {
                    "execution_time_seconds": execution_time,
                    "service_version": "1.0.0",
                    "timestamp": datetime.now().isoformat(),
                    "agentic_components_available": AGENTIC_COMPONENTS_AVAILABLE
                }
            }
    
    def update_revenue_agentic_sync(self, 
                                  company_name: str, 
                                  company_number: Optional[str] = None,
                                  progress_callback: Optional[Callable[[str, float], None]] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for agentic revenue extraction (now just an alias)
        
        Args:
            company_name: Name of the company
            company_number: Optional company registration number
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dict containing workflow results and extracted revenue data
        """
        # Since the main method is now synchronous, just call it directly
        return self.update_revenue_agentic(
            company_name=company_name,
            company_number=company_number,
            progress_callback=progress_callback
        )
    
    def get_filing_history(self, company_unique_id: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get filing history for a company
        
        Args:
            company_unique_id: Unique identifier for the company
            limit: Maximum number of records to return
            
        Returns:
            Filing history data or None if not available
        """
        try:
            if not self._filing_repository:
                logger.warning("Filing repository not available")
                return None
            
            filing_history = self._filing_repository.get_filing_history_by_unique_id(
                company_unique_id, limit
            )
            
            return {
                "success": True,
                "company_unique_id": company_unique_id,
                "filing_count": len(filing_history),
                "filings": filing_history,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get filing history: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_unique_id": company_unique_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def _default_progress_callback(self, message: str, progress: float):
        """Default progress callback that logs to console"""
        logger.info(f"🔄 Progress ({progress:.1f}%): {message}")
    
    def _mock_agentic_response(self, company_name: str, company_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Mock response when agentic components are not available
        
        Args:
            company_name: Name of the company
            company_number: Optional company registration number
            
        Returns:
            Mock response indicating components are not available
        """
        logger.warning(f"⚠️ Returning mock response for {company_name} - agentic components not available")
        
        return {
            "success": False,
            "error": "Agentic components not available",
            "company_name": company_name,
            "company_number": company_number,
            "mock_data": {
                "estimated_revenue": None,
                "confidence_score": 0.0,
                "extraction_method": "none",
                "document_count": 0,
                "workflow_steps": []
            },
            "service_metadata": {
                "execution_time_seconds": 0.1,
                "service_version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "agentic_components_available": False,
                "mock_response": True
            }
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the service and its components
        
        Returns:
            Service status information
        """
        return {
            "service_name": "UpdateRevenueService",
            "version": "1.0.0",
            "agentic_components_available": AGENTIC_COMPONENTS_AVAILABLE,
            "agentic_service_initialized": self._agentic_service is not None,
            "filing_repository_initialized": self._filing_repository is not None,
            "timestamp": datetime.now().isoformat()
        }

