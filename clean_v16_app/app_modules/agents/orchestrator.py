"""
Multi-Agent Orchestrator

This module provides the MultiAgentOrchestrator class that coordinates multiple AI agents
for enhanced SIC prediction and company analysis. It integrates with the existing
AI reasoning agent and other components to provide comprehensive AI-powered insights.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentResult
from .ai_reasoning_agent import AIReasoningAgent

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator(BaseAgent):
    """
    Orchestrates multiple AI agents for comprehensive company analysis and SIC prediction.
    
    This orchestrator coordinates:
    - AI Reasoning Agent for intelligent explanations
    - SIC matching and prediction logic
    - Companies House data validation
    - Confidence scoring and analysis
    """
    
    def __init__(self):
        super().__init__("Multi-Agent Orchestrator")
        self.ai_reasoning_agent = None
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize all sub-agents"""
        try:
            self.ai_reasoning_agent = AIReasoningAgent()
            self.log_activity("AI Reasoning Agent initialized successfully", "INFO")
        except Exception as e:
            self.log_activity(f"Failed to initialize AI Reasoning Agent: {e}", "ERROR")
            self.ai_reasoning_agent = None
    
    def process_company(self, company_data: Dict[str, Any]) -> AgentResult:
        """
        Process company data through the multi-agent system.
        
        Args:
            company_data: Dictionary containing company information
            
        Returns:
            AgentResult with orchestrated analysis results
        """
        try:
            start_time = datetime.now()
            
            # Extract company information
            company_name = company_data.get('company_name', '')
            business_description = company_data.get('business_description', '')
            current_sic = company_data.get('uk_sic_2007_code', '')
            predicted_sic = company_data.get('predicted_sic_code', '')
            
            self.log_activity(f"Processing company: {company_name}", "INFO")
            
            # Step 1: Analyze company context using AI Reasoning Agent
            reasoning_result = None
            if self.ai_reasoning_agent and business_description:
                try:
                    reasoning_input = {
                        'company_name': company_name,
                        'business_description': business_description,
                        'current_sic_code': current_sic,
                        'predicted_sic_code': predicted_sic
                    }
                    
                    reasoning_result = self.ai_reasoning_agent.process(reasoning_input)
                    self.log_activity("AI reasoning analysis completed", "INFO")
                    
                except Exception as e:
                    self.log_activity(f"AI reasoning failed: {e}", "ERROR")
            
            # Step 2: Generate SIC prediction if needed
            prediction_data = self._generate_sic_prediction(company_data)
            
            # Step 3: Combine results
            orchestration_result = {
                'company_name': company_name,
                'predicted_sic_code': prediction_data.get('predicted_sic_code', current_sic),
                'confidence_score': prediction_data.get('confidence_score', 0.0),
                'ai_reasoning': reasoning_result.data if reasoning_result and reasoning_result.success else None,
                'prediction_method': 'multi_agent_orchestrator',
                'orchestration_timestamp': datetime.now().isoformat(),
                'agents_used': ['AI Reasoning Agent'] if reasoning_result and reasoning_result.success else [],
                'execution_time_ms': int((datetime.now() - start_time).total_seconds() * 1000)
            }
            
            return AgentResult(
                agent_name=self.name,
                timestamp=datetime.now(),
                success=True,
                data=orchestration_result,
                confidence=prediction_data.get('confidence_score', 0.0)
            )
            
        except Exception as e:
            self.log_activity(f"Orchestration failed: {e}", "ERROR")
            return AgentResult(
                agent_name=self.name,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e),
                confidence=0.0
            )
    
    def _generate_sic_prediction(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SIC prediction using available data and agents.
        
        Args:
            company_data: Company information dictionary
            
        Returns:
            Dictionary with prediction results
        """
        try:
            # If we already have a predicted SIC, use it
            if company_data.get('predicted_sic_code'):
                return {
                    'predicted_sic_code': company_data.get('predicted_sic_code'),
                    'confidence_score': company_data.get('confidence_score', 0.0)
                }
            
            # Otherwise, use current SIC as baseline
            current_sic = company_data.get('uk_sic_2007_code', '82990')
            
            # For now, return the current SIC with moderate confidence
            # This can be enhanced with more sophisticated prediction logic
            return {
                'predicted_sic_code': current_sic,
                'confidence_score': 0.7  # Moderate confidence for existing SIC
            }
            
        except Exception as e:
            self.log_activity(f"SIC prediction failed: {e}", "ERROR")
            return {
                'predicted_sic_code': '82990',  # Default fallback SIC
                'confidence_score': 0.1
            }
    
    def generate_ai_reasoning(self, company_data: Dict[str, Any]) -> str:
        """
        Generate AI reasoning explanation for a company's SIC classification.
        
        Args:
            company_data: Company information dictionary
            
        Returns:
            AI-generated reasoning string
        """
        try:
            if not self.ai_reasoning_agent:
                return "AI reasoning agent not available - using fallback analysis"
            
            # Debug: Log the company data being passed
            print(f"🔍 DEBUG Orchestrator - Company data received: {company_data}")
            
            # Determine the analysis focus based on whether we have a predicted SIC
            current_sic = company_data.get('uk_sic_2007_code', '')
            predicted_sic = company_data.get('predicted_sic_code', '')
            
            # If we have a predicted SIC that's different from current, focus on new classification
            # Otherwise, explain why the current SIC has low accuracy
            if predicted_sic and predicted_sic != current_sic:
                analysis_focus = 'new_classification'
            else:
                analysis_focus = 'original_classification'
            
            reasoning_input = {
                'company_name': company_data.get('company_name', ''),
                'company_description': company_data.get('business_description', ''),
                'current_sic': current_sic,
                'new_sic': predicted_sic,
                'old_accuracy': company_data.get('existing_sic_confidence', company_data.get('confidence_score', 0.0)),
                'new_accuracy': company_data.get('confidence_score', 0.0),
                'analysis_focus': analysis_focus
            }
            
            # Debug: Log the reasoning input being passed to AI agent
            print(f"🔍 DEBUG Orchestrator - Reasoning input: {reasoning_input}")
            
            reasoning_result = self.ai_reasoning_agent.process(reasoning_input)
            
            if reasoning_result.success:
                # Extract the reasoning string from the data dictionary
                if isinstance(reasoning_result.data, dict) and 'reasoning' in reasoning_result.data:
                    return reasoning_result.data['reasoning']
                elif isinstance(reasoning_result.data, str):
                    return reasoning_result.data
                else:
                    return str(reasoning_result.data)
            else:
                return f"AI reasoning generation failed: {reasoning_result.error_message}"
                
        except Exception as e:
            self.log_activity(f"AI reasoning generation failed: {e}", "ERROR")
            return f"AI reasoning temporarily unavailable: {str(e)}"
    
    def analyze_company_context(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze company context using all available agents.
        
        Args:
            company_data: Company information dictionary
            
        Returns:
            Dictionary with analysis results
        """
        try:
            start_time = datetime.now()
            
            # Generate AI reasoning
            ai_reasoning = self.generate_ai_reasoning(company_data)
            
            # Calculate confidence metrics
            confidence_metrics = self._calculate_confidence_metrics(company_data)
            
            # Compile analysis result
            analysis_result = {
                'ai_reasoning': ai_reasoning,
                'confidence_metrics': confidence_metrics,
                'analysis_timestamp': datetime.now().isoformat(),
                'execution_time_ms': int((datetime.now() - start_time).total_seconds() * 1000),
                'orchestrator_version': '1.0.0'
            }
            
            return analysis_result
            
        except Exception as e:
            self.log_activity(f"Company context analysis failed: {e}", "ERROR")
            return {
                'ai_reasoning': f"Analysis failed: {str(e)}",
                'confidence_metrics': {'overall_confidence': 0.0},
                'analysis_timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _calculate_confidence_metrics(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confidence metrics for the analysis.
        
        Args:
            company_data: Company information dictionary
            
        Returns:
            Dictionary with confidence metrics
        """
        try:
            # Base confidence from existing score
            base_confidence = company_data.get('confidence_score', 0.0)
            
            # Adjust confidence based on data quality
            data_quality_score = self._assess_data_quality(company_data)
            
            # Overall confidence is combination of base confidence and data quality
            overall_confidence = (base_confidence + data_quality_score) / 2
            
            return {
                'overall_confidence': min(overall_confidence, 1.0),
                'base_confidence': base_confidence,
                'data_quality_score': data_quality_score,
                'has_business_description': bool(company_data.get('business_description')),
                'has_predicted_sic': bool(company_data.get('predicted_sic_code')),
                'assessment_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_activity(f"Confidence metrics calculation failed: {e}", "ERROR")
            return {
                'overall_confidence': 0.0,
                'error': str(e)
            }
    
    def _assess_data_quality(self, company_data: Dict[str, Any]) -> float:
        """
        Assess the quality of available company data.
        
        Args:
            company_data: Company information dictionary
            
        Returns:
            Data quality score (0.0 to 1.0)
        """
        try:
            score = 0.0
            max_score = 5.0
            
            # Check for company name
            if company_data.get('company_name'):
                score += 1.0
            
            # Check for business description
            business_desc = company_data.get('business_description', '')
            if business_desc and len(business_desc) > 20:
                score += 1.5
            elif business_desc:
                score += 0.5
            
            # Check for SIC codes
            if company_data.get('uk_sic_2007_code'):
                score += 1.0
            
            if company_data.get('predicted_sic_code'):
                score += 1.0
            
            # Check for financial data
            if company_data.get('sales_gbp') is not None:
                score += 0.5
            
            return min(score / max_score, 1.0)
            
        except Exception as e:
            self.log_activity(f"Data quality assessment failed: {e}", "ERROR")
            return 0.0
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Main processing method for the orchestrator (BaseAgent interface).
        
        Args:
            data: Input data (should be company data dictionary)
            **kwargs: Additional keyword arguments
            
        Returns:
            AgentResult with orchestration results
        """
        if isinstance(data, dict):
            return self.process_company(data)
        else:
            return AgentResult(
                agent_name=self.name,
                timestamp=datetime.now(),
                success=False,
                error_message="Invalid input data format - expected dictionary",
                confidence=0.0
            )


# Create a default instance for easy import
multi_agent_orchestrator = MultiAgentOrchestrator()