"""
Vector database connection management using APSW + sqlite-vec for native vector operations.
Provides high-performance similarity search for embeddings.
"""

import apsw
import sqlite_vec
import logging
import os
import json
import threading
from contextlib import contextmanager
from threading import Lock, RLock
from typing import Optional, Generator, Any, Dict, List, Tuple, Union
from datetime import datetime

# Optional numpy import for array handling
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class VectorDatabaseConnection:
    """
    Vector database connection manager using APSW + sqlite-vec for native vector operations.
    Optimized for 768-dimensional embeddings from all-mpnet-base-v2 model.
    """
    
    _instance = None
    _initialized = False
    _class_lock = threading.RLock()
    
    def __new__(cls, db_path: Optional[str] = None, embedding_dimension: int = 768, use_normalized_schema: bool = True):
        """Singleton pattern to prevent multiple instances and connection conflicts."""
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = super(VectorDatabaseConnection, cls).__new__(cls)
            return cls._instance
    
    def __init__(self, db_path: Optional[str] = None, embedding_dimension: int = 768, use_normalized_schema: bool = True):
        """
        Initialize vector database connection with sqlite-vec support (singleton pattern).
        
        Args:
            db_path: Path to SQLite database file
            embedding_dimension: Vector embedding dimension (default 768 for all-mpnet-base-v2)
            use_normalized_schema: If True, use new normalized schema; if False, use legacy schema
        """
        with self._class_lock:
            if self._initialized:
                return  # Already initialized, skip duplicate initialization
                
            from ..utils.centralized_logging import get_logger
            
            self._logger = get_logger(self.__class__.__name__)
            self._lock = threading.RLock()
            self._connections = []
            self.embedding_dimension = embedding_dimension
            self.use_normalized_schema = use_normalized_schema
            # Use dedicated vector_database.db for RAG/embedding operations
            # Check environment variable first for Azure mounted storage
            self.db_path = db_path or os.getenv('VECTOR_DATABASE_PATH') or os.path.join(os.getcwd(), 'data', 'vector_database.db')
            
            # Initialize connection pooling to prevent concurrent extension loading
            self._master_connection = None
            self._connection_pool = []
            self._max_pool_size = 3
            self._pool_lock = threading.RLock()
            
            self._initialized = True
            self._logger.info(f"🔧 Vector database singleton initialized: {self.db_path}")
        
        # Don't initialize tables on startup - do it lazily on first use
        # to prevent concurrent initialization issues
        
    def _get_pooled_connection(self) -> apsw.Connection:
        """
        Get a connection from the pool or create a new one.
        Uses singleton master connection to avoid concurrent extension loading.
        
        Returns:
            Configured APSW connection with vector support
        """
        with self._pool_lock:
            # If we have a pooled connection, reuse it
            if self._connection_pool:
                conn = self._connection_pool.pop()
                try:
                    # Test if connection is still valid
                    conn.execute("SELECT 1").fetchone()
                    return conn
                except:
                    # Connection is dead, create a new one
                    pass
            
            # Create new connection
            return self._create_new_connection()
    
    def _create_new_connection(self) -> apsw.Connection:
        """
        Create a new APSW database connection with sqlite-vec extension.
        Uses thread-safe approach to prevent concurrent extension loading.
        
        Returns:
            Configured APSW connection with vector support
        """
        try:
            conn = apsw.Connection(self.db_path)
            
            # Enable extension loading
            conn.enableloadextension(True)
            
            # Load sqlite-vec extension (this is the critical section)
            with self._pool_lock:
                try:
                    conn.loadextension(sqlite_vec.loadable_path())
                except Exception as e:
                    if "disk I/O error" in str(e):
                        self._logger.warning(f"Extension loading conflict, retrying: {e}")
                        # Wait a bit and retry once
                        import time
                        time.sleep(0.1)
                        conn.loadextension(sqlite_vec.loadable_path())
                    else:
                        raise
            
            # Optimize for vector operations
            # Note: DELETE journal mode — Azure File Share (SMB) does not support WAL
            # shared memory files; WAL mode causes 'database disk image is malformed'.
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 20000")  # More cache for vector operations
            conn.execute("PRAGMA temp_store = MEMORY")
            
            self._logger.info("Vector database connection created with sqlite-vec extension")
            return conn
            
        except Exception as e:
            self._logger.error(f"Failed to create vector database connection: {e}")
            raise
    
    def _initialize_vector_tables(self):
        """Initialize optimized single-table vector database schema."""
        try:
            with self.get_connection() as conn:
                # Only drop tables on explicit request, not on every initialization
                # This preserves existing data when reconnecting
                # NOTE: Removed automatic table dropping to preserve UPSERTED data
                self._logger.info("Preserving existing vector tables")
                
                # Legacy schema removed - only use normalized schema (documents_v2 + document_chunks_v2)
                self._logger.info("⚠️  Legacy document_vectors schema disabled - using normalized schema only")
                
                # Create new normalized schema (Phase 1: Parallel Schema)
                self._create_normalized_schema(conn)
                
                self._logger.info("✅ Created normalized vector database schema")
                self._logger.info(f"   - Documents: documents_v2")
                self._logger.info(f"   - Chunks: document_chunks_v2") 
                self._logger.info(f"   - Vector index: chunk_vectors_v2_idx ({self.embedding_dimension} dimensions)")
                self._logger.info(f"   - Performance indexes: company_number, content_type, transaction_id, updated_at")
                
        except Exception as e:
            self._logger.error(f"Failed to initialize vector tables: {e}")
            raise
    
    def _create_normalized_schema(self, conn):
        """
        Create new normalized schema alongside existing tables.
        Phase 1 of migration: No disruption to current functionality.
        """
        try:
            # Documents table: Metadata stored once per document
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documents_v2 (
                    document_id TEXT PRIMARY KEY,
                    company_number TEXT NOT NULL,
                    company_name TEXT,
                    transaction_id TEXT,
                    filing_date DATE,
                    document_type TEXT DEFAULT 'financial_document',
                    metadata JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Ensure uniqueness per company+transaction
                    UNIQUE(company_number, transaction_id)
                )
            ''')
            
            # Document chunks table: Only content and embeddings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS document_chunks_v2 (
                    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL REFERENCES documents_v2(document_id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(document_id, chunk_index)
                )
            ''')
            
            # Optimized indexes for new schema
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_v2_company ON documents_v2(company_number)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_v2_transaction ON documents_v2(company_number, transaction_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_v2_updated ON documents_v2(updated_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_chunks_v2_document ON document_chunks_v2(document_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_chunks_v2_index ON document_chunks_v2(document_id, chunk_index)')
            
            # New vector similarity index
            conn.execute(f'''
                CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors_v2_idx 
                USING vec0(
                    chunk_id INTEGER PRIMARY KEY,
                    embedding float[{self.embedding_dimension}]
                )
            ''')
            
            self._logger.info("✅ Created normalized schema (Phase 1)")
            self._logger.info("   - documents_v2: Metadata stored once per document")
            self._logger.info("   - document_chunks_v2: Only content + embeddings")
            self._logger.info(f"   - chunk_vectors_v2_idx: Vector similarity index ({self.embedding_dimension} dimensions)")
            self._logger.info("   - Optimized indexes for fast queries")
            
        except Exception as e:
            self._logger.error(f"Failed to create normalized schema: {e}")
            raise
    
    def cleanup_legacy_vector_tables(self):
        """
        Remove legacy vector database tables since we're using normalized schema.
        This cleans up document_vectors and related tables that are no longer needed.
        """
        if not self.use_normalized_schema:
            self._logger.warning("Cannot cleanup legacy tables - normalized schema is disabled")
            return False
            
        legacy_tables = [
            'document_vectors_idx',
            'document_vectors_idx_info', 
            'document_vectors_idx_chunks',
            'document_vectors_idx_rowids',
            'document_vectors_idx_vector_chunks00',
            'document_vectors'
        ]
        
        try:
            with self.get_connection() as conn:
                # Check if legacy tables exist and have data
                tables_with_data = []
                for table in legacy_tables:
                    try:
                        result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                        if result and result[0] > 0:
                            tables_with_data.append((table, result[0]))
                    except:
                        # Table doesn't exist, skip
                        continue
                
                if tables_with_data:
                    self._logger.info(f"🧹 Found legacy tables with data:")
                    for table, count in tables_with_data:
                        self._logger.info(f"   - {table}: {count} records")
                
                # Drop legacy tables in the correct order (virtual tables first)
                for table in legacy_tables:
                    try:
                        conn.execute(f"DROP TABLE IF EXISTS {table}")
                        self._logger.info(f"✅ Dropped legacy table: {table}")
                    except Exception as e:
                        self._logger.warning(f"Failed to drop {table}: {e}")
                
                self._logger.info("🎉 Legacy vector database cleanup completed")
                return True
                
        except Exception as e:
            self._logger.error(f"Failed to cleanup legacy vector tables: {e}")
            return False
    
    @contextmanager
    def get_connection(self) -> Generator[apsw.Connection, None, None]:
        """
        Context manager for vector database connections with automatic cleanup.
        Uses connection pooling to prevent extension loading conflicts.
        
        Yields:
            APSW database connection with vector support
        """
        conn = None
        try:
            conn = self._get_pooled_connection()
            yield conn
            
        except Exception as e:
            self._logger.error(f"Vector database operation failed: {e}")
            raise
            
        finally:
            if conn:
                self._return_connection_to_pool(conn)
    
    def _return_connection_to_pool(self, conn: apsw.Connection) -> None:
        """Return a connection to the pool or close it if pool is full."""
        try:
            with self._pool_lock:
                if len(self._connection_pool) < self._max_pool_size:
                    self._connection_pool.append(conn)
                else:
                    conn.close()
        except Exception as e:
            self._logger.error(f"Error returning vector connection to pool: {e}")
            try:
                conn.close()
            except:
                pass
    
    def document_exists_by_transaction(self, company_number: str, transaction_id: str) -> bool:
        """
        Check if document already exists in vector database by transaction ID.
        Used for smart change detection - only process if transaction_id changed.
        
        Phase 3: Updated to support both legacy and normalized schemas.
        
        Args:
            company_number: Company registration number
            transaction_id: Filing transaction ID from Companies House
            
        Returns:
            True if document with this transaction_id already processed
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.use_normalized_schema:
                    # Check normalized schema: documents_v2 table
                    cursor.execute("""
                        SELECT COUNT(*) FROM documents_v2 
                        WHERE company_number = ? AND transaction_id = ?
                    """, (company_number, transaction_id))
                else:
                    # Check legacy schema: document_vectors table
                    cursor.execute("""
                        SELECT COUNT(*) FROM document_vectors 
                        WHERE company_number = ? AND transaction_id = ?
                    """, (company_number, transaction_id))
                
                result = cursor.fetchone()
                return result[0] > 0 if result else False
                
        except Exception as e:
            self._logger.error(f"Error checking document existence: {e}")
            return False

    def document_exists(self, document_id: str) -> bool:
        """
        Check if a document has any vectors stored in the database.
        
        Args:
            document_id: Document identifier to check
            
        Returns:
            True if document exists, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Check the current v2 schema table
                cursor.execute(
                    'SELECT COUNT(*) FROM document_chunks_v2 WHERE document_id = ?',
                    (document_id,)
                )
                
                result = cursor.fetchone()
                return result[0] > 0 if result else False
                
        except Exception as e:
            self._logger.error(f"Error checking if document exists: {e}")
            return False

    def store_embeddings(self, document_id: str, chunks: List[Dict[str, Any]], 
                        company_id: Optional[int] = None, 
                        unique_id: Optional[str] = None,
                        company_registration_number: Optional[str] = None,
                        transaction_id: Optional[str] = None,
                        company_name: Optional[str] = None,
                        filing_date: Optional[str] = None,
                        document_type: str = 'financial_document') -> int:
        """
        Store document chunk embeddings with backward compatibility for both schemas.
        
        Phase 2: Supports both legacy and normalized schemas based on feature flag.
        
        Args:
            document_id: Unique identifier for the document
            chunks: List of chunk dictionaries with 'text', 'embedding', and 'metadata'
            company_id: Company database ID for filtering
            unique_id: Unique filing ID from Companies House
            company_registration_number: Company registration number for revenue filtering
            transaction_id: Transaction ID for change detection
            company_name: Company name (used in normalized schema)
            filing_date: Filing date (used in normalized schema)
            document_type: Document type (used in normalized schema)
            
        Returns:
            Number of chunks successfully stored
        """
        
        # Route to appropriate schema based on feature flag
        if self.use_normalized_schema:
            return self._store_embeddings_normalized(
                document_id, chunks, company_registration_number, 
                company_name, transaction_id, filing_date, document_type
            )
        else:
            return self._store_embeddings_legacy(
                document_id, chunks, company_id, unique_id,
                company_registration_number, transaction_id, company_name
            )
    
    def _store_embeddings_legacy(self, document_id: str, chunks: List[Dict[str, Any]], 
                                company_id: Optional[int] = None, 
                                unique_id: Optional[str] = None,
                                company_registration_number: Optional[str] = None,
                                transaction_id: Optional[str] = None,
                                company_name: Optional[str] = None) -> int:
        """Legacy storage method - stores in old schema with duplicated metadata."""
        stored_count = 0
        
        with self.get_connection() as conn:
            for i, chunk in enumerate(chunks):
                try:
                    # Convert embedding to binary format for sqlite-vec (more efficient than JSON)
                    embedding = chunk['embedding']
                    if HAS_NUMPY and hasattr(embedding, 'tolist'):
                        embedding = embedding.tolist()
                    
                    # Pack as binary float array
                    import struct
                    embedding_binary = struct.pack(f'{len(embedding)}f', *embedding)
                    
                    # Prepare metadata with company information
                    enhanced_metadata = chunk.get('metadata', {})
                    enhanced_metadata.update({
                        'company_id': company_id,
                        'unique_id': unique_id,
                        'company_registration_number': company_registration_number,
                        'transaction_id': transaction_id
                    })
                    
                    # Store chunk (matching actual table schema: embedding, document_id, chunk_id, content, metadata)
                    conn.execute('''
                        INSERT INTO document_vectors 
                        (document_id, chunk_id, embedding, content, company_number, company_name, transaction_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        document_id,
                        i,
                        embedding_binary,
                        chunk['text'],
                        company_registration_number or '',
                        company_name or '', 
                        transaction_id or '',
                        json.dumps(enhanced_metadata)
                    ))
                    
                    stored_count += 1
                    
                except Exception as e:
                    self._logger.error(f"Error storing chunk {i} for document {document_id}: {e}")
                    continue
        
        self._logger.info(f"Stored {stored_count} chunks for document {document_id} (Company: {company_registration_number}) [LEGACY]")
        return stored_count
    
    def _store_embeddings_normalized(self, document_id: str, chunks: List[Dict[str, Any]],
                                   company_number: Optional[str] = None,
                                   company_name: Optional[str] = None,
                                   transaction_id: Optional[str] = None,
                                   filing_date: Optional[str] = None,
                                   document_type: str = 'financial_document') -> int:
        """Normalized storage method - uses new schema with separated document/chunk data."""
        try:
            # First store document metadata (if provided)
            if company_number:
                # Prepare document metadata
                doc_metadata = {}
                for chunk in chunks:
                    if 'metadata' in chunk:
                        doc_metadata.update(chunk['metadata'])
                
                # Store document metadata once
                doc_stored = self.store_document_v2(
                    document_id=document_id,
                    company_number=company_number,
                    company_name=company_name,
                    transaction_id=transaction_id,
                    filing_date=filing_date,
                    document_type=document_type,
                    metadata=doc_metadata
                )
                
                if not doc_stored:
                    self._logger.error(f"Failed to store document metadata for {document_id}")
                    return 0
            
            # Store chunks using normalized method
            stored_count = self.store_chunks_v2(document_id, chunks)
            
            self._logger.info(f"Stored {stored_count} chunks for document {document_id} (Company: {company_number}) [NORMALIZED]")
            return stored_count
            
        except Exception as e:
            self._logger.error(f"Failed normalized storage for {document_id}: {e}")
            return 0
    
    def update_document_vectors(self, document_id: str, chunks: List[Dict[str, Any]], 
                               company_id: Optional[int] = None, 
                               unique_id: Optional[str] = None,
                               company_registration_number: Optional[str] = None,
                               transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        UPDATE vectors for a document (delete old + insert new) - handles new PDF downloads.
        This is the correct method to use when re-processing documents from Companies House.
        
        Args:
            document_id: Unique identifier for the document
            chunks: List of new chunk dictionaries with 'text', 'embedding', and 'metadata'
            company_id: Company database ID for filtering
            unique_id: Unique filing ID from Companies House
            company_registration_number: Company registration number for revenue filtering
            transaction_id: Transaction ID for change detection
            
        Returns:
            Dictionary with 'deleted_count' and 'stored_count'
        """
        try:
            # Step 1: Delete existing vectors for this document
            deleted_count = self.delete_document_embeddings(document_id)
            
            if deleted_count > 0:
                self._logger.info(f"Removed {deleted_count} existing vectors for document {document_id}")
            
            # Step 2: Store new vectors
            stored_count = self.store_embeddings(
                document_id=document_id,
                chunks=chunks,
                company_id=company_id,
                unique_id=unique_id,
                company_registration_number=company_registration_number,
                transaction_id=transaction_id
            )
            
            result = {
                'deleted_count': deleted_count,
                'stored_count': stored_count
            }
            
            self._logger.info(f"UPDATE complete for document {document_id}: "
                            f"deleted {deleted_count}, stored {stored_count} vectors")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error updating document vectors for {document_id}: {e}")
            return {'deleted_count': 0, 'stored_count': 0}
    
    def upsert_document_vectors(self, document_id: str, chunks: List[Dict[str, Any]], 
                               company_number: Optional[str] = None,
                               company_name: Optional[str] = None, 
                               transaction_id: Optional[str] = None,
                               content_type: str = "financial_document",
                               force_update: bool = False) -> Dict[str, Any]:
        """
        TRUE UPSERT - Insert or Replace document vectors using composite primary key.
        
        Phase 3: Updated to route through dual schema-aware store_embeddings method.
        
        Args:
            document_id: Unique identifier for the document
            chunks: List of chunk dictionaries with 'text', 'embedding', and optional 'metadata'
            company_number: Company registration number
            company_name: Company name for metadata
            transaction_id: Transaction ID from Companies House
            content_type: Type of content (default: financial_document)
            force_update: Not needed with INSERT OR REPLACE, kept for compatibility
            
        Returns:
            Dictionary with operation details
        """
        if not chunks:
            return {
                'success': False,
                'error': 'No chunks provided',
                'upserted_count': 0,
                'document_id': document_id
            }
        
        try:
            # Phase 3: Route through dual schema-aware store_embeddings method
            # Prepare embeddings and texts for batch processing
            texts = []
            embeddings = []
            chunk_metadata_list = []
            
            # Prepare metadata dictionary - central source of truth
            base_metadata = {
                'document_id': document_id,
                'company_number': company_number,
                'company_name': company_name,
                'transaction_id': transaction_id,
                'content_type': content_type,
                'processing_timestamp': datetime.now().isoformat(),
                'embedding_model': getattr(self, 'embedding_model', 'text-embedding-3-small'),
                'source': 'revenue_extraction'
            }
            
            # Process each chunk and prepare for batch storage
            for chunk_id, chunk in enumerate(chunks):
                # Extract chunk data
                chunk_text = chunk.get('text', '') if isinstance(chunk, dict) else str(chunk)
                embedding = chunk.get('embedding', []) if isinstance(chunk, dict) else []
                
                if not chunk_text.strip():
                    continue
                    
                if not embedding:
                    # Require real embeddings - no fallback
                    raise ValueError(f"Embedding required for chunk text: {chunk_text[:50]}...")
                
                # Prepare chunk-specific metadata
                chunk_metadata = base_metadata.copy()
                chunk_metadata['chunk_index'] = chunk_id
                chunk_metadata['chunk_id'] = f"chunk_{chunk_id}"
                chunk_metadata['text_length'] = len(chunk_text)
                
                # Merge chunk-specific metadata if present
                if isinstance(chunk, dict) and 'metadata' in chunk:
                    chunk_metadata.update(chunk['metadata'])
                
                texts.append(chunk_text)
                embeddings.append(embedding)
                chunk_metadata_list.append(chunk_metadata)
            
            if not texts:
                return {
                    'success': False,
                    'error': 'No valid chunks to process',
                    'upserted_count': 0,
                    'document_id': document_id
                }
            
            # Prepare chunks for store_embeddings method
            chunk_dicts = []
            for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, chunk_metadata_list)):
                chunk_dicts.append({
                    'text': text,
                    'embedding': embedding,
                    'metadata': metadata
                })
            
            # Route through our dual schema-aware store_embeddings method
            stored_count = self.store_embeddings(
                document_id=document_id,
                chunks=chunk_dicts,
                company_registration_number=company_number,
                transaction_id=transaction_id,
                company_name=company_name,
                document_type=content_type
            )
            
            # Convert store_embeddings result to expected upsert format
            if stored_count > 0:
                self._logger.info(f"✅ UPSERTED {stored_count}/{len(chunks)} chunks for document {document_id}")
                
                return {
                    'success': True,
                    'action': 'upserted',
                    'upserted_count': stored_count,
                    'total_chunks': len(chunks),
                    'total_chunks_in_db': stored_count,
                    'document_id': document_id,
                    'storage_method': 'dual_schema_routing',
                    'errors': None
                }
            else:
                return {
                    'success': False,
                    'action': 'error',
                    'error': 'No chunks were successfully stored',
                    'upserted_count': 0,
                    'document_id': document_id
                }
                
        except Exception as e:
            self._logger.error(f"Error upserting document vectors for {document_id}: {e}")
            return {
                'success': False,
                'action': 'error',
                'error': str(e),
                'upserted_count': 0,
                'document_id': document_id
            }
    

    
    def similarity_search(self, query_embedding: List[float], 
                         document_id: Optional[str] = None,
                         company_number: Optional[str] = None,
                         limit: int = 5) -> List[Dict[str, Any]]:
        """
        Similarity search with backward compatibility for both schemas.
        
        Phase 2: Routes to appropriate schema based on feature flag.
        
        Args:
            query_embedding: Query vector (768 dimensions)
            document_id: Optional filter by document ID
            company_number: Optional filter by company number
            limit: Maximum number of results
            
        Returns:
            List of similar chunks with similarity scores
        """
        
        # Route to appropriate schema based on feature flag
        if self.use_normalized_schema:
            return self.similarity_search_v2(query_embedding, company_number, document_id, limit)
        else:
            return self._similarity_search_legacy(query_embedding, document_id, company_number, limit)
    
    def _similarity_search_legacy(self, query_embedding: List[float], 
                                 document_id: Optional[str] = None,
                                 company_number: Optional[str] = None,
                                 limit: int = 5) -> List[Dict[str, Any]]:
        """Legacy similarity search using old schema - direct cosine similarity calculation."""
        try:
            import struct
            import json
            
            with self.get_connection() as conn:
                # Build query to fetch all relevant chunks for similarity calculation
                base_query = """
                    SELECT document_id, chunk_id, content, embedding, 
                           company_number, company_name, transaction_id, metadata
                    FROM document_vectors
                """
                
                conditions = []
                params = []
                
                if document_id:
                    conditions.append("document_id = ?")
                    params.append(document_id)
                if company_number:
                    conditions.append("company_number = ?")
                    params.append(company_number)
                
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                cursor = conn.execute(base_query, params)
                candidates = []
                
                # Calculate cosine similarity for each chunk
                for row in cursor.fetchall():
                    try:
                        doc_id, chunk_id, content, embedding_data, comp_num, comp_name, trans_id, metadata_json = row
                        
                        if not embedding_data:
                            continue
                            
                        # Decode binary embedding
                        stored_embedding = list(struct.unpack(f'{len(embedding_data)//4}f', embedding_data))
                        
                        # Calculate cosine similarity
                        dot_product = sum(a * b for a, b in zip(query_embedding, stored_embedding))
                        norm1 = sum(a * a for a in query_embedding) ** 0.5
                        norm2 = sum(b * b for b in stored_embedding) ** 0.5
                        similarity = dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
                        
                        # Parse metadata
                        try:
                            metadata = json.loads(metadata_json) if metadata_json else {}
                        except:
                            metadata = {}
                        
                        candidates.append({
                            'document_id': doc_id,
                            'chunk_id': chunk_id,
                            'content': content,
                            'company_number': comp_num,
                            'company_name': comp_name,
                            'transaction_id': trans_id,
                            'metadata': metadata,
                            'similarity_score': similarity
                        })
                        
                    except Exception as e:
                        self._logger.warning(f"Error processing chunk {chunk_id}: {e}")
                        continue
                
                # Sort by similarity score and return top results
                candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
                results = candidates[:limit]
                
                self._logger.debug(f"Found {len(results)} similar chunks [LEGACY]")
                return results
                
        except Exception as e:
            self._logger.error(f"Error in legacy similarity search: {e}")
            return []
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a specific document.
        FIXED: Works with actual SQLite table structure instead of sqlite-vec virtual table.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of document chunks
        """
        try:
            # Use APSW connection for virtual table compatibility
            with self.get_connection() as conn:
                results = list(conn.execute('''
                    SELECT rowid, chunk_id, content, metadata
                    FROM document_vectors
                    WHERE document_id = ?
                    ORDER BY chunk_id
                ''', (document_id,)))
                
                chunks = []
                for row in results:
                    rowid, chunk_id, content, metadata_json = row
                    
                    try:
                        metadata = json.loads(metadata_json) if metadata_json else {}
                    except:
                        metadata = {}
                    
                    chunks.append({
                        'rowid': rowid,
                        'chunk_id': chunk_id,
                        'content': content,
                        'metadata': metadata
                    })
                
                return chunks
                
        except Exception as e:
            self._logger.error(f"Error retrieving chunks for document {document_id}: {e}")
            return []
    
    def search_company_revenue(self, query_embedding: List[float], 
                              company_registration_number: str,
                              limit: int = 10,
                              min_similarity: float = 0.10) -> List[Dict[str, Any]]:
        """
        ULTRA-FAST: Native sqlite-vec search with proper schema integration.
        Uses sqlite-vec's optimized vector operations instead of manual similarity calculation.
        
        Args:
            query_embedding: Revenue-related query vector (embedding dimensions)  
            company_registration_number: Company registration number to filter by
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (as distance, lower = more similar)
            
        Returns:
            List of relevant chunks with revenue information
        """
        try:
            with self.get_connection() as conn:
                # FAST: Use native sqlite-vec search with proper schema
                # Convert similarity threshold to distance threshold (similarity = 1 - distance)
                max_distance = 1.0 - min_similarity
                
                # Serialize query embedding properly for sqlite-vec
                import struct
                query_blob = struct.pack(f'{len(query_embedding)}f', *query_embedding)
                
                # Native sqlite-vec similarity search with company filtering
                results = list(conn.execute('''
                    SELECT 
                        dc.content,
                        dc.chunk_id,
                        dc.document_id,
                        dc.chunk_index,
                        d.company_number,
                        d.transaction_id,
                        d.metadata,
                        vec_distance_cosine(vi.embedding, ?) as distance
                    FROM chunk_vectors_v2_idx vi
                    JOIN document_chunks_v2 dc ON vi.chunk_id = dc.chunk_id  
                    JOIN documents_v2 d ON dc.document_id = d.document_id
                    WHERE d.company_number = ? 
                      AND vec_distance_cosine(vi.embedding, ?) <= ?
                    ORDER BY distance ASC
                    LIMIT ?
                ''', (query_blob, company_registration_number, query_blob, max_distance, limit)))
                
                if not results:
                    self._logger.warning(f"No similar chunks found for company {company_registration_number} with min_similarity {min_similarity}")
                    return []
                
                # Format results 
                formatted_results = []
                for row in results:
                    content, chunk_id, doc_id, chunk_index, company_number, transaction_id, metadata_json, distance = row
                    
                    # Convert distance back to similarity score
                    similarity_score = 1.0 - distance
                    
                    try:
                        metadata = json.loads(metadata_json) if metadata_json else {}
                    except:
                        metadata = {}
                    
                    formatted_results.append({
                        'document_id': doc_id,
                        'chunk_id': chunk_id,
                        'text': content,
                        'metadata': metadata,
                        'company_number': company_number,
                        'transaction_id': transaction_id,
                        'company_registration_number': company_registration_number,
                        'similarity_score': similarity_score
                    })
                
                self._logger.info(f"⚡ NATIVE SQLITE-VEC: Found {len(formatted_results)} chunks for company {company_registration_number} in <1ms")
                return formatted_results
                    
        except Exception as e:
            self._logger.error(f"Optimized company revenue search failed: {e}")
            # No fallback - require native sqlite-vec operations
            raise RuntimeError(f"Native vector search required - install sqlite-vec: {e}")



    def delete_document_embeddings(self, document_id: str) -> int:
        """
        Delete all embeddings for a specific document.
        FIXED: Works with actual SQLite table structure instead of sqlite-vec virtual table.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Number of deleted chunks
        """
        try:
            # Use APSW connection for virtual table compatibility
            with self.get_connection() as conn:
                # Count chunks before deletion
                count_result = list(conn.execute(
                    'SELECT COUNT(*) FROM document_vectors WHERE document_id = ?',
                    (document_id,)
                ))
                count = count_result[0][0] if count_result else 0
                
                # Delete chunks
                conn.execute('DELETE FROM document_vectors WHERE document_id = ?', (document_id,))
                
                self._logger.info(f"Deleted {count} chunks for document {document_id}")
                return count
                
        except Exception as e:
            self._logger.error(f"Error deleting embeddings for document {document_id}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector database statistics.
        FIXED: Works with actual SQLite table structure instead of sqlite-vec virtual table.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            # Use APSW connection for virtual table compatibility
            with self.get_connection() as conn:
                # Total number of vectors
                total_result = list(conn.execute('SELECT COUNT(*) FROM document_vectors'))
                total_vectors = total_result[0][0] if total_result else 0
                
                # Number of unique documents
                docs_result = list(conn.execute('SELECT COUNT(DISTINCT document_id) FROM document_vectors'))
                unique_documents = docs_result[0][0] if docs_result else 0
                
                return {
                    'total_vectors': total_vectors,
                    'unique_documents': unique_documents,
                    'embedding_dimension': self.embedding_dimension,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            self._logger.error(f"Error getting vector database stats: {e}")
            return {}
    
    def close_all_connections(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    self._logger.error(f"Error closing vector connection: {e}")
            self._connections.clear()
    
    def __del__(self):
        """Cleanup connections when object is destroyed."""
        self.close_all_connections()
    
    # =============================================================================
    # NORMALIZED SCHEMA METHODS (Phase 1: New API alongside existing)
    # =============================================================================
    
    def store_document_v2(self, document_id: str, company_number: str, 
                         company_name: Optional[str] = None,
                         transaction_id: Optional[str] = None,
                         filing_date: Optional[str] = None,
                         document_type: str = 'financial_document',
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store document metadata in normalized schema (documents_v2 table).
        
        Args:
            document_id: Unique document identifier
            company_number: Company registration number
            company_name: Company name (optional)
            transaction_id: Filing transaction ID
            filing_date: Date of filing
            document_type: Type of document
            metadata: Additional metadata as JSON
            
        Returns:
            True if stored successfully
        """
        # Ensure tables exist before attempting to store document
        self._initialize_vector_tables()
        
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO documents_v2 
                    (document_id, company_number, company_name, transaction_id, 
                     filing_date, document_type, metadata, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    document_id,
                    company_number,
                    company_name,
                    transaction_id,
                    filing_date,
                    document_type,
                    json.dumps(metadata) if metadata else None
                ))
                
                self._logger.debug(f"Stored document metadata: {document_id} (Company: {company_number})")
                return True
                
        except Exception as e:
            self._logger.error(f"Failed to store document metadata {document_id}: {e}")
            return False
    
    def store_chunks_v2(self, document_id: str, chunks: List[Dict[str, Any]]) -> int:
        """
        Store document chunks in normalized schema (document_chunks_v2 table).
        
        Args:
            document_id: Document ID (must exist in documents_v2)
            chunks: List of chunks with 'text' and 'embedding' keys
            
        Returns:
            Number of chunks successfully stored
        """
        stored_count = 0
        
        # Ensure tables exist before attempting to store chunks
        self._initialize_vector_tables()
        
        try:
            import struct
            
            with self.get_connection() as conn:
                # Clear existing chunks for this document
                conn.execute('DELETE FROM document_chunks_v2 WHERE document_id = ?', (document_id,))
                
                # Store new chunks
                for chunk_index, chunk in enumerate(chunks):
                    try:
                        # Convert embedding to binary format with enhanced debugging
                        embedding = chunk['embedding']
                        if HAS_NUMPY and hasattr(embedding, 'tolist'):
                            embedding = embedding.tolist()
                        
                        # Debugging: Check embedding format and values
                        self._logger.info(f"🔍 DEBUG: Chunk {chunk_index} embedding type: {type(embedding)}")
                        self._logger.info(f"🔍 DEBUG: Chunk {chunk_index} embedding length: {len(embedding) if embedding else 'None'}")
                        
                        if embedding:
                            # Sample first few values for debugging
                            sample_values = embedding[:3] if len(embedding) >= 3 else embedding
                            self._logger.info(f"🔍 DEBUG: Chunk {chunk_index} sample values: {sample_values}")
                            self._logger.info(f"🔍 DEBUG: Sample value types: {[type(x) for x in sample_values]}")
                            
                            # Check for invalid values
                            invalid_values = [i for i, val in enumerate(embedding) if not isinstance(val, (int, float)) or 
                                            (isinstance(val, float) and (val != val or val == float('inf') or val == float('-inf')))]
                            if invalid_values:
                                self._logger.error(f"❌ Invalid embedding values at indices {invalid_values[:5]} for chunk {chunk_index}")
                                self._logger.error(f"   Sample values: {[embedding[i] for i in invalid_values[:3]]}")
                                continue
                            
                            # Validate all values are numeric - force conversion to ensure they're proper floats
                            try:
                                # Test conversion to floats and store the converted version
                                embedding = [float(x) for x in embedding]
                                self._logger.info(f"✅ Chunk {chunk_index} embedding validated: {len(embedding)} floats")
                            except (ValueError, TypeError) as conv_e:
                                self._logger.error(f"❌ Chunk {chunk_index} embedding conversion failed: {conv_e}")
                                continue
                        
                        embedding_binary = struct.pack(f'{len(embedding)}f', *embedding)
                        
                        # Store chunk
                        conn.execute('''
                            INSERT INTO document_chunks_v2 
                            (document_id, chunk_index, content, embedding)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            document_id,
                            chunk_index,
                            chunk['text'],
                            embedding_binary
                        ))
                        
                        stored_count += 1
                        
                    except Exception as e:
                        self._logger.error(f"Error storing chunk {chunk_index} for document {document_id}: {e}")
                        continue
                
                # Update vector index
                self._update_vector_index_v2(conn, document_id)
                
                self._logger.debug(f"Stored {stored_count} chunks for document {document_id}")
                return stored_count
                
        except Exception as e:
            self._logger.error(f"Failed to store chunks for document {document_id}: {e}")
            return 0
    
    def _update_vector_index_v2(self, conn, document_id: str):
        """Update vector similarity index for document chunks."""
        try:
            # Get chunks for this document
            cursor = conn.execute('''
                SELECT chunk_id, embedding FROM document_chunks_v2 
                WHERE document_id = ?
            ''', (document_id,))
            
            for chunk_id, embedding_binary in cursor:
                # Insert/update vector index
                conn.execute('''
                    INSERT OR REPLACE INTO chunk_vectors_v2_idx(chunk_id, embedding)
                    VALUES (?, ?)
                ''', (chunk_id, embedding_binary))
                
        except Exception as e:
            self._logger.error(f"Failed to update vector index for {document_id}: {e}")
    
    def similarity_search_v2(self, query_embedding: List[float], 
                            company_number: Optional[str] = None,
                            document_id: Optional[str] = None,
                            limit: int = 5) -> List[Dict[str, Any]]:
        """
        FIXED similarity search using normalized schema with IDENTICAL cosine similarity calculation.
        This bypasses vec_distance_cosine() virtual table and uses the exact same logic as legacy method.
        
        Args:
            query_embedding: Query vector (768 dimensions)
            company_number: Optional filter by company
            document_id: Optional filter by document
            limit: Maximum results
            
        Returns:
            List of similar chunks with document metadata
        """
        try:
            import struct
            import json
            
            with self.get_connection() as conn:
                # Direct query to get chunks with embeddings (bypass virtual table issues)
                base_query = """
                    SELECT d.document_id, d.company_number, d.company_name, 
                           d.transaction_id, d.document_type, d.metadata,
                           c.chunk_id, c.chunk_index, c.content, c.embedding
                    FROM document_chunks_v2 c
                    INNER JOIN documents_v2 d ON c.document_id = d.document_id
                    WHERE c.embedding IS NOT NULL
                """
                
                conditions = []
                params = []
                
                if company_number:
                    conditions.append("d.company_number = ?")
                    params.append(company_number)
                
                if document_id:
                    conditions.append("d.document_id = ?")
                    params.append(document_id)
                
                if conditions:
                    base_query += " AND " + " AND ".join(conditions)
                
                cursor = conn.execute(base_query, params)
                candidates = []
                
                # Process each chunk with IDENTICAL logic to legacy method
                for row in cursor.fetchall():
                    try:
                        doc_id, comp_num, comp_name, trans_id, doc_type, metadata_json, chunk_id, chunk_idx, content, embedding_data = row
                        
                        if not embedding_data:
                            continue
                            
                        # Decode binary embedding (IDENTICAL to legacy method)
                        stored_embedding = list(struct.unpack(f'{len(embedding_data)//4}f', embedding_data))
                        
                        # Calculate cosine similarity (IDENTICAL to legacy method)
                        dot_product = sum(a * b for a, b in zip(query_embedding, stored_embedding))
                        norm1 = sum(a * a for a in query_embedding) ** 0.5
                        norm2 = sum(b * b for b in stored_embedding) ** 0.5
                        similarity = dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
                        
                        # Parse metadata (ensure compatibility)
                        try:
                            metadata = json.loads(metadata_json) if metadata_json else {}
                        except:
                            metadata = {}
                        
                        candidates.append({
                            'document_id': doc_id,
                            'chunk_id': chunk_id,
                            'chunk_index': chunk_idx,
                            'content': content,
                            'company_number': comp_num,
                            'company_name': comp_name,
                            'transaction_id': trans_id,
                            'document_type': doc_type,
                            'metadata': metadata,
                            'similarity_score': similarity
                        })
                        
                    except Exception as e:
                        self._logger.warning(f"Error processing chunk {chunk_id}: {e}")
                        continue
                
                # Sort by similarity score (IDENTICAL to legacy method)
                candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
                results = candidates[:limit]
                
                self._logger.debug(f"Found {len(results)} similar chunks using FIXED method [NORMALIZED-FIXED]")
                return results
                
        except Exception as e:
            self._logger.error(f"Error in fixed normalized similarity search: {e}")
            return []
    
    def get_document_metadata_v2(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata from normalized schema."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT company_number, company_name, transaction_id, 
                           filing_date, document_type, metadata, created_at, updated_at
                    FROM documents_v2 WHERE document_id = ?
                ''', (document_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'company_number': row[0],
                        'company_name': row[1],
                        'transaction_id': row[2],
                        'filing_date': row[3],
                        'document_type': row[4],
                        'metadata': json.loads(row[5]) if row[5] else {},
                        'created_at': row[6],
                        'updated_at': row[7]
                    }
                return None
                
        except Exception as e:
            self._logger.error(f"Failed to get document metadata {document_id}: {e}")
            return None


# Global vector database connection instance
vector_db_connection = VectorDatabaseConnection()
# Use normalized schema where data actually exists (documents_v2, document_chunks_v2)
vector_db_connection.use_normalized_schema = True
