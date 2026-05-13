"""
Performance Optimization Module - Database connection pooling and SQLite tuning
"""

import sqlite3
import threading
import os
import time
from contextlib import contextmanager
from queue import Queue, Empty
from flask import current_app

class ConnectionPool:
    """
    SQLite connection pooling for improved performance
    """
    
    def __init__(self, database_path, pool_size=10, max_overflow=5, timeout=30):
        self.database_path = database_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        
        self._pool = Queue(maxsize=pool_size)
        self._overflow_connections = 0
        self._lock = threading.Lock()
        
        # Pre-populate the pool
        self._create_initial_connections()
        
        print(f"🔧 Connection pool initialized: {pool_size} base + {max_overflow} overflow")
    
    def _create_initial_connections(self):
        """Create initial pool connections"""
        for _ in range(self.pool_size):
            conn = self._create_optimized_connection()
            self._pool.put(conn)
    
    def _create_optimized_connection(self):
        """Create an optimized SQLite connection"""
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Apply SQLite performance optimizations
        # Note: DELETE journal mode (not WAL) — Azure File Share (SMB) does not
        # support WAL shared memory; WAL mode causes 'database disk image is malformed'.
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance performance/safety
        conn.execute("PRAGMA cache_size=10000")  # 10MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        conn.execute("PRAGMA page_size=4096")  # Optimal page size
        conn.execute("PRAGMA auto_vacuum=INCREMENTAL")  # Prevent db fragmentation
        
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys=ON")
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        start_time = time.time()
        
        try:
            # Try to get from pool first
            try:
                conn = self._pool.get(timeout=0.1)  # Very short timeout
            except Empty:
                # Pool is empty, create overflow connection if allowed
                with self._lock:
                    if self._overflow_connections < self.max_overflow:
                        conn = self._create_optimized_connection()
                        self._overflow_connections += 1
                    else:
                        # Wait for a connection to become available
                        conn = self._pool.get(timeout=self.timeout)
            
            # Test connection is still valid
            conn.execute("SELECT 1")
            
            yield conn
            
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Connection pool error: {e}")
            raise
            
        finally:
            if conn:
                # Check if this is an overflow connection
                is_overflow = False
                with self._lock:
                    if self._overflow_connections > 0 and self._pool.qsize() >= self.pool_size:
                        is_overflow = True
                        self._overflow_connections -= 1
                
                if is_overflow:
                    # Close overflow connection
                    conn.close()
                else:
                    # Return to pool
                    try:
                        self._pool.put(conn, timeout=0.1)
                    except:
                        # Pool might be full, close the connection
                        conn.close()
    
    def get_pool_stats(self):
        """Get connection pool statistics"""
        return {
            'pool_size': self.pool_size,
            'available_connections': self._pool.qsize(),
            'overflow_connections': self._overflow_connections,
            'max_overflow': self.max_overflow
        }
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break
        print("🔧 Connection pool closed")

class PerformanceOptimizer:
    """
    Database performance optimization utilities
    """
    
    @staticmethod
    def analyze_query_performance(query, params=None):
        """Analyze query performance using EXPLAIN QUERY PLAN"""
        try:
            from app_modules.database.connection import DatabaseConnection
            
            with DatabaseConnection().get_connection() as conn:
                # Get query plan
                cursor = conn.execute(f"EXPLAIN QUERY PLAN {query}", params or [])
                plan = cursor.fetchall()
                
                # Execute query with timing
                start_time = time.time()
                cursor = conn.execute(query, params or [])
                results = cursor.fetchall()
                execution_time = (time.time() - start_time) * 1000
                
                return {
                    'query': query,
                    'execution_time_ms': round(execution_time, 2),
                    'result_count': len(results),
                    'query_plan': [dict(row) for row in plan],
                    'timestamp': time.time()
                }
                
        except Exception as e:
            return {
                'query': query,
                'error': str(e),
                'timestamp': time.time()
            }
    
    @staticmethod
    def optimize_database():
        """Run database optimization commands"""
        try:
            from app_modules.database.connection import DatabaseConnection
            
            optimizations = []
            
            with DatabaseConnection().get_connection() as conn:
                # Run ANALYZE to update statistics
                start_time = time.time()
                conn.execute("ANALYZE")
                optimizations.append({
                    'operation': 'ANALYZE',
                    'time_ms': round((time.time() - start_time) * 1000, 2),
                    'status': 'success'
                })
                
                # Run incremental vacuum
                start_time = time.time()
                conn.execute("PRAGMA incremental_vacuum")
                optimizations.append({
                    'operation': 'INCREMENTAL_VACUUM',
                    'time_ms': round((time.time() - start_time) * 1000, 2),
                    'status': 'success'
                })
                
                # Optimize indexes
                start_time = time.time()
                conn.execute("PRAGMA optimize")
                optimizations.append({
                    'operation': 'OPTIMIZE',
                    'time_ms': round((time.time() - start_time) * 1000, 2),
                    'status': 'success'
                })
                
                # Check integrity
                start_time = time.time()
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                optimizations.append({
                    'operation': 'INTEGRITY_CHECK',
                    'time_ms': round((time.time() - start_time) * 1000, 2),
                    'status': 'success' if integrity_result == 'ok' else 'warning',
                    'result': integrity_result
                })
                
                conn.commit()
            
            return {
                'optimizations': optimizations,
                'total_time_ms': sum(opt['time_ms'] for opt in optimizations),
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    @staticmethod
    def get_database_stats():
        """Get comprehensive database statistics"""
        try:
            from app_modules.database.connection import DatabaseConnection
            
            with DatabaseConnection().get_connection() as conn:
                stats = {}
                
                # Database file size
                db_path = os.path.join('data', 'credit_risk.db')
                if os.path.exists(db_path):
                    stats['file_size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
                
                # Page statistics
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0] or 0
                
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0] or 4096
                
                cursor = conn.execute("PRAGMA freelist_count")
                free_pages = cursor.fetchone()[0] or 0
                
                stats.update({
                    'total_pages': page_count,
                    'page_size_bytes': page_size,
                    'free_pages': free_pages,
                    'used_pages': page_count - free_pages,
                    'fragmentation_percent': round((free_pages / max(page_count, 1)) * 100, 2)
                })
                
                # Table statistics
                cursor = conn.execute("""
                    SELECT name, COUNT(*) as record_count
                    FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                
                table_stats = {}
                for table_name, _ in cursor.fetchall():
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    record_count = cursor.fetchone()[0]
                    table_stats[table_name] = record_count
                
                stats['tables'] = table_stats
                
                # Index usage
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """)
                
                stats['custom_indexes'] = len(cursor.fetchall())
                
                # WAL mode status
                cursor = conn.execute("PRAGMA journal_mode")
                stats['journal_mode'] = cursor.fetchone()[0]
                
                cursor = conn.execute("PRAGMA cache_size")
                stats['cache_size_pages'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def create_missing_indexes():
        """Create additional performance indexes if they don't exist"""
        try:
            from app_modules.database.connection import DatabaseConnection
            
            # Define additional performance indexes
            performance_indexes = [
                # Company search optimization
                "CREATE INDEX IF NOT EXISTS idx_companies_name_country ON companies(name, country)",
                "CREATE INDEX IF NOT EXISTS idx_companies_employees_range ON companies(employees)",
                
                # API audit log optimization for analytics
                "CREATE INDEX IF NOT EXISTS idx_audit_status_time ON api_audit_log(response_status, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_audit_endpoint_method ON api_audit_log(endpoint, method)",
                "CREATE INDEX IF NOT EXISTS idx_audit_response_time ON api_audit_log(response_time_ms)",
                
                # Performance metrics optimization
                "CREATE INDEX IF NOT EXISTS idx_perf_metrics_updated ON api_performance_metrics(updated_at)",
                
                # System health optimization
                "CREATE INDEX IF NOT EXISTS idx_health_cpu_memory ON system_health_metrics(cpu_usage_percent, memory_usage_mb)",
                
                # Error tracking optimization
                "CREATE INDEX IF NOT EXISTS idx_error_unresolved ON error_tracking(resolved, timestamp)",
            ]
            
            created_indexes = []
            
            with DatabaseConnection().get_connection() as conn:
                for index_sql in performance_indexes:
                    try:
                        start_time = time.time()
                        conn.execute(index_sql)
                        
                        # Extract index name from SQL
                        index_name = index_sql.split("idx_")[1].split(" ")[0]
                        
                        created_indexes.append({
                            'index_name': f"idx_{index_name}",
                            'creation_time_ms': round((time.time() - start_time) * 1000, 2),
                            'status': 'created'
                        })
                        
                    except sqlite3.OperationalError as e:
                        if "already exists" in str(e).lower():
                            continue  # Index already exists
                        else:
                            raise
                
                conn.commit()
            
            return {
                'created_indexes': created_indexes,
                'total_created': len(created_indexes),
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': time.time()
            }

# Global connection pool instance
_connection_pool = None

def get_connection_pool():
    """Get or create the global connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        db_path = os.path.join('data', 'credit_risk.db')
        _connection_pool = ConnectionPool(db_path)
    
    return _connection_pool

def init_performance_optimizations():
    """Initialize all performance optimizations"""
    try:
        optimizer = PerformanceOptimizer()
        
        # Create missing indexes
        print("🔧 Creating performance indexes...")
        index_result = optimizer.create_missing_indexes()
        if 'error' not in index_result:
            print(f"   ✅ Created {index_result['total_created']} new performance indexes")
        
        # Optimize database
        print("🔧 Running database optimizations...")
        opt_result = optimizer.optimize_database()
        if 'error' not in opt_result:
            print(f"   ✅ Database optimized in {opt_result['total_time_ms']:.2f}ms")
        
        # Initialize connection pool
        print("🔧 Initializing connection pool...")
        pool = get_connection_pool()
        print(f"   ✅ Connection pool ready: {pool.pool_size} connections")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance optimization failed: {e}")
        return False