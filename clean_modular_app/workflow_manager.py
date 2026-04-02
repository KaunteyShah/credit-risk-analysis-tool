"""
Modular Workflow Manager for Credit Risk Analysis

This module provides a clean interface for managing existing workflows
including SIC code prediction and revenue update workflows.
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

class WorkflowManager:
    """Manages existing workflows in a modular fashion"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.workflow_file = os.path.join(data_dir, "workflows.json")
        self.workflows = self._load_workflows()
        
    def _load_workflows(self) -> Dict[str, Any]:
        """Load existing workflows from file or create default ones"""
        if os.path.exists(self.workflow_file):
            try:
                with open(self.workflow_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Return default existing workflows based on current app structure
        return {
            "sic_prediction": {
                "id": "sic_prediction_workflow",
                "name": "SIC Code Prediction Workflow", 
                "description": "AI-powered SIC code prediction using multi-agent orchestration",
                "agents": [
                    {
                        "id": "data_ingestion",
                        "name": "Data Ingestion Agent",
                        "type": "data-ingestion",
                        "description": "Loads and prepares company data for analysis",
                        "instructions": "Extract company name, registration number, and business description from input data",
                        "position": {"x": 100, "y": 100}
                    },
                    {
                        "id": "document_retrieval", 
                        "name": "Document Retrieval Agent",
                        "type": "document-processing",
                        "description": "Fetches relevant company documents and filings",
                        "instructions": "Retrieve company house documents and annual reports for SIC analysis",
                        "position": {"x": 300, "y": 100}
                    },
                    {
                        "id": "nlp_processing",
                        "name": "NLP Processing Agent", 
                        "type": "ai-reasoning",
                        "description": "Processes business descriptions using natural language understanding",
                        "instructions": "Analyze business descriptions and extract key industry indicators",
                        "position": {"x": 500, "y": 100}
                    },
                    {
                        "id": "sic_classification",
                        "name": "Sector Classification Agent",
                        "type": "classification", 
                        "description": "Predicts SIC codes using fuzzy matching and ML",
                        "instructions": "Match business activities to appropriate SIC codes with confidence scoring",
                        "position": {"x": 700, "y": 100}
                    }
                ],
                "connections": [
                    {"from": "data_ingestion", "to": "document_retrieval"},
                    {"from": "document_retrieval", "to": "nlp_processing"},
                    {"from": "nlp_processing", "to": "sic_classification"}
                ]
            },
            "revenue_update": {
                "id": "revenue_update_workflow",
                "name": "Revenue Update Workflow",
                "description": "Multi-agent revenue estimation and update process", 
                "agents": [
                    {
                        "id": "data_validation",
                        "name": "Data Validation Agent",
                        "type": "data-ingestion",
                        "description": "Validates current revenue data and market conditions",
                        "instructions": "Check data quality and validate against external sources",
                        "position": {"x": 100, "y": 200}
                    },
                    {
                        "id": "financial_extraction",
                        "name": "Smart Financial Extraction Agent",
                        "type": "ai-reasoning", 
                        "description": "Extracts financial data from company filings",
                        "instructions": "Analyze financial statements and extract revenue indicators",
                        "position": {"x": 300, "y": 200}
                    },
                    {
                        "id": "turnover_estimation",
                        "name": "Turnover Estimation Agent",
                        "type": "ai-reasoning",
                        "description": "Estimates updated revenue based on market analysis", 
                        "instructions": "Calculate revenue estimates using market data and company performance",
                        "position": {"x": 500, "y": 200}
                    },
                    {
                        "id": "data_persistence",
                        "name": "Data Persistence Agent",
                        "type": "data-ingestion",
                        "description": "Saves updated revenue data to database",
                        "instructions": "Persist revenue updates and maintain data integrity",
                        "position": {"x": 700, "y": 200}
                    }
                ],
                "connections": [
                    {"from": "data_validation", "to": "financial_extraction"},
                    {"from": "financial_extraction", "to": "turnover_estimation"},
                    {"from": "turnover_estimation", "to": "data_persistence"}
                ]
            }
        }
    
    def _save_workflows(self) -> bool:
        """Save workflows to file"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.workflow_file, 'w') as f:
                json.dump(self.workflows, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving workflows: {e}")
            return False
    
    def get_all_workflows(self) -> Dict[str, Any]:
        """Get all available workflows"""
        return self.workflows
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific workflow by ID"""
        return self.workflows.get(workflow_id)
    
    def get_workflow_agents(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get agents for a specific workflow"""
        workflow = self.get_workflow(workflow_id)
        if workflow:
            return workflow.get("agents", [])
        return []
    
    def update_agent(self, workflow_id: str, agent_id: str, updates: Dict[str, Any]) -> bool:
        """Update an agent's properties"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
            
        for agent in workflow.get("agents", []):
            if agent["id"] == agent_id:
                agent.update(updates)
                return self._save_workflows()
        
        return False
    
    def execute_agent(self, workflow_id: str, agent_id: str, agent_type: str) -> Dict[str, Any]:
        """Simulate agent execution (returns mock result for demo)"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {"status": "error", "message": "Workflow not found"}
        
        # Find the agent
        agent = None
        for a in workflow.get("agents", []):
            if a["id"] == agent_id:
                agent = a
                break
        
        if not agent:
            return {"status": "error", "message": "Agent not found"}
        
        # Simulate execution based on agent type and workflow
        execution_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        result = {
            "execution_id": execution_id,
            "timestamp": timestamp,
            "status": "completed",
            "agent_name": agent["name"],
            "agent_type": agent_type,
            "message": f"Successfully executed {agent['name']}",
            "workflow_id": workflow_id
        }
        
        # Add workflow-specific results
        if workflow_id == "sic_prediction":
            if agent_id == "sic_classification":
                result.update({
                    "predicted_sic": "73110",
                    "confidence": 0.87,
                    "description": "Research and experimental development on biotechnology"
                })
        elif workflow_id == "revenue_update":
            if agent_id == "turnover_estimation":
                result.update({
                    "estimated_revenue": 2500000,
                    "confidence": 0.92,
                    "currency": "USD"
                })
        
        return result
    
    def get_agent_types(self) -> List[Dict[str, str]]:
        """Get available agent types"""
        return [
            {"type": "data-ingestion", "name": "Data Ingestion", "icon": "📊"},
            {"type": "document-processing", "name": "Document Processing", "icon": "📄"}, 
            {"type": "ai-reasoning", "name": "AI Reasoning", "icon": "🧠"},
            {"type": "classification", "name": "Classification", "icon": "🎯"},
            {"type": "anomaly-detection", "name": "Anomaly Detection", "icon": "⚠️"},
            {"type": "orchestrator", "name": "Orchestrator", "icon": "🎭"}
        ]

    def create_workflow_summary(self, workflow_id: str) -> Dict[str, Any]:
        """Create a summary of workflow for UI display"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {}
        
        return {
            "id": workflow["id"],
            "name": workflow["name"],
            "description": workflow["description"],
            "agent_count": len(workflow.get("agents", [])),
            "connection_count": len(workflow.get("connections", [])),
            "agents": [
                {
                    "id": agent["id"],
                    "name": agent["name"],
                    "type": agent["type"],
                    "description": agent["description"]
                }
                for agent in workflow.get("agents", [])
            ]
        }