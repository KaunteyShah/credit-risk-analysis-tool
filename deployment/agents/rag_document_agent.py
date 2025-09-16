"""
RAG Document Agent - Vector-based semantic search and analysis for complex document queries.
"""
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import time
import json

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.base_agent import BaseAgent, AgentResult
from app.utils.config_manager import config
from app.utils.logger import logger

@dataclass
class DocumentChunk:
    """Represents a chunk of document text with metadata."""
    text: str
    page_number: Optional[int]
    section_type: str
    chunk_index: int
    metadata: Dict[str, Any]

@dataclass
class SemanticQuery:
    """Represents a semantic query for document analysis."""
    query_text: str
    query_type: str  # 'financial_data', 'company_info', 'risk_factors', etc.
    expected_data_type: str  # 'numeric', 'text', 'date', etc.
    context_window: int = 3  # Number of surrounding chunks to include

@dataclass
class RAGResult:
    """Result from RAG document analysis."""
    query: SemanticQuery
    relevant_chunks: List[DocumentChunk]
    extracted_data: Any
    confidence: float
    reasoning: str
    sources: List[str]

class RAGDocumentAgent(BaseAgent):
    """Agent that uses RAG (Retrieval Augmented Generation) for sophisticated document analysis."""
    
    def __init__(self):
        super().__init__("RAGDocumentAgent")
        
        # Configuration
        self.chunk_size = config.get("rag.chunk_size", 512)
        self.chunk_overlap = config.get("rag.chunk_overlap", 50)
        self.similarity_threshold = config.get("rag.similarity_threshold", 0.7)
        self.max_chunks_per_query = config.get("rag.max_chunks_per_query", 5)
        
        # Vector database configuration
        self.vector_db_type = config.get("rag.vector_db", "chromadb")  # 'chromadb', 'pinecone', 'mock'
        
        # Initialize components
        self._initialize_vector_db()
        self._initialize_embeddings()
        self._initialize_llm()
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process RAG-based document analysis.
        
        Args:
            data: Dictionary containing:
                - documents: List of documents to analyze
                - queries: List of SemanticQuery objects
                - rebuild_index: Whether to rebuild the vector index
        
        Returns:
            AgentResult with RAG analysis results
        """
        try:
            self.log_activity("Starting RAG document analysis")
            
            documents = data.get("documents", [])
            queries = data.get("queries", [])
            rebuild_index = data.get("rebuild_index", False)
            
            if not documents:
                return self.create_result(
                    success=False,
                    error_message="No documents provided for RAG analysis"
                )
            
            if not queries:
                return self.create_result(
                    success=False,
                    error_message="No queries provided for RAG analysis"
                )
            
            # Process documents and build/update vector index
            if rebuild_index or not self._index_exists():
                self.log_activity("Building vector index from documents")
                self._build_vector_index(documents)
            
            # Process queries
            rag_results = []
            for query in queries:
                try:
                    result = self._process_semantic_query(query)
                    rag_results.append(result)
                except Exception as e:
                    self.log_activity(f"Error processing query '{query.query_text}': {str(e)}", "ERROR")
                    rag_results.append(RAGResult(
                        query=query,
                        relevant_chunks=[],
                        extracted_data=None,
                        confidence=0.0,
                        reasoning=f"Query processing failed: {str(e)}",
                        sources=[]
                    ))
            
            # Calculate summary metrics
            successful_queries = [r for r in rag_results if r.confidence > 0.5]
            avg_confidence = sum(r.confidence for r in successful_queries) / len(successful_queries) if successful_queries else 0.0
            
            self.log_activity(f"Completed RAG analysis for {len(queries)} queries")
            
            return self.create_result(
                success=True,
                data={
                    "rag_results": rag_results,
                    "summary": {
                        "total_queries": len(queries),
                        "successful_queries": len(successful_queries),
                        "average_confidence": avg_confidence,
                        "vector_db_type": self.vector_db_type,
                        "total_chunks_indexed": self._get_index_size()
                    }
                },
                confidence=avg_confidence,
                query_count=len(successful_queries)
            )
            
        except Exception as e:
            error_msg = f"RAG document analysis failed: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
    
    def query_financial_data(self, query_text: str, documents: List[Any]) -> RAGResult:
        """
        Convenience method for querying financial data from documents.
        
        Args:
            query_text: Natural language query for financial data
            documents: List of documents to search
        
        Returns:
            RAGResult with financial data
        """
        semantic_query = SemanticQuery(
            query_text=query_text,
            query_type="financial_data",
            expected_data_type="numeric",
            context_window=3
        )
        
        # Build index if needed
        if not self._index_exists():
            self._build_vector_index(documents)
        
        return self._process_semantic_query(semantic_query)
    
    def _build_vector_index(self, documents: List[Any]) -> None:
        """Build vector index from documents."""
        try:
            self.log_activity("Chunking documents for vector indexing")
            
            all_chunks = []
            for doc_idx, document in enumerate(documents):
                # Extract text from document
                if hasattr(document, 'content'):
                    text_content = self._extract_text_from_document(document.content)
                else:
                    text_content = self._extract_text_from_document(document)
                
                if not text_content:
                    continue
                
                # Create chunks
                chunks = self._create_document_chunks(text_content, doc_idx)
                all_chunks.extend(chunks)
            
            self.log_activity(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
            
            # Generate embeddings and store in vector database
            self._store_chunks_in_vector_db(all_chunks)
            
        except Exception as e:
            self.log_activity(f"Error building vector index: {str(e)}", "ERROR")
            raise
    
    def _process_semantic_query(self, query: SemanticQuery) -> RAGResult:
        """Process a semantic query using RAG."""
        try:
            start_time = time.time()
            
            # Generate query embedding
            query_embedding = self._generate_embedding(query.query_text)
            
            # Retrieve relevant chunks
            relevant_chunks = self._retrieve_relevant_chunks(query_embedding, query.context_window)
            
            if not relevant_chunks:
                return RAGResult(
                    query=query,
                    relevant_chunks=[],
                    extracted_data=None,
                    confidence=0.0,
                    reasoning="No relevant chunks found for query",
                    sources=[]
                )
            
            # Extract data using LLM analysis
            extracted_data, confidence, reasoning = self._extract_data_with_llm(query, relevant_chunks)
            
            # Prepare sources
            sources = [f"Chunk {chunk.chunk_index} (Page {chunk.page_number})" 
                      for chunk in relevant_chunks if chunk.page_number]
            
            processing_time = time.time() - start_time
            self.log_activity(f"Query processed in {processing_time:.2f}s with confidence {confidence:.2f}")
            
            return RAGResult(
                query=query,
                relevant_chunks=relevant_chunks,
                extracted_data=extracted_data,
                confidence=confidence,
                reasoning=reasoning,
                sources=sources
            )
            
        except Exception as e:
            self.log_activity(f"Error processing semantic query: {str(e)}", "ERROR")
            return RAGResult(
                query=query,
                relevant_chunks=[],
                extracted_data=None,
                confidence=0.0,
                reasoning=f"Query processing error: {str(e)}",
                sources=[]
            )
    
    def _create_document_chunks(self, text: str, doc_idx: int) -> List[DocumentChunk]:
        """Create chunks from document text."""
        chunks = []
        
        # Split text into sentences for better chunking
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # Create chunk
                section_type = self._identify_section_type(current_chunk)
                chunk = DocumentChunk(
                    text=current_chunk.strip(),
                    page_number=None,  # Would be extracted from PDF metadata
                    section_type=section_type,
                    chunk_index=chunk_index,
                    metadata={
                        "document_index": doc_idx,
                        "character_count": len(current_chunk),
                        "sentence_count": current_chunk.count('.')
                    }
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
                chunk_index += 1
            else:
                current_chunk += " " + sentence
        
        # Add final chunk if there's remaining text
        if current_chunk.strip():
            section_type = self._identify_section_type(current_chunk)
            chunk = DocumentChunk(
                text=current_chunk.strip(),
                page_number=None,
                section_type=section_type,
                chunk_index=chunk_index,
                metadata={
                    "document_index": doc_idx,
                    "character_count": len(current_chunk),
                    "sentence_count": current_chunk.count('.')
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting - could be enhanced with NLTK or spaCy
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _identify_section_type(self, text: str) -> str:
        """Identify the type of section based on content."""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['profit', 'loss', 'revenue', 'turnover', 'income']):
            return "financial_statement"
        elif any(keyword in text_lower for keyword in ['balance', 'assets', 'liabilities']):
            return "balance_sheet"
        elif any(keyword in text_lower for keyword in ['cash', 'flow', 'financing', 'investing']):
            return "cash_flow"
        elif any(keyword in text_lower for keyword in ['risk', 'uncertainty', 'contingent']):
            return "risk_factors"
        elif any(keyword in text_lower for keyword in ['director', 'governance', 'board']):
            return "governance"
        else:
            return "general"
    
    def _extract_text_from_document(self, document_content: bytes) -> str:
        """Extract text from document content."""
        try:
            # Mock implementation - in production would use actual PDF extraction
            return """
            FINANCIAL STATEMENTS
            
            PROFIT AND LOSS ACCOUNT
            For the year ended 31 December 2023
            
            The company's revenue for the year was £850,000, representing a 15% increase from the previous year.
            This growth was driven by strong performance in our core markets and successful launch of new products.
            
            Operating costs were well controlled at £650,000, resulting in an operating profit of £200,000.
            Interest expenses of £15,000 were incurred on business loans.
            
            Profit before taxation was £185,000, with corporation tax of £37,000.
            Net profit after tax was £148,000, which will be retained to fund future growth.
            
            BALANCE SHEET
            As at 31 December 2023
            
            Fixed assets comprise property, plant and equipment valued at £300,000.
            Current assets include inventory of £120,000 and trade debtors of £80,000.
            Cash at bank amounts to £45,000.
            
            The company maintains a strong balance sheet with total assets of £545,000.
            Current liabilities are £95,000, primarily trade creditors.
            Long-term debt stands at £180,000.
            
            NOTES TO THE FINANCIAL STATEMENTS
            
            1. Revenue Recognition
            Revenue is recognized when goods are delivered and the customer accepts them.
            The company operates on standard 30-day payment terms.
            
            2. Risk Management
            The company faces normal commercial risks including credit risk from customers
            and market risk from economic conditions. These risks are actively managed
            through diversification and regular monitoring.
            """
            
        except Exception as e:
            self.log_activity(f"Error extracting text from document: {str(e)}", "ERROR")
            return ""
    
    def _initialize_vector_db(self) -> None:
        """Initialize vector database connection."""
        try:
            if self.vector_db_type == "chromadb":
                try:
                    import chromadb  # type: ignore
                    self.vector_client = chromadb.Client()
                    self.collection = self.vector_client.get_or_create_collection("financial_documents")
                    self.log_activity("ChromaDB initialized successfully")
                except ImportError:
                    self.vector_db_type = "mock"
                    self.log_activity("ChromaDB not available, using mock vector database", "WARNING")
            
            elif self.vector_db_type == "pinecone":
                try:
                    import pinecone  # type: ignore
                    # Pinecone initialization would go here
                    self.log_activity("Pinecone initialization - placeholder")
                    self.vector_db_type = "mock"
                except ImportError:
                    self.vector_db_type = "mock"
                    self.log_activity("Pinecone not available, using mock vector database", "WARNING")
            
            if self.vector_db_type == "mock":
                self.mock_vector_store = {}
                self.log_activity("Using mock vector database for demonstration")
                
        except Exception as e:
            self.log_activity(f"Error initializing vector database: {str(e)}", "ERROR")
            self.vector_db_type = "mock"
            self.mock_vector_store = {}
    
    def _initialize_embeddings(self) -> None:
        """Initialize embedding model."""
        try:
            # In production, would use actual embedding models
            self.embedding_model = "mock"
            self.embedding_dimension = 768
            self.log_activity("Mock embedding model initialized")
        except Exception as e:
            self.log_activity(f"Error initializing embeddings: {str(e)}", "ERROR")
            self.embedding_model = "mock"
    
    def _initialize_llm(self) -> None:
        """Initialize language model for data extraction."""
        try:
            # In production, would initialize actual LLM
            self.llm_model = "mock"
            self.log_activity("Mock LLM initialized")
        except Exception as e:
            self.log_activity(f"Error initializing LLM: {str(e)}", "ERROR")
            self.llm_model = "mock"
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            if self.embedding_model == "mock":
                # Mock embedding based on text characteristics
                import hashlib
                hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
                # Generate pseudo-random but deterministic embedding
                embedding = [(hash_val >> i) % 2 - 0.5 for i in range(self.embedding_dimension)]
                return embedding
            else:
                # In production, use actual embedding model
                return [0.0] * self.embedding_dimension
        except Exception as e:
            self.log_activity(f"Error generating embedding: {str(e)}", "ERROR")
            return [0.0] * self.embedding_dimension
    
    def _store_chunks_in_vector_db(self, chunks: List[DocumentChunk]) -> None:
        """Store document chunks in vector database."""
        try:
            if self.vector_db_type == "mock":
                for chunk in chunks:
                    embedding = self._generate_embedding(chunk.text)
                    self.mock_vector_store[chunk.chunk_index] = {
                        "chunk": chunk,
                        "embedding": embedding
                    }
            else:
                # Store in actual vector database
                for chunk in chunks:
                    embedding = self._generate_embedding(chunk.text)
                    self.collection.add(
                        embeddings=[embedding],
                        documents=[chunk.text],
                        metadatas=[chunk.metadata],
                        ids=[str(chunk.chunk_index)]
                    )
            
            self.log_activity(f"Stored {len(chunks)} chunks in vector database")
            
        except Exception as e:
            self.log_activity(f"Error storing chunks in vector database: {str(e)}", "ERROR")
            raise
    
    def _retrieve_relevant_chunks(self, query_embedding: List[float], context_window: int) -> List[DocumentChunk]:
        """Retrieve relevant chunks based on query embedding."""
        try:
            if self.vector_db_type == "mock":
                # Mock similarity calculation
                similarities = []
                for chunk_id, data in self.mock_vector_store.items():
                    similarity = self._calculate_cosine_similarity(query_embedding, data["embedding"])
                    if similarity > self.similarity_threshold:
                        similarities.append((similarity, data["chunk"]))
                
                # Sort by similarity and return top chunks
                similarities.sort(key=lambda x: x[0], reverse=True)
                return [chunk for _, chunk in similarities[:self.max_chunks_per_query]]
            
            else:
                # Query actual vector database
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=self.max_chunks_per_query
                )
                # Convert results to DocumentChunk objects
                # Implementation would depend on vector database format
                return []
                
        except Exception as e:
            self.log_activity(f"Error retrieving relevant chunks: {str(e)}", "ERROR")
            return []
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            import math
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        except Exception:
            return 0.0
    
    def _extract_data_with_llm(self, query: SemanticQuery, chunks: List[DocumentChunk]) -> Tuple[Any, float, str]:
        """Extract data from chunks using LLM analysis."""
        try:
            # Mock LLM analysis based on query type and chunk content
            if query.query_type == "financial_data":
                return self._mock_financial_extraction(query, chunks)
            else:
                return self._mock_general_extraction(query, chunks)
                
        except Exception as e:
            self.log_activity(f"Error in LLM data extraction: {str(e)}", "ERROR")
            return None, 0.0, f"LLM extraction failed: {str(e)}"
    
    def _mock_financial_extraction(self, query: SemanticQuery, chunks: List[DocumentChunk]) -> Tuple[Any, float, str]:
        """Mock financial data extraction."""
        query_lower = query.query_text.lower()
        
        # Look for financial keywords in chunks
        financial_data = {}
        confidence = 0.0
        reasoning_parts = []
        
        for chunk in chunks:
            chunk_text = chunk.text.lower()
            
            if "revenue" in query_lower and any(keyword in chunk_text for keyword in ["revenue", "turnover"]):
                # Extract revenue-like numbers
                import re
                numbers = re.findall(r'£([\d,]+)', chunk.text)
                if numbers:
                    financial_data["revenue"] = int(numbers[0].replace(',', ''))
                    confidence += 0.3
                    reasoning_parts.append(f"Found revenue reference in {chunk.section_type} section")
            
            if "profit" in query_lower and "profit" in chunk_text:
                numbers = re.findall(r'£([\d,]+)', chunk.text)
                if numbers:
                    financial_data["profit"] = int(numbers[-1].replace(',', ''))
                    confidence += 0.3
                    reasoning_parts.append(f"Found profit reference in {chunk.section_type} section")
        
        confidence = min(confidence, 0.9)  # Cap confidence
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No clear financial data patterns found"
        
        return financial_data if financial_data else None, confidence, reasoning
    
    def _mock_general_extraction(self, query: SemanticQuery, chunks: List[DocumentChunk]) -> Tuple[Any, float, str]:
        """Mock general data extraction."""
        # Simple keyword matching for demonstration
        query_keywords = query.query_text.lower().split()
        
        relevant_text = []
        confidence = 0.0
        
        for chunk in chunks:
            chunk_text = chunk.text.lower()
            keyword_matches = sum(1 for keyword in query_keywords if keyword in chunk_text)
            
            if keyword_matches > 0:
                relevant_text.append(chunk.text[:200])  # First 200 characters
                confidence += keyword_matches * 0.1
        
        confidence = min(confidence, 0.8)
        result_text = " ... ".join(relevant_text) if relevant_text else None
        reasoning = f"Found {len(relevant_text)} chunks with keyword matches"
        
        return result_text, confidence, reasoning
    
    def _index_exists(self) -> bool:
        """Check if vector index exists."""
        if self.vector_db_type == "mock":
            return len(self.mock_vector_store) > 0
        else:
            try:
                # Check if collection has any documents
                return self.collection.count() > 0
            except:
                return False
    
    def _get_index_size(self) -> int:
        """Get the number of chunks in the index."""
        if self.vector_db_type == "mock":
            return len(self.mock_vector_store)
        else:
            try:
                return self.collection.count()
            except:
                return 0
