"""
Multi-Agent Orchestrator - Coordinates the entire anomaly detection and correction workflow.
"""
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.data_ingestion_agent import DataIngestionAgent
from app.agents.anomaly_detection_agent import AnomalyDetectionAgent
from app.agents.sector_classification_agent import SectorClassificationAgent
from app.agents.turnover_estimation_agent import TurnoverEstimationAgent
from app.agents.document_download_agent import DocumentDownloadAgent
from app.agents.smart_financial_extraction_agent import SmartFinancialExtractionAgent
from app.agents.rag_document_agent import RAGDocumentAgent, SemanticQuery
from app.utils.config_manager import config
from app.utils.logger import logger

class MultiAgentOrchestrator:
    """Orchestrates the multi-agent anomaly detection and correction workflow."""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize core agents
        self.data_agent = DataIngestionAgent()
        self.anomaly_agent = AnomalyDetectionAgent()
        self.sector_agent = SectorClassificationAgent()
        self.turnover_agent = TurnoverEstimationAgent()
        
        # Initialize document processing agents
        self.document_agent = DocumentDownloadAgent()
        self.extraction_agent = SmartFinancialExtractionAgent()
        self.rag_agent = RAGDocumentAgent()
        
        # Workflow state
        self.workflow_state = {
            "session_id": self.session_id,
            "start_time": datetime.now(),
            "current_stage": "initialized",
            "results": {},
            "suggestions": [],
            "approved_suggestions": [],
            "rejected_suggestions": [],
            "document_processing": {
                "downloaded_documents": [],
                "extraction_results": [],
                "rag_queries": []
            }
        }
        
        logger.info(f"Multi-Agent Orchestrator initialized with session ID: {self.session_id}")
    
    def run_complete_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the complete anomaly detection and correction workflow.
        
        Args:
            input_data: Dictionary containing:
                - company_numbers: List of company numbers to analyze
                - search_queries: List of search terms for company discovery
                - include_filing_history: Boolean to include filing history
        
        Returns:
            Complete workflow results
        """
        try:
            logger.info("Starting complete multi-agent workflow")
            
            # Stage 1: Data Ingestion
            ingestion_result = self._run_data_ingestion(input_data)
            if not ingestion_result.success:
                return self._create_error_response("Data ingestion failed", ingestion_result.error_message or "Unknown error")
            
            # Stage 2: Anomaly Detection
            anomaly_result = self._run_anomaly_detection(ingestion_result.data)
            if not anomaly_result.success:
                return self._create_error_response("Anomaly detection failed", anomaly_result.error_message or "Unknown error")
            
            # Stage 3: Generate Suggestions
            suggestions_result = self._generate_suggestions(ingestion_result.data, anomaly_result.data)
            
            # Stage 4: Compile Results
            final_results = self._compile_final_results(
                ingestion_result, anomaly_result, suggestions_result
            )
            
            self.workflow_state["current_stage"] = "completed"
            self.workflow_state["end_time"] = datetime.now()
            
            logger.info("Multi-agent workflow completed successfully")
            return final_results
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            logger.error(error_msg)
            return self._create_error_response("Workflow failed", error_msg)
    
    def _run_data_ingestion(self, input_data: Dict[str, Any]) -> AgentResult:
        """Run the data ingestion stage."""
        logger.info("Stage 1: Running data ingestion")
        self.workflow_state["current_stage"] = "data_ingestion"
        
        result = self.data_agent.process(input_data)
        self.workflow_state["results"]["data_ingestion"] = {
            "success": result.success,
            "timestamp": result.timestamp,
            "company_count": result.data.get("count", 0) if result.success else 0,
            "error": result.error_message if not result.success else None
        }
        
        return result
    
    def _run_anomaly_detection(self, company_data: Dict[str, Any]) -> AgentResult:
        """Run the anomaly detection stage."""
        logger.info("Stage 2: Running anomaly detection")
        self.workflow_state["current_stage"] = "anomaly_detection"
        
        result = self.anomaly_agent.process(company_data)
        self.workflow_state["results"]["anomaly_detection"] = {
            "success": result.success,
            "timestamp": result.timestamp,
            "anomaly_count": result.data.get("summary", {}).get("total_anomalies", 0) if result.success else 0,
            "anomaly_rate": result.data.get("summary", {}).get("anomaly_rate", 0) if result.success else 0,
            "error": result.error_message if not result.success else None
        }
        
        return result
    
    def _generate_suggestions(self, company_data: Dict[str, Any], anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate suggestions for detected anomalies."""
        logger.info("Stage 3: Generating AI-powered suggestions")
        self.workflow_state["current_stage"] = "suggestion_generation"
        
        suggestions = {
            "sector_suggestions": [],
            "turnover_suggestions": [],
            "total_suggestions": 0
        }
        
        try:
            companies = company_data.get("companies", [])
            
            # Generate sector classification suggestions
            sector_result = self.sector_agent.process(companies)
            if sector_result.success:
                suggestions["sector_suggestions"] = sector_result.data.get("suggestions", [])
            
            # Generate turnover estimation suggestions
            turnover_result = self.turnover_agent.process(companies)
            if turnover_result.success:
                suggestions["turnover_suggestions"] = turnover_result.data.get("suggestions", [])
            
            suggestions["total_suggestions"] = (
                len(suggestions["sector_suggestions"]) + 
                len(suggestions["turnover_suggestions"])
            )
            
            self.workflow_state["results"]["suggestion_generation"] = {
                "success": True,
                "timestamp": datetime.now(),
                "sector_suggestions": len(suggestions["sector_suggestions"]),
                "turnover_suggestions": len(suggestions["turnover_suggestions"]),
                "total_suggestions": suggestions["total_suggestions"]
            }
            
        except Exception as e:
            error_msg = f"Suggestion generation failed: {str(e)}"
            logger.error(error_msg)
            self.workflow_state["results"]["suggestion_generation"] = {
                "success": False,
                "timestamp": datetime.now(),
                "error": error_msg
            }
        
        return suggestions
    
    def _compile_final_results(self, ingestion_result: AgentResult, anomaly_result: AgentResult, suggestions_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compile final workflow results."""
        logger.info("Stage 4: Compiling final results")
        
        # Calculate workflow duration
        duration = (datetime.now() - self.workflow_state["start_time"]).total_seconds()
        
        return {
            "workflow_info": {
                "session_id": self.session_id,
                "status": "completed",
                "duration_seconds": duration,
                "stages_completed": len([r for r in self.workflow_state["results"].values() if r.get("success", False)])
            },
            "data_summary": {
                "companies_processed": ingestion_result.data.get("count", 0) if ingestion_result.success else 0,
                "anomalies_detected": anomaly_result.data.get("summary", {}).get("total_anomalies", 0) if anomaly_result.success else 0,
                "suggestions_generated": suggestions_result.get("total_suggestions", 0),
                "data_quality_score": self._calculate_data_quality_score(anomaly_result)
            },
            "raw_data": {
                "companies": ingestion_result.data.get("companies", []) if ingestion_result.success else [],
                "dataframe": ingestion_result.data.get("dataframe") if ingestion_result.success else None,
                "anomalies": anomaly_result.data.get("anomalies", []) if anomaly_result.success else [],
                "anomaly_summary": anomaly_result.data.get("summary", {}) if anomaly_result.success else {}
            },
            "suggestions": {
                "sector_classifications": suggestions_result.get("sector_suggestions", []),
                "turnover_estimations": suggestions_result.get("turnover_suggestions", []),
                "total_count": suggestions_result.get("total_suggestions", 0),
                "high_confidence": len([s for s in (suggestions_result.get("sector_suggestions", []) + suggestions_result.get("turnover_suggestions", [])) if getattr(s, 'confidence', 0) > 0.8]),
                "medium_confidence": len([s for s in (suggestions_result.get("sector_suggestions", []) + suggestions_result.get("turnover_suggestions", [])) if 0.6 <= getattr(s, 'confidence', 0) <= 0.8]),
                "low_confidence": len([s for s in (suggestions_result.get("sector_suggestions", []) + suggestions_result.get("turnover_suggestions", [])) if getattr(s, 'confidence', 0) < 0.6])
            },
            "workflow_state": self.workflow_state,
            "next_steps": self._generate_next_steps()
        }
    
    def _calculate_data_quality_score(self, anomaly_result: AgentResult) -> float:
        """Calculate overall data quality score."""
        if not anomaly_result.success:
            return 0.0
        
        summary = anomaly_result.data.get("summary", {})
        anomaly_rate = summary.get("anomaly_rate", 1.0)
        
        # Data quality score = 100% - anomaly rate
        return max(0.0, (1.0 - anomaly_rate) * 100)
    
    def _generate_next_steps(self) -> List[str]:
        """Generate recommended next steps based on workflow results."""
        next_steps = []
        
        # Check if suggestions were generated
        if self.workflow_state["results"].get("suggestion_generation", {}).get("success"):
            next_steps.append("Review AI-generated suggestions in the analyst interface")
            next_steps.append("Accept or reject suggestions based on domain expertise")
            next_steps.append("Implement approved corrections in source systems")
        
        # Check for high anomaly rates
        anomaly_rate = self.workflow_state["results"].get("anomaly_detection", {}).get("anomaly_rate", 0)
        if anomaly_rate > 0.3:
            next_steps.append("Investigate data sources for systematic quality issues")
            next_steps.append("Consider additional validation rules")
        
        # General recommendations
        next_steps.extend([
            "Set up automated monitoring for data quality",
            "Schedule regular anomaly detection runs",
            "Train models with analyst feedback for improved accuracy"
        ])
        
        return next_steps
    
    def _validate_workflow_results(self, results: Dict[str, Any]) -> bool:
        """
        Validate that workflow results have the expected structure.
        
        Args:
            results: Workflow results dictionary
            
        Returns:
            True if results have valid structure, False otherwise
        """
        try:
            # Check for required top-level keys
            if not isinstance(results, dict):
                return False
                
            # Check for data key and structure
            if "data" not in results:
                return False
                
            data = results["data"]
            if not isinstance(data, dict):
                return False
                
            # Check for companies key which is needed for document processing
            if "companies" not in data:
                return False
                
            companies = data["companies"]
            if not isinstance(companies, list):
                return False
                
            return True
            
        except Exception:
            return False
    
    def _create_error_response(self, stage: str, error_message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        duration = (datetime.now() - self.workflow_state["start_time"]).total_seconds()
        
        return {
            "workflow_info": {
                "session_id": self.session_id,
                "status": "failed",
                "failed_stage": stage,
                "duration_seconds": duration,
                "error_message": error_message
            },
            "workflow_state": self.workflow_state,
            "next_steps": [
                "Check configuration and API credentials",
                "Verify data sources are accessible",
                "Review error logs for detailed information"
            ]
        }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        return {
            "session_id": self.session_id,
            "current_stage": self.workflow_state["current_stage"],
            "start_time": self.workflow_state["start_time"],
            "duration_seconds": (datetime.now() - self.workflow_state["start_time"]).total_seconds(),
            "stage_results": self.workflow_state["results"]
        }
    
    def export_results(self, file_path: Optional[str] = None) -> str:
        """Export workflow results to JSON file."""
        if not file_path:
            file_path = f"workflow_results_{self.session_id}.json"
        
        try:
            # Convert workflow state for JSON serialization
            export_data = {
                "session_id": self.session_id,
                "workflow_state": self.workflow_state,
                "export_timestamp": datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Workflow results exported to {file_path}")
            return file_path
            
        except Exception as e:
            error_msg = f"Failed to export results: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def run_enhanced_workflow_with_documents(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run enhanced workflow including document processing for revenue verification.
        
        Args:
            input_data: Dictionary containing:
                - company_numbers: List of Companies House company numbers
                - enable_document_processing: Whether to download and analyze documents
                - fallback_enabled: Whether to use tiered extraction fallback
                - rag_queries: Optional list of custom RAG queries
        
        Returns:
            Dictionary with comprehensive results including document analysis
        """
        try:
            logger.info("Starting enhanced workflow with document processing")
            
            # Stage 1: Run standard workflow first
            standard_results = self.run_complete_workflow(input_data)
            
            if not standard_results.get("success", False):
                return standard_results
            
            # Validate data structure before proceeding with document processing
            if not self._validate_workflow_results(standard_results):
                error_msg = "Standard workflow results missing required data structure"
                logger.error(error_msg)
                return self._create_error_response("Enhanced workflow failed", error_msg)
            
            # Stage 2: Document processing (if enabled)
            if input_data.get("enable_document_processing", False):
                document_results = self._run_document_processing_stage(
                    standard_results["data"]["companies"],
                    input_data
                )
                
                # Merge document results into standard results
                standard_results["data"]["document_processing"] = document_results
                
                # Update workflow state
                self.workflow_state["document_processing"] = document_results
            
            # Stage 3: Enhanced analysis with document data
            if "document_processing" in standard_results["data"]:
                enhanced_analysis = self._run_enhanced_analysis(
                    standard_results["data"]["companies"],
                    document_results
                )
                standard_results["data"]["enhanced_analysis"] = enhanced_analysis
            
            logger.info("Enhanced workflow completed successfully")
            return standard_results
            
        except Exception as e:
            error_msg = f"Enhanced workflow execution failed: {str(e)}"
            logger.error(error_msg)
            return self._create_error_response("Enhanced workflow failed", error_msg)
    
    def _run_document_processing_stage(self, companies: List[Dict[str, Any]], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run document download and processing stage."""
        logger.info("Stage: Document Processing")
        self.workflow_state["current_stage"] = "document_processing"
        
        try:
            # Step 1: Download documents
            download_results = []
            for company in companies[:5]:  # Limit to 5 companies for demo
                try:
                    download_result = self.document_agent.process({
                        "company_number": company.get("company_number"),
                        "document_types": ["annual-accounts"],
                        "max_documents": 1
                    })
                    
                    if download_result.success:
                        download_results.extend(download_result.data.get("downloaded_documents", []))
                    
                except Exception as e:
                    logger.warning(f"Document download failed for company {company.get('company_number')}: {str(e)}")
            
            # Step 2: Smart financial extraction
            extraction_results = []
            if download_results:
                extraction_result = self.extraction_agent.process({
                    "documents": download_results,
                    "extraction_targets": ["revenue", "profit_before_tax"],
                    "fallback_enabled": input_data.get("fallback_enabled", True)
                })
                
                if extraction_result.success:
                    extraction_results = extraction_result.data.get("extraction_results", [])
            
            # Step 3: RAG analysis (if requested)
            rag_results = []
            if input_data.get("rag_queries") and download_results:
                rag_queries = [
                    SemanticQuery(
                        query_text=query.get("query_text", ""),
                        query_type=query.get("query_type", "financial_data"),
                        expected_data_type=query.get("expected_data_type", "numeric")
                    )
                    for query in input_data["rag_queries"]
                ]
                
                rag_result = self.rag_agent.process({
                    "documents": download_results,
                    "queries": rag_queries,
                    "rebuild_index": True
                })
                
                if rag_result.success:
                    rag_results = rag_result.data.get("rag_results", [])
            
            return {
                "download_summary": {
                    "total_documents": len(download_results),
                    "successful_downloads": len([d for d in download_results if d]),
                },
                "extraction_summary": {
                    "total_extractions": len(extraction_results),
                    "successful_extractions": len([e for e in extraction_results if e.confidence > 0.5]),
                    "average_confidence": sum(e.confidence for e in extraction_results) / len(extraction_results) if extraction_results else 0.0
                },
                "rag_summary": {
                    "total_queries": len(rag_results),
                    "successful_queries": len([r for r in rag_results if r.confidence > 0.5])
                },
                "downloaded_documents": download_results,
                "extraction_results": extraction_results,
                "rag_results": rag_results
            }
            
        except Exception as e:
            logger.error(f"Document processing stage failed: {str(e)}")
            return {
                "error": str(e),
                "downloaded_documents": [],
                "extraction_results": [],
                "rag_results": []
            }
    
    def _run_enhanced_analysis(self, companies: List[Dict[str, Any]], document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run enhanced analysis comparing reported vs extracted financial data."""
        logger.info("Stage: Enhanced Analysis")
        self.workflow_state["current_stage"] = "enhanced_analysis"
        
        try:
            enhanced_insights = []
            extraction_results = document_data.get("extraction_results", [])
            
            # Compare reported vs extracted revenue data
            for i, company in enumerate(companies[:len(extraction_results)]):
                if i < len(extraction_results):
                    extraction = extraction_results[i]
                    
                    # Get extracted revenue
                    extracted_revenue = None
                    if extraction.financial_data and extraction.financial_data.revenue:
                        extracted_revenue = extraction.financial_data.revenue
                    
                    # Get reported revenue from company data
                    reported_revenue = company.get("turnover")
                    
                    # Analyze discrepancy
                    insight = self._analyze_revenue_discrepancy(
                        company, reported_revenue, extracted_revenue, extraction
                    )
                    enhanced_insights.append(insight)
            
            # Generate summary statistics
            total_discrepancies = len([i for i in enhanced_insights if i.get("has_discrepancy")])
            avg_discrepancy_rate = sum(i.get("discrepancy_percentage", 0) for i in enhanced_insights) / len(enhanced_insights) if enhanced_insights else 0
            
            return {
                "enhanced_insights": enhanced_insights,
                "summary": {
                    "total_companies_analyzed": len(enhanced_insights),
                    "companies_with_discrepancies": total_discrepancies,
                    "average_discrepancy_rate": avg_discrepancy_rate,
                    "high_confidence_extractions": len([i for i in enhanced_insights if i.get("extraction_confidence", 0) > 0.8])
                }
            }
            
        except Exception as e:
            logger.error(f"Enhanced analysis failed: {str(e)}")
            return {"error": str(e), "enhanced_insights": []}
    
    def _analyze_revenue_discrepancy(self, company: Dict[str, Any], reported_revenue: Optional[float], 
                                   extracted_revenue: Optional[float], extraction_result) -> Dict[str, Any]:
        """Analyze discrepancy between reported and extracted revenue."""
        try:
            company_name = company.get("company_name", "Unknown")
            company_number = company.get("company_number", "Unknown")
            
            if reported_revenue is None and extracted_revenue is None:
                return {
                    "company_name": company_name,
                    "company_number": company_number,
                    "has_discrepancy": False,
                    "analysis": "No revenue data available for comparison",
                    "extraction_confidence": extraction_result.confidence if extraction_result else 0.0
                }
            
            if reported_revenue is None or extracted_revenue is None:
                return {
                    "company_name": company_name,
                    "company_number": company_number,
                    "has_discrepancy": True,
                    "reported_revenue": reported_revenue,
                    "extracted_revenue": extracted_revenue,
                    "analysis": "Revenue data missing from one source",
                    "extraction_confidence": extraction_result.confidence if extraction_result else 0.0
                }
            
            # Calculate discrepancy
            discrepancy = abs(reported_revenue - extracted_revenue)
            discrepancy_percentage = (discrepancy / max(reported_revenue, extracted_revenue)) * 100
            
            has_significant_discrepancy = discrepancy_percentage > 10  # 10% threshold
            
            return {
                "company_name": company_name,
                "company_number": company_number,
                "reported_revenue": reported_revenue,
                "extracted_revenue": extracted_revenue,
                "discrepancy_amount": discrepancy,
                "discrepancy_percentage": discrepancy_percentage,
                "has_discrepancy": has_significant_discrepancy,
                "analysis": f"{'Significant' if has_significant_discrepancy else 'Minor'} discrepancy of {discrepancy_percentage:.1f}%",
                "extraction_confidence": extraction_result.confidence if extraction_result else 0.0,
                "extraction_method": extraction_result.extraction_method.value if extraction_result else "unknown"
            }
            
        except Exception as e:
            return {
                "company_name": company.get("company_name", "Unknown"),
                "company_number": company.get("company_number", "Unknown"),
                "has_discrepancy": False,
                "analysis": f"Analysis failed: {str(e)}",
                "extraction_confidence": 0.0
            }
