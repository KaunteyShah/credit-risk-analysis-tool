"""
Hybrid Companies House SIC Code Updater

This module implements both methods:
1. Direct lookup by company registration number (existing method)
2. Company name search with address verification (new method)

The hybrid approach maximizes coverage by trying the company number first,
then falling back to name-based search for companies without registration numbers.
"""

import sqlite3
import time
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

from app_modules.apis.companies_house_client import create_companies_house_client
from app_modules.utils.logger import logger

class HybridCompaniesHouseSICUpdater:
    def __init__(self, db_path: str = "data/credit_risk.db", delay_seconds: float = 0.5, batch_size: int = 25):
        """Initialize the hybrid updater."""
        self.db_path = db_path
        self.delay_seconds = delay_seconds
        self.batch_size = batch_size
        self.ch_client = create_companies_house_client()
        
        # Statistics tracking
        self.stats = {
            "total_records": 0,
            "method1_success": 0,  # Company number success
            "method2_success": 0,  # Name search success
            "method1_failed": 0,
            "method2_failed": 0,
            "no_company_number": 0,
            "no_name_match": 0,
            "errors": 0,
            "records_updated": 0
        }
    
    def update_ch_sic_codes_hybrid(self) -> Dict:
        """Update CH SIC codes using hybrid approach."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all records without CH SIC codes
                cursor = conn.cursor()
                query = """
                    SELECT s.id, s.company_id, s.company_name, c.company_number, 
                           c.address_line_1, c.city, c.post_code, c.status
                    FROM sic_prediction_history s
                    LEFT JOIN companies c ON s.company_name = c.company_name
                    WHERE (s.ch_sic_codes IS NULL OR s.ch_sic_codes = '')
                """
                cursor.execute(query)
                records = cursor.fetchall()
                
                self.stats["total_records"] = len(records)
                logger.info(f"Starting hybrid CH SIC update for {len(records)} records")
                
                batch_num = 0
                for i in range(0, len(records), self.batch_size):
                    batch_num += 1
                    batch = records[i:i + self.batch_size]
                    logger.info(f"Processing batch {batch_num}, records {i+1}/{len(records)}")
                    
                    for record in batch:
                        self._process_single_record_hybrid(conn, record)
                        time.sleep(self.delay_seconds)
                
                # Final statistics
                self._log_final_statistics()
                return self.stats
                
        except Exception as e:
            error_msg = f"Hybrid update failed: {str(e)}"
            logger.error(error_msg)
            self.stats["errors"] += 1
            return {"error": error_msg, "stats": self.stats}
    
    def _process_single_record_hybrid(self, conn: sqlite3.Connection, record: Tuple) -> None:
        """Process a single record using hybrid method."""
        record_id, company_id, company_name, company_number, address_line_1, city, post_code, status = record
        
        try:
            sic_codes = None
            method_used = None
            
            # Method 1: Try company number first (if available)
            if company_number and company_number.strip():
                logger.info(f"Method 1: Fetching CH SIC codes for {company_name} ({company_number})")
                sic_codes = self._get_sic_codes_by_number(company_number.strip())
                if sic_codes:
                    method_used = "method1"
                    self.stats["method1_success"] += 1
                    logger.info(f"✅ Method 1 success for {company_name}: CH SIC codes = {sic_codes}")
                else:
                    self.stats["method1_failed"] += 1
                    logger.warning(f"❌ Method 1 failed for {company_name} ({company_number})")
            else:
                self.stats["no_company_number"] += 1
            
            # Method 2: Try name-based search with address matching (if Method 1 failed or no company number)
            if not sic_codes and company_name and company_name.strip():
                logger.info(f"Method 2: Searching by name for {company_name}")
                sic_codes = self._get_sic_codes_by_name_and_address(
                    company_name.strip(), 
                    address_line_1, 
                    city, 
                    post_code
                )
                if sic_codes:
                    method_used = "method2"
                    self.stats["method2_success"] += 1
                    logger.info(f"✅ Method 2 success for {company_name}: CH SIC codes = {sic_codes}")
                else:
                    self.stats["method2_failed"] += 1
                    logger.warning(f"❌ Method 2 failed for {company_name}")
            
            # Update database if SIC codes found
            if sic_codes and method_used:
                self._update_database_record(conn, record_id, sic_codes, method_used)
                self.stats["records_updated"] += 1
            else:
                if not company_name or not company_name.strip():
                    self.stats["no_name_match"] += 1
                    logger.warning(f"No company_name found for record_id {record_id}")
                    
        except Exception as e:
            error_msg = f"Error processing record {record_id} ({company_name}): {str(e)}"
            logger.error(error_msg)
            self.stats["errors"] += 1
    
    def _get_sic_codes_by_number(self, company_number: str) -> Optional[str]:
        """Method 1: Get SIC codes using company registration number."""
        try:
            company_data = self.ch_client.get_company_by_number(company_number)
            if company_data and company_data.get("sic_codes"):
                # 🎯 FIXED: Use only the FIRST SIC code for consistency with sic_codes table format
                # This prevents comma-separated strings and ensures UI display consistency
                sic_codes_list = company_data["sic_codes"]
                if isinstance(sic_codes_list, list) and sic_codes_list:
                    return str(sic_codes_list[0]).strip()  # Return first SIC code only
                else:
                    return str(sic_codes_list).strip() if sic_codes_list else None
        except Exception as e:
            logger.error(f"Error fetching by number {company_number}: {str(e)}")
        return None
    
    def _get_sic_codes_by_name_and_address(self, company_name: str, address_line_1: Optional[str] = None, 
                                         city: Optional[str] = None, post_code: Optional[str] = None) -> Optional[str]:
        """Method 2: Get SIC codes using company name search with address verification."""
        try:
            # Search for companies by name
            search_result = self.ch_client.search_companies(company_name)
            
            if not (search_result.get("success") and search_result.get("data", {}).get("items")):
                return None
            
            search_items = search_result["data"]["items"]
            logger.info(f"Found {len(search_items)} potential matches for '{company_name}'")
            
            # Find the best match using multiple criteria
            best_match = self._find_best_company_match(
                search_items, company_name, address_line_1, city, post_code
            )
            
            if best_match:
                company_number = best_match.get("company_number")
                if company_number:
                    logger.info(f"Best match: {best_match.get('title')} ({company_number})")
                    
                    # Get full company data for the best match
                    company_data = self.ch_client.get_company_by_number(company_number)
                    if company_data and company_data.get("sic_codes"):
                        # 🎯 FIXED: Use only the FIRST SIC code for consistency with sic_codes table format
                        # This prevents comma-separated strings and ensures UI display consistency
                        sic_codes_list = company_data["sic_codes"]
                        if isinstance(sic_codes_list, list) and sic_codes_list:
                            return str(sic_codes_list[0]).strip()  # Return first SIC code only
                        else:
                            return str(sic_codes_list).strip() if sic_codes_list else None
            
        except Exception as e:
            logger.error(f"Error in name-based search for '{company_name}': {str(e)}")
        
        return None
    
    def _find_best_company_match(self, search_items: List[Dict], target_name: str,
                               target_address: Optional[str] = None, target_city: Optional[str] = None, 
                               target_postcode: Optional[str] = None) -> Optional[Dict]:
        """Find exact matching company from search results using exact name matching with suffix variations."""
        
        if not search_items:
            return None
        
        # Generate all possible exact variations of the target name
        target_variations = self._generate_name_variations(target_name)
        logger.info(f"Generated {len(target_variations)} name variations for '{target_name}'")
        for variation in target_variations[:5]:  # Show first 5 variations
            logger.debug(f"  Variation: '{variation}'")
        
        exact_matches = []
        
        # Check each search result against all target variations
        for item in search_items:
            item_name = item.get("title", "")
            item_variations = self._generate_name_variations(item_name)
            
            # Check if any target variation matches any item variation (exact match)
            match_found = False
            for target_var in target_variations:
                for item_var in item_variations:
                    if target_var == item_var:
                        logger.info(f"✅ Exact match found: '{item_name}' matches '{target_name}'")
                        logger.debug(f"   Matched variation: '{target_var}' == '{item_var}'")
                        exact_matches.append(item)
                        match_found = True
                        break
                if match_found:
                    break
        
        if not exact_matches:
            logger.warning(f"No exact name matches found for '{target_name}'")
            return None
        
        # Remove duplicates
        unique_matches = []
        seen_company_numbers = set()
        for match in exact_matches:
            company_number = match.get("company_number")
            if company_number not in seen_company_numbers:
                unique_matches.append(match)
                seen_company_numbers.add(company_number)
        
        exact_matches = unique_matches
        
        # If only one exact match, return it
        if len(exact_matches) == 1:
            logger.info(f"Single exact match found: {exact_matches[0].get('title')}")
            return exact_matches[0]
        
        # Multiple exact matches - use address to disambiguate
        logger.info(f"Found {len(exact_matches)} unique exact name matches, using address to disambiguate")
        return self._disambiguate_by_address(exact_matches, target_address, target_city, target_postcode)
    
    def _disambiguate_by_address(self, exact_matches: List[Dict], target_address: Optional[str] = None,
                                target_city: Optional[str] = None, target_postcode: Optional[str] = None) -> Optional[Dict]:
        """Use address information to pick the correct company when multiple exact name matches exist."""
        
        if not target_address and not target_city and not target_postcode:
            logger.warning("No address information available for disambiguation, returning first match")
            return exact_matches[0]
        
        logger.info(f"Using address to disambiguate between {len(exact_matches)} exact matches")
        logger.info(f"Target address: {target_address}, City: {target_city}, Postcode: {target_postcode}")
        
        # Try exact address matching first
        for match in exact_matches:
            match_address = match.get("address", {})
            match_addr_line = match_address.get("address_line_1", "")
            match_city = match_address.get("locality", "") 
            match_postcode = match_address.get("postal_code", "")
            
            logger.debug(f"Checking {match.get('title')}: {match_addr_line}, {match_city}, {match_postcode}")
            
            # Exact postcode match (highest priority)
            if target_postcode and match_postcode:
                if self._normalize_postcode(target_postcode) == self._normalize_postcode(match_postcode):
                    logger.info(f"✅ Found exact postcode match: {match.get('title')} ({match_postcode})")
                    return match
            
            # Exact city match with address similarity
            if target_city and match_city:
                if target_city.upper().strip() == match_city.upper().strip():
                    if target_address and match_addr_line:
                        if self._addresses_similar(target_address, match_addr_line):
                            logger.info(f"✅ Found city + address match: {match.get('title')}")
                            return match
                    else:
                        logger.info(f"✅ Found exact city match: {match.get('title')} ({match_city})")
                        return match
        
        # If no exact matches, return first one
        logger.warning("No address-based match found, returning first exact name match")
        return exact_matches[0]
    
    def _addresses_similar(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are similar (exact or one contains the other)."""
        if not addr1 or not addr2:
            return False
        
        # Normalize addresses
        norm_addr1 = self._normalize_address(addr1).upper()
        norm_addr2 = self._normalize_address(addr2).upper()
        
        # Exact match
        if norm_addr1 == norm_addr2:
            return True
        
        # One contains the other (partial match)
        if norm_addr1 in norm_addr2 or norm_addr2 in norm_addr1:
            return True
        
        return False
    
    def _calculate_address_score(self, item: Dict, target_address: Optional[str] = None,
                               target_city: Optional[str] = None, target_postcode: Optional[str] = None) -> float:
        """Calculate address-only match score for exact name matches."""
        
        score = 0.0
        weight_address = 0.5   # Address matching (50%)
        weight_city = 0.3      # City matching (30%)
        weight_postcode = 0.2  # Postcode matching (20%)
        
        item_address = item.get("address", {})
        
        # Address matching
        if item_address and target_address:
            address_similarity = self._address_similarity(
                item_address.get("address_line_1", ""),
                target_address
            )
            score += address_similarity * weight_address
        
        # City matching  
        if item_address and target_city:
            city_similarity = self._address_similarity(
                item_address.get("locality", "") or "",
                target_city
            )
            score += city_similarity * weight_city
        
        # Postcode matching (exact match required)
        if item_address and target_postcode:
            item_postcode = self._normalize_postcode(item_address.get("postal_code", ""))
            target_postcode_norm = self._normalize_postcode(target_postcode)
            
            if item_postcode and target_postcode_norm and item_postcode == target_postcode_norm:
                score += 1.0 * weight_postcode  # Exact postcode match
        
        return score
    
    def _address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between address components."""
        if not addr1 or not addr2:
            return 0.0
        
        # Normalize both addresses
        norm_addr1 = self._normalize_address(addr1).lower()
        norm_addr2 = self._normalize_address(addr2).lower()
        
        # Exact match
        if norm_addr1 == norm_addr2:
            return 1.0
        
        # Check if one contains the other (partial match)
        if norm_addr1 in norm_addr2 or norm_addr2 in norm_addr1:
            return 0.8
        
        # Use string similarity for partial matches
        return self._string_similarity(norm_addr1, norm_addr2)
    
    def _generate_name_variations(self, name: str) -> List[str]:
        """Generate all possible exact variations of a company name with different suffix formats."""
        if not name:
            return []
        
        # Start with the original name
        variations = set()
        
        # Normalize base: uppercase, clean punctuation, normalize spaces
        base_name = name.upper().strip()
        base_name = re.sub(r'\s+', ' ', base_name)  # normalize spaces
        
        # Define suffix mappings - each list contains equivalent formats
        suffix_groups = [
            ["PLC", "P.L.C.", "P L C", "PUBLIC LIMITED COMPANY"],
            ["LIMITED", "LTD", "L.T.D.", "L T D"],  
            ["GROUP", "GRP"],
            ["HOLDINGS", "HOLDING", "HLDGS"],
            ["COMPANY", "CO", "C O"],
            ["CORPORATION", "CORP"],
            ["THE"],
            ["INC", "INCORPORATED"],
            ["LLC"]
        ]
        
        # Try to identify and replace suffixes
        for suffix_group in suffix_groups:
            for suffix in suffix_group:
                # Check if name ends with this suffix (with word boundary)
                pattern = rf'\b{re.escape(suffix)}\.?\s*$'
                if re.search(pattern, base_name):
                    # Get the core name without this suffix
                    core_name = re.sub(pattern, '', base_name).strip()
                    
                    # Add variations with all equivalent suffixes  
                    for alt_suffix in suffix_group:
                        variations.add(f"{core_name} {alt_suffix}".strip())
                    
                    # Also add the core name without any suffix
                    if core_name:
                        variations.add(core_name)
                    break
        
        # If no suffix was found, add the cleaned original name
        if not variations:
            # Remove punctuation and normalize
            clean_name = re.sub(r'[^\w\s]', ' ', base_name)
            clean_name = ' '.join(clean_name.split())
            variations.add(clean_name)
        
        # Convert to list and sort for consistency
        result = sorted(list(variations))
        
        return result
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for exact comparison."""
        if not name:
            return ""
        
        # Convert to uppercase
        name = name.upper()
        
        # Remove punctuation first (before suffix removal)
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Remove common company suffixes
        suffixes = [
            "PUBLIC LIMITED COMPANY", "PLC", "P L C", 
            "LIMITED", "LTD", "L T D",
            "GROUP", "HOLDINGS", "HOLDING", 
            "THE", "COMPANY", "CO", 
            "CORPORATION", "CORP", "INC", "LLC"
        ]
        
        for suffix in suffixes:
            # Use word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(suffix)}\b'
            name = re.sub(pattern, '', name)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name.strip()
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for comparison."""
        if not address:
            return ""
        return re.sub(r'[^\w\s]', ' ', address.upper()).strip()
    
    def _normalize_postcode(self, postcode: str) -> str:
        """Normalize postcode for comparison."""
        if not postcode:
            return ""
        return re.sub(r'\s+', '', postcode.upper())
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _update_database_record(self, conn: sqlite3.Connection, record_id: int, 
                              sic_codes: str, method_used: str) -> None:
        """Update database record with CH SIC codes."""
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sic_prediction_history SET ch_sic_codes = ? WHERE id = ?",
                (sic_codes, record_id)
            )
            conn.commit()
            
            # Log which method was successful
            method_label = "Method 1 (Company Number)" if method_used == "method1" else "Method 2 (Name + Address)"
            logger.info(f"Updated record {record_id} using {method_label}: {sic_codes}")
            
        except Exception as e:
            logger.error(f"Error updating record {record_id}: {str(e)}")
    
    def _log_final_statistics(self) -> None:
        """Log comprehensive final statistics."""
        logger.info("""
🎉 Hybrid Companies House SIC Update Complete!
📊 Statistics:
  - Total records processed: {}
  - Method 1 (Company Number) successes: {}
  - Method 2 (Name + Address) successes: {}
  - Method 1 failures: {}
  - Method 2 failures: {}
  - Records without company number: {}
  - Records without name: {}
  - Total records updated: {}
  - Errors: {}
        """.format(
            self.stats["total_records"],
            self.stats["method1_success"], 
            self.stats["method2_success"],
            self.stats["method1_failed"],
            self.stats["method2_failed"], 
            self.stats["no_company_number"],
            self.stats["no_name_match"],
            self.stats["records_updated"],
            self.stats["errors"]
        ))
        
        if self.stats["total_records"] > 0:
            method1_success_rate = (self.stats["method1_success"] / 
                                  (self.stats["method1_success"] + self.stats["method1_failed"])) * 100 if (self.stats["method1_success"] + self.stats["method1_failed"]) > 0 else 0
            
            method2_success_rate = (self.stats["method2_success"] / 
                                  (self.stats["method2_success"] + self.stats["method2_failed"])) * 100 if (self.stats["method2_success"] + self.stats["method2_failed"]) > 0 else 0
            
            overall_success_rate = (self.stats["records_updated"] / self.stats["total_records"]) * 100
            
            logger.info(f"""
📈 Success Rates:
  - Method 1 success rate: {method1_success_rate:.1f}%
  - Method 2 success rate: {method2_success_rate:.1f}%
  - Overall coverage: {overall_success_rate:.1f}%
            """)

def main():
    """Main function to run the hybrid updater."""
    updater = HybridCompaniesHouseSICUpdater()
    results = updater.update_ch_sic_codes_hybrid()
    
    print("\n✅ Hybrid Update completed!")
    print(f"📈 Final Statistics: {results}")

if __name__ == "__main__":
    main()