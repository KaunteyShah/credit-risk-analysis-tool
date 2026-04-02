"""
LangGraph Workflow State Schema

Defines the TypedDict state structure that coordinates data flow between all agentic nodes.
This state preserves all existing data structures while adding agentic enhancements.

CRITICAL: All field names EXACTLY match actual database column names to avoid conversions.
Database Schema Alignment:
- companies table: id, company_number, company_name, business_description, sic_codes, 
  registered_office_address, status, company_type, jurisdiction, etc.
- sic table: company_id, sic_code_id, is_primary
- No field conversions or mappings - direct database column usage only.
"""

from typing import TypedDict, Optional, Dict, Any, List
from datetime import datetime


class CompanyData(TypedDict, total=False):
    """Company data using EXACT database column names from companies table with dual-key validation"""
    # Primary fields from companies table (exact column names)
    id: Optional[int]  # Primary key from companies table
    unique_id: Optional[str]  # DUAL-KEY: Unique business identifier for validation
    company_number: Optional[str]  # Exact database column
    company_name: str  # Exact database column  
    business_description: str  # Exact database column
    sic_codes: Optional[str]  # Exact database column
    status: Optional[str]  # Exact database column
    company_type: Optional[str]  # Exact database column
    jurisdiction: Optional[str]  # Exact database column
    registered_office_address: Optional[str]  # Exact database column
    
    # Additional workflow fields (not database columns)
    company_index: Optional[int]  # For batch processing index
    existing_sic_confidence: Optional[float]  # Calculated field
    existing_sic_code: Optional[str]  # Existing SIC code for current_sic mapping


class CompaniesHouseSICData(TypedDict, total=False):
    """Companies House SIC data using exact database field structure"""
    success: bool
    sic_codes: List[str]  # Direct from database sic_codes field format
    sic_descriptions: List[str]
    company_number: Optional[str]  # Exact database column name
    company_name: Optional[str]  # Exact database column name
    retrieval_method: str  # "company_number", "name_address", or "not_available"
    confidence: float
    raw_data: Optional[Dict[str, Any]]


class AIPredictionData(TypedDict, total=False):
    """AI prediction results using exact database field names"""
    predicted_sic_code: str  # Direct SIC code value
    predicted_sic_description: str
    confidence_score: float
    prediction_method: str  # "enhanced_fuzzy", "azure_openai", "rule_based"
    alternatives: List[Dict[str, Any]]
    reasoning_summary: str


class EvaluationResult(TypedDict, total=False):
    """Reflection and evaluation assessment"""
    ch_vs_ai_agreement: bool
    confidence_delta: float
    quality_score: float
    recommended_action: str  # "accept_ai", "accept_ch", "request_refinement", "use_fallback"
    evaluation_reasoning: str
    refinement_suggestions: Optional[List[str]]


class WorkflowDecision(TypedDict):
    """Individual decision tracking for transparency"""
    node_name: str
    timestamp: datetime
    decision: str
    reasoning: str
    confidence: float
    fallback_triggered: bool


class AgenticWorkflowState(TypedDict):
    """
    Main state schema for LangGraph workflow coordination.
    
    CRITICAL: Uses EXACT database column names - NO field conversions.
    All company data uses direct database field names from companies table.
    
    This state structure enables:
    - Data flow between all 5 nodes  
    - Decision tracking and transparency
    - Fallback mechanism coordination
    - Real-time reasoning generation
    - Zero-conversion database integration
    """
    
    # Input data (using exact database column names)
    company_data: CompanyData  # All fields match database columns exactly
    workflow_config: Dict[str, Any]  # Configuration for workflow behavior
    
    # Node outputs (using exact field structures)
    ch_sic_data: Optional[CompaniesHouseSICData]
    ai_prediction: Optional[AIPredictionData]
    evaluation_result: Optional[EvaluationResult]
    final_reasoning: Optional[str]
    
    # Workflow coordination
    workflow_decisions: List[WorkflowDecision]
    node_confidence_scores: Dict[str, float]
    fallback_triggers: List[str]
    current_node: str
    
    # Final outputs (compatible with existing API format)
    final_sic_code: Optional[str]
    final_sic_description: Optional[str]
    final_confidence: Optional[float]
    workflow_summary: Optional[str]
    
    # Error handling
    errors: List[str]
    warnings: List[str]
    
    # Timing and performance
    node_execution_times: Dict[str, float]
    total_workflow_time: Optional[float]
    
    # Integration with existing workflow_steps format
    workflow_steps: List[Dict[str, Any]]  # For frontend visualization


# Node-specific state helpers for type safety
class DataIngestionState(TypedDict):
    """State after data ingestion node"""
    company_data: CompanyData
    workflow_config: Dict[str, Any]
    workflow_decisions: List[WorkflowDecision]
    current_node: str


class CHSICRetrievalState(DataIngestionState):
    """State after Companies House SIC retrieval node"""
    ch_sic_data: Optional[CompaniesHouseSICData]


class AIPredictionState(CHSICRetrievalState):
    """State after AI prediction node"""
    ai_prediction: Optional[AIPredictionData]


class ReflectionState(AIPredictionState):
    """State after reflection and evaluation node"""
    evaluation_result: Optional[EvaluationResult]


class FinalState(ReflectionState):
    """Final state after reasoning generation"""
    final_reasoning: str
    final_sic_code: str
    final_sic_description: str
    final_confidence: float
    workflow_summary: str