"""
Data models for the agentic revenue extraction workflow.
Self-contained models that don't depend on legacy agents.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class SemanticQuery:
    """Query for semantic search in financial documents."""
    query_text: str
    query_type: str = "financial_extraction"
    expected_data_type: str = "text"
    context_window: int = 3


@dataclass
class DocumentChunk:
    """Processed document chunk with enhanced metadata for Q&A referencing."""
    text: str
    page_number: Optional[int] = None
    section_type: str = "content"
    chunk_index: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property 
    def reference_info(self) -> Dict[str, Any]:
        """Get comprehensive reference information for Q&A citations."""
        return {
            'chunk_id': f"chunk_{self.chunk_index:03d}",
            'document_title': self.metadata.get('document_title', 'Financial Document'),
            'company_name': self.metadata.get('company_name', 'Unknown Company'),
            'page_number': self.page_number,
            'section_type': self.section_type,
            'section_title': self.metadata.get('section_title'),
            'chunk_boundaries': {
                'start_char': self.metadata.get('start_char', 0),
                'end_char': self.metadata.get('end_char', len(self.text)),
                'start_page': self.metadata.get('start_page', self.page_number),
                'end_page': self.metadata.get('end_page', self.page_number)
            },
            'context': {
                'preceding_text': self.metadata.get('preceding_text', ''),
                'following_text': self.metadata.get('following_text', ''),
                'paragraph_number': self.metadata.get('paragraph_number')
            },
            'document_info': {
                'filing_date': self.metadata.get('filing_date'),
                'filing_type': self.metadata.get('filing_type'),
                'filename': self.metadata.get('filename')
            }
        }
    
    def get_citation_text(self) -> str:
        """Generate user-friendly citation text for Q&A responses."""
        ref = self.reference_info
        parts = []
        
        # Document title and company
        if ref['document_title'] and ref['company_name']:
            parts.append(f"'{ref['document_title']}' ({ref['company_name']})")
        
        # Page reference
        if ref['page_number']:
            parts.append(f"Page {ref['page_number']}")
        
        # Section reference
        if ref['section_title']:
            parts.append(f"Section: {ref['section_title']}")
        elif ref['section_type'] != 'content':
            parts.append(f"Section: {ref['section_type'].replace('_', ' ').title()}")
        
        # Chunk reference
        parts.append(f"Chunk {self.chunk_index + 1}")
        
        return " | ".join(parts)


@dataclass
class RAGResult:
    """Result from document processing with extracted data."""
    query: SemanticQuery
    relevant_chunks: List[DocumentChunk]
    extracted_data: Any = None
    confidence: float = 0.0
    reasoning: str = ""
    sources: List[str] = field(default_factory=list)


@dataclass
class DocumentProcessingResult:
    """Result from document processing pipeline."""
    success: bool
    document_id: str
    chunk_count: int = 0
    page_count: int = 0
    embedding_count: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0