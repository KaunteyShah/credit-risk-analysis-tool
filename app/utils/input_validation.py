"""
Input validation utilities for API endpoints.
Provides type checking and sanitization for user inputs.
"""

from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class InputValidator:
    """Validates and sanitizes API inputs."""
    
    @staticmethod
    def validate_company_index(value: Any) -> int:
        """
        Validate company index parameter.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated integer index
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError("Company index is required")
        
        # Handle string representations of numbers
        if isinstance(value, str):
            if not value.strip().isdigit():
                raise ValidationError("Company index must be a valid integer")
            value = int(value.strip())
        
        # Type checking
        if not isinstance(value, int):
            raise ValidationError(f"Company index must be integer, got {type(value).__name__}")
        
        # Range validation
        if value < 0:
            raise ValidationError("Company index must be non-negative")
        
        if value > 10000:  # Reasonable upper limit
            raise ValidationError("Company index too large (max 10000)")
        
        return value
    
    @staticmethod
    def validate_revenue(value: Any) -> float:
        """
        Validate revenue/financial values.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated float value
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError("Revenue value is required")
        
        # Handle string representations
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValidationError("Revenue value cannot be empty")
            
            # Remove common currency symbols and commas
            value = value.replace('$', '').replace(',', '').replace('£', '').replace('€', '')
            
            try:
                value = float(value)
            except ValueError:
                raise ValidationError("Revenue must be a valid number")
        
        # Type checking
        if not isinstance(value, (int, float)):
            raise ValidationError(f"Revenue must be numeric, got {type(value).__name__}")
        
        # Convert to float
        value = float(value)
        
        # Range validation
        if value < 0:
            raise ValidationError("Revenue cannot be negative")
        
        if value > 1e12:  # 1 trillion max
            raise ValidationError("Revenue value too large")
        
        return value
    
    @staticmethod
    def validate_string_input(value: Any, field_name: str, max_length: int = 1000, required: bool = True) -> str:
        """
        Validate string inputs with length limits.
        
        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            max_length: Maximum allowed length
            required: Whether the field is required
            
        Returns:
            Validated string
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if required:
                raise ValidationError(f"{field_name} is required")
            return ""
        
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")
        
        # Basic sanitization
        value = value.strip()
        
        if required and not value:
            raise ValidationError(f"{field_name} cannot be empty")
        
        if len(value) > max_length:
            raise ValidationError(f"{field_name} too long (max {max_length} characters)")
        
        # Basic security: prevent potential injection attempts
        dangerous_patterns = ['<script', 'javascript:', 'eval(', 'function(']
        value_lower = value.lower()
        for pattern in dangerous_patterns:
            if pattern in value_lower:
                logger.warning(f"Potentially dangerous input detected in {field_name}: {pattern}")
                raise ValidationError(f"Invalid characters detected in {field_name}")
        
        return value
    
    @staticmethod
    def validate_json_payload(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        Validate JSON payload structure.
        
        Args:
            data: JSON data to validate
            required_fields: List of required field names
            
        Returns:
            Validated data dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON object")
        
        # Check for required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check for unexpected large payloads
        if len(str(data)) > 50000:  # 50KB limit
            raise ValidationError("Request payload too large")
        
        return data

def validate_api_input(validation_func):
    """
    Decorator to add input validation to Flask route handlers.
    
    Args:
        validation_func: Function that takes request data and returns validated data
        
    Returns:
        Decorated function
    """
    def decorator(route_func):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            try:
                # Get JSON data
                data = request.get_json(force=True)
                if data is None:
                    return jsonify({'error': 'Invalid JSON in request body'}), 400
                
                # Validate input
                validated_data = validation_func(data)
                
                # Call original function with validated data
                return route_func(validated_data, *args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"Input validation failed: {e}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                logger.error(f"Unexpected validation error: {e}")
                return jsonify({'error': 'Invalid request data'}), 400
        
        wrapper.__name__ = route_func.__name__
        return wrapper
    return decorator


# Specific validation functions for our API endpoints

def validate_predict_sic_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for predict_sic endpoint."""
    validator = InputValidator()
    
    # Validate required JSON structure
    validated = validator.validate_json_payload(data, ['company_index'])
    
    # Validate company_index specifically
    validated['company_index'] = validator.validate_company_index(data['company_index'])
    
    return validated


def validate_update_revenue_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for update_revenue endpoint."""
    validator = InputValidator()
    
    # Validate required JSON structure
    validated = validator.validate_json_payload(data, ['company_index', 'new_revenue'])
    
    # Validate specific fields
    validated['company_index'] = validator.validate_company_index(data['company_index'])
    validated['new_revenue'] = validator.validate_revenue(data['new_revenue'])
    
    return validated