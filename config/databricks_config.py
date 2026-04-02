"""
Databricks Configuration Module
Handles authentication, connection, and environment setup for Databricks integration
"""

import os
import logging
from typing import Optional, Dict, Any
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from pyspark.sql import SparkSession
import mlflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

class DatabricksConfig:
    """
    Centralized configuration for Databricks integration
    """
    
    def __init__(self):
        self.workspace_client: Optional[WorkspaceClient] = None
        self.spark: Optional[SparkSession] = None
        self.is_databricks_environment = self._check_databricks_environment()
        self.config = self._load_config()
    
    def _check_databricks_environment(self) -> bool:
        """Check if running in Databricks environment"""
        return (
            os.getenv('DATABRICKS_RUNTIME_VERSION') is not None or
            os.path.exists('/databricks/driver') or
            'databricks' in os.getenv('SPARK_HOME', '').lower()
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables or config files"""
        return {
            'workspace_url': os.getenv('https://dbc-beccfe71-12b6.cloud.databricks.com'),
            'token': os.getenv('DATABRICKS_TOKEN'),
            'cluster_id': os.getenv('DATABRICKS_CLUSTER_ID'),
            'warehouse_id': os.getenv('DATABRICKS_WAREHOUSE_ID'),
            'catalog': os.getenv('DATABRICKS_CATALOG', 'credit_risk'),
            'schema': os.getenv('DATABRICKS_SCHEMA', 'default'),
            'unity_catalog_enabled': os.getenv('UNITY_CATALOG_ENABLED', 'true').lower() == 'true'
        }
    
    def initialize_workspace_client(self) -> WorkspaceClient:
        """Initialize Databricks Workspace Client"""
        try:
            if self.is_databricks_environment:
                # Running inside Databricks - use default authentication
                self.workspace_client = WorkspaceClient()
                logger.info("Initialized Databricks client in Databricks environment")
            else:
                # Running outside Databricks - use token authentication
                if not self.config['workspace_url'] or not self.config['token']:
                    raise ValueError(
                        "DATABRICKS_HOST and DATABRICKS_TOKEN environment variables required "
                        "when running outside Databricks environment"
                    )
                
                self.workspace_client = WorkspaceClient(
                    host=self.config['workspace_url'],
                    token=self.config['token']
                )
                logger.info(f"Initialized Databricks client for {self.config['workspace_url']}")
            
            return self.workspace_client
        
        except Exception as e:
            logger.error(f"Failed to initialize Databricks client: {str(e)}")
            raise
    
    def initialize_spark_session(self) -> SparkSession:
        """Initialize Spark session with Databricks optimizations"""
        try:
            if self.is_databricks_environment:
                # In Databricks, use the existing Spark session
                self.spark = SparkSession.getActiveSession()
                if not self.spark:
                    self.spark = SparkSession.builder.getOrCreate()
                logger.info("Using Databricks Spark session")
            else:
                # Local development with Databricks Connect
                self.spark = SparkSession.builder \
                    .appName("CreditRiskAnalysis") \
                    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
                    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
                    .config("spark.databricks.service.address", self.config['workspace_url']) \
                    .config("spark.databricks.service.token", self.config['token']) \
                    .config("spark.databricks.service.clusterId", self.config['cluster_id']) \
                    .getOrCreate()
                logger.info("Initialized Databricks Connect Spark session")
            
            return self.spark
        
        except Exception as e:
            logger.error(f"Failed to initialize Spark session: {str(e)}")
            raise
    
    def setup_mlflow(self):
        """Configure MLflow for Databricks"""
        try:
            if self.is_databricks_environment:
                # MLflow is automatically configured in Databricks
                logger.info("MLflow automatically configured in Databricks environment")
            else:
                # Configure MLflow for external access
                mlflow.set_tracking_uri("databricks")
                mlflow.set_registry_uri("databricks-uc" if self.config['unity_catalog_enabled'] else "databricks")
                logger.info("MLflow configured for external Databricks access")
        
        except Exception as e:
            logger.error(f"Failed to configure MLflow: {str(e)}")
            raise
    
    def get_catalog_schema(self) -> tuple:
        """Get catalog and schema names"""
        return self.config['catalog'], self.config['schema']
    
    def get_table_name(self, table_name: str) -> str:
        """Get fully qualified table name"""
        if self.config['unity_catalog_enabled']:
            return f"{self.config['catalog']}.{self.config['schema']}.{table_name}"
        else:
            return f"{self.config['schema']}.{table_name}"

# Global configuration instance
databricks_config = DatabricksConfig()

def get_databricks_config() -> DatabricksConfig:
    """Get the global Databricks configuration instance"""
    return databricks_config

def initialize_databricks():
    """Initialize all Databricks components"""
    config = get_databricks_config()
    
    # Initialize workspace client
    config.initialize_workspace_client()
    
    # Initialize Spark session
    config.initialize_spark_session()
    
    # Setup MLflow
    config.setup_mlflow()
    
    logger.info("Databricks initialization complete")
    return config
