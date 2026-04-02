"""
Reasoning Generator Node

This node leverages the existing RealtimeReasoningService to generate enhanced contextual
reasoning for the agentic workflow. It provides intelligent explanations for SIC predictions,
validates reasoning quality, and generates comprehensive workflow documentation.

Responsibilities:
- Generate enhanced SIC prediction reasoning using RealtimeReasoningService
- Create contextual workflow explanations
- Validate reasoning quality and coherence
- Provide detailed reasoning for strategic decisions
- Generate comprehensive workflow summary reasoning

Integration Points:
- Existing RealtimeReasoningService (core reasoning engine)
- Workflow state management and decision tracking
- Confidence calculation and validation systems
- Frontend workflow visualization and explanation
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..workflow_state import AgenticWorkflowState, WorkflowDecision

logger = logging.getLogger(__name__)


class ReasoningGeneratorNode:
    """
    Advanced reasoning generator node using existing RealtimeReasoningService infrastructure.
    
    This node enhances the agentic workflow with intelligent explanations, validates reasoning
    quality, and generates comprehensive workflow documentation for transparency and auditability.
    """
    
    def __init__(self, realtime_reasoning_service=None):
        """
        Initialize with existing infrastructure dependencies.
        
        Args:
            realtime_reasoning_service: RealtimeReasoningService instance for reasoning generation
        """
        self.realtime_reasoning_service = realtime_reasoning_service
        self.logger = logger.getChild(self.__class__.__name__)
    
    def __call__(self, state: AgenticWorkflowState) -> AgenticWorkflowState:
        """
        Execute intelligent reasoning generation for the workflow results.
        
        Args:
            state: Current workflow state with all node results and decisions
            
        Returns:
            Enhanced state with comprehensive reasoning and explanations
        """
        start_time = datetime.now()
        
        try:
            company_data = state.get('company_data')
            ai_prediction = state.get('ai_prediction')
            evaluation_result = state.get('evaluation_result')
            
            if not company_data or not ai_prediction:
                return self._handle_error(state, "Missing required data for reasoning generation", start_time)
            
            company_name = company_data.get('company_name', 'Unknown')
            predicted_sic = ai_prediction.get('predicted_sic_code', '')
            
            self.logger.info(f"🧠 Reasoning Generator: Creating enhanced reasoning for {company_name} -> {predicted_sic}")
            
            # Check if reasoning generation is enabled
            workflow_config = state.get('workflow_config', {})
            if not workflow_config.get('enable_reasoning_generation', True):
                return self._handle_disabled_reasoning(state, start_time)
            
            # Generate comprehensive reasoning using existing service
            if self.realtime_reasoning_service:
                enhanced_reasoning = self._generate_enhanced_reasoning(state)
            else:
                enhanced_reasoning = self._generate_fallback_reasoning(state)
            
            # Validate reasoning quality
            reasoning_quality = self._validate_reasoning_quality(enhanced_reasoning, state)
            
            # Generate workflow summary reasoning
            workflow_reasoning = self._generate_workflow_summary_reasoning(state, enhanced_reasoning)
            
            # Create workflow decision record
            decision = self._create_workflow_decision(
                "reasoning_generation",
                f"Enhanced reasoning generated: Quality {reasoning_quality['score']:.2f}",
                reasoning_quality['score']
            )
            
            # Update workflow state
            updated_state = state.copy()
            updated_state.update({
                'enhanced_reasoning': enhanced_reasoning,
                'workflow_reasoning': workflow_reasoning,
                'reasoning_quality': reasoning_quality,
                'workflow_decisions': state.get('workflow_decisions', []) + [decision],
                'node_confidence_scores': {
                    **state.get('node_confidence_scores', {}),
                    'reasoning_generation': reasoning_quality['score']
                },
                'current_node': 'reasoning_generation',
                'warnings': state.get('warnings', []) + reasoning_quality.get('warnings', []),
                'node_execution_times': {
                    **state.get('node_execution_times', {}),
                    'reasoning_generation': (datetime.now() - start_time).total_seconds()
                },
                # Note: Do not add separate workflow step - combined with reflection step for 5-step UI
            })
            
            success_msg = f"✅ Reasoning Generator: Enhanced reasoning generated - Quality: {reasoning_quality['score']:.2f}"
            self.logger.info(success_msg)
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ Reasoning Generator: Error during reasoning generation: {e}")
            return self._handle_error(state, f"Reasoning generation failed: {str(e)}", start_time)
    
    def _generate_enhanced_reasoning(self, state: AgenticWorkflowState) -> Dict[str, Any]:
        """
        Generate enhanced reasoning using the existing RealtimeReasoningService.
        
        This leverages the existing infrastructure to provide contextual SIC predictions
        with detailed explanations that consider the agentic workflow context.
        """
        company_data = state.get('company_data', {})
        ai_prediction = state.get('ai_prediction', {})
        ch_sic_data = state.get('ch_sic_data', {})
        evaluation_result = state.get('evaluation_result', {})
        
        # Prepare enhanced context for reasoning service
        reasoning_context = {
            'company_name': company_data.get('company_name', ''),
            'business_description': company_data.get('business_description', ''),
            'predicted_sic_code': ai_prediction.get('predicted_sic_code', ''),
            'prediction_method': ai_prediction.get('prediction_method', ''),
            'confidence_score': ai_prediction.get('confidence_score', 0.0),
            'alternatives': ai_prediction.get('alternatives', []),
            'ch_sic_codes': ch_sic_data.get('sic_codes', []) if ch_sic_data else [],
            'ch_confidence': ch_sic_data.get('confidence', 0.0) if ch_sic_data else 0.0,
            'evaluation_quality': evaluation_result.get('quality_score', 0.0),
            'ch_vs_ai_agreement': evaluation_result.get('ch_vs_ai_agreement', False),
            'workflow_nodes_executed': list(state.get('node_confidence_scores', {}).keys()),
            'fallback_triggers': state.get('fallback_triggers', [])
        }
        
        try:
            # Use existing RealtimeReasoningService for core reasoning
            reasoning_response = self.realtime_reasoning_service.generate_contextual_reasoning(
                company_name=reasoning_context['company_name'],
                business_description=reasoning_context['business_description'],
                predicted_sic=reasoning_context['predicted_sic_code'],
                confidence=reasoning_context['confidence_score'],
                context_data=reasoning_context
            )
            
            # Enhance with agentic workflow-specific reasoning
            enhanced_reasoning = {
                'core_reasoning': reasoning_response.get('reasoning', ''),
                'confidence_explanation': reasoning_response.get('confidence_explanation', ''),
                'methodology_explanation': self._generate_methodology_explanation(state),
                'workflow_decision_reasoning': self._generate_decision_reasoning(state),
                'data_quality_impact': self._explain_data_quality_impact(state),
                'alternative_considerations': self._explain_alternative_considerations(ai_prediction),
                'validation_reasoning': self._generate_validation_reasoning(state),
                'transparency_notes': self._generate_transparency_notes(state),
                'reasoning_metadata': {
                    'generation_timestamp': datetime.now().isoformat(),
                    'reasoning_service_version': reasoning_response.get('version', 'unknown'),
                    'context_completeness': self._assess_context_completeness(reasoning_context),
                    'reasoning_confidence': reasoning_response.get('reasoning_confidence', 0.0)
                }
            }
            
            return enhanced_reasoning
            
        except Exception as e:
            self.logger.warning(f"RealtimeReasoningService failed: {e}, using fallback reasoning")
            return self._generate_fallback_reasoning(state)
    
    def _generate_methodology_explanation(self, state: AgenticWorkflowState) -> str:
        """Generate explanation of the methodology used in the agentic workflow"""
        ai_prediction = state.get('ai_prediction', {})
        ch_sic_data = state.get('ch_sic_data', {})
        node_scores = state.get('node_confidence_scores', {})
        
        method_used = ai_prediction.get('prediction_method', 'unknown')
        ch_success = ch_sic_data.get('success', False) if ch_sic_data else False
        
        methodology_parts = []
        
        # Primary methodology description
        methodology_map = {
            'enhanced_fuzzy': 'Advanced fuzzy matching with semantic understanding',
            'rule_based': 'Rule-based classification using business patterns',
            'existing_sic_validation': 'Validation against existing SIC classifications',
            'fallback': 'Generic fallback classification method'
        }
        
        primary_method = methodology_map.get(method_used, f'Unknown method: {method_used}')
        methodology_parts.append(f"Primary prediction method: {primary_method}")
        
        # Data source integration
        if ch_success:
            methodology_parts.append("Companies House data successfully integrated for validation")
        else:
            methodology_parts.append("Companies House data unavailable or unreliable")
        
        # Quality assessment methodology
        data_quality = node_scores.get('data_ingestion', 0.0)
        if data_quality >= 0.8:
            methodology_parts.append("High-quality input data enabled robust classification")
        elif data_quality >= 0.6:
            methodology_parts.append("Medium-quality input data with additional validation layers")
        else:
            methodology_parts.append("Limited input data quality required enhanced validation methods")
        
        # Agentic workflow enhancements
        methodology_parts.append("Multi-node agentic workflow with reflection and quality validation")
        
        return " | ".join(methodology_parts)
    
    def _generate_decision_reasoning(self, state: AgenticWorkflowState) -> str:
        """Generate reasoning for key workflow decisions"""
        evaluation_result = state.get('evaluation_result', {})
        workflow_decisions = state.get('workflow_decisions', [])
        
        decision_points = []
        
        # Evaluation decision reasoning
        quality_score = evaluation_result.get('quality_score', 0.0)
        recommended_action = evaluation_result.get('recommended_action', 'unknown')
        
        if quality_score >= 0.8:
            decision_points.append(f"High confidence prediction (quality: {quality_score:.2f}) accepted directly")
        elif quality_score >= 0.6:
            decision_points.append(f"Medium confidence prediction (quality: {quality_score:.2f}) accepted with validation")
        else:
            decision_points.append(f"Low confidence prediction (quality: {quality_score:.2f}) requires additional review")
        
        # CH vs AI agreement decision
        ch_agreement = evaluation_result.get('ch_vs_ai_agreement', False)
        if ch_agreement:
            decision_points.append("Companies House data confirms AI prediction, increasing confidence")
        else:
            decision_points.append("AI prediction differs from Companies House data, requiring careful evaluation")
        
        # Fallback trigger decisions
        fallback_triggers = state.get('fallback_triggers', [])
        if fallback_triggers:
            decision_points.append(f"Fallback mechanisms triggered: {', '.join(fallback_triggers)}")
        
        return " | ".join(decision_points) if decision_points else "Standard workflow execution without special decisions"
    
    def _explain_data_quality_impact(self, state: AgenticWorkflowState) -> str:
        """Explain how data quality affected the prediction"""
        node_scores = state.get('node_confidence_scores', {})
        company_data = state.get('company_data', {})
        ch_sic_data = state.get('ch_sic_data', {})
        
        impact_factors = []
        
        # Input data quality impact
        data_score = node_scores.get('data_ingestion', 0.0)
        business_desc = company_data.get('business_description', '')
        
        if data_score >= 0.8:
            impact_factors.append("Excellent input data quality enabled high-confidence predictions")
        elif data_score >= 0.6:
            impact_factors.append("Good input data quality with minor limitations addressed")
        else:
            impact_factors.append("Limited input data quality required additional validation steps")
        
        # Business description impact
        if len(business_desc) > 100:
            impact_factors.append("Comprehensive business description provided rich context")
        elif len(business_desc) > 20:
            impact_factors.append("Basic business description provided adequate context")
        else:
            impact_factors.append("Limited business description required inference from company name")
        
        # Companies House data impact
        ch_score = node_scores.get('ch_sic_retrieval', 0.0)
        if ch_score >= 0.7:
            impact_factors.append("Reliable Companies House data enhanced prediction validation")
        elif ch_score >= 0.4:
            impact_factors.append("Partial Companies House data provided some validation")
        else:
            impact_factors.append("Limited Companies House data reduced external validation options")
        
        return " | ".join(impact_factors)
    
    def _explain_alternative_considerations(self, ai_prediction: Dict[str, Any]) -> str:
        """Explain alternative SIC codes that were considered and why they were rejected"""
        alternatives = ai_prediction.get('alternatives', [])
        predicted_sic = ai_prediction.get('predicted_sic_code', '')
        
        if not alternatives:
            return "No significant alternative classifications identified during analysis"
        
        alternative_explanations = []
        
        for i, alt in enumerate(alternatives[:3]):  # Limit to top 3 alternatives
            alt_code = alt.get('sic_code', '')
            alt_score = alt.get('fuzzy_score', 0)
            alt_desc = alt.get('sic_description', '')
            
            if alt_code and alt_code != predicted_sic:
                explanation = f"Alternative {i+1}: SIC {alt_code} ({alt_desc}) scored {alt_score:.1f}% but was rejected due to "
                
                # Explain why this alternative was not chosen
                if alt_score < 70:
                    explanation += "insufficient similarity to business description"
                elif alt_score < 85:
                    explanation += "lower contextual relevance than primary prediction"
                else:
                    explanation += "domain-specific factors favoring the primary prediction"
                
                alternative_explanations.append(explanation)
        
        if not alternative_explanations:
            return "Alternative classifications were not competitive with the primary prediction"
        
        return " | ".join(alternative_explanations)
        """Explain alternative predictions and why the chosen one was selected"""
        alternatives = ai_prediction.get('alternatives', [])
        predicted_sic = ai_prediction.get('predicted_sic_code', '')
        confidence = ai_prediction.get('confidence_score', 0.0)
        
        if not alternatives:
            return f"Single prediction {predicted_sic} with confidence {confidence:.2f} - no alternatives generated"
        
        considerations = []
        considerations.append(f"Primary prediction: {predicted_sic} (confidence: {confidence:.2f})")
        
        # Analyze alternatives
        alt_count = len(alternatives)
        considerations.append(f"{alt_count} alternative prediction(s) considered")
        
        if alt_count >= 3:
            considerations.append("Multiple strong alternatives indicate sector boundary classification")
        elif alt_count >= 1:
            top_alt = alternatives[0]
            alt_conf = top_alt.get('confidence', 0.0)
            alt_sic = top_alt.get('sic_code', '')
            
            if confidence - alt_conf < 0.1:
                considerations.append(f"Close alternative {alt_sic} (confidence: {alt_conf:.2f}) suggests sector ambiguity")
            else:
                considerations.append(f"Alternative {alt_sic} significantly lower confidence ({alt_conf:.2f})")
        
        return " | ".join(considerations)
    
    def _generate_validation_reasoning(self, state: AgenticWorkflowState) -> str:
        """Generate reasoning about validation steps and their outcomes"""
        evaluation_result = state.get('evaluation_result', {})
        node_scores = state.get('node_confidence_scores', {})
        
        validation_steps = []
        
        # Data validation
        if 'data_ingestion' in node_scores:
            validation_steps.append("Input data validated for completeness and quality")
        
        # CH validation
        if 'ch_sic_retrieval' in node_scores:
            ch_score = node_scores['ch_sic_retrieval']
            if ch_score >= 0.7:
                validation_steps.append("Companies House validation successful")
            else:
                validation_steps.append("Companies House validation incomplete or unreliable")
        
        # AI prediction validation
        if 'ai_prediction' in node_scores:
            validation_steps.append("AI prediction method validated for reliability")
        
        # Reflection validation
        if 'reflection_evaluation' in node_scores:
            reflection_score = node_scores['reflection_evaluation']
            if reflection_score >= 0.7:
                validation_steps.append("Quality reflection confirms prediction reliability")
            else:
                validation_steps.append("Quality reflection identifies potential improvements needed")
        
        # Overall validation assessment
        overall_quality = evaluation_result.get('quality_score', 0.0)
        if overall_quality >= 0.8:
            validation_steps.append("All validation steps confirm high prediction quality")
        elif overall_quality >= 0.6:
            validation_steps.append("Validation steps confirm acceptable prediction quality")
        else:
            validation_steps.append("Validation steps indicate quality improvements needed")
        
        return " | ".join(validation_steps)
    
    def _generate_transparency_notes(self, state: AgenticWorkflowState) -> str:
        """Generate transparency notes about the workflow process"""
        notes = []
        
        # Workflow execution transparency
        executed_nodes = list(state.get('node_confidence_scores', {}).keys())
        notes.append(f"Executed workflow nodes: {', '.join(executed_nodes)}")
        
        # Timing transparency
        execution_times = state.get('node_execution_times', {})
        if execution_times:
            total_time = sum(execution_times.values())
            notes.append(f"Total processing time: {total_time:.2f} seconds")
        
        # Error and warning transparency
        errors = state.get('errors', [])
        warnings = state.get('warnings', [])
        
        if errors:
            notes.append(f"Errors encountered: {len(errors)} (see logs for details)")
        if warnings:
            notes.append(f"Warnings generated: {len(warnings)} (quality impacts noted)")
        
        # Fallback transparency
        fallback_triggers = state.get('fallback_triggers', [])
        if fallback_triggers:
            notes.append(f"Fallback mechanisms activated: {', '.join(fallback_triggers)}")
        
        # Configuration transparency
        workflow_config = state.get('workflow_config', {})
        if workflow_config:
            config_items = [f"{k}={v}" for k, v in workflow_config.items() if isinstance(v, (bool, str, int, float))]
            if config_items:
                notes.append(f"Configuration: {', '.join(config_items[:3])}")  # Limit to first 3 items
        
        return " | ".join(notes)
    
    def _assess_context_completeness(self, reasoning_context: Dict[str, Any]) -> float:
        """Assess completeness of context provided to reasoning service"""
        required_fields = ['company_name', 'business_description', 'predicted_sic_code']
        optional_fields = ['alternatives', 'ch_sic_codes', 'evaluation_quality']
        
        score = 0.0
        
        # Required fields (60% of score)
        for field in required_fields:
            if reasoning_context.get(field):
                score += 0.2
        
        # Optional fields (40% of score)
        for field in optional_fields:
            if reasoning_context.get(field):
                score += 0.133  # 0.4 / 3 fields
        
        return min(score, 1.0)
    
    def _generate_workflow_summary_reasoning(self, state: AgenticWorkflowState, enhanced_reasoning: Dict[str, Any]) -> str:
        """Generate comprehensive workflow summary reasoning"""
        company_data = state.get('company_data', {})
        ai_prediction = state.get('ai_prediction', {})
        evaluation_result = state.get('evaluation_result', {})
        
        company_name = company_data.get('company_name', 'Unknown')
        predicted_sic = ai_prediction.get('predicted_sic_code', '')
        quality_score = evaluation_result.get('quality_score', 0.0)
        
        summary_parts = [
            f"Agentic SIC prediction completed for {company_name}",
            f"Predicted SIC code: {predicted_sic}",
            f"Overall quality assessment: {quality_score:.2f}",
            enhanced_reasoning.get('methodology_explanation', ''),
            enhanced_reasoning.get('validation_reasoning', ''),
            f"Reasoning confidence: {enhanced_reasoning.get('reasoning_metadata', {}).get('reasoning_confidence', 0.0):.2f}"
        ]
        
        return " | ".join(filter(None, summary_parts))
    
    def _generate_fallback_reasoning(self, state: AgenticWorkflowState) -> Dict[str, Any]:
        """Generate fallback reasoning when RealtimeReasoningService is unavailable"""
        self.logger.warning("Using fallback reasoning generation - RealtimeReasoningService unavailable")
        
        company_data = state.get('company_data', {})
        ai_prediction = state.get('ai_prediction', {})
        evaluation_result = state.get('evaluation_result', {})
        
        fallback_reasoning = {
            'core_reasoning': self._generate_basic_reasoning(company_data, ai_prediction),
            'confidence_explanation': self._generate_basic_confidence_explanation(ai_prediction),
            'methodology_explanation': self._generate_methodology_explanation(state),
            'workflow_decision_reasoning': self._generate_decision_reasoning(state),
            'data_quality_impact': self._explain_data_quality_impact(state),
            'alternative_considerations': self._explain_alternative_considerations(ai_prediction),
            'validation_reasoning': self._generate_validation_reasoning(state),
            'transparency_notes': self._generate_transparency_notes(state),
            'reasoning_metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'reasoning_service_version': 'fallback',
                'context_completeness': 0.5,  # Reduced for fallback
                'reasoning_confidence': 0.6  # Lower confidence for fallback
            }
        }
        
        return fallback_reasoning
    
    def _generate_basic_reasoning(self, company_data: Dict[str, Any], ai_prediction: Dict[str, Any]) -> str:
        """Generate basic reasoning without RealtimeReasoningService"""
        company_name = company_data.get('company_name', 'Unknown')
        business_desc = company_data.get('business_description', '')
        predicted_sic = ai_prediction.get('predicted_sic_code', '')
        method = ai_prediction.get('prediction_method', 'unknown')
        
        reasoning_parts = [
            f"SIC code {predicted_sic} predicted for {company_name}",
            f"Prediction method: {method}",
            f"Business context: {business_desc[:100]}..." if len(business_desc) > 100 else f"Business context: {business_desc}"
        ]
        
        return " | ".join(filter(None, reasoning_parts))
    
    def _generate_basic_confidence_explanation(self, ai_prediction: Dict[str, Any]) -> str:
        """Generate basic confidence explanation"""
        confidence = ai_prediction.get('confidence_score', 0.0)
        method = ai_prediction.get('prediction_method', 'unknown')
        alternatives = ai_prediction.get('alternatives', [])
        
        if confidence >= 0.8:
            explanation = f"High confidence ({confidence:.2f}) indicates strong pattern match"
        elif confidence >= 0.6:
            explanation = f"Medium confidence ({confidence:.2f}) suggests probable classification"
        else:
            explanation = f"Lower confidence ({confidence:.2f}) indicates classification uncertainty"
        
        if alternatives:
            explanation += f" with {len(alternatives)} alternatives considered"
        
        explanation += f" using {method} method"
        
        return explanation
    
    def _validate_reasoning_quality(self, enhanced_reasoning: Dict[str, Any], state: AgenticWorkflowState) -> Dict[str, Any]:
        """Validate quality of generated reasoning"""
        quality_assessment = {
            'score': 0.0,
            'warnings': [],
            'completeness': 0.0,
            'coherence': 0.0,
            'accuracy': 0.0
        }
        
        # Assess completeness (1/3 of score)
        required_components = ['core_reasoning', 'methodology_explanation', 'validation_reasoning']
        present_components = sum(1 for comp in required_components if enhanced_reasoning.get(comp))
        completeness = present_components / len(required_components)
        quality_assessment['completeness'] = completeness
        
        # Assess coherence (1/3 of score)
        core_reasoning = enhanced_reasoning.get('core_reasoning', '')
        methodology = enhanced_reasoning.get('methodology_explanation', '')
        
        coherence = 0.0
        if len(core_reasoning) > 50:  # Minimum reasoning length
            coherence += 0.3
        if len(methodology) > 30:  # Methodology explanation exists
            coherence += 0.3
        
        reasoning_confidence = enhanced_reasoning.get('reasoning_metadata', {}).get('reasoning_confidence', 0.0)
        coherence += reasoning_confidence * 0.4  # Reasoning service confidence
        
        quality_assessment['coherence'] = min(coherence, 1.0)
        
        # Assess accuracy (1/3 of score)
        context_completeness = enhanced_reasoning.get('reasoning_metadata', {}).get('context_completeness', 0.0)
        quality_assessment['accuracy'] = context_completeness
        
        # Calculate overall score
        quality_assessment['score'] = (completeness + coherence + context_completeness) / 3
        
        # Generate warnings
        if completeness < 0.8:
            quality_assessment['warnings'].append('Reasoning components incomplete')
        if coherence < 0.6:
            quality_assessment['warnings'].append('Reasoning coherence below expected level')
        if context_completeness < 0.7:
            quality_assessment['warnings'].append('Limited context affected reasoning quality')
        
        return quality_assessment
    
    def _create_workflow_decision(self, node_name: str, decision: str, confidence: float) -> WorkflowDecision:
        """Create standardized workflow decision record"""
        return WorkflowDecision(
            node_name=node_name,
            timestamp=datetime.now(),
            decision=decision,
            reasoning=f"Reasoning generation completed with quality {confidence:.2f}",
            confidence=confidence,
            fallback_triggered=confidence < 0.6
        )
    
    def _create_workflow_step(self, step_name: str, status: str, enhanced_reasoning: Dict[str, Any],
                            quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Create workflow step for frontend visualization"""
        return {
            'step': step_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'reasoning_quality': quality_assessment['score'],
                'completeness': quality_assessment['completeness'],
                'coherence': quality_assessment['coherence'],
                'accuracy': quality_assessment['accuracy'],
                'reasoning_confidence': enhanced_reasoning.get('reasoning_metadata', {}).get('reasoning_confidence', 0.0),
                'warnings_count': len(quality_assessment.get('warnings', [])),
                'reasoning_length': len(enhanced_reasoning.get('core_reasoning', '')),
                'service_version': enhanced_reasoning.get('reasoning_metadata', {}).get('reasoning_service_version', 'unknown')
            },
            'icon': '🧠',
            'duration_ms': 0
        }
    
    def _handle_disabled_reasoning(self, state: AgenticWorkflowState, start_time: datetime) -> AgenticWorkflowState:
        """Handle case where reasoning generation is disabled"""
        self.logger.info("🔇 Reasoning generation disabled by workflow configuration")
        
        # Create minimal reasoning
        basic_reasoning = {
            'core_reasoning': 'Reasoning generation disabled by configuration',
            'methodology_explanation': 'Standard workflow execution',
            'validation_reasoning': 'Basic validation completed',
            'reasoning_metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'reasoning_service_version': 'disabled',
                'context_completeness': 0.0,
                'reasoning_confidence': 0.0
            }
        }
        
        quality_assessment = {
            'score': 0.3,
            'warnings': ['Reasoning generation disabled'],
            'completeness': 0.0,
            'coherence': 0.0,
            'accuracy': 0.0
        }
        
        decision = WorkflowDecision(
            node_name="reasoning_generation",
            timestamp=datetime.now(),
            decision="Reasoning generation disabled",
            reasoning="Workflow configuration disabled reasoning generation",
            confidence=0.3,
            fallback_triggered=True
        )
        
        updated_state = state.copy()
        updated_state.update({
            'enhanced_reasoning': basic_reasoning,
            'reasoning_quality': quality_assessment,
            'workflow_decisions': state.get('workflow_decisions', []) + [decision],
            'node_confidence_scores': {
                **state.get('node_confidence_scores', {}),
                'reasoning_generation': 0.3
            },
            'current_node': 'reasoning_generation',
            'warnings': state.get('warnings', []) + ['Reasoning generation disabled'],
            'fallback_triggers': state.get('fallback_triggers', []) + ['reasoning_disabled'],
            'node_execution_times': {
                **state.get('node_execution_times', {}),
                'reasoning_generation': (datetime.now() - start_time).total_seconds()
            },
            'workflow_steps': state.get('workflow_steps', []) + [
                self._create_disabled_workflow_step()
            ]
        })
        
        return updated_state
    
    def _create_disabled_workflow_step(self) -> Dict[str, Any]:
        """Create workflow step for disabled reasoning"""
        return {
            'step': 'Reasoning Generation',
            'status': 'skipped',
            'timestamp': datetime.now().isoformat(),
            'details': {'reason': 'Disabled by configuration'},
            'icon': '🔇',
            'duration_ms': 0
        }
    
    def _handle_error(self, state: AgenticWorkflowState, error_message: str, start_time: datetime) -> AgenticWorkflowState:
        """Handle errors with fallback reasoning"""
        self.logger.error(f"❌ Reasoning Generator Error: {error_message}")
        
        # Create minimal error reasoning
        error_reasoning = {
            'core_reasoning': f'Reasoning generation failed: {error_message}',
            'methodology_explanation': 'Error in reasoning process',
            'validation_reasoning': 'Reasoning validation unavailable due to error',
            'reasoning_metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'reasoning_service_version': 'error',
                'context_completeness': 0.0,
                'reasoning_confidence': 0.0
            }
        }
        
        quality_assessment = {
            'score': 0.1,
            'warnings': [f'Reasoning generation error: {error_message}'],
            'completeness': 0.0,
            'coherence': 0.0,
            'accuracy': 0.0
        }
        
        updated_state = state.copy()
        updated_state.update({
            'enhanced_reasoning': error_reasoning,
            'reasoning_quality': quality_assessment,
            'errors': state.get('errors', []) + [error_message],
            'fallback_triggers': state.get('fallback_triggers', []) + ['reasoning_error'],
            'current_node': 'reasoning_generation',
            'node_execution_times': {
                **state.get('node_execution_times', {}),
                'reasoning_generation': (datetime.now() - start_time).total_seconds()
            },
            'workflow_steps': state.get('workflow_steps', []) + [
                self._create_error_workflow_step(error_message)
            ]
        })
        
        return updated_state
    
    def _create_error_workflow_step(self, error_message: str) -> Dict[str, Any]:
        """Create error workflow step for frontend display"""
        return {
            'step': 'Reasoning Generation',
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'details': {'error': error_message},
            'icon': '❌',
            'duration_ms': 0
        }
    
    def generate_dashboard_reasoning(self, state: AgenticWorkflowState) -> Dict[str, str]:
        """
        Generate compact reasoning for dashboard display.
        
        Returns:
            Dict with 'ai_reasoning' and 'ch_comparison' keys for dashboard
        """
        try:
            company_data = state.get('company_data', {})
            ai_prediction = state.get('ai_prediction', {})
            ch_sic_data = state.get('ch_sic_data', {})
            evaluation_result = state.get('evaluation_result', {})
            
            company_name = company_data.get('company_name', 'Company')
            predicted_sic = ai_prediction.get('predicted_sic_code', '')
            confidence = ai_prediction.get('confidence_score', 0.0)
            prediction_method = ai_prediction.get('prediction_method', 'AI analysis')
            
            # Generate 2-3 sentence AI reasoning explanation
            ai_reasoning = self._generate_compact_ai_reasoning(
                company_name, predicted_sic, confidence, prediction_method, ai_prediction
            )
            
            # Generate Companies House comparison reasoning
            ch_comparison = self._generate_ch_comparison_reasoning(
                predicted_sic, ch_sic_data, evaluation_result, company_name
            )
            
            self.logger.info(f"🔍 DEBUG - Dashboard reasoning generated: ai_reasoning='{ai_reasoning}', ch_comparison='{ch_comparison}'")
            
            return {
                'ai_reasoning': ai_reasoning,
                'ch_comparison': ch_comparison
            }
            
        except Exception as e:
            self.logger.error(f"Error generating dashboard reasoning: {e}")
            return {
                'ai_reasoning': "AI analysis completed using advanced reasoning algorithms to determine the most appropriate SIC code.",
                'ch_comparison': "Companies House data comparison performed to validate prediction accuracy."
            }
    
    def _generate_compact_ai_reasoning(self, company_name: str, predicted_sic: str, 
                                     confidence: float, method: str, ai_prediction: Dict) -> str:
        """Generate 2-3 sentence AI reasoning explanation"""
        
        # Get SIC code description if available
        sic_description = ai_prediction.get('sic_description', '')
        alternatives = ai_prediction.get('alternatives', [])
        
        # Build reasoning sentences
        sentences = []
        
        # Sentence 1: Main prediction reasoning
        if sic_description:
            sentences.append(f"AI analysis determined SIC code {predicted_sic} ({sic_description}) is the best match for {company_name}'s business activities.")
        else:
            sentences.append(f"AI analysis determined SIC code {predicted_sic} as the most appropriate classification for {company_name}.")
        
        # Sentence 2: Confidence and methodology with real-time explanation
        confidence_desc, confidence_explanation = self._get_confidence_description_with_explanation(confidence, method)
        method_description = self._get_method_description(method)
        sentences.append(f"This prediction has {confidence_desc} confidence ({confidence:.1%}) {method_description}. {confidence_explanation}")
        
        # Sentence 3: Alternatives consideration (if available and confidence not very high)
        if alternatives and confidence < 0.9 and len(alternatives) > 0:
            alt_codes = [alt.get('sic_code', '') for alt in alternatives[:2]]
            alt_codes_str = ', '.join(filter(None, alt_codes))
            if alt_codes_str:
                sentences.append(f"Alternative codes {alt_codes_str} were considered but ranked lower in relevance.")
        elif confidence >= 0.9:
            sentences.append(f"The high confidence score indicates strong alignment with standard industry classifications.")
        
        return ' '.join(sentences)

    def _get_confidence_description_with_explanation(self, confidence: float, method: str) -> tuple[str, str]:
        """Get confidence description and real-time explanation based on actual confidence score"""
        if confidence >= 0.8:
            desc = "high"
            explanation = f"The {confidence*100:.1f}% confidence reflects strong algorithmic certainty in the SIC classification."
        elif confidence >= 0.6:
            desc = "moderate"  
            explanation = f"The {confidence*100:.1f}% confidence indicates good algorithmic matching with acceptable uncertainty margins."
        elif confidence >= 0.4:
            desc = "moderate"
            explanation = f"The {confidence*100:.1f}% confidence suggests reasonable algorithmic fit despite some classification ambiguity."
        elif confidence >= 0.25:
            desc = "acceptable"
            explanation = f"The {confidence*100:.1f}% confidence reflects limited input data but follows standard classification principles."
        elif confidence > 0:
            desc = "low"
            explanation = f"The {confidence*100:.1f}% confidence indicates minimal algorithmic certainty due to insufficient classification data."
        else:
            desc = "unavailable"
            explanation = "No confidence score available - classification assigned using default business category."
            
        # Add method-specific technical context without generic fallback text
        if method == 'enhanced_sic_matching':
            explanation += " Based on enhanced pattern recognition algorithm."
        elif method == 'existing_sic_validation':
            explanation += " Validated against existing business registration data."
        # Remove generic fallback text for intelligent_fallback - let the confidence explanation stand alone
            
        return desc, explanation

    def _get_method_description(self, method: str) -> str:
        """Get dynamic method description based on actual prediction method"""
        method_descriptions = {
            'enhanced_sic_matching': 'using advanced pattern recognition analysis',
            'enhanced_fuzzy': 'using advanced fuzzy matching with semantic understanding',
            'existing_sic_validation': 'through existing business registration validation',
            'intelligent_fallback': 'using comprehensive business analysis',
            'vector_similarity': 'through semantic similarity matching',
            'business_description_analysis': 'via business description classification',
            'default': 'through standard classification methodology'
        }
        return method_descriptions.get(method, method_descriptions['default'])
    
    def generate_dashboard_reasoning(self, state: AgenticWorkflowState) -> Dict[str, str]:
        """Generate dashboard-specific reasoning for API response"""
        try:
            ai_prediction = state.get('ai_prediction', {})
            ch_sic_data = state.get('ch_sic_data', {})
            evaluation_result = state.get('evaluation_result', {})
            company_data = state.get('company_data', {})
            
            # Generate AI reasoning explanation (2-3 sentences)
            ai_reasoning = self._generate_compact_ai_reasoning_simple(ai_prediction, company_data)
            
            # Generate CH comparison explanation (1-2 sentences)
            predicted_sic = ai_prediction.get('predicted_sic_code', '') if ai_prediction else ''
            company_name = company_data.get('company_name', 'Unknown') if company_data else 'Unknown'
            ch_comparison = self._generate_ch_comparison_reasoning(
                predicted_sic, ch_sic_data, evaluation_result, company_name
            )
            
            return {
                'ai_reasoning': ai_reasoning,
                'ch_comparison': ch_comparison
            }
        except Exception as e:
            self.logger.error(f"Error generating dashboard reasoning: {e}")
            return {
                'ai_reasoning': 'AI reasoning unavailable due to processing error.',
                'ch_comparison': 'Companies House comparison unavailable due to processing error.'
            }

    def _generate_ch_comparison_reasoning(self, predicted_sic: str, ch_sic_data: Dict, 
                                        evaluation_result: Dict, company_name: str) -> str:
        """Generate Companies House SIC comparison reasoning"""
        
        if not ch_sic_data or not ch_sic_data.get('success', False):
            return f"Companies House SIC data not available for {company_name}, unable to perform validation comparison."
        
        ch_sic_codes = ch_sic_data.get('sic_codes', [])
        ch_confidence = ch_sic_data.get('confidence', 0.0)
        agreement = evaluation_result.get('ch_vs_ai_agreement', False)
        
        if not ch_sic_codes:
            return f"No SIC codes found in Companies House records for {company_name}."
        
        # Check if our prediction matches any CH SIC codes
        matches = [code for code in ch_sic_codes if code == predicted_sic]
        
        if matches:
            # Perfect match
            return f"✅ Excellent validation: Predicted SIC {predicted_sic} exactly matches Companies House registered code, confirming high accuracy of AI prediction."
        
        elif agreement:
            # Evaluation says there's agreement (maybe similar/related codes)
            primary_ch_sic = ch_sic_codes[0] if ch_sic_codes else ''
            return f"✅ Good validation: Predicted SIC {predicted_sic} aligns well with Companies House primary code {primary_ch_sic}, indicating consistent business classification."
        
        else:
            # No match - explain why
            primary_ch_sic = ch_sic_codes[0] if ch_sic_codes else ''
            if len(ch_sic_codes) == 1:
                return f"⚠️ Classification difference: Predicted SIC {predicted_sic} differs from Companies House code {primary_ch_sic}. This may indicate business evolution or more specific AI categorization."
            else:
                ch_codes_str = ', '.join(ch_sic_codes[:3])
                return f"⚠️ Classification difference: Predicted SIC {predicted_sic} differs from Companies House codes ({ch_codes_str}). This suggests either business diversification or more precise AI analysis of current activities."
    
    def _generate_compact_ai_reasoning_simple(self, ai_prediction: Dict, company_data: Dict) -> str:
        """Generate natural AI reasoning explanation using enhanced SIC matcher"""
        try:
            # Extract data for natural reasoning generation
            predicted_sic = ai_prediction.get('predicted_sic_code', '') if ai_prediction else ''
            confidence = ai_prediction.get('confidence_score', 0.0) if ai_prediction else 0.0
            predicted_sic_description = ai_prediction.get('predicted_sic_description', '') if ai_prediction else ''
            company_name = company_data.get('company_name', 'Company') if company_data else 'Company'
            business_description = company_data.get('business_description', '') if company_data else ''
            current_sic = company_data.get('existing_sic_code') or company_data.get('current_sic') if company_data else None
            existing_sic_confidence = company_data.get('existing_sic_confidence') if company_data else None
            
            # Try to use enhanced SIC matcher's natural AI reasoning generation
            from app_modules.utils.enhanced_sic_matcher import get_enhanced_sic_matcher
            
            enhanced_sic_matcher = get_enhanced_sic_matcher()
            
            # Get SIC description if not available
            if not predicted_sic_description:
                sic_descriptions = getattr(enhanced_sic_matcher, 'sic_descriptions', {})
                predicted_sic_description = sic_descriptions.get(predicted_sic, f'Classification code {predicted_sic}')
            
            # Generate natural AI reasoning
            ai_reasoning = enhanced_sic_matcher.generate_ai_reasoning(
                business_description=business_description,
                predicted_sic_code=predicted_sic,
                predicted_sic_description=predicted_sic_description,
                confidence_score=confidence,
                company_name=company_name,
                current_sic=current_sic,
                existing_sic_confidence=existing_sic_confidence
            )
            
            self.logger.info(f"✅ Generated natural AI reasoning in reasoning generator: {ai_reasoning[:100]}...")
            
            # Truncate if too long for dashboard display (keep first 2-3 sentences)
            sentences = ai_reasoning.split('. ')
            if len(sentences) > 3:
                ai_reasoning = '. '.join(sentences[:3]) + '.'
            
            return ai_reasoning
            
        except Exception as e:
            self.logger.error(f"Error generating natural AI reasoning: {e}")
            # Fallback to simple template if AI reasoning fails
            predicted_sic = ai_prediction.get('predicted_sic_code', '') if ai_prediction else ''
            confidence = ai_prediction.get('confidence_score', 0.0) if ai_prediction else 0.0
            company_name = company_data.get('company_name', 'Company') if company_data else 'Company'
            confidence_desc = "high confidence" if confidence >= 0.8 else "moderate confidence" if confidence >= 0.6 else "reasonable confidence"
            return f"AI analysis determined SIC {predicted_sic} as the most appropriate classification for {company_name} with {confidence_desc} ({confidence*100:.1f}% accuracy)."