"""
Workflow Repository Interface

This interface defines operations for workflow and session management.
It handles workflow state, session tracking, and progress monitoring.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime
from .base_repository import BaseRepositoryInterface

class WorkflowRepositoryInterface(BaseRepositoryInterface[Dict[str, Any]]):
    """Interface for workflow and session management operations"""
    
    @abstractmethod
    def create_workflow_session(self, session_data: Dict[str, Any]) -> str:
        """
        Create a new workflow session
        
        Args:
            session_data (Dict[str, Any]): Initial session data including:
                - workflow_type: Type of workflow
                - input_data: Input data for processing
                - user_id: User initiating the workflow
                
        Returns:
            str: Generated session ID
        """
        pass
    
    @abstractmethod
    def get_workflow_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow session by ID
        
        Args:
            session_id (str): Workflow session ID
            
        Returns:
            Optional[Dict[str, Any]]: Session data if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_workflow_status(self, session_id: str, status: str, 
                             progress: Optional[float] = None) -> bool:
        """
        Update workflow session status and progress
        
        Args:
            session_id (str): Workflow session ID
            status (str): New status (pending, running, completed, failed)
            progress (float, optional): Progress percentage (0.0 to 100.0)
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def add_workflow_step_result(self, session_id: str, step_name: str, 
                               result: Any, duration: Optional[float] = None) -> bool:
        """
        Add a workflow step result
        
        Args:
            session_id (str): Workflow session ID
            step_name (str): Name of the workflow step
            result (Any): Step result data
            duration (float, optional): Step execution duration in seconds
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_workflow_results(self, session_id: str) -> Dict[str, Any]:
        """
        Get all results for a workflow session
        
        Args:
            session_id (str): Workflow session ID
            
        Returns:
            Dict[str, Any]: Complete workflow results and step data
        """
        pass
    
    @abstractmethod
    def get_active_workflows(self) -> pd.DataFrame:
        """
        Get all currently active workflow sessions
        
        Returns:
            pd.DataFrame: Active workflows with status and progress
        """
        pass
    
    @abstractmethod
    def get_workflow_history(self, limit: int = 50) -> pd.DataFrame:
        """
        Get workflow execution history
        
        Args:
            limit (int): Maximum number of records to return
            
        Returns:
            pd.DataFrame: Workflow history records
        """
        pass
    
    @abstractmethod
    def cleanup_completed_workflows(self, older_than_days: int = 30) -> int:
        """
        Clean up completed workflow sessions older than specified days
        
        Args:
            older_than_days (int): Delete workflows older than this many days
            
        Returns:
            int: Number of workflows cleaned up
        """
        pass
    
    @abstractmethod
    def get_workflow_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for workflows
        
        Returns:
            Dict[str, Any]: Performance statistics including:
                - average_duration: Average workflow duration
                - success_rate: Workflow success rate
                - most_common_failures: Common failure reasons
        """
        pass
    
    @abstractmethod
    def set_workflow_error(self, session_id: str, error_message: str, 
                          error_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set error information for a workflow session
        
        Args:
            session_id (str): Workflow session ID
            error_message (str): Error message
            error_details (Dict[str, Any], optional): Additional error details
            
        Returns:
            bool: True if set successfully, False otherwise
        """
        pass