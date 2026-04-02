"""
Turnover Estimation Agent - Proposes turnover corrections using alternative data.
"""
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math

# Add the parent directory to sys.path to import modules

from ..agents.base_agent import BaseAgent, AgentResult
from ..utils.config_manager import config
from ..utils.logger import logger

@dataclass
class TurnoverSuggestion:
    """Represents a turnover estimation suggestion."""
    company_number: str
    company_name: str
    current_turnover: Optional[float]
    suggested_turnover: float
    confidence: float
    reasoning: str
    estimation_method: str
    data_sources: List[str]
    range_min: float
    range_max: float

class TurnoverEstimationAgent(BaseAgent):
    """Agent responsible for estimating turnover based on alternative data."""
    
    def __init__(self):
        super().__init__("TurnoverEstimationAgent")
        
        # Industry benchmarks (simplified for demo)
        self.industry_benchmarks = self._load_industry_benchmarks()
        
        # Company size indicators
        self.size_indicators = self._load_size_indicators()
        
        # Estimation models
        self.estimation_models = self._initialize_estimation_models()
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process turnover estimation for companies with turnover anomalies.
        
        Args:
            data: Dictionary containing companies with turnover anomalies
        
        Returns:
            AgentResult with turnover estimation suggestions
        """
        try:
            self.log_activity("Starting turnover estimation process")
            
            companies = []
            if isinstance(data, dict) and "companies" in data:
                companies = data["companies"]
            elif isinstance(data, list):
                companies = data
            
            if not companies:
                return self.create_result(
                    success=False,
                    error_message="No company data provided for turnover estimation"
                )
            
            suggestions = []
            
            for company in companies:
                # Only process companies that need turnover estimation
                if self._needs_turnover_estimation(company):
                    suggestion = self._estimate_turnover(company)
                    if suggestion:
                        suggestions.append(suggestion)
            
            self.log_activity(f"Generated {len(suggestions)} turnover estimation suggestions")
            
            return self.create_result(
                success=True,
                data={
                    "suggestions": suggestions,
                    "count": len(suggestions)
                },
                confidence=0.7,
                suggestion_count=len(suggestions)
            )
            
        except Exception as e:
            error_msg = f"Turnover estimation failed: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
    
    def _needs_turnover_estimation(self, company: Dict[str, Any]) -> bool:
        """Check if company needs turnover estimation."""
        turnover = company.get("turnover")
        
        # Needs estimation if:
        # 1. Missing turnover
        # 2. Negative turnover
        # 3. Zero turnover for active company
        # 4. Unrealistic turnover values
        return (
            turnover is None or 
            turnover < 0 or 
            (turnover == 0 and company.get("company_status") == "active") or
            self._is_unrealistic_turnover(turnover, company)
        )
    
    def _is_unrealistic_turnover(self, turnover: float, company: Dict[str, Any]) -> bool:
        """Check if turnover value is unrealistic."""
        if turnover is None:
            return False
        
        # Very high turnover might be unrealistic for some company types
        if turnover > 10000000000:  # 10 billion
            return True
        
        # Very low turnover for established companies might be unrealistic
        company_age = self._calculate_company_age(company.get("date_of_creation"))
        if company_age and company_age > 5 and turnover < 1000:
            return True
        
        return False
    
    def _estimate_turnover(self, company: Dict[str, Any]) -> Optional[TurnoverSuggestion]:
        """Estimate turnover for a company using various methods."""
        company_number = company.get("company_number", "")
        company_name = company.get("company_name", "")
        current_turnover = company.get("turnover")
        
        # Try multiple estimation methods
        estimates = []
        
        # Method 1: Industry benchmark estimation
        industry_estimate = self._estimate_by_industry(company)
        if industry_estimate:
            estimates.append(industry_estimate)
        
        # Method 2: Company size estimation
        size_estimate = self._estimate_by_size(company)
        if size_estimate:
            estimates.append(size_estimate)
        
        # Method 3: Business description analysis
        description_estimate = self._estimate_by_description(company)
        if description_estimate:
            estimates.append(description_estimate)
        
        # Method 4: Age-based estimation
        age_estimate = self._estimate_by_age(company)
        if age_estimate:
            estimates.append(age_estimate)
        
        if not estimates:
            return None
        
        # Combine estimates using weighted average
        final_estimate = self._combine_estimates(estimates)
        
        if not final_estimate:
            return None
        
        turnover, confidence, method, sources, reasoning, range_min, range_max = final_estimate
        
        return TurnoverSuggestion(
            company_number=company_number,
            company_name=company_name,
            current_turnover=current_turnover,
            suggested_turnover=turnover,
            confidence=confidence,
            reasoning=reasoning,
            estimation_method=method,
            data_sources=sources,
            range_min=range_min,
            range_max=range_max
        )
    
    def _estimate_by_industry(self, company: Dict[str, Any]) -> Optional[Tuple[float, float, str, List[str], str]]:
        """Estimate turnover based on industry benchmarks."""
        sic_code = company.get("primary_sic_code")
        if not sic_code:
            return None
        
        # Get industry category
        industry = self._get_industry_from_sic(sic_code)
        if industry not in self.industry_benchmarks:
            return None
        
        benchmark = self.industry_benchmarks[industry]
        
        # Base estimate on median turnover for industry
        estimated_turnover = benchmark["median_turnover"]
        confidence = 0.6
        
        sources = ["industry_benchmarks", "sic_code_analysis"]
        reasoning = f"Based on {industry} industry median turnover of £{estimated_turnover:,.0f}"
        
        return (estimated_turnover, confidence, "industry_benchmark", sources, reasoning)
    
    def _estimate_by_size(self, company: Dict[str, Any]) -> Optional[Tuple[float, float, str, List[str], str]]:
        """Estimate turnover based on company size indicators."""
        # Use various size indicators to estimate turnover
        size_score = 0
        size_factors = []
        
        # Factor 1: Company type
        company_type = company.get("company_type", "")
        if "public" in company_type.lower():
            size_score += 3
            size_factors.append("public company")
        elif "private" in company_type.lower():
            size_score += 1
            size_factors.append("private company")
        
        # Factor 2: Company age
        age = self._calculate_company_age(company.get("date_of_creation"))
        if age:
            if age >= 10:
                size_score += 2
                size_factors.append(f"{age} years established")
            elif age >= 5:
                size_score += 1
                size_factors.append(f"{age} years established")
        
        # Factor 3: Business description complexity
        description = company.get("description", "")
        if len(description) > 100:
            size_score += 1
            size_factors.append("detailed business description")
        
        # Map size score to turnover estimate
        if size_score >= 5:
            estimated_turnover = 2000000  # £2M
            confidence = 0.7
        elif size_score >= 3:
            estimated_turnover = 800000   # £800K
            confidence = 0.6
        elif size_score >= 1:
            estimated_turnover = 300000   # £300K
            confidence = 0.5
        else:
            return None
        
        sources = ["company_profile", "establishment_data"]
        reasoning = f"Size indicators: {', '.join(size_factors)} suggest {self._get_size_category(estimated_turnover)} company"
        
        return (estimated_turnover, confidence, "size_analysis", sources, reasoning)
    
    def _estimate_by_description(self, company: Dict[str, Any]) -> Optional[Tuple[float, float, str, List[str], str]]:
        """Estimate turnover based on business description analysis."""
        description = company.get("description", "")
        if not description:
            return None
        
        description_lower = description.lower()
        
        # High-value keywords
        high_value_keywords = ["consulting", "technology", "software", "financial", "investment", "professional"]
        medium_value_keywords = ["services", "advisory", "management", "solutions"]
        low_value_keywords = ["retail", "trading", "sales"]
        
        high_count = sum(1 for keyword in high_value_keywords if keyword in description_lower)
        medium_count = sum(1 for keyword in medium_value_keywords if keyword in description_lower)
        low_count = sum(1 for keyword in low_value_keywords if keyword in description_lower)
        
        if high_count >= 2:
            estimated_turnover = 1200000
            confidence = 0.65
            reasoning = "High-value service keywords suggest premium business model"
        elif high_count >= 1 or medium_count >= 2:
            estimated_turnover = 600000
            confidence = 0.6
            reasoning = "Professional service keywords suggest mid-market positioning"
        elif medium_count >= 1 or low_count >= 1:
            estimated_turnover = 250000
            confidence = 0.5
            reasoning = "Business description suggests standard commercial operation"
        else:
            return None
        
        sources = ["business_description_analysis", "keyword_analysis"]
        
        return (estimated_turnover, confidence, "description_analysis", sources, reasoning)
    
    def _estimate_by_age(self, company: Dict[str, Any]) -> Optional[Tuple[float, float, str, List[str], str]]:
        """Estimate turnover based on company age and growth patterns."""
        age = self._calculate_company_age(company.get("date_of_creation"))
        if not age:
            return None
        
        # Age-based estimation with growth curve
        if age <= 1:
            base_turnover = 50000
            confidence = 0.4
        elif age <= 3:
            base_turnover = 200000
            confidence = 0.5
        elif age <= 7:
            base_turnover = 500000
            confidence = 0.6
        elif age <= 15:
            base_turnover = 800000
            confidence = 0.65
        else:
            base_turnover = 1000000
            confidence = 0.6
        
        sources = ["company_age_analysis", "business_lifecycle_models"]
        reasoning = f"Company established {age} years ago, typical growth trajectory suggests £{base_turnover:,.0f} turnover"
        
        return (base_turnover, confidence, "age_analysis", sources, reasoning)
    
    def _combine_estimates(self, estimates: List[Tuple[float, float, str, List[str], str]]) -> Optional[Tuple[float, float, str, List[str], str, float, float]]:
        """Combine multiple estimates using weighted average."""
        if not estimates:
            return None
        
        # Calculate weighted average
        total_weight = sum(estimate[1] for estimate in estimates)  # Sum of confidences
        weighted_sum = sum(estimate[0] * estimate[1] for estimate in estimates)  # Weighted turnover sum
        
        final_turnover = weighted_sum / total_weight
        
        # Calculate final confidence as average of individual confidences
        final_confidence = total_weight / len(estimates)
        
        # Combine methods and sources
        methods = [estimate[2] for estimate in estimates]
        all_sources = []
        for estimate in estimates:
            all_sources.extend(estimate[3])
        unique_sources = list(set(all_sources))
        
        # Create combined reasoning
        reasoning = f"Combined estimation using {len(estimates)} methods: {', '.join(methods)}"
        
        # Calculate range (±30% of estimate)
        range_factor = 0.3
        range_min = final_turnover * (1 - range_factor)
        range_max = final_turnover * (1 + range_factor)
        
        return (final_turnover, final_confidence, "combined_analysis", unique_sources, reasoning, range_min, range_max)
    
    def _calculate_company_age(self, creation_date: str) -> Optional[int]:
        """Calculate company age in years."""
        if not creation_date:
            return None
        
        try:
            from datetime import datetime
            created = datetime.strptime(creation_date, "%Y-%m-%d")
            today = datetime.now()
            age = (today - created).days // 365
            return max(0, age)
        except (ValueError, TypeError):
            return None
    
    def _get_industry_from_sic(self, sic_code: str) -> str:
        """Map SIC code to industry category."""
        if not sic_code:
            return "other"
        
        # Map based on SIC code prefixes
        if sic_code.startswith(("62", "63")):
            return "technology"
        elif sic_code.startswith(("70", "71", "74")):
            return "professional_services"
        elif sic_code.startswith(("64", "65", "66")):
            return "financial_services"
        elif sic_code.startswith(("47", "46")):
            return "retail_wholesale"
        elif sic_code.startswith(("10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33")):
            return "manufacturing"
        elif sic_code.startswith(("41", "42", "43")):
            return "construction"
        elif sic_code.startswith("35"):
            return "energy"
        else:
            return "other"
    
    def _get_size_category(self, turnover: float) -> str:
        """Get size category based on turnover."""
        if turnover >= 36000000:
            return "large"
        elif turnover >= 10200000:
            return "medium"
        elif turnover >= 632000:
            return "small"
        else:
            return "micro"
    
    def _load_industry_benchmarks(self) -> Dict[str, Dict[str, Any]]:
        """Load industry benchmark data."""
        return {
            "technology": {
                "median_turnover": 750000,
                "mean_turnover": 1200000,
                "growth_rate": 0.15,
                "margin": 0.20
            },
            "professional_services": {
                "median_turnover": 400000,
                "mean_turnover": 650000,
                "growth_rate": 0.10,
                "margin": 0.25
            },
            "financial_services": {
                "median_turnover": 800000,
                "mean_turnover": 1500000,
                "growth_rate": 0.08,
                "margin": 0.30
            },
            "retail_wholesale": {
                "median_turnover": 300000,
                "mean_turnover": 500000,
                "growth_rate": 0.05,
                "margin": 0.15
            },
            "manufacturing": {
                "median_turnover": 1200000,
                "mean_turnover": 2000000,
                "growth_rate": 0.07,
                "margin": 0.12
            },
            "construction": {
                "median_turnover": 600000,
                "mean_turnover": 900000,
                "growth_rate": 0.06,
                "margin": 0.18
            },
            "energy": {
                "median_turnover": 2000000,
                "mean_turnover": 5000000,
                "growth_rate": 0.12,
                "margin": 0.25
            },
            "other": {
                "median_turnover": 350000,
                "mean_turnover": 600000,
                "growth_rate": 0.08,
                "margin": 0.20
            }
        }
    
    def _load_size_indicators(self) -> Dict[str, Any]:
        """Load company size indicators."""
        return {
            "micro": {"max_turnover": 632000, "max_employees": 10},
            "small": {"max_turnover": 10200000, "max_employees": 50},
            "medium": {"max_turnover": 36000000, "max_employees": 250},
            "large": {"min_turnover": 36000000, "min_employees": 250}
        }
    
    def _initialize_estimation_models(self) -> Dict[str, Any]:
        """Initialize estimation models and parameters."""
        return {
            "growth_curves": {
                "startup": {"year_1": 0.5, "year_2": 1.2, "year_3": 2.0, "year_5": 3.5},
                "established": {"year_1": 1.0, "year_3": 1.1, "year_5": 1.25, "year_10": 1.8},
                "mature": {"year_1": 1.0, "year_5": 1.05, "year_10": 1.1, "year_20": 1.2}
            },
            "sector_multipliers": {
                "technology": 1.3,
                "financial_services": 1.2,
                "professional_services": 1.0,
                "manufacturing": 1.1,
                "retail_wholesale": 0.8,
                "construction": 0.9,
                "energy": 1.4,
                "other": 1.0
            }
        }
