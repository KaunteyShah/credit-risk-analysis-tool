"""
Configuration management utility for the Credit Risk system.
"""
import os
from typing import Dict, Any, Optional, Union
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

class ConfigManager:
    """Manages configuration loading and access."""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "api_config.yaml"
        
        self.config_path = Path(config_path)
        self._config = None
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                self._config = yaml.safe_load(file)
            return self._config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def get(self, key_path: str, default=None):
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
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_api_config(self, service: str) -> Dict[str, Any]:
        """Get API configuration for a specific service."""
        return self.get(f"{service}", {})
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get model configuration for a specific model."""
        return self.get(f"models.{model_name}", {})

# Global configuration instance
config = ConfigManager()
