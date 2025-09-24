"""
LangGraph SIC Prediction Workflow - Phase 2 Implementation

This workflow replaces the mock agent visualization with real LangGraph-powered
multi-agent orchestration for SIC code prediction and credit risk analysis.
"""
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass
from datetime import datetime
import uuid

from langgraph import StateGraph, CompiledGraph
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

# Import our existing agents (Phase 1)
import sys
import os

from ..agents.base_agent import BaseAgent, AgentResult
from ..agents.data_ingestion_agent import DataIngestionAgent
from ..agents.document_download_agent import DocumentDownloadAgent
from ..agents.rag_document_agent import RAGDocumentAgent
from ..agents.sector_classification_agent import SectorClassificationAgent
from ..agents.anomaly_detection_agent import AnomalyDetectionAgent

@dataclass
class WorkflowState:
    """State management for LangGraph workflow"""
    company_data: Dict[str, Any]
    processing_stage: str
    agent_results: Dict[str, AgentResult]
    confidence_scores: Dict[str, float]
    errors: List[str]
    metadata: Dict[str, Any]
    workflow_id: str
    start_time: datetime
    
    def __post_init__(self):
        if not self.workflow_id:
            self.workflow_id = str(uuid.uuid4())
        if not self.start_time:
            self.start_time = datetime.now()

class SICPredictionWorkflow:
    """
    Real LangGraph workflow for SIC prediction replacing mock visualization
    
    Implements the 5-agent workflow:
    1. Data Ingestion Agent
    2. Document Retrieval Agent  
    3. NLP Processing Agent
    4. SIC Classification Agent
    5. Validation Agent
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.llm = self._initialize_llm()
        
        # Initialize Phase 1 agents for real processing
        self.data_agent = DataIngestionAgent()
        self.document_agent = DocumentDownloadAgent()
        self.rag_agent = RAGDocumentAgent()
        self.classification_agent = SectorClassificationAgent()
        self.validation_agent = AnomalyDetectionAgent()  # Repurposed for validation
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        self.compiled_workflow = self.workflow.compile()
    
    def _initialize_llm(self):
        """Initialize OpenAI LLM for agent communication (supports Azure OpenAI)"""
        
        # Load environment variables
        openai_endpoint = os.getenv('OPENAI_ENDPOINT')
        openai_key = os.getenv('OPENAI_API_KEY') or self.openai_api_key
        
        if not openai_key or openai_key == 'your_openai_api_key_here':
            # No API key configured - return None for mock mode
            return None
        
        if openai_endpoint and openai_endpoint != 'your_openai_endpoint_here':
            # Azure OpenAI configuration
            try:
                from langchain_openai import AzureChatOpenAI
                return AzureChatOpenAI(
                    azure_endpoint=openai_endpoint,
                    api_key=openai_key,
                    api_version=os.getenv('OPENAI_API_VERSION', '2024-02-15-preview'),
                    azure_deployment=os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-35-turbo'),
                    temperature=0.1
                )
            except ImportError:
                # Fallback to standard OpenAI if Azure import fails
                pass
        
        # Standard OpenAI configuration
        return ChatOpenAI(
            api_key=openai_key,
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            temperature=0.1
        )
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with real agent nodes"""
        workflow = StateGraph(WorkflowState)
        
        # Add agent nodes
        workflow.add_node("data_ingestion", self._data_ingestion_node)
        workflow.add_node("document_retrieval", self._document_retrieval_node)
        workflow.add_node("nlp_processing", self._nlp_processing_node)
        workflow.add_node("sic_classification", self._sic_classification_node)
        workflow.add_node("validation", self._validation_node)
        
        # Define workflow edges
        workflow.add_edge("data_ingestion", "document_retrieval")
        workflow.add_edge("document_retrieval", "nlp_processing")
        workflow.add_edge("nlp_processing", "sic_classification")
        workflow.add_edge("sic_classification", "validation")
        
        # Set entry point
        workflow.set_entry_point("data_ingestion")
        
        return workflow
    
    def _data_ingestion_node(self, state: WorkflowState) -> WorkflowState:
        """Node 1: Data Ingestion - Load and prepare company data"""
        try:
            # Use real Data Ingestion Agent
            result = self.data_agent.process(state.company_data)
            
            state.agent_results["data_ingestion"] = result
            state.processing_stage = "data_ingestion_complete"
            state.confidence_scores["data_ingestion"] = result.confidence
            
            if result.success:
                state.company_data.update(result.data or {})
            else:
                state.errors.append(f"Data ingestion failed: {result.error_message}")
                
        except Exception as e:
            error_msg = f"Data ingestion node error: {str(e)}"
            state.errors.append(error_msg)
            state.agent_results["data_ingestion"] = AgentResult(
                agent_name="DataIngestionAgent",
                timestamp=datetime.now(),
                success=False,
                error_message=error_msg
            )
        
        return state
    
    def _document_retrieval_node(self, state: WorkflowState) -> WorkflowState:
        """Node 2: Document Retrieval - Fetch company documents"""
        try:
            # Use real Document Download Agent
            company_number = state.company_data.get('company_number', '')
            result = self.document_agent.process({'company_number': company_number})
            
            state.agent_results["document_retrieval"] = result
            state.processing_stage = "document_retrieval_complete"
            state.confidence_scores["document_retrieval"] = result.confidence
            
            if result.success and result.data:
                state.company_data['documents'] = result.data
            else:
                state.errors.append(f"Document retrieval failed: {result.error_message}")
                
        except Exception as e:
            error_msg = f"Document retrieval node error: {str(e)}"
            state.errors.append(error_msg)
            state.agent_results["document_retrieval"] = AgentResult(
                agent_name="DocumentDownloadAgent",
                timestamp=datetime.now(),
                success=False,
                error_message=error_msg
            )
        
        return state
    
    def _nlp_processing_node(self, state: WorkflowState) -> WorkflowState:
        """Node 3: NLP Processing - Analyze business content"""
        try:
            # Use real RAG Document Agent for NLP processing
            documents = state.company_data.get('documents', [])
            if documents:
                # Process business description
                business_query = "What is the main business activity of this company?"
                result = self.rag_agent.process_semantic_query(business_query, documents)
            else:
                # Fallback to existing company description
                company_name = state.company_data.get('CompanyName', '')
                result = self.rag_agent.process({'company_name': company_name})
            
            state.agent_results["nlp_processing"] = result
            state.processing_stage = "nlp_processing_complete"
            state.confidence_scores["nlp_processing"] = result.confidence
            
            if result.success and result.data:
                state.company_data['business_analysis'] = result.data
            else:
                state.errors.append(f"NLP processing failed: {result.error_message}")
                
        except Exception as e:
            error_msg = f"NLP processing node error: {str(e)}"
            state.errors.append(error_msg)
            state.agent_results["nlp_processing"] = AgentResult(
                agent_name="RAGDocumentAgent",
                timestamp=datetime.now(),
                success=False,
                error_message=error_msg
            )
        
        return state
    
    def _sic_classification_node(self, state: WorkflowState) -> WorkflowState:
        """Node 4: SIC Classification - Predict SIC codes"""
        try:
            # Use real Sector Classification Agent
            business_data = {
                'company_name': state.company_data.get('CompanyName', ''),
                'business_analysis': state.company_data.get('business_analysis', {}),
                'existing_sic': state.company_data.get('SICCode.SicText_1', '')
            }
            
            result = self.classification_agent.process(business_data)
            
            state.agent_results["sic_classification"] = result
            state.processing_stage = "sic_classification_complete"
            state.confidence_scores["sic_classification"] = result.confidence
            
            if result.success and result.data:
                state.company_data['predicted_sic'] = result.data
            else:
                state.errors.append(f"SIC classification failed: {result.error_message}")
                
        except Exception as e:
            error_msg = f"SIC classification node error: {str(e)}"
            state.errors.append(error_msg)
            state.agent_results["sic_classification"] = AgentResult(
                agent_name="SectorClassificationAgent",
                timestamp=datetime.now(),
                success=False,
                error_message=error_msg
            )
        
        return state
    
    def _validation_node(self, state: WorkflowState) -> WorkflowState:
        """Node 5: Validation - Validate and score predictions"""
        try:
            # Use Anomaly Detection Agent for validation
            validation_data = {
                'original_sic': state.company_data.get('SICCode.SicText_1', ''),
                'predicted_sic': state.company_data.get('predicted_sic', {}),
                'confidence_scores': state.confidence_scores,
                'business_analysis': state.company_data.get('business_analysis', {})
            }
            
            result = self.validation_agent.process(validation_data)
            
            state.agent_results["validation"] = result
            state.processing_stage = "workflow_complete"
            state.confidence_scores["validation"] = result.confidence
            
            if result.success and result.data:
                state.company_data['validation_results'] = result.data
                # Calculate overall workflow confidence
                avg_confidence = sum(state.confidence_scores.values()) / len(state.confidence_scores)
                state.metadata['overall_confidence'] = avg_confidence
            else:
                state.errors.append(f"Validation failed: {result.error_message}")
                
        except Exception as e:
            error_msg = f"Validation node error: {str(e)}"
            state.errors.append(error_msg)
            state.agent_results["validation"] = AgentResult(
                agent_name="AnomalyDetectionAgent",
                timestamp=datetime.now(),
                success=False,
                error_message=error_msg
            )
        
        return state
    
    def execute_workflow(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete SIC prediction workflow
        
        Args:
            company_data: Company information to process
            
        Returns:
            Complete workflow results with agent outputs
        """
        # Initialize workflow state
        initial_state = WorkflowState(
            company_data=company_data,
            processing_stage="starting",
            agent_results={},
            confidence_scores={},
            errors=[],
            metadata={},
            workflow_id=str(uuid.uuid4()),
            start_time=datetime.now()
        )
        
        try:
            # Execute LangGraph workflow
            final_state = self.compiled_workflow.invoke(initial_state)
            
            # Prepare results
            results = {
                "workflow_id": final_state.workflow_id,
                "success": len(final_state.errors) == 0,
                "processing_stage": final_state.processing_stage,
                "company_data": final_state.company_data,
                "agent_results": {
                    name: {
                        "agent_name": result.agent_name,
                        "timestamp": result.timestamp.isoformat(),
                        "success": result.success,
                        "confidence": result.confidence,
                        "data": result.data,
                        "error_message": result.error_message
                    }
                    for name, result in final_state.agent_results.items()
                },
                "confidence_scores": final_state.confidence_scores,
                "errors": final_state.errors,
                "metadata": final_state.metadata,
                "execution_time": (datetime.now() - final_state.start_time).total_seconds()
            }
            
            return results
            
        except Exception as e:
            return {
                "workflow_id": initial_state.workflow_id,
                "success": False,
                "error": f"Workflow execution failed: {str(e)}",
                "processing_stage": "failed",
                "execution_time": (datetime.now() - initial_state.start_time).total_seconds()
            }
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of running workflow (for real-time UI updates)"""
        # In production, this would query a workflow state store
        return {
            "workflow_id": workflow_id,
            "status": "running",
            "current_stage": "processing",
            "agents_completed": 0,
            "total_agents": 5
        }

# Example usage for testing
if __name__ == "__main__":
    # Test the workflow with sample data
    workflow = SICPredictionWorkflow()
    
    sample_company = {
        "CompanyName": "Tech Solutions Ltd",
        "company_number": "12345678",
        "SICCode.SicText_1": "Computer programming activities"
    }
    
    results = workflow.execute_workflow(sample_company)
    
    # Use logger if available, otherwise fallback to print for this test script
    try:
        from ..utils.logger import logger
from app.utils.centralized_logging import get_logger
logger = get_logger(__name__)
        logger.info(f"Workflow Results: {results}")
    except ImportError:
        print("Workflow Results:", results)
