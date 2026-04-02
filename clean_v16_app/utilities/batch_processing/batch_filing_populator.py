#!/usr/bin/env python3
"""
Batch Filing History Populator

Efficiently populates filing history data for all companies to improve
real-time performance by avoiding on-demand API calls.
"""

import sys
import time
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

# Add app modules to path
sys.path.append('/Users/kaunteyshah/Databricks/Credit_Risk/clean_modular_app')

from app_modules.apis.companies_house_client import CompaniesHouseClient
from app_modules.database.connection import DatabaseConnection
from app_modules.repositories.implementations.file_based.sqlite_filing_history_repository import SQLiteFilingHistoryRepository
from app_modules.utils.logger import get_logger

# Set up logging
logger = get_logger(__name__)

@dataclass
class BatchProcessingStats:
    """Statistics for batch processing"""
    total_companies: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped_existing: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration_minutes(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0.0
    
    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return (self.successful / self.processed) * 100

class BatchFilingPopulator:
    """
    Efficiently populate filing history for all companies
    """
    
    def __init__(self, skip_existing: bool = True, batch_size: int = 50):
        """
        Initialize batch populator
        
        Args:
            skip_existing: Skip companies that already have filing data
            batch_size: Number of companies to process in each batch
        """
        self.companies_house = CompaniesHouseClient()
        self.db_connection = DatabaseConnection()
        self.filing_repository = SQLiteFilingHistoryRepository(self.db_connection)
        self.skip_existing = skip_existing
        self.batch_size = batch_size
        self.stats = BatchProcessingStats()
        
    def get_companies_needing_filing_data(self) -> List[Dict[str, Any]]:
        """
        Get list of companies that need filing data
        
        Returns:
            List of company dictionaries with id, name, company_number, etc.
        """
        try:
            logger.info(f"🔍 Querying database for companies needing filing data...")
            logger.info(f"Database path: {self.db_connection.db_path}")
            logger.info(f"Skip existing: {self.skip_existing}, Batch size: {self.batch_size}")
            if self.skip_existing:
                # Get companies that don't have filing data
                query = """
                    SELECT c.id, c.company_name, c.company_number, c.unique_id, c.status
                    FROM companies c
                    LEFT JOIN company_filing_history_accounts f ON c.unique_id = f.unique_id
                    WHERE f.id IS NULL 
                        AND c.company_number IS NOT NULL 
                        AND c.company_number != ''
                        AND c.status = 'Active'
                    ORDER BY c.id
                    LIMIT ?
                """
                logger.info(f"Executing query for companies needing filing data (batch_size: {self.batch_size})")
                results = self.db_connection.execute_query(query, (self.batch_size,))
                logger.info(f"Query returned {len(results) if results else 0} results")
            else:
                # Get all companies with company numbers
                query = """
                    SELECT id, company_name, company_number, unique_id, status
                    FROM companies
                    WHERE company_number IS NOT NULL 
                        AND company_number != ''
                        AND status = 'Active'
                    ORDER BY id
                    LIMIT ?
                """
                results = self.db_connection.execute_query(query, (self.batch_size,))
            
            return results if results else []
            
        except Exception as e:
            logger.error(f"Error getting companies list: {e}")
            return []
    
    def get_total_companies_count(self) -> int:
        """Get total count of companies that need processing"""
        try:
            if self.skip_existing:
                query = """
                    SELECT COUNT(*) as count
                    FROM companies c
                    LEFT JOIN company_filing_history_accounts f ON c.unique_id = f.unique_id
                    WHERE f.id IS NULL 
                        AND c.company_number IS NOT NULL 
                        AND c.company_number != ''
                        AND c.status = 'Active'
                """
            else:
                query = """
                    SELECT COUNT(*) as count
                    FROM companies
                    WHERE company_number IS NOT NULL 
                        AND company_number != ''
                        AND status = 'Active'
                """
            
            results = self.db_connection.execute_query(query)
            return results[0]['count'] if results else 0
            
        except Exception as e:
            logger.error(f"Error getting companies count: {e}")
            return 0
    
    def process_company_filing(self, company: Dict[str, Any]) -> bool:
        """
        Process filing history for a single company
        
        Args:
            company: Company data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        company_id = company['id']
        company_name = company['company_name']
        company_number = company['company_number']
        unique_id = company['unique_id']
        
        try:
            logger.info(f"Processing {company_name} ({company_number})...")
            
            # Check if already has filing data and skip_existing is True
            if self.skip_existing:
                existing_query = "SELECT id FROM company_filing_history_accounts WHERE unique_id = ?"
                existing = self.db_connection.execute_query(existing_query, (unique_id,))
                if existing:
                    logger.info(f"Skipping {company_name} - already has filing data")
                    self.stats.skipped_existing += 1
                    return True
            
            # Get filing history from Companies House API
            filing_result = self.companies_house.get_latest_financial_filing(company_number)
            
            if filing_result and filing_result.get('success'):
                # Prepare data for storage
                filing_data_to_store = {
                    'unique_id': unique_id,
                    'company_registration_number': company_number,
                    'company_name': company_name,
                    'company_address': '',  # Will be empty for batch processing
                    'filing_details': filing_result['data']['latest_filing'],
                    'raw_api_response': filing_result['data']['raw_api_response']
                }
                
                # Store in database
                storage_success = self.filing_repository.insert_filing_record(filing_data_to_store)
                
                if storage_success:
                    logger.info(f"✅ Successfully stored filing data for {company_name}")
                    self.stats.successful += 1
                    return True
                else:
                    logger.warning(f"❌ Failed to store filing data for {company_name}")
                    self.stats.failed += 1
                    return False
            else:
                # No filing data available or API error
                error_msg = filing_result.get('error', 'No filing data available') if filing_result else 'API call failed'
                logger.info(f"No filing data for {company_name}: {error_msg}")
                self.stats.failed += 1
                return False
                
        except Exception as e:
            logger.error(f"Error processing {company_name} ({company_number}): {e}")
            self.stats.failed += 1
            return False
    
    def run_batch_population(self, max_companies: Optional[int] = None) -> BatchProcessingStats:
        """
        Run the batch population process
        
        Args:
            max_companies: Maximum number of companies to process (None for all)
            
        Returns:
            BatchProcessingStats with results
        """
        self.stats.start_time = datetime.now()
        self.stats.total_companies = self.get_total_companies_count()
        
        if max_companies:
            self.stats.total_companies = min(self.stats.total_companies, max_companies)
        
        logger.info(f"🚀 Starting batch filing population for {self.stats.total_companies} companies...")
        logger.info(f"Batch size: {self.batch_size}, Skip existing: {self.skip_existing}")
        
        companies_processed = 0
        
        try:
            while companies_processed < self.stats.total_companies:
                # Get batch of companies
                remaining = self.stats.total_companies - companies_processed
                current_batch_size = min(self.batch_size, remaining)
                
                companies = self.get_companies_needing_filing_data()
                
                if not companies:
                    logger.info("No more companies to process")
                    break
                
                logger.info(f"Processing batch of {len(companies)} companies...")
                
                # Process each company in the batch
                for company in companies:
                    if max_companies and self.stats.processed >= max_companies:
                        break
                        
                    success = self.process_company_filing(company)
                    self.stats.processed += 1
                    companies_processed += 1
                    
                    # Rate limiting - respect Companies House API limits
                    time.sleep(0.6)  # 0.6 seconds between requests
                    
                    # Progress update every 10 companies
                    if self.stats.processed % 10 == 0:
                        progress = (self.stats.processed / self.stats.total_companies) * 100
                        logger.info(f"Progress: {self.stats.processed}/{self.stats.total_companies} ({progress:.1f}%)")
                
                # Small break between batches
                time.sleep(2)
                
        except KeyboardInterrupt:
            logger.info("Process interrupted by user")
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
        
        self.stats.end_time = datetime.now()
        
        # Log final statistics
        logger.info("📊 Batch Population Complete!")
        logger.info(f"Total Processed: {self.stats.processed}")
        logger.info(f"Successful: {self.stats.successful}")
        logger.info(f"Failed: {self.stats.failed}")
        logger.info(f"Skipped (existing): {self.stats.skipped_existing}")
        logger.info(f"Success Rate: {self.stats.success_rate:.1f}%")
        logger.info(f"Duration: {self.stats.duration_minutes:.1f} minutes")
        
        return self.stats

def main():
    """Main function for running batch population"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch populate filing history data")
    parser.add_argument('--max-companies', type=int, help='Maximum number of companies to process')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing')
    parser.add_argument('--no-skip-existing', action='store_true', help='Process all companies, even those with existing data')
    parser.add_argument('--test-run', action='store_true', help='Test run with first 5 companies only')
    
    args = parser.parse_args()
    
    # Configure for test run
    if args.test_run:
        max_companies = 5
        batch_size = 5
        logger.info("🧪 Running in TEST MODE - processing only 5 companies")
    else:
        max_companies = args.max_companies
        batch_size = args.batch_size
    
    skip_existing = not args.no_skip_existing
    
    # Create and run populator
    populator = BatchFilingPopulator(
        skip_existing=skip_existing,
        batch_size=batch_size
    )
    
    stats = populator.run_batch_population(max_companies=max_companies)
    
    # Return appropriate exit code
    if stats.processed > 0 and stats.success_rate >= 50:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main()