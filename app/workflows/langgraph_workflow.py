"""
LangGraph Credit Risk Analysis Workflow
======================================

This module defines the LangGraph-based workflow for credit risk analysis,
providing visual orchestration of the multi-agent system.
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
import json

try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.graph.message import add_messages
    from langchain_core.messages import BaseMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Fallback for development/testing without LangGraph
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"
    START = "START"
    add_messages = lambda x: x
    BaseMessage = object

from pydantic import BaseModel, Field

# Import existing agents
from ..agents.base_agent import BaseAgent, AgentResult
from ..agents.data_ingestion_agent import DataIngestionAgent  
from ..agents.anomaly_detection_agent import AnomalyDetectionAgent
from ..agents.sector_classification_agent import SectorClassificationAgent
from ..agents.turnover_estimation_agent import TurnoverEstimationAgent
from ..agents.document_download_agent import DocumentDownloadAgent
from ..agents.smart_financial_extraction_agent import SmartFinancialExtractionAgent
from ..agents.rag_document_agent import RAGDocumentAgent

class WorkflowState(TypedDict):
    """State for the credit risk analysis workflow"""
    session_id: str
    messages: List[Any]  # Simplified to avoid annotation issues
    current_stage: str
    company_data: Dict[str, Any]
    anomalies_detected: List[Dict[str, Any]]
    sector_predictions: Dict[str, Any]
    revenue_estimates: Dict[str, Any]
    document_data: Dict[str, Any]
    extracted_financials: Dict[str, Any]
    rag_insights: Dict[str, Any]
    workflow_progress: Dict[str, Any]
    workflow_summary: Optional[Dict[str, Any]]  # Added this field
    error_state: Optional[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    approved_actions: List[Dict[str, Any]]

class CreditRiskWorkflow:
    """LangGraph-based workflow for credit risk analysis"""
    
    def __init__(self):
        if not LANGGRAPH_AVAILABLE:
            # Fallback to simple orchestration
            self.workflow = None
            self.graph = None
        else:
            self.workflow = StateGraph(WorkflowState)
            self._setup_workflow()
        
        # Initialize agents
        self.agents = {
            'data_ingestion': DataIngestionAgent(),
            'anomaly_detection': AnomalyDetectionAgent(),  
            'sector_classification': SectorClassificationAgent(),
            'turnover_estimation': TurnoverEstimationAgent(),
            'document_download': DocumentDownloadAgent(),
            'financial_extraction': SmartFinancialExtractionAgent(),
            'rag_analysis': RAGDocumentAgent()
        }
    
    def _setup_workflow(self):
        """Setup the LangGraph workflow structure"""
        
        if not LANGGRAPH_AVAILABLE or not self.workflow:
            return
        
        # Add nodes for each agent
        self.workflow.add_node("data_ingestion", self._data_ingestion_node)
        self.workflow.add_node("anomaly_detection", self._anomaly_detection_node)
        self.workflow.add_node("sector_classification", self._sector_classification_node)
        self.workflow.add_node("document_processing", self._document_processing_node)
        self.workflow.add_node("financial_extraction", self._financial_extraction_node)
        self.workflow.add_node("rag_analysis", self._rag_analysis_node)
        self.workflow.add_node("turnover_estimation", self._turnover_estimation_node)
        self.workflow.add_node("workflow_summary", self._workflow_summary_node)
        
        # Define the workflow edges
        self.workflow.add_edge(START, "data_ingestion")
        self.workflow.add_edge("data_ingestion", "anomaly_detection")
        
        # Conditional routing after anomaly detection
        self.workflow.add_conditional_edges(
            "anomaly_detection",
            self._should_process_documents,
            {
                "process_documents": "document_processing",
                "classify_sectors": "sector_classification"
            }
        )
        
        # Document processing branch
        self.workflow.add_edge("document_processing", "financial_extraction")
        self.workflow.add_edge("financial_extraction", "rag_analysis")
        self.workflow.add_edge("rag_analysis", "sector_classification")
        
        # Main analysis flow
        self.workflow.add_edge("sector_classification", "turnover_estimation")
        self.workflow.add_edge("turnover_estimation", "workflow_summary")
        self.workflow.add_edge("workflow_summary", END)
        
        # Compile the workflow
        self.graph = self.workflow.compile()
    
    def _data_ingestion_node(self, state: WorkflowState) -> WorkflowState:
        """Data ingestion workflow node"""
        try:
            # Update progress
            state["workflow_progress"]["data_ingestion"] = {
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "progress": 0
            }
            
            # Simulate data ingestion (replace with actual agent call)
            result = self.agents['data_ingestion'].process({
                "action": "ingest_company_data",
                "session_id": state["session_id"]
            })
            
            # Update state with results
            state["company_data"] = result.data if result.success else {}
            state["current_stage"] = "data_ingested"
            
            # Update progress
            state["workflow_progress"]["data_ingestion"] = {
                "status": "completed" if result.success else "failed",
                "end_time": datetime.now().isoformat(),
                "progress": 100,
                "result_summary": f"Processed {len(state['company_data'])} companies"
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "data_ingestion",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _anomaly_detection_node(self, state: WorkflowState) -> WorkflowState:
        """Anomaly detection workflow node"""
        try:
            # Update progress
            state["workflow_progress"]["anomaly_detection"] = {
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "progress": 0
            }
            
            # Process anomaly detection
            result = self.agents['anomaly_detection'].process({
                "company_data": state["company_data"],
                "session_id": state["session_id"]
            })
            
            # Update state
            state["anomalies_detected"] = result.data.get("anomalies", []) if result.success else []
            state["current_stage"] = "anomalies_detected"
            
            # Update progress
            state["workflow_progress"]["anomaly_detection"] = {
                "status": "completed" if result.success else "failed",
                "end_time": datetime.now().isoformat(),
                "progress": 100,
                "anomalies_found": len(state["anomalies_detected"])
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "anomaly_detection",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _sector_classification_node(self, state: WorkflowState) -> WorkflowState:
        """Sector classification workflow node"""
        try:
            # Update progress
            state["workflow_progress"]["sector_classification"] = {
                "status": "running", 
                "start_time": datetime.now().isoformat(),
                "progress": 0
            }
            
            # Process sector classification
            result = self.agents['sector_classification'].process({
                "company_data": state["company_data"],
                "anomalies": state["anomalies_detected"],
                "session_id": state["session_id"]
            })
            
            # Update state
            state["sector_predictions"] = result.data if result.success else {}
            state["current_stage"] = "sectors_classified"
            
            # Update progress
            state["workflow_progress"]["sector_classification"] = {
                "status": "completed" if result.success else "failed",
                "end_time": datetime.now().isoformat(),
                "progress": 100,
                "classifications_made": len(state["sector_predictions"])
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "sector_classification",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _document_processing_node(self, state: WorkflowState) -> WorkflowState:
        """Document processing workflow node"""
        try:
            # Update progress
            state["workflow_progress"]["document_processing"] = {
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "progress": 0
            }
            
            # Process document downloads
            result = self.agents['document_download'].process({
                "company_data": state["company_data"],
                "anomalies": state["anomalies_detected"],
                "session_id": state["session_id"]
            })
            
            # Update state
            state["document_data"] = result.data if result.success else {}
            state["current_stage"] = "documents_processed"
            
            # Update progress
            state["workflow_progress"]["document_processing"] = {
                "status": "completed" if result.success else "failed",
                "end_time": datetime.now().isoformat(),
                "progress": 100,
                "documents_processed": len(state["document_data"])
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "document_processing",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _financial_extraction_node(self, state: WorkflowState) -> WorkflowState:
        """Financial extraction workflow node"""
        try:
            # Update progress
            state["workflow_progress"]["financial_extraction"] = {
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "progress": 0
            }
            
            # Process financial extraction
            result = self.agents['financial_extraction'].process({
                "document_data": state["document_data"],
                "session_id": state["session_id"]
            })
            
            # Update state
            state["extracted_financials"] = result.data if result.success else {}
            state["current_stage"] = "financials_extracted"
            
            # Update progress
            state["workflow_progress"]["financial_extraction"] = {
                "status": "completed" if result.success else "failed",
                "end_time": datetime.now().isoformat(),
                "progress": 100,
                "extractions_made": len(state["extracted_financials"])
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "financial_extraction",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _rag_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """RAG analysis workflow node"""
        try:
            # Update progress
            state["workflow_progress"]["rag_analysis"] = {
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "progress": 0
            }
            
            # Process RAG analysis
            result = self.agents['rag_analysis'].process({
                "extracted_financials": state["extracted_financials"],
                "document_data": state["document_data"],
                "session_id": state["session_id"]
            })
            
            # Update state
            state["rag_insights"] = result.data if result.success else {}
            state["current_stage"] = "rag_completed"
            
            # Update progress
            state["workflow_progress"]["rag_analysis"] = {
                "status": "completed" if result.success else "failed",
                "end_time": datetime.now().isoformat(),
                "progress": 100,
                "insights_generated": len(state["rag_insights"])
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "rag_analysis",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _turnover_estimation_node(self, state: WorkflowState) -> WorkflowState:
        """Turnover estimation workflow node"""
        try:
            # Update progress
            state["workflow_progress"]["turnover_estimation"] = {
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "progress": 0
            }
            
            # Process turnover estimation
            result = self.agents['turnover_estimation'].process({
                "company_data": state["company_data"],
                "sector_predictions": state["sector_predictions"],
                "extracted_financials": state["extracted_financials"],
                "session_id": state["session_id"]
            })
            
            # Update state
            state["revenue_estimates"] = result.data if result.success else {}
            state["current_stage"] = "turnover_estimated"
            
            # Update progress
            state["workflow_progress"]["turnover_estimation"] = {
                "status": "completed" if result.success else "failed",
                "end_time": datetime.now().isoformat(),
                "progress": 100,
                "estimates_made": len(state["revenue_estimates"])
            }
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "turnover_estimation",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _workflow_summary_node(self, state: WorkflowState) -> WorkflowState:
        """Workflow summary and final results"""
        try:
            # Create comprehensive summary
            summary = {
                "session_id": state["session_id"],
                "completion_time": datetime.now().isoformat(),
                "total_companies_processed": len(state["company_data"]),
                "anomalies_detected": len(state["anomalies_detected"]),
                "sectors_classified": len(state["sector_predictions"]),
                "revenue_estimates": len(state["revenue_estimates"]),
                "workflow_success": state["error_state"] is None,
                "stages_completed": [
                    stage for stage, progress in state["workflow_progress"].items()
                    if progress.get("status") == "completed"
                ]
            }
            
            state["current_stage"] = "workflow_completed"
            state["workflow_summary"] = summary
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "workflow_summary",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def _should_process_documents(self, state: WorkflowState) -> str:
        """Conditional logic to determine if document processing is needed"""
        # Check if there are anomalies that require document verification
        high_priority_anomalies = [
            a for a in state["anomalies_detected"] 
            if a.get("severity", "low") in ["high", "critical"]
        ]
        
        if high_priority_anomalies:
            return "process_documents"
        else:
            return "classify_sectors"
    
    def _execute_workflow_manually(self, state: WorkflowState) -> WorkflowState:
        """Fallback execution when LangGraph is not available"""
        try:
            # Execute workflow steps manually in sequence
            state = self._data_ingestion_node(state)
            if state.get("error_state"):
                return state
                
            state = self._anomaly_detection_node(state)
            if state.get("error_state"):
                return state
            
            # Check if we should process documents
            should_process_docs = self._should_process_documents(state)
            
            if should_process_docs == "process_documents":
                state = self._document_processing_node(state)
                if state.get("error_state"):
                    return state
                    
                state = self._financial_extraction_node(state)
                if state.get("error_state"):
                    return state
                    
                state = self._rag_analysis_node(state)
                if state.get("error_state"):
                    return state
            
            state = self._sector_classification_node(state)
            if state.get("error_state"):
                return state
                
            state = self._turnover_estimation_node(state)
            if state.get("error_state"):
                return state
                
            state = self._workflow_summary_node(state)
            
            return state
            
        except Exception as e:
            state["error_state"] = {
                "node": "manual_execution",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return state
    
    def execute_workflow(self, initial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete workflow"""
        
        # Initialize state
        initial_state: WorkflowState = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "messages": [],
            "current_stage": "initialized",
            "company_data": initial_data.get("company_data", {}),
            "anomalies_detected": [],
            "sector_predictions": {},
            "revenue_estimates": {},
            "document_data": {},
            "extracted_financials": {},
            "rag_insights": {},
            "workflow_progress": {},
            "workflow_summary": None,  # Initialize with None
            "error_state": None,
            "suggestions": [],
            "approved_actions": []
        }
        
        # Execute the workflow
        try:
            if LANGGRAPH_AVAILABLE and self.graph:
                final_state = self.graph.invoke(initial_state)
            else:
                # Fallback: Execute workflow manually without LangGraph
                final_state = self._execute_workflow_manually(initial_state)
                
            return {
                "success": True,
                "session_id": final_state["session_id"],
                "current_stage": final_state["current_stage"],
                "workflow_progress": final_state["workflow_progress"],
                "results": {
                    "anomalies": final_state["anomalies_detected"],
                    "sector_predictions": final_state["sector_predictions"],
                    "revenue_estimates": final_state["revenue_estimates"],
                    "rag_insights": final_state["rag_insights"]
                },
                "summary": final_state.get("workflow_summary", {}),
                "error": final_state["error_state"],
                "langgraph_enabled": LANGGRAPH_AVAILABLE
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "session_id": initial_state["session_id"],
                "langgraph_enabled": LANGGRAPH_AVAILABLE
            }
    
    def get_workflow_visualization(self) -> Dict[str, Any]:
        """Get workflow structure for visualization"""
        return {
            "nodes": [
                {"id": "data_ingestion", "label": "Data Ingestion", "type": "agent"},
                {"id": "anomaly_detection", "label": "Anomaly Detection", "type": "agent"},
                {"id": "document_processing", "label": "Document Processing", "type": "agent"},
                {"id": "financial_extraction", "label": "Financial Extraction", "type": "agent"},
                {"id": "rag_analysis", "label": "RAG Analysis", "type": "agent"},
                {"id": "sector_classification", "label": "Sector Classification", "type": "agent"},
                {"id": "turnover_estimation", "label": "Turnover Estimation", "type": "agent"},
                {"id": "workflow_summary", "label": "Workflow Summary", "type": "summary"}
            ],
            "edges": [
                {"from": "data_ingestion", "to": "anomaly_detection"},
                {"from": "anomaly_detection", "to": "document_processing", "condition": "high_priority_anomalies"},
                {"from": "anomaly_detection", "to": "sector_classification", "condition": "normal_flow"},
                {"from": "document_processing", "to": "financial_extraction"},
                {"from": "financial_extraction", "to": "rag_analysis"},
                {"from": "rag_analysis", "to": "sector_classification"},
                {"from": "sector_classification", "to": "turnover_estimation"},
                {"from": "turnover_estimation", "to": "workflow_summary"}
            ]
        }