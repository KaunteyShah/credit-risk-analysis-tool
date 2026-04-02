"""
Agentic Workflows Framework

This module provides intelligent agentic frameworks for enhanced business process automation.
Currently includes two dedicated workflow systems with multi-agent intelligence, reflection,
reasoning, and comprehensive validation capabilities.

Dedicated Workflow Systems:
1. **SIC Prediction Workflow** (sic_prediction/): Enhanced SIC classification with intelligent validation
2. **Revenue Extraction Workflow** (update_revenue/): Automated revenue extraction from financial documents

Key Architecture:
- **Dedicated Folders**: Separate workflow systems with independent node structures
- **Workflow State Management**: TypedDict schemas for robust state handling  
- **Multi-Strategy Processing**: Tiered approaches with intelligent fallback mechanisms
- **Service Integration**: Leverages existing infrastructure with 85-90% code reuse
- **API Routes**: Enhanced endpoints for both SIC prediction and revenue extraction

SIC Prediction Workflow (sic_prediction/):
1. Data Ingestion Node: Intelligent data preparation and quality assessment
2. Companies House SIC Retrieval Node: Dual-strategy CH data retrieval with fallbacks
3. AI Prediction Node: Enhanced SIC prediction using multiple methods and reasoning
4. Reflection Node: Quality evaluation and strategic decision-making
5. Reasoning Generator Node: Comprehensive reasoning and explanation generation

Revenue Extraction Workflow (update_revenue/):
1. Company Data Ingestion Node: Dual lookup methodology (number + name/address search)
2. Financial Document Extraction Node: PDF download, text processing, and vectorization
3. Turnover Estimation Node: Multi-strategy revenue extraction (RAG + Vector, Smart Agent, Regex, Manual)

Integration Strategy:
- Zero-impact deployment alongside existing infrastructure
- Maintains backward compatibility with current API endpoints
- Enhanced capabilities through new agentic endpoints
- Comprehensive error handling and fallback mechanisms
- Existing UI compatibility (no changes required)

Usage:
```python
from app_modules.agentic.sic_prediction import AgenticSICPredictionService
from app_modules.agentic.update_revenue import AgenticRevenueService

# SIC Prediction
sic_service = AgenticSICPredictionService(services)
sic_result = sic_service.predict_sic_agentic(
    company_name="Example Company Ltd",
    business_description="Software development"
)

# Revenue Extraction  
revenue_service = AgenticRevenueService(services)
revenue_result = revenue_service.extract_revenue_agentic(
    company_name="Example Company Ltd",
    company_number="12345678"
)
```

API Integration:
```python
from app_modules.agentic.agentic_routes import register_agentic_routes

# Register all agentic routes with Flask app
register_agentic_routes(app)

# Available endpoints:
# POST /api/agentic/predict_sic - Enhanced agentic SIC prediction  
# POST /api/agentic/extract_revenue - Enhanced agentic revenue extraction
# GET /api/agentic/status - Service health and configuration
# GET /api/agentic/config - Configuration schema and current settings
# POST /api/agentic/config - Update workflow configuration
# Direct routes: /api/predict_sic_agentic, /api/extract_revenue_agentic
```
"""

# SIC Prediction Workflow Components
from .sic_prediction.workflow_state import (
    AgenticWorkflowState,
    CompanyData,
    CompaniesHouseSICData,
    AIPredictionData,
    EvaluationResult,
    WorkflowDecision
)
from .sic_prediction.workflow_builder import (
    build_agentic_workflow,
    WorkflowBuilder,
    LANGGRAPH_AVAILABLE
)
from .sic_prediction.sic_service import AgenticSICPredictionService

# Revenue Extraction Workflow Components  
from .update_revenue.revenue_workflow_state import (
    RevenueWorkflowState,
    CompanyFilingData,
    DocumentProcessingData,
    RevenueExtractionData
)
from .update_revenue.revenue_agentic_service import AgenticRevenueService

# Individual SIC workflow nodes (for advanced usage)
from .sic_prediction.nodes.data_ingestion_node import DataIngestionNode
from .sic_prediction.nodes.ch_sic_retrieval_node import CHSICRetrievalNode  
from .sic_prediction.nodes.ai_prediction_node import AIPredictionNode
from .sic_prediction.nodes.reflection_node import ReflectionNode
from .sic_prediction.nodes.reasoning_generator_node import ReasoningGeneratorNode

# Individual Revenue workflow nodes (for advanced usage)
from .update_revenue.nodes.company_data_ingestion_node import CompanyDataIngestionNode
from .update_revenue.nodes.financial_extraction_node import FinancialExtractionNode
from .update_revenue.nodes.turnover_estimation_node import TurnoverEstimationNode

__all__ = [
    # SIC Prediction Workflow
    'AgenticWorkflowState',
    'CompanyData',
    'CompaniesHouseSICData', 
    'AIPredictionData',
    'EvaluationResult',
    'WorkflowDecision',
    'build_agentic_workflow',
    'WorkflowBuilder',
    'LANGGRAPH_AVAILABLE',
    'AgenticSICPredictionService',
    
    # Revenue Extraction Workflow
    'RevenueWorkflowState',
    'CompanyFilingData',
    'DocumentProcessingData',
    'RevenueExtractionData',
    'AgenticRevenueService',
    
    # SIC Prediction Nodes
    'DataIngestionNode',
    'CHSICRetrievalNode',
    'AIPredictionNode', 
    'ReflectionNode',
    'ReasoningGeneratorNode',
    
    # Revenue Extraction Nodes
    'CompanyDataIngestionNode',
    'FinancialExtractionNode',
    'TurnoverEstimationNode'
]

# Version information
__version__ = '2.0.0'
__author__ = 'Credit Risk Application Team'
__description__ = 'Intelligent agentic workflows framework for SIC prediction and revenue extraction'

# Module metadata for introspection
AGENTIC_MODULE_INFO = {
    'version': __version__,
    'author': __author__,
    'description': __description__,
    'workflows': {
        'sic_prediction': {
            'nodes': 5,
            'description': 'Enhanced SIC classification with intelligent validation'
        },
        'revenue_extraction': {
            'nodes': 3,
            'description': 'Automated revenue extraction from financial documents'
        }
    },
    'components': {
        'total_workflow_nodes': 8,
        'api_endpoints': 8,
        'state_schemas': 7,
        'langgraph_integration': LANGGRAPH_AVAILABLE
    },
    'dependencies': {
        'required': ['flask', 'typing', 'datetime', 'logging'],
        'optional': ['langgraph'],
        'internal': [
            'app_modules.services.*',
            'app_modules.apis.*',
            'app_modules.agents.*'
        ]
    },
    'features': {
        'dedicated_workflows': True,
        'multi_node_workflow': True,
        'intelligent_reflection': True,
        'reasoning_generation': True,
        'companies_house_validation': True,
        'revenue_extraction': True,
        'document_processing': True,
        'vector_search': True,
        'fallback_mechanisms': True,
        'zero_impact_deployment': True,
        'comprehensive_api': True
    }
}