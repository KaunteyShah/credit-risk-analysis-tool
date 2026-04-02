"""
Local SQLite Browser Management
Handles local SQLite browser for development environment
"""

import os
import logging
import sqlite3
import subprocess
import threading
import time
import webbrowser
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class LocalSQLiteBrowser:
    """Manages local SQLite Browser for development environment"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Local SQLite Browser Manager"""
        self.config = config or {}
        
        # Database settings
        self.db_path = self.config.get('database_path', 'data/credit_risk.db')
        self.timestamp_file = 'data/last_db_timestamp.txt'
        
        # Local SQLite browser process
        self.browser_process = None
        self.browser_url = "http://localhost:8080"  # Default SQLite browser port
        
        # Check if SQLite browser is available
        self.sqlite_browser_available = self._check_sqlite_browser_availability()
        
    def _check_sqlite_browser_availability(self) -> bool:
        """Check if SQLite browser is available locally"""
        try:
            # Try to find sqlite browser executable
            result = subprocess.run(['which', 'sqlite3'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("SQLite3 command line tool available")
                return True
            
            # Check for sqlitebrowser GUI application (macOS)
            result = subprocess.run(['which', 'sqlitebrowser'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("SQLite Browser GUI available")
                return True
                
            logger.warning("No SQLite browser tools found locally")
            return False
            
        except Exception as e:
            logger.error(f"Error checking SQLite browser availability: {e}")
            return False
    
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
            logger.debug(f"Saved database timestamp: {timestamp}")
        except Exception as e:
            logger.error(f"Error saving timestamp: {e}")
    
    def has_database_changed(self) -> bool:
        """Check if database has changed since last check"""
        current_timestamp = self.get_database_timestamp()
        last_timestamp = self.get_last_known_timestamp()
        
        changed = current_timestamp > last_timestamp
        
        if changed:
            logger.info(f"Database changed: {last_timestamp} -> {current_timestamp}")
            # Update timestamp immediately
            self.save_timestamp(current_timestamp)
        
        return changed
    
    def get_container_status(self) -> str:
        """Get browser status (simulated for compatibility)"""
        if not os.path.exists(self.db_path):
            return 'no_database'
        elif self.sqlite_browser_available:
            return 'ready'
        else:
            return 'unavailable'
    
    def get_container_url(self) -> Optional[str]:
        """Get the URL to access the database (file path for local)"""
        if os.path.exists(self.db_path):
            return f"file://{os.path.abspath(self.db_path)}"
        return None
    
    def start_container(self) -> Dict[str, Any]:
        """Start local SQLite browser (open database file)"""
        try:
            if not os.path.exists(self.db_path):
                return {
                    'success': False,
                    'error': f'Database file not found: {self.db_path}'
                }
            
            if not self.sqlite_browser_available:
                return {
                    'success': False,
                    'error': 'SQLite browser tools not available locally'
                }
            
            # Try to open with GUI SQLite browser first
            try:
                abs_db_path = os.path.abspath(self.db_path)
                
                # macOS - try to open with SQLite Browser app if available
                if os.path.exists('/Applications/DB Browser for SQLite.app'):
                    subprocess.Popen(['open', '-a', 'DB Browser for SQLite', abs_db_path])
                    logger.info(f"Opened database with DB Browser for SQLite: {abs_db_path}")
                    return {
                        'success': True,
                        'method': 'gui_app',
                        'url': abs_db_path,
                        'message': 'Database opened with DB Browser for SQLite'
                    }
                    
                # Try generic sqlitebrowser command
                elif subprocess.run(['which', 'sqlitebrowser'], capture_output=True).returncode == 0:
                    subprocess.Popen(['sqlitebrowser', abs_db_path])
                    logger.info(f"Opened database with sqlitebrowser: {abs_db_path}")
                    return {
                        'success': True,
                        'method': 'gui_command',
                        'url': abs_db_path,
                        'message': 'Database opened with sqlitebrowser'
                    }
                
                # Fallback: provide instructions for manual opening
                else:
                    logger.info(f"SQLite GUI not found, providing manual instructions for: {abs_db_path}")
                    return {
                        'success': True,
                        'method': 'manual',
                        'url': abs_db_path,
                        'message': f'Please open {abs_db_path} with your preferred SQLite browser',
                        'instructions': [
                            f'Database location: {abs_db_path}',
                            'You can open this file with:',
                            '- DB Browser for SQLite (https://sqlitebrowser.org/)',
                            '- SQLiteStudio (https://sqlitestudio.pl/)',
                            '- Command line: sqlite3 ' + abs_db_path
                        ]
                    }
                    
            except Exception as e:
                logger.error(f"Error opening SQLite browser: {e}")
                # Provide fallback information
                abs_db_path = os.path.abspath(self.db_path)
                return {
                    'success': True,
                    'method': 'fallback',
                    'url': abs_db_path,
                    'message': 'SQLite browser could not be opened automatically',
                    'error': str(e),
                    'instructions': [
                        f'Database location: {abs_db_path}',
                        'Please open this file manually with your SQLite browser'
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error in start_container: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restart_container(self) -> Dict[str, Any]:
        """Restart is not applicable for local browser"""
        return self.start_container()
    
    def stop_container(self) -> Dict[str, Any]:
        """Stop is not applicable for local browser"""
        return {
            'success': True,
            'message': 'Local SQLite browser session - no container to stop'
        }
    
    def check_and_restart_if_needed(self) -> Dict[str, Any]:
        """Check database and return status"""
        try:
            if not os.path.exists(self.db_path):
                return {
                    'success': False,
                    'error': f'Database file not found: {self.db_path}'
                }
            
            # Update timestamp if database changed
            if self.has_database_changed():
                return {
                    'success': True,
                    'action': 'database_updated',
                    'message': 'Database changes detected and timestamp updated'
                }
            else:
                return {
                    'success': True,
                    'action': 'ready',
                    'message': 'Local SQLite browser ready'
                }
                
        except Exception as e:
            logger.error(f"Error in check_and_restart_if_needed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the local SQLite browser system"""
        try:
            db_exists = os.path.exists(self.db_path)
            
            return {
                'database': {
                    'path': self.db_path,
                    'exists': db_exists,
                    'timestamp': self.get_database_timestamp() if db_exists else 0,
                    'last_known_timestamp': self.get_last_known_timestamp(),
                    'changed': self.has_database_changed() if db_exists else False
                },
                'browser': {
                    'type': 'local',
                    'available': self.sqlite_browser_available,
                    'url': self.get_container_url(),
                    'status': self.get_container_status()
                },
                'system': {
                    'mode': 'local',
                    'initialized': True,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                'error': str(e),
                'system': {
                    'mode': 'local',
                    'initialized': False,
                    'timestamp': datetime.now().isoformat()
                }
            }