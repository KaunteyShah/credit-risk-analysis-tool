"""
Database migration management system.
Handles applying and rolling back database schema migrations.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..connection import db_connection
from ._001_create_tables import MIGRATION_001_CREATE_TABLES, MIGRATION_001_ROLLBACK


class MigrationManager:
    """
    Manages database migrations for schema versioning and updates.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """
        Create migrations tracking table if it doesn't exist.
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT UNIQUE NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            rollback_sql TEXT
        )
        """
        
        try:
            db_connection.execute_update(create_table_sql)
            self.logger.info("Migration tracking table ensured")
        except Exception as e:
            self.logger.error(f"Failed to create migration table: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migration names.
        
        Returns:
            List of migration names that have been applied
        """
        query = "SELECT migration_name FROM schema_migrations ORDER BY applied_at"
        try:
            rows = db_connection.execute_query(query)
            return [row['migration_name'] for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def is_migration_applied(self, migration_name: str) -> bool:
        """
        Check if a specific migration has been applied.
        
        Args:
            migration_name: Name of the migration to check
            
        Returns:
            True if migration has been applied, False otherwise
        """
        query = "SELECT COUNT(*) as count FROM schema_migrations WHERE migration_name = ?"
        try:
            result = db_connection.execute_query(query, (migration_name,))
            return result[0]['count'] > 0
        except Exception as e:
            self.logger.error(f"Failed to check migration status: {e}")
            return False
    
    def apply_migration(self, migration_name: str, migration_sql: str, rollback_sql: Optional[str] = None) -> bool:
        """
        Apply a database migration.
        
        Args:
            migration_name: Unique name for the migration
            migration_sql: SQL commands to apply the migration
            rollback_sql: SQL commands to rollback the migration
            
        Returns:
            True if migration was successful, False otherwise
        """
        if self.is_migration_applied(migration_name):
            self.logger.info(f"Migration {migration_name} already applied, skipping")
            return True
        
        try:
            # Format migration SQL with timestamp
            formatted_sql = migration_sql.format(timestamp=datetime.now().isoformat())
            
            # Execute migration SQL
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executescript(formatted_sql)
                conn.commit()
            
            # Record migration in tracking table
            insert_sql = """
            INSERT INTO schema_migrations (migration_name, rollback_sql) 
            VALUES (?, ?)
            """
            db_connection.execute_update(insert_sql, (migration_name, rollback_sql))
            
            self.logger.info(f"Successfully applied migration: {migration_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply migration {migration_name}: {e}")
            return False
    
    def rollback_migration(self, migration_name: str) -> bool:
        """
        Rollback a specific migration.
        
        Args:
            migration_name: Name of the migration to rollback
            
        Returns:
            True if rollback was successful, False otherwise
        """
        if not self.is_migration_applied(migration_name):
            self.logger.info(f"Migration {migration_name} not applied, nothing to rollback")
            return True
        
        try:
            # Get rollback SQL from migration record
            query = "SELECT rollback_sql FROM schema_migrations WHERE migration_name = ?"
            result = db_connection.execute_query(query, (migration_name,))
            
            if not result or not result[0]['rollback_sql']:
                self.logger.error(f"No rollback SQL found for migration: {migration_name}")
                return False
            
            rollback_sql = result[0]['rollback_sql']
            
            # Execute rollback SQL
            with db_connection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executescript(rollback_sql)
                conn.commit()
            
            # Remove migration record
            delete_sql = "DELETE FROM schema_migrations WHERE migration_name = ?"
            db_connection.execute_update(delete_sql, (migration_name,))
            
            self.logger.info(f"Successfully rolled back migration: {migration_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback migration {migration_name}: {e}")
            return False
    
    def apply_all_migrations(self) -> bool:
        """
        Apply all available migrations in order.
        
        Returns:
            True if all migrations were successful, False otherwise
        """
        migrations = [
            ("001_create_tables", MIGRATION_001_CREATE_TABLES, MIGRATION_001_ROLLBACK),
        ]
        
        success = True
        for migration_name, migration_sql, rollback_sql in migrations:
            if not self.apply_migration(migration_name, migration_sql, rollback_sql):
                success = False
                break
        
        return success
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive migration status information.
        
        Returns:
            Dictionary with migration status details
        """
        applied_migrations = self.get_applied_migrations()
        available_migrations = ["001_create_tables"]
        
        pending_migrations = [m for m in available_migrations if m not in applied_migrations]
        
        return {
            'total_available': len(available_migrations),
            'total_applied': len(applied_migrations),
            'total_pending': len(pending_migrations),
            'applied_migrations': applied_migrations,
            'pending_migrations': pending_migrations,
            'database_exists': db_connection.table_exists('companies')
        }


# Global migration manager instance
migration_manager = MigrationManager()