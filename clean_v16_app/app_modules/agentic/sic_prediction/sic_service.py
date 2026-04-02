"""
Agentic SIC Prediction Service

This service provides the main orchestration layer for the intelligent agentic SIC prediction
system. It coordinates the LangGraph workflow execution, manages dependencies, handles
configuration, and provides a clean API interface for integration with existing systems.

Core Responsibilities:
- Orchestrate the complete agentic workflow using LangGraph
- Manage service dependencies and dependency injection
- Handle workflow configuration and customization
- Provide clean API interface for SIC prediction
- Integrate seamlessly with existing infrastructure
- Monitor and track workflow performance

Integration Strategy:
- Zero-impact deployment alongside existing endpoints
- Leverages all existing services and infrastructure
- Maintains backward compatibility with current API
- Provides enhanced capabilities while preserving existing functionality
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

from .workflow_builder import build_agentic_workflow, WorkflowBuilder, LANGGRAPH_AVAILABLE
from .workflow_state import AgenticWorkflowState, WorkflowDecision

logger = logging.getLogger(__name__)


class AgenticSICPredictionService:
    """
    Main orchestration service for intelligent agentic SIC prediction.
    
    This service provides a clean, high-level interface for running the complete
    agentic workflow while managing all the underlying complexity of node coordination,
    state management, and error handling.
    """
    
    def __init__(self, services_container: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the agentic SIC prediction service.
        
        Args:
            services_container: Container with all required service dependencies
                Required services:
                - sqlite_sic_repository: SQLiteSICPredictionRepository
                - companies_house_client: CompaniesHouseClient  
                - enhanced_sic_matcher: EnhancedSICMatcher
                
                Optional services:
                - realtime_reasoning_service: RealtimeReasoningService
                - company_service: CompanyService
                
            config: Optional workflow configuration and customization options
        """
        self.services_container = services_container
        self.config = config or {}
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Initialize workflow builder
        self.workflow_builder = WorkflowBuilder(services_container)
        self.compiled_workflow = None
        
        # Validate configuration
        self.validated_config = self.workflow_builder.validate_config(self.config)
        
        # Performance tracking
        self.execution_stats = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'average_execution_time': 0.0,
            'last_execution_time': None
        }
        
        # Check if LangGraph is available
        if not LANGGRAPH_AVAILABLE:
            self.logger.warning("⚠️ LangGraph not available - agentic features will be limited")
        else:
            # Pre-compile workflow during initialization for instant first prediction
            self.logger.info("🏗️ Pre-compiling workflow during initialization...")
            try:
                self.compiled_workflow = self._compile_workflow(self.validated_config)
                self.logger.info("✅ Workflow pre-compilation complete - ready for instant predictions")
            except Exception as e:
                self.logger.error(f"❌ Workflow pre-compilation failed: {e}")
                self.logger.warning("⚠️ Will compile on first use instead")
        
        self.logger.info("🤖 AgenticSICPredictionService initialized")
    
    def predict_sic_agentic(
        self,
        company_name: str,
        business_description: str = "",
        company_number: str = "",
        address: str = "",
        workflow_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute intelligent agentic SIC prediction for a company.
        
        This is the main entry point for agentic SIC prediction, providing enhanced
        capabilities while maintaining compatibility with existing API patterns.
        
        Args:
            company_name: Name of the company to classify
            business_description: Optional business description for enhanced prediction
            company_number: Optional Companies House number for validation
            address: Optional company address for improved matching
            workflow_config: Optional configuration overrides for this specific prediction
            
        Returns:
            Comprehensive prediction result with agentic enhancements:
            {
                'predicted_sic_code': str,
                'confidence_score': float,
                'prediction_method': str,
                'alternatives': List[Dict],
                'reasoning': str,
                'workflow_summary': Dict,
                'companies_house_validation': Dict,
                'agentic_insights': Dict,
                'execution_time': float,
                'workflow_steps': List[Dict],
                'quality_assessment': Dict
            }
        """
        start_time = datetime.now()
        
        try:
            # 🔍 CRITICAL DEBUG: Confirm method is being called
            print(f"🔍 CRITICAL: predict_sic_agentic called for {company_name}")
            self.logger.info(f"🤖 Starting agentic SIC prediction for: {company_name}")
            
            # Update execution stats
            self.execution_stats['total_predictions'] += 1
            
            # Merge configuration
            effective_config = {**self.validated_config, **(workflow_config or {})}
            effective_config = self.workflow_builder.validate_config(effective_config)
            
            # Check if agentic workflow is available
            print(f"🔍 CRITICAL: LANGGRAPH_AVAILABLE = {LANGGRAPH_AVAILABLE}")
            self.logger.info(f"🔍 CRITICAL: LANGGRAPH_AVAILABLE = {LANGGRAPH_AVAILABLE}")
            
            if not LANGGRAPH_AVAILABLE:
                print(f"❌ CRITICAL: Using fallback - LangGraph not available")
                self.logger.warning("🔄 LANGGRAPH NOT AVAILABLE - Using fallback prediction")
                return self._fallback_prediction(
                    company_name, business_description, company_number, address, start_time
                )
            else:
                print(f"✅ CRITICAL: LangGraph available - proceeding with full agentic workflow")
                self.logger.info("✅ LangGraph available - proceeding with full agentic workflow")
            
            # Compile workflow if needed
            if not self.compiled_workflow:
                self.compiled_workflow = self._compile_workflow(effective_config)
            
            # Prepare initial workflow state
            initial_state = self._prepare_initial_state(
                company_name, business_description, company_number, address, effective_config
            )
            
            # Execute the agentic workflow
            final_state = self._execute_workflow(initial_state)
            
            # Process and format the results
            result = self._format_agentic_result(final_state, start_time)
            
            # Update success statistics
            self.execution_stats['successful_predictions'] += 1
            self._update_execution_stats(start_time)
            
            self.logger.info(f"✅ Agentic prediction completed: {result['predicted_sic_code']} (confidence: {result['confidence_score']:.2f})")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Agentic SIC prediction failed: {e}")
            
            # Update failure statistics
            self.execution_stats['failed_predictions'] += 1
            self._update_execution_stats(start_time)
            
            # Return fallback result
            return self._create_error_result(company_name, str(e), start_time)
    
    def _compile_workflow(self, config: Dict[str, Any]) -> Any:
        """Compile the LangGraph workflow with the given configuration"""
        try:
            self.logger.info("🏗️ Compiling agentic workflow")
            compiled = build_agentic_workflow(self.services_container, config)
            self.logger.info("✅ Workflow compilation successful")
            return compiled
        except Exception as e:
            self.logger.error(f"❌ Workflow compilation failed: {e}")
            raise
    
    def _prepare_initial_state(
        self,
        company_name: str,
        business_description: str,
        company_number: str,
        address: str,
        config: Dict[str, Any]
    ) -> AgenticWorkflowState:
        """Prepare the initial state for workflow execution"""
        
        # Create company data structure
        company_data = {
            'company_name': company_name,
            'business_description': business_description,
            'company_number': company_number,
            'address': address,
            'data_source': 'api_request',
            'timestamp': datetime.now().isoformat()
        }
        
        # Initialize workflow state
        initial_state: AgenticWorkflowState = {
            'company_data': company_data,
            'workflow_config': config,
            'workflow_decisions': [],
            'node_confidence_scores': {},
            'current_node': 'initialization',
            'errors': [],
            'warnings': [],
            'fallback_triggers': [],
            'node_execution_times': {},
            'workflow_steps': [
                {
                    'step': 'Workflow Initialization',
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'details': {
                        'company_name': company_name,
                        'has_business_description': bool(business_description),
                        'has_company_number': bool(company_number),
                        'has_address': bool(address),
                        'config_enabled_features': [k for k, v in config.items() if v is True]
                    },
                    'icon': '🚀',
                    'duration_ms': 0
                }
            ]
        }
        
        return initial_state
    
    def _execute_workflow(self, initial_state: AgenticWorkflowState) -> AgenticWorkflowState:
        """Execute the compiled LangGraph workflow"""
        try:
            self.logger.info("⚡ Executing agentic workflow")
            
            # Execute the workflow using LangGraph
            result = self.compiled_workflow.invoke(initial_state)
            
            self.logger.info("✅ Workflow execution completed")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Workflow execution failed: {e}")
            
            # Create error state
            error_state = initial_state.copy()
            error_state.update({
                'errors': initial_state.get('errors', []) + [f"Workflow execution failed: {str(e)}"],
                'fallback_triggers': initial_state.get('fallback_triggers', []) + ['workflow_execution_error'],
                'workflow_completed': False,
                'current_node': 'execution_error'
            })
            
            return error_state
    
    def _format_agentic_result(self, final_state: AgenticWorkflowState, start_time: datetime) -> Dict[str, Any]:
        """Format the final workflow state into a comprehensive API response"""
        self.logger.info("🔍 ENTERING _format_agentic_result method")
        
        # Extract core prediction data
        ai_prediction = final_state.get('ai_prediction', {})
        evaluation_result = final_state.get('evaluation_result', {})
        enhanced_reasoning = final_state.get('enhanced_reasoning', {})
        workflow_summary = final_state.get('workflow_summary', {})
        ch_sic_data = final_state.get('ch_sic_data', {})
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Generate dashboard reasoning - ALWAYS generate, even without full workflow
        dashboard_reasoning = {}
        try:
            from app_modules.agentic.sic_prediction.nodes.reasoning_generator_node import ReasoningGeneratorNode
            reasoning_node = ReasoningGeneratorNode()
            dashboard_reasoning = reasoning_node.generate_dashboard_reasoning(final_state)
            self.logger.info(f"✅ Generated dashboard reasoning successfully: {dashboard_reasoning}")
            self.logger.debug(f"Dashboard reasoning keys: {list(dashboard_reasoning.keys()) if dashboard_reasoning else 'None'}")
            if dashboard_reasoning:
                self.logger.debug(f"AI reasoning value: '{dashboard_reasoning.get('ai_reasoning', 'MISSING')}'")
                self.logger.debug(f"CH comparison value: '{dashboard_reasoning.get('ch_comparison', 'MISSING')}'")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not generate full dashboard reasoning: {e}")
            # Fallback: Generate basic reasoning from available data
            # Use CH data from result if available, otherwise from final_state
            effective_ch_data = ch_sic_data
            if not effective_ch_data or not effective_ch_data.get('success'):
                # Try to get CH data from result's companies_house_validation
                ch_validation = final_state.get('companies_house_validation') if hasattr(final_state, 'get') else None
                if ch_validation and ch_validation.get('success'):
                    effective_ch_data = ch_validation
            
            dashboard_reasoning = self._generate_fallback_reasoning(ai_prediction, effective_ch_data, final_state)
        
        # Log final dashboard reasoning values before building result
        self.logger.debug(f"Final AI reasoning for result: '{dashboard_reasoning.get('ai_reasoning', 'EMPTY')}'")
        self.logger.debug(f"Final CH comparison for result: '{dashboard_reasoning.get('ch_comparison', 'EMPTY')}'")
        
        # Extract company data for current SIC
        company_data = final_state.get('company_data', {})
        
        # DEBUG: Log company_data contents before formatting result
        self.logger.info(f"🔍 COMPANY_DATA in _format_agentic_result:")
        self.logger.info(f"   - Type: {type(company_data)}")
        self.logger.info(f"   - existing_sic_confidence: {company_data.get('existing_sic_confidence') if hasattr(company_data, 'get') else 'NO GET METHOD'}")
        self.logger.info(f"   - existing_sic_code: {company_data.get('existing_sic_code') if hasattr(company_data, 'get') else 'NO GET METHOD'}")
        self.logger.info(f"   - sic_codes: {company_data.get('sic_codes') if hasattr(company_data, 'get') else 'NO GET METHOD'}")
        self.logger.info(f"   - uk_sic_2007_code: {company_data.get('uk_sic_2007_code') if hasattr(company_data, 'get') else 'NO GET METHOD'}")
        if hasattr(company_data, 'get'):
            self.logger.info(f"   - all keys: {list(company_data.keys()) if company_data else 'EMPTY DICT'}")
        
        # Build comprehensive result with safe data access
        result = {
            # Core prediction results (compatible with existing API)
            'predicted_sic_code': ai_prediction.get('predicted_sic_code', '') if ai_prediction else '',
            'confidence_score': ai_prediction.get('confidence_score', 0.0) if ai_prediction else 0.0,
            'prediction_method': ai_prediction.get('prediction_method', 'agentic_workflow') if ai_prediction else 'agentic_workflow',
            'alternatives': ai_prediction.get('alternatives', []) if ai_prediction else [],
            'reasoning': enhanced_reasoning.get('core_reasoning', ai_prediction.get('reasoning', '') if ai_prediction else '') if enhanced_reasoning else '',
            
            # Current SIC from authoritative company data (required for UI consistency)
            'current_sic': company_data.get('existing_sic_code') or company_data.get('uk_sic_2007_code') or company_data.get('sic_codes') if company_data else None,
            'existing_sic_confidence': company_data.get('existing_sic_confidence') if company_data else None,
            
            # Dashboard-specific reasoning (2-3 sentences)  
            'ai_reasoning_explanation': dashboard_reasoning.get('ai_reasoning', ''),
            'ch_comparison_explanation': dashboard_reasoning.get('ch_comparison', ''),
            
            # Enhanced agentic features
            'agentic_insights': {
                'workflow_quality_score': evaluation_result.get('quality_score', 0.0) if evaluation_result else 0.0,
                'ch_vs_ai_agreement': evaluation_result.get('ch_vs_ai_agreement', False) if evaluation_result else False,
                'confidence_delta': evaluation_result.get('confidence_delta', 0.0) if evaluation_result else 0.0,
                'recommended_action': evaluation_result.get('recommended_action', 'accept_ai') if evaluation_result else 'accept_ai',
                'refinement_suggestions': evaluation_result.get('refinement_suggestions', []) if evaluation_result else [],
                'methodology_explanation': enhanced_reasoning.get('methodology_explanation', '') if enhanced_reasoning else '',
                'validation_reasoning': enhanced_reasoning.get('validation_reasoning', '') if enhanced_reasoning else '',
                'transparency_notes': enhanced_reasoning.get('transparency_notes', '') if enhanced_reasoning else ''
            },
            
            # Companies House validation data
            'companies_house_validation': {
                'success': ch_sic_data.get('success', False) if ch_sic_data else False,
                'sic_codes': ch_sic_data.get('sic_codes', []) if ch_sic_data else [],
                'confidence': ch_sic_data.get('confidence', 0.0) if ch_sic_data else 0.0,
                'method_used': ch_sic_data.get('method_used', '') if ch_sic_data else '',
                'company_data': ch_sic_data.get('company_data', {}) if ch_sic_data else {}
            },
            
            # Workflow execution details
            'workflow_summary': {
                'completed_successfully': workflow_summary.get('workflow_completed', final_state.get('workflow_completed', False)),
                'total_execution_time': execution_time,
                'overall_confidence': workflow_summary.get('overall_confidence', 0.0),
                'nodes_executed': workflow_summary.get('nodes_executed', []),
                'errors_count': len(final_state.get('errors', [])),
                'warnings_count': len(final_state.get('warnings', [])),
                'fallback_triggers': final_state.get('fallback_triggers', [])
            },
            
            # Quality assessment
            'quality_assessment': {
                'node_confidence_scores': final_state.get('node_confidence_scores', {}),
                'evaluation_score': evaluation_result.get('quality_score', 0.0),
                'reasoning_quality': final_state.get('reasoning_quality', {}).get('score', 0.0),
                'data_quality_impact': enhanced_reasoning.get('data_quality_impact', ''),
                'overall_assessment': self._assess_overall_quality(final_state)
            },
            
            # Workflow steps for frontend visualization
            'workflow_steps': final_state.get('workflow_steps', []),
            
            # Execution metadata
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat(),
            'workflow_version': '1.0.0',
            'agentic_enabled': True,
            'langgraph_version': 'available' if LANGGRAPH_AVAILABLE else 'unavailable'
        }
        
        # 🔍 CRITICAL DEBUG: Log the actual values being set for UI consistency
        self.logger.info(f"🔍 CRITICAL: Setting current_sic = {result['current_sic']}")
        self.logger.info(f"🔍 CRITICAL: Setting existing_sic_confidence = {result['existing_sic_confidence']}")
        self.logger.info(f"🔍 CRITICAL: company_data type = {type(company_data)}")
        self.logger.info(f"🔍 CRITICAL: company_data empty check = {not company_data}")
        if company_data:
            self.logger.info(f"🔍 CRITICAL: existing_sic_code raw = {repr(company_data.get('existing_sic_code'))}")
            self.logger.info(f"🔍 CRITICAL: existing_sic_confidence raw = {repr(company_data.get('existing_sic_confidence'))}")
        
        # Add warnings and errors if present
        if final_state.get('warnings'):
            result['warnings'] = final_state['warnings']
        if final_state.get('errors'):
            result['errors'] = final_state['errors']
        
        # 💾 Save agentic prediction to database including Companies House SIC data
        try:
            # Extract company data from final_state
            company_data = final_state.get('company_data', {})
            self._save_agentic_prediction_to_db(
                company_name=company_data.get('company_name', ''),
                business_description=company_data.get('business_description', ''),
                result=result,
                ch_sic_data=ch_sic_data,
                final_state=final_state
            )
        except Exception as db_save_error:
            self.logger.warning(f"⚠️ Failed to save agentic prediction to database: {db_save_error}")
            # Don't fail the entire prediction if database save fails
        
        return result
    
    def _assess_overall_quality(self, final_state: AgenticWorkflowState) -> str:
        """Assess overall quality of the agentic prediction"""
        evaluation_result = final_state.get('evaluation_result', {})
        quality_score = evaluation_result.get('quality_score', 0.0)
        errors = final_state.get('errors', [])
        fallback_triggers = final_state.get('fallback_triggers', [])
        
        if errors:
            return "poor - errors encountered during workflow execution"
        elif quality_score >= 0.8:
            return "excellent - high confidence with strong validation"
        elif quality_score >= 0.6:
            return "good - acceptable confidence with adequate validation" 
        elif quality_score >= 0.4:
            return "moderate - medium confidence, manual review recommended"
        elif fallback_triggers:
            return "limited - fallback mechanisms triggered, reliability reduced"
        else:
            return "poor - low confidence prediction"
    
    def _fallback_prediction(
        self,
        company_name: str,
        business_description: str,
        company_number: str,
        address: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Provide fallback prediction when LangGraph is not available"""
        
        self.logger.warning("🔄 Using fallback prediction - LangGraph unavailable")
        
        # 🏛️ FIRST: Try to get Companies House SIC codes using both mechanisms
        ch_sic_result = self._try_companies_house_lookup(company_name, company_number, address)
        
        # Attempt to use existing enhanced SIC matcher directly
        predicted_sic = '82990'  # Other business support service activities n.e.c.
        confidence = 0.0
        prediction_explanation = f'Fallback prediction for {company_name} - LangGraph unavailable'
        
        try:
            enhanced_sic_matcher = self.services_container.get('enhanced_sic_matcher')
            if enhanced_sic_matcher and business_description and business_description.strip():
                # Use existing enhanced matching
                matches = enhanced_sic_matcher.find_best_match(business_description, top_n=1)
                
                if matches:
                    best_match = matches[0]
                    predicted_sic = best_match.get('sic_code', '82990')
                    confidence = best_match.get('similarity_score', 0.0)
                    prediction_explanation = f'SIC {predicted_sic} selected based on business description analysis with {confidence*100:.1f}% similarity match'
                else:
                    prediction_explanation = f'SIC {predicted_sic} assigned as generic business classification - no specific matches found for business description'
            else:
                if not business_description or not business_description.strip():
                    prediction_explanation = f'SIC {predicted_sic} assigned as generic business classification - no business description provided for analysis'
                else:
                    prediction_explanation = f'SIC {predicted_sic} assigned as generic business classification - enhanced matcher unavailable'
        
        except Exception as e:
            self.logger.error(f"❌ Enhanced SIC matcher failed: {e}")
            prediction_explanation = f'SIC {predicted_sic} assigned as generic business classification - matcher error occurred'
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
                'predicted_sic_code': predicted_sic,
                'confidence_score': confidence,
                'prediction_method': 'fallback_non_agentic',
                'alternatives': [],
                'reasoning': prediction_explanation,
                # Dashboard reasoning fields - use actual confidence and explanation
                'ai_reasoning_explanation': self._generate_natural_reasoning_for_fallback(predicted_sic, confidence, business_description, company_name),
                'ch_comparison_explanation': f'Companies House Validation: {ch_sic_result.get("status", "unavailable")} - {"SIC codes retrieved from official registry" if ch_sic_result.get("sic_codes") else "No official SIC codes found for comparison"}. Fallback prediction used due to limited agentic capabilities.',
                'agentic_insights': {
                    'workflow_quality_score': 0.2,
                    'ch_vs_ai_agreement': False,
                    'confidence_delta': 0.0,
                    'recommended_action': 'manual_review',
                    'refinement_suggestions': ['Install LangGraph for enhanced agentic capabilities'],
                    'methodology_explanation': 'Non-agentic fallback prediction',
                    'validation_reasoning': 'Limited validation - agentic workflow unavailable',
                    'transparency_notes': 'LangGraph dependency missing - reduced functionality'
                },
                'companies_house_validation': ch_sic_result,
                'workflow_summary': {
                    'completed_successfully': False,
                    'total_execution_time': execution_time,
                    'overall_confidence': confidence,
                    'nodes_executed': ['fallback_only'],
                    'errors_count': 0,
                    'warnings_count': 1,
                    'fallback_triggers': ['langgraph_unavailable']
                },
                'quality_assessment': {
                    'node_confidence_scores': {'fallback': confidence},
                    'evaluation_score': 0.2,
                    'reasoning_quality': 0.1,
                    'data_quality_impact': 'Unable to assess - agentic workflow disabled',
                    'overall_assessment': 'limited - agentic features unavailable'
                },
                'workflow_steps': [
                    {
                        'step': 'Fallback Prediction',
                        'status': 'completed',
                        'timestamp': datetime.now().isoformat(),
                        'details': {'reason': 'LangGraph unavailable'},
                        'icon': '🔄',
                        'duration_ms': int(execution_time * 1000)
                    }
                ],
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat(),
                'workflow_version': '1.0.0',
                'agentic_enabled': False,
                'langgraph_version': 'unavailable',
                'warnings': ['LangGraph not available - using fallback prediction method']
            }
    
    def _create_error_result(self, company_name: str, error_message: str, start_time: datetime) -> Dict[str, Any]:
        """Create error result when all prediction methods fail"""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'predicted_sic_code': '82990',  # Other business support service activities n.e.c. (more appropriate than dormant company)
            'confidence_score': 0.0,
            'prediction_method': 'error_fallback',
            'alternatives': [],
            'reasoning': f'Error occurred during prediction for {company_name}: {error_message}',
            'agentic_insights': {
                'workflow_quality_score': 0.0,
                'ch_vs_ai_agreement': False,
                'confidence_delta': 0.0,
                'recommended_action': 'manual_classification',
                'refinement_suggestions': ['Manual classification required due to system errors'],
                'methodology_explanation': 'Error fallback - all prediction methods failed',
                'validation_reasoning': 'No validation possible due to errors',
                'transparency_notes': f'System error prevented prediction: {error_message}'
            },
            'companies_house_validation': {
                'success': False,
                'sic_codes': [],
                'confidence': 0.0,
                'method_used': 'failed',
                'company_data': {}
            },
            'workflow_summary': {
                'completed_successfully': False,
                'total_execution_time': execution_time,
                'overall_confidence': 0.0,
                'nodes_executed': [],
                'errors_count': 1,
                'warnings_count': 0,
                'fallback_triggers': ['system_error']
            },
            'quality_assessment': {
                'node_confidence_scores': {},
                'evaluation_score': 0.0,
                'reasoning_quality': 0.0,
                'data_quality_impact': 'Unable to assess due to system error',
                'overall_assessment': 'failed - system error occurred'
            },
            'workflow_steps': [
                {
                    'step': 'Error Handling',
                    'status': 'error',
                    'timestamp': datetime.now().isoformat(),
                    'details': {'error': error_message},
                    'icon': '❌',
                    'duration_ms': int(execution_time * 1000)
                }
            ],
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat(),
            'workflow_version': '1.0.0',
            'agentic_enabled': False,
            'langgraph_version': 'error',
            'errors': [error_message]
        }
    
    def _update_execution_stats(self, start_time: datetime) -> None:
        """Update execution statistics"""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Update average execution time
        total_predictions = self.execution_stats['total_predictions']
        current_average = self.execution_stats['average_execution_time']
        
        new_average = ((current_average * (total_predictions - 1)) + execution_time) / total_predictions
        self.execution_stats['average_execution_time'] = new_average
        self.execution_stats['last_execution_time'] = execution_time
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status and health information"""
        return {
            'service_initialized': True,
            'langgraph_available': LANGGRAPH_AVAILABLE,
            'workflow_compiled': self.compiled_workflow is not None,
            'services_configured': {
                'total_services': len(self.services_container),
                'required_services_present': all(
                    srv in self.services_container 
                    for srv in ['sqlite_sic_repository', 'companies_house_client', 'enhanced_sic_matcher']
                ),
                'optional_services_present': {
                    'realtime_reasoning_service': 'realtime_reasoning_service' in self.services_container,
                    'sector_classification_agent': 'sector_classification_agent' in self.services_container,
                    'company_service': 'company_service' in self.services_container
                }
            },
            'configuration': self.validated_config,
            'execution_statistics': self.execution_stats,
            'workflow_info': self.workflow_builder.get_workflow_info() if self.workflow_builder else {},
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_workflow_config_schema(self) -> Dict[str, Any]:
        """Get the schema for workflow configuration options"""
        return self.workflow_builder.get_workflow_config_schema()
    
    def update_configuration(self, new_config: Dict[str, Any]) -> bool:
        """
        Update workflow configuration and recompile if necessary.
        
        Args:
            new_config: New configuration options
            
        Returns:
            True if configuration was updated successfully
        """
        try:
            # Validate new configuration
            validated_config = self.workflow_builder.validate_config(new_config)
            
            # Check if recompilation is needed
            needs_recompilation = (
                validated_config != self.validated_config and 
                self.compiled_workflow is not None
            )
            
            # Update configuration
            self.config.update(new_config)
            self.validated_config = validated_config
            
            # Recompile if necessary
            if needs_recompilation:
                self.logger.info("🔄 Configuration changed - recompiling workflow")
                self.compiled_workflow = None  # Force recompilation on next prediction
            
            self.logger.info("✅ Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Configuration update failed: {e}")
            return False
    
    def _save_agentic_prediction_to_db(self, company_name: str, business_description: str, 
                                     result: Dict[str, Any], ch_sic_data: Any, 
                                     final_state: Any) -> bool:
        """
        Save agentic SIC prediction to database including Companies House SIC data.
        ONLY saves predictions for companies that exist in the companies table.
        
        Args:
            company_name: Company name
            business_description: Business description  
            result: Agentic prediction result
            ch_sic_data: Companies House SIC data
            final_state: Final workflow state
            
        Returns:
            bool: True if saved successfully
        """
        try:
            self.logger.info(f"🔍 DEBUG: Attempting to save agentic prediction for {company_name}")
            
            # Get enhanced SIC matcher from services container
            sic_matcher = self.services_container.get('enhanced_sic_matcher')
            if not sic_matcher:
                self.logger.warning("⚠️ Enhanced SIC matcher not available - cannot save to database")
                return False
            
            self.logger.info(f"✅ DEBUG: Enhanced SIC matcher available: {type(sic_matcher)}")
            
            # MANDATORY: Find company_id - reject if not found
            # Use dual-key validation instead of single company_id lookup
            dual_keys = self._find_company_dual_keys_by_name(company_name)
            if dual_keys:
                company_id, unique_id = dual_keys
            else:
                company_id = None
            if not company_id:
                self.logger.warning(f"� Company '{company_name}' not found in companies table - REJECTING prediction save")
                self.logger.warning(f"� Only predictions for registered companies are allowed to prevent orphaned data")
                return False
                
            self.logger.info(f"✅ DUAL-KEY VALIDATION passed: '{company_name}' (ID: {company_id}, unique_id: '{unique_id}')")
            
            # Get existing company data to preserve existing_sic_confidence
            repository = self.services_container.get('company_repository')
            existing_sic_confidence = None
            if repository:
                try:
                    company_data = repository.get_company_by_id(company_id)
                    existing_sic_confidence = company_data.get('existing_sic_confidence') if company_data else None
                    if existing_sic_confidence:
                        self.logger.info(f"✅ Found stored existing_sic_confidence: {existing_sic_confidence}%")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not retrieve existing_sic_confidence: {e}")
            
            # Prepare Companies House SIC data for database storage
            ch_sic_codes_json = None
            ch_sic_description = None
            
            # Try multiple sources for CH data
            ch_data_source = None
            import json
            
            # 1. Check ch_sic_data parameter
            if ch_sic_data and ch_sic_data.get('success', False):
                ch_data_source = ch_sic_data
            # 2. Check result's companies_house_validation
            elif result.get('companies_house_validation', {}).get('success', False):
                ch_data_source = result['companies_house_validation']
            # 3. Check final_state's ch_sic_data
            elif final_state and final_state.get('ch_sic_data', {}).get('success', False):
                ch_data_source = final_state['ch_sic_data']
            
            if ch_data_source:
                ch_sic_codes = ch_data_source.get('sic_codes', [])
                if ch_sic_codes:
                    # 🎯 FIXED: Use only the FIRST SIC code in clean text format (consistent with sic_codes table)
                    # This prevents comma-separated strings and ensures UI display consistency
                    first_sic_code = ch_sic_codes[0] if isinstance(ch_sic_codes, list) else ch_sic_codes
                    ch_sic_codes_json = str(first_sic_code).strip()  # Clean single SIC code
                    
                    # 🔍 Look up SIC description from our internal sic_codes table
                    ch_sic_description = None
                    if ch_sic_codes_json:
                        ch_sic_description = self._lookup_sic_description(ch_sic_codes_json)
                    
                    self.logger.info(f"🏛️ Found CH SIC data for DB save: primary_code={ch_sic_codes_json}, description='{ch_sic_description or 'None'}', total_codes={len(ch_sic_codes) if isinstance(ch_sic_codes, list) else 1})")
            
            # Save agentic prediction with CH SIC data and preserved existing confidence
            # confidence_score: multiply decimal (0-1) by 100 so DB stores as % (consistent with approve endpoint)
            raw_confidence = result.get('confidence_score', 0.0)
            confidence_pct = raw_confidence * 100 if raw_confidence is not None and raw_confidence <= 1.0 else raw_confidence
            success = sic_matcher.save_prediction_to_db(
                company_id=company_id,
                company_name=company_name,
                business_description=business_description,
                predicted_sic_code=result.get('predicted_sic_code', '82990'),  # Other business support service activities n.e.c.
                predicted_sic_description=result.get('predicted_sic_description', ''),
                confidence_score=confidence_pct,
                existing_sic_confidence=existing_sic_confidence,  # Preserve stored confidence to prevent recalculation
                model_version='agentic_v1.0',
                prediction_method='AGENTIC_LANGGRAPH_WORKFLOW',
                ai_reasoning=result.get('reasoning', ''),
                ch_sic_codes=ch_sic_codes_json,
                ch_sic_description=ch_sic_description
            )
            
            if success:
                self.logger.info(f"💾 ✅ Agentic prediction saved to database for {company_name} (ID: {company_id})")
                if ch_sic_codes_json:
                    self.logger.info(f"🏛️ ✅ Companies House SIC codes saved: {ch_sic_codes_json}")
            else:
                self.logger.warning(f"⚠️ Failed to save agentic prediction to database for {company_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error saving agentic prediction to database: {e}")
            return False
    
    def _find_company_id_by_name(self, company_name: str) -> Optional[int]:
        """
        Find company ID by name using direct database lookup.
        Returns None if company doesn't exist (strict validation).
        
        NOTE: This method only returns company_id for backward compatibility.
        For dual-key operations, use _find_company_dual_keys_by_name() instead.
        """
        try:
            # Direct database lookup for reliable company validation
            from app_modules.database.connection import DatabaseConnection
            
            db_conn = DatabaseConnection()
            with db_conn.get_connection() as conn:
                cursor = conn.cursor()
                
                # Exact match first (most common case)
                cursor.execute("""
                    SELECT id FROM companies 
                    WHERE company_name = ?
                    LIMIT 1
                """, (company_name,))
                
                result = cursor.fetchone()
                if result:
                    company_id = result[0]
                    self.logger.info(f"📍 Exact match: company_id {company_id} for '{company_name}'")
                    return company_id
                
                # Fallback: case-insensitive with trim
                cursor.execute("""
                    SELECT id, company_name FROM companies 
                    WHERE UPPER(TRIM(company_name)) = UPPER(TRIM(?))
                    LIMIT 1
                """, (company_name,))
                
                result = cursor.fetchone()
                if result:
                    company_id = result[0]
                    actual_name = result[1]
                    self.logger.info(f"📍 Case-insensitive match: company_id {company_id} for '{company_name}' -> '{actual_name}'")
                    return company_id
                
                self.logger.warning(f"📍 Company '{company_name}' not found in companies table - validation failed")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Database error finding company ID for '{company_name}': {e}")
            return None
    
    def _find_company_dual_keys_by_name(self, company_name: str) -> Optional[tuple]:
        """
        Find both company_id and unique_id by name for dual-key validation.
        Returns (company_id, unique_id) tuple if found, None if company doesn't exist.
        """
        try:
            # Direct database lookup for reliable company validation
            from app_modules.database.connection import DatabaseConnection
            
            db_conn = DatabaseConnection()
            with db_conn.get_connection() as conn:
                cursor = conn.cursor()
                
                # Exact match first (most common case) - get both keys
                cursor.execute("""
                    SELECT id, unique_id FROM companies 
                    WHERE company_name = ?
                    LIMIT 1
                """, (company_name,))
                
                result = cursor.fetchone()
                if result:
                    company_id, unique_id = result
                    self.logger.info(f"✅ DUAL-KEY FOUND: company_id={company_id}, unique_id='{unique_id}' for '{company_name}'")
                    return (company_id, unique_id)
                
                # If exact match fails, try case-insensitive match
                cursor.execute("""
                    SELECT id, unique_id FROM companies 
                    WHERE LOWER(company_name) = LOWER(?)
                    LIMIT 1
                """, (company_name,))
                
                result = cursor.fetchone()
                if result:
                    company_id, unique_id = result
                    self.logger.info(f"✅ DUAL-KEY FOUND (case-insensitive): company_id={company_id}, unique_id='{unique_id}' for '{company_name}'")
                    return (company_id, unique_id)
                
                self.logger.warning(f"📍 DUAL-KEY VALIDATION: Company '{company_name}' not found in companies table")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Database error finding dual keys for '{company_name}': {e}")
            return None
    
    def _lookup_sic_description(self, sic_code: str) -> Optional[str]:
        """Look up SIC description from internal sic_codes table."""
        try:
            # Get enhanced SIC matcher which has access to the database
            sic_matcher = self.services_container.get('enhanced_sic_matcher')
            if not sic_matcher:
                self.logger.warning("⚠️ Enhanced SIC matcher not available for description lookup")
                return None
            
            # Use the same database connection approach as other parts of the system
            from app_modules.database.connection import DatabaseConnection
            
            # Get database connection using the standard approach
            db_connection = DatabaseConnection()
            
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                
                # Look up the SIC description
                cursor.execute('SELECT sic_description FROM sic_codes WHERE sic_code = ?', (sic_code,))
                result = cursor.fetchone()
            
            if result:
                description = result[0]
                self.logger.info(f"🔍 Found SIC description for {sic_code}: '{description}'")
                return description
            else:
                self.logger.info(f"🔍 No SIC description found for code: {sic_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error looking up SIC description for {sic_code}: {e}")
            return None

    def _generate_fallback_reasoning(self, ai_prediction: Any, ch_sic_data: Any, final_state: Any) -> Dict[str, str]:
        """Generate comprehensive fallback reasoning using enhanced SIC matcher's natural AI reasoning"""
        
        # Safe data extraction with defaults - handle different data types
        if hasattr(ai_prediction, 'get'):
            predicted_sic = ai_prediction.get('predicted_sic_code', 'Unknown')
            confidence = ai_prediction.get('confidence_score', 0.0)
            method = ai_prediction.get('prediction_method', 'analysis')
            alternatives = ai_prediction.get('alternatives', [])
            similarity_breakdown = ai_prediction.get('similarity_breakdown', {})
            match_reasoning = ai_prediction.get('match_reasoning', '')
            predicted_sic_description = ai_prediction.get('predicted_sic_description', '')
        elif hasattr(ai_prediction, 'predicted_sic_code'):
            predicted_sic = getattr(ai_prediction, 'predicted_sic_code', 'Unknown')
            confidence = getattr(ai_prediction, 'confidence_score', 0.0)
            method = getattr(ai_prediction, 'prediction_method', 'analysis')
            alternatives = getattr(ai_prediction, 'alternatives', [])
            similarity_breakdown = getattr(ai_prediction, 'similarity_breakdown', {})
            match_reasoning = getattr(ai_prediction, 'match_reasoning', '')
            predicted_sic_description = getattr(ai_prediction, 'predicted_sic_description', '')
        else:
            predicted_sic = 'Unknown'
            confidence = 0.0
            method = 'analysis'
            alternatives = []
            similarity_breakdown = {}
            match_reasoning = ''
            predicted_sic_description = ''
        
        # Extract company data for context
        company_data = final_state.get('company_data', {}) if hasattr(final_state, 'get') else {}
        company_name = company_data.get('company_name', 'Unknown Company') if company_data else 'Unknown Company'
        business_desc = company_data.get('business_description', '') if company_data else ''
        current_sic = company_data.get('existing_sic_code') or company_data.get('current_sic') if company_data else None
        existing_sic_confidence = company_data.get('existing_sic_confidence') if company_data else None
        
        # Generate natural AI reasoning explanation using enhanced SIC matcher
        try:
            # Try to use enhanced SIC matcher's natural AI reasoning generation
            from app_modules.utils.enhanced_sic_matcher import get_enhanced_sic_matcher
            
            enhanced_sic_matcher = get_enhanced_sic_matcher()
            ai_reasoning = enhanced_sic_matcher.generate_ai_reasoning(
                business_description=business_desc,
                predicted_sic_code=predicted_sic,
                predicted_sic_description=predicted_sic_description,
                confidence_score=confidence,
                company_name=company_name,
                current_sic=current_sic,
                existing_sic_confidence=existing_sic_confidence
            )
            
            self.logger.info(f"✅ Generated natural AI reasoning using enhanced matcher: {ai_reasoning[:100]}...")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not generate natural AI reasoning, using fallback template: {e}")
            # Fallback to simple template if AI reasoning fails
            confidence_desc = "high confidence" if confidence > 0.7 else "moderate confidence" if confidence > 0.5 else "low confidence"
            ai_reasoning = f"AI analysis identified SIC {predicted_sic} as the most appropriate classification for {company_name} with {confidence_desc} ({confidence*100:.1f}% accuracy). The prediction is based on business description analysis and industry pattern matching."

        
        # Generate comprehensive CH comparison explanation
        ch_comparison_parts = []
        
        if not ch_sic_data:
            ch_comparison = "Companies House data unavailable for validation. AI prediction stands as primary classification without external confirmation."
        else:
            success = False
            ch_sics = []
            ch_confidence = 0.0
            method_used = ''
            
            # Extract CH data safely
            if hasattr(ch_sic_data, 'get'):
                success = ch_sic_data.get('success', False)
                ch_sics = ch_sic_data.get('sic_codes', [])
                ch_confidence = ch_sic_data.get('confidence', 0.0)
                method_used = ch_sic_data.get('method_used', 'unknown')
            elif hasattr(ch_sic_data, 'success'):
                success = getattr(ch_sic_data, 'success', False)
                ch_sics = getattr(ch_sic_data, 'sic_codes', [])
                ch_confidence = getattr(ch_sic_data, 'confidence', 0.0)
                method_used = getattr(ch_sic_data, 'method_used', 'unknown')
                
            if success and ch_sics:
                # Convert to strings for comparison
                ch_sics_str = [str(sic) for sic in ch_sics]
                predicted_sic_str = str(predicted_sic)
                
                if predicted_sic_str in ch_sics_str:
                    # Agreement case
                    ch_comparison_parts.append(f"✅ Companies House confirms SIC {predicted_sic} matches registered classification (confidence: {ch_confidence*100:.1f}%).")
                    ch_comparison_parts.append("This alignment validates the AI prediction and increases overall confidence.")
                    if method_used:
                        ch_comparison_parts.append(f"Retrieved via {method_used} lookup method.")
                else:
                    # Disagreement case - detailed analysis
                    primary_ch_sic = ch_sics_str[0] if ch_sics_str else 'Unknown'
                    ch_comparison_parts.append(f"⚠️ Classification difference detected: AI predicts SIC {predicted_sic}, but Companies House shows {primary_ch_sic}.")
                    
                    # Explain potential reasons for difference
                    if confidence < 0.7:
                        ch_comparison_parts.append("The discrepancy may be due to business evolution or description updates not reflected in official records.")
                    elif len(ch_sics_str) > 1:
                        ch_comparison_parts.append(f"Company has multiple SIC codes ({', '.join(ch_sics_str[:3])}), suggesting diverse business activities.")
                    else:
                        ch_comparison_parts.append("This suggests either business model changes or different interpretations of primary activity.")
                    
                    # Recommendation based on confidence levels
                    if confidence > ch_confidence:
                        ch_comparison_parts.append("AI prediction may reflect current business better than registered classification.")
                    else:
                        ch_comparison_parts.append("Companies House classification likely more authoritative given higher confidence.")
                        
            else:
                # CH lookup failed
                ch_comparison_parts.append("Companies House lookup failed or returned no SIC data.")
                if method_used:
                    ch_comparison_parts.append(f"Attempted {method_used} method but encountered data limitations.")
                ch_comparison_parts.append("AI prediction proceeds without external validation.")
        
        ch_comparison = " ".join(ch_comparison_parts)
        
        return {
            'ai_reasoning': ai_reasoning,
            'ch_comparison': ch_comparison
        }
    
    def _generate_natural_reasoning_for_fallback(self, predicted_sic: str, confidence: float, 
                                               business_description: str, company_name: str) -> str:
        """Generate natural AI reasoning for fallback scenarios"""
        try:
            # Try to use enhanced SIC matcher's natural AI reasoning generation
            from app_modules.utils.enhanced_sic_matcher import get_enhanced_sic_matcher
            
            enhanced_sic_matcher = get_enhanced_sic_matcher()
            
            # Get SIC description for better reasoning
            sic_descriptions = getattr(enhanced_sic_matcher, 'sic_descriptions', {})
            predicted_sic_description = sic_descriptions.get(predicted_sic, f'Classification code {predicted_sic}')
            
            ai_reasoning = enhanced_sic_matcher.generate_ai_reasoning(
                business_description=business_description,
                predicted_sic_code=predicted_sic,
                predicted_sic_description=predicted_sic_description,
                confidence_score=confidence,
                company_name=company_name,
                current_sic=None  # No current SIC in fallback scenario
            )
            
            self.logger.info(f"✅ Generated natural fallback AI reasoning: {ai_reasoning[:100]}...")
            return ai_reasoning
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not generate natural fallback reasoning: {e}")
            # Simple fallback template
            confidence_desc = "high confidence" if confidence > 0.7 else "moderate confidence" if confidence > 0.5 else "reasonable confidence"
            return f"AI analysis determined SIC {predicted_sic} as the most appropriate classification for {company_name} with {confidence_desc} ({confidence*100:.1f}% accuracy) based on business description analysis and industry pattern matching."

    def _try_companies_house_lookup(self, company_name: str, company_number: str, address: str) -> Dict[str, Any]:
        """
        Try to get Companies House SIC codes using both mechanisms:
        1. Company registration number lookup (if available)
        2. Company name and address lookup (fallback)
        """
        try:
            companies_house_client = self.services_container.get('companies_house_client')
            if not companies_house_client:
                self.logger.warning("🏛️ Companies House client not available")
                return {
                    'success': False,
                    'sic_codes': [],
                    'confidence': 0.0,
                    'method_used': 'client_unavailable',
                    'company_data': {},
                    'error_details': 'Companies House client not configured'
                }

            self.logger.info(f"🏛️ Attempting Companies House lookup for: {company_name}")
            
            # Mechanism 1: Company number lookup (highest confidence)
            if company_number and company_number.strip():
                self.logger.info(f"🔍 Method 1: Trying company number lookup for {company_number}")
                try:
                    ch_data = companies_house_client.get_company_by_number(company_number.strip())
                    if ch_data and ch_data.get('sic_codes'):
                        self.logger.info(f"✅ CH Method 1 SUCCESS: Found SIC codes via company number: {ch_data.get('sic_codes')}")
                        return {
                            'success': True,
                            'sic_codes': ch_data.get('sic_codes', []),
                            'confidence': 0.9,
                            'method_used': 'company_number',
                            'company_data': {
                                'company_name': ch_data.get('company_name', company_name),
                                'company_status': ch_data.get('company_status', ''),
                                'company_number': ch_data.get('company_number', company_number)
                            }
                        }
                except Exception as e:
                    self.logger.warning(f"⚠️ Company number lookup failed: {e}")

            # Mechanism 2: Name and address lookup (medium confidence)
            if company_name and company_name.strip():
                self.logger.info(f"🔍 Method 2: Trying name and address lookup for '{company_name}'")
                try:
                    ch_data = companies_house_client.get_company_by_name_and_address(
                        company_name=company_name.strip(),
                        address=address.strip() if address else None,
                        status="active"
                    )
                    if ch_data and ch_data.get('sic_codes'):
                        self.logger.info(f"✅ CH Method 2 SUCCESS: Found SIC codes via name/address: {ch_data.get('sic_codes')}")
                        return {
                            'success': True,
                            'sic_codes': ch_data.get('sic_codes', []),
                            'confidence': 0.7 if address else 0.5,
                            'method_used': 'name_and_address' if address else 'name_only',
                            'company_data': {
                                'company_name': ch_data.get('company_name', company_name),
                                'company_status': ch_data.get('company_status', ''),
                                'company_number': ch_data.get('company_number', '')
                            }
                        }
                except Exception as e:
                    self.logger.warning(f"⚠️ Name and address lookup failed: {e}")

            # Both methods failed
            self.logger.warning(f"❌ All Companies House lookup methods failed for {company_name}")
            return {
                'success': False,
                'sic_codes': [],
                'confidence': 0.0,
                'method_used': 'all_methods_failed',
                'company_data': {},
                'error_details': 'No matching company found using both registration number and name/address lookup'
            }

        except Exception as e:
            self.logger.error(f"❌ Companies House lookup error: {e}")
            return {
                'success': False,
                'sic_codes': [],
                'confidence': 0.0,
                'method_used': 'error',
                'company_data': {},
                'error_details': str(e)
            }