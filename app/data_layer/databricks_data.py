"""
Databricks Data Layer
Handles data operations with Delta tables and Unity Catalog
"""

import pandas as pd
from pyspark.sql import SparkSession, DataFrame as SparkDataFrame
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, DateType
from delta.tables import DeltaTable
import logging
from typing import Optional, Dict, Any, List
from app.config.databricks_config import get_databricks_config

logger = logging.getLogger(__name__)

class DatabricksDataManager:
    """
    Manages data operations with Databricks Delta tables
    """
    
    def __init__(self):
        self.config = get_databricks_config()
        self.spark: Optional[SparkSession] = None
        self.catalog, self.schema = self.config.get_catalog_schema()
    
    def initialize(self) -> SparkSession:
        """Initialize Spark session"""
        if not self.spark:
            self.spark = self.config.initialize_spark_session()
        return self.spark
    
    def _ensure_spark(self) -> SparkSession:
        """Ensure Spark session is initialized and return it"""
        if self.spark is None:
            self.spark = self.initialize()
        return self.spark
    
    def create_credit_risk_schema(self):
        """Create the credit risk database schema if it doesn't exist"""
        try:
            spark = self._ensure_spark()
            
            if self.config.config['unity_catalog_enabled']:
                # Create catalog if it doesn't exist
                spark.sql(f"CREATE CATALOG IF NOT EXISTS {self.catalog}")
                logger.info(f"Created/verified catalog: {self.catalog}")
            
            # Create schema if it doesn't exist
            schema_sql = f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema}" if self.config.config['unity_catalog_enabled'] else f"CREATE DATABASE IF NOT EXISTS {self.schema}"
            spark.sql(schema_sql)
            logger.info(f"Created/verified schema: {self.schema}")
            
        except Exception as e:
            logger.error(f"Failed to create schema: {str(e)}")
            raise
    
    def get_companies_table_schema(self) -> StructType:
        """Define the schema for the companies table based on Sample_data2.csv"""
        return StructType([
            StructField("company_name", StringType(), True),
            StructField("registration_number", StringType(), True),
            StructField("duns_number", StringType(), True),
            StructField("address_line_1", StringType(), True),
            StructField("address_line_2", StringType(), True),
            StructField("address_line_3", StringType(), True),
            StructField("city", StringType(), True),
            StructField("post_code", StringType(), True),
            StructField("country", StringType(), True),
            StructField("phone", StringType(), True),
            StructField("company_email", StringType(), True),
            StructField("website", StringType(), True),
            StructField("sales_usd", StringType(), True),
            StructField("pre_tax_profit_usd", StringType(), True),
            StructField("assets_usd", StringType(), True),
            StructField("employees_single_site", StringType(), True),
            StructField("employees_total", StringType(), True),
            StructField("business_description", StringType(), True),
            StructField("ownership_type", StringType(), True),
            StructField("entity_type", StringType(), True),
            StructField("parent_company", StringType(), True),
            StructField("parent_country_region", StringType(), True),
            StructField("global_ultimate_company", StringType(), True),
            StructField("global_ultimate_country_region", StringType(), True),
            StructField("us_8_digit_sic_code", StringType(), True),
            StructField("us_8_digit_sic_description", StringType(), True),
            StructField("us_sic_1987_code", StringType(), True),
            StructField("us_sic_1987_description", StringType(), True),
            StructField("naics_2022_code", StringType(), True),
            StructField("naics_2022_description", StringType(), True),
            StructField("uk_sic_2007_code", StringType(), True),
            StructField("uk_sic_2007_description", StringType(), True),
            StructField("anzsic_2006_code", StringType(), True),
            StructField("anzsic_2006_description", StringType(), True),
            # Added columns for predictions
            StructField("predicted_sic", StringType(), True),
            StructField("prediction_confidence", DoubleType(), True),
            StructField("created_at", DateType(), True),
            StructField("updated_at", DateType(), True)
        ])
    
    def create_companies_table(self, overwrite: bool = False):
        """Create the companies Delta table"""
        try:
            spark = self._ensure_spark()
            table_name = self.config.get_table_name("companies")
            
            # Check if table exists
            table_exists = spark.catalog.tableExists(table_name)
            
            if table_exists and not overwrite:
                logger.info(f"Table {table_name} already exists")
                return
            
            # Create empty DataFrame with schema
            schema = self.get_companies_table_schema()
            empty_df = spark.createDataFrame([], schema)
            
            # Write as Delta table
            if overwrite and table_exists:
                empty_df.write.format("delta").mode("overwrite").saveAsTable(table_name)
                logger.info(f"Overwritten table: {table_name}")
            else:
                empty_df.write.format("delta").mode("ignore").saveAsTable(table_name)
                logger.info(f"Created table: {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create companies table: {str(e)}")
            raise
    
    def load_sample_data_to_delta(self, csv_file_path: str = "data/Sample_data2.csv"):
        """Load sample data from Sample_data2.csv to Delta table"""
        try:
            spark = self._ensure_spark()
            
            # Read CSV data
            if csv_file_path.startswith('/'):
                # Absolute path
                df_pandas = pd.read_csv(csv_file_path)
            else:
                # Relative path - default to Sample_data2.csv
                df_pandas = pd.read_csv(csv_file_path)
            
            logger.info(f"Loaded {len(df_pandas)} rows from {csv_file_path}")
            
            # Clean column names to match schema (remove special characters, spaces, etc.)
            df_pandas.columns = [
                'company_name', 'registration_number', 'duns_number', 'address_line_1', 
                'address_line_2', 'address_line_3', 'city', 'post_code', 'country', 
                'phone', 'company_email', 'website', 'sales_usd', 'pre_tax_profit_usd', 
                'assets_usd', 'employees_single_site', 'employees_total', 'business_description', 
                'ownership_type', 'entity_type', 'parent_company', 'parent_country_region', 
                'global_ultimate_company', 'global_ultimate_country_region', 'us_8_digit_sic_code', 
                'us_8_digit_sic_description', 'us_sic_1987_code', 'us_sic_1987_description', 
                'naics_2022_code', 'naics_2022_description', 'uk_sic_2007_code', 
                'uk_sic_2007_description', 'anzsic_2006_code', 'anzsic_2006_description'
            ]
            
            # Add prediction columns
            df_pandas['predicted_sic'] = None
            df_pandas['prediction_confidence'] = None
            df_pandas['created_at'] = pd.Timestamp.now().date()
            df_pandas['updated_at'] = pd.Timestamp.now().date()
            
            # Convert to Spark DataFrame
            df_spark = spark.createDataFrame(df_pandas)
            
            # Get table name
            table_name = self.config.get_table_name("companies")
            
            # Write to Delta table
            df_spark.write.format("delta").mode("append").saveAsTable(table_name)
            logger.info(f"Loaded data to table: {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to load sample data: {str(e)}")
            raise
    
    def read_companies_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Read companies data from Delta table"""
        try:
            spark = self._ensure_spark()
            table_name = self.config.get_table_name("companies")
            
            # Read from Delta table
            spark_df = spark.table(table_name)
            
            if limit:
                spark_df = spark_df.limit(limit)
            
            # Convert to Pandas for Streamlit compatibility
            pandas_df = spark_df.toPandas()
            logger.info(f"Read {len(pandas_df)} rows from {table_name}")
            
            return pandas_df
            
        except Exception as e:
            logger.error(f"Failed to read companies data: {str(e)}")
            # Fallback to CSV if Delta table doesn't exist
            return self._fallback_csv_read()
    
    def update_sic_prediction(self, registration_number: str, predicted_sic: str, confidence: float):
        """Update SIC prediction for a specific company using registration number"""
        try:
            spark = self._ensure_spark()
            table_name = self.config.get_table_name("companies")
            
            # Create Delta table reference
            delta_table = DeltaTable.forName(spark, table_name)
            
            # Update the record
            delta_table.update(
                condition=f"registration_number = '{registration_number}'",
                set={
                    "predicted_sic": f"'{predicted_sic}'",
                    "prediction_confidence": str(confidence),
                    "updated_at": "current_date()"
                }
            )
            
            logger.info(f"Updated SIC prediction for company with registration number {registration_number}")
            
        except Exception as e:
            logger.error(f"Failed to update SIC prediction: {str(e)}")
            raise
    
    def batch_update_sic_predictions(self, predictions: List[Dict[str, Any]]):
        """Batch update SIC predictions using registration numbers"""
        try:
            spark = self._ensure_spark()
            table_name = self.config.get_table_name("companies")
            
            # Create DataFrame with updates
            updates_df = spark.createDataFrame(predictions)
            
            # Create temporary view
            updates_df.createOrReplaceTempView("sic_updates")
            
            # Merge updates using SQL
            merge_sql = f"""
            MERGE INTO {table_name} as target
            USING sic_updates as source
            ON target.registration_number = source.registration_number
            WHEN MATCHED THEN UPDATE SET
                target.predicted_sic = source.predicted_sic,
                target.prediction_confidence = source.prediction_confidence,
                target.updated_at = current_date()
            """
            
            spark.sql(merge_sql)
            logger.info(f"Batch updated {len(predictions)} SIC predictions")
            
        except Exception as e:
            logger.error(f"Failed to batch update SIC predictions: {str(e)}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a Delta table"""
        try:
            spark = self._ensure_spark()
            full_table_name = self.config.get_table_name(table_name)
            
            # Get table details
            table_df = spark.sql(f"DESCRIBE TABLE {full_table_name}")
            schema_info = table_df.collect()
            
            # Get table statistics
            stats_df = spark.sql(f"DESCRIBE TABLE EXTENDED {full_table_name}")
            stats_info = stats_df.collect()
            
            return {
                "table_name": full_table_name,
                "schema": schema_info,
                "statistics": stats_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info: {str(e)}")
            return {}
    
    def _fallback_csv_read(self) -> pd.DataFrame:
        """Fallback to reading Sample_data2.csv file if Delta table is not available"""
        try:
            import os
            csv_path = "data/Sample_data2.csv"
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                # Clean column names to match expected format
                df.columns = [
                    'company_name', 'registration_number', 'duns_number', 'address_line_1', 
                    'address_line_2', 'address_line_3', 'city', 'post_code', 'country', 
                    'phone', 'company_email', 'website', 'sales_usd', 'pre_tax_profit_usd', 
                    'assets_usd', 'employees_single_site', 'employees_total', 'business_description', 
                    'ownership_type', 'entity_type', 'parent_company', 'parent_country_region', 
                    'global_ultimate_company', 'global_ultimate_country_region', 'us_8_digit_sic_code', 
                    'us_8_digit_sic_description', 'us_sic_1987_code', 'us_sic_1987_description', 
                    'naics_2022_code', 'naics_2022_description', 'uk_sic_2007_code', 
                    'uk_sic_2007_description', 'anzsic_2006_code', 'anzsic_2006_description'
                ]
                # Add prediction columns if they don't exist
                if 'predicted_sic' not in df.columns:
                    df['predicted_sic'] = None
                if 'prediction_confidence' not in df.columns:
                    df['prediction_confidence'] = None
                
                logger.info(f"Fallback: Read {len(df)} rows from Sample_data2.csv")
                return df
            else:
                logger.warning("No data source available - Sample_data2.csv not found")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Fallback CSV read failed: {str(e)}")
            return pd.DataFrame()

# Global data manager instance
data_manager = DatabricksDataManager()

def get_data_manager() -> DatabricksDataManager:
    """Get the global data manager instance"""
    return data_manager
