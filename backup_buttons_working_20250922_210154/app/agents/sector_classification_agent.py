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
                    reasoning = f"Matched keywords: {', '.join(matched_keywords)}. Business description indicates {sic_info['category']} activities."
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
        """Load SIC code mappings with keywords and categories."""
        # Enhanced SIC mappings with real UK SIC codes
        return {
            # Technology & IT Services
            "62020": {
                "description": "Information technology consultancy activities",
                "category": "technology",
                "keywords": ["software", "IT", "consultancy", "technology", "digital", "programming", "development"],
                "secondary_keywords": ["tech", "computer", "systems", "solutions"],
                "negative_keywords": []
            },
            "62090": {
                "description": "Other information technology and computer service activities",
                "category": "technology", 
                "keywords": ["computer", "IT services", "technology", "software", "systems"],
                "secondary_keywords": ["tech support", "maintenance", "hardware"],
                "negative_keywords": []
            },
            "63110": {
                "description": "Data processing, hosting and related activities",
                "category": "technology",
                "keywords": ["data", "hosting", "cloud", "server", "database"],
                "secondary_keywords": ["processing", "storage", "analytics"],
                "negative_keywords": []
            },
            
            # Professional Services
            "70220": {
                "description": "Business and other management consultancy activities",
                "category": "consulting",
                "keywords": ["consulting", "management", "advisory", "business", "strategy"],
                "secondary_keywords": ["consultancy", "advice", "planning"],
                "negative_keywords": []
            },
            "69201": {
                "description": "Accounting and auditing activities",
                "category": "finance",
                "keywords": ["accounting", "audit", "bookkeeping", "finance", "tax"],
                "secondary_keywords": ["accounts", "financial", "taxation"],
                "negative_keywords": []
            },
            "69202": {
                "description": "Tax consultancy",
                "category": "finance",
                "keywords": ["tax", "taxation", "VAT", "PAYE", "consultancy"],
                "secondary_keywords": ["advice", "compliance", "returns"],
                "negative_keywords": []
            },
            
            # Retail & Commerce
            "47190": {
                "description": "Other retail sale in non-specialised stores",
                "category": "retail",
                "keywords": ["retail", "shop", "store", "selling", "sales", "merchandise"],
                "secondary_keywords": ["goods", "products", "consumer"],
                "negative_keywords": ["wholesale", "manufacturing"]
            },
            "47910": {
                "description": "Retail sale via mail order houses or via Internet",
                "category": "retail",
                "keywords": ["online", "e-commerce", "internet", "mail order", "retail"],
                "secondary_keywords": ["website", "digital", "web"],
                "negative_keywords": []
            },
            
            # Manufacturing
            "32990": {
                "description": "Other manufacturing n.e.c.",
                "category": "manufacturing",
                "keywords": ["manufacturing", "production", "factory", "industrial", "maker"],
                "secondary_keywords": ["assembly", "fabrication", "goods"],
                "negative_keywords": ["service", "consulting"]
            },
            "10890": {
                "description": "Manufacture of other food products n.e.c.",
                "category": "manufacturing",
                "keywords": ["food", "manufacturing", "production", "processing"],
                "secondary_keywords": ["edible", "consumable", "nutrition"],
                "negative_keywords": ["restaurant", "catering"]
            },
            
            # Construction
            "41202": {
                "description": "Construction of domestic buildings",
                "category": "construction",
                "keywords": ["construction", "building", "homes", "residential", "houses"],
                "secondary_keywords": ["property", "development", "contractor"],
                "negative_keywords": []
            },
            "43999": {
                "description": "Other specialised construction activities n.e.c.",
                "category": "construction",
                "keywords": ["construction", "building", "contractor", "specialist"],
                "secondary_keywords": ["installation", "maintenance", "repair"],
                "negative_keywords": []
            },
            
            # Energy & Environment
            "35110": {
                "description": "Production of electricity",
                "category": "energy",
                "keywords": ["electricity", "power", "energy", "generation"],
                "secondary_keywords": ["renewable", "solar", "wind"],
                "negative_keywords": []
            },
            "35300": {
                "description": "Steam and air conditioning supply",
                "category": "energy",
                "keywords": ["heating", "cooling", "HVAC", "air conditioning", "steam"],
                "secondary_keywords": ["climate", "temperature"],
                "negative_keywords": []
            },
            
            # Transport & Logistics
            "49410": {
                "description": "Freight transport by road",
                "category": "transport",
                "keywords": ["transport", "freight", "logistics", "delivery", "haulage"],
                "secondary_keywords": ["shipping", "cargo", "goods"],
                "negative_keywords": ["passenger"]
            },
            "52290": {
                "description": "Other transportation support activities",
                "category": "transport",
                "keywords": ["transport", "logistics", "warehousing", "storage"],
                "secondary_keywords": ["distribution", "supply chain"],
                "negative_keywords": []
            },
            
            # Healthcare
            "86900": {
                "description": "Other human health activities",
                "category": "healthcare",
                "keywords": ["health", "medical", "healthcare", "treatment", "therapy"],
                "secondary_keywords": ["wellness", "care", "clinical"],
                "negative_keywords": []
            },
            "75000": {
                "description": "Veterinary activities",
                "category": "healthcare",
                "keywords": ["veterinary", "animal", "pet", "vet"],
                "secondary_keywords": ["care", "medical", "treatment"],
                "negative_keywords": ["human"]
            },
            
            # Education & Training
            "85590": {
                "description": "Other education n.e.c.",
                "category": "education",
                "keywords": ["education", "training", "teaching", "learning", "course"],
                "secondary_keywords": ["school", "academy", "tuition"],
                "negative_keywords": []
            },
            
            # Finance & Insurance
            "64209": {
                "description": "Other activities of credit granting",
                "category": "finance",
                "keywords": ["finance", "credit", "lending", "loan", "financial"],
                "secondary_keywords": ["investment", "funding", "capital"],
                "negative_keywords": []
            },
            "66190": {
                "description": "Other activities auxiliary to financial services",
                "category": "finance",
                "keywords": ["financial", "insurance", "investment", "advisory"],
                "secondary_keywords": ["wealth", "portfolio", "broker"],
                "negative_keywords": []
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
