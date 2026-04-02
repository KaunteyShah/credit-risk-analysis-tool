"""
Reflection and Evaluation Node

This node implements intelligent reflection and evaluation of AI predictions against
Companies House data and existing SIC information. It makes strategic decisions about
accepting, refining, or escalating predictions based on quality assessments.

Responsibilities:
- Compare AI predictions with Companies House SIC codes
- Validate prediction quality and reasoning
- Make intelligent decisions about acceptance or refinement
- Trigger fallback mechanisms when necessary
- Assess overall workflow quality and confidence

Integration Points:
- Existing confidence calculation patterns
- EnhancedSICMatcher validation methods
- Quality assessment frameworks
- Workflow decision management
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..workflow_state import AgenticWorkflowState, EvaluationResult, WorkflowDecision

logger = logging.getLogger(__name__)


class ReflectionNode:
    """
    Intelligent reflection and evaluation node for quality assessment and decision-making.
    
    This node analyzes AI predictions against available data sources and makes strategic
    decisions about workflow progression, refinement needs, and fallback triggers.
    """
    
    def __init__(self, sic_matcher=None):
        """
        Initialize with existing infrastructure dependencies.
        
        Args:
            sic_matcher: EnhancedSICMatcher instance for validation
        """
        self.sic_matcher = sic_matcher
        self.logger = logger.getChild(self.__class__.__name__)
    
    def __call__(self, state: AgenticWorkflowState) -> AgenticWorkflowState:
        """
        Execute intelligent reflection and evaluation of workflow results.
        
        Args:
            state: Current workflow state with company data, CH data, and AI prediction
            
        Returns:
            Enhanced state with evaluation results and strategic decisions
        """
        start_time = datetime.now()
        
        try:
            company_data = state.get('company_data')
            ai_prediction = state.get('ai_prediction')
            
            if not company_data or not ai_prediction:
                return self._handle_error(state, "Missing required data for reflection", start_time)
            
            company_name = company_data.get('company_name', 'Unknown')
            predicted_sic = ai_prediction.get('predicted_sic_code', '')
            
            self.logger.info(f"🔍 Reflection Node: Evaluating prediction {predicted_sic} for {company_name}")
            
            # Check if reflection is enabled
            workflow_config = state.get('workflow_config', {})
            if not workflow_config.get('enable_reflection', True):
                return self._handle_disabled_reflection(state, start_time)
            
            # Comprehensive evaluation of prediction quality
            evaluation_result = self._execute_comprehensive_evaluation(state)
            
            # Strategic decision-making based on evaluation
            strategic_decision = self._make_strategic_decision(evaluation_result, state)
            
            # Create workflow decision record
            decision = self._create_workflow_decision(
                "reflection_evaluation",
                f"Evaluation completed: {strategic_decision['action']} - {strategic_decision['reasoning']}",
                evaluation_result.get('quality_score', 0.0)
            )
            
            # Update workflow state
            updated_state = state.copy()
            updated_state.update({
                'evaluation_result': evaluation_result,
                'workflow_decisions': state.get('workflow_decisions', []) + [decision],
                'node_confidence_scores': {
                    **state.get('node_confidence_scores', {}),
                    'reflection_evaluation': evaluation_result.get('quality_score', 0.0)
                },
                'current_node': 'reflection_evaluation',
                'warnings': state.get('warnings', []) + evaluation_result.get('warnings', []),
                'node_execution_times': {
                    **state.get('node_execution_times', {}),
                    'reflection_evaluation': (datetime.now() - start_time).total_seconds()
                },
                'workflow_steps': state.get('workflow_steps', []) + [
                    self._create_workflow_step("Reflection & Evaluation", "completed", evaluation_result, strategic_decision)
                ]
            })
            
            # Handle strategic decision outcomes
            if strategic_decision['action'] == 'request_refinement':
                updated_state['fallback_triggers'] = state.get('fallback_triggers', []) + ['refinement_requested']
            elif strategic_decision['action'] == 'use_fallback':
                updated_state['fallback_triggers'] = state.get('fallback_triggers', []) + ['quality_below_threshold']
            
            success_msg = f"✅ Reflection Node: {strategic_decision['action']} - Quality score: {evaluation_result.get('quality_score', 0.0):.2f}"
            self.logger.info(success_msg)
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ Reflection Node: Error during evaluation: {e}")
            return self._handle_error(state, f"Reflection evaluation failed: {str(e)}", start_time)
    
    def _execute_comprehensive_evaluation(self, state: AgenticWorkflowState) -> EvaluationResult:
        """
        Execute comprehensive evaluation of prediction quality and workflow results.
        
        Evaluation Dimensions:
        1. CH SIC vs AI Prediction Agreement
        2. Confidence Level Assessment  
        3. Data Quality Impact Analysis
        4. Method Reliability Assessment
        5. Overall Workflow Quality Score
        """
        company_data = state.get('company_data', {})
        ch_sic_data = state.get('ch_sic_data', {})
        ai_prediction = state.get('ai_prediction', {})
        workflow_config = state.get('workflow_config', {})
        
        evaluation = EvaluationResult(
            ch_vs_ai_agreement=False,
            confidence_delta=0.0,
            quality_score=0.0,
            recommended_action='accept_ai',
            evaluation_reasoning='',
            refinement_suggestions=[]
        )
        
        # 1. CH SIC vs AI Prediction Agreement Analysis
        ch_agreement = self._evaluate_ch_agreement(ch_sic_data, ai_prediction)
        evaluation['ch_vs_ai_agreement'] = ch_agreement['agreement']
        evaluation['confidence_delta'] = ch_agreement['confidence_impact']
        
        # 2. Confidence Level Assessment
        confidence_assessment = self._assess_confidence_levels(ai_prediction, workflow_config)
        
        # 3. Data Quality Impact Analysis
        data_quality_impact = self._analyze_data_quality_impact(state)
        
        # 4. Method Reliability Assessment
        method_reliability = self._assess_method_reliability(ai_prediction, state)
        
        # 5. Calculate Overall Quality Score (weighted average)
        quality_components = {
            'ch_agreement': ch_agreement['score'] * 0.3,
            'confidence': confidence_assessment['score'] * 0.3,
            'data_quality': data_quality_impact['score'] * 0.2,
            'method_reliability': method_reliability['score'] * 0.2
        }
        
        evaluation['quality_score'] = sum(quality_components.values())
        
        # Generate comprehensive evaluation reasoning
        evaluation['evaluation_reasoning'] = self._generate_evaluation_reasoning(
            ch_agreement, confidence_assessment, data_quality_impact, method_reliability, quality_components
        )
        
        # Collect warnings from all assessment dimensions
        warnings = []
        warnings.extend(ch_agreement.get('warnings', []))
        warnings.extend(confidence_assessment.get('warnings', []))
        warnings.extend(data_quality_impact.get('warnings', []))
        warnings.extend(method_reliability.get('warnings', []))
        evaluation['warnings'] = warnings
        
        # Generate refinement suggestions if needed
        if evaluation['quality_score'] < 0.7:
            evaluation['refinement_suggestions'] = self._generate_refinement_suggestions(
                ch_agreement, confidence_assessment, data_quality_impact, method_reliability
            )
        
        return evaluation
    
    def _evaluate_ch_agreement(self, ch_sic_data: Dict[str, Any], ai_prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate agreement between Companies House SIC codes and AI prediction"""
        agreement = {
            'agreement': False,
            'score': 0.0,
            'confidence_impact': 0.0,
            'warnings': []
        }
        
        if not ch_sic_data or not ch_sic_data.get('success', False):
            # No CH data available
            agreement['score'] = 0.5  # Neutral score
            agreement['warnings'].append('No Companies House data available for comparison')
            return agreement
        
        ch_sic_codes = ch_sic_data.get('sic_codes', [])
        predicted_sic = ai_prediction.get('predicted_sic_code', '')
        ch_confidence = ch_sic_data.get('confidence', 0.0)
        ai_confidence = ai_prediction.get('confidence_score', 0.0)
        
        if predicted_sic in ch_sic_codes:
            # Exact agreement
            agreement['agreement'] = True
            agreement['score'] = 1.0
            agreement['confidence_impact'] = 0.2  # Boost AI confidence
        elif ch_sic_codes and len(ch_sic_codes) == 1:
            # Single CH SIC code disagrees with AI prediction
            agreement['score'] = 0.2
            agreement['confidence_impact'] = -0.1  # Reduce AI confidence
            agreement['warnings'].append(f'AI prediction {predicted_sic} differs from CH SIC {ch_sic_codes[0]}')
        elif ch_sic_codes and len(ch_sic_codes) > 1:
            # Multiple CH SIC codes - partial disagreement
            agreement['score'] = 0.4
            agreement['confidence_impact'] = -0.05
            agreement['warnings'].append(f'AI prediction {predicted_sic} not in CH SIC codes: {", ".join(ch_sic_codes)}')
        else:
            # No CH SIC codes found
            agreement['score'] = 0.3
            agreement['warnings'].append('No SIC codes found in Companies House data')
        
        # Adjust score based on CH data reliability
        if ch_confidence < 0.5:
            agreement['score'] *= 0.8  # Reduce impact of unreliable CH data
            agreement['warnings'].append('Companies House data has low confidence')
        
        return agreement
    
    def _assess_confidence_levels(self, ai_prediction: Dict[str, Any], workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assess AI prediction confidence against workflow thresholds"""
        assessment = {
            'score': 0.0,
            'meets_threshold': False,
            'warnings': []
        }
        
        confidence = ai_prediction.get('confidence_score', 0.0)
        threshold = workflow_config.get('confidence_threshold', 0.7)
        
        # Score based on confidence level
        if confidence >= threshold:
            assessment['score'] = 1.0
            assessment['meets_threshold'] = True
        elif confidence >= threshold * 0.8:  # Within 20% of threshold
            assessment['score'] = 0.8
            assessment['warnings'].append(f'Confidence {confidence:.2f} slightly below threshold {threshold}')
        elif confidence >= threshold * 0.6:  # Within 40% of threshold
            assessment['score'] = 0.6
            assessment['warnings'].append(f'Confidence {confidence:.2f} moderately below threshold {threshold}')
        else:
            assessment['score'] = 0.3
            assessment['warnings'].append(f'Confidence {confidence:.2f} significantly below threshold {threshold}')
        
        # Additional confidence quality indicators
        method = ai_prediction.get('prediction_method', 'unknown')
        if method == 'fallback':
            assessment['score'] *= 0.5
            assessment['warnings'].append('Prediction used fallback method')
        elif method == 'existing_sic_validation':
            assessment['score'] *= 0.7
            assessment['warnings'].append('Prediction based on existing SIC validation only')
        
        return assessment
    
    def _analyze_data_quality_impact(self, state: AgenticWorkflowState) -> Dict[str, Any]:
        """Analyze how data quality affects prediction reliability"""
        analysis = {
            'score': 0.0,
            'warnings': []
        }
        
        node_scores = state.get('node_confidence_scores', {})
        
        # Data ingestion quality impact
        data_ingestion_score = node_scores.get('data_ingestion', 0.0)
        if data_ingestion_score >= 0.8:
            analysis['score'] += 0.4
        elif data_ingestion_score >= 0.6:
            analysis['score'] += 0.3
            analysis['warnings'].append('Medium data quality may affect prediction accuracy')
        else:
            analysis['score'] += 0.1
            analysis['warnings'].append('Low data quality significantly impacts prediction reliability')
        
        # CH SIC retrieval quality impact
        ch_score = node_scores.get('ch_sic_retrieval', 0.0)
        if ch_score >= 0.7:
            analysis['score'] += 0.3
        elif ch_score >= 0.4:
            analysis['score'] += 0.2
        else:
            analysis['score'] += 0.1
            analysis['warnings'].append('Poor Companies House data quality')
        
        # AI prediction method quality
        ai_score = node_scores.get('ai_prediction', 0.0)
        if ai_score >= 0.7:
            analysis['score'] += 0.3
        elif ai_score >= 0.5:
            analysis['score'] += 0.2
        else:
            analysis['score'] += 0.1
            analysis['warnings'].append('AI prediction method produced low confidence results')
        
        return analysis
    
    def _assess_method_reliability(self, ai_prediction: Dict[str, Any], state: AgenticWorkflowState) -> Dict[str, Any]:
        """Assess reliability of prediction method used"""
        assessment = {
            'score': 0.0,
            'warnings': []
        }
        
        method = ai_prediction.get('prediction_method', 'unknown')
        alternatives = ai_prediction.get('alternatives', [])
        fallback_triggers = state.get('fallback_triggers', [])
        
        # Method reliability scoring
        method_scores = {
            'enhanced_fuzzy': 0.9,
            'rule_based': 0.7,
            'existing_sic_validation': 0.6,
            'fallback': 0.3,
            'disabled': 0.1,
            'unknown': 0.2
        }
        
        assessment['score'] = method_scores.get(method, 0.2)
        
        # Adjust for alternatives availability
        if alternatives and len(alternatives) >= 2:
            assessment['score'] += 0.1  # Having alternatives increases reliability
        elif not alternatives and method in ['enhanced_fuzzy', 'rule_based']:
            assessment['warnings'].append('No alternative predictions available')
        
        # Adjust for fallback triggers
        if fallback_triggers:
            assessment['score'] *= 0.8
            assessment['warnings'].append(f'Fallback triggers activated: {", ".join(fallback_triggers)}')
        
        # Method-specific warnings
        if method == 'fallback':
            assessment['warnings'].append('All prediction methods failed, using generic fallback')
        elif method == 'existing_sic_validation':
            assessment['warnings'].append('Prediction relies solely on existing SIC code validation')
        
        return assessment
    
    def _make_strategic_decision(self, evaluation: EvaluationResult, state: AgenticWorkflowState) -> Dict[str, Any]:
        """Make strategic decision based on evaluation results"""
        quality_score = evaluation.get('quality_score', 0.0)
        confidence_threshold = state.get('workflow_config', {}).get('confidence_threshold', 0.7)
        ch_agreement = evaluation.get('ch_vs_ai_agreement', False)
        
        decision = {
            'action': 'accept_ai',
            'reasoning': '',
            'confidence': quality_score
        }
        
        # Decision logic based on quality score and specific conditions
        if quality_score >= 0.8:
            decision['action'] = 'accept_ai'
            decision['reasoning'] = 'High quality prediction with strong validation'
        elif quality_score >= 0.6 and ch_agreement:
            decision['action'] = 'accept_ai'
            decision['reasoning'] = 'Good quality prediction validated by Companies House data'
        elif quality_score >= 0.6:
            decision['action'] = 'accept_ai'
            decision['reasoning'] = 'Acceptable quality prediction'
        elif quality_score >= 0.4:
            decision['action'] = 'accept_ch' if state.get('ch_sic_data', {}).get('success') else 'accept_ai'
            decision['reasoning'] = 'Medium quality - prefer Companies House data if available'
        elif quality_score >= 0.3:
            decision['action'] = 'request_refinement'
            decision['reasoning'] = 'Quality below threshold - refinement recommended'
        else:
            decision['action'] = 'use_fallback'
            decision['reasoning'] = 'Quality too low - fallback to existing systems required'
        
        return decision
    
    def _generate_evaluation_reasoning(self, ch_agreement: Dict[str, Any], confidence_assessment: Dict[str, Any],
                                     data_quality_impact: Dict[str, Any], method_reliability: Dict[str, Any],
                                     quality_components: Dict[str, float]) -> str:
        """Generate comprehensive evaluation reasoning"""
        reasoning_parts = []
        
        # Overall quality assessment
        total_score = sum(quality_components.values())
        reasoning_parts.append(f"Overall quality score: {total_score:.2f}")
        
        # Component breakdown
        reasoning_parts.append("Quality breakdown:")
        for component, score in quality_components.items():
            reasoning_parts.append(f"  - {component.replace('_', ' ').title()}: {score:.2f}")
        
        # Key findings
        if ch_agreement['agreement']:
            reasoning_parts.append("✓ Companies House validation confirms AI prediction")
        elif ch_agreement.get('warnings'):
            reasoning_parts.append(f"⚠ CH Agreement: {ch_agreement['warnings'][0]}")
        
        if confidence_assessment['meets_threshold']:
            reasoning_parts.append("✓ Confidence meets required threshold")
        elif confidence_assessment.get('warnings'):
            reasoning_parts.append(f"⚠ Confidence: {confidence_assessment['warnings'][0]}")
        
        return " | ".join(reasoning_parts)
    
    def _generate_refinement_suggestions(self, ch_agreement: Dict[str, Any], confidence_assessment: Dict[str, Any],
                                       data_quality_impact: Dict[str, Any], method_reliability: Dict[str, Any]) -> List[str]:
        """Generate specific refinement suggestions based on evaluation results"""
        suggestions = []
        
        # CH agreement suggestions
        if not ch_agreement['agreement'] and ch_agreement['score'] < 0.5:
            suggestions.append("Consider manual review due to disagreement with Companies House data")
        
        # Confidence improvement suggestions
        if not confidence_assessment['meets_threshold']:
            suggestions.append("Gather additional business description or company data to improve confidence")
        
        # Data quality improvement suggestions
        if data_quality_impact['score'] < 0.5:
            suggestions.append("Improve input data quality (business description, company identification)")
        
        # Method reliability suggestions
        if method_reliability['score'] < 0.6:
            suggestions.append("Consider using alternative prediction methods or manual classification")
        
        return suggestions
    
    def _create_workflow_decision(self, node_name: str, decision: str, confidence: float) -> WorkflowDecision:
        """Create standardized workflow decision record"""
        return WorkflowDecision(
            node_name=node_name,
            timestamp=datetime.now(),
            decision=decision,
            reasoning=f"Reflection evaluation completed with quality score {confidence:.2f}",
            confidence=confidence,
            fallback_triggered=confidence < 0.5
        )
    
    def _create_workflow_step(self, step_name: str, status: str, evaluation: EvaluationResult,
                            decision: Dict[str, Any]) -> Dict[str, Any]:
        """Create workflow step for frontend visualization"""
        return {
            'step': step_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'quality_score': evaluation.get('quality_score', 0.0),
                'ch_vs_ai_agreement': evaluation.get('ch_vs_ai_agreement', False),
                'recommended_action': evaluation.get('recommended_action', 'unknown'),
                'strategic_decision': decision['action'],
                'confidence_delta': evaluation.get('confidence_delta', 0.0),
                'warnings_count': len(evaluation.get('warnings', [])),
                'refinement_suggestions': evaluation.get('refinement_suggestions', [])
            },
            'icon': '🔍',
            'duration_ms': 0
        }
    
    def _handle_disabled_reflection(self, state: AgenticWorkflowState, start_time: datetime) -> AgenticWorkflowState:
        """Handle case where reflection is disabled"""
        self.logger.info("🔇 Reflection disabled by workflow configuration")
        
        # Create minimal evaluation result
        evaluation = EvaluationResult(
            ch_vs_ai_agreement=True,  # Assume agreement when disabled
            confidence_delta=0.0,
            quality_score=0.5,  # Neutral score
            recommended_action='accept_ai',
            evaluation_reasoning='Reflection disabled by configuration',
            refinement_suggestions=[]
        )
        
        decision = WorkflowDecision(
            node_name="reflection_evaluation",
            timestamp=datetime.now(),
            decision="Reflection disabled",
            reasoning="Workflow configuration disabled reflection and evaluation",
            confidence=0.5,
            fallback_triggered=False
        )
        
        updated_state = state.copy()
        updated_state.update({
            'evaluation_result': evaluation,
            'workflow_decisions': state.get('workflow_decisions', []) + [decision],
            'node_confidence_scores': {
                **state.get('node_confidence_scores', {}),
                'reflection_evaluation': 0.5
            },
            'current_node': 'reflection_evaluation',
            'fallback_triggers': state.get('fallback_triggers', []) + ['reflection_disabled'],
            'node_execution_times': {
                **state.get('node_execution_times', {}),
                'reflection_evaluation': (datetime.now() - start_time).total_seconds()
            },
            'workflow_steps': state.get('workflow_steps', []) + [
                self._create_disabled_workflow_step()
            ]
        })
        
        return updated_state
    
    def _create_disabled_workflow_step(self) -> Dict[str, Any]:
        """Create workflow step for disabled reflection"""
        return {
            'step': 'Reflection & Evaluation',
            'status': 'skipped',
            'timestamp': datetime.now().isoformat(),
            'details': {'reason': 'Disabled by configuration'},
            'icon': '🔇',
            'duration_ms': 0
        }
    
    def _handle_error(self, state: AgenticWorkflowState, error_message: str, start_time: datetime) -> AgenticWorkflowState:
        """Handle errors with fallback evaluation"""
        self.logger.error(f"❌ Reflection Error: {error_message}")
        
        # Create minimal fallback evaluation
        evaluation = EvaluationResult(
            ch_vs_ai_agreement=False,
            confidence_delta=0.0,
            quality_score=0.3,
            recommended_action='use_fallback',
            evaluation_reasoning=f'Evaluation failed: {error_message}',
            refinement_suggestions=['Manual review required due to evaluation failure']
        )
        
        updated_state = state.copy()
        updated_state.update({
            'evaluation_result': evaluation,
            'errors': state.get('errors', []) + [error_message],
            'fallback_triggers': state.get('fallback_triggers', []) + ['reflection_error'],
            'current_node': 'reflection_evaluation',
            'node_execution_times': {
                **state.get('node_execution_times', {}),
                'reflection_evaluation': (datetime.now() - start_time).total_seconds()
            },
            'workflow_steps': state.get('workflow_steps', []) + [
                self._create_error_workflow_step(error_message)
            ]
        })
        
        return updated_state
    
    def _create_error_workflow_step(self, error_message: str) -> Dict[str, Any]:
        """Create error workflow step for frontend display"""
        return {
            'step': 'Reflection & Evaluation',
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'details': {'error': error_message},
            'icon': '❌',
            'duration_ms': 0
        }