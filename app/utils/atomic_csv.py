"""
Atomic CSV writing utilities for data corruption prevention.

This module provides atomic file operations using temp file + rename pattern
with file locking to prevent data corruption during concurrent writes.
"""
import os
import tempfile
import shutil
import pandas as pd
from typing import Dict, Any
import portalocker
import logging

logger = logging.getLogger(__name__)

class AtomicCSVWriter:
    """
    Provides atomic CSV writing operations to prevent data corruption.
    
    Uses temp file + rename pattern with optional file locking for safe
    concurrent access to CSV data files.
    """
    
    @staticmethod
    def write_csv_atomic(df: pd.DataFrame, target_path: str, **csv_kwargs) -> bool:
        """
        Write DataFrame to CSV atomically to prevent corruption.
        
        Args:
            df: DataFrame to write
            target_path: Final path for the CSV file
            **csv_kwargs: Additional arguments for pandas to_csv()
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Create temporary file in same directory as target
            temp_dir = os.path.dirname(target_path)
            temp_suffix = '.tmp'
            
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=temp_suffix,
                dir=temp_dir,
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_path = temp_file.name
                
                # Write to temporary file first
                df.to_csv(temp_path, **csv_kwargs)
                logger.debug(f"Wrote data to temporary file: {temp_path}")
            
            # Atomic rename operation
            shutil.move(temp_path, target_path)
            logger.info(f"Atomically wrote CSV to: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Atomic CSV write failed: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return False
    
    @staticmethod
    def write_csv_with_lock(df: pd.DataFrame, target_path: str, timeout: float = 10.0, **csv_kwargs) -> bool:
        """
        Write DataFrame to CSV with file locking for concurrent access safety.
        
        Args:
            df: DataFrame to write
            target_path: Final path for the CSV file
            timeout: Lock timeout in seconds (used for retry logic)
            **csv_kwargs: Additional arguments for pandas to_csv()
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Use lock file to coordinate access
            lock_path = target_path + '.lock'
            
            with open(lock_path, 'w') as lock_file:
                # Acquire exclusive lock (blocking)
                portalocker.lock(lock_file, portalocker.LOCK_EX)
                
                # Perform atomic write under lock
                result = AtomicCSVWriter.write_csv_atomic(df, target_path, **csv_kwargs)
                
                # Lock is automatically released when file closes
                logger.debug(f"Released file lock for: {target_path}")
                return result
                
        except Exception as e:
            logger.error(f"Locked CSV write failed: {e}")
            return False
        finally:
            # Clean up lock file
            if os.path.exists(lock_path):
                try:
                    os.unlink(lock_path)
                except:
                    pass
    
    @staticmethod
    def read_csv_safe(file_path: str, **csv_kwargs) -> pd.DataFrame:
        """
        Safely read CSV with basic error handling and data type preservation.
        
        Args:
            file_path: Path to CSV file
            **csv_kwargs: Additional arguments for pandas read_csv()
            
        Returns:
            DataFrame: Loaded data or empty DataFrame if file doesn't exist
        """
        try:
            if os.path.exists(file_path):
                # Preserve data types for specific columns
                dtype_dict = {
                    'Registration number': str,
                    'Current_SIC': 'Int64',  # Nullable integer for SIC codes
                    'New_SIC': 'Int64',      # Nullable integer for SIC codes
                    'Company_Name': str,
                    'Updated_By': str
                }
                
                # Merge user-provided dtypes with our defaults
                final_kwargs = csv_kwargs.copy()
                if 'dtype' in final_kwargs:
                    dtype_dict.update(final_kwargs['dtype'])
                final_kwargs['dtype'] = dtype_dict
                
                return pd.read_csv(file_path, **final_kwargs)
            else:
                logger.warning(f"CSV file not found: {file_path}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to read CSV {file_path}: {e}")
            return pd.DataFrame()

def safe_csv_append(df: pd.DataFrame, target_path: str, **csv_kwargs) -> bool:
    """
    Convenience function for safely appending data to CSV files.
    
    Args:
        df: DataFrame to append
        target_path: Path to target CSV file
        **csv_kwargs: Additional arguments for pandas to_csv()
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load existing data if file exists
        existing_df = AtomicCSVWriter.read_csv_safe(target_path)
        
        # Combine with new data
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df
        
        # Write atomically with lock
        return AtomicCSVWriter.write_csv_with_lock(combined_df, target_path, **csv_kwargs)
        
    except Exception as e:
        logger.error(f"Safe CSV append failed: {e}")
        return False