"""
Example SIC Classification Service Implementation

This demonstrates how to implement a concrete service using the platform
service base classes with proper user access control and service isolation.
"""

from typing import Dict, Any, List, Set
import logging
from functools import lru_cache

from app.platform import (
    BaseService, ServiceMetadata, ServiceEndpoint, ServiceStatus,
    SubscriptionTier
)


class SICClassificationService(BaseService):
    """
    SIC Classification Service - AI-powered SIC code prediction
    
    This service provides SIC (Standard Industrial Classification) code
    prediction using advanced fuzzy matching and machine learning.
    
    Features:
    - Fuzzy matching with 751+ SIC codes
    - Machine learning-based predictions
    - User feedback integration
    - Batch processing capabilities
    - Accuracy tracking and analytics
    """
    
    def __init__(self):
        super().__init__()
        self._sic_matcher = None  # Lazy loaded
        self._user_contexts = {}  # Per-user prediction contexts
    
    @property
    def metadata(self) -> ServiceMetadata:
        """Service metadata and configuration"""
        return ServiceMetadata(
            name='sic-classification',
            display_name='SIC Classification Service',
            description='AI-powered SIC code prediction with fuzzy matching and ML',
            version='2.1.0',
            status=ServiceStatus.AVAILABLE,
            endpoints=[
                ServiceEndpoint(
                    path='/predict',
                    method='POST',
                    description='Predict SIC code from business description',
                    required_permissions=['predict_sic'],
                    rate_limit=100  # 100 predictions per minute
                ),
                ServiceEndpoint(
                    path='/update',
                    method='POST', 
                    description='Update SIC prediction with user feedback',
                    required_permissions=['update_sic'],
                    rate_limit=50
                ),
                ServiceEndpoint(
                    path='/batch-predict',
                    method='POST',
                    description='Batch SIC code predictions for multiple companies',
                    required_permissions=['batch_predict'],
                    rate_limit=10  # Limited for intensive operations
                ),
                ServiceEndpoint(
                    path='/accuracy-stats',
                    method='GET',
                    description='Get prediction accuracy statistics',
                    required_permissions=['view_analytics'],
                    rate_limit=20
                ),
                ServiceEndpoint(
                    path='/user-predictions',
                    method='GET',
                    description='Get user prediction history',
                    required_permissions=['view_history'],
                    rate_limit=30
                )
            ],
            required_permissions={
                'predict_sic', 'update_sic', 'batch_predict', 
                'view_analytics', 'view_history'
            },
            pricing_model='per_prediction',
            documentation_url='/docs/services/sic-classification'
        )
    
    def initialize_for_user(self, user_id: str) -> bool:
        """Initialize SIC service for a specific user"""
        try:
            # Lazy load SIC matcher if not already loaded
            if not self._sic_matcher:
                self._load_sic_matcher()
            
            # Create user context for tracking predictions
            self._user_contexts[user_id] = {
                'predictions_count': 0,
                'accuracy_feedback': [],
                'last_prediction_time': None,
                'preferences': {
                    'confidence_threshold': 0.7,
                    'max_suggestions': 5
                }
            }
            
            # Mark user as initialized
            self._initialized_users.add(user_id)
            
            self._logger.info(f"Initialized SIC service for user {user_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize SIC service for user {user_id}: {e}")
            return False
    
    def handle_request(self, endpoint: str, method: str, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming SIC service requests"""
        try:
            # Route to appropriate handler
            if endpoint == '/predict' and method == 'POST':
                return self._handle_predict_sic(user_id, request_data)
            elif endpoint == '/update' and method == 'POST':
                return self._handle_update_sic(user_id, request_data)
            elif endpoint == '/batch-predict' and method == 'POST':
                return self._handle_batch_predict(user_id, request_data)
            elif endpoint == '/accuracy-stats' and method == 'GET':
                return self._handle_accuracy_stats(user_id, request_data)
            elif endpoint == '/user-predictions' and method == 'GET':
                return self._handle_user_predictions(user_id, request_data)
            else:
                return {'error': f'Endpoint {method} {endpoint} not found', 'status': 404}
                
        except Exception as e:
            self._logger.error(f"Request handling failed: {e}")
            return {'error': 'Internal service error', 'status': 500}
    
    def cleanup_user(self, user_id: str) -> bool:
        """Cleanup SIC service resources for user"""
        try:
            # Remove user context
            if user_id in self._user_contexts:
                del self._user_contexts[user_id]
            
            # Call parent cleanup
            return super().cleanup_user(user_id)
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup SIC service for user {user_id}: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get SIC service health status"""
        base_status = super().get_health_status()
        
        # Add service-specific health info
        base_status.update({
            'sic_matcher_loaded': self._sic_matcher is not None,
            'active_user_contexts': len(self._user_contexts),
            'total_predictions_served': sum(
                ctx['predictions_count'] for ctx in self._user_contexts.values()
            )
        })
        
        return base_status
    
    # Private implementation methods
    
    def _load_sic_matcher(self):
        """Lazy load SIC matcher"""
        try:
            from app.utils.enhanced_sic_matcher import get_enhanced_sic_matcher
            self._sic_matcher = get_enhanced_sic_matcher()
            self._logger.info("SIC matcher loaded successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to load SIC matcher: {e}")
            raise
    
    def _handle_predict_sic(self, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SIC prediction request"""
        try:
            # Validate input
            business_description = request_data.get('business_description', '').strip()
            if not business_description:
                return {'error': 'business_description is required', 'status': 400}
            
            # Get user preferences
            user_context = self._user_contexts.get(user_id, {})
            preferences = user_context.get('preferences', {})
            
            # Make prediction
            prediction_result = self._sic_matcher.predict_sic_code(
                business_description,
                confidence_threshold=preferences.get('confidence_threshold', 0.7),
                max_suggestions=preferences.get('max_suggestions', 5)
            )
            
            # Update user context
            if user_id in self._user_contexts:
                self._user_contexts[user_id]['predictions_count'] += 1
                self._user_contexts[user_id]['last_prediction_time'] = self._get_current_time()
            
            # Format response
            return {
                'status': 'success',
                'prediction': {
                    'sic_code': prediction_result.get('sic_code'),
                    'sic_description': prediction_result.get('sic_description'),
                    'confidence': prediction_result.get('confidence', 0.0),
                    'match_type': prediction_result.get('match_type', 'fuzzy'),
                    'suggestions': prediction_result.get('alternatives', [])
                },
                'metadata': {
                    'user_id': user_id,
                    'prediction_id': self._generate_prediction_id(),
                    'timestamp': self._get_current_time(),
                    'service_version': self.metadata.version
                }
            }
            
        except Exception as e:
            self._logger.error(f"SIC prediction failed for user {user_id}: {e}")
            return {'error': 'Prediction failed', 'status': 500}
    
    def _handle_update_sic(self, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SIC update/feedback request"""
        try:
            # Validate input
            prediction_id = request_data.get('prediction_id')
            correct_sic = request_data.get('correct_sic_code')
            feedback_type = request_data.get('feedback_type', 'correction')
            
            if not prediction_id or not correct_sic:
                return {'error': 'prediction_id and correct_sic_code are required', 'status': 400}
            
            # Process feedback
            feedback_result = self._sic_matcher.update_prediction(
                prediction_id=prediction_id,
                correct_sic=correct_sic,
                feedback_type=feedback_type,
                user_id=user_id
            )
            
            # Update user context with feedback
            if user_id in self._user_contexts:
                self._user_contexts[user_id]['accuracy_feedback'].append({
                    'prediction_id': prediction_id,
                    'feedback_type': feedback_type,
                    'timestamp': self._get_current_time()
                })
            
            return {
                'status': 'success',
                'message': 'Feedback processed successfully',
                'updated': feedback_result.get('updated', False),
                'metadata': {
                    'user_id': user_id,
                    'prediction_id': prediction_id,
                    'timestamp': self._get_current_time()
                }
            }
            
        except Exception as e:
            self._logger.error(f"SIC update failed for user {user_id}: {e}")
            return {'error': 'Update failed', 'status': 500}
    
    def _handle_batch_predict(self, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch SIC prediction request"""
        try:
            # Validate input
            companies = request_data.get('companies', [])
            if not companies or len(companies) > 100:  # Limit batch size
                return {'error': 'companies list required (max 100 items)', 'status': 400}
            
            batch_results = []
            
            for i, company_data in enumerate(companies):
                business_description = company_data.get('business_description', '').strip()
                if not business_description:
                    batch_results.append({
                        'index': i,
                        'error': 'business_description required'
                    })
                    continue
                
                try:
                    prediction = self._sic_matcher.predict_sic_code(business_description)
                    batch_results.append({
                        'index': i,
                        'company_id': company_data.get('company_id'),
                        'prediction': {
                            'sic_code': prediction.get('sic_code'),
                            'confidence': prediction.get('confidence', 0.0),
                            'sic_description': prediction.get('sic_description')
                        }
                    })
                except Exception as e:
                    batch_results.append({
                        'index': i,
                        'error': f'Prediction failed: {str(e)}'
                    })
            
            # Update user context
            if user_id in self._user_contexts:
                self._user_contexts[user_id]['predictions_count'] += len([
                    r for r in batch_results if 'prediction' in r
                ])
            
            return {
                'status': 'success',
                'batch_size': len(companies),
                'successful_predictions': len([r for r in batch_results if 'prediction' in r]),
                'failed_predictions': len([r for r in batch_results if 'error' in r]),
                'results': batch_results,
                'metadata': {
                    'user_id': user_id,
                    'batch_id': self._generate_prediction_id(),
                    'timestamp': self._get_current_time()
                }
            }
            
        except Exception as e:
            self._logger.error(f"Batch prediction failed for user {user_id}: {e}")
            return {'error': 'Batch prediction failed', 'status': 500}
    
    def _handle_accuracy_stats(self, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle accuracy statistics request"""
        try:
            # Get global accuracy stats
            global_stats = self._sic_matcher.get_accuracy_stats() if self._sic_matcher else {}
            
            # Get user-specific stats
            user_context = self._user_contexts.get(user_id, {})
            user_stats = {
                'predictions_made': user_context.get('predictions_count', 0),
                'feedback_provided': len(user_context.get('accuracy_feedback', [])),
                'last_prediction': user_context.get('last_prediction_time')
            }
            
            return {
                'status': 'success',
                'global_accuracy': global_stats,
                'user_statistics': user_stats,
                'metadata': {
                    'user_id': user_id,
                    'timestamp': self._get_current_time(),
                    'service_version': self.metadata.version
                }
            }
            
        except Exception as e:
            self._logger.error(f"Accuracy stats failed for user {user_id}: {e}")
            return {'error': 'Failed to retrieve statistics', 'status': 500}
    
    def _handle_user_predictions(self, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user prediction history request"""
        try:
            user_context = self._user_contexts.get(user_id, {})
            
            # In a real implementation, this would query a database
            # For now, return basic context info
            history = {
                'total_predictions': user_context.get('predictions_count', 0),
                'feedback_history': user_context.get('accuracy_feedback', [])[-10:],  # Last 10
                'user_preferences': user_context.get('preferences', {}),
                'last_activity': user_context.get('last_prediction_time')
            }
            
            return {
                'status': 'success',
                'prediction_history': history,
                'metadata': {
                    'user_id': user_id,
                    'timestamp': self._get_current_time()
                }
            }
            
        except Exception as e:
            self._logger.error(f"User predictions failed for user {user_id}: {e}")
            return {'error': 'Failed to retrieve prediction history', 'status': 500}
    
    # Utility methods
    
    def _generate_prediction_id(self) -> str:
        """Generate unique prediction ID"""
        import uuid
        return f"sic_pred_{uuid.uuid4().hex[:12]}"
    
    def _get_current_time(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# Service permission matrix for different subscription tiers
SIC_SERVICE_PERMISSIONS = {
    SubscriptionTier.BASIC: set(),  # No access to SIC service in basic
    SubscriptionTier.STANDARD: {'predict_sic'},  # Basic predictions only
    SubscriptionTier.PREMIUM: {
        'predict_sic', 'update_sic', 'batch_predict', 'view_history'
    },  # Full functionality except analytics
    SubscriptionTier.ENTERPRISE: {
        'predict_sic', 'update_sic', 'batch_predict', 
        'view_analytics', 'view_history'
    }  # All features including analytics
}


def create_sic_service() -> BaseService:
    """Factory function to create SIC Classification Service"""
    return SICClassificationService()