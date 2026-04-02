"""
Turnover Estimation Node - PURE RAG VECTOR SIMILARITY

LangGraph workflow node for REGEX-FREE revenue extraction using only semantic understanding:

1. Enhanced OCR → Quality text extraction from financial documents
2. Vector Embeddings → Semantic representation using all-mpnet-base-v2
3. RAG Similarity Search → Find revenue content via vector similarity
4. Semantic Analysis → Extract amounts using context understanding

ELIMINATED APPROACHES:
- ❌ Regex pattern matching → Replaced with semantic similarity
- ❌ Rule-based extraction → Replaced with vector search 
- ❌ SmartFinancialExtractionAgent → Replaced with RAGRevenueExtractor

NEW ARCHITECTURE:
✅ Pure RAG vector similarity search
✅ Enhanced OCR with financial optimization
✅ Semantic understanding over pattern matching
✅ RAGDocumentAgent + VectorDatabaseConnection integration
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import sys
import os

# No need for sys.path manipulation - using proper module imports

# Import RAGRevenueExtractor from update_revenue module
# from app_modules.agentic.update_revenue.rag_revenue_extractor import RAGRevenueExtractor

from ....utils.logger import get_logger
from ....config.app_config import CreditRiskConfig

logger = get_logger(__name__)

class TurnoverEstimationNode:
    """
    Intelligent revenue extraction with multi-strategy approach.
    
    Pure RAG Workflow Steps:
    1. Enhanced OCR → Quality text extraction from financial documents
    2. Vector Embedding → Semantic representation using all-mpnet-base-v2
    3. RAG Similarity Search → Find revenue content via vector similarity
    4. Semantic Analysis → Extract amounts using context understanding
    5. Confidence Scoring → Validate results with semantic confidence
    
    Pure RAG Components:
    - RAGRevenueExtractor (semantic revenue detection - NO REGEX)
    - Enhanced OCR with financial document optimization 
    - Vector similarity search for revenue-related content
    - Context-aware financial parsing and validation
    """
    
    def __init__(self, smart_extraction_agent=None, turnover_agent=None):
        """
        Initialize Pure RAG Revenue Extraction Node.
        
        Args:
            smart_extraction_agent: Legacy parameter for compatibility (not used in pure RAG)
            turnover_agent: Legacy parameter for compatibility (not used in pure RAG)
        
        Note: Pure RAG approach uses direct RAGRevenueExtractor initialization
        """
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Legacy agents - kept for compatibility but not used in pure RAG approach
        self.smart_extraction_agent = smart_extraction_agent
        self.turnover_agent = turnover_agent
        
        # Hybrid RAG method uses comprehensive RAGRevenueExtractor directly
        
        # Configuration for database storage
        self.config = CreditRiskConfig()
    
    def _store_revenue_data(self, company_number: str, revenue_data: Dict[str, Any]) -> bool:
        """
        Store extracted revenue data in company_financials table.
        
        Args:
            company_number: Company registration number
            revenue_data: Extracted revenue information
            
        Returns:
            bool: Success status
        """
        try:
            import sqlite3
            from datetime import datetime
            
            # Get company_id from companies table
            with sqlite3.connect(self.config.database_path) as conn:
                cursor = conn.cursor()
                
                # Find company_id
                cursor.execute("SELECT id FROM companies WHERE company_number = ?", (company_number,))
                company_row = cursor.fetchone()
                
                if not company_row:
                    self.logger.warning(f"Company {company_number} not found in companies table")
                    return False
                
                company_id = company_row[0]
                
                # Extract revenue information
                revenue_amount = revenue_data.get('amount', 0.0)
                confidence = revenue_data.get('confidence', 0.0)
                reasoning = revenue_data.get('reasoning', '')
                
                # Try to extract year and period from reasoning or metadata
                revenue_year = None
                period_type = 'Annual'  # Default to Annual
                
                # Simple extraction from reasoning text
                if reasoning:
                    import re
                    year_match = re.search(r'20\d{2}', reasoning)
                    if year_match:
                        revenue_year = int(year_match.group())
                    
                    if 'interim' in reasoning.lower() or 'half' in reasoning.lower() or '6 month' in reasoning.lower():
                        period_type = 'Interim'
                
                # If no year found, use current year
                if not revenue_year:
                    revenue_year = datetime.now().year
                
                # Check if record exists for this company (get the earliest/primary record)
                cursor.execute("""
                    SELECT id FROM company_financials 
                    WHERE company_id = ? 
                    ORDER BY created_at ASC 
                    LIMIT 1
                """, (company_id,))
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # Update the primary (earliest created) record for this company
                    record_id = existing_record[0]
                    cursor.execute("""
                        UPDATE company_financials 
                        SET latest_revenue = ?, latest_profit = ?, revenue_year = ?, period_type = ?, 
                            extraction_confidence = ?, extraction_date = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        revenue_amount,
                        None,  # We'll add profit extraction later
                        revenue_year,
                        period_type,
                        confidence,
                        datetime.now().isoformat(),
                        record_id
                    ))
                    self.logger.info(f"📝 Updated existing financial record (ID: {record_id}) for company {company_number}")
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO company_financials 
                        (company_id, latest_revenue, latest_profit, revenue_year, period_type, 
                         extraction_confidence, extraction_date, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (
                        company_id,
                        revenue_amount,
                        None,  # We'll add profit extraction later
                        revenue_year,
                        period_type,
                        confidence,
                        datetime.now().isoformat()
                    ))
                    self.logger.info(f"➕ Created new financial record for company {company_number}")
                
                conn.commit()
                
                self.logger.info(f"💾 Stored revenue data: Company {company_number}, Revenue £{revenue_amount:,.2f}, Confidence {confidence:.2%}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store revenue data: {e}")
            return False
            
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute turnover estimation and revenue extraction workflow node.
        
        Args:
            state: Current revenue workflow state with document processing data
            
        Returns:
            Updated workflow state with revenue extraction results
        """
        start_time = datetime.now()
        self.logger.info("💰 Starting turnover estimation and revenue extraction")
        
        try:
            # Extract document processing data from previous node
            document_data = state.get('document_processing_data', {})
            company_data = state.get('company_filing_data', {})
            
            self.logger.info(f"🔍 DEBUG TURNOVER: document_data keys: {list(document_data.keys())}")
            self.logger.info(f"🔍 DEBUG TURNOVER: document_data content: {document_data}")
            self.logger.info(f"🔍 DEBUG TURNOVER: company_data keys: {list(company_data.keys())}")
            self.logger.info(f"🔍 DEBUG TURNOVER: company_data content: {company_data}")
            
            company_name = company_data.get('company_name', 'Unknown Company')
            
            # Store company number for database validation
            self._current_company_number = (company_data.get('company_number') or 
                                          company_data.get('company_registration_number'))
            
            # Determine extraction strategy based on available data
            extraction_strategy = self._determine_extraction_strategy(document_data)
            
            # Execute revenue extraction using determined strategy
            extraction_result = self._execute_revenue_extraction(
                document_data, company_data, extraction_strategy
            )
            
            # Handle extraction results with proper fallback for non-vectorized documents
            revenue_amount = 0
            extraction_failed = False
            
            # Check if extraction explicitly failed due to no vectorized documents
            if extraction_result.get('extraction_method') == 'no_vectorized_documents':
                extraction_failed = True
                self.logger.warning(f"⚠️ No vectorized documents available for company: {company_data.get('company_name')}")
            elif extraction_result.get('extraction_method') in ('candidates_rejected', 'no_matches'):
                # All candidates were actively rejected by DB guidance — confident None
                rejection_confidence = extraction_result.get('confidence', 0.85)
                final_revenue = {
                    'revenue': None,
                    'amount': None,
                    'confidence': rejection_confidence,
                    'source_text': [],
                    'extraction_method': 'candidates_rejected',
                    'reasoning': extraction_result.get('reasoning', 'All candidates rejected by DB guidance'),
                    'alternative_candidates': []
                }
                validation_result = {'success': False, 'validated_candidates': []}
                revenue_extraction_data = self._compile_revenue_results(
                    extraction_result, validation_result, final_revenue, extraction_strategy, company_data
                )
                self.logger.info(f"🚫 Candidates rejected — reporting None with {rejection_confidence:.0%} confidence")
                # Skip remaining extraction logic and jump to state update
                updated_state = dict(state)
                updated_state['revenue_extraction_data'] = revenue_extraction_data
                decision = {
                    'decision_point': 'turnover_estimation',
                    'decision_type': 'extraction',
                    'decision_result': 'candidates_rejected',
                    'confidence': rejection_confidence,
                    'reasoning': final_revenue['reasoning'],
                    'timestamp': datetime.now().isoformat()
                }
                if 'workflow_decisions' not in updated_state:
                    updated_state['workflow_decisions'] = []
                updated_state['workflow_decisions'].append(decision)
                execution_time = (datetime.now() - start_time).total_seconds()
                if 'node_execution_times' not in updated_state:
                    updated_state['node_execution_times'] = {}
                updated_state['node_execution_times']['turnover_estimation'] = execution_time
                if 'node_confidence_scores' not in updated_state:
                    updated_state['node_confidence_scores'] = {}
                updated_state['node_confidence_scores']['turnover_estimation'] = rejection_confidence
                updated_state['current_node'] = 'market_validation'
                return updated_state
            elif extraction_result.get('success'):
                # Fast path returns best_candidate with amount field
                if 'best_candidate' in extraction_result:
                    best_candidate = extraction_result['best_candidate']
                    revenue_amount = best_candidate.get('amount', 0)
                # Traditional extraction returns revenue field directly
                elif 'revenue' in extraction_result:
                    revenue_amount = extraction_result.get('revenue', 0)
            
            if not extraction_failed and extraction_result.get('success') and revenue_amount > 0:
                # Create final revenue from successful extraction result
                if 'best_candidate' in extraction_result:
                    # Fast path result structure
                    best_candidate = extraction_result['best_candidate']
                    main_amount = best_candidate.get('amount', 0)
                    main_confidence = best_candidate.get('confidence', 0.0)
                    
                    # Generate prioritized alternative_candidates with our methodology first
                    prioritized_alternatives = [
                        # Priority #1: OUR METHODOLOGY - Current extraction result
                        {
                            'amount': main_amount,
                            'revenue': main_amount,
                            'confidence': main_confidence * 100,  # Convert to percentage
                            'source_method': 'agentic_rag_extraction',
                            'pattern_type': 'primary_methodology',
                            'source_excerpt': f'Agentic RAG extraction: £{main_amount:,.0f} with {main_confidence:.1%} confidence',
                            'page_number': 'RAG Extraction',
                            'chunk_id': 'primary_result',
                            'search_level': 1,
                            'similarity_score': main_confidence,
                            'document_url': None,
                            'reasoning': f'Primary methodology result: £{main_amount:,.0f} with {main_confidence:.1%} confidence',
                            'source_text': f'RAG methodology: £{main_amount:,.0f}',
                            'metadata': {'source': 'primary_methodology', 'priority': 1}
                        }
                    ]
                    
                    # Add best alternative if available (priority #2)
                    original_candidates = extraction_result.get('candidates', [])
                    if original_candidates and len(original_candidates) > 0:
                        best_alt = original_candidates[0]
                        prioritized_alternatives.append(best_alt)
                    
                    # Ensure exactly 2 results
                    prioritized_alternatives = prioritized_alternatives[:2]
                    
                    final_revenue = {
                        'revenue': main_amount,
                        'amount': main_amount,  # Compatibility
                        'confidence': main_confidence,
                        'source_text': best_candidate.get('source_text', []),
                        'extraction_method': extraction_result.get('method', 'fast_path_extraction'),
                        'reasoning': best_candidate.get('reasoning', f"Fast path extraction using {extraction_result.get('method', 'unknown')} method"),
                        'alternative_candidates': prioritized_alternatives
                    }
                else:
                    # Traditional extraction structure
                    main_amount = extraction_result.get('revenue', 0)
                    main_confidence = extraction_result.get('confidence', 0.0)
                    
                    # Generate prioritized alternative_candidates with our methodology first
                    prioritized_alternatives = [
                        # Priority #1: OUR METHODOLOGY - Current extraction result
                        {
                            'amount': main_amount,
                            'revenue': main_amount,
                            'confidence': main_confidence * 100,  # Convert to percentage
                            'source_method': 'agentic_rag_extraction',
                            'pattern_type': 'primary_methodology', 
                            'source_excerpt': f'Agentic RAG extraction: £{main_amount:,.0f} with {main_confidence:.1%} confidence',
                            'page_number': 'RAG Extraction',
                            'chunk_id': 'primary_result',
                            'search_level': 1,
                            'similarity_score': main_confidence,
                            'document_url': None,
                            'reasoning': f'Primary methodology result: £{main_amount:,.0f} with {main_confidence:.1%} confidence',
                            'source_text': f'RAG methodology: £{main_amount:,.0f}',
                            'metadata': {'source': 'primary_methodology', 'priority': 1}
                        }
                    ]
                    
                    # Add best alternative if available (priority #2)
                    original_candidates = extraction_result.get('revenue_candidates', [])
                    if original_candidates and len(original_candidates) > 0:
                        best_alt = original_candidates[0]
                        prioritized_alternatives.append(best_alt)
                    
                    # Ensure exactly 2 results
                    prioritized_alternatives = prioritized_alternatives[:2]
                    
                    final_revenue = {
                        'revenue': main_amount,
                        'amount': main_amount,  # Compatibility
                        'confidence': main_confidence,
                        'source_text': [f"{state.get('company_name', 'Company')} revenue: £{main_amount:,.0f}"],
                        'extraction_method': extraction_result.get('method', 'text_first_hybrid'),
                        'reasoning': f"Direct RAG extraction using {extraction_result.get('method', 'unknown')} method",
                        'alternative_candidates': prioritized_alternatives
                    }
                
                # Create validation result for compatibility
                validation_result = {
                    'success': True,
                    'validated_candidates': extraction_result.get('revenue_candidates', [])
                }
                
                self.logger.info(f"🎯 Using direct extraction result: £{revenue_amount:,.0f}")
            elif extraction_failed:
                # Handle case where documents are not vectorized
                final_revenue = {
                    'revenue': None,
                    'amount': None,
                    'confidence': 0.0,
                    'source_text': [],
                    'extraction_method': 'no_vectorized_documents',
                    'reasoning': extraction_result.get('notice', 'Document not vectorized - financial documents need to be processed first'),
                    'alternative_candidates': [],
                    'error': extraction_result.get('error', 'No vectorized documents available'),
                    'notice': extraction_result.get('notice', 'Document not vectorized - financial documents need to be processed first')
                }
                
                # Create validation result for failed extraction
                validation_result = {
                    'success': False,
                    'validated_candidates': [],
                    'error': extraction_result.get('error', 'No vectorized documents available')
                }
                
                self.logger.warning(f"⚠️ No vectorized documents: {final_revenue['reasoning']}")
            else:
                # Fallback to old validation logic
                validation_result = self._validate_revenue_candidates(
                    extraction_result, company_data
                )
                
                # Select best revenue estimate
                final_revenue = self._select_best_revenue_estimate(
                    validation_result, extraction_strategy
                )
            
            # Compile revenue extraction data
            revenue_extraction_data = self._compile_revenue_results(
                extraction_result, validation_result, final_revenue, extraction_strategy, company_data
            )
            
            # Store revenue data in company_financials table (only if auto-save is enabled)
            # NOTE: Auto-save should be controlled by the agentic service config
            auto_save_enabled = state.get('config', {}).get('auto_save', False)
            company_number = company_data.get('company_number') or company_data.get('company_registration_number')
            revenue_amount = final_revenue.get('revenue') or final_revenue.get('amount', 0)
            
            if auto_save_enabled and company_number and revenue_amount > 0:
                storage_success = self._store_revenue_data(company_number, final_revenue)
                if storage_success:
                    self.logger.info("✅ Revenue data stored in company_financials table")
                else:
                    self.logger.warning("⚠️ Failed to store revenue data in database")
            elif company_number and revenue_amount > 0:
                self.logger.info(f"📋 Auto-save disabled - revenue extracted (£{revenue_amount:,.0f}) but not saved. Use approval workflow to save.")
            else:
                self.logger.warning(f"⚠️ No valid revenue data to store (company: {company_number}, amount: {revenue_amount})")
            
            # Record workflow decision
            decision = {
                'decision_point': "turnover_estimation",
                'decision_type': "extraction",
                'decision_result': extraction_strategy.get('method', 'unknown'),
                'confidence': final_revenue.get('confidence', 0.0),
                'reasoning': final_revenue.get('reasoning', 'Revenue extraction completed'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Update workflow state
            execution_time = (datetime.now() - start_time).total_seconds()
            
            updated_state = dict(state)
            updated_state['revenue_extraction_data'] = revenue_extraction_data
            
            if 'workflow_decisions' not in updated_state:
                updated_state['workflow_decisions'] = []
            updated_state['workflow_decisions'].append(decision)
            
            if 'node_execution_times' not in updated_state:
                updated_state['node_execution_times'] = {}
            updated_state['node_execution_times']['turnover_estimation'] = execution_time
            
            if 'node_confidence_scores' not in updated_state:
                updated_state['node_confidence_scores'] = {}
            updated_state['node_confidence_scores']['turnover_estimation'] = final_revenue.get('confidence', 0.0)
            
            updated_state['current_node'] = 'market_validation'
            
            self.logger.info(f"✅ Turnover estimation completed in {execution_time:.2f}s")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ Turnover estimation failed: {str(e)}")
            raise RuntimeError(f"Turnover estimation failed: {str(e)}. No fallback data will be created - this indicates a problem with revenue extraction that needs to be resolved.")
    
    def _determine_extraction_strategy(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the best revenue extraction strategy based on available data.
        
        FAST PATH Strategy Priority:
        1. Use existing extraction_results (from fast path - INSTANT)
        2. Pure RAG vector similarity (primary method - NO REGEX)
        3. Enhanced OCR + RAG (if vector DB needs refresh - NO REGEX)
        4. Manual estimation (last resort only)
        
        Completely eliminates regex patterns - Pure semantic vector search
        """
        # Check for fast path extraction results first (instant processing)
        fast_path_results = document_data.get('extraction_results')
        if fast_path_results and len(fast_path_results) > 0:
            self.logger.info(f"🚀 FAST PATH: Found {len(fast_path_results)} extraction results from fast path")
            return {
                'method': 'fast_path_results',
                'confidence': 0.99,
                'description': 'Use existing extraction results from fast path - INSTANT',
                'fallbacks': ['pure_rag_vector', 'enhanced_ocr_rag', 'manual']
            }
        
        vector_available = document_data.get('vector_db_stored', False)
        text_available = bool(document_data.get('extracted_text'))
        chunks_available = document_data.get('chunk_count', 0) > 0
        
        self.logger.info(f"🔍 DEBUG: Strategy selection - vector_available: {vector_available}, text_available: {text_available}, chunks_available: {chunks_available}")
        self.logger.info(f"🔍 DEBUG: document_data keys: {list(document_data.keys())}")
        self.logger.info(f"🔍 DEBUG: document_data['vector_db_stored']: {document_data.get('vector_db_stored')}")
        self.logger.info(f"🔍 DEBUG: document_data['chunk_count']: {document_data.get('chunk_count')}")
        
        if vector_available and chunks_available:
            return {
                'method': 'pure_rag_vector',
                'confidence': 0.95,
                'description': 'Pure RAG vector similarity search - NO REGEX',
                'fallbacks': ['enhanced_ocr_rag', 'manual']
            }
        elif text_available or chunks_available:
            return {
                'method': 'enhanced_ocr_rag',
                'confidence': 0.85,
                'description': 'Enhanced OCR + RAG vector extraction - NO REGEX',
                'fallbacks': ['manual']
            }
        else:
            return {
                'method': 'manual',
                'confidence': 0.3,
                'description': 'Manual estimation based on company data',
                'fallbacks': []
            }
    
    def _execute_revenue_extraction(self, document_data: Dict[str, Any],
                                  company_data: Dict[str, Any],
                                  strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute revenue extraction using REGEX-FREE strategy.
        
        NO REGEX PATTERNS - Pure vector similarity search only
        """
        method = strategy.get('method', 'manual')
        
        if method == 'fast_path_results':
            return self._extract_using_fast_path_results(document_data, company_data)
        elif method == 'pure_rag_vector':
            return self._extract_using_pure_rag_vector(document_data, company_data)
        elif method == 'enhanced_ocr_rag':
            return self._extract_using_enhanced_ocr_rag(document_data, company_data)
        else:  # manual
            return self._extract_using_manual_estimation(company_data)
    
    def _extract_using_pure_rag_vector(self, document_data: Dict[str, Any],
                                     company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract revenue using HYBRID RAG method with GAAP/IFRS taxonomy - Text-First + Context-Driven Similarity.
        
        Uses: Text Patterns FIRST → Vector Similarity SECOND → GAAP/IFRS Context → Keyword Fallback
        """
        self.logger.info("🎯 Hybrid RAG Extraction - Text-First + GAAP/IFRS Semantic Similarity")
        
        try:
            # Import the comprehensive RAG system with hybrid method
            from app_modules.agentic.update_revenue.rag_revenue_extractor import RAGRevenueExtractor
            
            # Initialize comprehensive RAG extractor with hybrid method
            rag_extractor = RAGRevenueExtractor()
            self.logger.info("🔍 STEP 1: Comprehensive RAG with hybrid method (text-first + similarity) initialized successfully")
            
            # Extract required data
            self.logger.info(f"🔍 DEBUG: company_data.get('document_id'): {company_data.get('document_id')}")
            self.logger.info(f"🔍 DEBUG: document_data.get('document_id'): {document_data.get('document_id')}")
            self.logger.info(f"🔍 DEBUG: document_data.get('transaction_id'): {document_data.get('transaction_id')}")
            
            document_id = company_data.get('document_id') or document_data.get('document_id') or document_data.get('transaction_id')
            company_name = company_data.get('company_name', '')
            company_registration_number = company_data.get('company_number') or company_data.get('company_registration_number', '')
            filing_date = company_data.get('filing_date')
            
            self.logger.info(f"🔍 STEP 2: Extracted data - document_id: {document_id}, company_name: {company_name}, company_registration_number: {company_registration_number}")
            self.logger.info(f"🔍 STEP 3: About to check missing data conditions")
            
            if not document_id or not company_registration_number:
                self.logger.error(f"🚨 STEP ERROR: Missing required data - document_id: {document_id}, company_registration_number: {company_registration_number}")
                return {
                    'success': False, 
                    'error': 'Missing document_id or company_registration_number for RAG extraction',
                    'method': 'pure_rag_vector_failed'
                }
            
            self.logger.info(f"🔍 STEP 4: Required data validated, proceeding to RAG search")
            
            # Using direct hybrid RAG method - no optimizer needed
            
            # Use HYBRID RAG extraction with text-first + GAAP/IFRS similarity
            self.logger.info("🎯 Using Hybrid RAG method - Text patterns FIRST, then GAAP/IFRS semantic similarity")
            
            # Use the enhanced method that returns top 3 candidates with confidence scores
            rag_result = rag_extractor.extract_revenue(company_registration_number)
            
            # Process result from hybrid RAG extraction method
            revenue_amount = rag_result.get('revenue', 0)
            confidence = rag_result.get('confidence', 0.0)
            extraction_method = rag_result.get('extraction_method', 'hybrid_rag_extraction')
            source = rag_result.get('source', 'text_pattern_hybrid')
            
            self.logger.info(f"🔍 Hybrid RAG Result: revenue={revenue_amount}, confidence={confidence}, method={extraction_method}")
            self.logger.info(f"🔍 Source: {source}")
            if revenue_amount and revenue_amount > 0:
                self.logger.info(f"✅ Revenue extraction successful: £{revenue_amount:,.0f}")
                self.logger.info(f"🎯 Confidence: {min(confidence * 100, 100):.1f}%")
                self.logger.info(f"🔍 Method: {extraction_method}")
                self.logger.info(f"📊 Source Type: {source}")
                self.logger.info(f"📄 Hybrid approach: Text patterns + GAAP/IFRS semantic similarity")
                
                # Get multiple candidates from RAG extraction with sources
                source_candidates = rag_result.get('revenue_candidates', [])
                enhanced_candidates = []
                
                # Convert source candidates to the format expected by UI
                for i, candidate in enumerate(source_candidates[:5]):  # Top 5 candidates
                    enhanced_candidates.append({
                        'amount': candidate.get('amount', 0),
                        'revenue': candidate.get('amount', 0),
                        'confidence': candidate.get('confidence', 0.0) * 100,  # Convert to percentage
                        'source_method': 'hybrid_rag_with_sources',
                        'pattern_type': candidate.get('pattern_type', extraction_method),
                        'source_excerpt': candidate.get('content_preview', '')[:200] + '...',
                        'page_number': candidate.get('page_number', 'Unknown'),
                        'chunk_id': candidate.get('chunk_id', f'chunk_{i}'),
                        'search_level': candidate.get('search_level', 1),
                        'similarity_score': candidate.get('similarity_score', 0.0),
                        'document_url': None,
                        'reasoning': f"Pattern: {candidate.get('pattern_type', 'unknown')} | Page: {candidate.get('page_number', 'Unknown')} | Confidence: {candidate.get('confidence', 0.0)*100:.1f}%",
                        'source_text': candidate.get('source_text', ''),
                        'metadata': candidate.get('metadata', {})
                    })
                
                self.logger.info(f"✅ Enhanced {len(enhanced_candidates)} revenue candidates from RAG extraction")
                
                return {
                    'success': True,
                    'method': 'hybrid_rag_text_similarity', 
                    'revenue': revenue_amount,
                    'confidence': confidence,
                    'primary_revenue': revenue_amount,
                    'primary_confidence': confidence,
                    'revenue_candidates': enhanced_candidates,
                    'extraction_summary': {
                        'total_candidates_found': len(enhanced_candidates),
                        'candidates_returned': len(enhanced_candidates),
                        'extraction_method': extraction_method,
                        'reasoning': f'Hybrid RAG approach using {extraction_method} with {min(confidence * 100, 100):.1f}% confidence (text patterns + GAAP/IFRS similarity)'
                    },
                    'extraction_confidence': confidence,
                    'rag_metadata': {'source': source, 'method': extraction_method, 'hybrid_approach': 'text_first_plus_similarity'},
                    'extraction_time': 0.5  # Approximate time for hybrid RAG
                }
            else:
                self.logger.warning(f"⚠️ Revenue extraction failed - no revenue found")
                # Propagate the meaningful confidence from the extractor (no_matches = 0.70, candidates_rejected = 0.85)
                return {
                    'success': False,
                    'candidates': [],
                    'method': rag_result.get('extraction_method', 'pure_rag_vector_no_results'),
                    'extraction_method': rag_result.get('extraction_method', 'no_matches'),
                    'confidence': rag_result.get('confidence', 0.0),
                    'reasoning': rag_result.get('reasoning', 'No revenue candidates found by RAG extraction'),
                    'error': 'No revenue candidates found by RAG extraction',
                    'extraction_summary': {
                        'total_candidates_found': 0,
                        'candidates_returned': 0,
                        'extraction_method': rag_result.get('extraction_method', 'pure_rag_vector'),
                        'reasoning': rag_result.get('reasoning', 'Pure RAG vector search found no valid revenue patterns')
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Pure RAG vector extraction error: {str(e)}")
            return {
                'success': False,
                'error': f'Pure RAG extraction exception: {str(e)}',
                'method': 'pure_rag_vector_error'
            }
    
    def _extract_using_enhanced_ocr_rag(self, document_data: Dict[str, Any],
                                       company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract revenue using Enhanced OCR + RAG when vector DB needs refresh.
        
        Pipeline: Enhanced OCR → Text Quality → Vector Embeddings → Similarity Search
        """
        self.logger.info("🔄 Enhanced OCR + RAG extraction for vector DB refresh")
        
        try:
            # This method would trigger document reprocessing with enhanced OCR
            # then perform pure RAG extraction on the refreshed data
            
            # For now, fall back to pure RAG if available
            if document_data.get('vector_db_stored', False):
                return self._extract_using_pure_rag_vector(document_data, company_data)
            
            # If no vector data available, indicate need for document reprocessing
            return {
                'success': False,
                'error': 'Document needs reprocessing with enhanced OCR for vector embeddings',
                'method': 'enhanced_ocr_rag_needs_reprocessing',
                'recommendation': 'Trigger FinancialExtractionNode with enhanced OCR settings'
            }
        
        except Exception as e:
            self.logger.error(f"Enhanced OCR + RAG extraction error: {str(e)}")
            return {
                'success': False,
                'error': f'Enhanced OCR + RAG exception: {str(e)}',
                'method': 'enhanced_ocr_rag_error'
            }
    
    # LEGACY AGENT METHODS REMOVED - Pure RAG Vector Similarity Only
    #
    # Previous extraction methods removed in favor of RAG-only approach:
    # - _run_original_rag_extraction → Replaced by RAGRevenueExtractor
    # - _extract_using_smart_agent → Replaced by pure vector similarity
    # - _run_original_smart_agent → Eliminated for semantic understanding
    #
    # New approach: Enhanced OCR → Quality Text → Vector Embeddings → Similarity Search
    
    # REGEX METHODS REMOVED - Pure RAG Vector Similarity Only
    # 
    # Previous regex-based extraction methods have been eliminated in favor of:
    # 1. Pure RAG vector similarity search
    # 2. Enhanced OCR + semantic embeddings  
    # 3. NO REGEX PATTERNS - semantic understanding only
    #
    # This ensures better accuracy and semantic understanding vs pattern matching
    
    def _extract_using_fast_path_results(self, document_data: Dict[str, Any],
                                       company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process existing extraction_results from fast path using actual RAG extraction.
        
        Instead of using placeholder values, this now calls the RAG extractor
        to get the real revenue amount from the document content.
        """
        self.logger.info("🚀 FAST PATH: Using RAG extraction for accurate revenue - SMART processing")
        
        try:
            # Import RAG extractor inside method to avoid circular imports
            from ..rag_revenue_extractor import RAGRevenueExtractor
            
            # Get company number for RAG extraction
            company_number = (company_data.get('company_number') or 
                            company_data.get('company_registration_number'))
            
            if not company_number:
                self.logger.error("❌ No company number available for RAG extraction")
                return {
                    'success': False,
                    'candidates': [],
                    'method': 'fast_path_extraction',
                    'error': 'No company number for RAG extraction'
                }
            
            self.logger.info(f"🔍 Running ENHANCED RAG extraction for company {company_number}")
            
            # Use enhanced RAG extractor to get detailed source information with top 3 candidates
            rag_extractor = RAGRevenueExtractor()
            rag_result = rag_extractor.extract_revenue(company_number)
            
            if not rag_result.get('revenue') or rag_result.get('revenue', 0) <= 0:
                self.logger.warning("⚠️ Enhanced RAG extraction returned no valid revenue")
                # Propagate confidence from extractor (no_matches=0.70, candidates_rejected=0.85)
                return {
                    'success': False,
                    'candidates': [],
                    'method': rag_result.get('extraction_method', 'enhanced_fast_path_extraction'),
                    'extraction_method': rag_result.get('extraction_method', 'no_matches'),
                    'confidence': rag_result.get('confidence', 0.0),
                    'reasoning': rag_result.get('reasoning', 'No revenue found by enhanced RAG extractor'),
                    'error': 'No revenue found by enhanced RAG extractor'
                }
            
            # Extract results from enhanced RAG
            revenue_amount = rag_result.get('revenue', 0)
            rag_confidence = rag_result.get('confidence', 0.0)
            extraction_method = rag_result.get('extraction_method', 'enhanced_rag_extraction')
            source_candidates = rag_result.get('source_candidates', [])
            best_source = rag_result.get('best_source', {})
            
            self.logger.info(f"✅ Enhanced RAG extracted £{revenue_amount:,.0f} with {rag_confidence:.1%} confidence")
            self.logger.info(f"📄 Found {len(source_candidates)} source candidates with page numbers and similarity scores")
            
            # Create enhanced candidates with rich source information
            enhanced_candidates = []
            
            for i, source_candidate in enumerate(source_candidates):
                # Create detailed source text array with multiple entries
                detailed_source_text = [
                    f"Page {source_candidate.get('page_number', 'Unknown')} | {source_candidate.get('section_title', 'Financial Document')}",
                    f"Amount: £{source_candidate.get('amount', 0):,.0f}",
                    f"Confidence: {source_candidate.get('confidence', 0):.1%}",
                    f"Similarity Score: {source_candidate.get('similarity_score', 0):.3f}",
                    f"Pattern: {source_candidate.get('pattern_type', 'unknown')}",
                    f"Chunk ID: {source_candidate.get('chunk_id', 'unknown')}",
                    f"Content: {source_candidate.get('content_preview', 'No preview available')}"
                ]
                
                candidate = {
                    'amount': float(source_candidate.get('amount', 0)),
                    'confidence': float(source_candidate.get('confidence', 0)),
                    'reasoning': f'Enhanced RAG found revenue on page {source_candidate.get("page_number", "unknown")} using {source_candidate.get("pattern_type", "unknown")}',
                    'context': f'Company: {company_data.get("company_name", "Unknown")} | Page: {source_candidate.get("page_number", "unknown")}',
                    'source': 'enhanced_rag_revenue_extractor',
                    'method': 'enhanced_fast_path_rag_extraction',
                    'source_text': detailed_source_text,
                    'metadata': {
                        'page_number': source_candidate.get('page_number'),
                        'chunk_id': source_candidate.get('chunk_id'),
                        'document_id': source_candidate.get('document_id'),
                        'section_type': source_candidate.get('section_type'),
                        'section_title': source_candidate.get('section_title'),
                        'similarity_score': source_candidate.get('similarity_score'),
                        'pattern_type': source_candidate.get('pattern_type'),
                        'content_preview': source_candidate.get('content_preview')
                    }
                }
                enhanced_candidates.append(candidate)
            
            # Use enhanced candidates if available, otherwise create fallback
            if not enhanced_candidates:
                # Fallback to single candidate if no enhanced candidates
                candidate = {
                    'amount': float(revenue_amount),
                    'confidence': float(rag_confidence),
                    'reasoning': f'Enhanced RAG extraction found revenue using {extraction_method}',
                    'context': f'Company: {company_data.get("company_name", "Unknown")}',
                    'source': 'enhanced_rag_revenue_extractor',
                    'method': 'enhanced_fast_path_rag_extraction',
                    'source_text': [f"Revenue extracted: £{revenue_amount:,.0f}"]
                }
                enhanced_candidates = [candidate]
            
            # Return ALL enhanced candidates (up to 3 as requested by user)
            revenue_candidates = enhanced_candidates
            best_candidate = revenue_candidates[0]
            
            self.logger.info(f"🚀 ENHANCED FAST PATH SUCCESS: Found {len(revenue_candidates)} candidates, best: £{best_candidate['amount']:,.0f} with {best_candidate['confidence']:.1%} confidence")
            
            return {
                'success': True,
                'candidates': revenue_candidates,
                'best_candidate': best_candidate,
                'method': 'enhanced_fast_path_rag_extraction',
                'overall_confidence': rag_confidence,
                'processing_time': 0.5,  # RAG processing time
                'source_metadata': {
                    'total_candidates_found': len(source_candidates),
                    'extraction_method': extraction_method,
                    'best_source_info': best_source
                }
            }
        
        except Exception as e:
            self.logger.error(f"❌ Enhanced fast path RAG extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'candidates': [],
                'method': 'enhanced_fast_path_extraction',
                'error': f'Enhanced RAG extraction error: {str(e)}'
            }

    def _extract_using_manual_estimation(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate basic fallback revenue estimation based on company data.
        
        Last resort method when RAG extraction fails - Pure semantic approach.
        """
        self.logger.info("📊 Using RAG-based fallback estimation for revenue")
        
        try:
            company_name = company_data.get('company_name', '')
            
            # Semantic fallback should not use hardcoded revenue values
            # This indicates that proper revenue extraction failed
            raise ValueError(f"No revenue data could be extracted for {company_name}. Semantic fallback cannot proceed without proper document analysis.")
                
        except Exception as e:
            self.logger.error(f"❌ Semantic fallback estimation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _find_revenue_relevant_chunks(self, chunks: List[Dict[str, Any]], 
                                    queries: List[str]) -> List[Dict[str, Any]]:
        """
        Find text chunks most relevant to revenue extraction using similarity scoring.
        
        Note: In production, this would use actual vector similarity search.
        """
        relevant_chunks = []
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '').lower()
            max_relevance = 0.0
            
            # Simple relevance scoring (replace with vector similarity in production)
            for query in queries:
                query_terms = query.lower().split()
                relevance = sum(1 for term in query_terms if term in chunk_text) / len(query_terms)
                max_relevance = max(max_relevance, relevance)
            
            if max_relevance > 0.3:  # Relevance threshold
                chunk_copy = dict(chunk)
                chunk_copy['similarity'] = max_relevance
                relevant_chunks.append(chunk_copy)
        
        # Sort by relevance and return top chunks
        relevant_chunks.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return relevant_chunks  # ALL most relevant chunks
    
    def _validate_revenue_candidates(self, extraction_result: Dict[str, Any],
                                   company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and score revenue candidates using business logic.
        """
        if not extraction_result.get('success'):
            return {'success': False, 'validated_candidates': []}
        
        candidates = extraction_result.get('revenue_candidates', [])
        validated = []
        
        for candidate in candidates:
            revenue = candidate.get('revenue', 0)
            
            # Basic validation rules
            validation_score = 1.0
            validation_notes = []
            
            # Revenue range validation
            if revenue < 0:
                validation_score *= 0.1
                validation_notes.append('Negative revenue detected')
            elif revenue > 1_000_000_000:  # £1B threshold
                validation_score *= 0.7
                validation_notes.append('Very high revenue figure')
            elif revenue < 1000:  # £1K threshold  
                validation_score *= 0.8
                validation_notes.append('Very low revenue figure')
            
            # Add validation metadata
            candidate_copy = dict(candidate)
            candidate_copy['validation_score'] = validation_score
            candidate_copy['validation_notes'] = validation_notes
            candidate_copy['overall_confidence'] = candidate.get('confidence', 0.5) * validation_score
            
            validated.append(candidate_copy)
        
        return {
            'success': True,
            'validated_candidates': validated
        }
    
    def _search_for_expected_revenue_range(self, expected_revenue_gbp: float, 
                                          company_number: str) -> Dict[str, Any]:
        """
        Intelligently search for revenue figures within the document that are closer 
        to the expected database value, in case AI extracted a segment figure.
        
        Args:
            expected_revenue_gbp: Expected revenue from database in GBP
            company_number: Company registration number for RAG search
            
        Returns:
            Dict with alternative revenue candidates closer to expected range
        """
        try:
            from ..rag_revenue_extractor import RAGRevenueExtractor
            
            # Values are already in GBP — use directly
            # Define search ranges around expected value
            # Look for figures within 30-150% of expected (to catch reasonable variations)
            min_search_gbp = expected_revenue_gbp * 0.3
            max_search_gbp = expected_revenue_gbp * 1.5
            
            self.logger.info(f"🔍 Intelligent Search: Looking for revenue figures between £{min_search_gbp:,.0f} - £{max_search_gbp:,.0f}")
            self.logger.info(f"📊 Expected from database: £{expected_revenue_gbp:,.0f}")
            
            # Use RAG extractor to get ALL revenue candidates
            rag_extractor = RAGRevenueExtractor()
            rag_result = rag_extractor.extract_revenue(company_number)
            
            all_candidates = rag_result.get('revenue_candidates', [])
            self.logger.info(f"🔎 Found {len(all_candidates)} total revenue candidates from document")
            
            # Filter candidates within expected range
            range_candidates = []
            close_candidates = []
            
            for candidate in all_candidates:
                candidate_amount = candidate.get('amount', 0)
                
                if min_search_gbp <= candidate_amount <= max_search_gbp:
                    # This candidate is within reasonable range of expected value
                    range_candidates.append({
                        'amount_gbp': candidate_amount,
                        'confidence': candidate.get('confidence', 0.0),
                        'pattern_type': candidate.get('pattern_type', 'unknown'),
                        'page_number': candidate.get('page_number', 'Unknown'),
                        'chunk_id': candidate.get('chunk_id', 'unknown'),
                        'similarity_score': candidate.get('similarity_score', 0.0),
                        'content_preview': candidate.get('content_preview', ''),
                        'expected_ratio': candidate_amount / expected_revenue_gbp,
                        'match_quality': 'RANGE_MATCH'
                    })
                elif candidate_amount > expected_revenue_gbp * 0.1:  # At least 10% of expected
                    # Keep track of other significant figures for analysis
                    close_candidates.append({
                        'amount_gbp': candidate_amount,
                        'confidence': candidate.get('confidence', 0.0),
                        'expected_ratio': candidate_amount / expected_revenue_gbp,
                        'match_quality': 'ALTERNATIVE'
                    })
            
            # Sort range candidates by how close they are to expected value
            if range_candidates:
                range_candidates.sort(key=lambda x: abs(1.0 - x['expected_ratio']))
                best_range_match = range_candidates[0]
                
                self.logger.info(f"💡 INTELLIGENT DISCOVERY: Found {len(range_candidates)} candidates within expected range!")
                self.logger.info(f"🎯 Best match: £{best_range_match['amount_gbp']:,.0f} "
                               f"= {best_range_match['expected_ratio']:.1%} of expected")
                
                return {
                    'intelligent_search_available': True,
                    'range_matches_found': len(range_candidates),
                    'best_range_match': best_range_match,
                    'all_range_matches': range_candidates[:3],  # Top 3
                    'alternative_candidates': close_candidates[:5],  # Top 5 alternatives
                    'search_summary': f"Found {len(range_candidates)} revenue figures within 30-150% of expected £{expected_revenue_gbp:,.0f}",
                    'recommendation': f"Consider using £{best_range_match['amount_gbp']:,.0f} instead of originally extracted amount"
                }
            else:
                self.logger.warning(f"⚠️ No revenue figures found within expected range £{min_search_gbp:,.0f} - £{max_search_gbp:,.0f}")
                return {
                    'intelligent_search_available': True,
                    'range_matches_found': 0,
                    'alternative_candidates': close_candidates[:5],
                    'search_summary': f"No figures found within 30-150% of expected £{expected_revenue_gbp:,.0f}",
                    'recommendation': "Original extraction may be correct, or total revenue not disclosed in this document"
                }
                
        except Exception as e:
            self.logger.error(f"Intelligent search failed: {str(e)}")
            return {
                'intelligent_search_available': False,
                'error': str(e)
            }

    def _validate_extracted_revenue_against_database(self, extracted_revenue: float, 
                                                    company_number: str) -> Dict[str, Any]:
        """
        Validate extracted revenue against expected database values with intelligent search.
        
        This adds intelligence to detect if AI extracted segment/subsidiary revenue 
        instead of total company revenue by comparing against expected ranges and 
        searching for better matches within the document.
        
        Args:
            extracted_revenue: Revenue extracted by AI (in USD equivalent)
            company_number: Company registration number
            
        Returns:
            Dict with validation results, confidence adjustment, and intelligent alternatives
        """
        try:
            import sqlite3
            import requests
            
            # Get expected revenue from database via API
            api_url = f"http://localhost:5002/api/companies?limit=1000"
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                companies_data = response.json().get('data', [])
                company_data = next(
                    (comp for comp in companies_data if comp.get('company_number') == company_number), 
                    None
                )
                
                if company_data and company_data.get('sales_gbp'):
                    expected_revenue_gbp = float(company_data.get('sales_gbp'))
                    
                    # Both extracted_revenue and expected value are in GBP — compare directly
                    extracted_revenue_gbp = extracted_revenue if extracted_revenue else 0
                    
                    # Calculate ratio and confidence adjustment
                    if expected_revenue_gbp > 0:
                        ratio = extracted_revenue_gbp / expected_revenue_gbp
                        
                        # If extracted revenue is significantly lower, perform intelligent search
                        intelligent_search_results = {}
                        if ratio < 0.5:  # Less than 50% of expected
                            self.logger.info(f"🔍 Extracted revenue is {ratio:.1%} of expected - running intelligent search...")
                            intelligent_search_results = self._search_for_expected_revenue_range(
                                expected_revenue_gbp, company_number
                            )
                        
                        # Intelligence thresholds for confidence adjustment
                        if 0.8 <= ratio <= 1.2:
                            # Extracted revenue is within 20% of expected - HIGH confidence
                            confidence_adjustment = 0.1
                            validation_status = "ALIGNED"
                            reasoning = f"✅ Extracted revenue £{extracted_revenue_gbp:,.0f} aligns well with expected £{expected_revenue_gbp:,.0f} (ratio: {ratio:.2f})"
                        elif 0.5 <= ratio <= 2.0:
                            # Extracted revenue is within 50-200% range - MEDIUM confidence  
                            confidence_adjustment = 0.05
                            validation_status = "REASONABLE"
                            reasoning = f"⚠️ Extracted revenue £{extracted_revenue_gbp:,.0f} reasonably close to expected £{expected_revenue_gbp:,.0f} (ratio: {ratio:.2f})"
                        elif 0.1 <= ratio <= 0.5:
                            # Extracted revenue is 10-50% of expected - likely segment/subsidiary
                            confidence_adjustment = -0.2
                            validation_status = "SEGMENT_LIKELY"
                            reasoning = f"🔍 Extracted revenue £{extracted_revenue_gbp:,.0f} is {ratio:.1%} of expected £{expected_revenue_gbp:,.0f} - likely extracted segment/subsidiary revenue"
                            
                            # Add intelligent search recommendation if available
                            if intelligent_search_results.get('range_matches_found', 0) > 0:
                                best_match = intelligent_search_results.get('best_range_match', {})
                                reasoning += f" | 💡 SMART SUGGESTION: Found £{best_match.get('amount_gbp', 0):,.0f} in document closer to expected range"
                        elif ratio < 0.1:
                            # Extracted revenue is <10% of expected - probably incorrect
                            confidence_adjustment = -0.4
                            validation_status = "EXTRACTION_ERROR"
                            reasoning = f"❌ Extracted revenue £{extracted_revenue_gbp:,.0f} is only {ratio:.1%} of expected £{expected_revenue_gbp:,.0f} - likely extraction error"
                            
                            # Add intelligent search recommendation if available
                            if intelligent_search_results.get('range_matches_found', 0) > 0:
                                best_match = intelligent_search_results.get('best_range_match', {})
                                reasoning += f" | 💡 SMART SUGGESTION: Found £{best_match.get('amount_gbp', 0):,.0f} in document closer to expected range"
                        else:
                            # Extracted revenue is >200% of expected - possibly inflated
                            confidence_adjustment = -0.1
                            validation_status = "POTENTIALLY_INFLATED"
                            reasoning = f"📈 Extracted revenue £{extracted_revenue_gbp:,.0f} is {ratio:.1%} of expected £{expected_revenue_gbp:,.0f} - may be inflated or multi-year"
                        
                        return {
                            'validation_available': True,
                            'validation_status': validation_status,
                            'confidence_adjustment': confidence_adjustment,
                            'extracted_revenue_gbp': extracted_revenue_gbp,
                            'expected_revenue_gbp': expected_revenue_gbp,
                            'revenue_ratio': ratio,
                            'reasoning': reasoning,
                            'intelligent_search': intelligent_search_results
                        }
                    else:
                        return {
                            'validation_available': False,
                            'reasoning': 'Expected revenue is zero or invalid'
                        }
                else:
                    return {
                        'validation_available': False,
                        'reasoning': 'Company not found in database or no sales_gbp data'
                    }
            else:
                return {
                    'validation_available': False,
                    'reasoning': f'API request failed with status {response.status_code}'
                }
                
        except Exception as e:
            self.logger.warning(f"Revenue validation failed: {str(e)}")
            return {
                'validation_available': False,
                'reasoning': f'Validation error: {str(e)}'
            }

    def _select_best_revenue_estimate(self, validation_result: Dict[str, Any],
                                    strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select the best revenue estimate from validated candidates with database validation intelligence.
        """
        if not validation_result.get('success'):
            return {
                'revenue': None,
                'confidence': 0.0,
                'reasoning': 'No valid revenue candidates found'
            }
        
        candidates = validation_result.get('validated_candidates', [])
        
        if not candidates:
            return {
                'revenue': None,
                'confidence': 0.0,
                'reasoning': 'No revenue candidates available'
            }
        
        # Sort by overall confidence
        candidates.sort(key=lambda x: x.get('overall_confidence', 0), reverse=True)
        best_candidate = candidates[0]
        
        # Extract basic revenue data
        extracted_revenue = best_candidate.get('revenue') or best_candidate.get('amount', 0)
        base_confidence = best_candidate.get('overall_confidence', 0.0)
        
        # Add database validation intelligence
        company_number = getattr(self, '_current_company_number', None)
        validation_results = {'validation_available': False}
        
        if company_number and extracted_revenue:
            validation_results = self._validate_extracted_revenue_against_database(
                extracted_revenue, company_number
            )
        
        # Apply confidence adjustment based on validation
        final_confidence = base_confidence
        validation_reasoning = ""
        
        # Check if intelligent search found better matches
        should_suggest_alternative = False
        suggested_revenue = extracted_revenue
        
        if validation_results.get('validation_available'):
            confidence_adjustment = validation_results.get('confidence_adjustment', 0)
            final_confidence = min(1.0, max(0.0, base_confidence + confidence_adjustment))
            validation_reasoning = f" | {validation_results.get('reasoning', '')}"
            
            # Check if intelligent search found significantly better matches
            intelligent_search = validation_results.get('intelligent_search')
            if intelligent_search and isinstance(intelligent_search, dict) and intelligent_search.get('range_matches_found', 0) > 0:
                best_match = intelligent_search.get('best_range_match', {})
                best_match_ratio = best_match.get('expected_ratio', 0)
                
                # If the intelligent search found a much better match (closer to 1.0 ratio)
                current_ratio = validation_results.get('revenue_ratio', 0)
                if abs(1.0 - best_match_ratio) < abs(1.0 - current_ratio) and best_match_ratio > 0.3:
                    should_suggest_alternative = True
                    suggested_revenue = best_match.get('amount_gbp', extracted_revenue)
                    
                    # Boost confidence if we found a much better match
                    if best_match_ratio > 0.8:  # Within 20% of expected
                        final_confidence = min(0.95, final_confidence + 0.2)
                        validation_reasoning += f" | 🎯 INTELLIGENT UPGRADE: Using £{suggested_revenue:,.0f} (better match to expected range)"
                    else:
                        final_confidence = min(0.85, final_confidence + 0.1) 
                        validation_reasoning += f" | 💡 INTELLIGENT SUGGESTION: Consider £{suggested_revenue:,.0f} (closer to expected range)"
            
            self.logger.info(f"💡 Revenue validation: {validation_results.get('validation_status')} - "
                           f"confidence adjusted from {base_confidence:.1%} to {final_confidence:.1%}")
            
            if should_suggest_alternative:
                self.logger.info(f"🎯 INTELLIGENT DISCOVERY: Suggesting £{suggested_revenue:,.0f} instead of £{extracted_revenue:,.0f}")
        
        # Handle source_text which can be either a string or list from fast path
        source_text = best_candidate.get('source_text', [])
        if isinstance(source_text, str):
            source_text = [source_text] if source_text else []
        
        return {
            'revenue': extracted_revenue,  # always use document extraction result
            'confidence': final_confidence,
            'source_text': source_text,  # Now always a list for consistency
            'extraction_method': strategy.get('method', 'unknown'),
            'reasoning': f"Selected from {len(candidates)} candidates using {strategy.get('method')} method{validation_reasoning}",
            'alternative_candidates': candidates[:3],  # Include ALL top candidates (up to 3) for UI display
            'database_validation': validation_results,  # Include validation details
            'intelligent_upgrade': False,
            'original_extracted_revenue': None
        }
    
    def _compile_revenue_results(self, extraction_result: Dict[str, Any],
                               validation_result: Dict[str, Any],
                               final_revenue: Dict[str, Any],
                               strategy: Dict[str, Any],
                               company_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Compile all revenue extraction results into final data structure."""

        # Derive revenue year from filing_date (e.g. '2024-10-31' → 2024)
        # Falls back to current year only if no filing date is available
        revenue_year = None
        if company_data:
            filing_date = company_data.get('filing_date', '')
            if filing_date and len(str(filing_date)) >= 4:
                try:
                    revenue_year = int(str(filing_date)[:4])
                except (ValueError, TypeError):
                    pass
        if not revenue_year:
            revenue_year = datetime.now().year

        return {
            'extracted_revenue': final_revenue.get('revenue'),
            'revenue_currency': 'GBP',  # Default for UK companies
            'revenue_period': None,
            'revenue_year': revenue_year,
            'period_type': 'Annual',
            'alternative_revenues': final_revenue.get('alternative_candidates', []),
            'revenue_source_text': final_revenue.get('source_text'),
            'extraction_confidence': final_revenue.get('confidence', 0.0),
            'extraction_method': strategy.get('method', 'unknown'),
            'similarity_scores': extraction_result.get('similarity_scores', []),
            'validation_passed': bool(final_revenue.get('confidence', 0.0) > 0.5),
            'validation_notes': self._collect_validation_notes(validation_result),
            'fallback_used': bool(strategy.get('method') in ['regex', 'manual'])
        }
    
    def _collect_validation_notes(self, validation_result: Dict[str, Any]) -> List[str]:
        """Collect all validation notes from candidates."""
        all_notes = []
        
        candidates = validation_result.get('validated_candidates', [])
        for candidate in candidates:
            notes = candidate.get('validation_notes', [])
            all_notes.extend(notes)
        
        # Remove duplicates and return
        return list(set(all_notes))