"""
SIC Prediction Agentic Workflow

Dedicated agentic workflow for intelligent SIC (Standard Industrial Classification) 
code prediction using LangGraph multi-agent orchestration.

Key Components:
- workflow_builder.py: SIC-specific workflow construction and compilation
- workflow_state.py: SIC prediction state management and data structures  
- sic_service.py: Main SIC agentic service interface
- nodes/: Specialized nodes for SIC prediction workflow steps

Architecture:
Multi-node workflow pattern for comprehensive SIC prediction:
1. Data Ingestion Node: Company data preparation and enrichment
2. Companies House SIC Retrieval Node: Official SIC code validation
3. AI Prediction Node: Enhanced SIC prediction with multiple strategies
4. Reflection Node: Quality evaluation and confidence assessment
5. Reasoning Generator Node: Comprehensive explanation generation
"""

# Core SIC workflow components
from .workflow_builder import WorkflowBuilder, build_agentic_workflow
from .workflow_state import AgenticWorkflowState, CompanyData, AIPredictionData
from .sic_service import AgenticSICPredictionService

# SIC prediction nodes
from .nodes.data_ingestion_node import DataIngestionNode
from .nodes.ch_sic_retrieval_node import CHSICRetrievalNode
from .nodes.ai_prediction_node import AIPredictionNode
from .nodes.reflection_node import ReflectionNode
from .nodes.reasoning_generator_node import ReasoningGeneratorNode

__all__ = [
    # Core services
    'AgenticSICPredictionService',
    'WorkflowBuilder', 
    'build_agentic_workflow',
    
    # State management
    'AgenticWorkflowState',
    'CompanyData',
    'AIPredictionData',
    
    # Workflow nodes
    'DataIngestionNode',
    'CHSICRetrievalNode', 
    'AIPredictionNode',
    'ReflectionNode',
    'ReasoningGeneratorNode'
]