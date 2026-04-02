"""
Ticker Symbol Resolution Service
Converts company names/numbers to stock ticker symbols for UK markets
"""

import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class TickerResolution:
    ticker: Optional[str]
    confidence: float
    method: str
    market: str  # LSE, AIM, etc.
    
class UKTickerResolver:
    """Resolve UK company names to ticker symbols"""
    
    def __init__(self):
        # FTSE 100 companies (high confidence mappings)
        self.ftse_100_map = {
            "tesco": "TSCO.L",
            "british petroleum": "BP.L",
            "shell": "SHEL.L", 
            "lloyds banking group": "LLOY.L",
            "barclays": "BARC.L",
            "hsbc": "HSBA.L",
            "vodafone": "VOD.L",
            "british american tobacco": "BATS.L",
            "astrazeneca": "AZN.L",
            "rio tinto": "RIO.L",
            "unilever": "ULVR.L",
            "glencore": "GLEN.L",
            "national grid": "NG.L",
            "sainsbury": "SBRY.L",
            "marks spencer": "MKS.L",
            # Add more as needed...
        }
        
        # Common company name patterns and variations
        self.name_normalizers = [
            (r'\bplc\b', ''),
            (r'\blimited\b', ''),  
            (r'\bltd\b', ''),
            (r'\bgroup\b', ''),
            (r'\bholdings\b', ''),
            (r'\binternational\b', ''),
            (r'\s+', ' '),  # Multiple spaces to single
        ]
    
    def normalize_company_name(self, name: str) -> str:
        """Normalize company name for ticker lookup"""
        normalized = name.lower().strip()
        
        for pattern, replacement in self.name_normalizers:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        return normalized.strip()
    
    def resolve_ticker_fuzzy_match(self, company_name: str) -> TickerResolution:
        """Find ticker using fuzzy matching against known companies"""
        normalized_name = self.normalize_company_name(company_name)
        
        # Direct match
        if normalized_name in self.ftse_100_map:
            return TickerResolution(
                ticker=self.ftse_100_map[normalized_name],
                confidence=0.95,
                method="direct_match",
                market="LSE"
            )
        
        # Partial match (contains)
        for known_name, ticker in self.ftse_100_map.items():
            if known_name in normalized_name or normalized_name in known_name:
                confidence = 0.7 if len(normalized_name) > 5 else 0.5
                return TickerResolution(
                    ticker=ticker,
                    confidence=confidence,
                    method="partial_match", 
                    market="LSE"
                )
        
        return TickerResolution(None, 0.0, "no_match", "")
    
    def resolve_ticker_api_search(self, company_name: str) -> TickerResolution:
        """Use Yahoo Finance search API to find ticker"""
        try:
            import yfinance as yf
            
            # Search for company
            search_results = yf.search(company_name, max_results=5)
            
            if search_results and len(search_results) > 0:
                # Look for London Stock Exchange listings (.L suffix)
                for result in search_results:
                    symbol = result.get('symbol', '')
                    name = result.get('longname', '')
                    
                    if symbol.endswith('.L'):  # LSE listing
                        confidence = 0.8 if company_name.lower() in name.lower() else 0.6
                        return TickerResolution(
                            ticker=symbol,
                            confidence=confidence,
                            method="yfinance_search",
                            market="LSE"
                        )
                
                # Fallback to first result if no .L found
                first_result = search_results[0]
                return TickerResolution(
                    ticker=first_result.get('symbol'),
                    confidence=0.4,  # Lower confidence for non-UK listings
                    method="yfinance_fallback",
                    market="OTHER"
                )
        
        except Exception:
            pass
        
        return TickerResolution(None, 0.0, "api_failed", "")
    
    def resolve_ticker(self, company_name: str, companies_house_number: str = None) -> TickerResolution:
        """Main method: resolve ticker using multiple methods"""
        
        # Method 1: Fuzzy match against known tickers (fastest, most reliable)
        fuzzy_result = self.resolve_ticker_fuzzy_match(company_name)
        if fuzzy_result.confidence >= 0.7:
            return fuzzy_result
        
        # Method 2: API search (slower but broader coverage)  
        api_result = self.resolve_ticker_api_search(company_name)
        if api_result.confidence >= 0.6:
            return api_result
        
        # Method 3: Return best result if any found
        if fuzzy_result.confidence > api_result.confidence:
            return fuzzy_result
        elif api_result.confidence > 0:
            return api_result
        else:
            return TickerResolution(None, 0.0, "not_found", "")

# Usage example:
def example_usage():
    resolver = UKTickerResolver()
    
    test_companies = [
        "Tesco PLC",
        "British Petroleum Company plc", 
        "Lloyds Banking Group plc",
        "Some Private Company Ltd"  # Should not find ticker
    ]
    
    for company in test_companies:
        result = resolver.resolve_ticker(company)
        print(f"{company} → {result.ticker} ({result.confidence:.2f} via {result.method})")

if __name__ == "__main__":
    example_usage()