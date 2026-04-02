"""
Streamlined document processing for agentic revenue extraction.
Uses native vector database operations with Azure-optimized PDF extraction.
"""

import logging
import tempfile
import os
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ...database.vector_connection import VectorDatabaseConnection
from .data_models import DocumentChunk, SemanticQuery, RAGResult, DocumentProcessingResult
from ...utils.logger import get_logger
from ...utils.config_manager import config

logger = get_logger(__name__)


class AgenticDocumentProcessor:
    """
    Streamlined document processor for agentic revenue extraction.
    Azure Document Intelligence is the primary extraction method (table-aware, premium).
    PyMuPDF is the fallback when Azure DI is unavailable.
    """
    
    def __init__(self):
        """
        Initialize the agentic document processor with Azure optimization.
        """
        self.logger = get_logger(self.__class__.__name__)
        
        # Use separate optimized vector database with sqlite-vec extension
        # This provides 10x+ faster vector similarity search compared to JSON storage
        # Phase 3: Force legacy schema to match revenue extractor
        self.vector_db = VectorDatabaseConnection()  # Uses default vector_database.db with native vector ops
        
        # Use normalized schema where data actually exists (documents_v2, document_chunks_v2)
        # This ensures document processing and revenue search use same database tables  
        self.vector_db.use_normalized_schema = True
        
        # Text processing parameters
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        # Azure Document Intelligence configuration
        self.azure_doc_intelligence_endpoint = config.get("azure.document_intelligence.endpoint", "")
        self.azure_doc_intelligence_key = config.get("azure.document_intelligence.key", "")
        self.azure_doc_intelligence_api_version = config.get("azure.document_intelligence.api_version", "2024-11-30")
        
        # Initialize embedding model
        self.embedding_model = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize smart embedding service (local-first for speed)."""
        try:
            # Use smart embedding service for speed (local-first with OpenAI fallback)
            from app_modules.services.embedding.smart_embedding_service import get_smart_embedding_service
            self.embedding_model = get_smart_embedding_service()
            
            if self.embedding_model is None:
                raise Exception("Failed to load smart embedding service")
                
            self.logger.info("✅ Embedding model initialized: Smart hybrid service (local-first, 768D) - high quality processing")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize embedding model: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_content: bytes, progress_callback=None) -> Tuple[str, str, float]:
        """
        2-tier PDF text extraction using Azure Document Intelligence as primary method.
        Azure DI is Tier 1 (premium — preserves table structure critical for financial data).
        PyMuPDF is Tier 2 fallback (free, fast, but loses table structure).
        
        Args:
            pdf_content: PDF file as bytes
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (extracted_text, method_used, cost_incurred)
        """
        if progress_callback:
            progress_callback("Analyzing PDF document...")

        page_count = self._get_pdf_page_count(pdf_content)
        self._last_page_count = page_count  # expose for callers

        # Tier 1: Azure Document Intelligence (premium — table-aware, structure-preserving)
        if self.azure_doc_intelligence_endpoint and self.azure_doc_intelligence_key:
            if progress_callback:
                progress_callback("Extracting with Azure Document Intelligence (table-aware)...")
            text, cost = self._extract_with_azure_doc_intelligence(pdf_content)
            if text and len(text.strip()) > 100:
                self.logger.info(f"✅ Azure Document Intelligence: {len(text):,} chars from {page_count} pages (cost: ${cost:.4f})")
                return text, "azure_document_intelligence", cost
            self.logger.warning("⚠️  Azure Document Intelligence returned insufficient text — falling back to PyMuPDF")
        else:
            self.logger.warning("⚠️  Azure Document Intelligence not configured — using PyMuPDF fallback")

        # Tier 2: PyMuPDF (free fallback — fast but loses table structure)
        if progress_callback:
            progress_callback("Falling back to PyMuPDF text extraction...")
        text, success = self._extract_with_pymupdf(pdf_content)
        if success:
            self.logger.info(f"✅ PyMuPDF fallback: {len(text):,} chars from {page_count} pages")
            return text, "pymupdf", 0.0

        self.logger.warning("❌ All PDF extraction tiers failed")
        return "", "failed", 0.0
    
    def _extract_with_pymupdf(self, pdf_content: bytes) -> Tuple[str, bool]:
        """Extract text using PyMuPDF with enhanced page sampling for financial documents."""
        try:
            import fitz  # PyMuPDF
            
            # Open PDF from bytes
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = len(pdf_doc)
            
            # Process ALL pages for complete document vectorization
            sample_pages = list(range(page_count))
            self.logger.info(f"� Full PyMuPDF processing: all {page_count} pages (no limits for complete vectorization)")
            
            text_content = ""
            for page_num in sample_pages:
                if page_num < page_count:  # Safety check
                    page = pdf_doc.load_page(page_num)
                    text_content += page.get_text()
            
            pdf_doc.close()
            
            # Check if we got meaningful text (not just whitespace/artifacts)
            if len(text_content.strip()) > 100:  # Minimum meaningful content
                self.logger.info(f"✅ Enhanced PyMuPDF extracted {len(text_content)} characters from {len(sample_pages)} pages")
                return text_content, True
            else:
                self.logger.info("⚠️  PyMuPDF: Insufficient text content, likely image-based PDF")
                return "", False
                
        except ImportError:
            self.logger.warning("📦 PyMuPDF not available, install with: pip install PyMuPDF")
            return "", False
        except Exception as e:
            self.logger.info(f"⚠️  PyMuPDF failed: {e}")
            return "", False
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> Tuple[str, bool]:
        """Extract text using pdfplumber (good for tables and forms)."""
        try:
            import pdfplumber
            import io
            
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                text_content = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
            
            if len(text_content.strip()) > 100:
                self.logger.info(f"✅ pdfplumber extracted {len(text_content)} characters")
                return text_content, True
            else:
                self.logger.info("⚠️  pdfplumber: Insufficient text content")
                return "", False
                
        except ImportError:
            self.logger.warning("📦 pdfplumber not available, install with: pip install pdfplumber")
            return "", False
        except Exception as e:
            self.logger.info(f"⚠️  pdfplumber failed: {e}")
            return "", False
    
    def _get_pdf_page_count(self, pdf_content: bytes) -> int:
        """Get PDF page count for processing optimization."""
        try:
            import fitz
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_count = len(pdf_doc)
            pdf_doc.close()
            return page_count
        except Exception as e:
            self.logger.warning(f"Could not determine page count: {e}")
            return 1  # Assume single page if count fails
    
    def _extract_with_smart_sampling(self, pdf_content: bytes, page_count: int) -> Tuple[str, bool]:
        """
        GAAP/IFRS-aware smart sampling for financial documents.
        Uses accounting standards knowledge to locate key financial statement pages.
        """
        try:
            import fitz
            import pytesseract
            from PIL import Image
            import re
            
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            text_content = ""
            
            # Phase 1: GAAP/IFRS Financial Statement Detection
            financial_pages = self._detect_financial_statement_pages(pdf_doc, page_count)
            
            # Phase 2: Strategic sampling based on accounting standards
            sample_pages = self._get_gaap_aware_sample_pages(page_count, financial_pages)
            
            self.logger.info(f"📊 GAAP-aware sampling: processing {len(sample_pages)}/{page_count} pages (detected {len(financial_pages)} financial pages)")
            
            for page_num in sample_pages:
                page = pdf_doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                
                # Enhanced OCR for financial data with GAAP terminology
                page_text = pytesseract.image_to_string(
                    img, 
                    config='--psm 6 -c tessedit_char_whitelist=0123456789.,£$€¥ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ():-'
                )
                text_content += f"\n--- Page {page_num + 1} (Financial: {'Yes' if page_num in financial_pages else 'No'}) ---\n" + page_text
            
            pdf_doc.close()
            
            if len(text_content.strip()) > 200:
                return text_content, True
            else:
                self.logger.warning("GAAP-aware sampling: insufficient content extracted")
                return "", False
                
        except ImportError:
            self.logger.warning("📦 OCR libraries not available - install: pip install pytesseract pillow")
            return "", False
        except Exception as e:
            self.logger.info(f"⚠️  GAAP-aware sampling failed: {e}")
            return "", False

    def _detect_financial_statement_pages(self, pdf_doc, page_count: int) -> List[int]:
        """
        Detect pages containing financial statements using GAAP/IFRS standard terminology.
        Returns list of page numbers likely to contain revenue/financial data.
        """
        import re
        
        financial_pages = []
        
        # Enhanced GAAP/IFRS Financial Statement Keywords (comprehensive coverage)
        financial_keywords = [
            # Core Financial Statements (GAAP/IFRS Universal)
            r'consolidated\s+statements?\s+of\s+(income|operations|earnings|profit|comprehensive\s+income)',
            r'consolidated\s+(income|profit)\s+statements?',
            r'profit\s+and\s+loss\s+(account|statement)',
            r'statement\s+of\s+comprehensive\s+income',
            r'consolidated\s+statements?\s+of\s+financial\s+position',
            r'statement\s+of\s+changes\s+in\s+equity',
            r'consolidated\s+financial\s+statements',
            
            # IFRS Specific Statements
            r'consolidated\s+statement\s+of\s+profit\s+or\s+loss',
            r'other\s+comprehensive\s+income',
            r'statement\s+of\s+cash\s+flows',
            
            # Revenue Recognition Standards (ASC 606 / IFRS 15)
            r'revenue\s+from\s+contracts?\s+with\s+customers?',
            r'asc\s*606|ifrs\s*15',
            r'performance\s+obligations?',
            r'contract\s+(assets?|liabilities)',
            r'net\s+(sales|revenue)',
            r'total\s+(revenue|sales|turnover)',
            r'operating\s+(revenue|income)',
            r'continuing\s+operations',
            r'discontinued\s+operations',
            
            # UK Companies House / FRS / IFRS Terminology
            r'group\s+(profit|revenue|sales|turnover)',
            r'profit\s+for\s+the\s+year',
            r'profit\s+attributable\s+to',
            r'administrative\s+expenses',
            r'distribution\s+costs',
            r'finance\s+costs',
            r'exceptional\s+items',
            r'cost\s+of\s+(sales|goods\s+sold)',
            r'turnover',
            
            # Accounting Standards References
            r'ifrs|international\s+financial\s+reporting\s+standards',
            r'gaap|generally\s+accepted\s+accounting\s+principles',
            r'frs\s*\d+|financial\s+reporting\s+standard',
            r'companies\s+act\s+2006',
            r'basis\s+of\s+preparation',
            r'accounting\s+policies',
            
            # Financial Metrics and KPIs
            r'gross\s+(profit|margin)',
            r'operating\s+(profit|margin|income)',
            r'ebitda|ebit',
            r'earnings\s+per\s+share',
            r'basic\s+eps|diluted\s+eps',
            r'return\s+on\s+(equity|assets|capital)',
            
            # Monetary Patterns (Multi-currency)
            r'[\£\$€¥₹]\s*\d{1,3}(?:,\d{3})+(?:\.\d{2})?\s*(?:million|billion|thousand|m|bn|k)?',
            r'\d{1,3}(?:,\d{3})+\s*(?:million|billion|thousand|m|bn|k)',
            r'thousands\s+of\s+[\£\$€¥₹]',
            r'in\s+millions\s+of\s+[\£\$€¥₹]',
            
            # Segment and Geographic Reporting
            r'segment\s+(revenue|profit|results)',
            r'segmental\s+analysis',
            r'geographic\s+(revenue|breakdown)',
            r'business\s+segments?',
            
            # Quarterly and Annual Reporting
            r'year\s+ended\s+\d+',
            r'three\s+months\s+ended',
            r'quarter\s+ended',
            r'interim\s+report',
            r'annual\s+report',
            r'financial\s+year\s+\d+',
            
            # Audit and Governance Terms
            r'independent\s+auditors?\s+report',
            r'directors?\s+report',
            r'management\s+discussion\s+and\s+analysis',
            r'notes\s+to\s+(?:the\s+)?(?:consolidated\s+)?financial\s+statements',
            r'critical\s+accounting\s+estimates',
            r'significant\s+accounting\s+judgments'
        ]
        
        # Sample pages strategically to detect financial content
        sample_size = min(50, max(25, page_count // 5))  # 25-50 pages for comprehensive coverage
        
        # Focus sampling on typical financial statement locations
        strategic_pages = []
        
        # First 10 pages (executive summary, key figures)
        strategic_pages.extend(range(min(10, page_count)))
        
        # Pages 15-50 (often where consolidated statements begin)
        if page_count > 15:
            strategic_pages.extend(range(15, min(50, page_count)))
        
        # Pages around 25% and 33% marks (common financial statement locations)
        if page_count > 40:
            quarter_mark = page_count // 4
            third_mark = page_count // 3
            strategic_pages.extend(range(quarter_mark, min(quarter_mark + 10, page_count)))
            strategic_pages.extend(range(third_mark, min(third_mark + 10, page_count)))
        
        # Remove duplicates and limit sampling
        strategic_pages = sorted(list(set(strategic_pages)))[:sample_size]
        
        try:
            for page_num in strategic_pages:
                page = pdf_doc.load_page(page_num)
                page_text = page.get_text()
                
                # Score page based on financial keyword density
                financial_score = 0
                for pattern in financial_keywords:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    financial_score += len(matches)
                
                # High-value indicators
                if any(keyword in page_text.lower() for keyword in [
                    'consolidated income', 'revenue from contracts', 'net sales', 'total revenue',
                    'profit and loss', 'statement of comprehensive income', 'turnover'
                ]):
                    financial_score += 10
                
                # Numeric financial data indicators
                if re.search(r'[£$€]\s*\d{1,3}(,\d{3})+', page_text):
                    financial_score += 5
                
                # Mark as financial page if score meets threshold
                if financial_score >= 3:
                    financial_pages.append(page_num)
                    self.logger.info(f"📊 Detected financial page {page_num + 1} (score: {financial_score})")
        
        except Exception as e:
            self.logger.warning(f"Financial page detection error: {e}")
        
        return financial_pages

    def _get_gaap_aware_sample_pages(self, page_count: int, financial_pages: List[int]) -> List[int]:
        """
        Generate optimal page sampling strategy based on GAAP/IFRS knowledge and detected financial pages.
        """
        sample_pages = []
        
        # Strategy 1: If we detected financial pages, prioritize those
        if financial_pages:
            sample_pages.extend(financial_pages)  # ALL financial pages
            
            # Add context pages around ALL financial pages
            for fp in financial_pages:
                if fp > 0:
                    sample_pages.append(fp - 1)  # Page before financial statement
                if fp < page_count - 1:
                    sample_pages.append(fp + 1)  # Page after financial statement
        
        # Strategy 2: Standard GAAP structure sampling
        # Annual reports typically follow: Cover -> Summary -> MD&A -> Financial Statements -> Notes
        
        # Cover and executive summary (pages 1-3)
        sample_pages.extend(range(min(3, page_count)))
        
        # Key financial highlights (often pages 4-8)
        if page_count > 8:
            sample_pages.extend(range(4, min(8, page_count)))
        
        # Enhanced financial statement section (pages 15-80 for comprehensive coverage)
        if page_count > 15:
            fin_start = 15
            fin_end = min(80, page_count)
            # Sample every 2nd page in financial section for better coverage
            sample_pages.extend(range(fin_start, fin_end, 2))
        
        # Notes to financial statements (usually last 25% of document)
        if page_count > 40:
            notes_start = int(page_count * 0.75)
            sample_pages.extend(range(notes_start, page_count, 5))  # Every 5th page in notes
        
        # Remove duplicates, sort, and limit to reasonable number
        sample_pages = sorted(list(set(sample_pages)))
        sample_pages = [p for p in sample_pages if p < page_count]
        
        # Return all sampled pages without any limits (for legacy compatibility)
        return sample_pages
    
    def _extract_with_tesseract_optimized(self, pdf_content: bytes, progress_callback=None, total_pages=None) -> Tuple[str, bool]:
        """
        ENHANCED Tesseract OCR for financial documents with quality optimization.
        Processes all pages with advanced financial pattern recognition and text cleaning.
        """
        try:
            import fitz
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter
            import re
            import time
            
            pdf_doc = fitz.open(stream=pdf_content, filetype="pdf")
            text_content = ""
            quality_score = 0.0
            total_doc_pages = len(pdf_doc)
            
            # Batch processing for better performance and progress tracking
            batch_size = 25 if total_doc_pages > 100 else 10
            start_time = time.time()
            
            # Memory-optimized processing for production real-time use
            import gc  # Garbage collection for memory management
            
            for page_num in range(total_doc_pages):
                # Progress updates every 10 pages or at batch boundaries
                if progress_callback and (page_num % 10 == 0 or page_num % batch_size == 0):
                    elapsed = time.time() - start_time
                    pages_per_minute = (page_num + 1) / (elapsed / 60) if elapsed > 0 else 0
                    remaining_pages = total_doc_pages - page_num - 1
                    est_remaining_minutes = remaining_pages / pages_per_minute if pages_per_minute > 0 else 0
                    
                    progress_callback(f"OCR processing page {page_num + 1}/{total_doc_pages} "
                                    f"({pages_per_minute:.1f} pages/min, ~{est_remaining_minutes:.1f} min remaining)")
                
                # Memory-optimized page processing
                page = None
                pix = None
                img = None
                
                try:
                    page = pdf_doc.load_page(page_num)
                    
                    # Use lower resolution for production memory efficiency (1.5x instead of 2x)
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    
                    # Clear pixmap immediately to free memory
                    pix = None
                    
                    # Image enhancement for OCR quality
                    enhanced_img = self._enhance_image_for_ocr(img)
                    
                    # Clear original image to save memory
                    img = None
                    
                    # Multi-pass OCR with financial-optimized configs
                    page_text = self._multi_pass_ocr(enhanced_img, page_num)
                    
                    # Clear enhanced image immediately
                    enhanced_img = None
                    
                    if page_text:
                        # Clean and validate text quality
                        cleaned_text = self._clean_financial_text(page_text)
                        if cleaned_text:
                            text_content += f"\n--- Page {page_num + 1} (Text Embedding) ---\n{cleaned_text}\n"
                            quality_score += self._assess_text_quality(cleaned_text)
                
                finally:
                    # Ensure memory cleanup after each page
                    if page:
                        page = None
                    if pix:
                        pix = None
                    if img:
                        img = None
                    
                    # Force garbage collection every 20 pages for memory management
                    if page_num % 20 == 0:
                        gc.collect()
            
            # Final progress update
            if progress_callback:
                elapsed = time.time() - start_time
                progress_callback(f"OCR completed: {total_doc_pages} pages in {elapsed:.1f}s ({total_doc_pages/(elapsed/60):.1f} pages/min)")
            
            pdf_doc.close()
            
            # Calculate average quality
            total_pages = len(pdf_doc)
            avg_quality = quality_score / total_pages if total_pages > 0 else 0.0
            
            # Enhanced quality validation
            if len(text_content.strip()) > 100 and avg_quality > 0.3:
                self.logger.info(f"✅ Text Embedding: {len(text_content)} chars, quality={avg_quality:.2f}")
                return text_content, True
            else:
                self.logger.warning(f"⚠️  Text Embedding: insufficient quality ({avg_quality:.2f}) or content")
                return "", False
                
        except ImportError:
            self.logger.warning("📦 Tesseract not available - install: pip install pytesseract pillow")
            return "", False
        except Exception as e:
            self.logger.info(f"⚠️  Enhanced Tesseract OCR failed: {e}")
            return "", False
    
    def _enhance_image_for_ocr(self, img):
        """Memory-optimized image enhancement for OCR on financial documents."""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            
            # Memory-optimized processing with immediate cleanup
            original_img = img
            
            # Convert to grayscale for better OCR (more memory efficient)
            if img.mode != 'L':
                img = img.convert('L')
                # Clear original if converted
                if img != original_img:
                    original_img = None
            
            # In-place enhancement operations for memory efficiency
            # Enhance contrast for financial documents
            enhancer = ImageEnhance.Contrast(img)
            enhanced_img = enhancer.enhance(1.3)  # Reduced enhancement to save processing
            img = None  # Clear intermediate
            
            # Apply minimal denoising only (skip sharpness to save memory)
            final_img = enhanced_img.filter(ImageFilter.MedianFilter(size=1))
            enhanced_img = None  # Clear intermediate
            
            return final_img
            
        except Exception as e:
            self.logger.debug(f"Image enhancement failed: {e}")
            return img
    
    def _multi_pass_ocr(self, img, page_num: int) -> str:
        """Multi-pass OCR with different configs optimized for financial data."""
        try:
            import pytesseract
            
            # Pass 1: Financial document optimized (numbers, currency, text)
            config1 = '--psm 6 -c tessedit_char_whitelist=0123456789.,£$€¥ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ():-'
            text1 = pytesseract.image_to_string(img, config=config1)
            
            # Pass 2: Table-focused for financial statements
            config2 = '--psm 4 -c preserve_interword_spaces=1'
            text2 = pytesseract.image_to_string(img, config=config2)
            
            # Pass 3: General with financial character bias
            config3 = '--psm 3 -c tessedit_char_blacklist=@#%^&*+=~`|\\[]{}"\''
            text3 = pytesseract.image_to_string(img, config=config3)
            
            # Combine results - prioritize by financial content
            best_text = self._select_best_ocr_result([text1, text2, text3])
            return best_text
            
        except Exception as e:
            self.logger.debug(f"Multi-pass OCR failed: {e}")
            return ""
    
    def _select_best_ocr_result(self, texts: list) -> str:
        """Select best OCR result based on financial content quality."""
        scored_texts = []
        
        for text in texts:
            if not text or len(text.strip()) < 10:
                continue
                
            score = 0.0
            # Score based on financial indicators
            financial_terms = ['revenue', 'turnover', 'sales', 'profit', 'income', '£', '$', '%']
            for term in financial_terms:
                score += text.lower().count(term) * 0.1
            
            # Score based on numerical content
            import re
            numbers = re.findall(r'\d+', text)
            score += len(numbers) * 0.05
            
            # Score based on text length (more is usually better)
            score += len(text) * 0.001
            
            scored_texts.append((score, text))
        
        if scored_texts:
            scored_texts.sort(reverse=True)
            return scored_texts[0][1]
        return ""
    
    def _clean_financial_text(self, text: str) -> str:
        """Clean and normalize financial document text for better embeddings."""
        if not text:
            return ""
        
        try:
            import re
            
            # PHASE 1: Remove OCR artifacts that hurt similarity (CONSERVATIVE - keep financial data)
            # Only remove obvious navigation artifacts, preserve financial content
            text = re.sub(r'Image\s+removed', '', text, flags=re.IGNORECASE)  # Remove image placeholders
            text = re.sub(r'www\s+[a-zA-Z0-9\s]+com\s+\d+', '', text)  # Remove website artifacts only if followed by numbers
            
            # PHASE 2: Clean currency and number formatting
            # Normalize currency symbols with proper spacing
            text = re.sub(r'£\s*(\d)', r'£\1', text)  # £ 3,754 -> £3,754
            text = re.sub(r'\$\s*(\d)', r'$\1', text)  # $ 100 -> $100
            
            # Fix common OCR errors in financial contexts
            ocr_fixes = {
                'O': '0',  # Letter O -> Zero in numbers
                'l': '1',  # Lowercase l -> One in numbers  
                'S': '5',  # S -> 5 in currency amounts
                'I': '1',  # Capital I -> One in numbers
                'o': '0',  # lowercase o -> zero in numbers
            }
            
            # Apply OCR fixes in numeric contexts only
            for old, new in ocr_fixes.items():
                # Fix around currency symbols
                text = re.sub(f'([£$€¥])\\s*{old}', f'\\1{new}', text)
                # Fix within number sequences
                text = re.sub(f'{old}(\\d)', f'{new}\\1', text)
                text = re.sub(f'(\\d){old}', f'\\1{new}', text)
                text = re.sub(f'(\\d),\\s*{old}', f'\\1,{new}', text)  # Fix in comma-separated numbers
            
            # PHASE 3: Standardize financial terminology
            # Ensure consistent spacing around key financial terms
            financial_terms = [
                'revenue', 'turnover', 'sales', 'income', 'profit', 'loss',
                'total', 'gross', 'net', 'consolidated', 'annual', 'million', 'billion'
            ]
            for term in financial_terms:
                text = re.sub(f'\\b{term}\\b', f' {term} ', text, flags=re.IGNORECASE)
            
            # PHASE 4: Preserve financial formatting but clean excessive noise
            # Keep table structure for financial statements, only remove excessive decorations
            text = re.sub(r'[-_=]{5,}', ' ', text)  # Remove very long horizontal lines only
            text = re.sub(r'[|]{3,}', ' ', text)  # Remove multiple table borders but keep single separators
            
            # PHASE 5: Final cleanup
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text.strip())
            
            # Remove empty parentheses and brackets
            text = re.sub(r'\(\s*\)', '', text)
            text = re.sub(r'\[\s*\]', '', text)
            
            return text
            
        except Exception as e:
            self.logger.debug(f"Enhanced text cleaning failed: {e}")
            return text.strip()
    
    def _assess_text_quality(self, text: str) -> float:
        """Assess text quality for embedding suitability (0.0 to 1.0)."""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        try:
            import re
            
            score = 0.0
            
            # Check for financial content
            financial_indicators = ['revenue', 'turnover', 'sales', 'profit', 'income', '£', '$', '%']
            for indicator in financial_indicators:
                if indicator.lower() in text.lower():
                    score += 0.1
            
            # Check for numerical content
            numbers = re.findall(r'\d+', text)
            score += min(len(numbers) * 0.05, 0.3)
            
            # Check for sentence structure
            sentences = text.split('.')
            if len(sentences) > 1:
                score += 0.2
            
            # Check character diversity (not just repeated characters)
            unique_chars = len(set(text.lower()))
            score += min(unique_chars * 0.01, 0.2)
            
            # Penalty for excessive special characters (OCR errors)
            special_chars = len(re.findall(r'[^a-zA-Z0-9\s£$€¥.,():-]', text))
            score -= min(special_chars * 0.02, 0.3)
            
            return min(max(score, 0.0), 1.0)
            
        except Exception as e:
            self.logger.debug(f"Quality assessment failed: {e}")
            return 0.5



    def _extract_with_azure_doc_intelligence(self, pdf_content: bytes) -> Tuple[str, float]:
        """Extract text using Azure Document Intelligence (paid, reliable for image PDFs)."""
        try:
            # Calculate cost (approximately $0.0015 per page)
            estimated_pages = max(1, len(pdf_content) // 50000)
            estimated_cost = estimated_pages * 0.0015

            endpoint = self.azure_doc_intelligence_endpoint.rstrip('/')
            api_version = self.azure_doc_intelligence_api_version

            # Azure Document Intelligence REST API (2023-09-30+)
            # Endpoint format: https://<resource>.cognitiveservices.azure.com/
            # REST path: /documentintelligence/documentModels/prebuilt-read:analyze
            analyze_url = (
                f"{endpoint}/documentintelligence/documentModels/prebuilt-read:analyze"
                f"?api-version={api_version}"
            )

            headers = {
                'Ocp-Apim-Subscription-Key': self.azure_doc_intelligence_key,
                'Content-Type': 'application/pdf'
            }

            self.logger.info(f"📤 Submitting to Azure Document Intelligence ({estimated_pages} est. pages, ${estimated_cost:.4f} est. cost)")
            response = requests.post(analyze_url, headers=headers, data=pdf_content, timeout=60)

            if response.status_code == 202:
                operation_location = response.headers.get('Operation-Location')
                if not operation_location:
                    self.logger.error("❌ Azure DI: No Operation-Location header in response")
                    return "", 0.0

                import time
                poll_headers = {'Ocp-Apim-Subscription-Key': self.azure_doc_intelligence_key}
                for attempt in range(60):   # up to 2 minutes
                    time.sleep(2)
                    result_response = requests.get(operation_location, headers=poll_headers, timeout=30)

                    if result_response.status_code != 200:
                        self.logger.warning(f"⚠️ Azure DI poll returned {result_response.status_code}")
                        continue

                    result_data = result_response.json()
                    status = result_data.get('status')

                    if status == 'succeeded':
                        text_content = ""
                        pages = result_data.get('analyzeResult', {}).get('pages', [])
                        for page in pages:
                            for line in page.get('lines', []):
                                text_content += line.get('content', '') + "\n"
                            text_content += "\n"   # blank line between pages

                        if text_content.strip():
                            self.logger.info(
                                f"✅ Azure Document Intelligence: {len(pages)} pages, "
                                f"{len(text_content):,} chars (cost: ${estimated_cost:.4f})"
                            )
                            return text_content.strip(), estimated_cost

                        self.logger.warning("⚠️ Azure DI succeeded but returned empty text")
                        return "", estimated_cost

                    elif status == 'failed':
                        err = result_data.get('error', {}).get('message', 'unknown')
                        self.logger.error(f"❌ Azure Document Intelligence failed: {err}")
                        return "", 0.0

                    # still running — keep polling
                    self.logger.debug(f"Azure DI status: {status} (attempt {attempt+1}/60)")

                self.logger.warning("⏰ Azure Document Intelligence timed out after 120s")
                return "", estimated_cost

            else:
                self.logger.error(
                    f"❌ Azure Document Intelligence API error: {response.status_code} — {response.text[:300]}"
                )
                return "", 0.0

        except Exception as e:
            self.logger.error(f"❌ Azure Document Intelligence failed: {e}")
            return "", 0.0
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> Tuple[str, bool]:
        """Extract text using PyPDF2 (basic fallback)."""
        try:
            import PyPDF2
            import io
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text_content = ""
            
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            if len(text_content.strip()) > 50:
                self.logger.info(f"✅ PyPDF2 extracted {len(text_content)} characters")
                return text_content, True
            else:
                return "", False
                
        except Exception as e:
            self.logger.info(f"⚠️  PyPDF2 failed: {e}")
            return "", False
            raise
        
    def _initialize_embeddings(self):
        """Initialize OpenAI text-embedding-3-small for cost-effective embedding generation."""
        try:
            from app_modules.services.embedding.openai_embedding_service import get_openai_embedding_service
            
            # Use OpenAI's cheapest embedding model for cost efficiency
            self.embedding_model = get_openai_embedding_service()
            self.embedding_dimension = 768  # All-mpnet-base-v2 dimensions (configured for 768D)
            self.logger.info(f"✅ Embedding model initialized: all-mpnet-base-v2 (768D)")
            
        except ImportError:
            self.logger.error("OpenAI embedding service not available!")
            raise ImportError("openai_embedding_service required for document processing")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            raise
    
    def process_document_with_metadata(self, document_id: str, company_name: str, 
                                     company_number: str, company_id: Optional[int] = None,
                                     unique_id: Optional[str] = None, 
                                     transaction_id: Optional[str] = None) -> DocumentProcessingResult:
        """
        Process a Companies House document with enhanced metadata for revenue extraction.
        Uses smart change detection - only processes if transaction_id changed.
        
        Args:
            document_id: Companies House document ID
            company_name: Company name
            company_number: Company registration number for revenue filtering
            company_id: Database company ID
            unique_id: Unique filing ID from Companies House
            transaction_id: Transaction ID for change detection
            
        Returns:
            DocumentProcessingResult with processing status and metadata
        """
        start_time = datetime.now()
        
        try:
            # Smart change detection: Check if transaction_id already processed with REAL content
            if transaction_id and self.vector_db.document_exists_by_transaction(company_number, transaction_id):
                try:
                    with self.vector_db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT COUNT(*), MIN(dc.content) FROM document_chunks_v2 dc
                            JOIN documents_v2 d ON dc.document_id = d.document_id
                            WHERE d.company_number = ? AND d.transaction_id = ?
                        """, (company_number, transaction_id))
                        row = cursor.fetchone()
                        actual_chunk_count = row[0] if row else 0
                        sample_content = row[1] or "" if row else ""
                except Exception as e:
                    self.logger.warning(f"Failed to get cached chunk count: {e}")
                    actual_chunk_count = 0
                    sample_content = ""

                # Reject cached chunks that are error-report placeholders from a previous failed run
                is_garbage = (
                    sample_content.startswith("DOCUMENT PROCESSING COMPLETED")
                    or sample_content.startswith("EXTRACTION ATTEMPTS")
                    or "❌ PyPDF2 Standard: Failed" in sample_content
                    or "❌ Local OCR:" in sample_content
                )
                if actual_chunk_count > 0 and not is_garbage:
                    self.logger.info(f"📋 Document {document_id} already processed (transaction_id: {transaction_id}), using cached data with {actual_chunk_count} chunks")
                    return DocumentProcessingResult(
                        success=True,
                        document_id=document_id,
                        chunk_count=actual_chunk_count,
                        embedding_count=actual_chunk_count,
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        extracted_data={'status': 'cached', 'transaction_id': transaction_id, 'chunk_count': actual_chunk_count}
                    )
                elif is_garbage:
                    self.logger.warning(f"⚠️ Cached chunks for {document_id} are error-report placeholders — re-processing document.")
                    # Delete stale garbage so fresh chunks can be stored
                    try:
                        with self.vector_db.get_connection() as conn:
                            conn.execute("""
                                DELETE FROM document_chunks_v2 WHERE document_id IN (
                                    SELECT document_id FROM documents_v2
                                    WHERE company_number = ? AND transaction_id = ?
                                )
                            """, (company_number, transaction_id))
                            conn.execute("""
                                DELETE FROM documents_v2 WHERE company_number = ? AND transaction_id = ?
                            """, (company_number, transaction_id))
                            conn.commit()
                    except Exception as e:
                        self.logger.warning(f"Failed to delete garbage chunks: {e}")
            
            # Download document from Companies House (only if not cached)
            document_content = self._download_document(document_id)
            if not document_content:
                return DocumentProcessingResult(
                    success=False,
                    document_id=document_id,
                    error_message="Failed to download document from Companies House"
                )
            
            # Extract text with OCR support
            text_content = self._extract_text_from_pdf(document_content)
            if not text_content or len(text_content.strip()) < 100:
                return DocumentProcessingResult(
                    success=False,
                    document_id=document_id,
                    error_message="Insufficient text extracted from PDF - may be image-based"
                )
            
            # Create chunks with enhanced metadata
            chunks = self._create_document_chunks(text_content, document_id, company_name)
            if not chunks:
                return DocumentProcessingResult(
                    success=False,
                    document_id=document_id,
                    error_message="No chunks created from extracted text"
                )
            
            # Store with enhanced metadata for revenue filtering
            chunk_data = []
            for chunk in chunks:
                # Preserve ALL rich metadata from chunk creation for Q&A functionality
                enhanced_metadata = chunk.metadata.copy()  # Start with rich metadata from chunking
                enhanced_metadata.update({
                    # Add processing-level metadata
                    'company_registration_number': company_number,
                    'unique_id': unique_id,
                    'section_type': chunk.section_type,
                    'page_number': chunk.page_number,
                    'chunk_index': chunk.chunk_index,
                    # Preserve Q&A-critical positioning data
                    'start_char': enhanced_metadata.get('start_char'),
                    'end_char': enhanced_metadata.get('end_char'),  
                    'start_page': enhanced_metadata.get('start_page'),
                    'end_page': enhanced_metadata.get('end_page'),
                    'paragraph_number': enhanced_metadata.get('paragraph_number'),
                    'section_title': enhanced_metadata.get('section_title'),
                    'document_title': enhanced_metadata.get('document_title'),
                    'filing_date': enhanced_metadata.get('filing_date'),
                    'filing_type': enhanced_metadata.get('filing_type'),
                    # Context for Q&A referencing
                    'preceding_text': enhanced_metadata.get('preceding_text'),
                    'following_text': enhanced_metadata.get('following_text')
                })
                
                # Get embedding - encode() returns List[List[float]], extract first element
                embedding_result = self.embedding_model.encode(chunk.text)
                if isinstance(embedding_result, list) and len(embedding_result) > 0:
                    # Extract the first (and only) embedding from the list
                    single_embedding = embedding_result[0]
                    if hasattr(single_embedding, 'tolist'):
                        embedding_vector = single_embedding.tolist()
                    else:
                        embedding_vector = list(single_embedding)
                else:
                    self.logger.error(f"❌ Invalid embedding result for chunk: {type(embedding_result)}")
                    continue
                
                chunk_dict = {
                    'text': chunk.text,
                    'embedding': embedding_vector,
                    'metadata': enhanced_metadata  # Now preserves ALL rich metadata for Q&A
                }
                chunk_data.append(chunk_dict)
            
            # Use TRUE UPSERT to prevent ALL duplication - INSERT OR REPLACE strategy
            upsert_result = self.vector_db.upsert_document_vectors(
                document_id=document_id,
                chunks=chunk_data,
                company_number=company_number or enhanced_metadata.get('company_number', ''),
                company_name=company_name or enhanced_metadata.get('company_name', ''),
                transaction_id=transaction_id or enhanced_metadata.get('transaction_id', ''),
                content_type="financial_document",
                force_update=True  # Always update when processing new PDFs from Companies House
            )
            stored_count = upsert_result.get('upserted_count', 0)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return DocumentProcessingResult(
                success=True,
                document_id=document_id,
                chunk_count=len(chunks),
                page_count=getattr(self, '_last_page_count', 0),
                embedding_count=stored_count,
                processing_time=processing_time,
                extracted_data={'text_preview': text_content[:500] if text_content else None}
            )
            
        except Exception as e:
            self.logger.error(f"Enhanced document processing failed for {document_id}: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return DocumentProcessingResult(
                success=False,
                document_id=document_id,
                error_message=str(e),
                processing_time=processing_time
            )
    
    def _download_document(self, document_id: str) -> Optional[bytes]:
        """Download document from Companies House Document API with enhanced logging."""
        self.logger.info(f"📥 DOWNLOADING document {document_id}...")
        download_start = datetime.now()
        
        try:
            from ...agents.document_download_agent import DocumentDownloadAgent
            
            self.logger.info(f"   🔗 Initializing document download agent...")
            agent = DocumentDownloadAgent()
            
            self.logger.info(f"   📡 Requesting document from Companies House API...")
            downloaded_doc = agent.download_by_document_id(document_id, "Unknown")
            
            download_time = (datetime.now() - download_start).total_seconds()
            
            if downloaded_doc and downloaded_doc.content:
                self.logger.info(f"✅ Document download successful in {download_time:.2f}s")
                self.logger.info(f"   📄 Document ID: {document_id}")
                self.logger.info(f"   📦 Content size: {len(downloaded_doc.content):,} bytes")
                self.logger.info(f"   🏷️  Content type: {getattr(downloaded_doc, 'content_type', 'unknown')}")
                return downloaded_doc.content
            else:
                self.logger.error(f"❌ Document download failed in {download_time:.2f}s")
                self.logger.error(f"   📄 Document ID: {document_id}")
                self.logger.error(f"   💥 Reason: Empty or null content returned from API")
                return None
                
        except Exception as e:
            download_time = (datetime.now() - download_start).total_seconds()
            self.logger.error(f"❌ Document download failed in {download_time:.2f}s")
            self.logger.error(f"   📄 Document ID: {document_id}")
            self.logger.error(f"   💥 Error: {str(e)}")
            
            # Log HTTP-specific errors if available
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                self.logger.error(f"   🌐 HTTP Status: {e.response.status_code}")
                if hasattr(e.response, 'text'):
                    self.logger.error(f"   📝 HTTP Response: {e.response.text[:200]}...")
            
            import traceback
            self.logger.error(f"   🔍 Download error traceback: {traceback.format_exc()}")
            return None
    
    def process_document_content(self, document_content: bytes, document_id: str, 
                               company_name: str, company_number: Optional[str] = None, 
                               transaction_id: Optional[str] = None) -> DocumentProcessingResult:
        """
        Process document content and store in vector database with enhanced logging.
        
        Args:
            document_content: Raw PDF content
            document_id: Unique document identifier
            company_name: Company name for metadata
            company_number: Company registration number
            transaction_id: Filing transaction identifier
            
        Returns:
            DocumentProcessingResult with processing status
        """
        start_time = datetime.now()
        
        # Enhanced logging: Start processing
        self.logger.info(f"🚀 STARTING document processing for {document_id}")
        self.logger.info(f"   📋 Company: {company_name} ({company_number})")
        self.logger.info(f"   📄 Document size: {len(document_content):,} bytes")
        self.logger.info(f"   🔄 Transaction ID: {transaction_id}")
        
        try:
            # Step 1: Extract text content
            self.logger.info(f"📖 STEP 1: Extracting text from PDF...")
            extraction_start = datetime.now()
            text_content = self._extract_text_from_pdf(document_content)
            extraction_time = (datetime.now() - extraction_start).total_seconds()
            
            if not text_content:
                self.logger.error(f"❌ TEXT EXTRACTION FAILED for {document_id}")
                return DocumentProcessingResult(
                    success=False,
                    document_id=document_id,
                    error_message="Failed to extract text from PDF"
                )
            
            self.logger.info(f"✅ Text extraction completed in {extraction_time:.2f}s")
            self.logger.info(f"   📝 Extracted text length: {len(text_content):,} characters")
            
            # Step 2: Create text chunks
            self.logger.info(f"🧩 STEP 2: Creating document chunks...")
            chunking_start = datetime.now()
            chunks = self._create_document_chunks(text_content, document_id, company_name)
            chunking_time = (datetime.now() - chunking_start).total_seconds()
            
            self.logger.info(f"✅ Chunking completed in {chunking_time:.2f}s")
            self.logger.info(f"   🧩 Created {len(chunks)} chunks from document {document_id}")
            
            if len(chunks) == 0:
                self.logger.error(f"❌ CHUNKING FAILED: No chunks created for {document_id}")
                return DocumentProcessingResult(
                    success=False,
                    document_id=document_id,
                    error_message="No text chunks could be created from document"
                )
            
            # Step 3: Generate embeddings and store with metadata
            self.logger.info(f"🔮 STEP 3: Generating embeddings and storing in vector database...")
            vectorization_start = datetime.now()
            embedding_count = self._store_chunks_with_embeddings_enhanced(
                document_id, chunks, company_name, company_number, transaction_id
            )
            vectorization_time = (datetime.now() - vectorization_start).total_seconds()
            
            if embedding_count == 0:
                self.logger.error(f"❌ VECTOR STORAGE FAILED: No embeddings stored for {document_id}")
                return DocumentProcessingResult(
                    success=False,
                    document_id=document_id,
                    error_message="Failed to store embeddings in vector database"
                )
            
            self.logger.info(f"✅ Vector storage completed in {vectorization_time:.2f}s")
            self.logger.info(f"   💾 Stored {embedding_count}/{len(chunks)} embeddings successfully")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Final success summary
            self.logger.info(f"🎉 PROCESSING COMPLETED for {document_id}")
            self.logger.info(f"   ⏱️  Total time: {processing_time:.2f}s")
            self.logger.info(f"   📊 Success rate: {embedding_count}/{len(chunks)} chunks ({100*embedding_count/len(chunks):.1f}%)")
            
            return DocumentProcessingResult(
                success=True,
                document_id=document_id,
                chunk_count=len(chunks),
                embedding_count=embedding_count,
                processing_time=processing_time,
                confidence=0.9 if embedding_count > 0 else 0.0
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"❌ DOCUMENT PROCESSING FAILED for {document_id}")
            self.logger.error(f"   💥 Error: {str(e)}")
            self.logger.error(f"   ⏱️  Failed after: {processing_time:.2f}s")
            import traceback
            self.logger.error(f"   🔍 Stack trace: {traceback.format_exc()}")
            
            return DocumentProcessingResult(
                success=False,
                document_id=document_id,
                processing_time=processing_time,
                error_message=str(e)
            )
    
    def query_document(self, query: SemanticQuery, document_id: Optional[str] = None) -> RAGResult:
        """
        Query processed documents using semantic search.
        
        Args:
            query: Semantic query for document search
            document_id: Optional filter by specific document
            
        Returns:
            RAGResult with relevant chunks and extracted data
        """
        try:
            # Generate query embedding - encode() returns List[List[float]], extract first element
            embedding_result = self.embedding_model.encode(query.query_text)
            if isinstance(embedding_result, list) and len(embedding_result) > 0:
                single_embedding = embedding_result[0]
                if hasattr(single_embedding, 'tolist'):
                    query_embedding = single_embedding.tolist()
                else:
                    query_embedding = list(single_embedding)
            else:
                self.logger.error(f"❌ Invalid query embedding result: {type(embedding_result)}")
                return RAGResult(chunks=[], extracted_data={})
            
            # Search for similar chunks - NO LIMIT for comprehensive analysis
            similar_chunks = self.vector_db.similarity_search(
                query_embedding=query_embedding,
                document_id=document_id,
                limit=50  # Increased from 5 to allow comprehensive chunk retrieval
            )
            
            # Apply similarity threshold filtering
            similar_chunks = [chunk for chunk in similar_chunks if chunk.get('similarity_score', 0) >= 0.7]
            
            # Convert to DocumentChunk objects
            relevant_chunks = []
            for result in similar_chunks:
                metadata = result.get('metadata', {})
                chunk = DocumentChunk(
                    text=result['content'],
                    page_number=metadata.get('page_number'),
                    section_type=metadata.get('section_type', 'content'),
                    chunk_index=result['chunk_id'],
                    metadata=metadata
                )
                relevant_chunks.append(chunk)
            
            # Extract financial data from chunks
            extracted_data, confidence = self._extract_financial_data(query, relevant_chunks)
            
            return RAGResult(
                query=query,
                relevant_chunks=relevant_chunks,
                extracted_data=extracted_data,
                confidence=confidence,
                reasoning=f"Found {len(relevant_chunks)} relevant chunks",
                sources=[f"Chunk {chunk.chunk_index}" for chunk in relevant_chunks]
            )
            
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            return RAGResult(
                query=query,
                relevant_chunks=[],
                confidence=0.0,
                reasoning=f"Query failed: {str(e)}"
            )
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content using enhanced PyMuPDF with full document processing.
        
        Args:
            pdf_content: Raw PDF bytes
            
        Returns:
            Extracted text content from enhanced PyMuPDF or OCR fallback
        """
        # Use our enhanced PyMuPDF method that processes ALL pages
        text_content, success = self._extract_with_pymupdf(pdf_content)
        
        if success and text_content.strip():
            self.logger.info(f"✅ Enhanced PyMuPDF extraction successful: {len(text_content)} characters")
            return text_content.strip()
        
        # Fallback to OCR if PyMuPDF fails
        self.logger.warning("⚠️ Enhanced PyMuPDF extraction failed - attempting OCR fallback")
        return self._extract_text_with_ocr(pdf_content)
    
    def _extract_text_with_ocr(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF using OCR with multiple fallback strategies.
        
        Args:
            pdf_content: Raw PDF bytes
            
        Returns:
            Extracted text from OCR or fallback message
        """
        # Strategy 1: Azure Document Intelligence (best quality, handles scanned PDFs)
        if self.azure_doc_intelligence_endpoint and self.azure_doc_intelligence_key:
            adi_text, _ = self._extract_with_azure_doc_intelligence(pdf_content)
            if adi_text and len(adi_text.strip()) > 100:
                self.logger.info(f"✅ Azure Document Intelligence extracted {len(adi_text):,} chars")
                return adi_text
            self.logger.warning("⚠️ Azure Document Intelligence failed or returned empty — falling back to local OCR")
        else:
            self.logger.info("ℹ️ Azure Document Intelligence not configured — using local OCR")

        # Strategy 2: Try OCR via PyMuPDF render + pytesseract (no poppler needed)
        pymupdf_ocr_result = self._try_pymupdf_ocr(pdf_content)
        if pymupdf_ocr_result['success']:
            return pymupdf_ocr_result['text']

        # Strategy 3: Try local OCR (pytesseract + poppler/pdf2image)
        local_ocr_result = self._try_local_ocr(pdf_content)
        if local_ocr_result['success']:
            return local_ocr_result['text']
        
        # Strategy 4: Try alternative PDF libraries
        alt_result = self._try_alternative_pdf_libraries(pdf_content)
        if alt_result['success']:
            return alt_result['text']
        
        # All strategies failed — log and return empty string.
        # IMPORTANT: do NOT return the fallback message as text — it is an error report,
        # not document content, and would be stored as fake chunks in the vector DB.
        self.logger.error(
            "❌ All PDF text extraction methods failed (Azure Doc Intelligence, PyMuPDF+OCR, local OCR, alternative libraries).\n"
            + self._generate_enhanced_fallback_message({
                'local_ocr_error': pymupdf_ocr_result.get('error') or local_ocr_result.get('error'),
                'alt_library_error': alt_result.get('error')
            })
        )
        return ""

    def _try_pymupdf_ocr(self, pdf_content: bytes) -> Dict[str, Any]:
        """OCR using PyMuPDF to render pages as PIL images + pytesseract.
        
        Advantage over _try_local_ocr: does NOT require pdf2image or poppler.
        PyMuPDF's built-in renderer handles the page-to-image conversion.
        """
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image

            self.logger.info("🔍 Attempting PyMuPDF+OCR extraction (no poppler needed)")
            doc = fitz.open(stream=pdf_content, filetype='pdf')
            extracted_text = ""
            successful_pages = 0

            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    page_text = pytesseract.image_to_string(img, config='--psm 1 --oem 3')
                    if page_text and len(page_text.strip()) > 20:
                        extracted_text += f"\n--- Page {page_num + 1} (OCR) ---\n{page_text.strip()}\n"
                        successful_pages += 1
                except Exception as page_error:
                    self.logger.debug(f"OCR failed for page {page_num + 1}: {page_error}")

            doc.close()

            if extracted_text.strip():
                self.logger.info(f"✅ PyMuPDF+OCR successful: {successful_pages} pages, {len(extracted_text)} chars")
                return {'success': True, 'text': extracted_text.strip()}
            return {'success': False, 'error': 'No readable text found via PyMuPDF+OCR'}

        except ImportError as e:
            return {'success': False, 'error': f'OCR dependencies not available: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'PyMuPDF OCR failed: {e}'}

    def _try_local_ocr(self, pdf_content: bytes) -> Dict[str, Any]:
        """Try local OCR with pytesseract and pdf2image."""
        try:
            import pytesseract
            import pdf2image
            from PIL import Image
            from io import BytesIO
            import tempfile
            import os
            
            self.logger.info("🔍 Attempting local OCR extraction")
            
            # Convert PDF to images
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf.write(pdf_content)
                temp_pdf_path = temp_pdf.name
            
            try:
                # Convert ALL pages to images (no limits for complete vectorization)
                images = pdf2image.convert_from_path(
                    temp_pdf_path, 
                    dpi=200
                )
                
                self.logger.info(f"📄 Converted {len(images)} PDF pages to images")
                
                extracted_text = ""
                successful_pages = 0
                
                for page_num, image in enumerate(images):
                    try:
                        page_text = pytesseract.image_to_string(image, config='--psm 1 --oem 3')
                        
                        if page_text and len(page_text.strip()) > 20:
                            cleaned_text = page_text.strip()
                            extracted_text += f"\n--- Page {page_num + 1} (OCR) ---\n{cleaned_text}\n"
                            successful_pages += 1
                            
                    except Exception as ocr_error:
                        self.logger.debug(f"OCR failed for page {page_num + 1}: {ocr_error}")
                        continue
                
                os.unlink(temp_pdf_path)
                
                if extracted_text.strip():
                    self.logger.info(f"✅ Local OCR successful: {successful_pages} pages, {len(extracted_text)} characters")
                    return {'success': True, 'text': extracted_text.strip()}
                else:
                    return {'success': False, 'error': 'No readable text found via OCR'}
                    
            except Exception as conversion_error:
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
                raise conversion_error
                
        except ImportError as import_error:
            return {'success': False, 'error': f'OCR libraries not available: {import_error}'}
        except Exception as e:
            return {'success': False, 'error': f'Local OCR failed: {e}'}
    
    def _try_alternative_pdf_libraries(self, pdf_content: bytes) -> Dict[str, Any]:
        """Try alternative PDF text extraction libraries."""
        try:
            # Try pdfplumber if available
            try:
                import pdfplumber
                from io import BytesIO
                
                self.logger.info("🔍 Attempting pdfplumber extraction")
                
                with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                    extracted_text = ""
                    successful_pages = 0
                    
                    # Process ALL pages for complete vectorization
                    for i in range(len(pdf.pages)):
                        try:
                            page_text = pdf.pages[i].extract_text()
                            if page_text and len(page_text.strip()) > 20:
                                extracted_text += f"\n--- Page {i + 1} (pdfplumber) ---\n{page_text.strip()}\n"
                                successful_pages += 1
                        except Exception as page_error:
                            self.logger.debug(f"pdfplumber page {i+1} failed: {page_error}")
                            continue
                    
                    if extracted_text.strip():
                        self.logger.info(f"✅ pdfplumber successful: {successful_pages} pages, {len(extracted_text)} characters")
                        return {'success': True, 'text': extracted_text.strip()}
                        
            except ImportError:
                self.logger.debug("pdfplumber not available")
            
            # Try pymupdf (fitz) if available
            try:
                import fitz  # PyMuPDF # type: ignore
                from io import BytesIO
                
                self.logger.info("🔍 Attempting PyMuPDF extraction")
                
                doc = fitz.open(stream=pdf_content, filetype="pdf")
                extracted_text = ""
                successful_pages = 0
                
                # Process ALL pages for complete vectorization
                for page_num in range(len(doc)):
                    try:
                        page = doc[page_num]
                        page_text = page.get_text()
                        if page_text and len(page_text.strip()) > 20:
                            extracted_text += f"\n--- Page {page_num + 1} (PyMuPDF) ---\n{page_text.strip()}\n"
                            successful_pages += 1
                    except Exception as page_error:
                        self.logger.debug(f"PyMuPDF page {page_num+1} failed: {page_error}")
                        continue
                
                doc.close()
                
                if extracted_text.strip():
                    self.logger.info(f"✅ PyMuPDF successful: {successful_pages} pages, {len(extracted_text)} characters")
                    return {'success': True, 'text': extracted_text.strip()}
                    
            except ImportError:
                self.logger.debug("PyMuPDF not available")
                
            return {'success': False, 'error': 'No alternative PDF libraries succeeded'}
            
        except Exception as e:
            return {'success': False, 'error': f'Alternative libraries failed: {e}'}
    
    def _generate_enhanced_fallback_message(self, error_details: Dict[str, Any]) -> str:
        """Generate enhanced fallback message with actionable information."""
        
        message = f"""DOCUMENT PROCESSING COMPLETED - ENHANCED TEXT EXTRACTION SUMMARY

Document Type: Companies House PDF Filing
Processing Status: Document cached and available for alternative processing
Text Extraction: Multiple methods attempted

EXTRACTION ATTEMPTS SUMMARY:
1. ✅ Document Download: Successful ({len(self._get_pdf_size())} bytes)
2. ❌ PyPDF2 Standard: Failed (image-based document detected)
3. ❌ Local OCR: {self._format_error_status(error_details.get('local_ocr_error'))}
4. ❌ Alternative Libraries: {self._format_error_status(error_details.get('alt_library_error'))}

DOCUMENT CHARACTERISTICS:
- Source: Companies House official filing
- Format: PDF (likely scanned document images)
- Text Layer: None or minimal text layer detected
- Content: Financial information in image format

AVAILABLE PROCESSING OPTIONS:

OPTION 1 - CLOUD OCR SERVICES:
• Azure Computer Vision OCR
• Google Cloud Vision API  
• AWS Textract
• Provides high accuracy for financial documents

OPTION 2 - ENHANCED LOCAL OCR SETUP:
• Install Tesseract: brew install tesseract
• Install Poppler: brew install poppler
• Then retry document processing

OPTION 3 - DOCUMENT METADATA PROCESSING:
• Company information: Available from database
• Filing metadata: Date, type, pages available
• Document categorization: Functional

OPTION 4 - MANUAL REVIEW:
• Document cached at: data/downloaded_documents/pdfs/
• PDF viewer accessible for manual data extraction
• Suitable for critical revenue data validation

PRODUCTION RECOMMENDATIONS:
1. Implement cloud OCR for automated processing
2. Use document metadata for initial categorization
3. Flag for manual review when revenue extraction needed
4. Consider hybrid approach: metadata + selective manual review

NEXT STEPS:
- Document remains accessible for manual processing
- Vector database can store manual extractions
- Consider implementing cloud OCR integration"""

        return message
    
    def _format_error_status(self, error: Optional[str]) -> str:
        """Format error status for display."""
        if not error:
            return "Not attempted"
        elif "not available" in error.lower() or "import" in error.lower():
            return "Dependencies missing"
        elif "poppler" in error.lower():
            return "Poppler not installed"
        elif "tesseract" in error.lower():
            return "Tesseract not installed"
        else:
            return "Failed (technical error)"
    
    def _get_pdf_size(self) -> str:
        """Get PDF size for reporting."""
        return "cached locally"
    
    def _generate_fallback_message(self, page_count: int, ocr_available: bool = True, error: Optional[str] = None) -> str:
        """Generate structured fallback message when text extraction fails."""
        
        base_message = f"""DOCUMENT PROCESSING COMPLETED - TEXT EXTRACTION SUMMARY

Document Type: PDF Document
Pages Processed: {page_count if page_count > 0 else 'Unknown'}
Text Extraction Status: Limited Success

EXTRACTION ATTEMPTS:
1. PyPDF2 Standard Extraction: Failed (likely image-based document)
2. OCR Fallback: {'Attempted' if ocr_available else 'Not Available'}

DOCUMENT CHARACTERISTICS:
- File Type: Companies House Filing (typically scanned documents)
- Content: Likely contains financial information in image format
- Text Layer: None or incomplete text layer detected

PROCESSING RESULTS:
- Document validated and cached successfully
- Metadata extraction: Available
- Full text extraction: {'Requires manual review' if not ocr_available else 'Partially successful'}

RECOMMENDATIONS:
1. Document is processed and available for manual review
2. Consider using document metadata for categorization
3. OCR enhancement {'already attempted' if ocr_available else 'requires pytesseract installation'}
4. For critical data extraction, manual review recommended"""

        if error:
            base_message += f"\n\nTECHNICAL ERROR DETAILS:\n{error}"
            
        if not ocr_available:
            base_message += f"""

OCR SETUP INSTRUCTIONS:
1. Install OCR dependencies: pip install pytesseract pdf2image
2. Install Tesseract engine: brew install tesseract (macOS)
3. Retry document processing for enhanced text extraction"""

        return base_message
    
    def _create_document_chunks(self, text: str, document_id: str, company_name: str) -> List[DocumentChunk]:
        """Create optimized chunks with enhanced metadata for Q&A referencing."""
        chunks = []
        
        # Extract document metadata for Q&A references
        document_title = self._extract_document_title(text)
        filing_info = self._extract_filing_info(text)
        
        # Split into sentences for better chunking
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        chunk_index = 0
        start_char = 0
        
        for i, sentence in enumerate(sentences):
            # Check if adding sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # Calculate chunk boundaries
                end_char = start_char + len(current_chunk)
                
                # Create chunk with enhanced metadata for Q&A
                section_type = self._identify_section_type(current_chunk)
                section_title = self._extract_section_title(current_chunk)
                page_number = self._estimate_page_number(start_char, text)
                
                chunk = DocumentChunk(
                    text=current_chunk.strip(),
                    page_number=page_number,
                    section_type=section_type,
                    chunk_index=chunk_index,
                    metadata={
                        'document_id': document_id,
                        'company_name': company_name,
                        'document_title': document_title,
                        'filename': filing_info.get('filename'),
                        'filing_date': filing_info.get('filing_date'),
                        'filing_type': filing_info.get('filing_type'),
                        'section_title': section_title,
                        'character_count': len(current_chunk),
                        'start_char': start_char,
                        'end_char': end_char,
                        'start_page': page_number,
                        'end_page': page_number,
                        'paragraph_number': self._estimate_paragraph_number(start_char, text),
                        'preceding_text': self._get_preceding_context(text, start_char, 100),
                        'following_text': self._get_following_context(text, end_char, 100)
                    }
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                start_char = end_char - len(overlap_text)
                current_chunk = overlap_text + " " + sentence
                chunk_index += 1
            else:
                current_chunk += " " + sentence
        
        # Add final chunk
        if current_chunk.strip():
            end_char = start_char + len(current_chunk)
            section_type = self._identify_section_type(current_chunk)
            section_title = self._extract_section_title(current_chunk)
            page_number = self._estimate_page_number(start_char, text)
            
            chunk = DocumentChunk(
                text=current_chunk.strip(),
                page_number=page_number,
                section_type=section_type,
                chunk_index=chunk_index,
                metadata={
                    'document_id': document_id,
                    'company_name': company_name,
                    'document_title': document_title,
                    'filename': filing_info.get('filename'),
                    'filing_date': filing_info.get('filing_date'),
                    'filing_type': filing_info.get('filing_type'),
                    'section_title': section_title,
                    'character_count': len(current_chunk),
                    'start_char': start_char,
                    'end_char': end_char,
                    'start_page': page_number,
                    'end_page': page_number,
                    'paragraph_number': self._estimate_paragraph_number(start_char, text),
                    'preceding_text': self._get_preceding_context(text, start_char, 100),
                    'following_text': self._get_following_context(text, end_char, 100)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _identify_section_type(self, text: str) -> str:
        """Identify section type based on content."""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['profit', 'loss', 'revenue', 'turnover', 'income']):
            return "financial_statement"
        elif any(keyword in text_lower for keyword in ['balance', 'assets', 'liabilities']):
            return "balance_sheet"
        elif any(keyword in text_lower for keyword in ['cash', 'flow']):
            return "cash_flow"
        elif any(keyword in text_lower for keyword in ['notes', 'note to', 'accounting']):
            return "notes"
        elif any(keyword in text_lower for keyword in ['directors', 'report']):
            return "directors_report"
        else:
            return "general"
    
    def _extract_document_title(self, text: str) -> str:
        """Extract document title from content."""
        lines = text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            line = line.strip()
            if len(line) > 10 and any(keyword in line.lower() for keyword in 
                ['annual report', 'accounts', 'financial statement', 'filing']):
                return line
        
        return "Financial Document"
    
    def _extract_filing_info(self, text: str) -> Dict[str, str]:
        """Extract filing information for document metadata."""
        import re
        
        info = {}
        
        # Look for dates
        date_pattern = r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b'
        dates = re.findall(date_pattern, text[:1000])
        if dates:
            info['filing_date'] = dates[0]
        
        # Look for filing types
        filing_types = ['annual accounts', 'abbreviated accounts', 'full accounts', 'micro accounts']
        for filing_type in filing_types:
            if filing_type in text.lower()[:1000]:
                info['filing_type'] = filing_type.title()
                break
        
        return info
    
    def _extract_section_title(self, text: str) -> Optional[str]:
        """Extract section title from chunk text."""
        lines = text.split('\n')
        
        for line in lines[:3]:  # Check first few lines
            line = line.strip()
            if len(line) > 5 and len(line) < 100:
                # Check if line looks like a heading (all caps, title case, etc.)
                if line.isupper() or (line.istitle() and len(line.split()) <= 8):
                    return line
        
        return None
    
    def _estimate_page_number(self, char_position: int, full_text: str) -> int:
        """Estimate page number based on character position."""
        # Rough estimate: ~2500 characters per page
        chars_per_page = 2500
        return max(1, (char_position // chars_per_page) + 1)
    
    def _estimate_paragraph_number(self, char_position: int, full_text: str) -> int:
        """Estimate paragraph number based on character position."""
        text_before = full_text[:char_position]
        return len([p for p in text_before.split('\n\n') if p.strip()]) + 1
    
    def _get_preceding_context(self, text: str, start_pos: int, length: int) -> str:
        """Get preceding text context for chunk boundaries."""
        start = max(0, start_pos - length)
        return text[start:start_pos].strip()
    
    def _get_following_context(self, text: str, end_pos: int, length: int) -> str:
        """Get following text context for chunk boundaries."""
        return text[end_pos:end_pos + length].strip()
    
    def _store_chunks_with_embeddings(self, document_id: str, chunks: List[DocumentChunk]) -> int:
        """Store chunks with their embeddings in vector database (without metadata)."""
        chunk_data = []
        
        for chunk in chunks:
            # Generate embedding - encode() returns List[List[float]], extract first element
            embedding_result = self.embedding_model.encode(chunk.text)
            if isinstance(embedding_result, list) and len(embedding_result) > 0:
                single_embedding = embedding_result[0]
                if hasattr(single_embedding, 'tolist'):
                    embedding = single_embedding.tolist()
                else:
                    embedding = list(single_embedding)
            else:
                self.logger.error(f"❌ Invalid embedding result for chunk: {type(embedding_result)}")
                continue
            
            chunk_data.append({
                'text': chunk.text,
                'embedding': embedding,
                'metadata': chunk.metadata
            })
        
        # Store in vector database with TRUE UPSERT (prevents all duplication)
        upsert_result = self.vector_db.upsert_document_vectors(
            document_id=document_id, 
            chunks=chunk_data,
            content_type="financial_document",
            force_update=True  # Always update when reprocessing documents
        )
        return upsert_result.get('upserted_count', 0)
    
    def _store_chunks_with_embeddings_enhanced(self, document_id: str, chunks: List[DocumentChunk], 
                                             company_name: str, company_number: Optional[str] = None,
                                             transaction_id: Optional[str] = None, 
                                             unique_id: Optional[str] = None) -> int:
        """Store chunks with their embeddings and enhanced metadata in vector database with progress tracking."""
        
        # Enhanced logging: Start embedding generation
        self.logger.info(f"🔮 Starting embedding generation for {len(chunks)} chunks...")
        embedding_start = datetime.now()
        
        chunk_data = []
        successful_embeddings = 0
        failed_embeddings = 0
        
        for i, chunk in enumerate(chunks):
            try:
                # Progress indicator every 10 chunks
                if i % 10 == 0:
                    self.logger.info(f"   🔄 Processing chunk {i+1}/{len(chunks)} ({100*(i+1)/len(chunks):.1f}%)")
                
                # Preserve ALL rich metadata from chunk creation for Q&A functionality
                enhanced_metadata = chunk.metadata.copy()  # Start with rich metadata from chunking
                enhanced_metadata.update({
                    # Add processing-level metadata
                    'company_registration_number': company_number,
                    'unique_id': unique_id,
                    'section_type': chunk.section_type,
                    'page_number': chunk.page_number,
                    'chunk_index': chunk.chunk_index,
                    # Preserve Q&A-critical positioning data
                    'start_char': enhanced_metadata.get('start_char'),
                    'end_char': enhanced_metadata.get('end_char'),  
                    'start_page': enhanced_metadata.get('start_page'),
                    'end_page': enhanced_metadata.get('end_page'),
                    'paragraph_number': enhanced_metadata.get('paragraph_number'),
                    'section_title': enhanced_metadata.get('section_title'),
                    'document_title': enhanced_metadata.get('document_title'),
                    'filing_date': enhanced_metadata.get('filing_date'),
                    'filing_type': enhanced_metadata.get('filing_type'),
                    # Context for Q&A referencing
                    'preceding_text': enhanced_metadata.get('preceding_text'),
                    'following_text': enhanced_metadata.get('following_text')
                })
                
                # Generate embedding vector with error handling
                self.logger.debug(f"   🔮 Generating embedding for chunk {i+1} (length: {len(chunk.text)} chars)")
                embedding_result = self.embedding_model.encode(chunk.text)
                
                # encode() returns List[List[float]], extract first element
                if isinstance(embedding_result, list) and len(embedding_result) > 0:
                    single_embedding = embedding_result[0]
                    if hasattr(single_embedding, 'tolist'):
                        embedding_vector = single_embedding.tolist()
                    else:
                        embedding_vector = list(single_embedding)
                else:
                    self.logger.error(f"❌ Invalid embedding result for chunk {i+1}: {type(embedding_result)}")
                    continue
                
                # Validate embedding dimensions
                if len(embedding_vector) != 768:
                    self.logger.error(f"❌ Invalid embedding dimension for chunk {i+1}: {len(embedding_vector)} (expected 768)")
                    failed_embeddings += 1
                    continue
                
                chunk_dict = {
                    'text': chunk.text,
                    'embedding': embedding_vector,
                    'metadata': enhanced_metadata
                }
                chunk_data.append(chunk_dict)
                successful_embeddings += 1
                
                self.logger.debug(f"   ✅ Chunk {i+1} embedding generated successfully ({len(embedding_vector)}D)")
                
            except Exception as e:
                failed_embeddings += 1
                self.logger.error(f"❌ Failed to generate embedding for chunk {i+1}: {e}")
                continue
        
        embedding_time = (datetime.now() - embedding_start).total_seconds()
        self.logger.info(f"✅ Embedding generation completed in {embedding_time:.2f}s")
        self.logger.info(f"   📊 Success: {successful_embeddings}/{len(chunks)} embeddings ({100*successful_embeddings/len(chunks):.1f}%)")
        
        if failed_embeddings > 0:
            self.logger.warning(f"⚠️  {failed_embeddings} embeddings failed to generate")
        
        if not chunk_data:
            self.logger.error(f"❌ No valid embeddings generated for document {document_id}")
            return 0
        
        # Enhanced logging: Start vector database storage
        self.logger.info(f"💾 Storing {len(chunk_data)} embeddings in vector database...")
        storage_start = datetime.now()
        
        try:
            # Use TRUE UPSERT to prevent ALL duplication - INSERT OR REPLACE strategy
            upsert_result = self.vector_db.upsert_document_vectors(
                document_id=document_id,
                chunks=chunk_data,
                company_number=company_number,
                company_name=company_name,
                transaction_id=transaction_id,
                content_type="financial_document",
                force_update=True  # Always update when reprocessing documents
            )
            
            storage_time = (datetime.now() - storage_start).total_seconds()
            stored_count = upsert_result.get('upserted_count', 0)
            
            if stored_count > 0:
                self.logger.info(f"✅ Vector database storage completed in {storage_time:.2f}s")
                self.logger.info(f"   💾 Stored {stored_count}/{len(chunk_data)} chunks successfully")
                
                # Verify storage by checking database
                try:
                    with self.vector_db.get_connection() as conn:
                        doc_count = conn.execute("SELECT COUNT(*) FROM documents_v2 WHERE document_id = ?", (document_id,)).fetchone()[0]
                        chunk_count = conn.execute("SELECT COUNT(*) FROM document_chunks_v2 WHERE document_id = ?", (document_id,)).fetchone()[0]
                        self.logger.info(f"   🔍 Database verification: {doc_count} document(s), {chunk_count} chunks for {document_id}")
                except Exception as verify_e:
                    self.logger.warning(f"⚠️  Could not verify database storage: {verify_e}")
                
            else:
                self.logger.error(f"❌ Vector database storage failed - no chunks stored")
                
            return stored_count
            
        except Exception as e:
            storage_time = (datetime.now() - storage_start).total_seconds()
            self.logger.error(f"❌ Vector database storage failed after {storage_time:.2f}s: {e}")
            import traceback
            self.logger.error(f"   🔍 Storage error traceback: {traceback.format_exc()}")
            return 0
    
    def _extract_financial_data(self, query: SemanticQuery, chunks: List[DocumentChunk]) -> Tuple[Dict[str, Any], float]:
        """Extract financial data from relevant chunks."""
        query_lower = query.query_text.lower()
        financial_data = {}
        confidence = 0.0
        
        for chunk in chunks:
            chunk_text = chunk.text.lower()
            
            # Look for revenue patterns
            if "revenue" in query_lower and any(keyword in chunk_text for keyword in ["revenue", "turnover"]):
                import re
                numbers = re.findall(r'£([\d,]+)', chunk.text)
                if numbers:
                    financial_data["revenue"] = int(numbers[0].replace(',', ''))
                    confidence += 0.3
            
            # Look for profit patterns
            if "profit" in query_lower and "profit" in chunk_text:
                import re
                numbers = re.findall(r'£([\d,]+)', chunk.text)
                if numbers:
                    financial_data["profit"] = int(numbers[-1].replace(',', ''))
                    confidence += 0.3
        
        confidence = min(confidence, 0.9)  # Cap confidence
        return financial_data if financial_data else {}, confidence