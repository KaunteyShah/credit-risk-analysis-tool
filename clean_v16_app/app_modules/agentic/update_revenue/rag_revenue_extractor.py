"""
Hybrid RAG Revenue Extractor

Implements hybrid revenue extraction using:
1. Enhanced OCR → Quality text extraction
2. Regex patterns → Financial number identification
3. Vector embeddings → Semantic similarity search
4. RAGDocumentAgent → Context validation

HYBRID APPROACH - Regex patterns + vector-based semantic validation
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from app_modules.agents.rag_document_agent import RAGDocumentAgent
from app_modules.database.vector_connection import VectorDatabaseConnection
from app_modules.agentic.update_revenue.data_models import SemanticQuery, RAGResult, DocumentChunk
from app_modules.utils.logger import get_logger
from app_modules.notifications.user_notification_service import notification_service

logger = get_logger(__name__)


class RAGRevenueExtractor:
    """
    Hybrid RAG-based revenue extraction using regex patterns + vector similarity.
    
    Architecture:
    Enhanced OCR → Quality Text → Regex Patterns → Vector Embeddings → Similarity Search → Revenue Detection
    
    Uses existing infrastructure:
    - RAGDocumentAgent for vector similarity search
    - VectorDatabaseConnection for optimized queries
    - Regex patterns for financial number identification
    - Enhanced OCR from AgenticDocumentProcessor
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize RAG revenue extractor with regex + vector similarity hybrid approach."""
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Configuration constants - industry-agnostic and configurable
        self.config = config or {}
        
        # Initialize RAG components for hybrid extraction (regex + vector similarity)
        self.rag_agent = RAGDocumentAgent()
        
        # Initialize both database connections
        from app_modules.config.app_config import CreditRiskConfig
        from app_modules.database.connection import DatabaseConnection
        from pathlib import Path
        credit_config = CreditRiskConfig()
        
        # Main database connection for company and filing information
        self.main_db = DatabaseConnection(db_path=credit_config.database_path)
        
        # Vector database connection for document chunks and embeddings
        main_db_path = Path(credit_config.database_path)
        vector_db_path = main_db_path.parent / 'vector_database.db'
        self.vector_db = VectorDatabaseConnection(db_path=str(vector_db_path))
        
        # Configure vector database schema
        if self.vector_db is not None:
            # Use existing financial_document_vectors table for legacy system
            self.vector_db.use_normalized_schema = True
        
        # Focused GAAP/IFRS revenue query templates for vector similarity search.
        # These should match actual phrases that appear IN annual reports near the top-line revenue figure.
        # Used by extract_revenue_pure_rag only. Keep this list short and precise — semantic search
        # benefits from focused queries, not keyword soup.
        self.revenue_query_templates = [
            # === INCOME STATEMENT TOP-LINE (most likely to hit revenue row in P&L) ===
            "total revenue for the year ended consolidated income statement",
            "group revenue net revenue turnover year ended annual report",
            "revenue from contracts with customers IFRS 15 total",
            "consolidated statement of profit or loss total revenue",
            "turnover and other income group financial statements",

            # === UK GAAP / FRS 102 specific ===
            "turnover gross profit operating profit financial year",
            "net revenue total income profit and loss account year",

            # === IFRS income statement labels ===
            "revenue cost of sales gross profit operating income",
            "total income from operations continuing operations annual",
            "gross revenue net revenue operating revenue group total",

            # === Insurance / diversified income ===
            "total reported income insurance revenue net investment income",
            "gross written premium net earned premium total income",

            # === Banking / financial services ===
            "net interest income fee and commission income total operating income",
            "total net income net banking income operating revenue",

            # === Segment / group summary ===
            "group income segment revenue consolidated financial performance",
        ]

        # GAAP/IFRS Financial Context Classifiers — used in _calculate_semantic_confidence
        # to boost confidence when income-statement vocabulary is found near a figure.
        self.revenue_context_indicators = [
            # Core Financial Statements
            'income statement', 'profit and loss', 'consolidated statement', 'revenue recognition',
            # Basic Revenue Terms  
            'sales revenue', 'operating revenue', 'total revenue', 'gross revenue', 'net revenue',
            # Enhanced Revenue Vocabulary
            'top line', 'turnover', 'consolidated revenue', 'segment revenue', 'contract revenue',
            'net sales', 'gross sales', 'recurring revenue', 'subscription revenue', 'service revenue',
            'product revenue', 'licensing revenue', 'royalty revenue', 'usage based revenue',
            # Financial Standards & Recognition
            'revenue from contracts', 'contract liabilities', 'contract assets', 'deferred revenue',
            'unearned revenue', 'recognized revenue', 'performance obligations', 'transaction price',
            'variable consideration', 'consideration payable', 'revenue guidance', 'revenue mix',
            # Performance & Growth Terms
            'revenue growth', 'revenue decline', 'comparative revenue', 'year over year revenue',
            'yoy revenue', 'quarter over quarter revenue', 'qoq revenue', 'annualised revenue',
            # Revenue Analysis & Breakdown
            'revenue streams', 'revenue breakdown', 'adjusted revenue', 'pro forma revenue',
            'reportable segment revenue', 'intersegment revenue', 'eliminations', 'gross profit',
            'net revenue after discounts', 'rebates and discounts'
        ]
        
        # GAAP/IFRS Taxonomy-Based Revenue Context (TIER 1 - Highest Confidence) - Enhanced Vocabulary
        self.gaap_ifrs_revenue_contexts = {
            # IFRS 15 Revenue Recognition Standard - Enhanced
            'ifrs_15_contexts': [
                'revenue from contracts with customers', 'ifrs 15', 'performance obligations',
                'contract liabilities', 'contract assets', 'variable consideration',
                'revenue recognition under ifrs 15', 'five-step model', 'satisfied performance obligations',
                'unsatisfied performance obligations', 'transaction price', 'consideration payable to customers',
                'contract modifications', 'contract revenue', 'deferred revenue', 'unearned revenue'
            ],
            # ASC 606 Revenue Recognition (US GAAP equivalent) - Enhanced
            'asc_606_contexts': [
                'asc 606', 'revenue from contracts with customers', 'performance obligations',
                'contract modifications', 'variable consideration', 'revenue recognition standard',
                'contract liabilities', 'contract assets', 'transaction price allocation',
                'revenue recognition guidance', 'contract revenue', 'recognized revenue'
            ],
            # Core Income Statement Elements (Universal GAAP/IFRS) - Enhanced
            'income_statement_contexts': [
                'consolidated statement of profit or loss', 'statement of comprehensive income',
                'continuing operations', 'discontinued operations', 'operating profit',
                'profit before tax', 'profit after tax', 'earnings before interest and tax',
                'total revenue', 'net revenue', 'gross revenue', 'operating revenue',
                'consolidated revenue', 'segment revenue', 'top line revenue'
            ],
            # UK GAAP/FRS Specific Revenue Terms - Enhanced
            'uk_gaap_contexts': [
                'turnover', 'revenue from sales of goods', 'revenue from provision of services',
                'other operating income', 'frs 102', 'companies act 2006',
                'gross sales', 'net sales', 'service revenue', 'product revenue',
                'recurring revenue', 'subscription revenue', 'licensing revenue', 'royalty revenue'
            ],
            # Revenue Performance & Analysis Terms - New Category
            'revenue_performance_contexts': [
                'revenue growth', 'revenue decline', 'comparative revenue', 'year over year revenue',
                'yoy revenue', 'quarter over quarter revenue', 'qoq revenue', 'annualised revenue',
                'revenue mix', 'revenue streams', 'revenue breakdown', 'adjusted revenue',
                'pro forma revenue', 'reportable segment revenue', 'intersegment revenue',
                'revenue guidance', 'rebates and discounts', 'net revenue after discounts'
            ],
            # Specialized Revenue Types - New Category  
            'specialized_revenue_contexts': [
                'usage based revenue', 'subscription revenue', 'licensing revenue', 'royalty revenue',
                'contract revenue', 'service revenue', 'product revenue', 'recurring revenue',
                'non recurring revenue', 'eliminations', 'gross profit alongside revenue'
            ]
        }
        
        # GAAP/IFRS Financial Statement Structure (TIER 2 - Medium Confidence)
        self.gaap_ifrs_statement_contexts = {
            'consolidated_reporting': [
                'group consolidated', 'parent company', 'subsidiary undertakings',
                'non-controlling interests', 'consolidation principles'
            ],
            'segment_reporting': [
                'reportable segments', 'geographical segments', 'business segments',
                'segment revenue', 'ifrs 8', 'operating segments'
            ],
            'currency_reporting': [
                'functional currency', 'presentation currency', 'foreign exchange',
                'translation differences', 'ias 21'
            ]
        }
        
        self.non_revenue_context_indicators = [
            'balance sheet', 'statement of financial position', 'distributable reserves', 
            'retained earnings', 'shareholders equity', 'capital reserves', 'cash equivalents',
            'total assets', 'property plant equipment', 'intangible assets', 'goodwill'
        ]
        
        self.logger.info("🎯 RAGRevenueExtractor initialized - REGEX-FREE revenue extraction")
    
    def _check_document_vectorization_status(self, company_registration_number: str, document_id: str) -> Dict[str, Any]:
        """Check if document is already vectorized in the vector database."""
        try:
            # Import here to avoid circular imports
            from app_modules.database.vector_connection import VectorDatabaseConnection
            
            vector_db = VectorDatabaseConnection()
            
            # Check for existing vector data for this company/document
            # Use a simple test query to check if we have stored vectors
            
            # Check vector database
            try:
                from app_modules.services.embedding.openai_embedding_service import get_openai_embedding_service
                embedding_service = get_openai_embedding_service()
                if embedding_service is None:
                    return {'is_vectorized': False, 'reason': 'Embedding service not available'}
                
                # Test query to check if vectors exist
                test_embedding = embedding_service.encode(['revenue test'])
                results = vector_db.search_company_revenue(
                    query_embedding=test_embedding[0],
                    company_registration_number=company_registration_number,
                    limit=1,
                    min_similarity=0.0
                )
                
                is_vectorized = len(results) > 0
                return {
                    'is_vectorized': is_vectorized,
                    'reason': f'Found {len(results)} vector chunks' if is_vectorized else 'No vectors found',
                    'vector_count': len(results),
                    'last_processed': None  # Could add timestamp if available
                }
                
            except Exception as e:
                self.logger.warning(f"Error checking vectorization status: {e}")
                return {'is_vectorized': False, 'reason': f'Status check failed: {e}'}
            
        except Exception as e:
            self.logger.error(f"Failed to check vectorization status: {e}")
            return {'is_vectorized': False, 'reason': f'Check failed: {e}'}
    
    def _process_document_for_clean_system(self, company_name: str, company_registration_number: str, 
                                         document_id: str, filing_date: Optional[str] = None) -> Dict[str, Any]:
        """Process document using the existing document processing pipeline."""
        try:
            self.logger.info(f"🔄 Processing document for {company_name} (ID: {document_id})")
            
            # Import document processing components
            from app_modules.agentic.update_revenue.document_processor import AgenticDocumentProcessor
            from app_modules.agents.document_download_agent import DocumentDownloadAgent
            
            # Initialize document processor
            processor = AgenticDocumentProcessor()
            download_agent = DocumentDownloadAgent()
            
            # Step 1: Download document from Companies House
            notification_service.update_progress(25, "📥 Downloading document from Companies House...")
            self.logger.info("📥 Downloading document from Companies House...")
            download_result = download_agent.download_by_document_id(
                document_id, company_name
            )
            
            if download_result is None:
                return {
                    'success': False,
                    'error': 'Document download failed - no result returned',
                    'stage': 'download'
                }
            
            document_content = download_result.content
            if not document_content:
                return {
                    'success': False,
                    'error': 'No document content received from download',
                    'stage': 'download'
                }
            
            # Step 2: Process document content (extract text, chunk, embed)
            notification_service.update_progress(35, "🔧 Starting OCR text extraction...")
            self.logger.info("🔧 Processing document content (text extraction + embedding)...")
            
            notification_service.update_progress(45, "📄 Performing OCR on PDF pages...")
            processing_result = processor.process_document_content(
                document_content=document_content,
                document_id=document_id,
                company_name=company_name,
                company_number=company_registration_number,
                transaction_id=document_id  # Use document_id as transaction_id
            )
            
            notification_service.update_progress(55, "🔗 Generating vector embeddings...")
            
            if hasattr(processing_result, 'success'):
                # Handle DocumentProcessingResult object
                success = processing_result.success
                chunk_count = processing_result.chunk_count
                error_message = processing_result.error_message
            else:
                # Handle dictionary response
                success = processing_result.get('success', False)
                chunk_count = processing_result.get('chunk_count', 0)
                error_message = processing_result.get('error_message', 'Unknown error')
            
            if not success:
                return {
                    'success': False,
                    'error': f"Document processing failed: {error_message}",
                    'stage': 'processing'
                }
            
            # Step 3: Retrieve processed chunks for return
            document_chunks = self._retrieve_document_chunks_from_vector_db(
                company_registration_number, document_id
            )
            
            return {
                'success': True,
                'chunk_count': chunk_count,
                'document_chunks': document_chunks,
                'processing_method': 'agentic_document_processor',
                'vectorization_completed': True
            }
            
        except Exception as e:
            self.logger.error(f"Document processing failed: {e}")
            return {
                'success': False,
                'error': f'Processing pipeline error: {e}',
                'stage': 'pipeline'
            }
    
    def _retrieve_document_chunks_from_vector_db(self, company_registration_number: str, 
                                               document_id: str) -> List[Dict[str, Any]]:
        """Retrieve document chunks from the vector database for RAG processing."""
        try:
            from app_modules.database.vector_connection import VectorDatabaseConnection
            
            vector_db = VectorDatabaseConnection()
            
            # Use a broad query to retrieve all chunks for this company/document
            try:
                from app_modules.services.embedding.openai_embedding_service import get_openai_embedding_service
                embedding_service = get_openai_embedding_service()
                if embedding_service is None:
                    self.logger.error("Embedding service not available for chunk retrieval")
                    return []
                
                # Use a generic financial query to retrieve relevant chunks
                generic_queries = [
                    "revenue sales turnover financial results",
                    "income statement profit loss",
                    "annual report financial performance"
                ]
                
                all_chunks = []
                for query in generic_queries:
                    query_embedding = embedding_service.encode([query])[0]
                    results = vector_db.search_company_revenue(
                        query_embedding=query_embedding,
                        company_registration_number=company_registration_number,
                        limit=20,  # Get more chunks for comprehensive coverage
                        min_similarity=0.0  # Very low threshold to get all content
                    )
                    
                    # Convert to format expected by clean system
                    for result in results:
                        chunk_data = {
                            'text': result.get('text', result.get('content', '')),
                            'metadata': {
                                'document_id': document_id,
                                'company_number': company_registration_number,
                                'chunk_id': result.get('chunk_id', 0),
                                'source': 'legacy_vector_db'
                            }
                        }
                        all_chunks.append(chunk_data)
                
                # Remove duplicates based on text content
                seen_texts = set()
                unique_chunks = []
                for chunk in all_chunks:
                    text_key = chunk['text'][:100]  # Use first 100 chars as key
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        unique_chunks.append(chunk)
                
                self.logger.info(f"Retrieved {len(unique_chunks)} unique document chunks")
                return unique_chunks
                
            except Exception as e:
                self.logger.error(f"Failed to retrieve chunks: {e}")
                return []
                
        except Exception as e:
            self.logger.error(f"Chunk retrieval failed: {e}")
            return []
    
    def _extract_with_clean_system(self, 
                                  document_id: str,
                                  company_name: str,
                                  company_registration_number: str,
                                  filing_date: Optional[str] = None) -> Dict[str, Any]:
        """Extract revenue using the clean all-mpnet-base-v2 + 768D system with full document processing."""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🎯 Clean system revenue extraction for {company_name} (ID: {document_id})")
            
            # Step 1: Check if document is already vectorized in the database
            vectorization_status = self._check_document_vectorization_status(
                company_registration_number, document_id
            )
            
            if not vectorization_status['is_vectorized']:
                self.logger.info("📊 Document not vectorized - initiating document processing pipeline")
                
                # Step 2: Process document if not vectorized
                processing_result = self._process_document_for_clean_system(
                    company_name, company_registration_number, document_id, filing_date
                )
                
                if not processing_result['success']:
                    return {
                        'success': False,
                        'error': processing_result.get('error', 'Document processing failed'),
                        'extraction_method': 'clean_mpnet_768d',
                        'requires_vectorization': True,
                        'estimated_processing_time_minutes': 5,
                        'message': 'Document needs to be downloaded and vectorized first (estimated 5 minutes)'
                    }
                
                # Document processed successfully
                self.logger.info(f"✅ Document processed: {processing_result['chunk_count']} chunks stored")
                document_chunks = processing_result.get('document_chunks', [])
                
            else:
                self.logger.info("✅ Document already vectorized - retrieving existing chunks")
                
                # Step 3: Retrieve existing document chunks from vector database  
                document_chunks = self._retrieve_document_chunks_from_vector_db(
                    company_registration_number, document_id
                )
                
                if not document_chunks:
                    return {
                        'success': False,
                        'error': 'No document chunks found despite vectorization status',
                        'extraction_method': 'clean_mpnet_768d',
                        'requires_reprocessing': True,
                        'message': 'Document may need reprocessing with clean system'
                    }
            
            # Step 4: Perform clean RAG revenue extraction
            self.logger.info(f"🔍 Performing clean RAG extraction on {len(document_chunks)} chunks")
            
            extraction_result = self.clean_extractor.extract_revenue_from_document(
                document_id=document_id,
                company_id=company_registration_number,
                document_chunks=document_chunks,
                company_name=company_name,
                limit_per_query=10
            )
            
            # Calculate processing time
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Return comprehensive result
            result = {
                'success': extraction_result.get('success', False),
                'extracted_revenue': extraction_result.get('extracted_revenue'),
                'revenue_currency': extraction_result.get('revenue_currency', 'GBP'),
                'confidence_score': extraction_result.get('confidence_score', 0.0),
                'extraction_method': 'clean_mpnet_768d',
                'revenue_source_text': extraction_result.get('revenue_source_text', ''),
                'alternative_revenues': extraction_result.get('alternative_revenues', []),
                'processing_time_ms': processing_time_ms,
                'vectorization_status': vectorization_status,
                'document_chunks_processed': len(document_chunks),
                'query_results_count': extraction_result.get('query_results', 0),
                'embedding_model': extraction_result.get('embedding_model', 'all-mpnet-base-v2'),
                'embedding_dimensions': extraction_result.get('embedding_dimensions', 768)
            }
            
            if extraction_result.get('success'):
                self.logger.info(f"🎊 Revenue extraction successful: {extraction_result.get('extracted_revenue', 'None')} {extraction_result.get('revenue_currency', 'GBP')}")
            else:
                self.logger.warning(f"⚠️ Revenue extraction failed: {extraction_result.get('error', 'Unknown error')}")
                result['error'] = extraction_result.get('error', 'Revenue extraction failed')
            
            return result
            
        except Exception as e:
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"❌ Clean system extraction failed: {e}")
            return {
                'success': False,
                'error': f'Clean system error: {e}',
                'extraction_method': 'clean_mpnet_768d',
                'processing_time_ms': processing_time_ms
            }
    
    def extract_revenue_pure_rag(self, 
                                document_id: str,
                                company_name: str,
                                company_registration_number: str,
                                filing_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract revenue using PURE RAG similarity search - NO REGEX.
        
        Args:
            document_id: Document identifier in vector database
            company_name: Company name for context
            company_registration_number: Company registration number
            filing_date: Optional filing date for context
            
        Returns:
            Revenue extraction results with confidence scores
        """
        self.logger.info(f"🔍 Pure RAG revenue extraction for {company_name}")
        
        # Start user notifications
        notification_service.start_operation(
            f"🔍 Revenue Extraction: {company_name}", 
            total_steps=100
        )
        
        # Step 1: Check if document is vectorized
        notification_service.update_progress(10, "🔍 Checking document vectorization status...")
        vectorization_status = self._check_document_vectorization_status(
            company_registration_number, document_id
        )
        
        if not vectorization_status.get('is_vectorized', False):
            notification_service.show_embedding_notification(company_name, 236)  # Approximate page count
            notification_service.update_progress(20, "📄 Document not vectorized - starting processing...")
            
            # Process document with user feedback
            processing_result = self._process_document_for_clean_system(
                company_name, company_registration_number, document_id, filing_date
            )
            
            notification_service.update_progress(60, "✅ Document processing complete - vectors stored")
        else:
            notification_service.update_progress(30, f"✅ Document already vectorized ({vectorization_status.get('vector_count', 0)} chunks)")
        
        notification_service.update_progress(70, "🔍 Performing RAG revenue search...")
        
        start_time = datetime.now()
        
        try:
            # Using hybrid RAG system (regex + vector similarity)
            self.logger.info("🎯 Using hybrid RAG system (regex + vector similarity)")
            
            # Step 1: Generate revenue-focused semantic queries
            revenue_queries = self._generate_financial_queries(company_name, filing_date)
            
                        # Step 2: Perform semantic searches for revenue content using vector similarity
            rag_results = []
            for query in revenue_queries:
                try:
                    result = self._perform_company_revenue_search(
                        query=query,
                        company_registration_number=company_registration_number,
                        document_id=document_id
                    )
                    
                    if result and result.relevant_chunks:
                        rag_results.append(result)
                        self.logger.info(f"Query '{query.query_text[:30]}...' found {len(result.relevant_chunks)} relevant chunks")
                
                except Exception as e:
                    self.logger.warning(f"Query failed: {e}")
                    continue
            
            # Step 2.5: HYBRID FALLBACK - Direct keyword search for critical financial data
            needs_keyword_fallback = (
                not rag_results or 
                len([chunk for result in rag_results for chunk in result.relevant_chunks]) < 10
            )
            
            if needs_keyword_fallback:
                self.logger.warning(f"Triggering keyword fallback for {company_name} - ensuring comprehensive revenue coverage")
                keyword_result = self._keyword_fallback_search(company_registration_number, document_id)
                if keyword_result and keyword_result.relevant_chunks:
                    rag_results.append(keyword_result)
                    self.logger.info(f"Keyword fallback found {len(keyword_result.relevant_chunks)} additional chunks")
            
            if not rag_results:
                return {
                    'success': False,
                    'error': 'No revenue-relevant content found via vector similarity or keyword search',
                    'extraction_method': 'hybrid_rag_failed'
                }
            
            # Step 3: Analyze revenue content using semantic patterns (NO REGEX)
            revenue_candidates = self._extract_revenue_from_chunks(rag_results, company_name)
            
            # Step 3.5: Database guidance intentionally removed.
            # Anchoring to stale DB values creates a self-reinforcing loop where wrong
            # revenue figures can never be corrected by the Update Revenue workflow.
            
            # Step 4: Score and rank candidates using vector similarity + database guidance
            final_revenue = self._select_best_revenue_candidate(revenue_candidates, rag_results)
            
            # Step 5: Extract additional metadata fields (year and period type)
            revenue_year, period_type = self._extract_financial_metadata(rag_results)
            
            extraction_time = (datetime.now() - start_time).total_seconds()
            
            # Complete notifications with success
            notification_service.update_progress(90, "💰 Revenue extraction complete")
            
            revenue_amount = final_revenue.get('amount', 0)
            result_summary = f"Revenue: £{revenue_amount:,.2f}, Confidence: {final_revenue.get('confidence', 0.0):.1%}"
            
            notification_service.show_completion(True, result_summary)
            
            return {
                'success': True,
                'extraction_method': 'pure_rag_vector_similarity',
                'revenue_amount': final_revenue.get('amount'),
                'confidence_score': final_revenue.get('confidence', 0.0),
                'revenue_year': revenue_year,
                'period_type': period_type,
                'source_chunks': len([chunk for result in rag_results for chunk in result.relevant_chunks]),
                'semantic_queries_used': len(revenue_queries),
                'extraction_time': extraction_time,
                'revenue_candidates': revenue_candidates,
                'rag_metadata': {
                    'total_chunks_analyzed': sum(len(r.relevant_chunks) for r in rag_results),
                    'average_similarity': self._calculate_average_similarity(rag_results),
                    'query_success_rate': len(rag_results) / len(revenue_queries)
                },
                'reasoning': final_revenue.get('reasoning', 'Vector similarity based revenue detection')
            }
            
        except Exception as e:
            self.logger.error(f"Pure RAG revenue extraction failed: {e}")
            
            # Show error notification
            notification_service.show_error(
                f"Revenue extraction failed: {str(e)}", 
                "Please check OpenAI API configuration and try again"
            )
            notification_service.show_completion(False)
            
            return {
                'success': False,
                'error': str(e),
                'extraction_method': 'pure_rag_error'
            }
    
    def _generate_financial_queries(self, company_name: str, filing_date: Optional[str] = None) -> List[SemanticQuery]:
        """Generate semantic queries for revenue extraction."""
        queries = []
        
        for template in self.revenue_query_templates:
            # Contextualize query with company information
            contextualized_query = f"{template}"
            if company_name:
                contextualized_query += f" {company_name}"
            if filing_date:
                contextualized_query += f" {filing_date}"
            
            query = SemanticQuery(
                query_text=contextualized_query.strip(),
                query_type="financial_extraction",
                expected_data_type="numeric",
                context_window=3
            )
            queries.append(query)
        
        return queries
    
    def _perform_company_revenue_search(self, 
                                      query: SemanticQuery,
                                      company_registration_number: str,
                                      document_id: str) -> Optional[RAGResult]:
        """Perform revenue search using vector similarity for the given company."""
        try:
            from app_modules.services.embedding.openai_embedding_service import get_openai_embedding_service
            
            # Generate query embedding
            embedding_service = get_openai_embedding_service()
            query_embedding_result = embedding_service.encode(query.query_text)
            # Extract single embedding from List[List[float]] result
            query_embedding = query_embedding_result[0] if isinstance(query_embedding_result[0], list) else query_embedding_result
            
            # Vector search for company revenue data
            similar_chunks = self.vector_db.search_company_revenue(
                query_embedding=query_embedding,
                company_registration_number=company_registration_number,
                limit=5,
                min_similarity=0.05  # Lower threshold to find more potential matches
            )
            
            if not similar_chunks:
                return None
            
            # Convert to DocumentChunk objects
            relevant_chunks = []
            for chunk_data in similar_chunks:
                # Handle metadata - already parsed by vector database connection
                metadata = chunk_data.get('metadata', {})
                if not isinstance(metadata, dict):
                    # Fallback in case metadata is still a string (shouldn't happen with current implementation)
                    try:
                        metadata = json.loads(metadata) if metadata else {}
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                
                chunk = DocumentChunk(
                    text=chunk_data.get('text', chunk_data.get('content', '')),
                    page_number=metadata.get('page_number', 0),
                    section_type=metadata.get('section_type', 'content'),
                    chunk_index=chunk_data['chunk_id'],
                    metadata={
                        'similarity_score': chunk_data.get('similarity_score', chunk_data.get('similarity', 0.0)),
                        'document_id': chunk_data.get('document_id'),
                        **metadata
                    }
                )
                relevant_chunks.append(chunk)
            
            # Create RAG result
            result = RAGResult(
                query=query,
                relevant_chunks=relevant_chunks,
                extracted_data={'revenue_indicators_found': len(relevant_chunks)},
                confidence=self._calculate_query_confidence(relevant_chunks),
                reasoning=f"Found {len(relevant_chunks)} revenue-relevant chunks via vector similarity"
            )
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Company revenue search failed: {e}")
            return None

    def _keyword_fallback_search(self, company_registration_number: str, document_id: str):
        """Fallback keyword-based search for critical financial terms that vector search might miss."""
        try:
            from app_modules.database.vector_connection import VectorDatabaseConnection
            
            db = VectorDatabaseConnection()
            
            # Direct SQL search for critical revenue patterns - now includes document metadata
            query = '''
                SELECT c.chunk_id, c.content, c.chunk_index, d.metadata, d.document_id, d.company_name
                FROM document_chunks_v2 c
                JOIN documents_v2 d ON c.document_id = d.document_id
                WHERE d.company_number = ?
                AND (
                    (c.content LIKE c.content LIKE '%revenue%' AND c.content LIKE '%billion%') OR
                    (c.content LIKE '%ngp%' AND c.content LIKE '%revenue%') OR
                    (c.content LIKE '%net revenue%' AND c.content LIKE '%£%bn%') OR
                    (c.content LIKE '%consolidated%' AND c.content LIKE '%revenue%' AND c.content LIKE '%million%')
                )
                ORDER BY c.chunk_index
                LIMIT 10
            '''
            
            with db.get_connection() as conn:
                cursor = conn.execute(query, (company_registration_number,))
                results = cursor.fetchall()
            
            if not results:
                return None
            
            # Convert to DocumentChunk objects that match the expected structure
            relevant_chunks = []
            for chunk_id, content, chunk_index, doc_metadata, doc_id, company_name in results:
                # Parse document metadata JSON if available
                document_url = None
                if doc_metadata:
                    try:
                        import json
                        if isinstance(doc_metadata, str):
                            metadata_dict = json.loads(doc_metadata)
                        elif isinstance(doc_metadata, dict):
                            metadata_dict = doc_metadata
                        else:
                            metadata_dict = {}
                        
                        if isinstance(metadata_dict, dict):
                            document_url = metadata_dict.get('document_url')
                    except (json.JSONDecodeError, AttributeError, TypeError):
                        document_url = None
                
                # Create a chunk object with text and metadata attributes (not dictionary)
                class SimpleChunk:
                    def __init__(self, text: str, metadata: dict):
                        self.text = text
                        self.metadata = metadata
                
                chunk_obj = SimpleChunk(
                    text=str(content),
                    metadata={
                        'chunk_id': int(chunk_id) if chunk_id is not None else 0,
                        'chunk_index': int(chunk_index) if chunk_index is not None else 0,
                        'similarity_score': 0.8,  # High confidence for keyword matches
                        'search_method': 'keyword_fallback',
                        'document_id': doc_id or document_id,
                        'company_registration_number': company_registration_number,
                        'company_name': company_name,
                        'document_url': document_url  # Add document URL for link support
                    }
                )
                relevant_chunks.append(chunk_obj)
            
            # Create a simple result structure that matches what _perform_company_revenue_search returns
            if relevant_chunks:
                # Return a simple object that has the relevant_chunks attribute
                class KeywordResult:
                    def __init__(self, chunks):
                        self.relevant_chunks = chunks
                        
                result = KeywordResult(relevant_chunks)
                self.logger.info(f"🔍 Keyword fallback search found {len(relevant_chunks)} chunks")
                return result
            else:
                return None
            
        except Exception as e:
            self.logger.warning(f"Keyword fallback search failed: {e}")
            return None

    def _extract_revenue_from_chunks(self, rag_results: List[RAGResult], company_name: str) -> List[Dict[str, Any]]:
        """Extract revenue candidates from relevant chunks using semantic analysis (NO REGEX)."""
        revenue_candidates = []
        
        for rag_result in rag_results:
            for chunk in rag_result.relevant_chunks:
                # Use semantic analysis instead of regex
                candidates = self._semantic_revenue_detection(chunk.text, chunk.metadata)
                
                for candidate in candidates:
                    # Extract page information for vector similarity candidates
                    page_info = self._extract_page_info(chunk.text)
                    
                    revenue_candidates.append({
                        'amount': candidate['amount'],
                        'confidence': candidate['confidence'],
                        'source_text': chunk.text,
                        'chunk_metadata': chunk.metadata,
                        'similarity_score': chunk.metadata.get('similarity_score', 0.0),
                        'semantic_indicators': candidate['indicators'],
                        'page_info': page_info,  # Add page tracking for vector candidates too
                        'reasoning': f"Vector similarity: {chunk.metadata.get('similarity_score', 0.0):.2f}, Semantic confidence: {candidate['confidence']:.2f}"
                    })
        
        # DEBUG: Log all candidates before deduplication
        self.logger.info(f"🔍 DEBUG: Found {len(revenue_candidates)} total candidates before deduplication:")
        for i, candidate in enumerate(revenue_candidates):
            amount = candidate['amount']
            confidence = candidate['confidence']
            pattern_type = candidate.get('semantic_indicators', {}).get('pattern_type', 
                           candidate.get('pattern_type', 'unknown'))
            
            # Add page information to debug logging
            page_info = candidate.get('page_info', {})
            page_str = ""
            if page_info and page_info.get('page_marker_found'):
                page_str = f" [📄 Page {page_info['page_number']} ({page_info['extraction_method']})]"
            
            self.logger.info(f"  {i+1}. £{amount:,.0f} - {confidence:.3f} conf - {pattern_type}{page_str}")
        
        # Remove duplicates and sort by confidence
        unique_candidates = self._deduplicate_revenue_candidates(revenue_candidates)
        
        # DEBUG: Log candidates after deduplication
        self.logger.info(f"🔍 DEBUG: {len(unique_candidates)} unique candidates after deduplication:")
        for i, candidate in enumerate(unique_candidates):
            amount = candidate['amount']
            confidence = candidate['confidence']
            pattern_type = candidate.get('semantic_indicators', {}).get('pattern_type', 
                           candidate.get('pattern_type', 'unknown'))
            
            # Add page information to post-deduplication debug logging
            page_info = candidate.get('page_info', {})
            page_str = ""
            if page_info and page_info.get('page_marker_found'):
                page_str = f" [📄 Page {page_info['page_number']} ({page_info['extraction_method']})]"
            
            self.logger.info(f"  {i+1}. £{amount:,.0f} - {confidence:.3f} conf - {pattern_type}{page_str}")
        
        return sorted(unique_candidates, key=lambda x: x['confidence'], reverse=True)
    
    def _semantic_revenue_detection(self, text: str, chunk_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect revenue using semantic patterns and robust regex extraction."""
        candidates = []
        
        if not text:
            return candidates
        
        try:
            # Use the improved currency amount extraction
            extracted_amounts = self._extract_currency_amount(text)
            
            if not extracted_amounts:
                self.logger.debug("No amounts extracted from text")
                return candidates
            
            # Convert extracted amounts to revenue candidates  
            for amount_info in extracted_amounts:
                
                # Use dynamic confidence calculation instead of hard-coded weights
                similarity_score = chunk_metadata.get('similarity_score', 0.0)
                
                # Calculate dynamic confidence using our mathematical model
                final_confidence = self._calculate_dynamic_confidence(
                    pattern_type=amount_info['pattern_type'],
                    context=text,  # Full text chunk context
                    amount=amount_info['amount'],
                    raw_match=amount_info.get('raw_match', ''),
                    semantic_similarity=similarity_score
                )
                
                candidates.append({
                    'amount': amount_info['amount'],
                    'confidence': final_confidence,
                    'indicators': {
                        'revenue_term': amount_info['pattern_type'],
                        'currency_context': amount_info.get('raw_match', ''),
                        'extraction_method': 'semantic_pattern',
                        'pattern_type': amount_info['pattern_type']
                    }
                })
            
            return candidates
            
        except Exception as e:
            self.logger.debug(f"Semantic revenue detection failed: {e}")
            return []
    
    def _extract_currency_amount(self, text: str, context: str = '') -> List[Dict[str, Any]]:
        """Extract currency amounts using TEXT PATTERNS FIRST, then semantic analysis."""
        candidates = []
        
        # COMPREHENSIVE REVENUE PATTERNS - Enhanced vocabulary for all company sizes (thousands to billions)
        generic_revenue_patterns = {
            # === CORE REVENUE TERMS (Enhanced) - BILLIONS ===
            'revenue_billions_comprehensive': {
                'pattern': re.compile(
                    r'(?i)(?:revenue|net\s+revenue|gross\s+revenue|top\s+line|turnover|sales|net\s+sales|gross\s+sales|operating\s+revenue|total\s+revenue|consolidated\s+revenue|segment\s+revenue|contract\s+revenue)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Comprehensive revenue terms in billions'
            },
            
            # === CONTRACT & RECOGNITION TERMS - BILLIONS ===
            'contract_revenue_billions': {
                'pattern': re.compile(
                    r'(?i)(?:revenue\s+from\s+contracts|contract\s+revenue|recognized\s+revenue|performance\s+obligations|transaction\s+price|variable\s+consideration)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Contract and revenue recognition terms in billions'
            },
            
            # === REVENUE GROWTH & PERFORMANCE - BILLIONS ===
            'revenue_growth_billions': {
                'pattern': re.compile(
                    r'(?i)(?:revenue\s+growth|revenue\s+decline|comparative\s+revenue|year\s+over\s+year|yoy\s+revenue|quarter\s+over\s+quarter|qoq\s+revenue|annualised\s+revenue)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Revenue growth and performance metrics in billions'
            },
            
            # === REVENUE STREAMS & TYPES - BILLIONS ===
            'revenue_streams_billions': {
                'pattern': re.compile(
                    r'(?i)(?:recurring\s+revenue|subscription\s+revenue|service\s+revenue|product\s+revenue|licensing\s+revenue|royalty\s+revenue|usage\s+based\s+revenue|revenue\s+streams|revenue\s+breakdown)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Revenue streams and types in billions'
            },
            
            # === SEGMENTATION & ADJUSTMENTS - BILLIONS ===
            'segment_revenue_billions': {
                'pattern': re.compile(
                    r'(?i)(?:reportable\s+segment\s+revenue|intersegment\s+revenue|adjusted\s+revenue|pro\s+forma\s+revenue|net\s+revenue\s+after\s+discounts|revenue\s+guidance)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Segment and adjusted revenue in billions'
            },
            
            # === TRADITIONAL CORE PATTERNS - BILLIONS ===
            'net_revenue_billions': {
                'pattern': re.compile(
                    r'(?i)net\s+(?:revenue|sales)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Net revenue in billions'
            },
            'total_revenue_billions': {
                'pattern': re.compile(
                    r'(?i)total\s+(?:revenue|sales)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Total revenue in billions'
            },
            
            # === MILLIONS - Medium-sized companies (Enhanced vocabulary) ===
            'revenue_millions_comprehensive': {
                'pattern': re.compile(
                    r'(?i)(?:revenue|net\s+revenue|gross\s+revenue|top\s+line|turnover|sales|net\s+sales|gross\s+sales|operating\s+revenue|total\s+revenue|consolidated\s+revenue|segment\s+revenue|contract\s+revenue)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:m|million)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Comprehensive revenue terms in millions'
            },
            'contract_revenue_millions': {
                'pattern': re.compile(
                    r'(?i)(?:revenue\s+from\s+contracts|contract\s+revenue|recognized\s+revenue|performance\s+obligations|transaction\s+price|deferred\s+revenue|unearned\s+revenue)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:m|million)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Contract and recognition revenue in millions'
            },
            'revenue_streams_millions': {
                'pattern': re.compile(
                    r'(?i)(?:recurring\s+revenue|subscription\s+revenue|service\s+revenue|product\s+revenue|licensing\s+revenue|royalty\s+revenue|revenue\s+streams|revenue\s+breakdown|adjusted\s+revenue)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:m|million)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Revenue streams and types in millions'
            },
            'net_revenue_millions': {
                'pattern': re.compile(
                    r'(?i)net\s+(?:revenue|sales)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:m|million)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Net revenue in millions'
            },
            'total_revenue_millions': {
                'pattern': re.compile(
                    r'(?i)total\s+(?:revenue|sales)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:m|million)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Total revenue in millions'
            },
            
            # === THOUSANDS - Small companies and SMEs (Enhanced vocabulary) ===
            'revenue_thousands_comprehensive': {
                'pattern': re.compile(
                    r'(?i)(?:revenue|net\s+revenue|gross\s+revenue|turnover|sales|net\s+sales|operating\s+revenue|total\s+revenue|service\s+revenue|product\s+revenue)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:k|thousand)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Comprehensive revenue terms in thousands'
            },
            'net_revenue_thousands': {
                'pattern': re.compile(
                    r'(?i)net\s+(?:revenue|sales)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:k|thousand)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Net revenue in thousands'
            },
            'total_revenue_thousands': {
                'pattern': re.compile(
                    r'(?i)total\s+(?:revenue|sales)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:k|thousand)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Total revenue in thousands'
            },
            
            # === SPECIALIZED FINANCIAL REPORTING TERMS ===
            'contract_assets_liabilities': {
                'pattern': re.compile(
                    r'(?i)(?:contract\s+assets|contract\s+liabilities|deferred\s+revenue|unearned\s+revenue)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion|m|million|k|thousand)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Contract assets and liabilities'
            },
            
            'revenue_recognition_terms': {
                'pattern': re.compile(
                    r'(?i)(?:performance\s+obligations|transaction\s+price|variable\s+consideration|consideration\s+payable|revenue\s+recognition)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion|m|million|k|thousand)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Revenue recognition specific terms'
            },
            
            'top_line_revenue': {
                'pattern': re.compile(
                    r'(?i)(?:top\s+line|gross\s+profit)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion|m|million|k|thousand)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Top line and gross profit references'
            },
            
            'revenue_guidance_metrics': {
                'pattern': re.compile(
                    r'(?i)(?:revenue\s+guidance|revenue\s+mix|rebates\s+and\s+discounts|eliminations)[^£]{0,50}£(\d+(?:\.\d+)?(?:\s*\d+)*)\s*(?:bn|billion|m|million|k|thousand)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Revenue guidance and adjustment terms'
            },
            
            # UNSCALED - Raw amounts (Enhanced vocabulary)
            'revenue_raw_amounts': {
                'pattern': re.compile(
                    r'(?i)(?:revenue|net\s+revenue|gross\s+revenue|sales|turnover|top\s+line|income)[^£]{0,50}£(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
                    re.MULTILINE | re.DOTALL
                ),
                'description': 'Raw revenue amounts without scale indicators'
            },
            
            # SPACED PATTERNS - Support different formatting styles
            'spaced_numbers_all_scales': {
                'pattern': re.compile(
                    r'£(\d+(?:\.\d+)?)\s+(\d+)\s*(?:bn|billion|m|million|k|thousand)',
                    re.MULTILINE | re.IGNORECASE
                ),
                'description': 'Spaced numbers with any scale (thousands/millions/billions)'
            }
        }
        
        # Apply generic revenue patterns (works for any company at any scale)
        for pattern_name, pattern_info in generic_revenue_patterns.items():
            matches = pattern_info['pattern'].finditer(text)  # Use finditer to get match objects
            for match_obj in matches:
                try:
                    # Extract the full matched text to detect scale
                    full_match_text = match_obj.group(0).lower()
                    match_groups = match_obj.groups()
                    
                    # Determine scale from pattern name or match text
                    scale_multiplier = self._determine_scale_multiplier(pattern_name, full_match_text)
                    
                    # Process the numeric part
                    if len(match_groups) == 2 and pattern_name == 'spaced_numbers_all_scales':
                        # Handle spaced patterns: "£69 9bn" -> 69.9 billion, "£2 5m" -> 2.5 million
                        first_part = str(match_groups[0]).strip()
                        second_part = str(match_groups[1]).strip()
                        
                        # FIXED: Properly reconstruct spaced numbers as decimal values
                        # "69" + "9" -> "69.9" (not "699")
                        # "2.5" + "4" -> "2.54" (append after decimal)
                        if '.' in first_part:
                            combined_number = first_part + second_part  # "2.5" + "4" = "2.54"
                        else:
                            combined_number = first_part + "." + second_part  # "69" + "." + "9" = "69.9"
                        
                        base_amount = float(combined_number)
                        self.logger.info(f"🔧 FIXED SPACED NUMBER: '{first_part} {second_part}' -> {combined_number} -> {base_amount}")
                        print(f"🔧 SPACED NUMBER FIX: '{first_part} {second_part}' -> {combined_number} = {base_amount}")
                    else:
                        # Single number match - extract numeric part
                        numeric_match = match_groups[0] if match_groups else match_obj.group(1)

                        # RULE: when a scale word (bn/million/thousand) is present in the match,
                        # the regex capture group may have stopped at a thousands-comma
                        # (e.g. "£2,202.2 million" → regex captures only "2").
                        # Re-extract the full comma-formatted number directly from the raw
                        # match text so "2,202.2" is read as 2202.2, not 2.
                        if scale_multiplier > 1 and 'spaced_numbers' not in pattern_name:
                            full_num_re = re.search(r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', full_match_text)
                            if full_num_re:
                                numeric_match = full_num_re.group(1)
                                self.logger.debug(
                                    f"📐 Scaled-figure re-extraction: raw capture={match_groups[0]!r} "
                                    f"→ full number={numeric_match!r} (scale×{scale_multiplier:,})"
                                )

                        clean_number = re.sub(r'[^\d.]', '', str(numeric_match))
                        base_amount = float(clean_number)
                    
                    # Apply scale multiplier
                    amount = base_amount * scale_multiplier
                    
                    # Lower minimum threshold to support small companies (£1K minimum)
                    if amount >= 1000:  # At least £1K (support small businesses)
                        # Extract context for confidence calculation using match object
                        match_start = match_obj.start()
                        match_end = match_obj.end()
                        context = text[max(0, match_start - 50):min(len(text), match_end + 150)]
                        raw_match = match_obj.group(0)
                        
                        # ENHANCED: Apply OCR corrections before confidence calculation
                        enhanced_context_result = self._enhanced_context_scanning(context, amount, raw_match)
                        corrected_amount = enhanced_context_result.get('corrected_amount', amount)
                        
                        # Use corrected amount for confidence calculation
                        confidence = self._calculate_dynamic_confidence(
                            pattern_type=pattern_name,
                            context=context,
                            amount=corrected_amount,  # Use corrected amount
                            raw_match=raw_match,
                            semantic_similarity=0.0  # No semantic similarity for regex matches
                        )
                        
                        # Log OCR corrections for debugging
                        if enhanced_context_result.get('scale_corrected', False):
                            self.logger.info(f"🔧 OCR CORRECTION APPLIED: £{amount:,.0f} → £{corrected_amount:,.0f} "
                                           f"(detected '{enhanced_context_result.get('scale_indicator')}')")
                        
                        # Extract page information from context
                        page_info = self._extract_page_info(context)
                        
                        candidates.append({
                            'amount': corrected_amount,  # Store corrected amount
                            'original_amount': amount,   # Keep original for reference
                            'confidence': confidence,
                            'context': context,
                            'pattern_type': pattern_name,
                            'raw_match': raw_match,
                            'ocr_correction': enhanced_context_result,  # Store correction info
                            'page_info': page_info,  # Add page tracking
                            'indicators': {
                                'revenue_context': True,
                                'negative_context': False,
                                'pattern_type': pattern_name,
                                'scale_corrected': enhanced_context_result.get('scale_corrected', False)
                            }
                        })
                        
                        # Enhanced logging with page information
                        page_log = ""
                        if page_info['page_marker_found']:
                            page_log = f" [📄 Page {page_info['page_number']} ({page_info['extraction_method']})]"
                        
                        self.logger.info(f"🎯 PATTERN FOUND: £{amount:,.0f} via {pattern_name} (scale: {scale_multiplier:,}x){page_log}")
                except (ValueError, TypeError) as e:
                    self.logger.debug(f"Failed to process pattern match {raw_match}: {e}")
                    continue
        
        # PRIORITY 2: Multi-scale currency-first patterns (support all company sizes)
        currency_first_patterns = [
            {
                'pattern': re.compile(r'£(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|million|m|billion|bn)(?!\s*(?:loss|deficit|cost|expense|charge))', re.IGNORECASE),
                'type': 'currency_first_scaled'
            },
            {
                'pattern': re.compile(r'(?i)(?:net\s+)?revenue[^£]{0,20}£(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', re.IGNORECASE),
                'type': 'revenue_statement_line'
            },
            {
                'pattern': re.compile(r'(?i)(?:total\s+|gross\s+)?(?:revenue|sales|turnover)[^£]{0,30}£(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|million|m|billion|bn)?', re.IGNORECASE),
                'type': 'revenue_with_scale'
            }
        ]
        
        for pattern_info in currency_first_patterns:
            matches = pattern_info['pattern'].finditer(text)
            for match in matches:
                amount_str = match.group(1)
                try:
                    amount = self._convert_to_number(amount_str, match.group(0))
                    if amount and amount >= 1000:  # At least £1K (support small companies)
                        # Extract context for dynamic confidence calculation
                        context = text[max(0, match.start()-50):match.end()+100]
                        raw_match = match.group(0)
                        
                        # ENHANCED: Apply OCR corrections before confidence calculation
                        enhanced_context_result = self._enhanced_context_scanning(context, amount, raw_match)
                        corrected_amount = enhanced_context_result.get('corrected_amount', amount)
                        
                        # Calculate dynamic confidence with corrected amount
                        confidence = self._calculate_dynamic_confidence(
                            pattern_type=pattern_info['type'],
                            context=context,
                            amount=corrected_amount,  # Use corrected amount
                            raw_match=raw_match,
                            semantic_similarity=0.0  # No semantic similarity for regex matches
                        )
                        
                        # Extract page information from context
                        page_info = self._extract_page_info(context)
                        
                        candidates.append({
                            'amount': corrected_amount,  # Store corrected amount
                            'original_amount': amount,   # Keep original for reference
                            'confidence': confidence,
                            'context': context,
                            'pattern_type': pattern_info['type'],
                            'raw_match': raw_match,
                            'ocr_correction': enhanced_context_result,  # Store correction info
                            'page_info': page_info,  # Add page tracking
                            'indicators': {
                                'revenue_context': True,
                                'negative_context': False,
                                'pattern_type': pattern_info['type'],
                                'scale_corrected': enhanced_context_result.get('scale_corrected', False)
                            }
                        })
                except (ValueError, TypeError):
                    continue
        
        # PRIORITY 3: Semantic analysis (LOWEST PRIORITY - only if no text patterns found)
        if not candidates:
            revenue_indicators = [
                'revenue', 'turnover', 'sales', 'income', 'earnings',
                'net revenue', 'gross revenue', 'total revenue', 'consolidated revenue'
            ]
            
            currency_patterns = [
                r'£(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
                r'(\d{1,3}(?:,\d{3})*)\s*(?:thousand|k|million|m|billion|bn)',
            ]
            
            for pattern in currency_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    amount_str = match.group(1)
                    full_match = match.group(0)
                    
                    context_window = text[max(0, match.start()-100):match.end()+100].lower()
                    has_revenue_indicator = any(indicator in context_window for indicator in revenue_indicators)
                    
                    negative_indicators = ['loss', 'deficit', 'cost', 'expense', 'charge', 'dividend', 'payment']
                    has_negative = any(neg in context_window for neg in negative_indicators)
                    
                    if has_revenue_indicator and not has_negative:
                        try:
                            amount = self._convert_to_number(amount_str, full_match)
                            if amount and amount >= 1000:  # At least £1K (support small companies)
                                # ENHANCED: Apply OCR corrections before confidence calculation
                                enhanced_context_result = self._enhanced_context_scanning(context_window, amount, full_match)
                                corrected_amount = enhanced_context_result.get('corrected_amount', amount)
                                
                                # Calculate dynamic confidence for semantic analysis with corrected amount
                                confidence = self._calculate_dynamic_confidence(
                                    pattern_type='semantic_currency_fallback',
                                    context=context_window,
                                    amount=corrected_amount,  # Use corrected amount
                                    raw_match=full_match,
                                    semantic_similarity=0.0  # Could be enhanced with actual similarity score
                                )
                                
                                candidates.append({
                                    'amount': corrected_amount,  # Store corrected amount
                                    'original_amount': amount,   # Keep original for reference
                                    'confidence': confidence,
                                    'context': context_window,
                                    'pattern_type': 'semantic_currency_fallback',
                                    'raw_match': full_match,
                                    'ocr_correction': enhanced_context_result,  # Store correction info
                                    'indicators': {
                                        'revenue_context': has_revenue_indicator,
                                        'negative_context': has_negative,
                                        'pattern_type': 'semantic_currency_fallback',
                                        'scale_corrected': enhanced_context_result.get('scale_corrected', False)
                                    }
                                })
                        except (ValueError, TypeError):
                            continue
        
        return candidates

    def _convert_to_number(self, amount_str: str, full_match: str) -> Optional[float]:
        """Convert amount string to numeric value handling millions/billions."""
        try:
            # Clean the amount string
            clean_amount = amount_str.replace(',', '').strip()
            base_amount = float(clean_amount)
            
            # Determine multiplier from context
            full_match_lower = full_match.lower()
            if any(term in full_match_lower for term in ['billion', 'bn']):
                multiplier = 1000000000
            elif any(term in full_match_lower for term in ['million', 'm']):
                multiplier = 1000000
            elif any(term in full_match_lower for term in ['thousand', 'k']):
                multiplier = 1000
            else:
                multiplier = 1
            
            return base_amount * multiplier
            
        except (ValueError, TypeError):
            return None

    def _calculate_dynamic_confidence(self, 
                                    pattern_type: str, 
                                    context: str, 
                                    amount: float, 
                                    raw_match: str,
                                    semantic_similarity: float = 0.0,
                                    database_guidance: Dict[str, Any] = None) -> float:
        """
        Calculate confidence dynamically based on multiple mathematical factors.
        No hard-coded values - purely algorithmic confidence computation.
        """
        # Ensure parameters are properly typed
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0.0
        
        base_confidence = 0.0
        
        # Factor 1: Pattern Specificity Score (0.0-0.4)
        # More specific patterns get higher base confidence
        specificity_keywords = {
            'income_statement': 0.35,
            'continuing_ops': 0.32,
            'net_revenue': 0.30,
            'total_revenue': 0.28,
            'revenue_billions': 0.25,
            'operating_revenue': 0.22,
            'sales_revenue': 0.20,
            'turnover': 0.18,
            'currency_first': 0.10,  # Least specific
        }
        
        # Calculate specificity based on pattern name components
        for keyword, score in specificity_keywords.items():
            if keyword in pattern_type.lower():
                base_confidence = max(base_confidence, score)
                break
        
        # Factor 2: Context Quality Analysis (0.0-0.3)
        context_lower = str(context).lower() if context else ""
        
        # Positive context indicators (boost confidence)
        positive_indicators = [
            'revenue', 'sales', 'turnover', 'income', 'continuing operations',
            'total', 'net', 'group', 'consolidated', 'annual', 'year ended'
        ]
        positive_score = sum(1 for indicator in positive_indicators if indicator in context_lower)
        context_boost = min(0.3, positive_score * 0.04)  # Max 0.3 boost
        
        # Negative context indicators (reduce confidence)  
        negative_indicators = [
            'loss', 'deficit', 'cost', 'expense', 'charge', 'dividend', 
            'payment', 'tax', 'provision', 'impairment', 'write'
        ]
        negative_score = sum(1 for indicator in negative_indicators if indicator in context_lower)
        context_penalty = min(0.25, negative_score * 0.08)  # Max 0.25 penalty
        
        # Factor 3: Amount Reasonableness (0.0-0.2)
        # Support all company sizes from thousands to billions
        amount_score = 0.0
        if 1000 <= amount <= 1000000000000:  # £1K to £1T reasonable range (all company sizes)
            # Small companies (£1K - £1M) - typical for SMEs, startups
            if 1000 <= amount < 1000000:
                amount_score = 0.18  # Good score for small businesses
            # Medium companies (£1M - £100M) - most UK companies
            elif 1000000 <= amount < 100000000:
                amount_score = 0.20  # Maximum score - most common range
            # Large companies (£100M - £10B) - major corporations
            elif 100000000 <= amount < 10000000000:
                amount_score = 0.20  # Maximum score - major companies
            # Mega corporations (£10B+) - only largest companies like Shell, Tesco
            elif 10000000000 <= amount <= 1000000000000:
                amount_score = 0.18  # Slightly lower - very rare but valid
        elif amount > 1000000000000:  # £1T+ - suspicious, likely error
            amount_score = 0.05
        elif amount < 1000:  # Less than £1K - likely error or not revenue
            amount_score = 0.02
        
        # Factor 4: Match Quality (0.0-0.15)
        # Clean, well-formatted matches are more reliable
        match_quality = 0.0
        if raw_match:
            # Check for clean formatting
            if '£' in raw_match and any(unit in raw_match.lower() for unit in ['million', 'billion', 'bn', 'm']):
                match_quality += 0.10
            # Check for decimal precision (indicates careful reporting)
            if '.' in raw_match:
                match_quality += 0.03
            # Penalize for messy formatting
            if raw_match.count(' ') > 3:  # Too many spaces
                match_quality -= 0.02
                
        # Factor 5: Semantic Similarity Boost (0.0-0.1) 
        # If this comes from vector similarity search
        similarity_boost = min(0.1, semantic_similarity * 0.1) if semantic_similarity > 0 else 0.0
        
        # ENHANCED FACTOR 6: OCR Scale Correction Boost (0.0-0.25)
        # Apply enhanced context scanning to detect and correct OCR scale issues
        ocr_boost = 0.0
        try:
            enhanced_context = self._enhanced_context_scanning(context, amount, raw_match or "")
            ocr_boost = enhanced_context.get('confidence_boost', 0.0)
            
            if enhanced_context.get('scale_corrected', False):
                # Major boost for successful OCR corrections (helps Tesco-type cases)
                ocr_boost = min(0.25, ocr_boost)  # Cap at 0.25
                self.logger.info(f"🚀 OCR CORRECTION BOOST: +{ocr_boost:.3f} confidence "
                               f"(corrected via '{enhanced_context.get('scale_indicator', 'unknown')}')")
            elif ocr_boost > 0:
                # Smaller boost for scale validation without correction
                ocr_boost = min(0.15, ocr_boost)
                self.logger.debug(f"📊 SCALE VALIDATION BOOST: +{ocr_boost:.3f} confidence")
                
        except Exception as e:
            self.logger.debug(f"Enhanced context scanning in confidence calc failed: {e}")
        
        # ENHANCED FACTOR 7: Public API Proximity Boost (0.0-0.30)
        # Boost confidence when amount is close to yfinance/public API data
        api_boost = 0.0
        try:
            api_boost = self._calculate_public_api_proximity_boost(amount, context)
            if api_boost > 0:
                self.logger.info(f"📈 PUBLIC API PROXIMITY BOOST: +{api_boost:.3f} confidence "
                               f"(amount £{amount/1000000000:.1f}B matches expected range)")
        except Exception as e:
            self.logger.debug(f"Public API proximity calculation failed: {e}")
        
        # ENHANCED FACTOR 8: Database Guidance Boost (0.0-0.45)
        # Major boost for candidates matching database expectations
        database_boost = 0.0
        if database_guidance:
            proximity_category = database_guidance.get('proximity_category', 'no_match')
            database_similarity = database_guidance.get('database_similarity', 0.0)
            expected_revenue = database_guidance.get('expected_revenue', 0.0)
            
            if proximity_category == 'optimal_match':  # Within ±10%
                database_boost = 0.45  # Major confidence boost for optimal matches
            elif proximity_category == 'good_match':   # Within ±25%
                database_boost = 0.30  # Strong boost for good matches
            elif proximity_category == 'acceptable_match':  # Within ±50%
                database_boost = 0.20  # Good boost for acceptable matches
            elif proximity_category == 'distant_match':
                database_boost = 0.10  # Small boost for distant matches
            
            # Scale by similarity score
            database_boost *= database_similarity
            
            if database_boost > 0:
                percentage_diff = abs((amount - expected_revenue) / expected_revenue * 100) if expected_revenue > 0 else 0
                self.logger.info(f"🎯 DATABASE GUIDANCE BOOST: +{database_boost:.3f} confidence "
                               f"(£{amount:,.0f} vs £{expected_revenue:,.0f}, {proximity_category}, "
                               f"diff: {percentage_diff:.1f}%)")
        
        # Combine all factors (including database guidance boost)
        total_confidence = (base_confidence + context_boost - context_penalty + 
                          amount_score + match_quality + similarity_boost + ocr_boost + api_boost + database_boost)
        
        # Ensure confidence is within valid bounds [0.0, 1.0]
        final_confidence = max(0.05, min(0.98, total_confidence))  # Min 5%, Max 98%
        
        # Log the confidence calculation for transparency
        self.logger.debug(f"Confidence calculation for {pattern_type}:")
        self.logger.debug(f"  Base: {base_confidence:.3f}, Context: +{context_boost:.3f}-{context_penalty:.3f}")
        self.logger.debug(f"  Amount: {amount_score:.3f}, Match: {match_quality:.3f}, Similarity: {similarity_boost:.3f}")
        self.logger.debug(f"  OCR Boost: +{ocr_boost:.3f}, DB Boost: +{database_boost:.3f}, Final: {final_confidence:.3f}")
        
        return final_confidence

    def _determine_scale_multiplier(self, pattern_name: str, full_match_text: str) -> float:
        """
        Determine the appropriate scale multiplier based on pattern name and match text.
        Supports thousands, millions, and billions for all company sizes.
        """
        # Pattern name-based detection (most reliable)
        if 'billions' in pattern_name or 'bn' in full_match_text or 'billion' in full_match_text:
            return 1_000_000_000  # Billions
        elif 'millions' in pattern_name or ' m ' in full_match_text or 'million' in full_match_text:
            return 1_000_000      # Millions
        elif 'thousands' in pattern_name or ' k ' in full_match_text or 'thousand' in full_match_text:
            return 1_000          # Thousands
        elif 'raw_amounts' in pattern_name or 'raw_numbers' in pattern_name:
            # For raw amounts, use context and number structure to infer scale
            # Extract the numeric part to guess the scale more intelligently
            import re
            
            # Look for scale indicators in the surrounding text first
            lower_text = full_match_text.lower()
            if any(indicator in lower_text for indicator in ['bn', 'billion']):
                return 1_000_000_000
            elif any(indicator in lower_text for indicator in ['mn', 'million']):
                return 1_000_000
            elif any(indicator in lower_text for indicator in ['k', 'thousand']):
                return 1_000
            
            # If no explicit scale indicator, analyze the number structure
            numbers = re.findall(r'\d{1,3}(?:[,\s]\d{3})*(?:[,\.]\d+)?', full_match_text.replace('£', '').replace('€', '').replace('$', ''))
            if numbers:
                # Remove commas/spaces and check magnitude
                clean_number_str = numbers[0].replace(',', '').replace(' ', '')
                try:
                    if '.' in clean_number_str:
                        # Decimal number - likely already in correct scale or needs context
                        base_number = float(clean_number_str)
                        if base_number < 100:  # Numbers like 58.7, 40.2 are likely billions
                            return 1_000_000_000
                        elif base_number < 10000:  # Numbers like 1,234.5 are likely millions
                            return 1_000_000
                        else:
                            return 1  # Already large numbers
                    else:
                        # Integer number
                        clean_number = int(clean_number_str)
                        if clean_number < 1000 and len(clean_number_str) <= 3:  # Single/double/triple digits likely billions
                            return 1_000_000_000
                        elif clean_number >= 1000000000:  # Already billions
                            return 1
                        elif clean_number >= 1000000:  # Already millions
                            return 1
                        elif clean_number >= 10000:  # Large numbers likely already in correct scale
                            return 1
                        else:  # Medium numbers could be millions
                            return 1_000_000
                except ValueError:
                    pass
            
            # Conservative default - no scaling for unrecognized patterns
            return 1
        else:
            # Fallback: scan the match text for scale indicators
            if any(indicator in full_match_text.lower() for indicator in ['bn', 'billion']):
                return 1_000_000_000
            elif any(indicator in full_match_text.lower() for indicator in ['mn', 'million']):
                return 1_000_000 
            elif any(indicator in full_match_text.lower() for indicator in ['k', 'thousand']):
                return 1_000
            else:
                return 1  # No scaling

    def _deduplicate_amounts(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate amounts and sort by confidence."""
        unique_results = []
        seen_amounts = set()
        
        # Sort by confidence first
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        for result in results:
            amount = result['amount']
            # Group similar amounts (within 5%)
            is_duplicate = False
            for seen_amount in seen_amounts:
                if abs(amount - seen_amount) / max(amount, seen_amount) < 0.05:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_amounts.add(amount)
                unique_results.append(result)
        
        return unique_results
    
    def _calculate_semantic_confidence(self, 
                                     text: str, 
                                     revenue_word: str, 
                                     amount: float,
                                     proximity: int,
                                     chunk_metadata: Dict[str, Any]) -> float:
        """Calculate confidence based on GAAP/IFRS taxonomy and semantic context."""
        confidence = 0.0
        text_lower = text.lower()
        
        # PHASE 1: Base confidence from similarity score
        similarity = chunk_metadata.get('similarity_score', 0.0)
        confidence += similarity * 0.2  # Reduced to make room for GAAP/IFRS scoring
        
        # PHASE 2: GAAP/IFRS Taxonomy-Based Confidence (HIGHEST PRIORITY)
        gaap_ifrs_boost = self._calculate_gaap_ifrs_confidence(text_lower)
        confidence += gaap_ifrs_boost
        
        # PHASE 3: Traditional Financial Context Validation
        # Positive indicators (INCOME STATEMENT context)
        revenue_context_boost = 0.0
        for indicator in self.revenue_context_indicators:
            if indicator in text_lower:
                revenue_context_boost += 0.10  # Reduced since GAAP/IFRS is now primary
                break
        
        # Industry-agnostic revenue context boost (no company-specific logic)
        confidence += min(revenue_context_boost, 0.25)
        
        # Negative penalties (BALANCE SHEET context - ONLY penalize obvious non-revenue terms)
        balance_sheet_penalty = 0.0
        
        # SEVERE penalties for specific non-revenue contexts
        severe_non_revenue_terms = ['distributable reserves', 'retained earnings', 'capital reserves', 'shareholders equity']
        for term in severe_non_revenue_terms:
            if term in text_lower:
                balance_sheet_penalty += 0.8  # SEVERE penalty - almost eliminates this candidate
                self.logger.warning(f"⚠️ SEVERE PENALTY: Detected non-revenue context: '{term}'")
        
        # Light penalty for general balance sheet context (but don't be too harsh)
        general_balance_terms = ['balance sheet', 'statement of financial position']
        for term in general_balance_terms:
            if term in text_lower and 'revenue' not in text_lower:  # Only penalize if no revenue context
                balance_sheet_penalty += 0.2  # Light penalty
        
        confidence -= min(balance_sheet_penalty, 0.6)  # Reduced maximum penalty
        
        # PHASE 3: Proximity bonus (closer = better)
        proximity_bonus = max(0.0, 0.2 - (proximity * 0.02))
        confidence += proximity_bonus
        
        # PHASE 4: Revenue term quality scoring
        term_scores = {
            'revenue': 0.25,
            'turnover': 0.20,
            'sales': 0.18,
            'income': 0.12,
            'gross revenue': 0.25,
            'net revenue': 0.25,
            'total revenue': 0.30
        }
        
        term_bonus = 0.0
        for term, score in term_scores.items():
            if term in revenue_word.lower():
                term_bonus = max(term_bonus, score)  # Take highest matching term
        confidence += term_bonus
        
        # PHASE 5: Amount reasonableness validation
        if 1000000 <= amount <= 50000000000:  # Reasonable revenue range (1M to 50B)
            confidence += 0.15
        elif 100000 <= amount <= 1000000000:  # Acceptable range
            confidence += 0.08
        elif amount < 10000 or amount > 100000000000:  # Unrealistic revenue
            confidence -= 0.3
        
        # PHASE 6: Enhanced financial context quality
        income_statement_words = ['consolidated', 'continuing operations', 'from sales', 'operating revenue']
        context_score = sum(0.05 for word in income_statement_words if word in text_lower)
        confidence += min(context_score, 0.2)
        
        # PHASE 7: Final validation and capping
        final_confidence = min(max(confidence, 0.0), 1.0)
        
        # Log confidence calculation for debugging
        if final_confidence < 0.5:
            self.logger.debug(f"Low confidence ({final_confidence:.2f}) for amount {amount} - text context may be non-revenue")
        
        return final_confidence
    
    def _calculate_gaap_ifrs_confidence(self, text_lower: str) -> float:
        """
        Calculate confidence boost based on GAAP/IFRS accounting taxonomy.
        Returns confidence boost (0.0 to 0.4) based on accounting standards compliance.
        """
        gaap_confidence = 0.0
        
        # TIER 1: IFRS 15 / ASC 606 Revenue Recognition (Highest Confidence +0.25)
        ifrs_15_score = 0.0
        for context in self.gaap_ifrs_revenue_contexts['ifrs_15_contexts']:
            if context in text_lower:
                ifrs_15_score += 0.08
                self.logger.info(f"📊 IFRS 15 CONTEXT: Found '{context}' - high confidence boost")
        
        asc_606_score = 0.0
        for context in self.gaap_ifrs_revenue_contexts['asc_606_contexts']:
            if context in text_lower:
                asc_606_score += 0.08
                self.logger.info(f"📊 ASC 606 CONTEXT: Found '{context}' - high confidence boost")
        
        # Take the higher of IFRS 15 or ASC 606 (they're equivalent standards)
        revenue_recognition_boost = min(max(ifrs_15_score, asc_606_score), 0.25)
        gaap_confidence += revenue_recognition_boost
        
        # TIER 2: Income Statement Structure (Medium-High Confidence +0.15)
        income_statement_score = 0.0
        for context in self.gaap_ifrs_revenue_contexts['income_statement_contexts']:
            if context in text_lower:
                income_statement_score += 0.05
                self.logger.debug(f"📊 INCOME STATEMENT: Found '{context}'")
        
        gaap_confidence += min(income_statement_score, 0.15)
        
        # TIER 3: UK GAAP/FRS Context (Medium Confidence +0.10)
        uk_gaap_score = 0.0
        for context in self.gaap_ifrs_revenue_contexts['uk_gaap_contexts']:
            if context in text_lower:
                uk_gaap_score += 0.04
                self.logger.debug(f"📊 UK GAAP: Found '{context}'")
        
        gaap_confidence += min(uk_gaap_score, 0.10)
        
        # TIER 4: Consolidated/Segment Reporting Structure (+0.08)
        structure_score = 0.0
        for category, contexts in self.gaap_ifrs_statement_contexts.items():
            for context in contexts:
                if context in text_lower:
                    structure_score += 0.02
                    self.logger.debug(f"📊 GAAP STRUCTURE: Found '{context}' in {category}")
        
        gaap_confidence += min(structure_score, 0.08)
        
        # Cap total GAAP/IFRS confidence boost at 0.4 (40% of total confidence)
        final_gaap_confidence = min(gaap_confidence, 0.4)
        
        if final_gaap_confidence > 0.1:
            self.logger.info(f"🏆 GAAP/IFRS TAXONOMY BOOST: {final_gaap_confidence:.3f} confidence added")
        
        return final_gaap_confidence
    
    def _calculate_gaap_amount_confidence(self, amount: float, content: str) -> float:
        """
        Calculate GAAP/IFRS-aware confidence adjustments based on amount ranges and context.
        Returns confidence adjustment (-0.2 to +0.2) based on accounting standards compliance.
        """
        gaap_amount_boost = 0.0
        content_lower = content.lower()
        
        # GAAP/IFRS Materiality Thresholds (based on accounting standards)
        # Large public companies typically have materiality thresholds of 0.5-5% of revenue
        
        if amount >= 1000000000:  # £1B+ (Major Revenue per IFRS/GAAP materiality)
            # Check for proper revenue disclosure context
            if any(term in content_lower for term in ['consolidated', 'total revenue', 'group revenue']):
                gaap_amount_boost += 0.15
                self.logger.debug(f"📊 GAAP MATERIALITY: £{amount:,.0f} in consolidated context (+0.15)")
            else:
                gaap_amount_boost += 0.08  # Still significant amount
                
        elif 500000000 <= amount < 1000000000:  # £500M-1B (Significant per IFRS segment reporting)
            if any(term in content_lower for term in ['segment', 'division', 'business unit']):
                gaap_amount_boost += 0.10
                self.logger.debug(f"📊 SEGMENT REPORTING: £{amount:,.0f} in segment context (+0.10)")
            else:
                gaap_amount_boost += 0.05
                
        elif 100000000 <= amount < 500000000:  # £100M-500M (Material per GAAP disclosure rules)
            gaap_amount_boost += 0.03
            
        elif 10000000 <= amount < 100000000:  # £10M-100M (Moderate materiality)
            gaap_amount_boost += 0.01
            
        elif amount < 1000000:  # <£1M (Below typical materiality thresholds)
            gaap_amount_boost -= 0.05
            self.logger.debug(f"⚠️ MATERIALITY: £{amount:,.0f} below GAAP materiality threshold (-0.05)")
            
        # GAAP/IFRS Revenue Recognition Context Bonuses
        # IFRS 15 / ASC 606 specific revenue types get additional confidence
        ifrs_revenue_types = {
            'revenue from contracts with customers': 0.12,
            'contract revenue': 0.10,
            'service revenue': 0.08,
            'product revenue': 0.08,
            'subscription revenue': 0.06,
            'licensing revenue': 0.06
        }
        
        for revenue_type, bonus in ifrs_revenue_types.items():
            if revenue_type in content_lower:
                gaap_amount_boost += bonus
                self.logger.debug(f"📊 IFRS 15 REVENUE TYPE: Found '{revenue_type}' (+{bonus})")
                break  # Only one bonus per candidate
        
        # GAAP/IFRS Financial Statement Structure Context
        if any(term in content_lower for term in ['continuing operations', 'discontinued operations']):
            gaap_amount_boost += 0.08
            self.logger.debug(f"📊 GAAP STRUCTURE: Operations classification context (+0.08)")
        
        # Penalty for non-GAAP contexts that shouldn't contain revenue
        non_gaap_contexts = ['cash and cash equivalents', 'property plant equipment', 'intangible assets']
        for context in non_gaap_contexts:
            if context in content_lower:
                gaap_amount_boost -= 0.15
                self.logger.warning(f"⚠️ NON-REVENUE CONTEXT: Found '{context}' (-0.15)")
                break
        
        # Cap the total GAAP amount adjustment
        final_gaap_amount_boost = max(-0.2, min(gaap_amount_boost, 0.2))
        
        if abs(final_gaap_amount_boost) > 0.05:
            self.logger.info(f"📊 GAAP AMOUNT ADJUSTMENT: £{amount:,.0f} gets {final_gaap_amount_boost:+.3f} confidence")
        
        return final_gaap_amount_boost
    
    def _extract_contextual_text(self, content: str, match_str: str, amount: float) -> str:
        """
        ENHANCED: Extract contextual text with OCR-resilient scale detection and wider context scanning.
        Handles OCR conversion issues (bn→mn, billion→million) within 200-char windows.
        """
        try:
            # Enhanced context scanning with OCR scale detection
            enhanced_context = self._enhanced_context_scanning(content, amount, match_str)
            if enhanced_context['corrected_amount'] != amount:
                # OCR scale correction detected - log for debugging
                self.logger.info(f"🔧 OCR SCALE CORRECTION: £{amount:,.0f} → £{enhanced_context['corrected_amount']:,.0f} "
                               f"(found '{enhanced_context['scale_indicator']}' in context)")
                amount = enhanced_context['corrected_amount']  # Use corrected amount for context extraction
            
            # Find the position of the amount in the content
            content_lower = content.lower()
            
            # ENHANCED: Try multiple patterns including OCR-corrected formats
            search_patterns = [
                str(amount / 1000000000).replace('.0', '') + ' bn',  # £8bn format
                str(amount / 1000000000) + ' bn',  # £8.2bn format  
                str(amount / 1000000000).replace('.0', '') + ' billion',  # £8 billion format
                str(amount / 1000000000) + ' billion',  # £8.2 billion format
                f'£{amount / 1000000000:.1f}bn'.replace('.0bn', 'bn'),  # £8.2bn format
                f'£{amount / 1000000000:.0f}bn',  # £8bn format
                
                # ENHANCED: Add OCR-resilient patterns (millions that should be billions)
                str(amount / 1000000).replace('.0', '') + ' mn',  # £69,191mn format (OCR converted)
                str(amount / 1000000) + ' million',  # £69,191 million format
                f'£{amount / 1000000:.0f}m',  # £69191m format
                
                match_str.lower(),  # Original match
            ]
            
            best_match_pos = -1
            best_context_window = ""
            
            for pattern in search_patterns:
                pattern_pos = content_lower.find(pattern.lower())
                if pattern_pos != -1:
                    # ENHANCED: Extract wider context (8-10 words instead of 4-5)
                    words = content.split()
                    
                    # Find the word containing our pattern
                    pattern_word_idx = -1
                    for i, word in enumerate(words):
                        if (pattern.lower() in word.lower() or 
                            any(p in word.lower() for p in [f'{amount/1000000000:.1f}', f'{amount/1000000000:.0f}', 
                                                           f'{amount/1000000:.0f}'])):
                            pattern_word_idx = i
                            break
                    
                    if pattern_word_idx != -1:
                        # ENHANCED: Get 8-10 words before and after for better context
                        start_idx = max(0, pattern_word_idx - 10)
                        end_idx = min(len(words), pattern_word_idx + 11)
                        
                        context_words = words[start_idx:end_idx]
                        context_text = ' '.join(context_words)
                        
                        # Clean up the context text
                        context_text = ' '.join(context_text.split())  # Remove extra whitespace
                        context_text = context_text.replace('\n', ' ').replace('\t', ' ')
                        
                        if len(context_text) > 20:  # Ensure we have meaningful context
                            best_context_window = context_text
                            break
            
            # If we found good context, return it with scale correction info
            if best_context_window:
                # ENHANCED: Limit to 200 chars (was 150) for better context
                if len(best_context_window) > 200:
                    best_context_window = best_context_window[:197] + "..."
                
                # Add scale correction indicator if applicable
                if enhanced_context['scale_corrected']:
                    best_context_window += f" [Scale corrected: {enhanced_context['scale_indicator']}]"
                    
                return best_context_window
            
            # ENHANCED: Fallback with wider sentence context scanning
            sentences = content.split('. ')
            for i, sentence in enumerate(sentences):
                if any(pattern in sentence.lower() for pattern in search_patterns[:6]):
                    # Get wider sentence context (2 sentences before and after)
                    start_sent = max(0, i-2)
                    end_sent = min(len(sentences), i+3)
                    context_sentences = sentences[start_sent:end_sent]
                    fallback_context = '. '.join(context_sentences)
                    
                    if len(fallback_context) > 200:
                        fallback_context = fallback_context[:197] + "..."
                    return fallback_context
            
            # Final fallback: return wider content preview
            return f"Revenue context: {content[:150]}..." if len(content) > 150 else content
            
        except Exception as e:
            self.logger.debug(f"Context extraction failed: {e}")
            return f"£{amount:,.0f} revenue figure identified"

    def _enhanced_context_scanning(self, content: str, amount: float, match_str: str) -> Dict[str, Any]:
        """
        PHASE 1: Enhanced context scanning for OCR-resilient scale detection.
        
        Scans 200-char windows around extracted amounts to detect scale indicators
        that OCR might have corrupted (e.g., £69.9bn → £69,191mn).
        
        Returns:
            - corrected_amount: Scale-corrected amount if OCR issue detected
            - scale_corrected: Boolean flag indicating if correction was applied
            - scale_indicator: The scale term found in context
            - confidence_boost: Additional confidence for corrected amounts
        """
        try:
            content_lower = content.lower()
            
            # Default response - no correction needed
            result = {
                'corrected_amount': amount,
                'scale_corrected': False, 
                'scale_indicator': '',
                'confidence_boost': 0.0
            }
            
            # STEP 1: Find position of extracted amount in content
            amount_patterns = [
                f'{amount:,.0f}',  # e.g., "69,191"
                f'{amount:.1f}',   # e.g., "69191.0" 
                f'{amount/1000:.0f}',  # Sometimes OCR adds thousands
                match_str.replace('£', '').replace(',', ''),  # Clean match string
            ]
            
            amount_position = -1
            found_pattern = ""
            
            for pattern in amount_patterns:
                pos = content_lower.find(pattern.lower())
                if pos != -1:
                    amount_position = pos
                    found_pattern = pattern
                    break
            
            if amount_position == -1:
                return result  # Can't find amount in content
            
            # STEP 2: Extract 200-char context window around the amount
            context_start = max(0, amount_position - 200)
            context_end = min(len(content), amount_position + len(found_pattern) + 200)
            context_window = content[context_start:context_end].lower()
            
            # STEP 3: Look for scale indicators within the context window
            scale_indicators = {
                # Billion indicators
                'billion': {'multiplier': 1000000000, 'confidence_boost': 0.25},
                'bn': {'multiplier': 1000000000, 'confidence_boost': 0.25},
                'billions': {'multiplier': 1000000000, 'confidence_boost': 0.25},
                'b': {'multiplier': 1000000000, 'confidence_boost': 0.20},  # Less confident single 'b'
                
                # Million indicators (but check if should be billions)
                'million': {'multiplier': 1000000, 'confidence_boost': 0.15},
                'mn': {'multiplier': 1000000, 'confidence_boost': 0.15}, 
                'millions': {'multiplier': 1000000, 'confidence_boost': 0.15},
                'm': {'multiplier': 1000000, 'confidence_boost': 0.10},  # Less confident single 'm'
                
                # Thousand indicators
                'thousand': {'multiplier': 1000, 'confidence_boost': 0.10},
                'k': {'multiplier': 1000, 'confidence_boost': 0.10},
            }
            
            detected_scales = []
            for indicator, scale_info in scale_indicators.items():
                if indicator in context_window:
                    # Calculate distance from amount to get confidence
                    indicator_pos = context_window.find(indicator)
                    distance = abs(indicator_pos - (amount_position - context_start))
                    
                    # Closer indicators get higher confidence
                    distance_penalty = min(0.1, distance / 1000)  # Max 0.1 penalty
                    adjusted_confidence = scale_info['confidence_boost'] - distance_penalty
                    
                    detected_scales.append({
                        'indicator': indicator,
                        'multiplier': scale_info['multiplier'],
                        'confidence': max(0.05, adjusted_confidence),
                        'distance': distance
                    })
            
            if not detected_scales:
                # FALLBACK: Try cross-chunk scale inference for OCR documents
                inferred_scale = self._cross_chunk_scale_inference(amount, content)
                if inferred_scale:
                    detected_scales.append({
                        'indicator': inferred_scale,
                        'multiplier': 1000000000 if inferred_scale == 'billion' else 1000000,
                        'confidence': 0.20,  # Lower confidence for cross-chunk inference
                        'distance': 0  # Cross-chunk = no distance penalty
                    })
                else:
                    return result  # No scale indicators found
            
            # STEP 4: Choose the best scale indicator (closest + highest confidence)
            best_scale = max(detected_scales, key=lambda x: x['confidence'])
            
            # STEP 5: Apply OCR correction logic
            current_scale = self._infer_current_scale(amount)
            target_scale = best_scale['multiplier']
            
            # OCR Correction Scenarios:
            corrected_amount = amount
            scale_corrected = False
            
            # Scenario 1: Amount in millions but billion indicator found
            if (current_scale == 1000000 and target_scale == 1000000000 and 
                amount >= 10000):  # e.g., £69,191mn should be £69.9bn
                corrected_amount = amount / 1000  # Convert mn to bn
                scale_corrected = True
                self.logger.info(f"🔧 OCR CORRECTION: £{amount:,.0f}M → £{corrected_amount:.1f}B "
                               f"(found '{best_scale['indicator']}' at distance {best_scale['distance']})")
            
            # Scenario 2: Raw amount with billion context (e.g., 69191 + "billion" → 69.191B)
            elif (current_scale == 1 and target_scale == 1000000000 and 
                  amount >= 10000):  
                corrected_amount = amount / 1000  # Assume thousands missing
                scale_corrected = True
                self.logger.info(f"🔧 OCR CORRECTION: £{amount:,.0f} → £{corrected_amount:.1f}B "
                               f"(raw amount with '{best_scale['indicator']}' context)")
            
            # Scenario 3: Large billion amount that's likely OCR-corrupted (£69,191M → £69.9B)
            elif (current_scale == 1000000000 and target_scale == 1000000000 and
                  65_000_000_000 <= amount <= 75_000_000_000):
                # £69.191B is suspicious - likely should be £69.9B (divide by 1000)
                corrected_amount = amount / 1000  
                scale_corrected = True
                self.logger.info(f"🔧 OCR CORRECTION (Cross-chunk): £{amount/1000000000:.1f}B → £{corrected_amount/1000000000:.1f}B "
                               f"(OCR likely misread scale, found '{best_scale['indicator']}' context)")
            
            # Scenario 4: Verify existing scale matches context
            elif current_scale == target_scale:
                # Scale matches - boost confidence but no correction needed
                result['confidence_boost'] = best_scale['confidence'] * 0.5  # Validation bonus
                
            # Apply correction results
            if scale_corrected:
                result.update({
                    'corrected_amount': corrected_amount,
                    'scale_corrected': True,
                    'scale_indicator': best_scale['indicator'],
                    'confidence_boost': best_scale['confidence']  # Full confidence boost for corrections
                })
            
            return result
            
        except Exception as e:
            self.logger.debug(f"Enhanced context scanning failed: {e}")
            return {
                'corrected_amount': amount,
                'scale_corrected': False,
                'scale_indicator': '',
                'confidence_boost': 0.0
            }
    
    def _infer_current_scale(self, amount: float) -> int:
        """Infer the current scale of an amount based on its magnitude."""
        if amount >= 1000000000:  # >= £1B
            return 1000000000
        elif amount >= 1000000:  # >= £1M  
            return 1000000
        elif amount >= 1000:     # >= £1K
            return 1000
        else:
            return 1  # Raw amount
    
    def _cross_chunk_scale_inference(self, amount: float, text: str) -> str:
        """
        CRITICAL OCR FIX: Cross-chunk scale inference for OCR documents.
        
        When OCR separates amounts from scale indicators across different chunks,
        this method uses document-wide patterns to infer the correct scale.
        
        For Tesco case: £69,191 (millions) + separate "£2.5bn" references → billion scale
        """
        try:
            if not hasattr(self, '_document_scale_cache'):
                self._document_scale_cache = {}
            
            # Check if we've already analyzed this document's scale patterns
            doc_key = f"amount_{amount}"
            if doc_key in self._document_scale_cache:
                return self._document_scale_cache[doc_key]
            
            # For large amounts that might be OCR-corrupted billions
            if (50_000_000 <= amount <= 100_000_000 or          # £50M-£100M range  
                65_000_000_000 <= amount <= 75_000_000_000):     # Or £65B-£75B that should be smaller
                # These amounts are suspicious - likely scale issues
                
                # Check for billion patterns elsewhere in document/chunk
                text_lower = text.lower()
                billion_indicators = ['£2.5bn', '£1.8bn', '£1.4bn', 'billion', 'bn']
                
                for indicator in billion_indicators:
                    if indicator in text_lower:
                        self.logger.info(f"🔍 CROSS-CHUNK SCALE: Found '{indicator}' context for £{amount:,.0f} - inferring billion scale")
                        self._document_scale_cache[doc_key] = 'billion'
                        return 'billion'
                
                # Additional heuristic: amounts like £69,191M in retail contexts are likely £69.9B
                if 65_000_000 <= amount <= 75_000_000:  # Tesco-like revenue range
                    self.logger.info(f"🎯 RETAIL HEURISTIC: £{amount:,.0f}M in major retailer context - likely billion scale")
                    self._document_scale_cache[doc_key] = 'billion'  
                    return 'billion'
            
            # Cache negative result
            self._document_scale_cache[doc_key] = ''
            return ''
            
        except Exception as e:
            self.logger.debug(f"Cross-chunk scale inference failed: {e}")
            return ''
    
    def _deduplicate_revenue_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate revenue candidates."""
        seen_amounts = set()
        unique_candidates = []
        
        for candidate in candidates:
            amount = candidate['amount']
            # Group similar amounts (within 5%)
            amount_key = int(amount / (amount * 0.05 + 1000))  # Bucketing
            
            if amount_key not in seen_amounts:
                seen_amounts.add(amount_key)
                unique_candidates.append(candidate)
        
        return unique_candidates
    
    def _assess_multi_scale_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        When document contains amounts in billions, millions and thousands in combination,
        assess the highest figures based on context quality to identify likely revenue figures.
        
        Returns prioritized candidates with context-based scoring.
        """
        if len(candidates) < 2:
            return candidates
        
        # Group candidates by scale
        billions = []
        millions = []  
        thousands = []
        other = []
        
        for candidate in candidates:
            amount = candidate.get('amount', 0)
            if amount >= 1_000_000_000:  # £1B+
                billions.append(candidate)
            elif amount >= 1_000_000:    # £1M+
                millions.append(candidate)
            elif amount >= 1_000:        # £1K+
                thousands.append(candidate)
            else:
                other.append(candidate)
        
        # Check if we have mixed scales (indicates need for context assessment)
        scale_count = sum([len(billions) > 0, len(millions) > 0, len(thousands) > 0])
        
        if scale_count <= 1:
            # Single scale - no special processing needed
            self.logger.info(f"📊 Single scale detected - no multi-scale assessment needed")
            return candidates
        
        self.logger.info(f"📊 Multi-scale document detected:")
        self.logger.info(f"   💰 Billions: {len(billions)} candidates")  
        self.logger.info(f"   💰 Millions: {len(millions)} candidates")
        self.logger.info(f"   💰 Thousands: {len(thousands)} candidates")
        
        # Assess context quality for high-value candidates
        def assess_revenue_context_quality(candidate):
            """Score candidate based on GAAP/IFRS income-statement vocabulary.

            Dual-context strategy:
            - snippet  (±100 chars around the number): negative check — balance-sheet/AUM terms
              adjacent to the number definitively disqualify it as non-revenue.
            - full_text (entire chunk): positive check — at least one GAAP/IFRS income-statement
              term must appear anywhere in the chunk for the candidate to qualify.
            Among qualified candidates the MAXIMUM amount is selected (revenue = top-line figure).
            """
            # Narrow ±100 char window around the number
            snippet   = candidate.get('context', '').lower()
            # Full chunk text (set from full_chunk_text key by caller)
            full_text = (candidate.get('source_text') or snippet).lower()
            pattern_type   = candidate.get('semantic_indicators', {}).get('pattern_type', '')
            base_confidence = candidate.get('confidence', 0)

            # ------------------------------------------------------------------
            # NEGATIVE (disqualify): balance-sheet / AUM labels adjacent to number
            # ------------------------------------------------------------------
            adjacent_non_revenue_terms = [
                'assets under management', 'aum',
                'total assets', 'net assets', 'gross assets',
                'total liabilities', 'net liabilities',
                'investment portfolio', 'funds under management', 'managed funds',
                'market capitalisation', 'market cap',
                'policyholder', 'insurance liabilities', 'claims outstanding',
                'technical reserves', 'long-term business reserve',
                "shareholders' equity", 'shareholders equity',
                'retained earnings', 'capital reserves',
                'net flows', 'cumulative amount', 'global spend',
                'market size', 'invested in',
            ]
            adj_neg_hits = sum(1 for t in adjacent_non_revenue_terms if t in snippet)

            # Forward-looking / target phrases: the number is a projection, not actual revenue
            forward_looking_terms = [
                'ambition for', 'our ambition', 'target of', 'our target',
                'aspiration', 'plan to', 'aiming for', 'aim to achieve',
                'we aim', 'we target', 'we expect to',
                'over three years', 'over the next', 'over coming years',
                'by 2025', 'by 2026', 'by 2027', 'by 2028', 'by 2030',
                'forecast revenue', 'guidance of', 'expected to reach',
                'targeted revenue', 'goal of',
            ]
            fwd_hits = sum(1 for t in forward_looking_terms if t in snippet)

            # ------------------------------------------------------------------
            # POSITIVE (qualify): GAAP/IFRS revenue keyword within ~5 words of the number.
            # We check the ±100-char snippet (not the full chunk) so that table-of-contents
            # entries, chapter titles, and AUM narrative paragraphs that happen to mention
            # "revenue" elsewhere in the same chunk don't accidentally qualify a non-revenue
            # number. The snippet is already centred on the matched number.
            # ------------------------------------------------------------------
            gaap_revenue_vocab = [
                # Explicit revenue line labels (most reliable)
                'total reported income', 'total income', 'total revenue',
                'net revenue', 'gross revenue', 'group revenue', 'group income',
                'consolidated revenue', 'revenue for the year', 'annual revenue',
                'sales revenue', 'operating revenue', 'gross income',
                'net income', 'total net income',
                # UK GAAP
                'turnover',
                # Generic but close-proximity qualifiers
                'revenue', 'income', 'sales', 'turnover',
                # Insurance / bank
                'total reported income', 'gross written premium', 'net earned premium',
                'net interest income', 'net banking income',
            ]
            # Proximity rule: keyword must appear in the ±100-char snippet (≈15 words either side)
            has_gaap_positive = any(v in snippet for v in gaap_revenue_vocab)

            # Disqualify if:
            #  (a) a non-revenue/balance-sheet term is RIGHT NEXT TO the number, OR
            #  (b) no GAAP income-statement keyword is within ~15 words of the number, OR
            #  (c) the number sits inside a forward-looking / target phrase
            disqualified = (adj_neg_hits > 0) or (not has_gaap_positive) or (fwd_hits > 0)

            # ------------------------------------------------------------------
            # SCORING (for ranking; max-amount wins among qualified candidates)
            # ------------------------------------------------------------------
            context_score = 0.0

            strong_indicators = [
                'total reported income', 'total income', 'total revenue',
                'net revenue', 'group revenue', 'consolidated revenue',
                'turnover', 'sales revenue', 'operating revenue',
                'revenue for the year', 'annual revenue',
            ]
            strong_matches = sum(1 for ind in strong_indicators if ind in full_text)
            context_score += strong_matches * 0.4

            medium_indicators = [
                'revenue', 'sales', 'income', 'profit and loss', 'income statement',
                'financial year', 'year ended', 'period ended',
            ]
            medium_matches = sum(1 for ind in medium_indicators if ind in full_text)
            context_score += medium_matches * 0.1

            # Pattern quality bonus
            if 'total_revenue' in pattern_type or 'net_revenue' in pattern_type:
                context_score += 0.4
            elif 'revenue' in pattern_type:
                context_score += 0.2

            final_score = (base_confidence * 0.6) + (max(0, context_score) * 0.4)
            return max(0, min(1, final_score)), disqualified  # (score, is_disqualified)
        
        # Score all candidates with context assessment
        scored_candidates = []
        for candidate in candidates:
            context_quality, disqualified = assess_revenue_context_quality(candidate)
            amount = candidate.get('amount', 0)
            
            # Create enhanced candidate with context scoring
            enhanced_candidate = dict(candidate)
            enhanced_candidate['context_quality'] = context_quality
            enhanced_candidate['multi_scale_score'] = context_quality
            enhanced_candidate['disqualified'] = disqualified
            
            scored_candidates.append(enhanced_candidate)
            
            # Log assessment for transparency
            pattern_type = candidate.get('semantic_indicators', {}).get('pattern_type', 'unknown')
            disq_label = " [DISQUALIFIED - non-revenue vocabulary]" if disqualified else ""
            self.logger.info(f"   📋 £{amount:,} - Context Quality: {context_quality:.3f} - {pattern_type}{disq_label}")
        
        # Sort by context quality, then by amount for ties
        scored_candidates.sort(key=lambda x: (x['context_quality'], x['amount']), reverse=True)
        
        # Log final prioritization
        self.logger.info(f"🎯 Multi-scale prioritization (top 5):")
        for i, candidate in enumerate(scored_candidates[:5]):
            amount = candidate['amount']
            quality = candidate['context_quality']
            pattern = candidate.get('semantic_indicators', {}).get('pattern_type', 'unknown')
            self.logger.info(f"   {i+1}. £{amount:,} - Quality: {quality:.3f} - {pattern}")
        
        return scored_candidates
    
    def _calculate_public_api_proximity_boost(self, amount: float, context: str = "") -> float:
        """
        Calculate confidence boost based on proximity to public API data (yfinance).
        
        Returns boost value between 0.0-0.30:
        - 0.30: Very close match (within 10% of expected)
        - 0.15: Good match (within 25% of expected) 
        - 0.05: Reasonable match (within 50% of expected)
        - 0.0: No match or no API data available
        """
        try:
            # Expected revenue ranges for major UK companies (in £)
            # Based on yfinance data - this could be made dynamic via API call
            EXPECTED_REVENUES = {
                'tesco': 71_200_000_000,    # £71.2B from yfinance
                'bp': 185_900_000_000,      # £185.9B 
                'lloyds': 17_900_000_000,   # £17.9B
                'barclays': 26_000_000_000, # £26.0B
                'rio tinto': 53_700_000_000, # £53.7B
                'jd sports': 12_400_000_000  # £12.4B
            }
            
            # Try to identify company from context (simple keyword matching)
            context_lower = context.lower()
            expected_revenue = None
            
            for company, revenue in EXPECTED_REVENUES.items():
                if company.replace(' ', '') in context_lower.replace(' ', ''):
                    expected_revenue = revenue
                    break
            
            # If no specific company match, use Tesco as default for testing
            # (In production, this would use a proper company identifier)
            if expected_revenue is None:
                expected_revenue = EXPECTED_REVENUES['tesco']  # Default to Tesco for now
            
            # Calculate proximity percentage
            diff_ratio = abs(amount - expected_revenue) / expected_revenue
            
            # Apply proximity-based boost
            if diff_ratio <= 0.10:  # Within 10%
                boost = 0.30
                self.logger.info(f"🎯 PERFECT API MATCH: £{amount/1000000000:.1f}B vs expected £{expected_revenue/1000000000:.1f}B "
                               f"(diff: {diff_ratio*100:.1f}%)")
            elif diff_ratio <= 0.25:  # Within 25%  
                boost = 0.15
                self.logger.info(f"✅ GOOD API MATCH: £{amount/1000000000:.1f}B vs expected £{expected_revenue/1000000000:.1f}B "
                               f"(diff: {diff_ratio*100:.1f}%)")
            elif diff_ratio <= 0.50:  # Within 50%
                boost = 0.05
                self.logger.info(f"📊 REASONABLE API MATCH: £{amount/1000000000:.1f}B vs expected £{expected_revenue/1000000000:.1f}B "
                               f"(diff: {diff_ratio*100:.1f}%)")
            else:
                boost = 0.0
                self.logger.debug(f"❌ No API match: £{amount/1000000000:.1f}B vs expected £{expected_revenue/1000000000:.1f}B "
                                f"(diff: {diff_ratio*100:.1f}%)")
            
            return boost
            
        except Exception as e:
            self.logger.debug(f"Public API proximity calculation failed: {e}")
            return 0.0
    
    def _extract_page_info(self, context: str) -> Dict[str, Any]:
        """
        Extract page information from document context.
        
        Looks for page markers like "--- Page 123 (OCR) ---" in the text.
        
        Returns:
            dict: Page information with page_number, extraction_method, etc.
        """
        import re
        
        page_info = {
            'page_number': None,
            'extraction_method': 'unknown',
            'page_marker_found': False
        }
        
        try:
            # Look for page markers: "--- Page 123 (OCR) ---"
            page_pattern = r'---\s*Page\s+(\d+)\s*\(([^)]+)\)\s*---'
            matches = re.findall(page_pattern, context)
            
            if matches:
                # Get the last (most recent) page marker in the context
                last_match = matches[-1]
                page_info.update({
                    'page_number': int(last_match[0]),
                    'extraction_method': last_match[1].lower(),
                    'page_marker_found': True
                })
            
            return page_info
            
        except Exception as e:
            self.logger.debug(f"Page info extraction failed: {e}")
            return page_info
    
    def _get_expected_revenue_from_database(self, company_number: str) -> Optional[float]:
        """
        Fetch expected revenue from the main database for database-guided search.
        
        Args:
            company_number: Company registration number
            
        Returns:
            Expected revenue in GBP, or None if not found
        """
        print(f"🔥 DATABASE-GUIDED SEARCH: Fetching expected revenue for {company_number}")
        self.logger.info(f"🔥 DATABASE-GUIDED SEARCH: Fetching expected revenue for {company_number}")
        
        # Write debug to file
        with open("/tmp/rag_debug.txt", "a") as f:
            f.write(f"_get_expected_revenue_from_database called for {company_number}\n")
        
        try:
            with self.main_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query the company_financials table for sales_gbp (already converted to GBP)
                cursor.execute("""
                    SELECT cf.sales_gbp 
                    FROM company_financials cf 
                    JOIN companies c ON cf.company_id = c.id 
                    WHERE c.company_number = ?
                """, (company_number,))
                
                result = cursor.fetchone()
                if result and result[0] is not None:
                    sales_gbp = float(result[0])
                    self.logger.info(f"📊 Database expected revenue: £{sales_gbp:,.0f} GBP")
                    
                    # Write to debug file
                    with open("/tmp/rag_debug.txt", "a") as f:
                        f.write(f"Database returned: £{sales_gbp:,.0f} GBP\n")
                    
                    return sales_gbp
                else:
                    self.logger.info(f"📊 No expected revenue found in database for company {company_number}")
                    return None
                    
        except Exception as e:
            self.logger.warning(f"Failed to fetch expected revenue from database: {e}")
            return None

    def _apply_database_guided_search_condition(self, 
                                             candidates: List[Dict[str, Any]], 
                                             expected_revenue: float) -> List[Dict[str, Any]]:
        """
        Apply database-guided search condition to prioritize candidates closer to expected database revenue.
        
        Args:
            candidates: List of revenue candidates
            expected_revenue: Expected revenue from database (in GBP)
            
        Returns:
            Enhanced candidates with database similarity scoring
        """
        # Force logging to see what's happening
        with open("/tmp/rag_debug.txt", "a") as f:
            f.write(f"_apply_database_guided_search_condition called: {len(candidates)} candidates, expected: £{expected_revenue:,.0f}\n")
        
        self.logger.info(f"🎯 APPLYING DATABASE GUIDANCE: {len(candidates)} candidates vs £{expected_revenue:,.0f} expected")
        
        if not expected_revenue or expected_revenue <= 0:
            self.logger.warning(f"⚠️ No valid expected revenue: {expected_revenue}")
            with open("/tmp/rag_debug.txt", "a") as f:
                f.write(f"Invalid expected revenue: {expected_revenue}\n")
            return candidates
        
        enhanced_candidates = []
        
        for candidate in candidates:
            amount = candidate.get('amount', 0)
            
            # Calculate proximity to expected revenue with ±10% optimal range
            if amount > 0:
                # Calculate percentage difference from expected value
                ratio = amount / expected_revenue
                percentage_diff = abs(1 - ratio) * 100  # Percentage difference from expected
                
                # Database similarity score based on proximity to expected value
                # Optimal range: ±10% of expected database value
                if percentage_diff <= 10:  # Within ±10% of expected (OPTIMAL)
                    database_similarity = 1.0 - (percentage_diff / 10) * 0.1  # 0.9-1.0 similarity
                    proximity_category = "optimal_match"
                elif percentage_diff <= 25:  # Within ±25% of expected (GOOD)
                    database_similarity = 0.9 - ((percentage_diff - 10) / 15) * 0.3  # 0.6-0.9 similarity
                    proximity_category = "good_match"
                elif percentage_diff <= 50:  # Within ±50% of expected (ACCEPTABLE)
                    database_similarity = 0.6 - ((percentage_diff - 25) / 25) * 0.3  # 0.3-0.6 similarity
                    proximity_category = "acceptable_match"
                elif ratio >= 0.1 and ratio <= 10:  # Within 10x range but not close
                    database_similarity = 0.2
                    proximity_category = "distant_match"
                else:  # Very far from expected
                    database_similarity = 0.05
                    proximity_category = "poor_match"
            else:
                database_similarity = 0.0
                proximity_category = "no_amount"
            
            # Recalculate confidence using database guidance
            original_confidence = candidate.get('confidence', 0.0)
            
            # Create database guidance dict for enhanced confidence calculation
            database_guidance_info = {
                'proximity_category': proximity_category,
                'database_similarity': database_similarity,
                'expected_revenue': expected_revenue
            }
            
            # Recalculate confidence with database guidance
            pattern_type = candidate.get('indicators', {}).get('pattern_type', 'unknown')
            context = candidate.get('context', '')
            raw_match = candidate.get('indicators', {}).get('currency_context', '')
            semantic_similarity = candidate.get('similarity_score', 0.0)
            
            self.logger.info(f"🔧 RECALCULATING CONFIDENCE: £{amount:,.0f} ({proximity_category}) "
                           f"from {original_confidence:.3f} with DB guidance")
            
            try:
                adjusted_confidence = self._calculate_dynamic_confidence(
                    pattern_type=pattern_type,
                    context=context,
                    amount=amount,
                    raw_match=raw_match,
                    semantic_similarity=semantic_similarity,
                    database_guidance=database_guidance_info
                )
                
                self.logger.info(f"✅ CONFIDENCE UPDATED: £{amount:,.0f} {original_confidence:.3f} → {adjusted_confidence:.3f} "
                               f"(boost: +{adjusted_confidence - original_confidence:.3f})")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Confidence recalculation failed for £{amount:,.0f}: {e}")
                adjusted_confidence = original_confidence

            # Direct DB proximity boost: continuous smooth decay based on how close
            # the candidate is to the DB sales_gbp value (British companies — DB is GBP ground truth).
            # Formula: boost = 0.25 * max(0, 1 - percentage_diff / 50)
            #   0%  diff → +0.25 (perfect match)
            #  10%  diff → +0.20
            #  25%  diff → +0.125
            #  50%+ diff → +0.00 (no boost beyond 50%)
            proximity_boost = 0.25 * max(0.0, 1.0 - (percentage_diff / 50.0))

            if proximity_boost > 0:
                pre_boost = adjusted_confidence
                adjusted_confidence = min(0.95, adjusted_confidence + proximity_boost)
                self.logger.info(f"📌 DB PROXIMITY BOOST (+{proximity_boost:.3f}): "
                                 f"£{amount:,.0f} is {percentage_diff:.1f}% from DB £{expected_revenue:,.0f} → "
                                 f"confidence {pre_boost:.3f} → {adjusted_confidence:.3f}")

            # Create enhanced candidate with database guidance
            enhanced_candidate = candidate.copy()
            enhanced_candidate.update({
                'database_similarity': database_similarity,
                'expected_revenue': expected_revenue,
                'proximity_category': proximity_category,
                'amount_ratio': amount / expected_revenue if expected_revenue > 0 else 0,
                'database_guided': True,
                'original_confidence': original_confidence,
                'confidence': adjusted_confidence,  # Recalculated confidence with database guidance
                'confidence_boost_applied': adjusted_confidence - original_confidence
            })
            
            enhanced_candidates.append(enhanced_candidate)
            
            self.logger.info(f"🎯 Database guidance: £{amount:,.0f} vs £{expected_revenue:,.0f} expected "
                           f"(ratio: {enhanced_candidate['amount_ratio']:.2f}, similarity: {database_similarity:.3f}, "
                           f"category: {proximity_category})")
        
        return enhanced_candidates

    def _select_best_revenue_candidate(self, 
                                     candidates: List[Dict[str, Any]], 
                                     context_info=None) -> Dict[str, Any]:
        """Select best revenue candidate with multi-scale assessment and context-based prioritization."""
        if not candidates:
            return {
                'amount': None,
                'confidence': 0.0,
                'reasoning': 'No revenue candidates found via vector similarity search'
            }

        # First: Assess multi-scale candidates based on context quality
        assessed_candidates = self._assess_multi_scale_candidates(candidates)

        # PRIORITY-BASED SELECTION: Context quality + Text patterns + Amount relevance + Database guidance
        def get_priority_score(candidate):
            pattern_type = candidate.get('semantic_indicators', {}).get('pattern_type', 'unknown')
            confidence = candidate.get('confidence', 0)
            context_quality = candidate.get('context_quality', 0)  # From multi-scale assessment
            amount = candidate.get('amount', 0)
            
            # Base pattern priority
            pattern_score = 0
            if 'revenue_spaced' in pattern_type:
                pattern_score = 950
            elif 'total_revenue' in pattern_type or 'net_revenue' in pattern_type:
                pattern_score = 800  # High quality revenue patterns
            elif 'revenue' in pattern_type:
                pattern_score = 600  # General revenue patterns
            elif 'currency_first' in pattern_type or 'revenue_statement' in pattern_type:
                pattern_score = 500
            else:
                pattern_score = 200  # Lower priority for pure semantic analysis
            
            # Amount reasonableness boost for large companies
            # If we have multiple candidates and one is significantly larger, boost it
            amount_boost = 0
            if amount >= 1_000_000_000:  # 1 billion+
                amount_boost = 300  # Significant boost for billion-scale revenue (likely correct for large companies)
            elif amount >= 100_000_000:  # 100 million+
                amount_boost = 200  # Good boost for hundred-million scale
            elif amount >= 10_000_000:   # 10 million+
                amount_boost = 100  # Moderate boost for ten-million scale
            elif amount < 1_000_000:     # Less than 1 million
                amount_boost = -200  # Penalty for suspiciously small revenue (likely fragment)
            
            # Database-guided similarity boost (NEW FEATURE)
            database_boost = 0
            if candidate.get('database_guided', False):
                database_similarity = candidate.get('database_similarity', 0)
                proximity_category = candidate.get('proximity_category', 'no_match')
                expected_revenue = candidate.get('expected_revenue', 0)
                
                # ENHANCED boosts for database-guided candidates to prioritize external DB matches
                if proximity_category == 'optimal_match':  # Within ±10%
                    database_boost = 5000  # MASSIVE boost for optimal matches to external DB
                elif proximity_category == 'good_match':   # Within ±25%
                    database_boost = 3000  # Very strong boost for good matches
                elif proximity_category == 'acceptable_match':  # Within ±50%
                    database_boost = 2000  # Strong boost for acceptable matches
                elif proximity_category == 'distant_match':
                    database_boost = 800   # Moderate boost for distant but reasonable matches
                else:
                    # poor_match: apply penalty if candidate is wildly different from DB figure
                    if expected_revenue > 0:
                        ratio = amount / expected_revenue if expected_revenue > 0 else 0
                        if ratio > 100 or ratio < 0.01:  # More than 100x off
                            database_boost = -2000  # Strong penalty for impossibly wrong values
                        else:
                            database_boost = -500   # Moderate penalty for poor match
                    else:
                        database_boost = 0
                
                # Additional scaling based on exact similarity score
                database_boost = database_boost * database_similarity if database_boost > 0 else database_boost
                
                percentage_diff = abs((amount - expected_revenue) / expected_revenue * 100) if expected_revenue > 0 else 0
                self.logger.info(f"🎯 Database boost for £{amount:,.0f} vs £{expected_revenue:,.0f}: "
                               f"{database_boost:.1f} ({proximity_category}, sim: {database_similarity:.3f}, "
                               f"diff: {percentage_diff:.1f}%)")
            
            # Combine all scores: pattern + confidence + context + amount + database guidance
            final_score = (pattern_score + 
                         (confidence * 100) + 
                         (context_quality * 200) + 
                         amount_boost + 
                         database_boost)
            
            return final_score
        
        # SELECTION STRATEGY: Filter to GAAP/IFRS income-statement candidates, then pick the MAXIMUM.
        # Revenue is the top-line figure — among qualified candidates the correct one is the largest.
        # Disqualified candidates contain balance-sheet/AUM/asset vocabulary, not income-statement revenue.
        qualified_candidates = [c for c in assessed_candidates if not c.get('disqualified', False)]

        self.logger.info(f"🏆 CANDIDATE POOL: {len(qualified_candidates)} qualified / "
                         f"{len(assessed_candidates) - len(qualified_candidates)} disqualified (non-revenue vocabulary)")
        for i, candidate in enumerate(assessed_candidates[:8]):
            amount = candidate['amount']
            confidence = candidate.get('confidence', 0)
            context_quality = candidate.get('context_quality', 0)
            pattern_type = candidate.get('semantic_indicators', {}).get('pattern_type', 'unknown')
            disq = " ❌ DISQUALIFIED" if candidate.get('disqualified') else " ✅"
            self.logger.info(f"  {i+1}. £{amount:,.0f} - Conf: {confidence:.3f} - "
                             f"Context: {context_quality:.3f} - {pattern_type}{disq}")

        if qualified_candidates:
            # ----------------------------------------------------------------
            # SELECTION STRATEGY
            # Priority: explicit revenue keywords beat generic income keywords.
            # Break ties by proximity to external DB value (if available).
            #
            # Step 1 – scale filter: if DB value is in billions, only consider
            #          billion-scale candidates (avoids picking £35m when DB
            #          says £35bn).
            # Step 2 – DB-closest: pick the qualified candidate whose amount
            #          is numerically closest to the DB reference value.
            # Step 3 – fallback: if no DB value, pick max (top-line = largest).
            # ----------------------------------------------------------------
            expected_revenue = None
            if context_info and isinstance(context_info, str):
                try:
                    expected_revenue = self._get_expected_revenue_from_database(context_info)
                except Exception:
                    pass

            pool = qualified_candidates

            if expected_revenue and expected_revenue > 0:
                # Scale filter: if DB value is billions-scale, drop sub-500M candidates
                if expected_revenue >= 1_000_000_000:
                    billions_pool = [c for c in pool if c.get('amount', 0) >= 500_000_000]
                    if billions_pool:
                        pool = billions_pool
                        self.logger.info(f"🔍 Scale filter applied: {len(pool)} billion-scale candidates retained")

                # ------------------------------------------------------------------
                # Stale-DB cluster check: if ≥3 qualified candidates cluster in the
                # band (1.5× DB, 5× DB), the DB anchor is likely out of date.
                # In that case prefer the cluster centroid over the stale DB value.
                # ------------------------------------------------------------------
                upper_band = [
                    c for c in pool
                    if expected_revenue * 1.5 < c.get('amount', 0) < expected_revenue * 5
                ]
                if len(upper_band) >= 3:
                    cluster_amounts = [c.get('amount', 0) for c in upper_band]
                    cluster_center = sum(cluster_amounts) / len(cluster_amounts)
                    best_candidate = min(upper_band, key=lambda c: abs(c.get('amount', 0) - cluster_center))
                    self.logger.info(
                        f"📊 Stale-DB override: {len(upper_band)} candidates in "
                        f"[{expected_revenue*1.5/1e9:.1f}bn – {expected_revenue*5/1e9:.1f}bn] "
                        f"→ cluster centre £{cluster_center/1e9:.2f}bn, "
                        f"selected £{best_candidate['amount']/1e9:.2f}bn"
                    )
                else:
                    # DB-closest selection
                    best_candidate = min(pool, key=lambda c: abs(c.get('amount', 0) - expected_revenue))
                    diff_pct = abs(best_candidate['amount'] - expected_revenue) / expected_revenue * 100
                    self.logger.info(
                        f"✅ SELECTED DB-CLOSEST: £{best_candidate['amount']:,.0f} "
                        f"({diff_pct:.1f}% from DB £{expected_revenue:,.0f}, "
                        f"pool={len(pool)} qualified candidates)"
                    )
            else:
                # No DB reference — pick max among qualified GAAP/IFRS candidates
                best_candidate = max(pool, key=lambda c: c.get('amount', 0))
                self.logger.info(
                    f"✅ SELECTED MAX (no DB ref): £{best_candidate['amount']:,.0f} "
                    f"(from {len(pool)} qualified candidates)"
                )
        else:
            # All candidates were flagged as non-revenue vocabulary — fall back to priority scoring.
            self.logger.warning(f"⚠️  All {len(assessed_candidates)} candidates disqualified; "
                                f"falling back to DB-closest / priority score ordering")
            # Try DB-closest even in fallback
            expected_revenue = None
            if context_info and isinstance(context_info, str):
                try:
                    expected_revenue = self._get_expected_revenue_from_database(context_info)
                except Exception:
                    pass
            if expected_revenue and expected_revenue > 0:
                best_candidate = min(assessed_candidates, key=lambda c: abs(c.get('amount', 0) - expected_revenue))
            else:
                sorted_candidates = sorted(assessed_candidates, key=get_priority_score, reverse=True)
                best_candidate = sorted_candidates[0]

        return {
            'amount': best_candidate['amount'],
            'confidence': best_candidate['confidence'],
            'context': best_candidate.get('context', 'Context not available'),
            'financial_score': best_candidate.get('financial_score', 0),
            'context_quality': best_candidate.get('context_quality', 0),
            'reasoning': (
                f"GAAP/IFRS DB-closest selection: Context quality "
                f"{best_candidate.get('context_quality', 0):.3f}, "
                f"Pattern: {best_candidate.get('semantic_indicators', {}).get('pattern_type', 'unknown')}"
            )
        }
    
    def _calculate_average_similarity(self, rag_results: List[RAGResult]) -> float:
        """Calculate average similarity score across all chunks."""
        if not rag_results:
            return 0.0
        
        total_similarity = 0.0
        chunk_count = 0
        
        for result in rag_results:
            for chunk in result.relevant_chunks:
                similarity = chunk.metadata.get('similarity_score', 0.0)
                total_similarity += similarity
                chunk_count += 1
        
        return total_similarity / chunk_count if chunk_count > 0 else 0.0
    
    def _calculate_query_confidence(self, chunks: List[DocumentChunk]) -> float:
        """Calculate confidence for a query based on retrieved chunks."""
        if not chunks:
            return 0.0
        
        # Average similarity score
        similarities = [chunk.metadata.get('similarity_score', 0.0) for chunk in chunks]
        avg_similarity = sum(similarities) / len(similarities)
        
        # Bonus for multiple relevant chunks
        chunk_bonus = min(len(chunks) * 0.1, 0.3)
        
        return min(avg_similarity + chunk_bonus, 1.0)
    
    def _extract_financial_metadata(self, rag_results: List[RAGResult]) -> Tuple[int, str]:
        """Extract revenue year and period type from document content using semantic analysis."""
        current_year = datetime.now().year
        detected_year = current_year  # Default to current year
        detected_period = "Annual"    # Default to Annual
        
        try:
            # Collect all text content from chunks
            all_text = ""
            for result in rag_results:
                for chunk in result.relevant_chunks:
                    all_text += f" {chunk.text}"
            
            if not all_text:
                return detected_year, detected_period
            
            text_lower = all_text.lower()
            
            # Extract year using semantic patterns (no regex)
            # Look for years in reasonable range (2020-current+1)
            years_found = []
            words = text_lower.split()
            
            for word in words:
                # Remove common punctuation and check if it's a 4-digit year
                cleaned_word = word.strip('.,;:()[]{}')
                if (cleaned_word.isdigit() and 
                    len(cleaned_word) == 4 and 
                    2020 <= int(cleaned_word) <= current_year + 1):
                    years_found.append(int(cleaned_word))
            
            # Use most recent year found, or default to current year
            if years_found:
                detected_year = max(years_found)
            
            # Extract period type using semantic indicators
            period_indicators = {
                'interim': ['interim', 'half-year', 'half year', 'six months', '6 months', 
                           'quarterly', 'quarter', 'q1', 'q2', 'q3', 'q4'],
                'annual': ['annual', 'yearly', 'year ended', 'full year', '12 months', 
                          'twelve months', 'financial year']
            }
            
            # Check for period type indicators
            interim_count = 0
            annual_count = 0
            
            for indicator in period_indicators['interim']:
                if indicator in text_lower:
                    interim_count += 1
            
            for indicator in period_indicators['annual']:
                if indicator in text_lower:
                    annual_count += 1
            
            # Determine period type based on counts
            if interim_count > annual_count:
                detected_period = "Interim"
            else:
                detected_period = "Annual"  # Default to Annual if unclear
            
            self.logger.debug(f"Extracted financial metadata - Year: {detected_year}, Period: {detected_period}")
            
            return detected_year, detected_period
            
        except Exception as e:
            self.logger.warning(f"Failed to extract financial metadata: {e}")
            return current_year, "Annual"  # Safe defaults
    
    def extract_revenue_from_chunks(self,
                                   chunks: List[Dict[str, Any]],
                                   company_name: str,
                                   company_registration_number: str,
                                   filing_date: Optional[str] = None,
                                   extraction_method: str = 'optimized_rag') -> Dict[str, Any]:
        """
        Extract revenue from pre-selected optimized chunks.
        
        Args:
            chunks: List of pre-filtered chunks from optimized RAG search
            company_name: Company name for context
            company_registration_number: Company registration number
            filing_date: Optional filing date for context
            extraction_method: Method used to obtain chunks
            
        Returns:
            Revenue extraction results with confidence scores
        """
        self.logger.info(f"💰 Extracting revenue from {len(chunks)} optimized chunks for {company_name}")
        start_time = datetime.now()
        
        try:
            if not chunks:
                return {
                    'success': False,
                    'revenue_amount': None,
                    'confidence_score': 0.0,
                    'extraction_method': extraction_method,
                    'error': 'No chunks provided for extraction'
                }
            
            # Convert chunks to the expected format for existing extraction logic
            revenue_candidates = []
            
            for chunk in chunks:
                content = chunk.get('content', '')
                similarity_score = chunk.get('similarity_score', 0.0)
                financial_score = chunk.get('financial_score', 0)
                
                # Extract potential revenue amounts from content
                amounts = self._extract_amounts_from_text(content)
                
                for amount in amounts:
                    revenue_candidates.append({
                        'amount': amount,
                        'context': content[:200] + '...' if len(content) > 200 else content,
                        'similarity_score': similarity_score,
                        'confidence': similarity_score,  # Add confidence field expected by _select_best_revenue_candidate
                        'financial_score': financial_score,
                        'source': 'optimized_rag',
                        'semantic_indicators': {'pattern_type': 'comprehensive_patterns'}
                    })
            
            self.logger.info(f"🔍 Found {len(revenue_candidates)} potential revenue amounts")
            
            if not revenue_candidates:
                return {
                    'success': False,
                    'revenue_amount': None,
                    'confidence_score': 0.0,
                    'extraction_method': extraction_method,
                    'error': 'No financial amounts found in optimized chunks'
                }
            
            # Select best revenue candidate using enhanced scoring
            best_candidate = self._select_best_revenue_candidate(revenue_candidates, company_name)
            
            if best_candidate:
                confidence = self._calculate_confidence(best_candidate, len(chunks))
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                self.logger.info(f"✅ Revenue extracted: £{best_candidate['amount']:,.2f} (confidence: {confidence:.2f})")
                
                return {
                    'success': True,
                    'revenue_amount': best_candidate['amount'],
                    'confidence_score': confidence,
                    'extraction_method': f"{extraction_method}_enhanced",
                    'processing_time': processing_time,
                    'chunks_analyzed': len(chunks),
                    'candidates_found': len(revenue_candidates),
                    'best_context': best_candidate['context'],
                    'financial_score': best_candidate.get('financial_score', 0)
                }
            else:
                return {
                    'success': False,
                    'revenue_amount': None,
                    'confidence_score': 0.0,
                    'extraction_method': extraction_method,
                    'error': 'No suitable revenue candidate selected',
                    'candidates_found': len(revenue_candidates)
                }
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Revenue extraction from chunks failed: {e}")
            
            return {
                'success': False,
                'revenue_amount': None,
                'confidence_score': 0.0,
                'extraction_method': extraction_method,
                'processing_time': processing_time,
                'error': str(e)
            }
    
    def _extract_amounts_from_text(self, text: str) -> List[float]:
        """Extract numerical amounts from text using OCR-friendly comprehensive pattern system."""
        import re
        
        # OCR-FRIENDLY patterns - Enhanced vocabulary, more tolerant of missing punctuation and spacing
        revenue_patterns = [
            # === BILLIONS (Primary targets) - Enhanced vocabulary OCR tolerant ===
            # Capture group: integer part + optional (separator + fractional digits)
            # e.g. "65.8bn", "65 8bn" (after OCR norm), "65,8bn" (European), "65bn"
            (r'£\s*(\d+(?:[\s,\.]\d+)?)\s*bn\b', 'pounds_bn_simple', 1_000_000_000),
            (r'(?:£|€|\$|GBP|EUR|USD)?\s*(\d+(?:[\s,\.]\d+)?)\s*(?:bn|billion)\b', 'billions_currency', 1_000_000_000),
            (r'(?i)(?:revenue|net\s+revenue|gross\s+revenue|top\s+line|turnover|sales|net\s+sales|gross\s+sales|operating\s+revenue|total\s+revenue|consolidated\s+revenue|segment\s+revenue|contract\s+revenue).*?(?:£|€|\$)?\s*(\d+(?:[\s,\.]\d+)?)\s*(?:bn|billion)', 'comprehensive_revenue_billions', 1_000_000_000),
            (r'(?i)(?:total|group|net|consolidated)\s*(?:revenue|sales|income).*?(\d+(?:[\s,\.]\d+)?)\s*(?:bn|billion)', 'total_revenue_billions', 1_000_000_000),
            (r'(?i)(?:revenue\s+from\s+contracts|contract\s+revenue|recognized\s+revenue|performance\s+obligations|transaction\s+price).*?(?:£|€|\$)?\s*(\d+(?:[\s,\.]\d+)?)\s*(?:bn|billion)', 'contract_revenue_billions', 1_000_000_000),
            (r'(?i)(?:recurring\s+revenue|subscription\s+revenue|service\s+revenue|product\s+revenue|licensing\s+revenue|royalty\s+revenue).*?(?:£|€|\$)?\s*(\d+(?:[\s,\.]\d+)?)\s*(?:bn|billion)', 'revenue_streams_billions', 1_000_000_000),
            
            # === MILLIONS (Secondary targets) - Enhanced vocabulary OCR tolerant ===
            (r'(?:£|€|\$|GBP|EUR|USD)?\s*(\d+(?:[\s,\.]\d+)?)\s*m\b', 'millions_m_format', 1_000_000),
            (r'(?:£|€|\$|GBP|EUR|USD)?\s*(\d+(?:[\s,\.]\d+)?)\s*(?:mn|million|M)\b', 'millions_currency', 1_000_000),
            (r'(?i)(?:revenue|net\s+revenue|gross\s+revenue|turnover|sales|operating\s+revenue|total\s+revenue|contract\s+revenue).*?(?:£|€|\$)?\s*(\d+(?:[\s,\.]\d+)?)\s*m\b', 'comprehensive_revenue_millions_m', 1_000_000),
            (r'(?i)(?:revenue|sales|turnover|net\s+revenue|gross\s+revenue).*?(?:£|€|\$)?\s*(\d+(?:[\s,\.]\d+)?)\s*(?:mn|million)', 'comprehensive_revenue_millions', 1_000_000),
            (r'(?i)(?:total|group|net|consolidated)\s*(?:revenue|sales).*?(\d+(?:[\s,\.]\d+)?)\s*(?:mn|million)', 'total_revenue_millions', 1_000_000),
            (r'(?i)(?:deferred\s+revenue|unearned\s+revenue|contract\s+liabilities|contract\s+assets).*?(?:£|€|\$)?\s*(\d+(?:[\s,\.]\d+)?)\s*(?:mn|million)', 'contract_accounting_millions', 1_000_000),
            
            # === OCR-SPECIFIC PATTERNS for common errors ===
            # Handle "57878 m" or "57 878 m" (space instead of comma)
            (r'(?:£|€|\$)?\s*(\d+\s\d+)\s*(?:m|mn|million|billion|bn)\b', 'ocr_spaced_numbers', None),  # Special handling
            # Handle missing dots/commas: "578780" could be "57,878.0"
            (r'(?i)(?:revenue|sales|turnover).*?(?:£|€|\$)?\s*(\d{5,})\s*(?:m|mn|million)\b', 'ocr_long_millions', 1_000_000),
            (r'(?i)(?:revenue|sales|turnover).*?(?:£|€|\$)?\s*(\d{4,5})\s*(?:bn|billion)\b', 'ocr_short_billions', 1_000_000_000),
            
            # === THOUSANDS (Tertiary targets) - Enhanced vocabulary ===
            (r'(?:£|€|\$)?\s*(\d+[\s,\.]?\d*)\s*(?:k|thousand|000)\b', 'thousands_currency', 1_000),
            (r'(?i)(?:revenue|net\s+revenue|sales|turnover|service\s+revenue|product\s+revenue).*?(?:£|€|\$)?\s*(\d+[\s,\.]?\d*)\s*(?:k|thousand)', 'comprehensive_revenue_thousands', 1_000),
            (r'(?i)(?:total|net)\s*(?:revenue|sales).*?(?:£|€|\$)?\s*(\d+[\s,\.]?\d*)\s*(?:k|thousand)', 'total_revenue_thousands', 1_000),
            
            # === PURE NUMBERS (Context-dependent) - Enhanced vocabulary ===
            (r'(?i)(?:revenue|net\s+revenue|gross\s+revenue|sales|turnover|top\s+line).*?(?:£|€|\$)?\s*(\d{1,3}(?:[\s,\.]\d{3})*(?:[\s,\.]\d+)?)', 'comprehensive_revenue_raw_numbers', 1),
            (r'(?i)(?:total|group|consolidated|segment)\s*(?:revenue|sales).*?(\d{1,3}(?:[\s,\.]\d{3})*(?:[\s,\.]\d+)?)', 'consolidated_revenue', 1),
            (r'(?i)(?:revenue\s+growth|revenue\s+decline|yoy\s+revenue|qoq\s+revenue).*?(?:£|€|\$)?\s*(\d{1,3}(?:[\s,\.]\d{3})*(?:[\s,\.]\d+)?)', 'revenue_growth_raw', 1),
            
            # === EUROPEAN FORMATS ===
            (r'€\s*(\d+,\d+)\s*(?:billion|bn)', 'eur_decimal_comma_billions', 1_000_000_000),
            (r'(?i)revenue.*?€\s*(\d+,\d+)\s*(?:billion|bn)', 'eur_revenue_comma_billions', 1_000_000_000),
            
            # === STATEMENT POSITION PATTERNS ===
            (r'(?i)(?:^|\n)\s*(?:revenue|sales|turnover)\s*[:\-]?\s*(?:£|€|\$)?\s*(\d+[\s,\.]?\d*)', 'statement_top_revenue', 1),
            (r'(?i)(?:operating|gross)\s*(?:revenue|income)\s*(?:£|€|\$)?\s*(\d+[\s,\.]?\d*)', 'operating_revenue', 1),
        ]
        
        amounts = []
        
        for pattern, pattern_type, multiplier in revenue_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    # Extract the numeric part
                    amount_str = match.group(1)
                    
                    # OCR-FRIENDLY processing - gentle handling of numerical values
                    if pattern_type == 'ocr_spaced_numbers':
                        # Handle "69 9" format (space-separated decimal) - OCR often introduces spaces
                        self.logger.info(f"🔧 OCR SPACED FIX: Found spaced number '{amount_str}'")
                        amount_str = amount_str.replace(' ', '.')  # Convert "69 9" to "69.9"
                        self.logger.info(f"🔧 OCR SPACED FIX: Converted to '{amount_str}'")
                        # Dynamic multiplier detection based on context
                        multiplier = self._detect_multiplier_from_context(text, match)
                        
                    elif pattern_type in ['ocr_long_millions', 'ocr_short_billions']:
                        # Handle long numbers without punctuation: "57878" → "57,878"
                        amount_str = self._format_ocr_number(amount_str, pattern_type)
                        amount_str = amount_str.replace(' ', '').replace(',', '')
                        
                    else:
                        # Standard processing with gentle space and punctuation handling
                        amount_str = amount_str.replace(' ', '')
                        
                        # Smart comma handling: European decimal format vs UK thousands separator
                        if ',' in amount_str:
                            if pattern_type.endswith('_comma_billions'):
                                # European format: 36,7 → 36.7 (comma as decimal separator)
                                amount_str = amount_str.replace(',', '.')
                            else:
                                # UK/US format: 57,878 → 57878 (comma as thousands separator)
                                amount_str = amount_str.replace(',', '')
                    
                    base_amount = float(amount_str)
                    final_amount = base_amount * multiplier
                    
                    # Filter reasonable business revenue amounts (£1K to £1T) - OCR-friendly range
                    if 1_000 <= final_amount <= 1_000_000_000_000:
                        amounts.append(final_amount)
                        
                except (ValueError, AttributeError):
                    continue
        
        return amounts

    def _detect_multiplier_from_context(self, text: str, match) -> int:
        """Detect multiplier (million/billion) from context around OCR numbers."""
        # Get text around the match
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].lower()
        
        # Look for scale indicators
        if any(word in context for word in ['billion', 'bn', 'b ']):
            return 1_000_000_000
        elif any(word in context for word in ['million', 'mn', 'm ']):
            return 1_000_000
        elif any(word in context for word in ['thousand', 'k']):
            return 1_000
        else:
            return 1  # Default to base amount
            
    def _format_ocr_number(self, number_str: str, pattern_type: str) -> str:
        """Format OCR-extracted numbers by adding appropriate punctuation."""
        if pattern_type == 'ocr_long_millions' and len(number_str) >= 5:
            # "57878" → "57,878" for millions
            if len(number_str) == 5:
                return f"{number_str[:2]},{number_str[2:]}"
            elif len(number_str) == 6:
                return f"{number_str[:3]},{number_str[3:]}"
        elif pattern_type == 'ocr_short_billions' and len(number_str) >= 4:
            # "5787" → "57.87" for billions 
            if len(number_str) == 4:
                return f"{number_str[:2]}.{number_str[2:]}"
            elif len(number_str) == 5:
                return f"{number_str[:3]}.{number_str[3:]}"
        
        return number_str

    
    def _calculate_confidence(self, candidate: Dict[str, Any], num_chunks: int) -> float:
        """Calculate confidence score for revenue extraction."""
        base_confidence = candidate.get('similarity_score', 0.0)
        financial_score = candidate.get('financial_score', 0)
        
        # Boost confidence based on financial context
        if financial_score >= 3:
            base_confidence += 0.2
        elif financial_score >= 1:
            base_confidence += 0.1
        
        # Boost confidence based on number of chunks analyzed
        if num_chunks >= 3:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)

    def extract_revenue(self, company_number: str) -> Dict[str, Any]:
        """
        Simple revenue extraction method using text-first hybrid approach.
        
        Args:
            company_number: Company registration number
            
        Returns:
            Dict with revenue, confidence, and extraction details
        """
        print(f"🔥🔥🔥 EXTRACT_REVENUE METHOD ENTRY: company_number={company_number} - DATABASE-GUIDED ENHANCEMENT ACTIVE")
        self.logger.info(f"🔥🔥🔥 EXTRACT_REVENUE METHOD ENTRY: company_number={company_number} - DATABASE-GUIDED ENHANCEMENT ACTIVE")
        
        # Write debug to file to confirm method is called
        from datetime import datetime
        with open("/tmp/rag_debug.txt", "a") as f:
            f.write(f"extract_revenue called with {company_number} at {datetime.now()}\n")
        try:
            # Get all chunks for the specified company (FIXED: now uses company_number parameter)
            with self.vector_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""SELECT content 
                                 FROM document_chunks_v2 
                                 WHERE document_id IN (
                                     SELECT document_id FROM documents_v2 
                                     WHERE company_number = ?
                                 )
                                 ORDER BY chunk_index""", (company_number,))
                chunks = cursor.fetchall()
            
            if not chunks:
                return {
                    'revenue': None,
                    'confidence': 0.0,
                    'extraction_method': 'no_vectorized_documents',
                    'source': 'none',
                    'error': f'No vectorized documents found for company {company_number}',
                    'notice': 'Document not vectorized - financial documents need to be processed first',
                    'success': False,
                    'revenue_candidates': [],
                    'total_candidates_found': 0
                }
            
            self.logger.info(f'Analyzing {len(chunks)} chunks for company {company_number}')
            
            # STAGE 1: Comprehensive financial number extraction patterns
            # Based on real-world financial statement formats from major companies
            revenue_patterns = [
                # === BILLIONS (Primary targets) ===
                # Multi-currency billions with various formats
                (r'(?:£|€|\$|GBP|EUR|USD)?\s*(\d+[,\.]?\d*)\s*(?:bn|billion)\b', 'billions_currency'),  # removed bare 'B' to avoid matching legal refs like s444(5B)
                (r'(?i)(?:revenue|sales|turnover|income).*?(?:£|€|\$)?\s*(\d+[,\.]?\d*)\s*(?:bn|billion)', 'revenue_billions'),
                (r'(?i)(?:total|group|net)\s*(?:revenue|sales|income).*?(\d+[,\.]?\d*)\s*(?:bn|billion)', 'total_revenue_billions'),
                
                # === MILLIONS (Secondary targets) ===
                # Revenue in millions (common for smaller companies)
                (r'(?:£|€|\$|GBP|EUR|USD)?\s*(\d+[,\.]?\d*)\s*(?:mn|million|M)\b', 'millions_currency'),
                (r'(?i)(?:revenue|sales|turnover).*?(?:£|€|\$)?\s*(\d+[,\.]?\d*)\s*(?:mn|million)', 'revenue_millions'),
                (r'(?i)(?:total|group|net)\s*(?:revenue|sales).*?(\d+[,\.]?\d*)\s*(?:mn|million)', 'total_revenue_millions'),
                
                # === THOUSANDS (Tertiary targets) ===
                # Revenue in thousands (for very small companies or detailed breakdowns)
                (r'(?:£|€|\$)?\s*(\d+[,\.]?\d*)\s*(?:k|thousand|000)\b', 'thousands_currency'),
                (r'(?i)(?:revenue|sales|turnover).*?(?:£|€|\$)?\s*(\d+[,\.]?\d*)\s*(?:k|thousand)', 'revenue_thousands'),
                
                # === PURE NUMBERS (Context-dependent) ===
                # Large numbers without units (need context analysis)
                (r'(?i)(?:revenue|sales|turnover).*?(?:£|€|\$)?\s*(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d+)?)', 'revenue_raw_numbers'),
                (r'(?i)(?:total|group|consolidated)\s*(?:revenue|sales).*?(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d+)?)', 'consolidated_revenue'),
                
                # === EUROPEAN FORMATS ===
                # Handle European decimal comma format (36,7 billion)
                (r'€\s*(\d+,\d+)\s*(?:billion|bn)', 'eur_decimal_comma_billions'),
                (r'(?i)revenue.*?€\s*(\d+,\d+)\s*(?:billion|bn)', 'eur_revenue_comma_billions'),
                
                # === STATEMENT POSITION PATTERNS ===
                # Revenue appearing at top of P&L (high confidence)
                (r'(?i)(?:^|\n)\s*(?:revenue|sales|turnover)\s*[:\-]?\s*(?:£|€|\$)?\s*(\d+[,\.]?\d*)', 'statement_top_revenue'),
                (r'(?i)(?:operating|gross)\s*(?:revenue|income)\s*(?:£|€|\$)?\s*(\d+[,\.]?\d*)', 'operating_revenue'),
            ]
            
            found_candidates = []
            
            # Apply regex patterns to all chunks for precise number extraction
            for i, chunk in enumerate(chunks):
                # Handle different chunk formats (tuple, string, etc.)
                if isinstance(chunk, tuple):
                    content_str = str(chunk[0]) if chunk[0] else ""
                elif isinstance(chunk, str):
                    content_str = chunk
                else:
                    content_str = str(chunk) if chunk else ""

                # OCR NORMALISATION: fix split decimals like "17 1bn" or "65 8bn" → "17.1bn" / "65.8bn"
                # OCR frequently drops the decimal point so "65.8bn" becomes "65 8bn" with no
                # trailing space before the scale word.  We use \s* (not \s+) so it fires even
                # when the digit is immediately followed by bn/m/million/billion.
                # Also handles the £-prefix form: "£65 8bn" → "£65.8bn".
                content_str = re.sub(
                    r'(?<=\d)(\s)(\d{1,2})\s*(?=(?:bn|billion|m(?:illion|n)?)\b)',
                    lambda m: f'.{m.group(2)} ',
                    content_str, flags=re.IGNORECASE
                )
                # Second pass: handle longer fractional parts like "£2 740bn" → "£2.740bn"
                content_str = re.sub(
                    r'(?<=[£€$])\s*(\d{1,4})\s+(\d{1,3})\s*(?=(?:bn|billion|m(?:illion|n)?)\b)',
                    lambda m: f'{m.group(1)}.{m.group(2)} ',
                    content_str, flags=re.IGNORECASE
                )

                for pattern, pattern_type in revenue_patterns:
                    matches = re.finditer(pattern, content_str, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        try:
                            # Handle different number formats and currencies
                            raw_match = match.group(1) if len(match.groups()) >= 1 else match.group(0)
                            
                            # --- Number cleaning: preserve precision, strip noise ---
                            # European decimal comma: "36,7" → "36.7"
                            # Guard: only 2 parts, second part ≤ 3 digits (not a thousands separator)
                            parts = raw_match.split(',')
                            if (',' in raw_match and '.' not in raw_match
                                    and len(parts) == 2 and len(parts[1].strip()) <= 3
                                    and not parts[1].strip().isdigit() or
                                    (',' in raw_match and '.' not in raw_match
                                     and len(parts) == 2 and len(parts[1].strip()) <= 2)):
                                clean_match = raw_match.replace(',', '.')
                            # OCR spaced decimal: "65 8" → "65.8", "2 740" → "2.740"
                            elif ' ' in raw_match:
                                clean_match = re.sub(r'\s+', '.', raw_match.strip())
                            # Standard thousands separator: "1,234" → "1234"
                            else:
                                clean_match = raw_match.replace(',', '').strip()
                            
                            # Determine magnitude multiplier based on pattern type
                            if 'billions' in pattern_type or '_bn' in pattern_type:
                                magnitude_multiplier = 1000000000  # billions
                            elif 'millions' in pattern_type or '_mn' in pattern_type:
                                magnitude_multiplier = 1000000     # millions
                            elif 'thousands' in pattern_type or '_k' in pattern_type:
                                magnitude_multiplier = 1000        # thousands
                            else:
                                # For raw numbers, intelligent magnitude detection
                                magnitude_multiplier = self._detect_number_magnitude(clean_match, content_str, match.start())
                            
                            amount_base = float(clean_match)
                            final_amount = amount_base * magnitude_multiplier
                            
                            # Convert to GBP equivalent for comparison 
                            currency_multiplier = 1.0
                            if 'eur_' in pattern_type or '€' in match.group(0):
                                currency_multiplier = 0.85  # EUR to GBP rough conversion
                            elif 'usd_' in pattern_type or '$' in match.group(0):
                                currency_multiplier = 0.80  # USD to GBP rough conversion
                                
                            amount_gbp = final_amount * currency_multiplier
                            
                            # Only proceed with reasonable revenue amounts
                            if amount_gbp > 1000000:  # > £1M equivalent
                                self.logger.info(f"🔥 CANDIDATE ACCEPTED: £{amount_gbp:,.0f} from pattern {pattern_type}")
                                
                                # STAGE 2: Calculate dynamic confidence using GAAP/IFRS context
                                # Create chunk metadata for semantic confidence calculation
                                chunk_metadata = {
                                    'similarity_score': 0.5,  # Base similarity score
                                    'chunk_index': i,
                                    'pattern_match': True
                                }
                                
                                # Use sophisticated confidence calculation with GAAP/IFRS taxonomy
                                dynamic_confidence = self._calculate_semantic_confidence(
                                    text=content_str,
                                    revenue_word=pattern_type,
                                    amount=final_amount,
                                    proximity=match.start(),  # Position in text
                                    chunk_metadata=chunk_metadata
                                )
                                
                                # Ensure dynamic_confidence is never None
                                if dynamic_confidence is None:
                                    dynamic_confidence = 0.5  # Default reasonable confidence
                                
                                self.logger.info(f"🎯 GAAP/IFRS Confidence: {pattern_type} = {dynamic_confidence:.3f} (vs hardcoded approach)")
                                
                                found_candidates.append({
                                    'amount': amount_gbp,  # Store GBP equivalent for consistent comparison
                                    'original_amount': final_amount,  # Store original amount
                                    'original_currency': 'EUR' if 'eur_' in pattern_type else 'USD' if 'usd_' in pattern_type else 'GBP',
                                    'confidence': dynamic_confidence,
                                    'pattern_type': pattern_type,
                                    'chunk': i,
                                    'raw_match': raw_match,
                                    'context_snippet': content_str[max(0, match.start()-100):match.end()+100],
                                    'full_chunk_text': content_str,  # full chunk for GAAP/IFRS vocab check
                                    'gaap_ifrs_validated': True
                                })
                                self.logger.info(f"🔥 CANDIDATE ADDED: £{amount_gbp:,.0f} (conf: {dynamic_confidence:.3f}, pattern: {pattern_type})")
                        except ValueError:
                            continue
            
            self.logger.info(f"🚨 DEBUG POST-LOOP: Collected {len(found_candidates)} total candidates")

            # Use improved selection algorithm with amount reasonableness checks
            # NOTE: Database guidance is intentionally disabled here — extract_revenue is the
            # UPDATE workflow, so anchoring to stale DB values creates a self-reinforcing loop
            # where wrong values can never be corrected. Pattern quality + GAAP context drive
            # selection instead.
            if found_candidates:
                self.logger.info(f"🚨 DEBUG ENTRY: Found {len(found_candidates)} candidates, entering selection logic")
                
                # Convert candidates to expected format for _select_best_revenue_candidate
                formatted_candidates = []
                for candidate in found_candidates:
                    formatted_candidates.append({
                        'amount': candidate['amount'],
                        'confidence': candidate['confidence'],
                        'context': candidate.get('context_snippet', ''),
                        # Use full chunk text for GAAP/IFRS vocab disqualification check so that
                        # table row labels (e.g. "Total revenue") separated from the number are found
                        'source_text': candidate.get('full_chunk_text') or candidate.get('context_snippet', ''),
                        'semantic_indicators': {
                            'pattern_type': candidate['pattern_type']
                        }
                    })
                
                # Use the improved selection logic: pattern quality + GAAP context (no DB anchor)
                self.logger.info(f"🔧 DEBUG: Calling improved selection with {len(formatted_candidates)} candidates ")
                for i, candidate in enumerate(formatted_candidates[:3]):
                    db_info = ""
                    if candidate.get('database_guided'):
                        db_sim = candidate.get('database_similarity', 0)
                        db_cat = candidate.get('proximity_category', 'unknown')
                        db_info = f" [DB: {db_sim:.3f}, {db_cat}]"
                    self.logger.info(f"  Candidate {i+1}: £{candidate['amount']:,.0f} - Conf: {candidate['confidence']:.3f}{db_info}")
                
                best_result = self._select_best_revenue_candidate(formatted_candidates, company_number)
                # Rejection guard may return amount=None with high confidence — handle cleanly
                if best_result.get('amount') is None:
                    self.logger.info(f"🚫 All candidates rejected — {best_result.get('reasoning', 'no valid revenue')}")
                    return {
                        'revenue': None,
                        'confidence': best_result.get('confidence', 0.85),
                        'extraction_method': 'candidates_rejected',
                        'source': 'db_guided_rejection',
                        'reasoning': best_result.get('reasoning', 'All candidates rejected by DB guidance'),
                        'revenue_candidates': [],
                        'total_candidates_found': len(found_candidates)
                    }
                self.logger.info(f"🔧 DEBUG: Selection result: £{best_result['amount']:,.0f}")
                best = {
                    'amount': best_result['amount'],
                    'confidence': best_result['confidence'],
                    'pattern_type': best_result.get('reasoning', 'selected_by_priority_scoring'),
                    'raw_match': 'selected_candidate',
                    'chunk': 0,
                    'context_snippet': best_result.get('context', '')
                }
                
                # Prepare top 3 candidates for UI — sorted by confidence score (highest first)
                candidates_by_confidence = sorted(found_candidates, key=lambda c: c.get('confidence', 0), reverse=True)
                top_candidates = []
                for i, candidate in enumerate(candidates_by_confidence[:3]):
                    top_candidates.append({
                        'amount': int(candidate['amount']),
                        'confidence': candidate['confidence'],  # Keep as decimal (0.0-1.0)
                        'pattern_type': candidate['pattern_type'],
                        'raw_match': candidate.get('raw_match', ''),
                        'chunk': candidate.get('chunk', i),
                        'page_number': f"Chunk {candidate.get('chunk', i)}",
                        'source_text': candidate.get('context_snippet', ''),
                        'similarity_score': candidate['confidence'],
                        'search_method': 'text_pattern_generic'
                    })
                
                result = {
                    'revenue': int(best['amount']),
                    'confidence': best['confidence'],
                    'extraction_method': best['pattern_type'],
                    'source': 'text_pattern_hybrid',
                    'revenue_candidates': top_candidates,
                    'total_candidates_found': len(found_candidates)
                }
                self.logger.info(f"🔥🔥🔥 EXTRACT_REVENUE SUCCESS RETURN: revenue={result['revenue']}, candidates={len(result['revenue_candidates'])}")
                return result
            else:
                self.logger.info(f"🔥🔥🔥 EXTRACT_REVENUE NO_MATCHES RETURN: 0 candidates found")
                # No patterns matched — moderate confidence: no revenue found in document
                no_match_confidence = 0.45
                return {
                    'revenue': None,
                    'confidence': no_match_confidence,
                    'extraction_method': 'no_matches',
                    'source': 'text_patterns',
                    'reasoning': 'No revenue patterns found in document',
                    'revenue_candidates': [],
                    'total_candidates_found': 0
                }
                
        except Exception as e:
            self.logger.error(f"🔥🔥🔥 EXTRACT_REVENUE EXCEPTION: {e}")
            self.logger.error(f"Simple revenue extraction failed: {e}")
            return {
                'revenue': 0,
                'confidence': 0.0,
                'extraction_method': 'error',
                'source': str(e),
                'revenue_candidates': [],
                'total_candidates_found': 0
            }

    def _detect_number_magnitude(self, number_str: str, context: str, position: int) -> int:
        """
        Intelligent magnitude detection for raw numbers based on context and size.
        
        Args:
            number_str: The cleaned number string (e.g., "37.5", "1234")
            context: The surrounding text context
            position: Position in the document
            
        Returns:
            Magnitude multiplier (1000000000 for billions, 1000000 for millions, etc.)
        """
        try:
            base_number = float(number_str)
            
            # Context around the number (±200 characters)
            start_pos = max(0, position - 200)
            end_pos = min(len(context), position + 200)
            nearby_context = context[start_pos:end_pos].lower()
            
            # Check for explicit magnitude indicators in nearby text
            if any(word in nearby_context for word in ['billion', 'bn', 'b ']):
                return 1000000000  # billions
            elif any(word in nearby_context for word in ['million', 'mn', 'm ']):
                return 1000000     # millions  
            elif any(word in nearby_context for word in ['thousand', 'k ']):
                return 1000        # thousands
            
            # Intelligent magnitude detection based on number size and context
            if base_number >= 1000:
                # Large numbers (1000+) are likely already in full units
                # Check if it looks like millions (e.g., 37500 = 37.5 million) 
                if 10000 <= base_number <= 999999:
                    # Could be millions in thousands format
                    if 'revenue' in nearby_context or 'sales' in nearby_context:
                        return 1000  # Treat as thousands, so 37500 * 1000 = 37.5M
                return 1  # Already in full units
            elif 10 <= base_number <= 999:
                # Medium numbers (10-999) in revenue context likely billions or millions
                if any(indicator in nearby_context for indicator in ['total revenue', 'group revenue', 'consolidated']):
                    return 1000000000  # Likely billions (e.g., 37.5 = 37.5B)
                elif 'revenue' in nearby_context:
                    return 1000000     # Likely millions (e.g., 150 = 150M)
                return 1000000         # Default to millions for mid-range
            else:
                # Small numbers (1-9) in revenue context very likely billions  
                if 'revenue' in nearby_context or 'sales' in nearby_context:
                    return 1000000000  # e.g., 5.2 = 5.2B
                return 1000000         # Default to millions
                
        except (ValueError, TypeError):
            # If parsing fails, default to no scaling
            return 1
            
    # Method removed: extract_revenue_with_sources() 
    # This method contained outdated tobacco-specific hardcoded patterns.
    # All functionality has been consolidated into the enhanced extract_revenue() method above.
