"""
Azure Document Intelligence Service for Enhanced Financial Document Processing
"""
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import asyncio
from dataclasses import dataclass
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

@dataclass
class FinancialExtraction:
    """Enhanced financial data extraction result"""
    revenue_entries: List[Dict[str, Any]]
    confidence_score: float
    page_references: List[int]
    table_locations: List[Dict[str, Any]]
    context_snippets: List[str]
    extraction_method: str = "azure_document_intelligence"

class AzureDocumentIntelligenceService:
    """
    Enhanced document processing using Azure Document Intelligence
    Specialized for financial document analysis with table extraction
    """
    
    def __init__(self, endpoint: str, api_key: str):
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
        self.logger = logging.getLogger(__name__)
        
    async def extract_financial_data(self, 
                                   document_path: str,
                                   expected_revenue_range: Optional[Tuple[float, float]] = None) -> FinancialExtraction:
        """
        Extract financial data using Azure Document Intelligence with enhanced table processing
        """
        try:
            # Use prebuilt-document model for enhanced table and key-value extraction
            with open(document_path, "rb") as document:
                poller = self.client.begin_analyze_document(
                    model_id="prebuilt-document",
                    analyze_request=document,
                    features=["tables", "keyValuePairs", "languages"]
                )
                
            result = poller.result()
            
            # Enhanced financial extraction
            financial_data = await self._process_document_result(
                result, expected_revenue_range
            )
            
            return financial_data
            
        except Exception as e:
            self.logger.error(f"Azure Document Intelligence extraction failed: {e}")
            raise
    
    async def _process_document_result(self, 
                                     result: Any,
                                     expected_range: Optional[Tuple[float, float]]) -> FinancialExtraction:
        """Process Azure DI result with financial focus"""
        
        revenue_entries = []
        page_references = []
        table_locations = []
        context_snippets = []
        
        # Extract from tables (primary source for financial data)
        if result.tables:
            table_revenue = await self._extract_from_tables(result.tables)
            revenue_entries.extend(table_revenue['entries'])
            table_locations.extend(table_revenue['locations'])
            page_references.extend(table_revenue['pages'])
        
        # Extract from key-value pairs
        if result.key_value_pairs:
            kv_revenue = await self._extract_from_key_value_pairs(result.key_value_pairs)
            revenue_entries.extend(kv_revenue['entries'])
            page_references.extend(kv_revenue['pages'])
        
        # Extract from paragraphs with enhanced context
        if result.paragraphs:
            paragraph_revenue = await self._extract_from_paragraphs(
                result.paragraphs, expected_range
            )
            revenue_entries.extend(paragraph_revenue['entries'])
            context_snippets.extend(paragraph_revenue['contexts'])
            page_references.extend(paragraph_revenue['pages'])
        
        # Calculate confidence based on multiple extraction sources
        confidence = self._calculate_enhanced_confidence(
            revenue_entries, table_locations, expected_range
        )
        
        return FinancialExtraction(
            revenue_entries=revenue_entries,
            confidence_score=confidence,
            page_references=sorted(list(set(page_references))),
            table_locations=table_locations,
            context_snippets=context_snippets
        )
    
    async def _extract_from_tables(self, tables: List[Any]) -> Dict[str, List]:
        """Enhanced table extraction for financial statements"""
        entries = []
        locations = []
        pages = []
        
        for table_idx, table in enumerate(tables):
            # Look for revenue-related headers
            revenue_headers = self._identify_revenue_columns(table)
            
            if revenue_headers:
                for row_idx, row in enumerate(table.cells):
                    for cell in row:
                        if self._is_revenue_cell(cell, revenue_headers):
                            amount = self._extract_amount_from_cell(cell.content)
                            if amount:
                                entries.append({
                                    'amount': amount,
                                    'source': f'table_{table_idx}_row_{row_idx}',
                                    'cell_content': cell.content,
                                    'confidence': 0.9,  # High confidence for table data
                                    'extraction_method': 'table_cell'
                                })
                                
                                locations.append({
                                    'table_id': table_idx,
                                    'row': row_idx,
                                    'bounding_box': cell.bounding_regions[0].polygon if cell.bounding_regions else None
                                })
                                
                                if cell.bounding_regions:
                                    pages.append(cell.bounding_regions[0].page_number)
        
        return {'entries': entries, 'locations': locations, 'pages': pages}
    
    async def _extract_from_paragraphs(self, 
                                     paragraphs: List[Any],
                                     expected_range: Optional[Tuple[float, float]]) -> Dict[str, List]:
        """Extract revenue from paragraphs with enhanced context awareness"""
        entries = []
        contexts = []
        pages = []
        
        # Enhanced financial patterns for Azure DI processed text
        financial_patterns = [
            # Billions with enhanced context detection
            r'(?i)(?:total\s+|group\s+|consolidated\s+)?(?:revenue|sales|turnover).*?£?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*(?:billion|bn)',
            r'(?i)revenue.*?£\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*(?:billion|bn)',
            
            # Millions with scale validation
            r'(?i)(?:revenue|sales|turnover).*?£?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)\s*(?:million|mn|m)\b',
            
            # Raw numbers with strong revenue context
            r'(?i)(?:total\s+revenue|group\s+revenue|net\s+revenue).*?£\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)',
            
            # Table-like patterns in text
            r'(?i)revenue\s*[:\-]\s*£?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?)',
        ]
        
        for paragraph in paragraphs:
            text = paragraph.content
            
            # Apply enhanced patterns
            for pattern in financial_patterns:
                import re
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    amount_str = match.group(1)
                    amount = self._parse_financial_amount(amount_str, text)
                    
                    if amount and self._validate_amount_range(amount, expected_range):
                        entries.append({
                            'amount': amount,
                            'source': 'paragraph_enhanced_pattern',
                            'raw_text': text,
                            'matched_pattern': pattern,
                            'confidence': self._calculate_pattern_confidence(pattern, text),
                            'extraction_method': 'enhanced_paragraph'
                        })
                        
                        contexts.append(text[:200] + "..." if len(text) > 200 else text)
                        
                        if paragraph.bounding_regions:
                            pages.append(paragraph.bounding_regions[0].page_number)
        
        return {'entries': entries, 'contexts': contexts, 'pages': pages}
    
    def _identify_revenue_columns(self, table: Any) -> List[str]:
        """Identify columns containing revenue data"""
        revenue_keywords = [
            'revenue', 'sales', 'turnover', 'income', 'total revenue',
            'group revenue', 'consolidated revenue', 'net sales'
        ]
        
        revenue_columns = []
        
        # Check header row for revenue indicators
        if table.cells:
            header_row = table.cells[0] if table.cells else []
            for cell in header_row:
                cell_text = cell.content.lower().strip()
                for keyword in revenue_keywords:
                    if keyword in cell_text:
                        revenue_columns.append(cell_text)
                        break
        
        return revenue_columns
    
    def _parse_financial_amount(self, amount_str: str, context: str) -> Optional[float]:
        """Enhanced financial amount parsing with context validation"""
        import re
        
        # Clean the amount string
        clean_amount = re.sub(r'[£$€,\s]', '', amount_str)
        
        try:
            base_amount = float(clean_amount)
            
            # Determine scale from context
            context_lower = context.lower()
            
            if any(word in context_lower for word in ['billion', 'bn']):
                return base_amount * 1_000_000_000
            elif any(word in context_lower for word in ['million', 'mn', 'm']):
                return base_amount * 1_000_000
            elif any(word in context_lower for word in ['thousand', 'k']):
                return base_amount * 1_000
            else:
                # For raw numbers, apply intelligent scaling
                if base_amount > 1_000_000:
                    return base_amount  # Already in appropriate scale
                elif 50 <= base_amount <= 100:  # Likely billions (e.g., 69.9 -> 69.9B)
                    return base_amount * 1_000_000_000
                elif 1_000 <= base_amount <= 100_000:  # Likely millions
                    return base_amount * 1_000_000
                else:
                    return base_amount
                    
        except (ValueError, TypeError):
            return None
    
    def _validate_amount_range(self, 
                             amount: float, 
                             expected_range: Optional[Tuple[float, float]]) -> bool:
        """Validate extracted amount against expected range"""
        if not expected_range:
            return True
            
        min_expected, max_expected = expected_range
        
        # Allow 50% variance from expected range
        lower_bound = min_expected * 0.5
        upper_bound = max_expected * 1.5
        
        return lower_bound <= amount <= upper_bound
    
    def _calculate_enhanced_confidence(self, 
                                     revenue_entries: List[Dict],
                                     table_locations: List[Dict],
                                     expected_range: Optional[Tuple[float, float]]) -> float:
        """Calculate confidence score based on multiple factors"""
        if not revenue_entries:
            return 0.0
        
        confidence_factors = []
        
        # Factor 1: Multiple source validation
        extraction_methods = set(entry.get('extraction_method', '') for entry in revenue_entries)
        multi_source_bonus = min(len(extraction_methods) * 0.2, 0.6)
        confidence_factors.append(multi_source_bonus)
        
        # Factor 2: Table presence (higher confidence)
        table_bonus = 0.3 if table_locations else 0.0
        confidence_factors.append(table_bonus)
        
        # Factor 3: Expected range validation
        if expected_range:
            amounts = [entry['amount'] for entry in revenue_entries]
            range_validated = sum(1 for amount in amounts 
                                if self._validate_amount_range(amount, expected_range))
            range_factor = (range_validated / len(amounts)) * 0.4
            confidence_factors.append(range_factor)
        
        # Factor 4: Pattern strength
        pattern_confidences = [entry.get('confidence', 0.5) for entry in revenue_entries]
        avg_pattern_confidence = sum(pattern_confidences) / len(pattern_confidences)
        confidence_factors.append(avg_pattern_confidence * 0.4)
        
        return min(sum(confidence_factors), 1.0)

# Integration with existing RAG system
class EnhancedDocumentProcessor:
    """
    Integration layer between Azure Document Intelligence and existing RAG system
    """
    
    def __init__(self, azure_di_service: AzureDocumentIntelligenceService):
        self.azure_di = azure_di_service
        self.logger = logging.getLogger(__name__)
    
    async def process_document_with_intelligence(self, 
                                               document_path: str,
                                               company_name: str,
                                               public_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Enhanced document processing combining Azure DI with public data validation
        """
        
        # Determine expected revenue range from public data
        expected_range = None
        if public_data and 'revenue' in public_data:
            expected_revenue = public_data['revenue']
            # Allow 30% variance for document vs public data differences
            expected_range = (expected_revenue * 0.7, expected_revenue * 1.3)
        
        # Process with Azure Document Intelligence
        financial_extraction = await self.azure_di.extract_financial_data(
            document_path, expected_range
        )
        
        # Enhanced result formatting
        return {
            'revenue_candidates': financial_extraction.revenue_entries,
            'confidence_score': financial_extraction.confidence_score,
            'page_references': financial_extraction.page_references,
            'table_locations': financial_extraction.table_locations,
            'context_snippets': financial_extraction.context_snippets,
            'extraction_method': 'azure_document_intelligence_enhanced',
            'public_data_validation': public_data is not None,
            'expected_range_used': expected_range is not None
        }