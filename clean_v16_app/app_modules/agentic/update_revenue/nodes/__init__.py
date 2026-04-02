"""
Revenue Extraction Workflow Nodes

Specialized workflow nodes for intelligent revenue extraction from Companies House filings.
Each node handles a specific aspect of the revenue processing pipeline with existing agent integration.

Available Nodes:
- CompanyDataIngestionNode: Dual company lookup (number + name/address) and filing retrieval
- FinancialExtractionNode: PDF download, text processing, and vectorization
- RAGNode: Real-time document retrieval and semantic analysis for financial data
- TurnoverEstimationNode: Multi-strategy revenue extraction with validation

Integration Strategy:
- Leverages existing Companies House client (90% code reuse)
- Reuses DocumentDownloadAgent and RAGDocumentAgent (85-90% code reuse)  
- Integrates SmartFinancialExtractionAgent and TurnoverEstimationAgent (85-90% code reuse)
- Compatible with sqlite-vec for vector database functionality
- Sequential execution with comprehensive fallback mechanisms
"""

from .company_data_ingestion_node import CompanyDataIngestionNode
from .financial_extraction_node import FinancialExtractionNode
from .rag_node import RAGNode
from .turnover_estimation_node import TurnoverEstimationNode

__all__ = [
    'CompanyDataIngestionNode',
    'FinancialExtractionNode',
    'RAGNode', 
    'TurnoverEstimationNode'
]