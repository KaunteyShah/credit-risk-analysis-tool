"""
Container-Friendly Configuration Management for Credit Risk Analysis Application.

This module provides a hybrid configuration approach that works seamlessly with:
- Local development (using defaults and .env files)
- Docker containers (using environment variables) 
- Azure deployments (using Azure App Settings)
- Kubernetes (using ConfigMaps and Secrets)
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from app_modules.utils.centralized_logging import get_logger

logger = get_logger(__name__)


class CreditRiskConfig:
    """
    Container-friendly configuration management for Credit Risk Analysis.
    
    Supports configuration hierarchy:
    1. Environment variables (highest priority)
    2. Default values based on project structure
    3. Runtime detection of container environments
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize configuration with automatic environment detection.
        
        Args:
            project_root: Optional override for project root path
        """
        # Auto-detect project root or use provided
        self.project_root = project_root or self._find_project_root()
        
        # Environment detection
        self.environment = os.getenv('ENVIRONMENT', self._detect_environment())
        self.is_container = self._is_running_in_container()
        
        # Database configuration - set URL first before resolving path
        self.database_url = os.getenv('DATABASE_URL')  # For PostgreSQL/MySQL
        self.database_path = self._resolve_database_path()
        
        # Model configuration  
        self.model_version = os.getenv('SIC_MODEL_VERSION', '1.0')
        self.confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', '0.75'))
        
        # Database schema configuration (container-friendly)
        self.sic_table_name = os.getenv('SIC_TABLE_NAME', 'sic_codes')
        self.prediction_table_name = os.getenv('PREDICTION_TABLE_NAME', 'sic_prediction_history')
        
        # File paths (container-aware)
        self.data_directory = self._resolve_data_directory()
        self.updated_predictions_file = self._resolve_predictions_file()
        
        # Application settings
        self.flask_secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
        self.debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Azure-specific settings
        self.azure_storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.azure_key_vault_url = os.getenv('AZURE_KEY_VAULT_URL')
        
        # Log configuration summary
        self._log_configuration()
    
    def _find_project_root(self) -> Path:
        """
        Find project root directory by looking for characteristic files/folders.
        Works in local development, containers, and Azure environments.
        """
        current = Path(__file__).resolve()
        
        # Look for project markers (data folder, app_modules, etc.)
        markers = ['data', 'app_modules', 'requirements.txt', 'Dockerfile']
        
        while current.parent != current:
            if any((current / marker).exists() for marker in markers):
                logger.debug(f"Found project root: {current}")
                return current
            current = current.parent
        
        # Fallback for container environments
        container_paths = [Path('/app'), Path('/home/site/wwwroot'), Path.cwd()]
        for path in container_paths:
            if path.exists() and any((path / marker).exists() for marker in markers):
                logger.info(f"Using container project root: {path}")
                return path
        
        # Final fallback
        fallback = Path(__file__).parent.parent.parent
        logger.warning(f"Using fallback project root: {fallback}")
        return fallback
    
    def _detect_environment(self) -> str:
        """Detect runtime environment (development, staging, production)."""
        # Check explicit environment variable
        if env := os.getenv('ENVIRONMENT'):
            return env.lower()
        
        # Azure App Service detection
        if os.getenv('WEBSITE_SITE_NAME'):
            return 'production' if 'prod' in os.getenv('WEBSITE_SITE_NAME', '') else 'staging'
        
        # Container detection
        if self._is_running_in_container():
            return 'production'
        
        # Local development
        return 'development'
    
    def _is_running_in_container(self) -> bool:
        """Detect if running inside a container."""
        # Docker container detection
        if os.path.exists('/.dockerenv'):
            return True
        
        # Kubernetes detection
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            return True
        
        # Azure Container Instance detection
        if os.getenv('ACI_RESOURCE_GROUP'):
            return True
        
        # Check for container-specific mount points
        container_mounts = ['/app', '/home/site/wwwroot']
        return any(Path(mount).exists() and Path(mount) != Path.cwd() for mount in container_mounts)
    
    def _resolve_database_path(self) -> str:
        """
        Resolve database path based on environment and container setup.
        
        Priority:
        1. DATABASE_PATH environment variable
        2. DATABASE_URL for cloud databases
        3. Environment-specific defaults
        4. Project-relative default
        """
        # Explicit database path override
        if db_path := os.getenv('DATABASE_PATH'):
            path = Path(db_path)
            if path.is_absolute():
                return str(path)
            else:
                return str(self.project_root / db_path)
        
        # Cloud database URL (PostgreSQL, MySQL, etc.)
        if self.database_url:
            return self.database_url
        
        # Environment-specific defaults
        if self.environment == 'production':
            # Production: Use absolute path in container
            if self.is_container:
                return '/app/data/credit_risk.db'
            else:
                return str(self.project_root / 'data' / 'production.db')
        
        elif self.environment == 'staging':
            return str(self.project_root / 'data' / 'staging.db')
        
        # Development default
        return str(self.project_root / 'data' / 'credit_risk.db')
    
    def _resolve_data_directory(self) -> Path:
        """Resolve data directory path."""
        if data_dir := os.getenv('DATA_DIRECTORY'):
            return Path(data_dir)
        
        # Container-aware data directory
        if self.is_container:
            return Path('/app/data')
        
        return self.project_root / 'data'
    
    def _resolve_predictions_file(self) -> str:
        """Resolve updated predictions CSV file path."""
        filename = os.getenv('PREDICTIONS_FILE', 'updated_sic_predictions.csv')
        return str(self.data_directory / filename)
    
    def _log_configuration(self):
        """Log configuration summary for debugging."""
        logger.info(f"Configuration loaded - Environment: {self.environment}")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Database path: {self.database_path}")
        logger.info(f"Container mode: {self.is_container}")
        logger.debug(f"Model version: {self.model_version}")
        logger.debug(f"Data directory: {self.data_directory}")
    
    def get_database_connection(self) -> sqlite3.Connection:
        """
        Get database connection with proper configuration.
        
        Returns:
            SQLite connection object
        """
        if self.database_url and not self.database_url.endswith('.db'):
            # TODO: Add support for PostgreSQL/MySQL connections
            raise NotImplementedError("Cloud database connections not yet implemented")
        
        # Ensure database directory exists
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        return sqlite3.connect(self.database_path)
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate configuration and return status report.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'environment': self.environment,
            'container_mode': self.is_container
        }
        
        # Check database accessibility
        try:
            conn = self.get_database_connection()
            conn.close()
            results['database_accessible'] = True
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Database not accessible: {e}")
            results['database_accessible'] = False
        
        # Check data directory
        if not self.data_directory.exists():
            results['warnings'].append(f"Data directory does not exist: {self.data_directory}")
        
        # Validate model version format
        try:
            float(self.model_version)
        except ValueError:
            results['warnings'].append(f"Invalid model version format: {self.model_version}")
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary for debugging/logging."""
        return {
            'environment': self.environment,
            'is_container': self.is_container,
            'project_root': str(self.project_root),
            'database_path': self.database_path,
            'model_version': self.model_version,
            'confidence_threshold': self.confidence_threshold,
            'sic_table_name': self.sic_table_name,
            'prediction_table_name': self.prediction_table_name,
            'data_directory': str(self.data_directory),
            'debug_mode': self.debug_mode
        }


def get_config() -> CreditRiskConfig:
    """
    Get singleton configuration instance.
    
    Returns:
        CreditRiskConfig instance
    """
    if not hasattr(get_config, '_instance'):
        get_config._instance = CreditRiskConfig()
    return get_config._instance


def validate_environment() -> bool:
    """
    Quick environment validation for container health checks.
    
    Returns:
        True if environment is properly configured
    """
    try:
        config = get_config()
        results = config.validate_configuration()
        return results['valid']
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return False