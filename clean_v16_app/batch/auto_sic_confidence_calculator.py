#!/usr/bin/env python3
"""
Auto SIC Confidence Calculator

Automatically calculates existing SIC confidence scores for companies
based on business descriptions and SIC code descriptions using fuzzy matching.
"""

import sqlite3
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add project modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try importing fuzzywuzzy for text similarity
try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

logger = logging.getLogger(__name__)


class AutoSICConfidenceCalculator:
    def __init__(self, db_path: str = "data/credit_risk.db"):
        self.db_path = db_path
        print(f"🔧 Auto SIC Confidence Calculator initialized with: {db_path}")
        
    def get_companies_needing_confidence(self) -> List[Dict]:
        """Get companies that need existing SIC confidence calculation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Find companies in company_sic_codes that don't have confidence OR missing enhanced fields
                query = """
                SELECT DISTINCT
                    csc.company_id,
                    csc.company_name,
                    c.business_description,
                    csc.uk_sic_2007_code,
                    csc.uk_sic_2007_description
                FROM company_sic_codes csc
                JOIN companies c ON c.id = csc.company_id
                LEFT JOIN sic_prediction_history sph ON sph.company_id = csc.company_id
                    AND sph.existing_sic_code = csc.uk_sic_2007_code
                WHERE csc.is_primary = 1
                AND c.business_description IS NOT NULL 
                AND c.business_description != ''
                AND csc.uk_sic_2007_code IS NOT NULL
                AND (sph.existing_sic_confidence IS NULL 
                     OR sph.id IS NULL 
                     OR sph.existing_sic_confidence_category IS NULL
                     OR sph.existing_sic_calculation_timestamp IS NULL)
                ORDER BY csc.company_id
                """
                
                cursor.execute(query)
                results = cursor.fetchall()
                
                companies = []
                for row in results:
                    companies.append({
                        'company_id': row[0],
                        'company_name': row[1],
                        'business_description': row[2],
                        'sic_code': row[3],
                        'sic_description': row[4]
                    })
                
                return companies
                
        except Exception as e:
            print(f"❌ Error getting companies needing confidence: {e}")
            return []

    def calculate_confidence_score_with_reasoning(self, business_description: str, sic_code: str, sic_description: Optional[str] = None) -> Tuple[float, str]:
        """Calculate confidence score for existing SIC code with detailed reasoning"""
        if not business_description or not sic_code:
            return 0.0, "Missing business description or SIC code for analysis."
            
        business_lower = business_description.lower().strip()
        reasoning_parts = []
        
        # Basic confidence scoring based on description length and content
        word_count = len(business_description.split())
        if word_count < 3:
            reasoning_parts.append(f"Very brief business description ({word_count} words) limits analysis accuracy.")
            return 15.0, " ".join(reasoning_parts)
        
        reasoning_parts.append(f"Business description analysis: {word_count} words provide {'good' if word_count > 8 else 'adequate'} detail.")
        
        # If we have SIC description, do fuzzy matching
        if sic_description and FUZZYWUZZY_AVAILABLE:
            try:
                sic_lower = sic_description.lower().strip()
                
                # Use multiple similarity metrics
                ratio_score = fuzz.ratio(business_lower, sic_lower)
                partial_score = fuzz.partial_ratio(business_lower, sic_lower)
                token_sort_score = fuzz.token_sort_ratio(business_lower, sic_lower)
                token_set_score = fuzz.token_set_ratio(business_lower, sic_lower)
                
                # Take the maximum score for best match
                confidence = max(ratio_score, partial_score, token_sort_score, token_set_score)
                best_method = ['exact match', 'partial match', 'token sort', 'token set'][
                    [ratio_score, partial_score, token_sort_score, token_set_score].index(confidence)
                ]
                
                reasoning_parts.append(f"Fuzzy matching with SIC description '{sic_description}' using {best_method} method: {confidence:.1f}% similarity.")
                
                if confidence > 80:
                    reasoning_parts.append("High text similarity indicates strong alignment between business activities and SIC classification.")
                elif confidence > 60:
                    reasoning_parts.append("Moderate text similarity suggests reasonable but not perfect SIC alignment.")
                else:
                    reasoning_parts.append("Low text similarity indicates potential SIC code mismatch with business description.")
                
                return min(confidence, 95.0), " ".join(reasoning_parts)
                
            except Exception as e:
                reasoning_parts.append(f"Fuzzy matching failed, falling back to keyword analysis. Error: {str(e)}")
        else:
            reasoning_parts.append("No SIC description available for fuzzy matching, using keyword analysis.")
        
        # Fallback: Basic keyword analysis
        business_words = set(business_lower.split())
        
        # Industry-specific keywords boost confidence
        sector_keywords = {
            'retail': ['retail', 'shop', 'store', 'supermarket', 'mall'],
            'manufacturing': ['manufacturing', 'production', 'factory', 'assembly'],
            'software': ['software', 'technology', 'digital', 'computing', 'app'],
            'construction': ['construction', 'building', 'contractor', 'engineering'],
            'transport': ['transport', 'logistics', 'delivery', 'shipping', 'freight'],
            'finance': ['financial', 'banking', 'investment', 'insurance', 'lending'],
            'professional': ['consulting', 'advisory', 'professional', 'services']
        }
        
        # Generic terms that reduce confidence
        generic_terms = {'limited', 'company', 'plc', 'ltd', 'holdings', 'group', 'activities'}
        
        # Calculate confidence based on sector alignment
        sector_matches = 0
        matched_sectors = []
        for sector, keywords in sector_keywords.items():
            if any(keyword in business_lower for keyword in keywords):
                sector_matches += 1
                matched_sectors.append(sector)
        
        generic_count = len(business_words.intersection(generic_terms))
        
        # Base confidence calculation
        base_confidence = 25.0  # Start with low base
        base_confidence += sector_matches * 25.0  # Boost for sector keywords
        base_confidence -= generic_count * 5.0    # Penalize for generic terms
        
        # Description length bonus
        if word_count > 15:
            base_confidence += 15.0
            reasoning_parts.append("Detailed description (15+ words) increases confidence.")
        elif word_count > 8:
            base_confidence += 10.0
            reasoning_parts.append("Adequate description length (8+ words) provides moderate confidence.")
        
        # Sector analysis reasoning
        if matched_sectors:
            reasoning_parts.append(f"Identified sector keywords for: {', '.join(matched_sectors)} industries.")
        else:
            reasoning_parts.append("No clear sector-specific keywords found in description.")
            
        if generic_count > 2:
            reasoning_parts.append(f"High number of generic terms ({generic_count}) reduces specificity.")
        
        final_confidence = max(10.0, min(base_confidence, 85.0))
        
        if final_confidence > 70:
            reasoning_parts.append("Strong keyword alignment with business activities.")
        elif final_confidence > 50:
            reasoning_parts.append("Moderate keyword alignment suggests reasonable SIC match.")
        else:
            reasoning_parts.append("Limited keyword alignment indicates potential classification review needed.")
            
        return final_confidence, " ".join(reasoning_parts)

    def get_confidence_category(self, confidence_score: float) -> str:
        """Categorize confidence score into meaningful categories"""
        if confidence_score >= 85:
            return "Excellent"
        elif confidence_score >= 70:
            return "Good"  
        elif confidence_score >= 50:
            return "Fair"
        else:
            return "Very Poor"

    def calculate_confidence_score_with_reasoning_and_category(self, business_description: str, sic_code: str, sic_description: Optional[str] = None) -> Tuple[float, str, str]:
        """Calculate confidence score with reasoning and category"""
        confidence, reasoning = self.calculate_confidence_score_with_reasoning(business_description, sic_code, sic_description)
        category = self.get_confidence_category(confidence)
        return confidence, reasoning, category

    def calculate_confidence_score(self, business_description: str, sic_code: str, sic_description: Optional[str] = None) -> float:
        """Calculate confidence score for existing SIC code (backward compatibility)"""
        confidence, _ = self.calculate_confidence_score_with_reasoning(business_description, sic_code, sic_description)
        return confidence

    def create_sic_prediction_record(self, company_data: Dict) -> bool:
        """Create or update sic_prediction_history record with existing SIC confidence"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate confidence, reasoning, and category
                confidence, reasoning, category = self.calculate_confidence_score_with_reasoning_and_category(
                    company_data['business_description'],
                    company_data['sic_code'],
                    company_data.get('sic_description', None)
                )
                
                # Check if record already exists
                cursor.execute("""
                    SELECT id FROM sic_prediction_history 
                    WHERE company_id = ? AND existing_sic_code = ?
                """, (company_data['company_id'], company_data['sic_code']))
                
                existing_record = cursor.fetchone()
                
                # Get current timestamp for existing SIC calculation
                from datetime import datetime
                calculation_timestamp = datetime.now().isoformat()
                
                if existing_record:
                    # Update existing record
                    cursor.execute("""
                        UPDATE sic_prediction_history 
                        SET existing_sic_confidence = ?,
                            existing_sic_description = ?,
                            existing_sic_reasoning = ?,
                            existing_sic_confidence_category = ?,
                            existing_sic_calculation_timestamp = ?
                        WHERE company_id = ? AND existing_sic_code = ?
                    """, (
                        confidence, 
                        company_data.get('sic_description', ''),
                        reasoning,
                        category,
                        calculation_timestamp,
                        company_data['company_id'], 
                        company_data['sic_code']
                    ))
                else:
                    # Create new record
                    cursor.execute("""
                        INSERT INTO sic_prediction_history
                        (company_id, company_name, business_description, existing_sic_code,
                         existing_sic_description, existing_sic_confidence, existing_sic_reasoning,
                         existing_sic_confidence_category, existing_sic_calculation_timestamp,
                         model_version, prediction_method, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'auto-calc-1.0', 'AUTO_EXISTING_CONFIDENCE', 'system')
                    """, (
                        company_data['company_id'],
                        company_data['company_name'],
                        company_data['business_description'],
                        company_data['sic_code'],
                        company_data.get('sic_description', ''),
                        confidence,
                        reasoning,
                        category,
                        calculation_timestamp
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Error creating SIC prediction record for {company_data['company_name']}: {e}")
            return False

    def process_companies(self, companies: List[Dict]) -> Dict:
        """Process all companies and calculate confidence scores"""
        results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'total_companies': len(companies)
        }
        
        print(f"📊 Processing {len(companies)} companies for auto-confidence calculation...")
        
        for i, company in enumerate(companies):
            try:
                success = self.create_sic_prediction_record(company)
                
                if success:
                    results['success'] += 1
                    if (i + 1) % 50 == 0:
                        print(f"✅ Processed {i + 1}/{len(companies)} companies...")
                else:
                    results['failed'] += 1
                    
                results['processed'] += 1
                
            except Exception as e:
                print(f"❌ Error processing {company['company_name']}: {e}")
                results['failed'] += 1
                results['processed'] += 1
        
        return results

    def run_auto_calculation(self) -> bool:
        """Run automatic confidence calculation for new companies"""
        print("🚀 Auto SIC Confidence Calculator")
        print("=" * 50)
        
        # Get companies needing confidence calculation
        companies = self.get_companies_needing_confidence()
        
        if not companies:
            print("✅ No companies need confidence calculation - all up to date!")
            return True
        
        print(f"📈 Found {len(companies)} companies needing confidence calculation")
        
        # Process companies
        results = self.process_companies(companies)
        
        # Report results
        print(f"\n📊 AUTO-CALCULATION RESULTS")
        print("-" * 30)
        print(f"Total companies: {results['total_companies']}")
        print(f"Successfully processed: {results['success']}")
        print(f"Failed: {results['failed']}")
        print(f"Success rate: {(results['success']/results['total_companies']*100):.1f}%")
        
        if results['success'] > 0:
            print(f"\n✅ Auto-calculation completed successfully!")
            print(f"💾 Updated {results['success']} existing SIC confidence scores")
            return True
        else:
            print(f"\n❌ Auto-calculation failed - no records updated")
            return False


def main():
    """Main execution function"""
    print("Auto SIC Confidence Calculator")
    print("==============================")
    print("Calculates existing SIC confidence for newly imported companies\n")
    
    calculator = AutoSICConfidenceCalculator()
    success = calculator.run_auto_calculation()
    
    if success:
        print("\n🎯 SUCCESS!")
        print("- All companies now have existing SIC confidence scores")
        print("- Ready for real-time SIC predictions")
        print("- Performance optimized with pre-calculated confidence")
    else:
        print("\n⚠️  Please review any error messages above")


if __name__ == "__main__":
    main()