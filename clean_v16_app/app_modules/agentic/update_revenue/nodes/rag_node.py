"""
RAG Node for Agentic Revenue Extraction Workflow

Real-time document retrieval and analysis node that:
1. Performs semantic search on processed document chunks
2. Extracts relevant financial information using vector similarity
3. Provides contextual revenue data for estimation
4. Uses native vector database operations for high performance

This is an agentic workflow node, not a legacy agent.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..document_processor import AgenticDocumentProcessor
from ..data_models import SemanticQuery, RAGResult, DocumentChunk
from ....utils.logger import get_logger

logger = get_logger(__name__)


class RAGNode:
    """
    RAG (Retrieval-Augmented Generation) node for agentic revenue extraction.
    
    Performs real-time document retrieval and contextual analysis:
    1. Receives queries from turnover estimation node
    2. Searches processed document chunks using vector similarity
    3. Extracts relevant financial data and context
    4. Returns structured data for revenue calculation
    
    This is a workflow node that processes state and makes decisions.
    """
    
    def __init__(self, document_processor: Optional[AgenticDocumentProcessor] = None):
        """
        Initialize RAG node with document processor.
        
        Args:
            document_processor: Document processor with vector database access
        """
        self.document_processor = document_processor or AgenticDocumentProcessor()
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Configure for revenue-focused queries
        self.revenue_queries = [
            "revenue turnover sales income annual",
            "profit loss earnings before tax",
            "gross revenue net sales total income",
            "financial performance year ended"
        ]
        
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute RAG node for document retrieval and analysis.
        
        Args:
            state: Current workflow state with document processing data
            
        Returns:
            Updated state with RAG analysis results
        """
        start_time = datetime.now()
        self.logger.info("🔍 Starting RAG document analysis")
        
        try:
            # Extract document processing data from previous node
            document_data = state.get('document_processing_data', {})
            company_data = state.get('company_filing_data', {})
            
            document_id = document_data.get('document_id') or company_data.get('document_id')
            company_name = company_data.get('company_name', 'Unknown Company')
            
            if not document_id:
                self.logger.warning("No document ID available for RAG analysis")
                return self._create_fallback_state(state, "No document available for analysis")
            
            # Perform multi-query RAG analysis
            rag_results = self._perform_comprehensive_rag_analysis(document_id, company_name)
            
            # Extract and consolidate financial insights
            financial_insights = self._consolidate_financial_insights(rag_results)
            
            # Calculate confidence and prepare results
            overall_confidence = self._calculate_overall_confidence(rag_results)
            
            # Record workflow decision
            decision = {
                'decision_point': "rag_analysis",
                'decision_type': "retrieval",
                'decision_result': "analysis_completed",
                'confidence': overall_confidence,
                'reasoning': f"Analyzed {len(rag_results)} queries, found {sum(len(r.relevant_chunks) for r in rag_results)} relevant chunks",
                'timestamp': datetime.now().isoformat()
            }
            
            # Update workflow state
            execution_time = (datetime.now() - start_time).total_seconds()
            
            updated_state = dict(state)
            updated_state['rag_analysis_data'] = {
                'rag_results': rag_results,
                'financial_insights': financial_insights,
                'overall_confidence': overall_confidence,
                'queries_processed': len(rag_results),
                'total_chunks_found': sum(len(r.relevant_chunks) for r in rag_results),
                'analysis_time': execution_time,
                'document_id': document_id
            }
            
            # Add workflow tracking
            if 'workflow_decisions' not in updated_state:
                updated_state['workflow_decisions'] = []
            updated_state['workflow_decisions'].append(decision)
            
            if 'node_execution_times' not in updated_state:
                updated_state['node_execution_times'] = {}
            updated_state['node_execution_times']['rag_analysis'] = execution_time
            
            if 'node_confidence_scores' not in updated_state:
                updated_state['node_confidence_scores'] = {}
            updated_state['node_confidence_scores']['rag_analysis'] = overall_confidence
            
            updated_state['current_node'] = 'turnover_estimation'
            
            self.logger.info(f"✅ RAG analysis completed in {execution_time:.2f}s with confidence {overall_confidence:.2f}")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ RAG analysis failed: {str(e)}")
            return self._create_fallback_state(state, str(e))
    
    def _perform_comprehensive_rag_analysis(self, document_id: str, company_name: str) -> List[RAGResult]:
        """
        Perform comprehensive RAG analysis with multiple financial queries.
        
        Args:
            document_id: Document to search
            company_name: Company name for context
            
        Returns:
            List of RAG results for different query types
        """
        rag_results = []
        
        for query_text in self.revenue_queries:
            try:
                # Create semantic query
                query = SemanticQuery(
                    query_text=query_text,
                    query_type="financial_extraction",
                    expected_data_type="numeric",
                    context_window=3
                )
                
                # Perform document query
                result = self.document_processor.query_document(query, document_id)
                
                if result.relevant_chunks:
                    rag_results.append(result)
                    self.logger.info(f"Query '{query_text[:30]}...' found {len(result.relevant_chunks)} chunks")
                
            except Exception as e:
                self.logger.error(f"Query failed for '{query_text}': {e}")
                continue
        
        return rag_results
    
    def _consolidate_financial_insights(self, rag_results: List[RAGResult]) -> Dict[str, Any]:
        """
        Consolidate financial insights from multiple RAG results.
        
        Args:
            rag_results: Results from multiple queries
            
        Returns:
            Consolidated financial insights
        """
        insights = {
            'revenue_indicators': [],
            'profit_indicators': [],
            'financial_metrics': {},
            'contextual_information': [],
            'confidence_scores': {}
        }
        
        for result in rag_results:
            query_type = result.query.query_text.lower()
            
            # Categorize findings
            if any(term in query_type for term in ['revenue', 'turnover', 'sales']):
                insights['revenue_indicators'].extend(result.relevant_chunks)
                if result.extracted_data:
                    insights['financial_metrics'].update(result.extracted_data)
            
            elif any(term in query_type for term in ['profit', 'earnings']):
                insights['profit_indicators'].extend(result.relevant_chunks)
                if result.extracted_data:
                    insights['financial_metrics'].update(result.extracted_data)
            
            # Store confidence scores
            insights['confidence_scores'][query_type[:20]] = result.confidence
            
            # Add contextual information
            for chunk in result.relevant_chunks:
                if chunk.section_type in ['financial_statement', 'balance_sheet']:
                    insights['contextual_information'].append({
                        'text': chunk.text[:200] + '...',
                        'section': chunk.section_type,
                        'confidence': result.confidence
                    })
        
        return insights
    
    def _calculate_overall_confidence(self, rag_results: List[RAGResult]) -> float:
        """
        Calculate overall confidence from RAG results.
        
        Args:
            rag_results: Results from multiple queries
            
        Returns:
            Overall confidence score
        """
        if not rag_results:
            return 0.0
        
        # Weight by number of chunks found and confidence
        total_weighted_confidence = 0.0
        total_weight = 0.0
        
        for result in rag_results:
            weight = len(result.relevant_chunks)  # More chunks = higher weight
            total_weighted_confidence += result.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(total_weighted_confidence / total_weight, 0.95)  # Cap at 0.95
    
    def _create_fallback_state(self, state: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """
        Create fallback state when RAG analysis fails.
        
        Args:
            state: Current state
            error_message: Error description
            
        Returns:
            Updated state with fallback data
        """
        updated_state = dict(state)
        
        # Create minimal RAG analysis data
        updated_state['rag_analysis_data'] = {
            'rag_results': [],
            'financial_insights': {
                'revenue_indicators': [],
                'profit_indicators': [],
                'financial_metrics': {},
                'contextual_information': [],
                'confidence_scores': {}
            },
            'overall_confidence': 0.0,
            'queries_processed': 0,
            'total_chunks_found': 0,
            'analysis_time': 0.0,
            'error': error_message
        }
        
        # Add to errors
        if 'errors' not in updated_state:
            updated_state['errors'] = []
        updated_state['errors'].append(f"RAG analysis failed: {error_message}")
        
        if 'fallback_triggers' not in updated_state:
            updated_state['fallback_triggers'] = []
        updated_state['fallback_triggers'].append('rag_analysis_failure')
        
        updated_state['current_node'] = 'turnover_estimation'  # Continue workflow
        
        return updated_state
    
    def query_specific_information(self, document_id: str, query_text: str) -> RAGResult:
        """
        Query specific information from a document (for direct use by other nodes).
        
        Args:
            document_id: Document to search
            query_text: Specific query text
            
        Returns:
            RAG result with relevant information
        """
        query = SemanticQuery(
            query_text=query_text,
            query_type="specific_query",
            expected_data_type="text"
        )
        
        return self.document_processor.query_document(query, document_id)
    
    def get_revenue_context(self, document_id: str) -> Dict[str, Any]:
        """
        Get comprehensive revenue context for a document.
        
        Args:
            document_id: Document to analyze
            
        Returns:
            Revenue context information
        """
        revenue_query = SemanticQuery(
            query_text="revenue turnover sales income annual total",
            query_type="revenue_context",
            expected_data_type="numeric"
        )
        
        result = self.document_processor.query_document(revenue_query, document_id)
        
        return {
            'relevant_chunks': result.relevant_chunks,
            'extracted_data': result.extracted_data,
            'confidence': result.confidence,
            'context_summary': result.reasoning
        }