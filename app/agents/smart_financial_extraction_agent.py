"""
Smart Financial Extraction Agent - Tiered approach for extracting financial data from documents.
"""
import sys
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import time
from enum import Enum

# Add the parent directory to sys.path to import modules

from ..agents.base_agent import BaseAgent, AgentResult
from ..utils.config_manager import config
from ..utils.logger import logger

class ExtractionMethod(Enum):
    """Extraction method types."""
    REGEX_PATTERN = "regex_pattern"
    SECTION_VECTORIZATION = "section_vectorization" 
    FULL_RAG = "full_rag"
    FAILED = "failed"

@dataclass
class FinancialData:
    """Extracted financial data structure."""
    revenue: Optional[float]
    profit_before_tax: Optional[float]
    profit_after_tax: Optional[float]
    total_assets: Optional[float]
    current_assets: Optional[float]
    total_liabilities: Optional[float]
    net_worth: Optional[float]
    period_start: Optional[str]
    period_end: Optional[str]

@dataclass
class ExtractionResult:
    """Result of financial data extraction."""
    financial_data: FinancialData
    extraction_method: ExtractionMethod
    confidence: float
    processing_time: float
    raw_text_matched: Optional[str]
    error_message: Optional[str]

class SmartFinancialExtractionAgent(BaseAgent):
    """Agent that uses tiered approach to extract financial data from documents."""
    
    def __init__(self):
        super().__init__("SmartFinancialExtractionAgent")
        
        # Configuration
        self.tier1_timeout = config.get("processing.tier1_timeout", 5)  # seconds
        self.tier2_timeout = config.get("processing.tier2_timeout", 20)  # seconds
        self.tier3_timeout = config.get("processing.tier3_timeout", 60)  # seconds
        
        # Regex patterns for financial data extraction
        self.financial_patterns = self._initialize_financial_patterns()
        
        # Initialize PDF processing
        self._initialize_pdf_processor()
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process financial data extraction from documents.
        
        Args:
            data: Dictionary containing:
                - documents: List of DownloadedDocument objects
                - extraction_targets: List of financial metrics to extract
                - fallback_enabled: Whether to use tiered fallback
        
        Returns:
            AgentResult with extracted financial data
        """
        try:
            self.log_activity("Starting smart financial extraction")
            
            documents = data.get("documents", [])
            extraction_targets = data.get("extraction_targets", ["revenue", "profit_before_tax"])
            fallback_enabled = data.get("fallback_enabled", True)
            
            if not documents:
                return self.create_result(
                    success=False,
                    error_message="No documents provided for extraction"
                )
            
            extraction_results = []
            
            for document in documents:
                try:
                    result = self._extract_financial_data_smart(document, extraction_targets, fallback_enabled)
                    extraction_results.append(result)
                except Exception as e:
                    self.log_activity(f"Error extracting from document: {str(e)}", "ERROR")
                    extraction_results.append(ExtractionResult(
                        financial_data=FinancialData(None, None, None, None, None, None, None, None, None),
                        extraction_method=ExtractionMethod.FAILED,
                        confidence=0.0,
                        processing_time=0.0,
                        raw_text_matched=None,
                        error_message=str(e)
                    ))
            
            # Calculate summary statistics
            successful_extractions = [r for r in extraction_results if r.extraction_method != ExtractionMethod.FAILED]
            avg_processing_time = sum(r.processing_time for r in successful_extractions) / len(successful_extractions) if successful_extractions else 0
            
            self.log_activity(f"Completed extraction for {len(documents)} documents")
            
            return self.create_result(
                success=True,
                data={
                    "extraction_results": extraction_results,
                    "summary": {
                        "total_documents": len(documents),
                        "successful_extractions": len(successful_extractions),
                        "average_processing_time": avg_processing_time,
                        "method_distribution": self._calculate_method_distribution(extraction_results)
                    }
                },
                confidence=0.8,
                extraction_count=len(successful_extractions)
            )
            
        except Exception as e:
            error_msg = f"Smart financial extraction failed: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
    
    def extract_revenue_smart(self, document_content: bytes) -> ExtractionResult:
        """
        Extract revenue using smart tiered approach.
        
        Args:
            document_content: PDF document content as bytes
        
        Returns:
            ExtractionResult with revenue data
        """
        return self._extract_financial_data_smart(
            document_content, 
            extraction_targets=["revenue"],
            fallback_enabled=True
        )
    
    def _extract_financial_data_smart(self, document, extraction_targets: List[str], fallback_enabled: bool) -> ExtractionResult:
        """Smart extraction using tiered approach."""
        start_time = time.time()
        
        # Extract text from PDF
        if hasattr(document, 'content'):
            text_content = self._extract_text_from_pdf(document.content)
        else:
            text_content = self._extract_text_from_pdf(document)
        
        if not text_content:
            return ExtractionResult(
                financial_data=FinancialData(None, None, None, None, None, None, None, None, None),
                extraction_method=ExtractionMethod.FAILED,
                confidence=0.0,
                processing_time=time.time() - start_time,
                raw_text_matched=None,
                error_message="Could not extract text from PDF"
            )
        
        # Tier 1: Fast regex pattern matching
        tier1_result = self._tier1_regex_extraction(text_content, extraction_targets)
        processing_time = time.time() - start_time
        
        if tier1_result and tier1_result.confidence >= 0.8:
            tier1_result.processing_time = processing_time
            self.log_activity(f"Tier 1 extraction successful (confidence: {tier1_result.confidence:.2f})")
            return tier1_result
        
        if not fallback_enabled:
            return tier1_result or ExtractionResult(
                financial_data=FinancialData(None, None, None, None, None, None, None, None, None),
                extraction_method=ExtractionMethod.FAILED,
                confidence=0.0,
                processing_time=processing_time,
                raw_text_matched=None,
                error_message="Tier 1 extraction failed and fallback disabled"
            )
        
        # Tier 2: Section-specific processing
        if processing_time < self.tier2_timeout:
            tier2_result = self._tier2_section_extraction(text_content, extraction_targets)
            processing_time = time.time() - start_time
            
            if tier2_result and tier2_result.confidence >= 0.7:
                tier2_result.processing_time = processing_time
                self.log_activity(f"Tier 2 extraction successful (confidence: {tier2_result.confidence:.2f})")
                return tier2_result
        
        # Tier 3: Full RAG analysis (placeholder for now)
        if processing_time < self.tier3_timeout:
            tier3_result = self._tier3_rag_extraction(text_content, extraction_targets)
            tier3_result.processing_time = time.time() - start_time
            self.log_activity(f"Tier 3 extraction completed (confidence: {tier3_result.confidence:.2f})")
            return tier3_result
        
        # Return best available result
        best_result = tier1_result or ExtractionResult(
            financial_data=FinancialData(None, None, None, None, None, None, None, None, None),
            extraction_method=ExtractionMethod.FAILED,
            confidence=0.0,
            processing_time=time.time() - start_time,
            raw_text_matched=None,
            error_message="All extraction tiers failed or timed out"
        )
        
        return best_result
    
    def _tier1_regex_extraction(self, text_content: str, extraction_targets: List[str]) -> Optional[ExtractionResult]:
        """Tier 1: Fast regex pattern matching."""
        try:
            financial_data = FinancialData(None, None, None, None, None, None, None, None, None)
            matched_patterns = []
            confidence_scores = []
            
            # Clean text for better matching
            clean_text = self._clean_financial_text(text_content)
            
            for target in extraction_targets:
                if target == "revenue":
                    revenue_match = self._extract_revenue_regex(clean_text)
                    if revenue_match:
                        financial_data.revenue = revenue_match["value"]
                        matched_patterns.append(revenue_match["matched_text"])
                        confidence_scores.append(revenue_match["confidence"])
                
                elif target == "profit_before_tax":
                    profit_match = self._extract_profit_regex(clean_text)
                    if profit_match:
                        financial_data.profit_before_tax = profit_match["value"]
                        matched_patterns.append(profit_match["matched_text"])
                        confidence_scores.append(profit_match["confidence"])
            
            # Extract period information
            period_match = self._extract_period_regex(clean_text)
            if period_match:
                financial_data.period_start = period_match.get("start")
                financial_data.period_end = period_match.get("end")
            
            # Calculate overall confidence
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            if overall_confidence > 0.5:
                return ExtractionResult(
                    financial_data=financial_data,
                    extraction_method=ExtractionMethod.REGEX_PATTERN,
                    confidence=overall_confidence,
                    processing_time=0.0,  # Will be set by caller
                    raw_text_matched="; ".join(matched_patterns),
                    error_message=None
                )
            
            return None
            
        except Exception as e:
            self.log_activity(f"Tier 1 extraction error: {str(e)}", "ERROR")
            return None
    
    def _tier2_section_extraction(self, text_content: str, extraction_targets: List[str]) -> Optional[ExtractionResult]:
        """Tier 2: Section-specific intelligent extraction."""
        try:
            # Find financial statement sections
            financial_sections = self._identify_financial_sections(text_content)
            
            financial_data = FinancialData(None, None, None, None, None, None, None, None, None)
            confidence_scores = []
            matched_text_parts = []
            
            for section_name, section_text in financial_sections.items():
                if "revenue" in extraction_targets:
                    revenue_value = self._extract_from_financial_section(section_text, "revenue")
                    if revenue_value:
                        financial_data.revenue = revenue_value["value"]
                        confidence_scores.append(revenue_value["confidence"])
                        matched_text_parts.append(f"{section_name}: {revenue_value['matched_text']}")
                
                if "profit_before_tax" in extraction_targets:
                    profit_value = self._extract_from_financial_section(section_text, "profit_before_tax")
                    if profit_value:
                        financial_data.profit_before_tax = profit_value["value"]
                        confidence_scores.append(profit_value["confidence"])
                        matched_text_parts.append(f"{section_name}: {profit_value['matched_text']}")
            
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            if overall_confidence > 0.6:
                return ExtractionResult(
                    financial_data=financial_data,
                    extraction_method=ExtractionMethod.SECTION_VECTORIZATION,
                    confidence=overall_confidence,
                    processing_time=0.0,
                    raw_text_matched="; ".join(matched_text_parts),
                    error_message=None
                )
            
            return None
            
        except Exception as e:
            self.log_activity(f"Tier 2 extraction error: {str(e)}", "ERROR")
            return None
    
    def _tier3_rag_extraction(self, text_content: str, extraction_targets: List[str]) -> ExtractionResult:
        """Tier 3: Full RAG analysis (placeholder implementation)."""
        try:
            # This is a placeholder for full RAG implementation
            # In production, this would use vector databases and LLM queries
            
            self.log_activity("Tier 3 RAG extraction - using enhanced pattern matching")
            
            # Enhanced extraction with context awareness
            financial_data = FinancialData(None, None, None, None, None, None, None, None, None)
            
            # Use more sophisticated analysis
            if "revenue" in extraction_targets:
                revenue_context = self._find_revenue_with_context(text_content)
                if revenue_context:
                    financial_data.revenue = revenue_context["value"]
            
            # Placeholder confidence based on data availability
            confidence = 0.6 if financial_data.revenue else 0.3
            
            return ExtractionResult(
                financial_data=financial_data,
                extraction_method=ExtractionMethod.FULL_RAG,
                confidence=confidence,
                processing_time=0.0,
                raw_text_matched="RAG-based extraction",
                error_message=None if confidence > 0.5 else "RAG extraction yielded low confidence results"
            )
            
        except Exception as e:
            self.log_activity(f"Tier 3 extraction error: {str(e)}", "ERROR")
            return ExtractionResult(
                financial_data=FinancialData(None, None, None, None, None, None, None, None, None),
                extraction_method=ExtractionMethod.FAILED,
                confidence=0.0,
                processing_time=0.0,
                raw_text_matched=None,
                error_message=str(e)
            )
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content."""
        try:
            # Placeholder for PDF text extraction
            # In production, would use PyPDF2, pdfplumber, or similar
            self.log_activity("PDF text extraction - using mock implementation")
            
            # Mock text content for demonstration
            return """
            PROFIT AND LOSS ACCOUNT
            For the year ended 31 December 2023
            
            Turnover                                    £850,000
            Cost of sales                              (£420,000)
            Gross profit                                £430,000
            
            Administrative expenses                     (£280,000)
            Operating profit                            £150,000
            
            Interest receivable                         £5,000
            Profit before taxation                      £155,000
            Tax on profit                              (£31,000)
            Profit after taxation                       £124,000
            
            BALANCE SHEET
            As at 31 December 2023
            
            Fixed assets                                £200,000
            Current assets                              £180,000
            Total assets                                £380,000
            """
            
        except Exception as e:
            self.log_activity(f"PDF text extraction error: {str(e)}", "ERROR")
            return ""
    
    def _clean_financial_text(self, text: str) -> str:
        """Clean and normalize financial text for better pattern matching."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize currency symbols
        text = re.sub(r'[£$€]', '£', text)
        
        # Normalize number formats
        text = re.sub(r'\(([£$€]?\d+[,\d]*)\)', r'-\1', text)  # Convert (£1,000) to -£1,000
        
        return text
    
    def _extract_revenue_regex(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract revenue using regex patterns."""
        patterns = self.financial_patterns["revenue"]
        
        for pattern_info in patterns:
            matches = re.finditer(pattern_info["pattern"], text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    # Extract numeric value
                    value_str = match.group(1) if match.groups() else match.group(0)
                    value = self._parse_financial_value(value_str)
                    
                    if value and value > 1000:  # Reasonable revenue threshold
                        return {
                            "value": value,
                            "confidence": pattern_info["confidence"],
                            "matched_text": match.group(0)
                        }
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_profit_regex(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract profit using regex patterns."""
        patterns = self.financial_patterns["profit_before_tax"]
        
        for pattern_info in patterns:
            matches = re.finditer(pattern_info["pattern"], text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    value_str = match.group(1) if match.groups() else match.group(0)
                    value = self._parse_financial_value(value_str)
                    
                    if value is not None:  # Profit can be negative
                        return {
                            "value": value,
                            "confidence": pattern_info["confidence"],
                            "matched_text": match.group(0)
                        }
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_period_regex(self, text: str) -> Optional[Dict[str, Optional[str]]]:
        """Extract accounting period from text."""
        period_patterns = [
            r"for the year ended\s+(\d{1,2}[\/\-\s]\w+[\/\-\s]\d{4})",
            r"year ended\s+(\d{1,2}[\/\-\s]\w+[\/\-\s]\d{4})",
            r"period from\s+(\d{1,2}[\/\-\s]\w+[\/\-\s]\d{4})\s+to\s+(\d{1,2}[\/\-\s]\w+[\/\-\s]\d{4})"
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.groups() and len(match.groups()) == 2:
                    return {"start": match.group(1), "end": match.group(2)}
                elif match.groups() and len(match.groups()) == 1:
                    return {"start": None, "end": match.group(1)}
        
        return None
    
    def _parse_financial_value(self, value_str: str) -> Optional[float]:
        """Parse financial value from string."""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[£$€,\s]', '', value_str)
            
            # Handle negative values in parentheses
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            
            # Handle 'k' and 'm' suffixes
            if cleaned.lower().endswith('k'):
                return float(cleaned[:-1]) * 1000
            elif cleaned.lower().endswith('m'):
                return float(cleaned[:-1]) * 1000000
            
            return float(cleaned)
            
        except (ValueError, AttributeError):
            return None
    
    def _identify_financial_sections(self, text: str) -> Dict[str, str]:
        """Identify different financial statement sections."""
        sections = {}
        
        # Common section headers
        section_patterns = {
            "profit_loss": r"(profit\s+and\s+loss|income\s+statement).*?(?=balance\s+sheet|notes\s+to|directors|$)",
            "balance_sheet": r"(balance\s+sheet).*?(?=notes\s+to|directors|cash\s+flow|$)",
            "cash_flow": r"(cash\s+flow).*?(?=notes\s+to|directors|$)"
        }
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section_name] = match.group(0)
        
        return sections
    
    def _extract_from_financial_section(self, section_text: str, target: str) -> Optional[Dict[str, Any]]:
        """Extract specific financial metric from a section."""
        if target == "revenue":
            return self._extract_revenue_regex(section_text)
        elif target == "profit_before_tax":
            return self._extract_profit_regex(section_text)
        
        return None
    
    def _find_revenue_with_context(self, text: str) -> Optional[Dict[str, Any]]:
        """Find revenue with surrounding context for better accuracy."""
        # Enhanced pattern matching with context
        context_patterns = [
            r"turnover[\s\w]*?£([\d,]+)",
            r"revenue[\s\w]*?£([\d,]+)",
            r"sales[\s\w]*?£([\d,]+)"
        ]
        
        for pattern in context_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = self._parse_financial_value(match.group(1))
                if value and value > 1000:
                    return {"value": value, "context": match.group(0)}
        
        return None
    
    def _calculate_method_distribution(self, results: List[ExtractionResult]) -> Dict[str, int]:
        """Calculate distribution of extraction methods used."""
        distribution = {}
        for result in results:
            method = result.extraction_method.value
            distribution[method] = distribution.get(method, 0) + 1
        return distribution
    
    def _initialize_financial_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize regex patterns for financial data extraction."""
        return {
            "revenue": [
                {
                    "pattern": r"turnover\s*£([\d,]+)",
                    "confidence": 0.9,
                    "description": "Turnover line item"
                },
                {
                    "pattern": r"revenue\s*£([\d,]+)",
                    "confidence": 0.9,
                    "description": "Revenue line item"
                },
                {
                    "pattern": r"sales\s*£([\d,]+)",
                    "confidence": 0.8,
                    "description": "Sales line item"
                },
                {
                    "pattern": r"total\s+income\s*£([\d,]+)",
                    "confidence": 0.8,
                    "description": "Total income"
                }
            ],
            "profit_before_tax": [
                {
                    "pattern": r"profit\s+before\s+tax(?:ation)?\s*[£\(\-]?([\d,]+)",
                    "confidence": 0.95,
                    "description": "Profit before taxation"
                },
                {
                    "pattern": r"operating\s+profit\s*[£\(\-]?([\d,]+)",
                    "confidence": 0.85,
                    "description": "Operating profit"
                },
                {
                    "pattern": r"profit\s+before\s+interest\s+and\s+tax\s*[£\(\-]?([\d,]+)",
                    "confidence": 0.9,
                    "description": "EBIT"
                }
            ]
        }
    
    def _initialize_pdf_processor(self) -> None:
        """Initialize PDF processing capabilities."""
        try:
            # Check for PDF processing libraries
            try:
                # Try importing PyPDF2
                import PyPDF2  # type: ignore
                self.pdf_library = "PyPDF2"
            except ImportError:
                try:
                    # Try importing pdfplumber
                    import pdfplumber  # type: ignore
                    self.pdf_library = "pdfplumber"
                except ImportError:
                    self.pdf_library = "mock"
                    self.log_activity("No PDF processing library found, using mock implementation", "WARNING")
        except Exception as e:
            self.log_activity(f"Error initializing PDF processor: {str(e)}", "ERROR")
            self.pdf_library = "mock"
