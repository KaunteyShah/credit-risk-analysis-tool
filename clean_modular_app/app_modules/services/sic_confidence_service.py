#!/usr/bin/env python3
"""
SIC Confidence Service

Provides automatic existing SIC confidence calculation for companies.
This service can be called whenever a new company is added to immediately
calculate their existing SIC confidence score.

Author: AI Assistant
Date: 2025-10-04
"""

import sys
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add project modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the auto calculator
try:
    from auto_sic_confidence_calculator import AutoSICConfidenceCalculator
except ImportError:
    # Fallback import path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from auto_sic_confidence_calculator import AutoSICConfidenceCalculator

logger = logging.getLogger(__name__)


class SICConfidenceService:
    """Service for managing existing SIC confidence calculations"""
    
    def __init__(self, db_path: str = "data/credit_risk.db"):
        self.db_path = db_path
        self.calculator = AutoSICConfidenceCalculator(db_path)
        logger.info(f"SIC Confidence Service initialized with: {db_path}")
    
    def calculate_for_company(self, company_id: int) -> Dict:
        """
        Calculate existing SIC confidence for a single company
        
        Args:
            company_id: The company ID to calculate confidence for
            
        Returns:
            Dictionary with calculation results
        """
        try:
            # Get company data
            company_data = self._get_company_data(company_id)
            if not company_data:
                return {
                    'success': False,
                    'error': f'Company not found: {company_id}',
                    'company_id': company_id
                }
            
            # Calculate confidence using the auto-calculator
            success = self.calculator.create_sic_prediction_record(company_data)
            
            if success:
                # Get the calculated confidence and reasoning
                result = self._get_calculated_confidence_with_reasoning(company_id, company_data['sic_code'])
                
                if result:
                    return {
                        'success': True,
                        'company_id': company_id,
                        'company_name': company_data['company_name'],
                        'existing_sic_code': company_data['sic_code'],
                        'existing_sic_confidence': result['confidence'],
                        'existing_ai_reasoning': result['reasoning'],
                        'existing_sic_confidence_category': result['category'],
                        'existing_sic_calculation_timestamp': result['calculation_timestamp'],
                        'message': f'Successfully calculated confidence for {company_data["company_name"]}'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to retrieve calculated confidence from database',
                        'company_id': company_id
                    }
            else:
                return {
                    'success': False,
                    'error': 'Failed to calculate confidence',
                    'company_id': company_id
                }
                
        except Exception as e:
            logger.error(f"Error calculating confidence for company {company_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'company_id': company_id
            }
    
    def calculate_for_new_companies(self) -> Dict:
        """
        Calculate existing SIC confidence for all companies that don't have it yet
        
        Returns:
            Dictionary with batch calculation results
        """
        try:
            # Get companies needing confidence calculation
            companies = self.calculator.get_companies_needing_confidence()
            
            if not companies:
                return {
                    'success': True,
                    'message': 'All companies already have existing SIC confidence',
                    'processed': 0,
                    'total': 0
                }
            
            # Process all companies
            results = self.calculator.process_companies(companies)
            
            return {
                'success': True,
                'message': f'Successfully processed {results["success"]} out of {results["total_companies"]} companies',
                'processed': results['processed'],
                'success_count': results['success'],
                'failed_count': results['failed'],
                'total': results['total_companies']
            }
            
        except Exception as e:
            logger.error(f"Error in batch confidence calculation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_company_data(self, company_id: int) -> Optional[Dict]:
        """Get company data needed for confidence calculation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get company and SIC data
                cursor.execute("""
                    SELECT 
                        c.id,
                        c.company_name,
                        c.business_description,
                        csc.uk_sic_2007_code,
                        csc.uk_sic_2007_description
                    FROM companies c
                    JOIN company_sic_codes csc ON c.id = csc.company_id
                    WHERE c.id = ?
                    LIMIT 1
                """, (company_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'company_id': row[0],
                        'company_name': row[1],
                        'business_description': row[2] or '',
                        'sic_code': row[3],
                        'sic_description': row[4] or ''
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting company data for {company_id}: {e}")
            return None
    
    def _get_calculated_confidence_with_reasoning(self, company_id: int, sic_code: str) -> Optional[Dict]:
        """Get the calculated confidence and reasoning from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT existing_sic_confidence, existing_sic_reasoning, 
                           existing_sic_confidence_category, existing_sic_calculation_timestamp
                    FROM sic_prediction_history 
                    WHERE company_id = ? AND existing_sic_code = ?
                    ORDER BY prediction_timestamp DESC
                    LIMIT 1
                """, (company_id, sic_code))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'confidence': result[0],
                        'reasoning': result[1] or 'No reasoning available.',
                        'category': result[2] or 'Uncategorized',
                        'calculation_timestamp': result[3] or 'No timestamp available'
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting calculated confidence: {e}")
            return None

    def _get_calculated_confidence(self, company_id: int, sic_code: str) -> Optional[float]:
        """Get the calculated confidence from the database (backward compatibility)"""
        result = self._get_calculated_confidence_with_reasoning(company_id, sic_code)
        return result['confidence'] if result else None
    
    def has_existing_confidence(self, company_id: int) -> bool:
        """Check if a company already has existing SIC confidence calculated"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) FROM sic_prediction_history 
                    WHERE company_id = ? AND existing_sic_confidence IS NOT NULL
                """, (company_id,))
                
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking existing confidence for company {company_id}: {e}")
            return False


# Convenience functions for easy integration
def calculate_confidence_for_company(company_id: int, db_path: str = "data/credit_risk.db") -> Dict:
    """
    Convenience function to calculate existing SIC confidence for a single company
    
    Usage:
        result = calculate_confidence_for_company(123)
        if result['success']:
            print(f"Confidence: {result['existing_sic_confidence']}")
    """
    service = SICConfidenceService(db_path)
    return service.calculate_for_company(company_id)


def calculate_confidence_for_new_companies(db_path: str = "data/credit_risk.db") -> Dict:
    """
    Convenience function to calculate existing SIC confidence for all companies missing it
    
    Usage:
        result = calculate_confidence_for_new_companies()
        print(f"Processed: {result['processed']} companies")
    """
    service = SICConfidenceService(db_path)
    return service.calculate_for_new_companies()


if __name__ == "__main__":
    # Test the service
    print("🧪 Testing SIC Confidence Service")
    
    # Test batch calculation
    result = calculate_confidence_for_new_companies()
    print(f"📊 Batch result: {result}")
    
    # Test single company calculation (if there are companies)
    try:
        result = calculate_confidence_for_company(1)
        print(f"🏢 Single company result: {result}")
    except Exception as e:
        print(f"⚠️  Single company test failed: {e}")