"""
Database connection management for SQLite with connection pooling and error handling.
Follows modular architecture pattern.
"""

import sqlite3
import logging
import os
from contextlib import contextmanager
from threading import Lock
from typing import Optional, Generator, Any, Dict, List
from datetime import datetime


class DatabaseConnection:
    """
    SQLite database connection manager with connection pooling and thread safety.
    """
    
    def __init__(self, db_path: Optional[str] = None, pool_size: int = 10):
        """
        Initialize database connection manager.
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool
        """
        # Priority: explicit path > DATABASE_PATH env var > default local path
        if db_path:
            self.db_path: str = db_path
        elif os.getenv('DATABASE_PATH'):
            self.db_path: str = os.getenv('DATABASE_PATH', '')
            logging.getLogger(__name__).info(f"✅ Using DATABASE_PATH from environment: {self.db_path}")
        else:
            self.db_path: str = os.path.join(os.getcwd(), 'data', 'credit_risk.db')
            logging.getLogger(__name__).info(f"Using default database path: {self.db_path}")
        
        self.pool_size = pool_size
        self._connections = []
        self._lock = Lock()
        self._logger = logging.getLogger(__name__)
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection with optimized settings.
        
        Returns:
            Configured SQLite connection
        """
        try:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Optimize for read performance
            # Note: DELETE journal mode (not WAL) — Azure File Share (SMB) does not
            # support WAL-mode shared memory, which causes 'database disk image is
            # malformed' errors on network-mounted SQLite databases.
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            
            # Set row factory for dict-like access
            conn.row_factory = sqlite3.Row
            
            return conn
            
        except sqlite3.Error as e:
            self._logger.error(f"Failed to create database connection: {e}")
            raise
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections with automatic cleanup.
        
        Yields:
            Database connection from pool
        """
        conn = None
        try:
            with self._lock:
                if self._connections:
                    conn = self._connections.pop()
                else:
                    conn = self._create_connection()
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            self._logger.error(f"Database operation failed: {e}")
            raise
            
        finally:
            if conn:
                try:
                    with self._lock:
                        if len(self._connections) < self.pool_size:
                            self._connections.append(conn)
                        else:
                            conn.close()
                except Exception as e:
                    self._logger.error(f"Error returning connection to pool: {e}")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[sqlite3.Row]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL SELECT statement
            params: Query parameters
            
        Returns:
            List of rows as sqlite3.Row objects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL statement
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute multiple statements with different parameters.
        
        Args:
            query: SQL statement
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def get_last_insert_id(self, query: str, params: Optional[tuple] = None) -> Optional[int]:
        """
        Execute INSERT and return the last inserted row ID.
        
        Args:
            query: INSERT statement
            params: Query parameters
            
        Returns:
            Last inserted row ID or None if no row was inserted
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        result = self.execute_query(query, (table_name,))
        return len(result) > 0
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = f"PRAGMA table_info({table_name})"
        rows = self.execute_query(query)
        return [dict(row) for row in rows]
    
    def close_all_connections(self):
        """
        Close all connections in the pool.
        """
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    self._logger.error(f"Error closing connection: {e}")
            self._connections.clear()
    
    def __del__(self):
        """Cleanup connections when object is destroyed."""
        self.close_all_connections()


# Global database connection instance
db_connection = DatabaseConnection()