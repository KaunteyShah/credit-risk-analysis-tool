#!/usr/bin/env python3
"""
Fast Document Extraction Test - Uses Smart Embedding Service

Tests the complete document extraction workflow with:
1. Smart hybrid embedding service (local-first for speed)
2. Fast offline embeddings using sentence-transformers
3. Clean vector database storage
4. Revenue extraction pipeline

This should solve all the issues:
- No API dependency for bulk processing (fast)
- Proper chunk storage (no "No document chunks could be stored" errors) 
- Local vector database storage
- Optimized hybrid retrieval
"""

import time
from pathlib import Path
from typing import List, Dict, Any
from smart_embedding_service import get_smart_embedding_service
from clean_vector_db import CleanVectorDB
from app_modules.utils.logger import get_logger

logger = get_logger(__name__)

class FastDocumentExtractor:
    """Fast document extractor using smart embedding service."""
    
    def __init__(self):
        """Initialize fast document extractor."""
        self.logger = get_logger("FastExtractor")
        
        # Use smart embedding service (local-first for speed)
        self.embedding_service = get_smart_embedding_service(prefer_local=True)
        
        # Force local embeddings for bulk processing
        self.embedding_service.switch_to_local()
        
        self.logger.info("✅ Fast Document Extractor initialized with local embeddings")
    
    def extract_revenue_from_document(self,
                                    document_id: str,
                                    company_id: str,
                                    document_chunks: List[Dict[str, Any]],
                                    company_name: str = None) -> Dict[str, Any]:
        """
        Fast revenue extraction using local embeddings and clean vector DB.
        
        Args:
            document_id: Document identifier
            company_id: Company identifier
            document_chunks: List of document text chunks
            company_name: Optional company name
            
        Returns:
            Extraction results with revenue data
        """
        self.logger.info(f"🚀 Fast extraction for document: {document_id}")
        start_time = time.time()
        
        try:
            # Create temporary clean vector database
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
                clean_db_path = tmp_db.name
            
            try:
                # Use local embedding dimensions (768D)
                with CleanVectorDB(clean_db_path, embedding_dim=768) as vector_db:
                    self.logger.info(f"✅ Clean vector DB initialized: 768D (local embeddings)")
                    
                    # Step 1: Store document chunks with fast local embeddings
                    stored_count = self._store_document_chunks_fast(
                        vector_db, document_id, company_id, document_chunks
                    )
                    
                    if stored_count == 0:
                        return {
                            'success': False,
                            'error': 'No document chunks could be stored',
                            'stored_chunks': 0,
                            'processing_time': time.time() - start_time
                        }
                    
                    self.logger.info(f"✅ Stored {stored_count} chunks with fast local embeddings")
                    
                    # Step 2: Execute revenue queries using fast similarity search
                    revenue_results = self._execute_fast_revenue_queries(
                        vector_db, document_id, company_id, company_name or "Unknown"
                    )
                    
                    processing_time = time.time() - start_time
                    
                    return {
                        'success': True,
                        'stored_chunks': stored_count,
                        'revenue_results': revenue_results,
                        'processing_time': processing_time,
                        'embedding_service': 'local_fast',
                        'embedding_dimensions': 768,
                        'vector_db': 'clean_sqlite_vec'
                    }
                    
            finally:
                # Cleanup temporary database
                Path(clean_db_path).unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(f"❌ Fast extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _store_document_chunks_fast(self,
                                  vector_db: CleanVectorDB,
                                  document_id: str,
                                  company_id: str,
                                  chunks: List[Dict[str, Any]]) -> int:
        """Store document chunks using fast local embeddings."""
        stored_count = 0
        
        # Extract all chunk texts first
        chunk_texts = []
        for chunk in chunks:
            chunk_text = chunk.get('text', '') if isinstance(chunk, dict) else str(chunk)
            if chunk_text.strip():
                chunk_texts.append(chunk_text)
        
        if not chunk_texts:
            self.logger.warning("No valid chunk texts found")
            return 0
            
        self.logger.info(f"🔄 Generating embeddings for {len(chunk_texts)} chunks using LOCAL service...")
        
        # Generate all embeddings in one batch (FAST)
        start_time = time.time()
        embeddings = self.embedding_service.encode(chunk_texts, force_local=True)
        embedding_time = time.time() - start_time
        
        self.logger.info(f"⚡ Generated {len(embeddings)} embeddings in {embedding_time:.2f}s (LOCAL)")
        
        # Store each chunk with its embedding
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            try:
                chunk_text = chunk.get('text', '') if isinstance(chunk, dict) else str(chunk)
                if not chunk_text.strip():
                    continue
                
                success = vector_db.store_document_with_embedding(
                    document_id=f"{document_id}_chunk_{i}",
                    company_id=company_id,
                    document_type='financial_filing',
                    chunk_index=i,
                    chunk_text=chunk_text,
                    embedding=embedding,
                    metadata={
                        'source_document': document_id,
                        'chunk_index': i,
                        'embedding_model': 'all-mpnet-base-v2',
                        'dimensions': len(embedding),
                        'processing_method': 'fast_local'
                    }
                )
                
                if success:
                    stored_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to store chunk {i}: {e}")
                
        return stored_count
    
    def _execute_fast_revenue_queries(self,
                                    vector_db: CleanVectorDB,
                                    document_id: str,
                                    company_id: str,
                                    company_name: str) -> List[Dict[str, Any]]:
        """Execute revenue queries using fast local embeddings."""
        
        # Revenue-focused queries
        revenue_queries = [
            "net revenue total revenue sales turnover",
            "annual revenue financial performance results",
            f"{company_name} revenue sales income turnover", 
            "profit loss statement revenue figures",
            "financial results revenue growth"
        ]
        
        all_results = []
        
        for query in revenue_queries:
            try:
                self.logger.info(f"🔍 Revenue query: {query}")
                
                # Generate query embedding (local/fast)
                query_embeddings = self.embedding_service.encode([query], force_local=True)
                if not query_embeddings:
                    continue
                    
                query_embedding = query_embeddings[0]
                
                # Fast similarity search
                similar_results = vector_db.native_similarity_search(
                    query_embedding=query_embedding,
                    limit=5,
                    company_id=company_id
                )
                
                # Process results
                for result in similar_results:
                    revenue_match = self._extract_revenue_from_text(result.chunk_text)
                    if revenue_match:
                        all_results.append({
                            'query': query,
                            'text': result.chunk_text,
                            'similarity': result.similarity_score,
                            'revenue_match': revenue_match,
                            'chunk_id': result.document_id
                        })
                
            except Exception as e:
                self.logger.error(f"Query failed: {e}")
                
        return all_results
    
    def _extract_revenue_from_text(self, text: str) -> Dict[str, Any]:
        """Extract revenue information from text using patterns."""
        import re
        
        # Revenue patterns
        revenue_patterns = [
            r'(?:net\s+)?(?:revenue|sales|turnover)(?:\s+was|\s+of|\s+reached)?\s*[£$€]?([\d,]+(?:\.\d+)?)\s*(?:billion|million|bn|mn|m)?',
            r'[£$€]([\d,]+(?:\.\d+)?)\s*(?:billion|million|bn|mn|m)?\s+(?:revenue|sales|turnover)',
            r'(?:total\s+)?(?:revenue|sales|turnover):\s*[£$€]?([\d,]+(?:\.\d+)?)\s*(?:billion|million|bn|mn|m)?'
        ]
        
        for pattern in revenue_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Extract numeric value
                    value_str = matches[0].replace(',', '')
                    value = float(value_str)
                    
                    # Determine scale
                    scale_multiplier = 1
                    if 'billion' in text.lower() or 'bn' in text.lower():
                        scale_multiplier = 1000000000
                    elif 'million' in text.lower() or 'mn' in text.lower() or 'm' in text.lower():
                        scale_multiplier = 1000000
                    
                    final_value = value * scale_multiplier
                    
                    return {
                        'raw_value': value,
                        'scale_multiplier': scale_multiplier,
                        'final_value': final_value,
                        'currency': 'GBP',  # Default assumption
                        'text_match': matches[0],
                        'confidence': 0.8  # Pattern-based confidence
                    }
                except:
                    continue
                    
        return None
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the fast extraction service."""
        return {
            'extraction_method': 'fast_local_embeddings',
            'embedding_service': self.embedding_service.get_service_info(),
            'benefits': [
                'No API dependency',
                'Fast offline processing',
                'Reliable chunk storage', 
                'Local vector database',
                'Optimized for bulk processing'
            ]
        }


def test_fast_extraction():
    """Test the fast document extraction system."""
    print("🧪 Testing Fast Document Extraction System...")
    
    # Initialize fast extractor
    extractor = FastDocumentExtractor()
    
    # Show service info
    import json
    print("\n📊 FAST EXTRACTION SERVICE INFO:")
    print(json.dumps(extractor.get_service_info(), indent=2))
    
    # Test with sample document chunks
    test_chunks = [
        {'text': 'Imperial Brands plc is a British multinational tobacco company headquartered in London.'},
        {'text': 'Net revenue was £31.4 billion in 2023, representing strong performance across all divisions.'},
        {'text': 'Total turnover from tobacco sales increased to £8.2 billion, driven by premium product growth.'},
        {'text': 'Operating income reached £2.1 billion for the financial year ended September 2023.'},
        {'text': 'The company reported solid growth in NGP revenue of £1.2 billion, up 15% year-over-year.'},
        {'text': 'Dividend payments to shareholders totaled £850 million during the reporting period.'},
        {'text': 'Research and development expenditure was £180 million, focusing on next-generation products.'},
        {'text': 'Total assets under management reached £45.7 billion at the end of the fiscal year.'}
    ]
    
    print(f"\n🧪 Testing with {len(test_chunks)} document chunks...")
    
    # Run fast extraction
    start_time = time.time()
    result = extractor.extract_revenue_from_document(
        document_id="test_imperial_brands_2023",
        company_id="imperial_brands_plc",
        document_chunks=test_chunks,
        company_name="Imperial Brands"
    )
    end_time = time.time()
    
    print(f"\n✅ EXTRACTION RESULTS:")
    print(f"Success: {result.get('success', False)}")
    print(f"Processing time: {end_time - start_time:.2f}s")
    
    if result.get('success'):
        print(f"Stored chunks: {result.get('stored_chunks', 0)}")
        print(f"Revenue results found: {len(result.get('revenue_results', []))}")
        print(f"Embedding service: {result.get('embedding_service', 'unknown')}")
        print(f"Vector DB: {result.get('vector_db', 'unknown')}")
        
        # Show revenue matches
        revenue_results = result.get('revenue_results', [])
        if revenue_results:
            print(f"\n💰 REVENUE MATCHES FOUND:")
            for i, match in enumerate(revenue_results[:3]):  # Show top 3
                print(f"  {i+1}. {match.get('revenue_match', {}).get('final_value', 0):,.0f} GBP")
                print(f"     Similarity: {match.get('similarity', 0):.3f}")
                print(f"     Text: {match.get('text', '')[:100]}...")
        else:
            print("   No revenue matches found")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n🎯 PERFORMANCE SUMMARY:")
    print(f"   Total time: {end_time - start_time:.2f}s")
    print(f"   Embedding method: LOCAL (offline)")
    print(f"   Storage method: sqlite-vec")
    print(f"   API calls: 0 (completely offline)")


if __name__ == "__main__":
    test_fast_extraction()