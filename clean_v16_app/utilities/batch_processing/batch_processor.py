#!/usr/bin/env python3
"""
Ultra-Light Batch Processor for Revenue Extraction

This script runs LOCALLY or in GitHub Actions to pre-process company data.
Generates a lightweight SQLite database for ultra-fast Azure deployment.

Key Benefits:
- Process everything offline (no Azure compute costs)
- Generate pre-computed embeddings and revenue data
- Create lightweight runtime database
- Deploy only simple Flask app to Azure

Usage:
    python batch_processor.py --companies 1000 --output precomputed.db
"""

import sqlite3
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib

# Only import heavy dependencies for batch processing
try:
    import fitz  # PyMuPDF
    from sentence_transformers import SentenceTransformer
    import pandas as pd
    import requests
    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False
    print("⚠️  ML libraries not installed. Install with: pip install -r requirements-dev.txt")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UltraLightBatchProcessor:
    """
    Batch processor for pre-computing revenue data offline.
    Generates ultra-light SQLite database for Azure deployment.
    """
    
    def __init__(self, db_path: str = "precomputed_revenue.db"):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        
        # Initialize ML models (only for batch processing)
        if HAS_ML_LIBS:
            logger.info("🤖 Loading sentence-transformers model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Model loaded successfully")
        else:
            self.embedding_model = None
            
        self._initialize_database()
    
    def _initialize_database(self):
        """Create optimized database schema for fast runtime queries."""
        cursor = self.db.cursor()
        
        # Pre-computed revenue data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS precomputed_revenue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                company_name_normalized TEXT NOT NULL,
                company_number TEXT,
                revenue_data TEXT,  -- JSON with extracted revenue figures
                confidence_score REAL,
                last_updated TEXT,
                document_id TEXT,
                transaction_id TEXT,
                processing_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_number, transaction_id)
            )
        """)
        
        # Pre-computed text chunks for fallback processing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS precomputed_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_number TEXT NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_embedding BLOB,  -- Binary embedding data
                chunk_metadata TEXT,   -- JSON metadata
                revenue_relevant BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Company name variations for fuzzy matching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                similarity_score REAL,
                company_number TEXT,
                UNIQUE(canonical_name, alias_name)
            )
        """)
        
        # Create indexes for fast runtime queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_normalized ON precomputed_revenue(company_name_normalized)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_number ON precomputed_revenue(company_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transaction_id ON precomputed_revenue(transaction_id)")
        
        self.db.commit()
        logger.info("✅ Database schema initialized")
    
    def process_companies_batch(self, company_list: List[Dict], max_companies: int = 1000):
        """
        Process a batch of companies and store pre-computed revenue data.
        
        Args:
            company_list: List of company dictionaries with name, number, etc.
            max_companies: Maximum number of companies to process
        """
        processed_count = 0
        success_count = 0
        
        for company in company_list[:max_companies]:
            try:
                logger.info(f"📋 Processing: {company.get('name', 'Unknown')} ({processed_count + 1}/{max_companies})")
                
                # Check if already processed
                if self._is_already_processed(company):
                    logger.info("   ⏭️  Already processed, skipping")
                    continue
                
                # Process company
                result = self._process_single_company(company)
                if result:
                    success_count += 1
                    logger.info(f"   ✅ Success - Revenue: {result.get('revenue', 'N/A')}")
                else:
                    logger.warning(f"   ❌ Failed to process")
                
                processed_count += 1
                
                # Commit every 10 companies for safety
                if processed_count % 10 == 0:
                    self.db.commit()
                    logger.info(f"💾 Committed {processed_count} companies")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {company.get('name', 'Unknown')}: {e}")
                processed_count += 1
        
        self.db.commit()
        logger.info(f"🎯 Batch processing complete: {success_count}/{processed_count} successful")
        return success_count, processed_count
    
    def _process_single_company(self, company: Dict) -> Optional[Dict]:
        """Process a single company and extract revenue data."""
        try:
            # Get latest filing
            filing_info = self._get_latest_filing(company)
            if not filing_info:
                return None
            
            # Download and extract text
            text_content = self._download_and_extract_text(filing_info['document_id'])
            if not text_content:
                return None
            
            # Extract revenue using simple patterns (no complex ML)
            revenue_data = self._extract_revenue_simple(text_content)
            
            # Store pre-computed result
            self._store_precomputed_result(company, filing_info, revenue_data, text_content)
            
            return revenue_data
            
        except Exception as e:
            logger.error(f"Error processing company {company.get('name')}: {e}")
            return None
    
    def _extract_revenue_simple(self, text: str) -> Dict:
        """
        Simple pattern-based revenue extraction (no complex ML).
        Fast, lightweight, good enough for most cases.
        """
        import re
        
        revenue_patterns = [
            r'turnover[:\s]+£?([0-9,]+)',
            r'revenue[:\s]+£?([0-9,]+)', 
            r'total income[:\s]+£?([0-9,]+)',
            r'sales[:\s]+£?([0-9,]+)',
            r'£([0-9,]+)[^\d]*(?:turnover|revenue|sales)'
        ]
        
        found_values = []
        for pattern in revenue_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                try:
                    value = int(match.replace(',', ''))
                    if 1000 <= value <= 10000000000:  # Reasonable range
                        found_values.append(value)
                except:
                    continue
        
        if found_values:
            # Take the most common value or median
            revenue = sorted(found_values)[len(found_values)//2]
            confidence = min(0.8, len(found_values) * 0.2)  # Higher confidence for multiple matches
            
            return {
                'revenue': revenue,
                'confidence': confidence,
                'method': 'pattern_extraction',
                'all_values': found_values[:5]  # Store top 5 for validation
            }
        
        return {
            'revenue': None,
            'confidence': 0.0,
            'method': 'not_found',
            'all_values': []
        }
    
    def _download_and_extract_text(self, document_id: str) -> Optional[str]:
        """Download PDF and extract text using simple PyMuPDF."""
        if not HAS_ML_LIBS:
            logger.warning("ML libraries not available for PDF processing")
            return None
            
        try:
            # Mock download for now - replace with actual Companies House API
            # pdf_content = self._download_from_companies_house(document_id)
            
            # For demo, return mock text
            return f"Mock text content for document {document_id}. Turnover: £500,000. Revenue increased from previous year."
            
        except Exception as e:
            logger.error(f"Error downloading/extracting document {document_id}: {e}")
            return None
    
    def _store_precomputed_result(self, company: Dict, filing_info: Dict, revenue_data: Dict, text_content: str):
        """Store pre-computed result in database."""
        cursor = self.db.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO precomputed_revenue 
            (company_name, company_name_normalized, company_number, revenue_data, 
             confidence_score, last_updated, document_id, transaction_id, processing_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company.get('name', ''),
            self._normalize_company_name(company.get('name', '')),
            company.get('number', ''),
            json.dumps(revenue_data),
            revenue_data.get('confidence', 0.0),
            datetime.now().isoformat(),
            filing_info.get('document_id', ''),
            filing_info.get('transaction_id', ''),
            'batch_processed'
        ))
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for consistent matching."""
        import re
        normalized = name.lower()
        normalized = re.sub(r'\b(ltd|limited|plc|inc|corp|corporation)\b', '', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _get_latest_filing(self, company: Dict) -> Optional[Dict]:
        """Get latest filing info for company."""
        # Mock implementation - replace with actual Companies House API
        return {
            'document_id': f"doc_{company.get('number', 'unknown')}",
            'transaction_id': f"txn_{datetime.now().strftime('%Y%m%d')}",
            'filing_date': datetime.now().isoformat()
        }
    
    def _is_already_processed(self, company: Dict) -> bool:
        """Check if company already processed."""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM precomputed_revenue 
            WHERE company_number = ?
        """, (company.get('number', ''),))
        return cursor.fetchone()[0] > 0
    
    def generate_statistics(self) -> Dict:
        """Generate processing statistics."""
        cursor = self.db.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM precomputed_revenue")
        total_companies = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM precomputed_revenue WHERE revenue_data LIKE '%\"revenue\": null%'")
        no_revenue = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(confidence_score) FROM precomputed_revenue WHERE confidence_score > 0")
        avg_confidence = cursor.fetchone()[0] or 0
        
        return {
            'total_companies': total_companies,
            'companies_with_revenue': total_companies - no_revenue,
            'companies_without_revenue': no_revenue,
            'success_rate': (total_companies - no_revenue) / max(total_companies, 1),
            'average_confidence': round(avg_confidence, 3),
            'database_size_mb': self._get_db_size_mb()
        }
    
    def _get_db_size_mb(self) -> float:
        """Get database size in MB."""
        import os
        try:
            size_bytes = os.path.getsize(self.db_path)
            return round(size_bytes / (1024 * 1024), 2)
        except:
            return 0.0


def main():
    """Main entry point for batch processing."""
    parser = argparse.ArgumentParser(description='Ultra-Light Batch Processor for Revenue Extraction')
    parser.add_argument('--companies', type=int, default=100, help='Number of companies to process')
    parser.add_argument('--output', type=str, default='precomputed_revenue.db', help='Output database path')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    
    args = parser.parse_args()
    
    processor = UltraLightBatchProcessor(args.output)
    
    if args.stats:
        stats = processor.generate_statistics()
        print("\n📊 Processing Statistics:")
        print(f"   Total companies: {stats['total_companies']}")
        print(f"   Success rate: {stats['success_rate']:.1%}")
        print(f"   Average confidence: {stats['average_confidence']}")
        print(f"   Database size: {stats['database_size_mb']} MB")
        return
    
    # Mock company data for demo
    mock_companies = [
        {'name': 'Test Company Ltd', 'number': f'0123456{i:02d}'} 
        for i in range(args.companies)
    ]
    
    logger.info(f"🚀 Starting batch processing of {args.companies} companies")
    success_count, total_count = processor.process_companies_batch(mock_companies, args.companies)
    
    stats = processor.generate_statistics()
    print(f"\n✅ Batch processing complete!")
    print(f"   Processed: {success_count}/{total_count}")
    print(f"   Database: {stats['database_size_mb']} MB")
    print(f"   Ready for ultra-light Azure deployment!")


if __name__ == "__main__":
    main()