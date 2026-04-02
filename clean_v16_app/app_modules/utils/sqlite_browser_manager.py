"""
SQLite Browser Container Management
Handles automated detection of database changes and container lifecycle management
"""

import os
import logging
import json
import requests
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

# Optional Azure imports - only needed for Azure mode
try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.containerinstance import ContainerInstanceManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Azure SDK not available - Azure Container mode will not work")

logger = logging.getLogger(__name__)

class SQLiteBrowserManager:
    """Manages SQLite Browser container lifecycle and database change detection"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the SQLite Browser Manager"""
        self.config = config or {}
        
        # Check if Azure SDK is available
        if not AZURE_AVAILABLE:
            raise ImportError("Azure SDK not available - cannot initialize Azure Container mode")
        
        # Azure settings
        self.subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID', self.config.get('subscription_id'))
        self.resource_group = os.getenv('SQLITE_RESOURCE_GROUP', 'rg-credit-risk-clean')
        self.container_name = os.getenv('SQLITE_CONTAINER_NAME', 'sqlite-browser')
        
        # Storage Account settings
        self.storage_account_name = os.getenv('STORAGE_ACCOUNT_NAME', 'creditriskstorageacc')
        self.storage_account_key = os.getenv('STORAGE_ACCOUNT_KEY')
        self.file_share_name = os.getenv('FILE_SHARE_NAME', 'credit-risk-db')
        
        # Database settings
        self.db_path = self.config.get('database_path', 'data/credit_risk.db')
        self.timestamp_file = 'data/last_db_timestamp.txt'
        
        # Container settings
        self.container_image = 'coleifer/sqlite-web'  # Web-based SQLite browser
        self.container_port = 8080  # SQLite-web interface port
        
        # Initialize Azure clients (lazy loading)
        self._container_client = None
        self._resource_client = None
        
    @property
    def container_client(self):
        """Lazy load Azure Container Instance client with error handling"""
        if self._container_client is None:
            try:
                credential = DefaultAzureCredential()
                # Test the credential by trying to get a token
                credential.get_token("https://management.azure.com/.default")
                self._container_client = ContainerInstanceManagementClient(
                    credential, self.subscription_id
                )
                logger.info("✅ Azure Container Instance client initialized successfully")
            except Exception as e:
                logger.info(f"🔧 Azure Container Instance client authentication failed: {e}")
                # Return None to indicate authentication failure
                return None
        return self._container_client
    
    def get_database_timestamp(self) -> float:
        """Get the current database file modification timestamp"""
        try:
            if os.path.exists(self.db_path):
                return os.path.getmtime(self.db_path)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting database timestamp: {e}")
            return 0.0
    
    def get_last_known_timestamp(self) -> float:
        """Get the last known database timestamp"""
        try:
            if os.path.exists(self.timestamp_file):
                with open(self.timestamp_file, 'r') as f:
                    return float(f.read().strip())
            return 0.0
        except Exception as e:
            logger.error(f"Error reading last known timestamp: {e}")
            return 0.0
    
    def save_timestamp(self, timestamp: float) -> None:
        """Save the current database timestamp"""
        try:
            os.makedirs(os.path.dirname(self.timestamp_file), exist_ok=True)
            with open(self.timestamp_file, 'w') as f:
                f.write(str(timestamp))
            logger.info(f"Saved database timestamp: {timestamp}")
        except Exception as e:
            logger.error(f"Error saving timestamp: {e}")
    
    def upload_database_to_storage(self) -> bool:
        """Upload database file to Azure File Share"""
        try:
            if not os.path.exists(self.db_path):
                logger.error(f"Database file not found: {self.db_path}")
                return False
            
            # Create file share client
            file_client = ShareFileClient(
                account_url=f"https://{self.storage_account_name}.file.core.windows.net",
                share_name=self.file_share_name,
                file_path="credit_risk.db",
                credential=self.storage_account_key
            )
            
            # Upload database file (delete existing first if it exists)
            try:
                file_client.delete_file()
                logger.info("Deleted existing database file from storage")
            except Exception:
                logger.info("No existing database file to delete")
                
            with open(self.db_path, 'rb') as source_file:
                file_client.upload_file(source_file)
            
            logger.info("Database uploaded to Azure File Share successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading database to storage: {e}")
            return False
    
    def ensure_file_share_exists(self) -> bool:
        """Ensure the Azure File Share exists"""
        try:
            from azure.storage.fileshare import ShareServiceClient
            
            # Create share service client
            share_service_client = ShareServiceClient(
                account_url=f"https://{self.storage_account_name}.file.core.windows.net",
                credential=self.storage_account_key
            )
            
            # Create file share if it doesn't exist
            try:
                share_service_client.create_share(self.file_share_name)
                logger.info(f"Created file share: {self.file_share_name}")
            except Exception as e:
                if "ShareAlreadyExists" in str(e):
                    logger.info(f"File share already exists: {self.file_share_name}")
                else:
                    raise e
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring file share exists: {e}")
            return False
    
    def has_database_changed(self) -> bool:
        """Check if database has changed since last check"""
        current_timestamp = self.get_database_timestamp()
        last_timestamp = self.get_last_known_timestamp()
        
        changed = current_timestamp > last_timestamp
        
        if changed:
            logger.info(f"Database changed: {last_timestamp} -> {current_timestamp}")
        else:
            logger.debug(f"Database unchanged: {current_timestamp}")
            
        return changed
    
    def is_container_running(self) -> bool:
        """Check if SQLite browser container is running"""
        try:
            if self.container_client is None:
                logger.debug("Cannot check container status - Azure authentication failed")
                return False
                
            container = self.container_client.container_groups.get(
                self.resource_group, 
                self.container_name
            )
            return container.provisioning_state == 'Succeeded'
        except Exception as e:
            logger.debug(f"Container not found or error checking status: {e}")
            return False
    
    def get_container_status(self) -> str:
        """Get detailed container status"""
        try:
            if self.container_client is None:
                return 'auth_failed'
                
            container = self.container_client.container_groups.get(
                self.resource_group, 
                self.container_name
            )
            
            state = container.provisioning_state
            if state == 'Succeeded':
                # Check if container instance is actually running
                if container.containers and len(container.containers) > 0:
                    instance_state = container.containers[0].instance_view
                    if instance_state and instance_state.current_state:
                        current_state = instance_state.current_state.state
                        if current_state == 'Running':
                            return 'running'
                        elif current_state in ['Pending', 'Waiting']:
                            return 'starting'
                        else:
                            return 'stopped'
                return 'running'  # Assume running if we can't get detailed state
            elif state in ['Creating', 'Pending']:
                return 'starting'
            else:
                return 'stopped'
                
        except Exception as e:
            logger.debug(f"Container not found or error checking status: {e}")
            return 'stopped'
    
    def get_container_url(self) -> Optional[str]:
        """Get the URL to access the running container"""
        try:
            if self.container_client is None:
                logger.debug("Cannot get container URL - Azure authentication failed")
                return None
                
            container = self.container_client.container_groups.get(
                self.resource_group, 
                self.container_name
            )
            if container.ip_address and container.ip_address.ip:
                return f"http://{container.ip_address.ip}:{self.container_port}"
            return None
        except Exception as e:
            logger.error(f"Error getting container URL: {e}")
            return None
    
    def start_container(self) -> Dict[str, Any]:
        """Start the SQLite browser container"""
        try:
            logger.info("Starting SQLite browser container...")
            
            # Check if Azure authentication is available
            if self.container_client is None:
                error_msg = ("Azure authentication failed. SQLite browser container cannot be started. "
                           "This typically happens in Azure Web Apps without managed identity configured. "
                           "Please enable managed identity or use local development mode.")
                logger.error(error_msg)
                return {
                    'success': False, 
                    'error': error_msg,
                    'suggestion': 'Enable managed identity in Azure Web App or use local development'
                }
            
            # Ensure file share exists and upload current database
            if not self.ensure_file_share_exists():
                return {'success': False, 'error': 'Failed to ensure file share exists'}
            
            if not self.upload_database_to_storage():
                return {'success': False, 'error': 'Failed to upload database to storage'}
            
            # Container configuration
            container_config = {
                'location': 'ukwest',
                'containers': [{
                    'name': self.container_name,
                    'image': self.container_image,
                    'resources': {
                        'requests': {
                            'memory_in_gb': 1.0,  # Lighter requirements for web-based SQLite browser
                            'cpu': 1.0
                        }
                    },
                    'ports': [{
                        'port': self.container_port,
                        'protocol': 'TCP'
                    }],
                    'environment_variables': [
                        {'name': 'SQLITE_DATABASE', 'value': '/data/credit_risk.db'}
                    ],
                    'volume_mounts': [{
                        'name': 'database-volume',
                        'mount_path': '/data'
                    }]
                }],
                'os_type': 'Linux',
                'ip_address': {
                    'type': 'Public',
                    'ports': [{
                        'port': self.container_port,
                        'protocol': 'TCP'
                    }]
                },
                'volumes': [{
                    'name': 'database-volume',
                    'azure_file': {
                        'share_name': self.file_share_name,
                        'storage_account_name': self.storage_account_name,
                        'storage_account_key': self.storage_account_key
                    }
                }],
                'restart_policy': 'OnFailure'
            }
            
            # Create container group (double-check authentication)
            if self.container_client is None:
                return {'success': False, 'error': 'Azure authentication not available'}
                
            operation = self.container_client.container_groups.begin_create_or_update(
                self.resource_group,
                self.container_name,
                container_config
            )
            
            # Wait for completion
            result = operation.result()
            
            logger.info(f"Container started successfully: {result.name}")
            
            return {
                'success': True,
                'container_name': result.name,
                'status': result.provisioning_state,
                'url': self.get_container_url()
            }
            
        except Exception as e:
            logger.error(f"Error starting container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restart_container(self) -> Dict[str, Any]:
        """Restart the SQLite browser container"""
        try:
            logger.info("Restarting SQLite browser container...")
            
            # Stop existing container
            if self.is_container_running():
                self.stop_container()
            
            # Start new container
            return self.start_container()
            
        except Exception as e:
            logger.error(f"Error restarting container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_container(self) -> Dict[str, Any]:
        """Stop the SQLite browser container"""
        try:
            logger.info("Stopping SQLite browser container...")
            
            if self.container_client is None:
                return {'success': False, 'error': 'Azure authentication not available'}
            
            self.container_client.container_groups.delete(
                self.resource_group,
                self.container_name
            )
            
            logger.info("Container stopped successfully")
            
            return {
                'success': True,
                'message': 'Container stopped successfully'
            }
            
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_and_restart_if_needed(self) -> Dict[str, Any]:
        """Check if database changed and restart container if needed"""
        try:
            logger.info("Checking for database changes...")
            
            if not self.has_database_changed():
                return {
                    'success': True,
                    'action': 'none',
                    'message': 'Database unchanged, no restart needed'
                }
            
            # Database changed - update timestamp first
            current_timestamp = self.get_database_timestamp()
            self.save_timestamp(current_timestamp)
            
            # Restart container if running
            if self.is_container_running():
                logger.info("Database changed - restarting container...")
                result = self.restart_container()
                result['action'] = 'restart'
                return result
            else:
                logger.info("Database changed but container not running")
                return {
                    'success': True,
                    'action': 'timestamp_updated',
                    'message': 'Database timestamp updated, container not running'
                }
                
        except Exception as e:
            logger.error(f"Error in check_and_restart_if_needed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the SQLite browser system"""
        try:
            container_running = self.is_container_running()
            container_url = self.get_container_url() if container_running else None
            
            return {
                'database': {
                    'path': self.db_path,
                    'exists': os.path.exists(self.db_path),
                    'timestamp': self.get_database_timestamp(),
                    'last_known_timestamp': self.get_last_known_timestamp(),
                    'changed': self.has_database_changed()
                },
                'container': {
                    'name': self.container_name,
                    'running': container_running,
                    'url': container_url,
                    'resource_group': self.resource_group
                },
                'system': {
                    'initialized': True,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                'error': str(e),
                'system': {
                    'initialized': False,
                    'timestamp': datetime.now().isoformat()
                }
            }


# Global instance for easy access
sqlite_browser_manager = None

def get_sqlite_browser_manager(config: Optional[Dict[str, Any]] = None):
    """Get or create the global SQLite browser manager instance (local or Azure)"""
    global sqlite_browser_manager
    if sqlite_browser_manager is None:
        # Determine mode from config
        mode = config.get('mode', 'azure') if config else 'azure'
        
        if mode == 'local':
            # Use local SQLite browser for development
            from app_modules.utils.local_sqlite_browser import LocalSQLiteBrowser
            sqlite_browser_manager = LocalSQLiteBrowser(config)
            logger.info("Initialized Local SQLite Browser for development")
        else:
            # Use Azure Container Instances for deployed environments
            if not AZURE_AVAILABLE:
                logger.warning("Azure SDK not available - falling back to local mode")
                from app_modules.utils.local_sqlite_browser import LocalSQLiteBrowser
                sqlite_browser_manager = LocalSQLiteBrowser(config)
            else:
                sqlite_browser_manager = SQLiteBrowserManager(config)
                logger.info("Initialized Azure Container SQLite Browser for production")
            
    return sqlite_browser_manager

def initialize_sqlite_browser_system(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Initialize the SQLite browser system and check for database changes"""
    try:
        manager = get_sqlite_browser_manager(config)
        
        # Try to initialize and let the authentication check happen in the client
        # The manager will handle authentication gracefully
        
        result = manager.check_and_restart_if_needed()
        
        mode = config.get('mode', 'azure') if config else 'azure'
        logger.info(f"SQLite browser system initialized ({mode} mode): {result}")
        return result
        
    except Exception as e:
        logger.debug(f"SQLite browser system initialization issue: {e}")
        return {
            'success': True,
            'action': 'fallback',
            'message': f'SQLite browser container not available: {e}'
        }