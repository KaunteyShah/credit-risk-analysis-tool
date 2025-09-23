"""
Azure Key Vault Integration
Retrieves secrets from Azure Key Vault for secure configuration
"""

import os
import logging
from typing import Dict, Any, Optional
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

logger = logging.getLogger(__name__)

class AzureKeyVaultClient:
    """
    Azure Key Vault client for retrieving application secrets
    """
    
    def __init__(self):
        self.key_vault_url = os.getenv('AZURE_KEY_VAULT_URL')
        self.credential = None
        self.client = None
        
        if self.key_vault_url:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Key Vault client with appropriate credentials"""
        try:
            # Try Managed Identity first (for Azure App Service)
            try:
                self.credential = ManagedIdentityCredential()
                self.client = SecretClient(
                    vault_url=self.key_vault_url,
                    credential=self.credential
                )
                # Test the connection
                list(self.client.list_properties_of_secrets(max_page_size=1))
                logger.info("Connected to Key Vault using Managed Identity")
                return
            except Exception:
                pass
            
            # Fallback to DefaultAzureCredential
            self.credential = DefaultAzureCredential()
            self.client = SecretClient(
                vault_url=self.key_vault_url,
                credential=self.credential
            )
            logger.info("Connected to Key Vault using Default Azure Credential")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Key Vault client: {e}")
            self.client = None
    
    def get_secret(self, secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret from Key Vault
        
        Args:
            secret_name: Name of the secret (dashes will be converted to match Key Vault naming)
            default_value: Default value if secret not found
            
        Returns:
            Secret value or default value
        """
        if not self.client:
            return default_value
        
        try:
            # Key Vault secret names use dashes instead of underscores
            kv_secret_name = secret_name.replace('_', '-').upper()
            
            secret = self.client.get_secret(kv_secret_name)
            logger.info(f"Retrieved secret: {kv_secret_name}")
            return secret.value
            
        except Exception as e:
            logger.warning(f"Failed to retrieve secret {secret_name}: {e}")
            return default_value
    
    def get_all_secrets(self) -> Dict[str, str]:
        """
        Retrieve all secrets from Key Vault
        
        Returns:
            Dictionary of secret names and values
        """
        secrets = {}
        
        if not self.client:
            return secrets
        
        try:
            secret_properties = self.client.list_properties_of_secrets()
            
            for secret_property in secret_properties:
                try:
                    secret = self.client.get_secret(secret_property.name)
                    # Convert Key Vault naming back to environment variable format
                    env_name = secret_property.name.replace('-', '_').upper()
                    secrets[env_name] = secret.value
                except Exception as e:
                    logger.warning(f"Failed to retrieve secret {secret_property.name}: {e}")
            
            logger.info(f"Retrieved {len(secrets)} secrets from Key Vault")
            
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
        
        return secrets
    
    def is_available(self) -> bool:
        """Check if Key Vault is available and accessible"""
        return self.client is not None

# Global instance
_kv_client = None

def get_key_vault_client() -> AzureKeyVaultClient:
    """Get singleton Key Vault client"""
    global _kv_client
    if _kv_client is None:
        _kv_client = AzureKeyVaultClient()
    return _kv_client

def get_secret_or_env(secret_name: str, env_name: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """
    Get value from Key Vault first, then environment variable, then default
    
    Args:
        secret_name: Name of the secret in Key Vault
        env_name: Environment variable name (defaults to secret_name)
        default: Default value if neither source has the value
        
    Returns:
        The secret value
    """
    if env_name is None:
        env_name = secret_name
    
    # Try Key Vault first
    kv_client = get_key_vault_client()
    if kv_client.is_available():
        value = kv_client.get_secret(secret_name)
        if value:
            return value
    
    # Fallback to environment variable
    value = os.getenv(env_name)
    if value and value != f"your_{secret_name.lower()}_here":
        return value
    
    return default
