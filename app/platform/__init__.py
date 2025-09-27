"""
Platform Service Base Classes and Interfaces

This module defines the core abstractions for the Credit Risk Platform
service-oriented architecture with user access control.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SubscriptionTier(Enum):
    """User subscription tiers with different service access levels"""
    BASIC = "basic"
    STANDARD = "standard" 
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class ServiceStatus(Enum):
    """Service operational status"""
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


@dataclass
class ServiceEndpoint:
    """Represents a service API endpoint"""
    path: str
    method: str
    description: str
    required_permissions: List[str]
    rate_limit: Optional[int] = None


@dataclass
class ServiceMetadata:
    """Service registration metadata"""
    name: str
    display_name: str
    description: str
    version: str
    status: ServiceStatus
    endpoints: List[ServiceEndpoint]
    required_permissions: Set[str]
    pricing_model: str
    documentation_url: Optional[str] = None


class BaseService(ABC):
    """
    Base class for all platform services
    
    Each service must implement this interface to be registerable
    with the platform service registry and accessible to users.
    """
    
    def __init__(self):
        self._initialized_users: Set[str] = set()
        self._logger = logging.getLogger(f"service.{self.metadata.name}")
    
    @property
    @abstractmethod
    def metadata(self) -> ServiceMetadata:
        """Service metadata including name, endpoints, permissions"""
        pass
    
    @abstractmethod
    def initialize_for_user(self, user_id: str) -> bool:
        """
        Initialize service for a specific user
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    def handle_request(self, endpoint: str, method: str, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming API request
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            user_id: User making the request
            request_data: Request payload and parameters
            
        Returns:
            Dict containing response data
        """
        pass
    
    def cleanup_user(self, user_id: str) -> bool:
        """
        Cleanup resources for a user (when they unsubscribe)
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if cleanup successful
        """
        if user_id in self._initialized_users:
            self._initialized_users.remove(user_id)
        return True
    
    def is_initialized_for_user(self, user_id: str) -> bool:
        """Check if service is initialized for user"""
        return user_id in self._initialized_users
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            'status': 'healthy',
            'initialized_users': len(self._initialized_users),
            'service': self.metadata.name,
            'version': self.metadata.version
        }


class ServiceRegistry:
    """
    Central registry for all platform services
    
    Manages service registration, discovery, and user access control.
    """
    
    def __init__(self):
        self._services: Dict[str, BaseService] = {}
        self._service_permissions: Dict[str, Dict[SubscriptionTier, Set[str]]] = {}
        self._logger = logging.getLogger("platform.service_registry")
    
    def register_service(self, service: BaseService, permission_matrix: Dict[SubscriptionTier, Set[str]]) -> bool:
        """
        Register a service with the platform
        
        Args:
            service: Service instance to register
            permission_matrix: Permissions by subscription tier
            
        Returns:
            bool: True if registration successful
        """
        try:
            service_name = service.metadata.name
            
            # Validate service
            if not self._validate_service(service):
                return False
            
            # Register service
            self._services[service_name] = service
            self._service_permissions[service_name] = permission_matrix
            
            self._logger.info(f"Registered service: {service_name} v{service.metadata.version}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register service {service.metadata.name}: {e}")
            return False
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get service by name"""
        return self._services.get(service_name)
    
    def get_user_accessible_services(self, user_id: str, subscription_tier: SubscriptionTier) -> List[ServiceMetadata]:
        """
        Get services accessible to user based on their subscription
        
        Args:
            user_id: User identifier
            subscription_tier: User's subscription level
            
        Returns:
            List of service metadata for accessible services
        """
        accessible_services = []
        
        for service_name, service in self._services.items():
            # Check if user has permissions for this service
            service_permissions = self._service_permissions.get(service_name, {})
            user_permissions = service_permissions.get(subscription_tier, set())
            
            # User needs at least one permission to access service
            if user_permissions and service.metadata.status == ServiceStatus.AVAILABLE:
                # Create filtered metadata with only accessible endpoints
                accessible_endpoints = [
                    endpoint for endpoint in service.metadata.endpoints
                    if any(perm in user_permissions for perm in endpoint.required_permissions)
                ]
                
                if accessible_endpoints:  # Only include if user can access some endpoints
                    accessible_metadata = ServiceMetadata(
                        name=service.metadata.name,
                        display_name=service.metadata.display_name,
                        description=service.metadata.description,
                        version=service.metadata.version,
                        status=service.metadata.status,
                        endpoints=accessible_endpoints,
                        required_permissions=user_permissions,
                        pricing_model=service.metadata.pricing_model,
                        documentation_url=service.metadata.documentation_url
                    )
                    accessible_services.append(accessible_metadata)
        
        return accessible_services
    
    def can_access_service(self, user_id: str, service_name: str, subscription_tier: SubscriptionTier) -> bool:
        """Check if user can access specific service"""
        if service_name not in self._services:
            return False
            
        service_permissions = self._service_permissions.get(service_name, {})
        user_permissions = service_permissions.get(subscription_tier, set())
        
        return len(user_permissions) > 0
    
    def can_access_endpoint(self, user_id: str, service_name: str, endpoint_path: str, 
                          subscription_tier: SubscriptionTier) -> bool:
        """Check if user can access specific endpoint"""
        if not self.can_access_service(user_id, service_name, subscription_tier):
            return False
            
        service = self._services.get(service_name)
        if not service:
            return False
            
        # Find endpoint
        endpoint = next((ep for ep in service.metadata.endpoints if ep.path == endpoint_path), None)
        if not endpoint:
            return False
            
        # Check permissions
        service_permissions = self._service_permissions.get(service_name, {})
        user_permissions = service_permissions.get(subscription_tier, set())
        
        return any(perm in user_permissions for perm in endpoint.required_permissions)
    
    def get_all_services(self) -> Dict[str, ServiceMetadata]:
        """Get metadata for all registered services"""
        return {name: service.metadata for name, service in self._services.items()}
    
    def _validate_service(self, service: BaseService) -> bool:
        """Validate service implementation"""
        try:
            # Check required attributes
            metadata = service.metadata
            if not metadata.name or not metadata.display_name:
                self._logger.error(f"Service missing name or display_name")
                return False
                
            # Check for duplicate registration
            if metadata.name in self._services:
                self._logger.error(f"Service {metadata.name} already registered")
                return False
                
            return True
            
        except Exception as e:
            self._logger.error(f"Service validation failed: {e}")
            return False


class UserAccessControl:
    """
    Manages user access control and permissions
    
    This class handles user subscriptions, permissions, and service access.
    """
    
    def __init__(self):
        # In production, this would connect to a database
        self._user_data: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger("platform.access_control")
    
    def set_user_subscription(self, user_id: str, subscription_tier: SubscriptionTier, 
                            permissions: Optional[Set[str]] = None) -> bool:
        """Set user subscription and permissions"""
        try:
            self._user_data[user_id] = {
                'subscription_tier': subscription_tier,
                'custom_permissions': permissions or set(),
                'rate_limits': self._get_default_rate_limits(subscription_tier),
                'active': True
            }
            self._logger.info(f"Set subscription for user {user_id}: {subscription_tier.value}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to set subscription for user {user_id}: {e}")
            return False
    
    def get_user_subscription(self, user_id: str) -> Optional[SubscriptionTier]:
        """Get user's subscription tier"""
        user_data = self._user_data.get(user_id)
        return user_data['subscription_tier'] if user_data and user_data.get('active') else None
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get user's custom permissions"""
        user_data = self._user_data.get(user_id)
        return user_data.get('custom_permissions', set()) if user_data else set()
    
    def is_user_active(self, user_id: str) -> bool:
        """Check if user account is active"""
        user_data = self._user_data.get(user_id)
        return user_data.get('active', False) if user_data else False
    
    def get_user_rate_limits(self, user_id: str) -> Dict[str, int]:
        """Get user's rate limits"""
        user_data = self._user_data.get(user_id)
        return user_data.get('rate_limits', {}) if user_data else {}
    
    def _get_default_rate_limits(self, subscription_tier: SubscriptionTier) -> Dict[str, int]:
        """Get default rate limits for subscription tier"""
        limits = {
            SubscriptionTier.BASIC: {'requests_per_minute': 60, 'requests_per_day': 1000},
            SubscriptionTier.STANDARD: {'requests_per_minute': 300, 'requests_per_day': 10000},
            SubscriptionTier.PREMIUM: {'requests_per_minute': 1000, 'requests_per_day': 50000},
            SubscriptionTier.ENTERPRISE: {'requests_per_minute': 5000, 'requests_per_day': 500000}
        }
        return limits.get(subscription_tier, limits[SubscriptionTier.BASIC])


class ServiceAPIGateway:
    """
    API Gateway that routes requests to appropriate services
    
    Handles authentication, authorization, rate limiting, and request routing.
    """
    
    def __init__(self, service_registry: ServiceRegistry, access_control: UserAccessControl):
        self.registry = service_registry
        self.access_control = access_control
        self._logger = logging.getLogger("platform.api_gateway")
    
    def route_request(self, user_id: str, service_name: str, endpoint: str, 
                     method: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route API request to appropriate service
        
        Args:
            user_id: User making the request
            service_name: Target service name
            endpoint: API endpoint path
            method: HTTP method
            request_data: Request payload
            
        Returns:
            Dict containing response data or error
        """
        try:
            # 1. Validate user
            if not self.access_control.is_user_active(user_id):
                return {'error': 'User account inactive', 'status': 401}
            
            subscription_tier = self.access_control.get_user_subscription(user_id)
            if not subscription_tier:
                return {'error': 'No valid subscription', 'status': 403}
            
            # 2. Check service access
            if not self.registry.can_access_service(user_id, service_name, subscription_tier):
                return {'error': f'Access denied to service {service_name}', 'status': 403}
            
            # 3. Check endpoint access  
            if not self.registry.can_access_endpoint(user_id, service_name, endpoint, subscription_tier):
                return {'error': f'Access denied to endpoint {endpoint}', 'status': 403}
            
            # 4. Get service
            service = self.registry.get_service(service_name)
            if not service:
                return {'error': f'Service {service_name} not found', 'status': 404}
            
            # 5. Initialize service for user if needed
            if not service.is_initialized_for_user(user_id):
                if not service.initialize_for_user(user_id):
                    return {'error': 'Failed to initialize service', 'status': 500}
            
            # 6. Route request to service
            response = service.handle_request(endpoint, method, user_id, request_data)
            
            # 7. Log successful request
            self._logger.info(f"Routed {method} {service_name}{endpoint} for user {user_id}")
            
            return response
            
        except Exception as e:
            self._logger.error(f"Request routing failed: {e}")
            return {'error': 'Internal server error', 'status': 500}
    
    def get_user_services(self, user_id: str) -> Dict[str, Any]:
        """Get services available to user"""
        try:
            subscription_tier = self.access_control.get_user_subscription(user_id)
            if not subscription_tier:
                return {'error': 'No valid subscription'}
            
            accessible_services = self.registry.get_user_accessible_services(user_id, subscription_tier)
            
            return {
                'user_id': user_id,
                'subscription_tier': subscription_tier.value,
                'services': [
                    {
                        'name': svc.name,
                        'display_name': svc.display_name,
                        'description': svc.description,
                        'version': svc.version,
                        'endpoints': [
                            {
                                'path': ep.path,
                                'method': ep.method,
                                'description': ep.description,
                                'rate_limit': ep.rate_limit
                            }
                            for ep in svc.endpoints
                        ],
                        'pricing_model': svc.pricing_model,
                        'documentation_url': svc.documentation_url
                    }
                    for svc in accessible_services
                ]
            }
            
        except Exception as e:
            self._logger.error(f"Failed to get user services: {e}")
            return {'error': 'Failed to retrieve services'}