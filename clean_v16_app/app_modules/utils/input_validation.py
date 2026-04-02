"""
Input validation utilities for API endpoints.
Provides type checking and sanitization for user inputs.
"""

from typing import Any, Dict, List, Optional, Union, Tuple
import logging

# Use direct logging to avoid circular imports
logger = logging.getLogger(__name__)

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
    def validate_company_id(value: Any) -> int:
        """
        Validate company_id parameter.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated integer company_id
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError("Company ID is required")
        
        # Handle string representations of numbers
        if isinstance(value, str):
            value = value.strip()
            if not value.isdigit():
                raise ValidationError("Company ID must be a valid integer")
            value = int(value)
        
        # Type checking
        if not isinstance(value, int):
            raise ValidationError(f"Company ID must be integer, got {type(value).__name__}")
        
        # Range validation
        if value <= 0:
            raise ValidationError("Company ID must be positive")
        
        if value > 100000:  # Reasonable upper limit for company IDs
            raise ValidationError("Company ID too large (max 100000)")
        
        return value
    
    @staticmethod
    def validate_company_name(value: Any) -> str:
        """
        Validate company name parameter.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated string name
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError("Company name is required")
        
        # Convert to string and strip whitespace
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        
        # Check for empty string
        if not value:
            raise ValidationError("Company name cannot be empty")
        
        # Check length limits
        if len(value) < 2:
            raise ValidationError("Company name too short (minimum 2 characters)")
        
        if len(value) > 200:  # Reasonable upper limit
            raise ValidationError("Company name too long (maximum 200 characters)")
        
        return value
    
    @staticmethod
    def validate_unique_id(value: Any) -> str:
        """
        Validate unique_id parameter.
        
        Args:
            value: Input value to validate
            
        Returns:
            Validated string unique_id
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError("Unique ID is required")
        
        # Convert to string and strip whitespace
        if not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        
        # Check for empty string
        if not value:
            raise ValidationError("Unique ID cannot be empty")
        
        # Check format: should be 10 characters (2 letters + 8 digits)
        import re
        if not re.match(r'^[A-Z]{2}\d{8}$', value):
            raise ValidationError("Unique ID must be in format: 2 uppercase letters + 8 digits (e.g., AB12345678)")
        
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
    """
    Validate input for predict_sic endpoint using hybrid approach:
    - unique_id is required (primary identifier)
    - company_name is optional but validated if provided (for safety/confirmation)
    """
    validator = InputValidator()
    
    # Validate required JSON structure - Only unique_id is required now
    validated = validator.validate_json_payload(data, ['unique_id'])
    
    # Validate unique_id specifically (required)
    validated['unique_id'] = validator.validate_unique_id(data['unique_id'])
    
    # Validate company_name if provided (optional but validated for consistency)
    if 'company_name' in data and data['company_name']:
        validated['company_name'] = validator.validate_company_name(data['company_name'])
    
    # Optional fields
    if 'registration_number' in data:
        validated['registration_number'] = str(data['registration_number']).strip()
    
    if 'sic_code' in data:
        validated['sic_code'] = str(data['sic_code']).strip()
    
    return validated


def validate_predict_sic_company_id_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate input for predict_sic endpoint using company_id approach (CORRECT APPROACH):
    - company_id is required (integer database primary key)
    - company_name is optional but validated if provided (for safety/confirmation)
    """
    validator = InputValidator()
    
    # Validate required JSON structure - company_id is required
    validated = validator.validate_json_payload(data, ['company_id'])
    
    # Validate company_id (integer primary key from database)
    validated['company_id'] = validator.validate_company_id(data['company_id'])
    
    # Validate company_name if provided (optional but validated for consistency)
    if 'company_name' in data and data['company_name']:
        validated['company_name'] = validator.validate_company_name(data['company_name'])
    
    # Optional fields
    if 'registration_number' in data:
        validated['registration_number'] = str(data['registration_number']).strip()
    
    if 'sic_code' in data:
        validated['sic_code'] = str(data['sic_code']).strip()
    
    return validated


def validate_predict_sic_robust_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ROBUST validation for predict_sic endpoint - accepts BOTH company_id and unique_id:
    - Tries company_id first (integer), then unique_id (string)
    - Returns standardized format with both identifiers when available
    - Ensures exact company lookup using both business identifiers
    """
    validator = InputValidator()
    
    # Check what identifier we have
    has_company_id = 'company_id' in data and data['company_id'] is not None
    has_unique_id = 'unique_id' in data and data['unique_id'] is not None
    
    if not has_company_id and not has_unique_id:
        raise ValidationError("Either 'company_id' or 'unique_id' is required")
    
    validated = {}
    
    # Validate company_id if provided
    if has_company_id:
        validated['company_id'] = validator.validate_company_id(data['company_id'])
    
    # Validate unique_id if provided  
    if has_unique_id:
        validated['unique_id'] = validator.validate_unique_id(data['unique_id'])
    
    # Validate company_name if provided (optional but validated for consistency)
    if 'company_name' in data and data['company_name']:
        validated['company_name'] = validator.validate_company_name(data['company_name'])
    
    # Optional fields
    if 'registration_number' in data:
        validated['registration_number'] = str(data['registration_number']).strip()
    
    if 'sic_code' in data:
        validated['sic_code'] = str(data['sic_code']).strip()
    
    return validated


def validate_update_revenue_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for update_revenue endpoint - supports company_name and company_number from frontend."""
    validator = InputValidator()
    
    # Validate required JSON structure - matches frontend parameters
    validated = validator.validate_json_payload(data, ['company_name', 'revenue'])
    
    # Validate specific fields
    validated['company_name'] = validator.validate_company_name(data['company_name'])
    validated['revenue'] = validator.validate_revenue(data['revenue'])
    
    # Company number is optional
    if 'company_number' in data and data['company_number']:
        validated['company_number'] = validator.validate_string_input(data['company_number'], 'company_number', max_length=50, required=False)
    
    return validated


def validate_approve_sic_prediction_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate input for approve SIC prediction endpoint.
    Supports both unique_id and company_id with comprehensive validation.
    """
    validator = InputValidator()
    
    # Check what identifier we have
    has_company_id = 'company_id' in data and data['company_id'] is not None
    has_unique_id = 'unique_id' in data and data['unique_id'] is not None
    
    if not has_company_id and not has_unique_id:
        raise ValidationError("Either 'company_id' or 'unique_id' is required")
    
    validated = {}
    
    # Validate company_id if provided
    if has_company_id:
        validated['company_id'] = validator.validate_company_id(data['company_id'])
    
    # Validate unique_id if provided  
    if has_unique_id:
        validated['unique_id'] = validator.validate_unique_id(data['unique_id'])
    
    # Validate predicted_sic (required)
    if 'predicted_sic' not in data or not data['predicted_sic']:
        raise ValidationError("predicted_sic is required")
    
    predicted_sic = str(data['predicted_sic']).strip()
    if not predicted_sic.isdigit() or len(predicted_sic) < 4 or len(predicted_sic) > 7:
        raise ValidationError("predicted_sic must be a 4-7 digit SIC code")
    validated['predicted_sic'] = predicted_sic
    
    # Validate confidence (required)
    if 'confidence' not in data:
        raise ValidationError("confidence is required")
    
    try:
        confidence = float(data['confidence'])
        if confidence < 0 or confidence > 100:
            raise ValidationError("confidence must be between 0 and 100")
        validated['confidence'] = confidence
    except (ValueError, TypeError):
        raise ValidationError("confidence must be a valid number")
    
    # Optional fields
    if 'workflow_type' in data and data['workflow_type']:
        workflow_type = str(data['workflow_type']).strip()
        if len(workflow_type) > 50:
            raise ValidationError("workflow_type too long (maximum 50 characters)")
        validated['workflow_type'] = workflow_type
    
    if 'company_name' in data and data['company_name']:
        validated['company_name'] = validator.validate_company_name(data['company_name'])
    
    # Optional Companies House SIC fields
    if 'ch_sic_codes' in data and data['ch_sic_codes']:
        if isinstance(data['ch_sic_codes'], list):
            validated['ch_sic_codes'] = data['ch_sic_codes']
        else:
            validated['ch_sic_codes'] = str(data['ch_sic_codes']).split(',')
    
    if 'ch_sic_description' in data and data['ch_sic_description']:
        validated['ch_sic_description'] = str(data['ch_sic_description']).strip()
    
    return validated


def validate_toggle_demo_mode_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for toggle demo mode endpoint."""
    if not isinstance(data, dict):
        raise ValidationError("Request body must be valid JSON")
    
    if 'demo_mode' not in data:
        raise ValidationError("demo_mode parameter is required")
    
    demo_mode = data['demo_mode']
    if not isinstance(demo_mode, bool):
        raise ValidationError("demo_mode must be a boolean value")
    
    return {'demo_mode': demo_mode}


def validate_update_sic_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for update SIC endpoint."""
    validator = InputValidator()
    
    # Validate required fields
    if 'company_index' not in data:
        raise ValidationError("company_index is required")
    
    if 'new_sic' not in data:
        raise ValidationError("new_sic is required")
    
    validated = {}
    
    # Validate company_index
    validated['company_index'] = validator.validate_company_index(data['company_index'])
    
    # Validate new_sic
    new_sic = str(data['new_sic']).strip()
    if not new_sic.isdigit() or len(new_sic) != 5:
        raise ValidationError("new_sic must be a 5-digit SIC code")
    validated['new_sic'] = new_sic
    
    # Optional confidence field
    if 'confidence' in data and data['confidence'] is not None:
        try:
            confidence = float(data['confidence'])
            if confidence < 0 or confidence > 100:
                raise ValidationError("confidence must be between 0 and 100")
            validated['confidence'] = confidence
        except (ValueError, TypeError):
            raise ValidationError("confidence must be a valid number")
    
    return validated


def validate_add_company_with_sic_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for add company with SIC endpoint."""
    validator = InputValidator()
    
    # Required fields
    required_fields = ['company_name', 'business_description', 'existing_sic_code']
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValidationError(f"{field} is required")
    
    validated = {}
    
    # Validate company_name
    validated['company_name'] = validator.validate_company_name(data['company_name'])
    
    # Validate business_description
    business_desc = validator.validate_string_input(
        data['business_description'], 
        'business_description', 
        max_length=2000, 
        required=True
    )
    validated['business_description'] = business_desc
    
    # Validate existing_sic_code
    existing_sic = str(data['existing_sic_code']).strip()
    if not existing_sic.isdigit() or len(existing_sic) != 5:
        raise ValidationError("existing_sic_code must be a 5-digit SIC code")
    validated['existing_sic_code'] = existing_sic
    
    # Optional existing_sic_description
    if 'existing_sic_description' in data and data['existing_sic_description']:
        validated['existing_sic_description'] = validator.validate_string_input(
            data['existing_sic_description'],
            'existing_sic_description',
            max_length=500,
            required=False
        )
    
    # Optional company_number
    if 'company_number' in data and data['company_number']:
        company_number = str(data['company_number']).strip()
        if len(company_number) > 20:
            raise ValidationError("company_number too long (maximum 20 characters)")
        validated['company_number'] = company_number
    
    return validated


def validate_update_main_table_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for update main table endpoint."""
    validator = InputValidator()
    
    # Required fields
    required_fields = ['company_index', 'old_sic', 'new_sic', 'company_name']
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"{field} is required")
    
    validated = {}
    
    # Validate company_index
    validated['company_index'] = validator.validate_company_index(data['company_index'])
    
    # Validate company_name
    validated['company_name'] = validator.validate_company_name(data['company_name'])
    
    # Validate old_sic
    old_sic = str(data['old_sic']).strip()
    if old_sic and (not old_sic.isdigit() or len(old_sic) != 5):
        raise ValidationError("old_sic must be a 5-digit SIC code or empty")
    validated['old_sic'] = old_sic
    
    # Validate new_sic
    new_sic = str(data['new_sic']).strip()
    if not new_sic.isdigit() or len(new_sic) != 5:
        raise ValidationError("new_sic must be a 5-digit SIC code")
    validated['new_sic'] = new_sic
    
    # Optional new_accuracy
    if 'new_accuracy' in data and data['new_accuracy'] is not None:
        try:
            new_accuracy = float(data['new_accuracy'])
            if new_accuracy < 0 or new_accuracy > 100:
                raise ValidationError("new_accuracy must be between 0 and 100")
            validated['new_accuracy'] = new_accuracy
        except (ValueError, TypeError):
            raise ValidationError("new_accuracy must be a valid number")
    
    return validated


def validate_run_agent_workflow_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input for run agent workflow endpoint."""
    validator = InputValidator()
    
    # workflow_input is required
    if 'workflow_input' not in data:
        raise ValidationError("workflow_input is required")
    
    workflow_input = data['workflow_input']
    if not isinstance(workflow_input, dict):
        raise ValidationError("workflow_input must be a dictionary")
    
    validated = {'workflow_input': workflow_input}
    
    # Optional workflow_type
    if 'workflow_type' in data and data['workflow_type']:
        workflow_type = validator.validate_string_input(
            data['workflow_type'],
            'workflow_type',
            max_length=50,
            required=False
        )
        validated['workflow_type'] = workflow_type  # type: ignore
    
    return validated