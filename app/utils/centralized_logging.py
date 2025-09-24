"""
Centralized logging configuration for the Credit Risk Analysis system
"""
import os
import logging
import logging.config
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union
from enum import Enum


class LogLevel(Enum):
    """Logging levels enum for type safety"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class CreditRiskLogger:
    """Centralized logger configuration and management"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.log_dir = os.path.join(self.project_root, 'logs')
        self.config_applied = False
        
        # Ensure logs directory exists
        Path(self.log_dir).mkdir(exist_ok=True)
    
    def get_logging_config(self, environment: str = 'development') -> Dict:
        """Get logging configuration dictionary"""
        
        # Determine log level based on environment
        if environment.lower() in ['production', 'prod']:
            default_level = 'INFO'
            console_level = 'WARNING'
        elif environment.lower() in ['development', 'dev', 'local']:
            default_level = 'INFO'
            console_level = 'INFO'
        elif environment.lower() in ['debug', 'test']:
            default_level = 'DEBUG'
            console_level = 'DEBUG'
        else:
            default_level = 'INFO'
            console_level = 'INFO'
        
        # Override with environment variables
        env_level = os.environ.get('LOG_LEVEL', default_level).upper()
        console_level = os.environ.get('CONSOLE_LOG_LEVEL', console_level).upper()
        
        # Generate log file names with timestamps
        timestamp = datetime.now().strftime('%Y%m%d')
        app_log_file = os.path.join(self.log_dir, f'credit_risk_app_{timestamp}.log')
        error_log_file = os.path.join(self.log_dir, f'credit_risk_errors_{timestamp}.log')
        
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '[%(asctime)s] %(name)s (%(levelname)s): %(message)s',
                    'datefmt': '%Y-%m-%dT%H:%M:%S'
                },
                'simple': {
                    'format': '%(levelname)s:%(name)s:%(message)s'
                },
                'json': {
                    'format': '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}',
                    'datefmt': '%Y-%m-%dT%H:%M:%S'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': console_level,
                    'formatter': 'detailed',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': env_level,
                    'formatter': 'detailed',
                    'filename': app_log_file,
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5,
                    'encoding': 'utf-8'
                },
                'error_file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'ERROR',
                    'formatter': 'detailed',
                    'filename': error_log_file,
                    'maxBytes': 10485760,  # 10MB  
                    'backupCount': 5,
                    'encoding': 'utf-8'
                }
            },
            'loggers': {
                # Application loggers
                'credit_risk_system': {
                    'level': env_level,
                    'handlers': ['console', 'file', 'error_file'],
                    'propagate': False
                },
                'app.agents': {
                    'level': env_level,
                    'handlers': ['console', 'file', 'error_file'],
                    'propagate': False
                },
                'app.utils': {
                    'level': env_level,
                    'handlers': ['console', 'file', 'error_file'],
                    'propagate': False
                },
                'app.apis': {
                    'level': env_level,
                    'handlers': ['console', 'file', 'error_file'],
                    'propagate': False
                },
                'app.workflows': {
                    'level': env_level,
                    'handlers': ['console', 'file', 'error_file'],
                    'propagate': False
                },
                # Flask and related loggers
                'flask': {
                    'level': 'WARNING',
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'werkzeug': {
                    'level': 'WARNING',
                    'handlers': ['file'],
                    'propagate': False
                },
                # Third-party loggers (reduced verbosity)
                'urllib3': {
                    'level': 'WARNING',
                    'handlers': ['file'],
                    'propagate': False
                },
                'requests': {
                    'level': 'WARNING', 
                    'handlers': ['file'],
                    'propagate': False
                }
            },
            'root': {
                'level': env_level,
                'handlers': ['console', 'file']
            }
        }
        
        return config
    
    def apply_config(self, environment: str = 'development') -> None:
        """Apply logging configuration"""
        try:
            config = self.get_logging_config(environment)
            logging.config.dictConfig(config)
            self.config_applied = True
            
            # Log successful configuration
            logger = logging.getLogger('credit_risk_system')
            logger.info(f"Logging configuration applied for environment: {environment}")
            logger.info(f"Log files location: {self.log_dir}")
            logger.info(f"Console log level: {config['handlers']['console']['level']}")
            logger.info(f"File log level: {config['handlers']['file']['level']}")
            
        except Exception as e:
            print(f"Failed to configure logging: {e}")
            # Fallback to basic configuration
            logging.basicConfig(
                level=logging.INFO,
                format='[%(asctime)s] %(name)s (%(levelname)s): %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S'
            )
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the standardized configuration"""
        if not self.config_applied:
            self.apply_config()
        
        return logging.getLogger(name)
    
    def set_log_level(self, logger_name: str, level: Union[str, LogLevel]) -> None:
        """Change log level for a specific logger"""
        logger = logging.getLogger(logger_name)
        
        if isinstance(level, LogLevel):
            numeric_level = level.value
        elif isinstance(level, str):
            numeric_level = getattr(logging, level.upper(), logging.INFO)
        else:
            numeric_level = logging.INFO
        
        logger.setLevel(numeric_level)
    
    def get_log_files_info(self) -> Dict:
        """Get information about current log files"""
        info = {
            'log_directory': self.log_dir,
            'log_files': []
        }
        
        try:
            log_path = Path(self.log_dir)
            if log_path.exists():
                for log_file in log_path.glob('*.log'):
                    stat = log_file.stat()
                    info['log_files'].append({
                        'name': log_file.name,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        except Exception as e:
            info['error'] = str(e)
        
        return info
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Clean up log files older than specified days"""
        try:
            log_path = Path(self.log_dir)
            if not log_path.exists():
                return 0
            
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            deleted_count = 0
            
            for log_file in log_path.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger = self.get_logger('credit_risk_system')
            logger.error(f"Error cleaning up logs: {e}")
            return 0


# Global logger instance
_logger_manager = CreditRiskLogger()

# Convenience functions for backward compatibility
def get_logger(name: str = 'credit_risk_system') -> logging.Logger:
    """Get a standardized logger"""
    return _logger_manager.get_logger(name)

def setup_logging(environment: str = 'development') -> None:
    """Setup logging configuration"""
    _logger_manager.apply_config(environment)

def get_logging_info() -> Dict:
    """Get logging configuration info"""
    return _logger_manager.get_log_files_info()

# Default logger for backward compatibility
logger = get_logger('credit_risk_system')