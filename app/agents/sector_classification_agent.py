"""
Sector Classification Agent - Suggests correct sector codes using business descriptions.
"""
import sys
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.base_agent import BaseAgent, AgentResult
from app.utils.config_manager import config
from app.utils.logger import logger

@dataclass
class SectorSuggestion:
    """Represents a sector code suggestion."""
    company_number: str
    company_name: str
    current_sic_code: Optional[str]
    suggested_sic_code: str
    suggested_description: str
    confidence: float
    reasoning: str
    business_description: str
    keywords_matched: List[str]

class SectorClassificationAgent(BaseAgent):
    """Agent responsible for suggesting correct sector codes."""
    
    def __init__(self):
        super().__init__("SectorClassificationAgent")
        
        # Load SIC code mappings
        self.sic_mappings = self._load_sic_mappings()
        
        # Initialize keyword patterns for classification
        self.keyword_patterns = self._initialize_keyword_patterns()
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process sector classification for companies with anomalies.
        
        Args:
            data: Dictionary containing companies with sector anomalies
        
        Returns:
            AgentResult with sector classification suggestions
        """
        try:
            self.log_activity("Starting sector classification process")
            
            companies = []
            if isinstance(data, dict) and "companies" in data:
                companies = data["companies"]
            elif isinstance(data, list):
                companies = data
            
            if not companies:
                return self.create_result(
                    success=False,
                    error_message="No company data provided for sector classification"
                )
            
            suggestions = []
            
            for company in companies:
                # Only process companies that need sector classification
                if self._needs_sector_classification(company):
                    suggestion = self._classify_sector(company)
                    if suggestion:
                        suggestions.append(suggestion)
            
            self.log_activity(f"Generated {len(suggestions)} sector classification suggestions")
            
            return self.create_result(
                success=True,
                data={
                    "suggestions": suggestions,
                    "count": len(suggestions)
                },
                confidence=0.8,
                suggestion_count=len(suggestions)
            )
            
        except Exception as e:
            error_msg = f"Sector classification failed: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
    
    def _needs_sector_classification(self, company: Dict[str, Any]) -> bool:
        """Check if company needs sector classification."""
        primary_sic = company.get("primary_sic_code")
        description = company.get("description", "")
        
        # Needs classification if:
        # 1. Missing SIC code
        # 2. Has description but potentially wrong SIC code
        return (not primary_sic) or (description and self._is_potentially_wrong_sic(primary_sic, description))
    
    def _is_potentially_wrong_sic(self, sic_code: str, description: str) -> bool:
        """Check if SIC code might be wrong based on description."""
        if not sic_code or not description:
            return False
        
        # Get expected categories from description
        expected_categories = self._extract_business_categories(description)
        
        # Get current SIC category
        current_category = self._get_sic_category(sic_code)
        
        # Check for mismatch
        if expected_categories and current_category:
            return current_category not in expected_categories
        
        return False
    
    def _classify_sector(self, company: Dict[str, Any]) -> Optional[SectorSuggestion]:
        """Classify the sector for a company based on business description."""
        company_number = company.get("company_number", "")
        company_name = company.get("company_name", "")
        current_sic = company.get("primary_sic_code")
        description = company.get("description", "")
        
        if not description:
            return None
        
        # Analyze description to find best matching SIC code
        best_match = self._find_best_sic_match(description)
        
        if not best_match:
            return None
        
        sic_code, sic_description, confidence, keywords_matched, reasoning = best_match
        
        return SectorSuggestion(
            company_number=company_number,
            company_name=company_name,
            current_sic_code=current_sic,
            suggested_sic_code=sic_code,
            suggested_description=sic_description,
            confidence=confidence,
            reasoning=reasoning,
            business_description=description,
            keywords_matched=keywords_matched
        )
    
    def _find_best_sic_match(self, description: str) -> Optional[Tuple[str, str, float, List[str], str]]:
        """Find the best SIC code match for a business description."""
        description_lower = description.lower()
        
        best_score = 0
        best_match = None
        
        for sic_code, sic_info in self.sic_mappings.items():
            score = 0
            matched_keywords = []
            
            # Check primary keywords
            for keyword in sic_info["keywords"]:
                if keyword.lower() in description_lower:
                    score += 2
                    matched_keywords.append(keyword)
            
            # Check secondary keywords (lower weight)
            for keyword in sic_info.get("secondary_keywords", []):
                if keyword.lower() in description_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Check for negative keywords (disqualifying terms)
            negative_match = False
            for neg_keyword in sic_info.get("negative_keywords", []):
                if neg_keyword.lower() in description_lower:
                    negative_match = True
                    break
            
            if negative_match:
                continue
            
            # Calculate confidence based on score and keyword matches
            if score > 0:
                confidence = min(0.95, (score / max(len(sic_info["keywords"]), 3)) * 0.8 + 0.2)
                
                if score > best_score:
                    best_score = score
                    reasoning = f"Matched keywords: {', '.join(matched_keywords)}. Business description indicates {sic_info['description'][:50]}... activities."
                    best_match = (sic_code, sic_info["description"], confidence, matched_keywords, reasoning)
        
        return best_match
    
    def _extract_business_categories(self, description: str) -> List[str]:
        """Extract business categories from description."""
        categories = set()
        description_lower = description.lower()
        
        category_keywords = {
            "technology": ["software", "technology", "IT", "programming", "development", "digital"],
            "consulting": ["consulting", "advisory", "consultancy", "advice"],
            "finance": ["financial", "finance", "investment", "banking", "insurance"],
            "retail": ["retail", "shop", "store", "selling", "sales"],
            "manufacturing": ["manufacturing", "production", "factory", "industrial"],
            "construction": ["construction", "building", "contractor"],
            "energy": ["energy", "renewable", "solar", "wind", "power"],
            "healthcare": ["healthcare", "medical", "health", "pharmaceutical"],
            "education": ["education", "training", "school", "learning"],
            "transport": ["transport", "logistics", "delivery", "shipping"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                categories.add(category)
        
        return list(categories)
    
    def _get_sic_category(self, sic_code: str) -> Optional[str]:
        """Get the category for a SIC code."""
        if not sic_code:
            return None
        
        # Map SIC code to category based on first digits
        if sic_code.startswith("62") or sic_code.startswith("63"):
            return "technology"
        elif sic_code.startswith("70") or sic_code.startswith("74"):
            return "consulting"
        elif sic_code.startswith("64") or sic_code.startswith("65") or sic_code.startswith("66"):
            return "finance"
        elif sic_code.startswith("47"):
            return "retail"
        elif sic_code.startswith("10") or sic_code.startswith("20") or sic_code.startswith("30"):
            return "manufacturing"
        elif sic_code.startswith("41") or sic_code.startswith("42") or sic_code.startswith("43"):
            return "construction"
        elif sic_code.startswith("35"):
            return "energy"
        elif sic_code.startswith("86") or sic_code.startswith("87"):
            return "healthcare"
        elif sic_code.startswith("85"):
            return "education"
        elif sic_code.startswith("49") or sic_code.startswith("50") or sic_code.startswith("51"):
            return "transport"
        
        return "other"
    
    def _load_sic_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive SIC code mappings based on official UK SIC 2007 data."""
        return {
            # Hospitality (55xx-56xx) - KEY FOR COMPASS GROUP
            "56101": {
                "description": "Licenced restaurants", 
                "keywords": ["restaurant", "dining", "food", "licensed", "alcohol", "catering"]
            },
            "56102": {
                "description": "Unlicenced restaurants and cafes",
                "keywords": ["restaurant", "cafe", "food", "dining", "unlicensed", "catering"]
            },
            "56210": {
                "description": "Event catering activities",
                "keywords": ["catering", "events", "food", "service", "hospitality"]
            },
            
            # Financial Services (64xx-66xx) - KEY FOR HSBC
            "64191": {
                "description": "Banks",
                "keywords": ["bank", "banking", "financial", "services", "lending", "deposit"]
            },
            "64192": {
                "description": "Building societies",
                "keywords": ["building", "society", "mortgage", "savings", "financial"]
            },
            "65110": {
                "description": "Life insurance",
                "keywords": ["insurance", "life", "assurance", "coverage"]
            },
            "65120": {
                "description": "Non-life insurance",
                "keywords": ["insurance", "general", "coverage", "protection"]
            },
            
            # Retail and Wholesale (45xx-47xx) - KEY FOR TESCO, M&S
            "47110": {
                "description": "Retail sale in non-specialised stores with food, beverages or tobacco predominating",
                "keywords": ["retail", "supermarket", "grocery", "food", "general"]
            },
            "47190": {
                "description": "Other retail sale in non-specialised stores",
                "keywords": ["retail", "department", "general", "variety"]
            },
            "47710": {
                "description": "Retail sale of clothing in specialised stores",
                "keywords": ["retail", "clothing", "fashion", "apparel", "garments"]
            },
            "47730": {
                "description": "Dispensing chemist in specialised stores",
                "keywords": ["pharmacy", "chemist", "medicine", "healthcare", "drugs"]
            },
            
            # Information and Communication (58xx-63xx) - KEY FOR BT
            "61100": {
                "description": "Wired telecommunications activities",
                "keywords": ["telecommunications", "wired", "internet", "broadband"]
            },
            "61200": {
                "description": "Wireless telecommunications activities",
                "keywords": ["mobile", "wireless", "telecommunications", "cellular"]
            },
            "62010": {
                "description": "Computer programming activities",
                "keywords": ["programming", "software", "development", "coding", "IT"]
            },
            "62020": {
                "description": "Computer consultancy activities",
                "keywords": ["consulting", "IT", "technology", "advice", "systems"]
            },
            "63110": {
                "description": "Data processing, hosting and related activities",
                "keywords": ["data", "hosting", "processing", "cloud", "IT"]
            },
            
            # Manufacturing - KEY FOR ROLLS-ROYCE
            "30300": {
                "description": "Manufacture of air and spacecraft and related machinery",
                "keywords": ["aircraft", "aerospace", "aviation", "manufacturing", "aerospace engineering"]
            },
            "10110": {
                "description": "Processing and preserving of meat",
                "keywords": ["food", "meat", "processing", "manufacturing"]
            },
            "20110": {
                "description": "Manufacture of industrial gases", 
                "keywords": ["chemicals", "gases", "industrial", "manufacturing"]
            },
            "26110": {
                "description": "Manufacture of electronic components",
                "keywords": ["electronics", "components", "technology", "manufacturing"]
            },
            
            # Professional Services (69xx-75xx)
            "69101": {
                "description": "Barristers at law",
                "keywords": ["legal", "barrister", "law", "advocate", "court"]
            },
            "69102": {
                "description": "Solicitors",
                "keywords": ["legal", "solicitor", "law", "attorney", "advice"]
            },
            "69201": {
                "description": "Accounting and auditing activities",
                "keywords": ["accounting", "audit", "financial", "bookkeeping", "tax"]
            },
            "70220": {
                "description": "Business and other management consultancy activities",
                "keywords": ["consulting", "management", "business", "advisory", "strategy"]
            },
            "71111": {
                "description": "Architectural activities",
                "keywords": ["architecture", "design", "building", "construction", "planning"]
            },
            
            # Transportation (49xx-53xx)
            "49100": {
                "description": "Passenger rail transport, interurban",
                "keywords": ["rail", "passenger", "transport", "railway", "train"]
            },
            "49410": {
                "description": "Freight transport by road",
                "keywords": ["freight", "road", "transport", "trucking", "logistics"]
            },
            "51100": {
                "description": "Passenger air transport",
                "keywords": ["airline", "passenger", "aviation", "air", "transport"]
            },
            "52100": {
                "description": "Warehousing and storage",
                "keywords": ["warehousing", "storage", "logistics", "distribution"]
            },
            
            # Real Estate (68xx)
            "68100": {
                "description": "Buying and selling of own real estate",
                "keywords": ["real estate", "property", "buying", "selling", "development"]
            },
            "68310": {
                "description": "Real estate agencies",
                "keywords": ["estate", "agent", "property", "real estate", "sales"]
            },
            
            # Construction (41xx-43xx)
            "41200": {
                "description": "Construction of residential and non-residential buildings",
                "keywords": ["construction", "building", "residential", "commercial"]
            },
            "42110": {
                "description": "Construction of roads and motorways", 
                "keywords": ["construction", "roads", "infrastructure", "civil"]
            },
            
            # Energy and Utilities (35xx-39xx)
            "35110": {
                "description": "Production of electricity",
                "keywords": ["electricity", "power", "energy", "generation"]
            },
            "36000": {
                "description": "Water collection, treatment and supply",
                "keywords": ["water", "treatment", "supply", "utility"]
            },
            
            # Education and Healthcare
            "85200": {
                "description": "Primary education",
                "keywords": ["education", "primary", "school", "teaching"]
            },
            "86101": {
                "description": "Hospital activities",
                "keywords": ["hospital", "medical", "healthcare", "treatment"]
            },
            "86210": {
                "description": "General medical practice activities",
                "keywords": ["medical", "GP", "healthcare", "practice", "doctor"]
            },
            
            # Agriculture (01xx-03xx)
            "01110": {
                "description": "Growing of cereals (except rice), leguminous crops and oil seeds",
                "keywords": ["farming", "agriculture", "cereals", "crops", "growing", "grain"]
            },
            "01410": {
                "description": "Raising of dairy cattle", 
                "keywords": ["dairy", "cattle", "milk", "farming", "livestock"]
            },
            "03110": {
                "description": "Marine fishing",
                "keywords": ["fishing", "marine", "seafood", "commercial"]
            }
        }
    
    def predict_single_company(self, company_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Predict SIC code for a single company
        
        Args:
            company_data: Dictionary with company information including business description
            
        Returns:
            Dictionary with prediction results or None if no prediction possible
        """
        try:
            # Extract relevant fields
            company_name = company_data.get('Company Name', '')
            business_description = company_data.get('Business Description', '')
            current_sic = company_data.get('UK SIC 2007 Code', '')
            
            if not business_description:
                return {
                    "success": False,
                    "error": "No business description available for prediction",
                    "company_name": company_name
                }
            
            # Find best SIC match
            best_match = self._find_best_sic_match(business_description)
            
            if not best_match:
                return {
                    "success": False,
                    "error": "No suitable SIC code match found",
                    "company_name": company_name
                }
            
            sic_code, sic_description, confidence, keywords_matched, reasoning = best_match
            
            return {
                "success": True,
                "company_name": company_name,
                "current_sic": current_sic,
                "predicted_sic": sic_code,
                "predicted_description": sic_description,
                "confidence": confidence,
                "reasoning": reasoning,
                "keywords_matched": keywords_matched,
                "business_description": business_description[:100] + "..." if len(business_description) > 100 else business_description
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Prediction failed: {str(e)}",
                "company_name": company_name
            }
        """Load SIC code mappings with keywords and descriptions."""
        return {
            # Technology and IT
            "62011": {
                "description": "Ready-made interactive leisure and entertainment software development",
                "category": "technology",
                "keywords": ["software", "game", "entertainment", "interactive", "development"],
                "secondary_keywords": ["programming", "coding", "app"],
                "negative_keywords": ["hardware", "retail"]
            },
            "62012": {
                "description": "Business and domestic software development",
                "category": "technology",
                "keywords": ["software", "development", "programming", "application", "system"],
                "secondary_keywords": ["IT", "technology", "digital", "coding"],
                "negative_keywords": ["hardware", "retail"]
            },
            "62020": {
                "description": "Information technology consultancy activities",
                "category": "technology",
                "keywords": ["IT", "technology", "consultancy", "consulting", "advisory"],
                "secondary_keywords": ["digital", "systems", "technical"],
                "negative_keywords": ["manufacturing", "retail"]
            },
            "63110": {
                "description": "Data processing, hosting and related activities",
                "category": "technology",
                "keywords": ["data", "hosting", "processing", "cloud", "server"],
                "secondary_keywords": ["IT", "technology", "digital"],
                "negative_keywords": ["consulting", "development"]
            },
            
            # Professional Services
            "70210": {
                "description": "Public relations and communication activities",
                "category": "consulting",
                "keywords": ["public relations", "PR", "communication", "marketing", "media"],
                "secondary_keywords": ["advertising", "promotion", "branding"],
                "negative_keywords": ["manufacturing", "retail"]
            },
            "70220": {
                "description": "Business and other management consultancy activities",
                "category": "consulting",
                "keywords": ["consulting", "consultancy", "management", "advisory", "business"],
                "secondary_keywords": ["strategy", "advice", "professional"],
                "negative_keywords": ["manufacturing", "retail"]
            },
            "71200": {
                "description": "Technical testing and analysis",
                "category": "consulting",
                "keywords": ["testing", "analysis", "technical", "inspection", "quality"],
                "secondary_keywords": ["engineering", "consulting", "assessment"],
                "negative_keywords": ["retail", "manufacturing"]
            },
            
            # Financial Services
            "64209": {
                "description": "Other activities of holding companies n.e.c.",
                "category": "finance",
                "keywords": ["holding", "investment", "company", "financial"],
                "secondary_keywords": ["portfolio", "assets", "management"],
                "negative_keywords": ["retail", "manufacturing"]
            },
            "66220": {
                "description": "Activities of insurance agents and brokers",
                "category": "finance",
                "keywords": ["insurance", "financial", "advisory", "broker", "agent"],
                "secondary_keywords": ["investment", "planning", "finance"],
                "negative_keywords": ["manufacturing", "retail"]
            },
            
            # Energy and Environment
            "35110": {
                "description": "Production of electricity",
                "category": "energy",
                "keywords": ["electricity", "power", "generation", "energy"],
                "secondary_keywords": ["renewable", "solar", "wind"],
                "negative_keywords": ["retail", "consulting"]
            },
            "35300": {
                "description": "Steam and air conditioning supply",
                "category": "energy",
                "keywords": ["steam", "heating", "cooling", "HVAC", "energy"],
                "secondary_keywords": ["air conditioning", "climate"],
                "negative_keywords": ["retail", "software"]
            },
            
            # Retail and Wholesale
            "47190": {
                "description": "Other retail sale in non-specialised stores",
                "category": "retail",
                "keywords": ["retail", "store", "shop", "selling", "sales"],
                "secondary_keywords": ["commercial", "trading"],
                "negative_keywords": ["consulting", "software", "energy"]
            },
            "46190": {
                "description": "Agents involved in the sale of a variety of goods",
                "category": "retail",
                "keywords": ["wholesale", "trading", "distribution", "agent", "sales"],
                "secondary_keywords": ["commercial", "broker"],
                "negative_keywords": ["manufacturing", "software"]
            }
        }
    
    def _initialize_keyword_patterns(self) -> Dict[str, List[str]]:
        """Initialize keyword patterns for different business types."""
        return {
            "technology": [
                r'\b(software|programming|development|IT|technology|digital|app|system|platform)\b',
                r'\b(web|mobile|cloud|database|algorithm|AI|machine learning)\b'
            ],
            "consulting": [
                r'\b(consulting|consultancy|advisory|advice|professional services)\b',
                r'\b(strategy|management|business|analysis|planning)\b'
            ],
            "finance": [
                r'\b(financial|finance|investment|banking|insurance|fund)\b',
                r'\b(wealth|portfolio|asset|trading|broker|advisor)\b'
            ],
            "energy": [
                r'\b(energy|renewable|solar|wind|power|electricity|green)\b',
                r'\b(environmental|sustainability|carbon|efficiency)\b'
            ]
        }
