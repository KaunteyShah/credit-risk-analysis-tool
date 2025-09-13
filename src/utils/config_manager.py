"""
Configuration management utility for the Credit Risk system.
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

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
        """Load default configuration."""
        self._config = {
            "companies_house": {
                "api_key": os.getenv("COMPANIES_HOUSE_API_KEY", ""),
                "base_url": "https://api.company-information.service.gov.uk",
                "rate_limit": 600
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "model": "gpt-4",
                "max_tokens": 1000
            },
            "databricks": {
                "host": os.getenv("DATABRICKS_HOST", ""),
                "token": os.getenv("DATABRICKS_TOKEN", ""),
                "cluster_id": os.getenv("DATABRICKS_CLUSTER_ID", "")
            },
            "models": {
                "sector_classification": {
                    "model_name": "sector_classifier_v1",
                    "confidence_threshold": 0.7
                },
                "turnover_estimation": {
                    "model_name": "turnover_estimator_v1",
                    "confidence_threshold": 0.6
                }
            },
            "processing": {
                "batch_size": 1000,
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
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get model configuration for a specific model."""
        result = self.get(f"models.{model_name}", {})
        return result if isinstance(result, dict) else {}

# Global configuration instance
config = ConfigManager()
