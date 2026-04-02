#!/usr/bin/env python3
"""
Interim vs Annual Report Validation Logic

Adjust validation ranges and logic based on report type (interim vs annual)
"""

import os
import sys
import re
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ReportTypeValidator:
    def __init__(self):
        # Company-specific annual revenue ranges (in millions)
        self.annual_revenue_ranges = {
            'ADMIRAL GROUP PLC': (2500, 4500),  # £2.5B - £4.5B
            'ATLAS FM GROUP LIMITED': (50, 200),  # £50M - £200M
            'ARUP GROUP LIMITED': (1500, 3000),  # £1.5B - £3B
            'AVIVA PLC': (15000, 25000),  # £15B - £25B
            'ASHTEAD GROUP PLC': (6000, 10000),  # £6B - £10B
            'default': (100, 50000)  # Default range for unknown companies
        }
        
        # Interim report patterns
        self.interim_patterns = [
            r'interim\s+results?',
            r'half\s+year\s+results?',
            r'h1\s+20\d{2}',
            r'first\s+half',
            r'six\s+months?',
            r'6\s+months?',
            r'half\s+yearly?',
            r'mid\s+year',
        ]
        
        # Annual report patterns
        self.annual_patterns = [
            r'annual\s+report',
            r'full\s+year\s+results?',
            r'fy\s+20\d{2}',
            r'year\s+ended?',
            r'annual\s+accounts?',
            r'twelve\s+months?',
            r'12\s+months?',
            r'financial\s+year',
        ]
    
    def detect_report_type(self, text: str, document_date: str | None = None) -> Dict:
        """Detect if this is an interim or annual report"""
        
        text_lower = text.lower()
        
        # Count interim indicators
        interim_score = 0
        interim_matches = []
        for pattern in self.interim_patterns:
            matches = re.findall(pattern, text_lower)
            interim_score += len(matches)
            if matches:
                interim_matches.extend(matches)
        
        # Count annual indicators
        annual_score = 0
        annual_matches = []
        for pattern in self.annual_patterns:
            matches = re.findall(pattern, text_lower)
            annual_score += len(matches)
            if matches:
                annual_matches.extend(matches)
        
        # Analyze document date if provided
        date_analysis = self._analyze_document_date(document_date)
        
        # Determine report type
        if interim_score > annual_score:
            report_type = 'interim'
            confidence = min(0.9, 0.6 + (interim_score - annual_score) * 0.1)
        elif annual_score > interim_score:
            report_type = 'annual'
            confidence = min(0.9, 0.6 + (annual_score - interim_score) * 0.1)
        else:
            # Use date analysis as tiebreaker
            if date_analysis['likely_interim']:
                report_type = 'interim'
                confidence = 0.5
            else:
                report_type = 'annual'
                confidence = 0.5
        
        return {
            'type': report_type,
            'confidence': confidence,
            'interim_indicators': interim_matches,
            'annual_indicators': annual_matches,
            'date_analysis': date_analysis,
            'reasoning': f"Found {interim_score} interim vs {annual_score} annual indicators"
        }
    
    def _analyze_document_date(self, document_date: str | None = None) -> Dict:
        """Analyze document date to infer report type"""
        if not document_date:
            return {'likely_interim': False, 'reasoning': 'No date provided'}
        
        try:
            # Parse date (assuming YYYY-MM-DD format)
            doc_date = datetime.strptime(document_date, '%Y-%m-%d')
            month = doc_date.month
            
            # Interim reports typically filed in Aug/Sep (H1 results)
            # Annual reports typically filed in Mar/Apr/May
            if month in [8, 9]:
                return {
                    'likely_interim': True,
                    'reasoning': f'Filed in month {month} (typical for interim reports)'
                }
            elif month in [3, 4, 5]:
                return {
                    'likely_interim': False,
                    'reasoning': f'Filed in month {month} (typical for annual reports)'
                }
            else:
                return {
                    'likely_interim': False,
                    'reasoning': f'Filed in month {month} (neutral indicator)'
                }
        except:
            return {'likely_interim': False, 'reasoning': 'Could not parse date'}
    
    def get_adjusted_validation_ranges(self, company_name: str, report_type: str) -> Tuple[float, float]:
        """Get validation ranges adjusted for report type"""
        
        # Get base annual range
        if company_name in self.annual_revenue_ranges:
            annual_min, annual_max = self.annual_revenue_ranges[company_name]
        else:
            annual_min, annual_max = self.annual_revenue_ranges['default']
        
        if report_type == 'interim':
            # Interim reports typically show 6 months, so expect ~40-60% of annual
            # (not exactly 50% due to seasonality)
            interim_min = annual_min * 0.35  # 35% of annual minimum
            interim_max = annual_max * 0.65  # 65% of annual maximum
            return (interim_min, interim_max)
        else:
            # Annual reports - use full range
            return (annual_min, annual_max)
    
    def validate_revenue_for_report_type(self, 
                                       revenue_candidates: List[Dict], 
                                       company_name: str, 
                                       report_analysis: Dict) -> Dict:
        """Validate revenue candidates based on report type"""
        
        report_type = report_analysis['type']
        min_range, max_range = self.get_adjusted_validation_ranges(company_name, report_type)
        
        validated_candidates = []
        
        for candidate in revenue_candidates:
            amount_millions = candidate.get('amount', 0) / 1_000_000
            
            # Check if amount is within expected range
            within_range = min_range <= amount_millions <= max_range
            
            # Calculate distance from expected range (for scoring)
            if amount_millions < min_range:
                range_distance = (min_range - amount_millions) / min_range
                range_status = 'below_range'
            elif amount_millions > max_range:
                range_distance = (amount_millions - max_range) / max_range
                range_status = 'above_range'
            else:
                range_distance = 0
                range_status = 'within_range'
            
            # Adjust confidence based on range validation
            base_confidence = candidate.get('confidence', 0.5)
            if within_range:
                adjusted_confidence = min(1.0, base_confidence + 0.2)
            else:
                # Penalize candidates outside expected range
                penalty = min(0.4, range_distance * 0.5)
                adjusted_confidence = max(0.1, base_confidence - penalty)
            
            validated_candidate = candidate.copy()
            validated_candidate.update({
                'within_expected_range': within_range,
                'expected_range_min': min_range,
                'expected_range_max': max_range,
                'range_distance': range_distance,
                'range_status': range_status,
                'adjusted_confidence': adjusted_confidence,
                'report_type': report_type
            })
            
            validated_candidates.append(validated_candidate)
        
        # Sort by adjusted confidence
        validated_candidates.sort(key=lambda x: x['adjusted_confidence'], reverse=True)
        
        return {
            'candidates': validated_candidates,
            'report_type': report_type,
            'expected_range': (min_range, max_range),
            'validation_summary': {
                'total_candidates': len(validated_candidates),
                'within_range': sum(1 for c in validated_candidates if c['within_expected_range']),
                'above_range': sum(1 for c in validated_candidates if c['range_status'] == 'above_range'),
                'below_range': sum(1 for c in validated_candidates if c['range_status'] == 'below_range')
            }
        }


def test_report_type_validation():
    """Test report type detection and validation"""
    
    validator = ReportTypeValidator()
    
    # Test report type detection
    test_cases = [
        {
            'text': "Admiral Group reports excellent H1 2025 results. Interim results highlights show strong growth.",
            'date': "2025-08-08",
            'company': "ADMIRAL GROUP PLC"
        },
        {
            'text': "Annual Report 2024. Full year results demonstrate strong performance across all divisions.",
            'date': "2025-04-15", 
            'company': "ADMIRAL GROUP PLC"
        },
        {
            'text': "Atlas FM Group Limited - Six months ended 31 December 2023. Half year financial statements.",
            'date': "2023-12-31",
            'company': "ATLAS FM GROUP LIMITED"
        }
    ]
    
    print("🧪 TESTING REPORT TYPE VALIDATION")
    print("=" * 45)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['company']}")
        print(f"📅 Date: {test_case['date']}")
        print(f"📄 Text: {test_case['text'][:100]}...")
        print("-" * 50)
        
        # Detect report type
        report_analysis = validator.detect_report_type(test_case['text'], test_case['date'])
        
        print(f"📊 Report Type: {report_analysis['type'].upper()}")
        print(f"🎯 Confidence: {report_analysis['confidence']:.2f}")
        print(f"💭 Reasoning: {report_analysis['reasoning']}")
        
        if report_analysis['interim_indicators']:
            print(f"📈 Interim indicators: {report_analysis['interim_indicators']}")
        if report_analysis['annual_indicators']:
            print(f"📈 Annual indicators: {report_analysis['annual_indicators']}")
        
        # Get adjusted ranges
        min_range, max_range = validator.get_adjusted_validation_ranges(
            test_case['company'], 
            report_analysis['type']
        )
        
        print(f"💰 Expected range: £{min_range:.0f}M - £{max_range:.0f}M")
        
        # Test with sample revenue candidates
        sample_candidates = [
            {'amount': 521_000_000, 'confidence': 0.8, 'category': 'profit'},  # £521M
            {'amount': 2_800_000_000, 'confidence': 0.9, 'category': 'revenue'},  # £2.8B
            {'amount': 1_200_000_000, 'confidence': 0.7, 'category': 'turnover'}  # £1.2B
        ]
        
        validation_result = validator.validate_revenue_for_report_type(
            sample_candidates, test_case['company'], report_analysis
        )
        
        print(f"\n🔍 Validation Results:")
        for j, candidate in enumerate(validation_result['candidates'], 1):
            amount_m = candidate['amount'] / 1_000_000
            print(f"   {j}. £{amount_m:.0f}M ({candidate['category']})")
            print(f"      Status: {candidate['range_status']}")
            print(f"      Confidence: {candidate['confidence']:.2f} → {candidate['adjusted_confidence']:.2f}")
        
        summary = validation_result['validation_summary']
        print(f"📈 Summary: {summary['within_range']}/{summary['total_candidates']} within range")


if __name__ == "__main__":
    test_report_type_validation()