"""
Financial Extraction Node

LangGraph workflow node for PDF document processing and text extraction.
Integrates existing document download and RAG processing capabilities:
1. Download PDF documents using transaction_id
2. Extract and chunk text content  
3. Store in vector database (sqlite-vec integration)
4. Prepare for revenue extraction workflow

Reuses existing infrastructure:
- DocumentDownloadAgent for PDF downloads (90% code reuse)
- RAGDocumentAgent for vectorization (85% code reuse)  
- Companies House document URLs and metadata
- Vector database integration with sqlite-vec
"""

import logging
import os
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime

from ....agents.document_download_agent import DocumentDownloadAgent
from ..document_processor import AgenticDocumentProcessor
from ..data_models import SemanticQuery
from ..rag_revenue_extractor import RAGRevenueExtractor
from ....utils.logger import get_logger

logger = get_logger(__name__)

class FinancialExtractionNode:
    """
    Streamlined document processing node for revenue extraction.
    Uses native vector database operations without legacy agent dependencies.
    
    Workflow Steps:
    1. Validate transaction_id and company data from previous node
    2. Download PDF document using DocumentDownloadAgent
    3. Extract and chunk text using AgenticDocumentProcessor
    4. Generate embeddings and store in native vector database
    5. Perform semantic search for revenue extraction
    
    Components Used:
    - DocumentDownloadAgent: PDF downloads from Companies House
    - AgenticDocumentProcessor: Native vector DB operations with sentence-transformers
    - VectorDatabaseConnection: APSW + sqlite-vec for high-performance vector operations
    """
    
    def __init__(self, document_agent: Optional[DocumentDownloadAgent] = None,
                 document_processor: Optional[AgenticDocumentProcessor] = None):
        """Initialize Financial Extraction Node with RAG capabilities."""
        """
        Initialize with streamlined dependencies (no legacy RAG agent).
        
        Args:
            document_agent: Document download agent
            document_processor: Streamlined document processor with native vector DB
        """
        self.document_agent = document_agent or DocumentDownloadAgent()
        self.document_processor = document_processor or AgenticDocumentProcessor()
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Initialize comprehensive RAG revenue extractor with strict validation
        self.rag_revenue_extractor = None
        self.strict_mode_enabled = False
        
        try:
            self.rag_revenue_extractor = RAGRevenueExtractor()
            
            # STRICT CONTROL: Test database connectivity immediately
            self._validate_rag_extractor_connectivity()
            
            self.strict_mode_enabled = True
            self.logger.info("✅ RAG Revenue Extractor initialized and validated - strict mode enabled")
        except Exception as e:
            self.logger.error(f"❌ CRITICAL: Failed to initialize RAG Revenue Extractor: {e}")
            self.logger.error("❌ STRICT MODE: Agentic workflow will fail explicitly without proper RAG system")
            # Don't raise during initialization - fail during execution instead
            self.rag_revenue_extractor = None
            self.strict_mode_enabled = False
        
        # Configure for revenue extraction workflow
        self._configure_for_revenue_extraction()
    
    def _validate_rag_extractor_connectivity(self):
        """
        STRICT CONTROL: Validate RAG extractor can connect to databases and APIs.
        Fails fast to prevent misleading fallback behavior.
        """
        try:
            # Test vector database connectivity
            from app_modules.database.vector_connection import VectorDatabaseConnection
            
            vector_db = VectorDatabaseConnection()
            with vector_db.get_connection() as conn:
                # Quick connectivity test
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM documents_v2 LIMIT 1')
                cursor.fetchone()
            
            self.logger.info("✅ Vector database connectivity validated")
            
            # Test embedding service availability  
            from app_modules.services.embedding.smart_embedding_service import get_smart_embedding_service
            
            embedding_service = get_smart_embedding_service()
            if embedding_service is None:
                raise Exception("Embedding service not available")
            
            # Quick embedding test
            test_embedding = embedding_service.encode(['test'])
            if not test_embedding or len(test_embedding) == 0:
                raise Exception("Embedding generation failed")
                
            self.logger.info("✅ Embedding service connectivity validated")
            
        except Exception as e:
            self.logger.error(f"❌ RAG extractor connectivity validation failed: {e}")
            raise ValueError(f"RAG system connectivity validation failed: {e}. Cannot proceed with agentic workflow.")
        
    def _configure_for_revenue_extraction(self):
        """Configure agents specifically for revenue extraction workflow."""
        # Enable caching for document downloads
        if hasattr(self.document_agent, 'cache_enabled'):
            self.document_agent.cache_enabled = True
    
    def _has_existing_vectors(self, company_number: str, transaction_id: Optional[str] = None, document_id: Optional[str] = None) -> bool:
        """
        Check if the CURRENT document already has vectors in database.
        
        FIXED: Now checks for current document vectors, not just any company vectors.
        This prevents skipping document download when old/irrelevant vectors exist.
        
        Args:
            company_number: Company registration number
            transaction_id: Current transaction ID being processed
            document_id: Current document ID being processed
            
        Returns:
            True if CURRENT document vectors exist, False otherwise
        """
        try:
            from app_modules.database.vector_connection import VectorDatabaseConnection
            
            vector_db = VectorDatabaseConnection()
            
            # Check for vectors from the CURRENT document only, not all company documents
            with vector_db.get_connection() as conn:
                cursor = conn.cursor()
                
                if transaction_id:
                    # Check if THIS specific document (by transaction_id) is already vectorized
                    cursor.execute("""
                        SELECT COUNT(*) FROM document_chunks_v2 dc
                        INNER JOIN documents_v2 d ON dc.document_id = d.document_id
                        WHERE d.company_number = ? AND d.transaction_id = ?
                    """, (company_number, transaction_id))
                elif document_id:
                    # Check if THIS specific document (by document_id) is already vectorized
                    cursor.execute("""
                        SELECT COUNT(*) FROM document_chunks_v2 dc
                        INNER JOIN documents_v2 d ON dc.document_id = d.document_id
                        WHERE d.company_number = ? AND d.document_id = ?
                    """, (company_number, document_id))
                else:
                    # No specific document identifier - force fresh processing
                    self.logger.info(f"⚠️ No transaction_id or document_id provided - forcing fresh document processing for {company_number}")
                    return False
                
                result = cursor.fetchone()
                count = result[0] if result else 0

                if count == 0:
                    self.logger.info(f"❌ No vectors found for CURRENT document - will download and process (transaction_id: {transaction_id}, document_id: {document_id})")
                    return False

                # Sanity check: chunks should exceed the page count of the document.
                # The metadata JSON in documents_v2 stores the last chunk's start_page,
                # which gives us the highest page number processed. If chunks <= page_count
                # the vectorization was partial/corrupted and we must re-process.
                try:
                    page_col = "d.transaction_id = ?" if transaction_id else "d.document_id = ?"
                    cursor.execute(f"""
                        SELECT CAST(json_extract(d.metadata, '$.start_page') AS INTEGER)
                        FROM documents_v2 d
                        WHERE d.company_number = ? AND ({page_col})
                        LIMIT 1
                    """, (company_number, transaction_id or document_id))
                    meta_row = cursor.fetchone()
                    max_page = int(meta_row[0]) if meta_row and meta_row[0] else 0

                    if max_page > 0 and count <= max_page:
                        self.logger.warning(
                            f"⚠️ Only {count} chunks for a {max_page}-page document "
                            f"(transaction_id: {transaction_id}) — partial vectorization detected. Re-processing."
                        )
                        return False
                    elif max_page > 0:
                        self.logger.info(f"✅ Chunk count {count} > page count {max_page} — vectorization looks complete")
                    # If max_page == 0 (no page info stored), skip the check and trust the data
                except Exception as _page_check_err:
                    self.logger.debug(f"Page-count sanity check skipped: {_page_check_err}")

                # Validate that stored chunks are real document text, not error-report placeholders
                # from a previous failed extraction run.
                cursor.execute("""
                    SELECT content FROM document_chunks_v2 dc
                    INNER JOIN documents_v2 d ON dc.document_id = d.document_id
                    WHERE d.company_number = ? AND (%s)
                    LIMIT 1
                """ % ("d.transaction_id = ?" if transaction_id else "d.document_id = ?"),
                    (company_number, transaction_id or document_id))
                sample = cursor.fetchone()
                if sample:
                    content = sample[0] or ""
                    is_error_report = (
                        content.startswith("DOCUMENT PROCESSING COMPLETED")
                        or content.startswith("EXTRACTION ATTEMPTS")
                        or "❌ PyPDF2 Standard: Failed" in content
                        or "❌ Local OCR:" in content
                    )
                    if is_error_report:
                        self.logger.warning(
                            f"⚠️ Existing chunks for document (transaction_id: {transaction_id}) "
                            "are error-report placeholders — treating as unprocessed and re-downloading."
                        )
                        return False

                self.logger.info(f"✅ Found {count} valid existing vectors for CURRENT document (transaction_id: {transaction_id}, document_id: {document_id})")
                return True
            
        except Exception as e:
            self.logger.error(f"❌ Error checking existing vectors: {e}")
            return False

    def _execute_fast_path(self, state: Dict[str, Any], company_number: str, 
                          company_name: str, start_time: datetime) -> Dict[str, Any]:
        """
        Execute fast path using existing vectors in database.
        
        Args:
            state: Current workflow state
            company_number: Company registration number
            company_name: Company name
            start_time: When processing started
            
        Returns:
            Updated workflow state with fast extraction results
        """
        try:
            self.logger.info(f"⚡ FAST PATH: Executing direct vector database extraction for {company_name}")

            # Lazy import to avoid circular dependency at module level
            try:
                from ..revenue_agentic_service import AgenticRevenueService as _ARS
                _log = lambda msg, level='info': _ARS.append_log(company_number or '', msg, level)
            except Exception:
                _log = lambda msg, level='info': None

            _log("⚡ Found existing document vectors — skipping re-download and OCR")
            
            if not self.rag_revenue_extractor:
                raise ValueError("RAGRevenueExtractor not initialized")
            
            _log("💬 Querying vector database for revenue figures...")
            # Execute comprehensive hybrid RAG extraction (text-first + similarity)
            rag_results = self.rag_revenue_extractor.extract_revenue(company_number)
            
            if not rag_results.get('success'):
                raise ValueError(f"Fast RAG extraction failed: {rag_results.get('error', 'Unknown error')}")
            
            n_extractions = len(rag_results.get('revenue_extractions', []))
            _log(f"✅ RAG search complete — {n_extractions} revenue figure(s) found")
            
            # Create minimal document processing data for compatibility
            document_processing_data = {
                'download_success': True,
                'chunk_count': len(rag_results.get('source_texts', [])),
                'vector_db_stored': True,
                'embedding_model': 'OpenAI text-embedding-3-small',
                'processing_errors': [],
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'fast_path_used': True,
                'extraction_results': rag_results
            }
            
            # Record workflow decision
            decision = {
                'decision_point': "financial_extraction",
                'decision_type': "fast_path",
                'decision_result': "vector_db_extracted",
                'confidence': rag_results.get('overall_confidence', 0.8),
                'reasoning': f"Used existing vectors, found {len(rag_results.get('revenue_extractions', []))} revenue extractions",
                'timestamp': datetime.now().isoformat()
            }
            
            # Update workflow state
            execution_time = (datetime.now() - start_time).total_seconds()
            
            updated_state = dict(state)
            updated_state['document_processing_data'] = document_processing_data
            
            if 'workflow_decisions' not in updated_state:
                updated_state['workflow_decisions'] = []
            updated_state['workflow_decisions'].append(decision)
            
            if 'node_execution_times' not in updated_state:
                updated_state['node_execution_times'] = {}
            updated_state['node_execution_times']['financial_extraction'] = execution_time
            
            if 'node_confidence_scores' not in updated_state:
                updated_state['node_confidence_scores'] = {}
            updated_state['node_confidence_scores']['financial_extraction'] = rag_results.get('overall_confidence', 0.8)
            
            updated_state['current_node'] = 'turnover_estimation'
            
            self.logger.info(f"⚡ FAST PATH completed in {execution_time:.3f}s ({len(rag_results.get('revenue_extractions', []))} extractions)")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ Fast path execution failed: {e}")
            # Fall back to slow path
            self.logger.info("📄 Falling back to traditional document processing")
            return self._execute_slow_path(state, start_time)
    
    def _execute_slow_path(self, state: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """
        Execute traditional document processing pipeline (slow path).
        
        Args:
            state: Current workflow state
            start_time: When processing started
            
        Returns:
            Updated workflow state with traditional processing results
        """
        try:
            # Extract required data from state
            company_data = state.get('company_filing_data', {})
            if not company_data:
                transaction_id = state.get('transaction_id') or state.get('company_data', {}).get('transaction_id')
                company_name = state.get('company_name')
            else:
                transaction_id = company_data.get('transaction_id')
                company_name = company_data.get('company_name')
                
            company_number = (company_data.get('company_number') or 
                             state.get('company_number') or
                             state.get('company_data', {}).get('company_number'))
            
            # Validate required fields
            if not company_name:
                raise ValueError("Company name is required for document processing")
            if not transaction_id:
                raise ValueError("Transaction ID is required for document processing")

            # Build a complete company_data dict that merges root-level state fields
            # (transaction_id, document_id, company_number, unique_id) with company_filing_data.
            # This is necessary because sequential workflows store these at root level, not nested.
            merged_company_data = dict(company_data)
            for k in ('transaction_id', 'document_id', 'company_number', 'unique_id', 'company_name'):
                if not merged_company_data.get(k) and state.get(k):
                    merged_company_data[k] = state[k]

            # Lazy import to avoid circular dependency at module level
            try:
                from ..revenue_agentic_service import AgenticRevenueService as _ARS
                _log = lambda msg, level='info': _ARS.append_log(company_number or '', msg, level)
            except Exception:
                _log = lambda msg, level='info': None

            # Step 1: Download PDF document
            _log(f"📥 Downloading financial accounts PDF from Companies House...")
            download_result = self._download_financial_document(merged_company_data)
            
            if not download_result.get('success'):
                _log(f"❌ Download failed: {download_result.get('error', 'Unknown error')}", 'error')
                raise ValueError(f"Document download failed: {download_result.get('error')}")
            
            size_mb = download_result.get('document_size', 0) / 1_000_000
            _log(f"✅ PDF downloaded ({size_mb:.1f} MB) — submitting to Azure Document Intelligence...")

            # Step 2: Extract and process text content
            processing_result = self._process_document_content(
                download_result, company_name, transaction_id, company_number
            )
            
            chunk_count = processing_result.get('chunk_count', 0) if hasattr(processing_result, 'get') else 0
            if processing_result.get('success') if hasattr(processing_result, 'get') else False:
                _log(f"✅ OCR extraction complete — {chunk_count} text chunks, generating embeddings...")
            else:
                _log(f"⚠️ Document processing encountered issues — {processing_result.get('error', '')}", 'warning')

            # Step 3: Store in vector database
            vectorization_result = self._vectorize_and_store(
                processing_result, company_name, transaction_id
            )
            
            # Compile document processing data
            document_processing_data = self._compile_processing_results(
                download_result, processing_result, vectorization_result
            )
            
            # Get chunk count for reporting
            chunk_count = processing_result.get('chunk_count', 0) if hasattr(processing_result, 'get') else getattr(processing_result, 'chunk_count', 0)
            chunks_stored = vectorization_result.get('chunks_stored', chunk_count)
            if vectorization_result.get('success'):
                _log(f"✅ {chunks_stored} chunks stored in vector database — starting RAG revenue search...")
            else:
                _log(f"⚠️ Vector storage issue: {vectorization_result.get('error', '')}", 'warning')
            
            # Record workflow decision
            decision = {
                'decision_point': "financial_extraction",
                'decision_type': "processing",
                'decision_result': "document_processed",
                'confidence': vectorization_result.get('confidence', 0.8),
                'reasoning': f"Processed {chunk_count} text chunks",
                'timestamp': datetime.now().isoformat()
            }
            
            # Update workflow state
            execution_time = (datetime.now() - start_time).total_seconds()
            
            updated_state = dict(state)
            updated_state['document_processing_data'] = document_processing_data
            
            if 'workflow_decisions' not in updated_state:
                updated_state['workflow_decisions'] = []
            updated_state['workflow_decisions'].append(decision)
            
            if 'node_execution_times' not in updated_state:
                updated_state['node_execution_times'] = {}
            updated_state['node_execution_times']['financial_extraction'] = execution_time
            
            if 'node_confidence_scores' not in updated_state:
                updated_state['node_confidence_scores'] = {}
            updated_state['node_confidence_scores']['financial_extraction'] = vectorization_result.get('confidence', 0.8)
            
            updated_state['current_node'] = 'turnover_estimation'
            
            self.logger.info(f"✅ Traditional document processing completed in {execution_time:.2f}s")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ Slow path processing failed: {e}")
            
            # Create fallback response
            updated_state = dict(state)
            fallback_data = {
                'download_success': False,
                'chunk_count': 0,
                'vector_db_stored': False,
                'embedding_model': 'none',
                'processing_errors': [str(e)],
                'processing_time': (datetime.now() - start_time).total_seconds()
            }
            
            updated_state['document_processing_data'] = fallback_data
            
            if 'errors' not in updated_state:
                updated_state['errors'] = []
            updated_state['errors'].append(f"Document processing failed: {str(e)}")
            
            updated_state['current_node'] = 'turnover_estimation'  # Continue workflow
            
            return updated_state
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute document processing and vectorization workflow node.
        
        OPTIMIZED: First checks if company documents are already in vector database.
        If yes, skips expensive document processing and goes directly to fast RAG extraction.
        
        Args:
            state: Current revenue workflow state with company filing data
            
        Returns:
            Updated workflow state with document processing results
        """
        start_time = datetime.now()
        self.logger.info("📄 Starting financial document extraction")

        try:
            # Extract required data from previous nodes
            company_data = state.get('company_filing_data', {})
            if not company_data:
                # Sequential workflow format
                transaction_id = state.get('transaction_id') or state.get('company_data', {}).get('transaction_id')
                company_name = state.get('company_name')
            else:
                # LangGraph workflow format
                transaction_id = company_data.get('transaction_id')
                company_name = company_data.get('company_name')
                
            # Extract company_number and document_id with fallback logic
            company_number = (company_data.get('company_number') or 
                            state.get('company_number') or
                            state.get('company_data', {}).get('company_number'))
            
            # Extract document_id for precise vector checking
            document_id = (company_data.get('document_id') or
                          state.get('document_id') or
                          state.get('company_data', {}).get('document_id'))
            
            # Validate required data
            if not company_name:
                raise ValueError("No company_name available in workflow state. Company data ingestion failed.")
            
            if not transaction_id:
                raise ValueError(f"No transaction ID available for {company_name}. Company data ingestion did not complete properly.")
            
            # 🚀 FAST PATH: Check if THIS SPECIFIC DOCUMENT is already vectorized
            if company_number and self._has_existing_vectors(company_number, transaction_id, document_id):
                self.logger.info(f"⚡ FAST PATH: Found existing vectors for CURRENT document (transaction_id: {transaction_id}), skipping document processing")
                return self._execute_fast_path(state, company_number, company_name, start_time)
            
            # SLOW PATH: Continue with traditional document processing
            self.logger.info("📄 Executing traditional document processing pipeline")
            return self._execute_slow_path(state, start_time)
            
        except Exception as e:
            self.logger.error(f"❌ Financial document extraction failed: {str(e)}")
            
            # Handle extraction failure with fallback
            updated_state = dict(state)
            
            # Create fallback document processing data
            fallback_data = {
                'download_success': False,
                'chunk_count': 0,
                'vector_db_stored': False,
                'embedding_model': 'none',
                'processing_errors': [str(e)],
                'processing_time': (datetime.now() - start_time).total_seconds()
            }
            
            updated_state['document_processing_data'] = fallback_data
            
            if 'errors' not in updated_state:
                updated_state['errors'] = []
            updated_state['errors'].append(f"Financial extraction failed: {str(e)}")
            
            if 'fallback_triggers' not in updated_state:
                updated_state['fallback_triggers'] = []
            updated_state['fallback_triggers'].append('document_extraction_failure')
            
            updated_state['current_node'] = 'turnover_estimation'  # Continue to next node with fallback
            
            return updated_state
    
    def _download_financial_document(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download PDF document using document_id from the database.
        
        Now uses direct document_id lookup for efficient downloads.
        """
        self.logger.info("📥 Downloading financial document using document_id")
        
        try:
            # Get document_id from company data (should be available from database)
            document_id = company_data.get('document_id')
            company_name = company_data.get('company_name', 'Unknown Company')
            
            if not document_id:
                # If document_id not provided, try to get it from database
                unique_id = company_data.get('unique_id')
                transaction_id = company_data.get('transaction_id')
                
                if unique_id and transaction_id:
                    # Query database for document_id
                    from app_modules.database.connection import DatabaseConnection
                    
                    db_connection = DatabaseConnection()
                    with db_connection.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT document_id FROM company_filing_history_accounts 
                            WHERE unique_id = ? AND transaction_id = ?
                        ''', (unique_id, transaction_id))
                        result = cursor.fetchone()
                        
                        if result and result[0]:
                            document_id = result[0]
                            self.logger.info(f"Retrieved document_id from database: {document_id}")
                        else:
                            raise ValueError(f"No document_id found for {unique_id}, transaction: {transaction_id}")
                else:
                    raise ValueError("Document ID not available and cannot retrieve from database")
            
            # Use new direct download method
            downloaded_doc = self.document_agent.download_by_document_id(document_id, company_name)
            
            if downloaded_doc:
                return {
                    'success': True,
                    'document_path': f'memory:{document_id}',  # In-memory reference
                    'document_size': downloaded_doc.file_size,
                    'document_content': downloaded_doc.content,
                    'document_id': document_id,
                    'download_timestamp': downloaded_doc.download_timestamp.isoformat(),
                    'content_hash': downloaded_doc.content_hash
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to download document {document_id}'
                }
                
        except Exception as e:
            self.logger.error(f"Document download failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_document_content(self, download_result: Dict[str, Any], 
                                company_name: str, transaction_id: str, 
                                company_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Process document content for text extraction and chunking.
        
        Now handles in-memory document content from direct downloads.
        """
        self.logger.info("🔤 Processing document text content")
        
        try:
            document_content = download_result.get('document_content')
            document_id = download_result.get('document_id', '')
            
            if not document_content:
                return {
                    'success': False,
                    'error': 'No document content available for processing'
                }
            
            # Create a temporary file for RAG processing if needed
            import tempfile
            temp_file_path = None
            
            try:
                # Create temporary file for RAG agent processing
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(document_content)
                    temp_file_path = temp_file.name
                
                # Process document using enhanced processor with metadata (includes enhanced page scanning)
                # Ensure company_number is provided for proper processing
                if not company_number:
                    raise ValueError("Company number is required for document processing")
                    
                processing_result = self.document_processor.process_document_with_metadata(
                    document_id=document_id,
                    company_name=company_name,
                    company_number=company_number,
                    transaction_id=transaction_id
                )
                
                if processing_result.success:
                    # Query for revenue-related information
                    revenue_query = SemanticQuery(
                        query_text="revenue turnover sales income",
                        query_type="financial_extraction",
                        expected_data_type="numeric",
                        context_window=3
                    )
                    
                    # Perform semantic search
                    rag_result = self.document_processor.query_document(revenue_query, document_id)
                    
                    return {
                        'success': True,
                        'extracted_text': f"Processed {processing_result.chunk_count} chunks",
                        'text_chunks': rag_result.relevant_chunks,
                        'chunk_count': processing_result.chunk_count,
                        'processing_metadata': {
                            'embedding_count': processing_result.embedding_count,
                            'processing_time': processing_result.processing_time,
                            'confidence': rag_result.confidence,
                            'extracted_data': rag_result.extracted_data
                        },
                        'document_id': document_id
                    }
                else:
                    return {
                        'success': False,
                        'error': processing_result.error_message or 'Document processing failed'
                    }
            
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                
        except Exception as e:
            self.logger.error(f"Document processing error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _vectorize_and_store(self, processing_result: Dict[str, Any],
                           company_name: str, transaction_id: str) -> Dict[str, Any]:
        """
        Vectorize text chunks and store in vector database using proper VectorDatabaseConnection.
        
        Since AgenticDocumentProcessor already handles vectorization, we just validate success.
        """
        self.logger.info("🗂️  Vectorizing and storing document chunks")
        
        try:
            # Check if AgenticDocumentProcessor already completed vectorization
            # Handle both dict and object response types
            success = processing_result.get('success') if hasattr(processing_result, 'get') else getattr(processing_result, 'success', False)
            chunk_count = processing_result.get('chunk_count', 0) if hasattr(processing_result, 'get') else getattr(processing_result, 'chunk_count', 0)
            
            self.logger.info(f"🐛 DEBUG: processing_result type={type(processing_result)}")
            self.logger.info(f"🐛 DEBUG: has get method={hasattr(processing_result, 'get')}")
            self.logger.info(f"🐛 DEBUG: extracted success={success}, chunk_count={chunk_count}")
            
            if success and chunk_count > 0:
                # AgenticDocumentProcessor already handled vectorization successfully
                self.logger.info(f"✅ Document processor already vectorized {chunk_count} chunks")
                self.logger.info(f"🐛 DEBUG: processing_result success={success}, chunk_count={chunk_count}")
                return {
                    'success': True,
                    'vector_collection_id': f"revenue_{company_name.replace(' ', '_').lower()}_{transaction_id.replace(' ', '_').lower()}",
                    'chunks_stored': chunk_count,
                    'total_chunks': chunk_count,
                    'confidence': 0.8,
                    'embedding_model': 'OpenAI text-embedding-3-small',
                    'storage_errors': []
                }
            # If processing failed, return failure
            if not success:
                return {
                    'success': False,
                    'error': 'Cannot vectorize - document processing failed'
                }
            
            # If no chunks, return failure  
            if chunk_count == 0:
                return {
                    'success': False,
                    'error': 'No text chunks available for vectorization'
                }
            
            # Processing successful but no vectorization needed - already done by AgenticDocumentProcessor
            return {
                'success': False,
                'error': 'AgenticDocumentProcessor vectorization not properly detected'
            }
            
        except Exception as e:
            self.logger.error(f"Vectorization error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'confidence': 0.0
            }
    
    def _compile_processing_results(self, download_result: Dict[str, Any],
                                  processing_result: Dict[str, Any],
                                  vectorization_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compile all processing results into document processing data."""
        
        return {
            # Document download information
            'document_url': download_result.get('document_url'),
            'document_size': download_result.get('document_size', 0),
            'download_success': download_result.get('success', False),
            'download_timestamp': download_result.get('download_timestamp'),
            
            # Text extraction results  
            'extracted_text': processing_result.get('extracted_text') if hasattr(processing_result, 'get') else getattr(processing_result, 'extracted_text', None),
            'text_chunks': processing_result.get('text_chunks', []) if hasattr(processing_result, 'get') else getattr(processing_result, 'text_chunks', []),
            'chunk_count': processing_result.get('chunk_count', 0) if hasattr(processing_result, 'get') else getattr(processing_result, 'chunk_count', 0),
            'page_count': processing_result.get('page_count', 0) if hasattr(processing_result, 'get') else getattr(processing_result, 'page_count', 0),
            
            # Vector database integration
            'vector_db_stored': vectorization_result.get('success', False),
            'vector_collection_id': vectorization_result.get('vector_collection_id'),
            'embedding_model': vectorization_result.get('embedding_model', 'openai'),
            
            # Processing metadata
            'processing_errors': self._collect_all_errors(download_result, processing_result, vectorization_result),
            'processing_time': 0.0  # Will be set by caller
        }
    
    def _collect_all_errors(self, *results: Dict[str, Any]) -> List[str]:
        """Collect all errors from processing steps."""
        all_errors = []
        
        for result in results:
            if not result.get('success', True):
                error = result.get('error')
                if error:
                    all_errors.append(error)
            
            # Collect storage errors if present
            storage_errors = result.get('storage_errors', [])
            if storage_errors:
                all_errors.extend(storage_errors)
        
        return all_errors
    
    def extract_revenue_with_financial_rag(self, document_chunks: List[Dict[str, Any]], 
                                          company_registration_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract revenue using FAST Financial RAG Engine with vector database optimization.
        
        Args:
            document_chunks: List of document chunks with text and metadata (for fallback)
            company_registration_number: Company registration number for fast vector search
            
        Returns:
            Revenue extraction results with enhanced confidence scoring
        """
        if not self.rag_revenue_extractor:
            self.logger.error("❌ STRICT CONTROL: RAG Revenue Extractor not available - agentic workflow cannot proceed")
            raise ValueError("CRITICAL: RAG Revenue Extractor must be initialized for agentic workflow. Check database paths and dependencies.")
        
        try:
            self.logger.info("🔍 Starting Hybrid RAG revenue extraction")
            
            # Use Hybrid RAG method if company registration number is available
            if company_registration_number:
                self.logger.info(f"🚀 Using hybrid RAG extraction for company {company_registration_number}")
                rag_results = self.rag_revenue_extractor.extract_revenue(company_registration_number)
            else:
                # Fallback to document chunks if no company number (should rarely happen)
                self.logger.warning("⚠️ No company registration number, falling back to document processing")
                raise Exception("Company registration number required for fast RAG")
            
            if rag_results.get('success'):
                self.logger.info(f"✅ Financial RAG extraction successful: {rag_results.get('overall_confidence', 0):.2f} confidence")
                
                # Extract the best revenue information
                best_extraction = self._find_best_revenue_extraction(rag_results.get('revenue_extractions', []))
                
                # Use enhanced source texts from FastFinancialRAG (with GAAP/IFRS indicators)
                source_text_preview = rag_results.get('source_texts', [])
                
                return {
                    'success': True,
                    'extraction_method': 'financial_rag',
                    'extracted_revenue': best_extraction.get('response', '') if best_extraction else '',
                    'confidence_score': rag_results.get('overall_confidence', 0.0),
                    'rag_results': rag_results,
                    'sources_count': len(best_extraction.get('sources', [])) if best_extraction else 0,
                    'revenue_source_text': source_text_preview,  # NEW: Source text for UI display
                    'timestamp': datetime.now().isoformat()
                }
            else:
                self.logger.error("❌ STRICT CONTROL: Financial RAG extraction failed - no fallback allowed")
                raise ValueError(f"RAG extraction failed: {rag_results.get('error', 'Unknown error')}. Document must be properly processed and vectorized.")
                
        except Exception as e:
            self.logger.error(f"❌ STRICT CONTROL: Financial RAG extraction error - no fallback allowed: {e}")
            raise ValueError(f"RAG extraction system error: {e}. Check database connections and document processing pipeline.")

    def _extract_source_text_preview(self, best_extraction: Optional[Dict[str, Any]]) -> List[str]:
        """
        Extract 3-4 lines of source text showing where revenue figures were found.
        
        Args:
            best_extraction: Best revenue extraction result from RAG
            
        Returns:
            List of text snippets (3-4 lines each) showing revenue context
        """
        if not best_extraction or not best_extraction.get('sources'):
            return []
        
        source_previews = []
        sources = best_extraction.get('sources', [])
        
        # Extract preview text from top 2-3 sources
        for i, source in enumerate(sources[:3]):  # Limit to top 3 sources
            if 'text' in source:
                # Split text into sentences and take meaningful chunks
                text = source['text']
                similarity = source.get('similarity', 0)
                
                # Split by sentences and take 3-4 lines around revenue-relevant content
                sentences = [s.strip() for s in text.replace('\n', '. ').split('.') if s.strip()]
                
                # Take first 3-4 sentences as a preview
                preview_sentences = sentences[:4] if len(sentences) >= 4 else sentences
                preview_text = '. '.join(preview_sentences)
                
                # Ensure reasonable length (not too long for UI)
                if len(preview_text) > 300:
                    preview_text = preview_text[:300] + "..."
                
                source_previews.append({
                    'text': preview_text,
                    'similarity_score': similarity,
                    'source_index': i + 1
                })
        
        return source_previews

    def _find_best_revenue_extraction(self, extractions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the revenue extraction with highest confidence."""
        if not extractions:
            return None
        
        # Filter out failed extractions
        valid_extractions = [e for e in extractions if 'error' not in e and e.get('confidence', 0) > 0.3]
        
        if not valid_extractions:
            return None
        
        # Return extraction with highest confidence
        return max(valid_extractions, key=lambda x: x.get('confidence', 0))
    
    def _fallback_revenue_extraction(self, document_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        STRICT CONTROL: NO FALLBACK MECHANISM ALLOWED.
        
        This method previously created misleading fake chunks when the RAG system failed.
        Now it strictly requires proper document processing and vectorization.
        
        If this method is called, it means the system is not working properly and should fail explicitly.
        """
        self.logger.error("❌ STRICT CONTROL: Fallback revenue extraction called - this indicates system failure")
        self.logger.error("❌ The agentic workflow must work with proper document download and vectorization")
        self.logger.error("❌ No fake chunks or keyword extraction allowed - failing explicitly")
        
        return {
            'success': False,
            'extraction_method': 'strict_failure',
            'extracted_revenue': '',
            'confidence_score': 0.0,
            'error': 'STRICT CONTROL: Agentic workflow requires proper document processing and vectorization. Fallback mechanisms disabled to prevent misleading results.',
            'revenue_source_text': [],
            'timestamp': datetime.now().isoformat(),
            'system_message': 'The document must be properly downloaded from Companies House and fully vectorized before revenue extraction can proceed.'
        }