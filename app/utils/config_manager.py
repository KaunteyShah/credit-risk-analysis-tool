"""
Configuration management utility for the Credit Risk system.
Azure-ready with Key Vault integration.
"""
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

# Try to import Azure Key Vault client
try:
    from app.utils.azure_keyvault import get_secret_or_env
    AZURE_KEYVAULT_AVAILABLE = True
except ImportError:
    AZURE_KEYVAULT_AVAILABLE = False
    
    def get_secret_or_env(secret_name: str, env_name: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
        """Fallback when Azure Key Vault is not available"""
        return os.getenv(env_name or secret_name, default)

class ConfigManager:
    """Manages configuration loading and access."""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_dir = Path(__file__).parent.parent / "config"
            config_path = str(config_dir / "api_config.json")
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load_default_config()
    
    def load_default_config(self) -> Dict[str, Any]:
        """Load default configuration with Azure Key Vault integration."""
        self._config = {
            "companies_house": {
                "api_key": get_secret_or_env("COMPANIES_HOUSE_API_KEY", default=""),
                "base_url": "https://api.companieshouse.gov.uk",
                "rate_limit": int(os.getenv("COMPANIES_HOUSE_RATE_LIMIT", "600")),
                "timeout": 30,
                "max_retries": 3
            },
            "openai": {
                "api_key": get_secret_or_env("OPENAI_API_KEY", default=""),
                "model": os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "1500")),
                "endpoint": os.getenv("OPENAI_ENDPOINT", ""),
                "api_version": os.getenv("OPENAI_API_VERSION", "2024-02-01"),
                "deployment_name": os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-4")
            },
            "databricks": {
                "workspace_url": os.getenv("DATABRICKS_WORKSPACE_URL", ""),
                "token": get_secret_or_env("DATABRICKS_TOKEN", default=""),
                "cluster_id": os.getenv("DATABRICKS_CLUSTER_ID", ""),
                "warehouse_id": os.getenv("DATABRICKS_WAREHOUSE_ID", ""),
                "catalog": os.getenv("DATABRICKS_CATALOG", "credit_risk"),
                "schema": os.getenv("DATABRICKS_SCHEMA", "production"),
                "unity_catalog_enabled": os.getenv("UNITY_CATALOG_ENABLED", "true").lower() == "true"
            },
            "azure": {
                "key_vault_url": os.getenv("AZURE_KEY_VAULT_URL", ""),
                "environment": os.getenv("ENVIRONMENT", "development"),
                "resource_group": os.getenv("AZURE_RESOURCE_GROUP", ""),
                "app_service_name": os.getenv("AZURE_APP_SERVICE_NAME", "")
            },
            "models": {
                "sector_classification": {
                    "model_name": "sector_classifier_v1",
                    "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
                },
                "turnover_estimation": {
                    "model_name": "turnover_estimator_v1",
                    "confidence_threshold": 0.6
                }
            },
            "processing": {
                "batch_size": int(os.getenv("BATCH_SIZE", "1000")),
                "max_workers": 4,
                "timeout": 30
            }
        }
        return self._config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration value
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value[key]
                else:
                    return default
            return value
        except (KeyError, TypeError):
            return default
    
    def get_api_config(self, service: str) -> Dict[str, Any]:
        """Get API configuration for a specific service."""
        result = self.get(service, {})
        return result if isinstance(result, dict) else {}
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that all required API keys are configured."""
        validations = {}
        
        # Validate OpenAI
        openai_key = self.get("openai.api_key")
        openai_endpoint = self.get("openai.endpoint")
        validations["openai"] = bool(
            openai_key and 
            openai_key != "sk-your_openai_api_key_here" and
            (openai_key.startswith("sk-") or openai_endpoint)
        )
        
        # Validate Companies House
        ch_key = self.get("companies_house.api_key")
        validations["companies_house"] = bool(
            ch_key and ch_key != "your_companies_house_api_key_here"
        )
        
        # Validate Databricks
        db_workspace_url = self.get("databricks.workspace_url")
        db_token = self.get("databricks.token")
        validations["databricks"] = bool(
            db_workspace_url and db_token and
            "your-databricks-workspace" not in db_workspace_url and
            db_token != "your-databricks-personal-access-token"
        )
        
        return validations
    
    def is_production_ready(self) -> bool:
        """Check if all services are configured for production."""
        validations = self.validate_api_keys()
        return all(validations.values())
    
    def get_missing_configs(self) -> List[str]:
        """Get list of missing or invalid configurations."""
        validations = self.validate_api_keys()
        return [service for service, valid in validations.items() if not valid]
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get model configuration for a specific model."""
        result = self.get(f"models.{model_name}", {})
        return result if isinstance(result, dict) else {}

# Global configuration instance
config = ConfigManager()
