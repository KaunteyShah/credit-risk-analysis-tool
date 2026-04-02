"""
Revenue Update Workflow State Management

TypedDict definitions for revenue extraction workflow state management.
Designed to integrate with existing LangGraph workflow infrastructure while 
maintaining compatibility with existing database schemas and agent interfaces.

State Structure:
- RevenueWorkflowState: Complete workflow state container
- CompanyFilingData: Company and filing information from Companies House  
- RevenueExtractionData: Extracted revenue data with confidence scoring
- DocumentProcessingData: PDF processing and vectorization results
- ValidationData: Cross-validation and quality assessment results
"""

from typing import TypedDict, List, Dict, Any, Optional, Union
from datetime import datetime

class CompanyFilingData(TypedDict, total=False):
    """Company and filing data using exact database field names"""
    # Company identification (multiple lookup methods)
    unique_id: str  # Database primary key
    company_number: Optional[str]  # Companies House number (Method 1)
    company_name: str  # For name+address lookup (Method 2)
    company_address: Optional[str]  # For address matching validation
    
    # Filing information from Companies House API
    transaction_id: Optional[str]  # Key field for document download
    filing_date: Optional[str]  # Latest financial filing date
    filing_category: Optional[str]  # "accounts", "annual-return", etc.
    filing_description: Optional[str]  # Human-readable filing description
    
    # API response metadata
    lookup_method: str  # "company_number", "name_address", or "manual"
    api_response_raw: Optional[Dict[str, Any]]  # Complete CH API response
    lookup_confidence: float  # Confidence in company identification

class DocumentProcessingData(TypedDict, total=False):
    """PDF document processing and vectorization results"""
    # Document download information
    document_url: Optional[str]  # Companies House PDF URL
    document_size: Optional[int]  # File size in bytes
    download_success: bool  # Download operation success
    download_timestamp: Optional[datetime]
    
    # Text extraction results
    extracted_text: Optional[str]  # Full PDF text content
    text_chunks: List[Dict[str, Any]]  # Chunked text for vectorization
    chunk_count: int  # Number of text chunks created
    
    # Vector database integration (sqlite-vec)
    vector_db_stored: bool  # Successfully stored in vector DB
    vector_collection_id: Optional[str]  # Collection identifier
    embedding_model: str  # "openai" or other embedding model used
    
    # Processing metadata
    processing_errors: List[str]  # Any errors encountered
    processing_time: float  # Total processing time in seconds

class RevenueExtractionData(TypedDict, total=False):
    """Revenue extraction results with confidence scoring"""
    # Core revenue data
    extracted_revenue: Optional[float]  # Main revenue figure extracted
    revenue_currency: str  # "GBP", "USD", etc.
    revenue_period: Optional[str]  # Financial period (e.g., "2023", "Year ended 31/12/2023")
    
    # Alternative revenue figures (for validation)
    alternative_revenues: List[Dict[str, Any]]  # Other potential revenue figures
    revenue_source_text: Optional[str]  # Original text where revenue was found
    
    # Confidence and validation
    extraction_confidence: float  # 0.0 to 1.0 confidence score
    extraction_method: str  # "regex", "rag", "ai_reasoning", "manual"
    similarity_scores: List[float]  # Vector similarity scores
    
    # Quality indicators
    validation_passed: bool  # Cross-validation checks passed
    validation_notes: List[str]  # Validation warnings or notes
    fallback_used: bool  # Whether fallback extraction was needed

class ValidationData(TypedDict, total=False):
    """Revenue validation and quality assessment results"""
    # Market validation
    market_revenue_estimate: Optional[float]  # Market-based revenue estimate
    market_confidence: float  # Confidence in market estimate
    market_data_source: str  # Source of market validation data
    
    # Historical comparison  
    previous_revenue: Optional[float]  # Previous year's revenue (if available)
    revenue_change_percentage: Optional[float]  # Year-over-year change
    change_reasonableness: bool  # Is the change reasonable?
    
    # Cross-validation results
    cross_validation_score: float  # Overall validation score
    validation_flags: List[str]  # Any red flags or warnings
    recommendation: str  # "accept", "review", "reject"

class WorkflowDecision(TypedDict, total=False):
    """Individual workflow decision tracking"""
    decision_point: str  # Where in workflow decision was made
    decision_type: str  # Type of decision ("routing", "validation", "fallback")
    decision_result: str  # Actual decision taken
    confidence: float  # Confidence in decision
    reasoning: str  # Why this decision was made
    timestamp: str  # When decision was made

class RevenueWorkflowState(TypedDict):
    """
    Complete revenue extraction workflow state.
    
    Integrates with existing LangGraph infrastructure while maintaining
    compatibility with existing database schemas and service interfaces.
    """
    # Core data containers (required)
    company_filing_data: CompanyFilingData  # Company and filing information
    document_processing_data: DocumentProcessingData  # PDF processing results
    revenue_extraction_data: RevenueExtractionData  # Revenue extraction results
    validation_data: ValidationData  # Validation and quality assessment
    
    # Workflow configuration and control (required)
    workflow_config: Dict[str, Any]  # Configuration overrides
    workflow_decisions: List[WorkflowDecision]  # Decision audit trail
    current_node: str  # Currently executing workflow node
    
    # Error handling and fallbacks (required)
    errors: List[str]  # Workflow errors encountered
    warnings: List[str]  # Workflow warnings
    fallback_triggers: List[str]  # What triggered fallback strategies
    
    # Performance and monitoring (required)
    node_execution_times: Dict[str, float]  # Execution time per node
    node_confidence_scores: Dict[str, float]  # Confidence per node
    workflow_start_time: datetime  # Workflow start timestamp
    
    # Integration with existing systems (required)
    original_request_data: Dict[str, Any]  # Original API request data
    database_update_status: Dict[str, Any]  # Database update results
    ui_notification_data: Dict[str, Any]  # Data for UI updates

# Type aliases for common workflow state operations
RevenueWorkflowInput = Dict[str, Any]  # Input to workflow nodes
RevenueWorkflowOutput = RevenueWorkflowState  # Output from workflow nodes

# Workflow state validation helpers
def create_initial_revenue_state(
    company_name: str,
    company_number: Optional[str] = None,
    unique_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> RevenueWorkflowState:
    """
    Create initial workflow state for revenue extraction.
    
    Args:
        company_name: Company name for processing
        company_number: Optional Companies House number  
        unique_id: Optional database unique ID
        config: Optional workflow configuration
        
    Returns:
        Initial workflow state ready for processing
    """
    return RevenueWorkflowState(
        company_filing_data=CompanyFilingData(
            company_name=company_name,
            company_number=company_number,
            unique_id=unique_id or f"temp_{company_name}_{datetime.now().isoformat()}",
            lookup_method="pending",
            lookup_confidence=0.0
        ),
        document_processing_data=DocumentProcessingData(
            download_success=False,
            chunk_count=0,
            vector_db_stored=False,
            embedding_model="openai",
            processing_errors=[],
            processing_time=0.0
        ),
        revenue_extraction_data=RevenueExtractionData(
            revenue_currency="GBP",  # Default to GBP for UK companies
            extraction_confidence=0.0,
            extraction_method="pending",
            similarity_scores=[],
            validation_passed=False,
            validation_notes=[],
            fallback_used=False,
            alternative_revenues=[]
        ),
        validation_data=ValidationData(
            market_confidence=0.0,
            market_data_source="none",
            cross_validation_score=0.0,
            validation_flags=[],
            recommendation="pending"
        ),
        workflow_config=config or {},
        workflow_decisions=[],
        current_node="initialization",
        errors=[],
        warnings=[],
        fallback_triggers=[],
        node_execution_times={},
        node_confidence_scores={},
        workflow_start_time=datetime.now(),
        original_request_data={},
        database_update_status={},
        ui_notification_data={}
    )