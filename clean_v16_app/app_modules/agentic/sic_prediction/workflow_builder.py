"""
LangGraph Workflow Builder

This module creates and configures the LangGraph workflow for intelligent agentic SIC prediction.
It connects all the individual nodes, defines routing logic, manages state transitions, and
provides comprehensive error handling and fallback mechanisms.

Core Components:
- Workflow graph construction using LangGraph
- Node routing and conditional logic
- State transition management
- Error handling and recovery
- Workflow configuration and customization
- Performance monitoring and logging

Integration Points:
- All agentic nodes (DataIngestion, CHSICRetrieval, AIPrediction, Reflection, ReasoningGenerator)
- Existing infrastructure services through dependency injection
- Workflow state management and decision tracking
- Frontend visualization and progress tracking
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
    print(f"✅ CRITICAL DEBUG: LangGraph import SUCCESSFUL in workflow_builder")
    print(f"✅ StateGraph: {StateGraph}")
    print(f"✅ END: {END}")
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"
    print(f"❌ CRITICAL DEBUG: LangGraph import FAILED in workflow_builder: {e}")
    print(f"❌ Import error type: {type(e)}")
    import sys
    print(f"❌ Python executable during import: {sys.executable}")
except Exception as e:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"
    print(f"❌ CRITICAL DEBUG: Unexpected error importing LangGraph: {e}")
    print(f"❌ Error type: {type(e)}")
    import sys
    print(f"❌ Python executable during error: {sys.executable}")

from .workflow_state import AgenticWorkflowState, WorkflowDecision
from .nodes.data_ingestion_node import DataIngestionNode
from .nodes.ch_sic_retrieval_node import CHSICRetrievalNode
from .nodes.ai_prediction_node import AIPredictionNode
from .nodes.reflection_node import ReflectionNode
from .nodes.reasoning_generator_node import ReasoningGeneratorNode

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """
    LangGraph workflow builder for intelligent agentic SIC prediction.
    
    This class constructs and manages the complete agentic workflow using LangGraph,
    providing intelligent routing, error handling, and state management.
    """
    
    def __init__(self, services_container=None):
        """
        Initialize workflow builder with service dependencies.
        
        Args:
            services_container: Container with all required services
                - sqlite_sic_repository: SQLiteSICPredictionRepository
                - company_service: CompanyService  
                - companies_house_client: CompaniesHouseClient
                - enhanced_sic_matcher: EnhancedSICMatcher
                - realtime_reasoning_service: RealtimeReasoningService
        """
        self.services_container = services_container or {}
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Initialize nodes with service dependencies
        self.data_ingestion_node = DataIngestionNode(
            repository=services_container.get('sqlite_sic_repository'),
            company_service=services_container.get('company_service')
        )
        
        self.ch_sic_retrieval_node = CHSICRetrievalNode(
            companies_house_client=services_container.get('companies_house_client')
        )
        
        self.ai_prediction_node = AIPredictionNode(
            sic_matcher=services_container.get('enhanced_sic_matcher'),
            reasoning_service=services_container.get('realtime_reasoning_service')
            # sector_agent removed - pure agentic system, no traditional agent fallbacks
        )
        
        self.reflection_node = ReflectionNode(
            sic_matcher=services_container.get('enhanced_sic_matcher')
        )
        
        self.reasoning_generator_node = ReasoningGeneratorNode(
            realtime_reasoning_service=services_container.get('realtime_reasoning_service')
        )
        
        self.workflow_graph = None
        self._is_compiled = False
    
    def build_workflow(self, config: Optional[Dict[str, Any]] = None) -> 'StateGraph':
        """
        Build and configure the complete LangGraph workflow.
        
        Args:
            config: Workflow configuration options
                - enable_reflection: Enable reflection and evaluation (default: True)
                - enable_reasoning_generation: Enable reasoning generation (default: True)
                - confidence_threshold: Minimum confidence threshold (default: 0.7)
                - enable_ch_fallback: Enable CH data fallback (default: True)
                - max_execution_time: Maximum workflow execution time in seconds (default: 60)
                - enable_parallel_execution: Enable parallel node execution where possible (default: False)
        
        Returns:
            Compiled LangGraph workflow ready for execution
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph is required but not available. Please install langgraph package.")
        
        config = config or {}
        self.logger.info("🏗️ Building LangGraph agentic workflow")
        
        # Create state graph
        workflow = StateGraph(AgenticWorkflowState)
        
        # Add nodes to the workflow
        workflow.add_node("data_ingestion", self._wrap_node(self.data_ingestion_node, "data_ingestion"))
        workflow.add_node("ch_sic_retrieval", self._wrap_node(self.ch_sic_retrieval_node, "ch_sic_retrieval"))
        workflow.add_node("ai_prediction", self._wrap_node(self.ai_prediction_node, "ai_prediction"))
        
        # Conditional nodes based on configuration
        if config.get('enable_reflection', True):
            workflow.add_node("reflection_evaluation", self._wrap_node(self.reflection_node, "reflection_evaluation"))
        
        if config.get('enable_reasoning_generation', True):
            workflow.add_node("reasoning_generation", self._wrap_node(self.reasoning_generator_node, "reasoning_generation"))
        
        # Add error handling and fallback nodes
        workflow.add_node("error_handler", self._create_error_handler())
        workflow.add_node("workflow_finalizer", self._create_workflow_finalizer())
        
        # Define workflow entry point
        workflow.set_entry_point("data_ingestion")
        
        # Define workflow edges and routing logic
        self._define_workflow_edges(workflow, config)
        
        # Compile the workflow
        compiled_workflow = workflow.compile()
        self.workflow_graph = compiled_workflow
        self._is_compiled = True
        
        self.logger.info("✅ LangGraph workflow successfully built and compiled")
        return compiled_workflow
    
    def _define_workflow_edges(self, workflow: 'StateGraph', config: Dict[str, Any]) -> None:
        """
        Define edges and routing logic for the workflow.
        
        This creates the intelligent routing between nodes based on conditions,
        error states, and configuration options.
        """
        # Standard progression: data_ingestion -> ch_sic_retrieval
        workflow.add_edge("data_ingestion", "ch_sic_retrieval")
        
        # Conditional routing from CH SIC retrieval
        workflow.add_conditional_edges(
            "ch_sic_retrieval",
            self._route_after_ch_retrieval,
            {
                "continue_to_ai": "ai_prediction",
                "error_handler": "error_handler"
            }
        )
        
        # Conditional routing from AI prediction
        if config.get('enable_reflection', True):
            workflow.add_conditional_edges(
                "ai_prediction",
                self._route_after_ai_prediction,
                {
                    "continue_to_reflection": "reflection_evaluation", 
                    "skip_to_reasoning": "reasoning_generation" if config.get('enable_reasoning_generation', True) else "workflow_finalizer",
                    "error_handler": "error_handler"
                }
            )
            
            # Routing from reflection
            if config.get('enable_reasoning_generation', True):
                workflow.add_conditional_edges(
                    "reflection_evaluation",
                    self._route_after_reflection,
                    {
                        "continue_to_reasoning": "reasoning_generation",
                        "finalize_workflow": "workflow_finalizer",
                        "error_handler": "error_handler"
                    }
                )
                
                # Final routing from reasoning generation
                workflow.add_conditional_edges(
                    "reasoning_generation",
                    self._route_after_reasoning,
                    {
                        "finalize_workflow": "workflow_finalizer",
                        "error_handler": "error_handler"
                    }
                )
            else:
                # Skip reasoning generation
                workflow.add_edge("reflection_evaluation", "workflow_finalizer")
        else:
            # Skip reflection - go directly to reasoning or finalizer
            next_node = "reasoning_generation" if config.get('enable_reasoning_generation', True) else "workflow_finalizer"
            workflow.add_edge("ai_prediction", next_node)
            
            if config.get('enable_reasoning_generation', True):
                workflow.add_edge("reasoning_generation", "workflow_finalizer")
        
        # Error handler always goes to finalizer
        workflow.add_edge("error_handler", "workflow_finalizer")
        
        # Workflow finalizer is the end
        workflow.add_edge("workflow_finalizer", END)
    
    def _route_after_ch_retrieval(self, state: AgenticWorkflowState) -> str:
        """Route after Companies House SIC retrieval based on results and errors"""
        errors = state.get('errors', [])
        if errors:
            self.logger.warning(f"CH retrieval errors detected, routing to error handler: {errors}")
            return "error_handler"
        
        # Continue to AI prediction regardless of CH success/failure
        return "continue_to_ai"
    
    def _route_after_ai_prediction(self, state: AgenticWorkflowState) -> str:
        """Route after AI prediction based on results and configuration"""
        errors = state.get('errors', [])
        if errors:
            self.logger.warning(f"AI prediction errors detected, routing to error handler: {errors}")
            return "error_handler"
        
        ai_prediction = state.get('ai_prediction')
        if not ai_prediction:
            self.logger.warning("No AI prediction result, routing to error handler")
            return "error_handler"
        
        # Check if reflection should be skipped based on confidence
        confidence = ai_prediction.get('confidence_score', 0.0) if ai_prediction else 0.0
        workflow_config = state.get('workflow_config', {})
        confidence_threshold = workflow_config.get('confidence_threshold', 0.7)
        
        # Very high confidence predictions can skip reflection if configured
        if confidence >= 0.95 and workflow_config.get('skip_reflection_high_confidence', False):
            self.logger.info(f"Very high confidence ({confidence:.2f}) - skipping reflection")
            return "skip_to_reasoning"
        
        return "continue_to_reflection"
    
    def _route_after_reflection(self, state: AgenticWorkflowState) -> str:
        """Route after reflection based on evaluation results"""
        errors = state.get('errors', [])
        if errors:
            self.logger.warning(f"Reflection errors detected, routing to error handler: {errors}")
            return "error_handler"
        
        evaluation_result = state.get('evaluation_result')
        if not evaluation_result:
            self.logger.warning("No evaluation result, routing to error handler")
            return "error_handler"
        
        # Check if refinement is needed
        recommended_action = evaluation_result.get('recommended_action', 'accept_ai')
        if recommended_action == 'use_fallback':
            self.logger.info("Evaluation recommends fallback - finalizing workflow")
            return "finalize_workflow"
        
        return "continue_to_reasoning"
    
    def _route_after_reasoning(self, state: AgenticWorkflowState) -> str:
        """Route after reasoning generation - always finalize unless errors"""
        errors = state.get('errors', [])
        if errors:
            self.logger.warning(f"Reasoning generation errors detected, routing to error handler: {errors}")
            return "error_handler"
        
        return "finalize_workflow"
    
    def _wrap_node(self, node_instance: Any, node_name: str) -> Callable[[AgenticWorkflowState], AgenticWorkflowState]:
        """
        Wrap node instance with error handling, timing, and logging.
        
        This provides consistent error handling, performance monitoring, and
        logging across all workflow nodes.
        """
        def wrapped_node(state: AgenticWorkflowState) -> AgenticWorkflowState:
            start_time = datetime.now()
            
            try:
                self.logger.info(f"🚀 Executing node: {node_name}")
                
                # Add workflow configuration to state if not present
                if 'workflow_config' not in state:
                    state = state.copy()
                    state['workflow_config'] = {}
                
                # Execute the node
                result_state = node_instance(state)
                
                # Update execution tracking
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if 'node_execution_times' not in result_state:
                    result_state = result_state.copy()
                    result_state['node_execution_times'] = {}
                
                result_state['node_execution_times'][node_name] = execution_time
                
                self.logger.info(f"✅ Node {node_name} completed in {execution_time:.2f}s")
                return result_state
                
            except Exception as e:
                self.logger.error(f"❌ Node {node_name} failed: {e}")
                
                # Create error state
                error_state = state.copy()
                error_state.update({
                    'errors': state.get('errors', []) + [f"{node_name}: {str(e)}"],
                    'current_node': node_name,
                    'node_execution_times': {
                        **state.get('node_execution_times', {}),
                        node_name: (datetime.now() - start_time).total_seconds()
                    },
                    'workflow_steps': state.get('workflow_steps', []) + [
                        self._create_error_step(node_name, str(e))
                    ]
                })
                
                return error_state
        
        return wrapped_node
    
    def _create_error_handler(self) -> Callable[[AgenticWorkflowState], AgenticWorkflowState]:
        """Create error handling node for workflow recovery"""
        def error_handler(state: AgenticWorkflowState) -> AgenticWorkflowState:
            self.logger.info("🔧 Error handler: Attempting workflow recovery")
            
            errors = state.get('errors', [])
            current_node = state.get('current_node', 'unknown')
            
            # Attempt to provide fallback results based on what data is available
            recovery_state = state.copy()
            
            # If we have company data but no AI prediction, create fallback prediction
            if state.get('company_data') and not state.get('ai_prediction'):
                fallback_prediction = self._create_fallback_prediction(state)
                recovery_state['ai_prediction'] = fallback_prediction
                recovery_state['fallback_triggers'] = state.get('fallback_triggers', []) + ['error_recovery_prediction']
            
            # If we have AI prediction but no evaluation, create basic evaluation
            if state.get('ai_prediction') and not state.get('evaluation_result'):
                basic_evaluation = self._create_basic_evaluation(state)
                recovery_state['evaluation_result'] = basic_evaluation
                recovery_state['fallback_triggers'] = state.get('fallback_triggers', []) + ['error_recovery_evaluation']
            
            # Add error recovery decision
            error_decision = WorkflowDecision(
                node_name="error_handler",
                timestamp=datetime.now(),
                decision=f"Error recovery attempted for {len(errors)} errors",
                reasoning=f"Workflow recovery after errors in {current_node}: {'; '.join(errors[-3:])}",  # Last 3 errors
                confidence=0.3,
                fallback_triggered=True
            )
            
            recovery_state.update({
                'workflow_decisions': state.get('workflow_decisions', []) + [error_decision],
                'warnings': state.get('warnings', []) + [f'Workflow recovered from {len(errors)} errors'],
                'current_node': 'error_handler',
                'workflow_steps': state.get('workflow_steps', []) + [
                    self._create_recovery_step(len(errors), current_node)
                ]
            })
            
            self.logger.info(f"🔧 Error handler: Recovery attempted for {len(errors)} errors")
            return recovery_state
        
        return error_handler
    
    def _create_workflow_finalizer(self) -> Callable[[AgenticWorkflowState], AgenticWorkflowState]:
        """Create workflow finalizer for final processing and cleanup"""
        def workflow_finalizer(state: AgenticWorkflowState) -> AgenticWorkflowState:
            self.logger.info("🏁 Workflow finalizer: Completing agentic workflow")
            
            # Calculate overall workflow statistics
            execution_times = state.get('node_execution_times', {})
            total_execution_time = sum(execution_times.values())
            
            node_scores = state.get('node_confidence_scores', {})
            overall_confidence = sum(node_scores.values()) / len(node_scores) if node_scores else 0.0
            
            errors = state.get('errors', [])
            warnings = state.get('warnings', [])
            fallback_triggers = state.get('fallback_triggers', [])
            
            # Create final workflow summary
            workflow_summary = {
                'workflow_completed': True,
                'total_execution_time': total_execution_time,
                'overall_confidence': overall_confidence,
                'nodes_executed': list(execution_times.keys()),
                'errors_count': len(errors),
                'warnings_count': len(warnings),
                'fallback_triggers_count': len(fallback_triggers),
                'final_prediction': state.get('ai_prediction', {}).get('predicted_sic_code', '') if state.get('ai_prediction') else '',
                'prediction_confidence': state.get('ai_prediction', {}).get('confidence_score', 0.0) if state.get('ai_prediction') else 0.0,
                'workflow_quality_score': state.get('evaluation_result', {}).get('quality_score', 0.0) if state.get('evaluation_result') else 0.0,
                'completion_timestamp': datetime.now().isoformat()
            }
            
            # Final decision
            final_decision = WorkflowDecision(
                node_name="workflow_finalizer",
                timestamp=datetime.now(),
                decision="Agentic workflow completed successfully",
                reasoning=f"Workflow completed in {total_execution_time:.2f}s with {len(node_scores)} nodes executed",
                confidence=overall_confidence,
                fallback_triggered=len(fallback_triggers) > 0
            )
            
            # Final state
            final_state = state.copy()
            final_state.update({
                'workflow_summary': workflow_summary,
                'workflow_decisions': state.get('workflow_decisions', []) + [final_decision],
                'current_node': 'workflow_finalizer',
                'workflow_completed': True,
                'node_execution_times': {
                    **execution_times,
                    'workflow_finalizer': 0.1  # Minimal time for finalizer
                },
                'workflow_steps': state.get('workflow_steps', []) + [
                    self._create_completion_step(workflow_summary)
                ]
            })
            
            success_msg = f"🏁 Workflow completed: {workflow_summary['final_prediction']} (confidence: {workflow_summary['prediction_confidence']:.2f})"
            self.logger.info(success_msg)
            return final_state
        
        return workflow_finalizer
    
    def _create_fallback_prediction(self, state: AgenticWorkflowState) -> Dict[str, Any]:
        """Create fallback prediction when AI prediction fails"""
        company_data = state.get('company_data', {})
        company_name = company_data.get('company_name', 'Unknown')
        
        return {
            'predicted_sic_code': '82990',  # Other business support service activities n.e.c. (more appropriate than dormant company)
            'confidence_score': 0.1,
            'prediction_method': 'error_fallback',
            'alternatives': [],
            'reasoning': f'Fallback prediction for {company_name} due to workflow errors',
            'timestamp': datetime.now().isoformat(),
            'fallback_triggered': True
        }
    
    def _create_basic_evaluation(self, state: AgenticWorkflowState) -> Dict[str, Any]:
        """Create basic evaluation when reflection fails"""
        return {
            'ch_vs_ai_agreement': False,
            'confidence_delta': 0.0,
            'quality_score': 0.3,
            'recommended_action': 'accept_ai',
            'evaluation_reasoning': 'Basic evaluation due to reflection errors',
            'refinement_suggestions': ['Manual review recommended due to evaluation errors']
        }
    
    def _create_error_step(self, node_name: str, error_message: str) -> Dict[str, Any]:
        """Create error workflow step"""
        return {
            'step': node_name.replace('_', ' ').title(),
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'details': {'error': error_message},
            'icon': '❌',
            'duration_ms': 0
        }
    
    def _create_recovery_step(self, error_count: int, failed_node: str) -> Dict[str, Any]:
        """Create recovery workflow step"""
        return {
            'step': 'Error Recovery',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'errors_recovered': error_count,
                'failed_node': failed_node,
                'recovery_method': 'fallback_generation'
            },
            'icon': '🔧',
            'duration_ms': 0
        }
    
    def _create_completion_step(self, workflow_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Create completion workflow step"""
        return {
            'step': 'Workflow Completion',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'total_time': workflow_summary['total_execution_time'],
                'overall_confidence': workflow_summary['overall_confidence'],
                'nodes_executed': len(workflow_summary['nodes_executed']),
                'final_prediction': workflow_summary['final_prediction'],
                'quality_score': workflow_summary['workflow_quality_score']
            },
            'icon': '🏁',
            'duration_ms': int(workflow_summary['total_execution_time'] * 1000)
        }
    
    def get_workflow_config_schema(self) -> Dict[str, Any]:
        """Get the schema for workflow configuration options"""
        return {
            'enable_reflection': {
                'type': 'boolean',
                'default': True,
                'description': 'Enable reflection and evaluation node'
            },
            'enable_reasoning_generation': {
                'type': 'boolean', 
                'default': True,
                'description': 'Enable reasoning generation node'
            },
            'confidence_threshold': {
                'type': 'number',
                'default': 0.7,
                'minimum': 0.0,
                'maximum': 1.0,
                'description': 'Minimum confidence threshold for predictions'
            },
            'enable_ch_fallback': {
                'type': 'boolean',
                'default': True,
                'description': 'Enable Companies House data fallback'
            },
            'max_execution_time': {
                'type': 'number',
                'default': 60,
                'minimum': 10,
                'maximum': 300,
                'description': 'Maximum workflow execution time in seconds'
            },
            'skip_reflection_high_confidence': {
                'type': 'boolean',
                'default': False,
                'description': 'Skip reflection for very high confidence predictions (>= 0.95)'
            },
            'enable_parallel_execution': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable parallel node execution where possible'
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize workflow configuration"""
        schema = self.get_workflow_config_schema()
        validated_config = {}
        
        for key, schema_def in schema.items():
            value = config.get(key, schema_def['default'])
            
            # Type validation
            expected_type = schema_def['type']
            if expected_type == 'boolean' and not isinstance(value, bool):
                value = bool(value)
            elif expected_type == 'number' and not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    value = schema_def['default']
            
            # Range validation for numbers
            if expected_type == 'number':
                if 'minimum' in schema_def:
                    value = max(value, schema_def['minimum'])
                if 'maximum' in schema_def:
                    value = min(value, schema_def['maximum'])
            
            validated_config[key] = value
        
        return validated_config
    
    def is_compiled(self) -> bool:
        """Check if workflow has been compiled and is ready for execution"""
        return self._is_compiled and self.workflow_graph is not None
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the built workflow"""
        if not self.is_compiled():
            return {'status': 'not_compiled', 'nodes': [], 'edges': []}
        
        return {
            'status': 'compiled',
            'nodes': [
                'data_ingestion',
                'ch_sic_retrieval', 
                'ai_prediction',
                'reflection_evaluation',
                'reasoning_generation',
                'error_handler',
                'workflow_finalizer'
            ],
            'langgraph_available': LANGGRAPH_AVAILABLE,
            'services_configured': len(self.services_container),
            'builder_version': '1.0.0'
        }


def build_agentic_workflow(services_container: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> 'StateGraph':
    """
    Convenience function to build and compile the agentic workflow.
    
    Args:
        services_container: Container with all required services
        config: Optional workflow configuration
        
    Returns:
        Compiled LangGraph workflow ready for execution
        
    Raises:
        ImportError: If LangGraph is not available
        ValueError: If required services are missing
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError(
            "LangGraph is required for agentic workflow. Please install with: pip install langgraph"
        )
    
    # Validate required services
    required_services = [
        'sqlite_sic_repository',
        'companies_house_client', 
        'enhanced_sic_matcher'
    ]
    
    missing_services = [srv for srv in required_services if srv not in services_container]
    if missing_services:
        raise ValueError(f"Missing required services: {', '.join(missing_services)}")
    
    # Build and compile workflow
    builder = WorkflowBuilder(services_container)
    validated_config = builder.validate_config(config or {})
    
    logger.info(f"🚀 Building agentic workflow with config: {validated_config}")
    return builder.build_workflow(validated_config)