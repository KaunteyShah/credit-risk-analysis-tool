"""
Revenue Extraction Agentic Workflow

Dedicated agentic workflow for intelligent revenue extraction from Companies House 
financial filings using multi-agent sequential processing with optional LangGraph support.

Key Components:
- revenue_workflow_state.py: Revenue workflow state management and TypedDict structures
- revenue_agentic_service.py: Main revenue agentic service interface with sequential execution
- nodes/: Specialized nodes for revenue extraction workflow steps

Architecture:
3-step sequential workflow for comprehensive revenue extraction:
1. Company Data Ingestion Node: Dual lookup (number + name/address) and filing retrieval
2. Financial Extraction Node: PDF download, text processing, and vectorization using existing agents
3. Turnover Estimation Node: Multi-strategy revenue extraction (RAG+Vector, Smart Agent, Regex, Manual)

Integration Strategy:
- Leverages existing Companies House client (90% code reuse)  
- Reuses DocumentDownloadAgent and RAGDocumentAgent (85-90% code reuse)
- Integrates SmartFinancialExtractionAgent and TurnoverEstimationAgent (85-90% code reuse)
- Compatible with existing /api/update_revenue endpoint and UI
- Zero-impact deployment alongside existing functionality
"""

# Core revenue workflow components  
from .revenue_workflow_state import RevenueWorkflowState, CompanyFilingData, DocumentProcessingData, RevenueExtractionData
from .revenue_agentic_service import AgenticRevenueService

# Revenue extraction nodes
from .nodes.company_data_ingestion_node import CompanyDataIngestionNode
from .nodes.financial_extraction_node import FinancialExtractionNode
from .nodes.turnover_estimation_node import TurnoverEstimationNode

__all__ = [
    # Core services
    'AgenticRevenueService',
    
    # State management
    'RevenueWorkflowState', 
    'CompanyFilingData',
    'DocumentProcessingData',
    'RevenueExtractionData',
    
    # Workflow nodes
    'CompanyDataIngestionNode',
    'FinancialExtractionNode',
    'TurnoverEstimationNode'
]