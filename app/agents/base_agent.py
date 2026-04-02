"""
Base agent class for the multi-agent system.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
import sys
import os

# Add parent directory to path for imports

from app.utils.logger import get_logger

logger = get_logger(__name__)
logger = get_logger(__name__)

@dataclass
class AgentResult:
    """Standard result format for all agents."""
    agent_name: str
    timestamp: datetime
    success: bool
    data: Any = None
    confidence: float = 0.0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str):
        self.name = name
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
    
    @abstractmethod
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process data and return results.
        
        Args:
            data: Input data to process
            **kwargs: Additional parameters
        
        Returns:
            AgentResult with processing results
        """
        pass
    
    def log_activity(self, message: str, level: str = "INFO") -> None:
        """Log agent activity."""
        timestamp = datetime.now().isoformat()
        log_msg = f"[{timestamp}] {self.name} ({level}): {message}"
        
        if level.upper() == "ERROR":
            logger.error(log_msg)
        elif level.upper() == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def create_result(
        self,
        success: bool,
        data: Any = None,
        confidence: float = 0.0,
        error_message: Optional[str] = None,
        **metadata
    ) -> AgentResult:
        """Create a standardized result object."""
        return AgentResult(
            agent_name=self.name,
            timestamp=datetime.now(),
            success=success,
            data=data,
            confidence=confidence,
            error_message=error_message,
            metadata=metadata
        )
