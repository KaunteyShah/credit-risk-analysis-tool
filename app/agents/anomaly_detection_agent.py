"""
Anomaly Detection Agent - Identifies inconsistencies in sector codes and turnover data.
"""
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.base_agent import BaseAgent, AgentResult
from app.utils.config_manager import config
from app.utils.logger import logger

@dataclass
class Anomaly:
    """Represents a detected anomaly."""
    company_number: str
    company_name: str
    anomaly_type: str  # "sector_code" or "turnover"
    current_value: Any
    anomaly_score: float
    confidence: float
    description: str
    suggested_investigation: str

class AnomalyDetectionAgent(BaseAgent):
    """Agent responsible for detecting anomalies in business data."""
    
    def __init__(self):
        super().__init__("AnomalyDetectionAgent")
        
        # Standard SIC code mapping for validation
        self.valid_sic_codes = self._load_valid_sic_codes()
        
        # Turnover validation thresholds
        self.turnover_thresholds = {
            "micro": {"min": 0, "max": 632000},
            "small": {"min": 632000, "max": 10200000},
            "medium": {"min": 10200000, "max": 36000000},
            "large": {"min": 36000000, "max": float('inf')}
        }
    
    def process(self, data: Any, **kwargs) -> AgentResult:
        """
        Process anomaly detection on company data.
        
        Args:
            data: Dictionary containing company data or pandas DataFrame
        
        Returns:
            AgentResult with detected anomalies
        """
        try:
            self.log_activity("Starting anomaly detection process")
            
            companies = []
            if isinstance(data, dict) and "companies" in data:
                companies = data["companies"]
            elif isinstance(data, dict) and "dataframe" in data:
                # Convert DataFrame back to list of dicts if needed
                df = data["dataframe"]
                companies = df.to_dict('records') if hasattr(df, 'to_dict') else []
            elif isinstance(data, list):
                companies = data
            
            if not companies:
                return self.create_result(
                    success=False,
                    error_message="No company data provided for anomaly detection"
                )
            
            # Detect anomalies
            anomalies = []
            
            for company in companies:
                # Check sector code anomalies
                sector_anomalies = self._detect_sector_anomalies(company)
                anomalies.extend(sector_anomalies)
                
                # Check turnover anomalies
                turnover_anomalies = self._detect_turnover_anomalies(company)
                anomalies.extend(turnover_anomalies)
            
            # Calculate overall statistics
            total_companies = len(companies)
            anomaly_count = len(anomalies)
            anomaly_rate = anomaly_count / total_companies if total_companies > 0 else 0
            
            self.log_activity(f"Detected {anomaly_count} anomalies across {total_companies} companies")
            
            return self.create_result(
                success=True,
                data={
                    "anomalies": anomalies,
                    "summary": {
                        "total_companies": total_companies,
                        "total_anomalies": anomaly_count,
                        "anomaly_rate": anomaly_rate,
                        "sector_anomalies": len([a for a in anomalies if a.anomaly_type == "sector_code"]),
                        "turnover_anomalies": len([a for a in anomalies if a.anomaly_type == "turnover"])
                    }
                },
                confidence=0.8,
                anomaly_count=anomaly_count,
                anomaly_rate=anomaly_rate
            )
            
        except Exception as e:
            error_msg = f"Anomaly detection failed: {str(e)}"
            self.log_activity(error_msg, "ERROR")
            return self.create_result(
                success=False,
                error_message=error_msg
            )
    
    def _detect_sector_anomalies(self, company: Dict[str, Any]) -> List[Anomaly]:
        """Detect sector code anomalies for a company."""
        anomalies = []
        
        company_number = company.get("company_number", "")
        company_name = company.get("company_name", "")
        sic_codes = company.get("all_sic_codes", "").split(",") if company.get("all_sic_codes") else []
        primary_sic = company.get("primary_sic_code")
        description = company.get("description", "")
        
        # Check for invalid SIC codes
        for sic_code in sic_codes:
            sic_code = sic_code.strip()
            if sic_code and not self._is_valid_sic_code(sic_code):
                anomalies.append(Anomaly(
                    company_number=company_number,
                    company_name=company_name,
                    anomaly_type="sector_code",
                    current_value=sic_code,
                    anomaly_score=0.9,
                    confidence=0.95,
                    description=f"Invalid SIC code: {sic_code}",
                    suggested_investigation="Verify SIC code against official classification"
                ))
        
        # Check for missing primary SIC code
        if not primary_sic and not sic_codes:
            anomalies.append(Anomaly(
                company_number=company_number,
                company_name=company_name,
                anomaly_type="sector_code",
                current_value=None,
                anomaly_score=0.8,
                confidence=0.9,
                description="Missing SIC code classification",
                suggested_investigation="Assign appropriate SIC code based on business activity"
            ))
        
        # Check for inconsistency between SIC codes and business description
        if description and primary_sic:
            if self._detect_sic_description_mismatch(primary_sic, description):
                anomalies.append(Anomaly(
                    company_number=company_number,
                    company_name=company_name,
                    anomaly_type="sector_code",
                    current_value=primary_sic,
                    anomaly_score=0.7,
                    confidence=0.75,
                    description=f"Potential mismatch between SIC code {primary_sic} and business description",
                    suggested_investigation="Review business description against SIC code classification"
                ))
        
        return anomalies
    
    def _detect_turnover_anomalies(self, company: Dict[str, Any]) -> List[Anomaly]:
        """Detect turnover anomalies for a company."""
        anomalies = []
        
        company_number = company.get("company_number", "")
        company_name = company.get("company_name", "")
        turnover = company.get("turnover")
        company_type = company.get("company_type", "")
        
        if turnover is None:
            # Missing turnover data
            anomalies.append(Anomaly(
                company_number=company_number,
                company_name=company_name,
                anomaly_type="turnover",
                current_value=None,
                anomaly_score=0.6,
                confidence=0.7,
                description="Missing turnover data",
                suggested_investigation="Obtain turnover information from financial reports or estimates"
            ))
            return anomalies
        
        # Check for unrealistic turnover values
        if turnover < 0:
            anomalies.append(Anomaly(
                company_number=company_number,
                company_name=company_name,
                anomaly_type="turnover",
                current_value=turnover,
                anomaly_score=1.0,
                confidence=1.0,
                description="Negative turnover value",
                suggested_investigation="Verify turnover calculation and data source"
            ))
        
        elif turnover == 0:
            anomalies.append(Anomaly(
                company_number=company_number,
                company_name=company_name,
                anomaly_type="turnover",
                current_value=turnover,
                anomaly_score=0.8,
                confidence=0.8,
                description="Zero turnover for active company",
                suggested_investigation="Confirm if company is dormant or verify turnover data"
            ))
        
        elif turnover > 1000000000:  # 1 billion threshold
            anomalies.append(Anomaly(
                company_number=company_number,
                company_name=company_name,
                anomaly_type="turnover",
                current_value=turnover,
                anomaly_score=0.7,
                confidence=0.6,
                description="Exceptionally high turnover value",
                suggested_investigation="Verify turnover figure against published accounts"
            ))
        
        return anomalies
    
    def _is_valid_sic_code(self, sic_code: str) -> bool:
        """Check if a SIC code is valid."""
        # Remove any non-numeric characters and check format
        numeric_code = ''.join(filter(str.isdigit, sic_code))
        
        # UK SIC codes are typically 4 or 5 digits
        if len(numeric_code) not in [4, 5]:
            return False
        
        # Check against known valid codes (simplified check)
        return numeric_code in self.valid_sic_codes
    
    def _detect_sic_description_mismatch(self, sic_code: str, description: str) -> bool:
        """Detect potential mismatch between SIC code and business description."""
        # This is a simplified implementation
        # In practice, you would use more sophisticated NLP techniques
        
        description_lower = description.lower()
        
        # Basic keyword matching for common SIC code categories
        sic_keywords = {
            "46": ["retail", "wholesale", "trading", "distribution"],
            "47": ["retail", "shop", "store", "selling"],
            "62": ["software", "programming", "development", "IT", "technology"],
            "68": ["property", "real estate", "letting", "rental"],
            "70": ["consulting", "advisory", "management"],
            "82": ["administration", "support", "services"]
        }
        
        sic_prefix = sic_code[:2] if len(sic_code) >= 2 else sic_code
        keywords = sic_keywords.get(sic_prefix, [])
        
        if keywords:
            # If none of the keywords appear in the description, it might be a mismatch
            return not any(keyword in description_lower for keyword in keywords)
        
        return False
    
    def _load_valid_sic_codes(self) -> set:
        """Load valid SIC codes (simplified set for demo)."""
        # In practice, this would load from a comprehensive SIC code database
        return {
            # Agriculture, forestry and fishing
            "01110", "01120", "01130", "01140", "01150", "01160", "01170", "01190",
            "01210", "01220", "01230", "01240", "01250", "01260", "01270", "01280", "01290",
            
            # Manufacturing
            "10110", "10120", "10130", "10200", "10310", "10320", "10390",
            
            # Construction
            "41100", "41200", "42110", "42120", "42130", "42210", "42220", "42910", "42990",
            "43110", "43120", "43130", "43210", "43220", "43290", "43310", "43320", "43330",
            "43340", "43390", "43910", "43991", "43999",
            
            # Wholesale and retail trade
            "45111", "45112", "45190", "45200", "45310", "45320", "45400",
            "46110", "46120", "46130", "46140", "46150", "46160", "46170", "46180", "46190",
            "47110", "47190", "47210", "47220", "47230", "47240", "47250", "47260", "47290",
            
            # Information and communication
            "58110", "58120", "58130", "58140", "58190", "58210", "58290",
            "59110", "59120", "59130", "59140", "59200",
            "60100", "60200",
            "61100", "61200", "61300", "61900",
            "62011", "62012", "62020", "62030", "62090",
            "63110", "63120", "63910", "63990",
            
            # Professional, scientific and technical activities
            "69101", "69102", "69109", "69201", "69202", "69203", "69209",
            "70100", "70210", "70220",
            "71111", "71112", "71121", "71122", "71129", "71200",
            "72110", "72190", "72200",
            "73110", "73120", "73200",
            "74100", "74201", "74202", "74203", "74209", "74300", "74901", "74909",
            "75000",
            
            # Administrative and support service activities
            "77110", "77120", "77210", "77220", "77290", "77310", "77320", "77330", "77340", "77390",
            "78100", "78200", "78300",
            "79110", "79120", "79900",
            "80100", "80200", "80300",
            "81100", "81210", "81220", "81290", "81300",
            "82110", "82190", "82200", "82300", "82910", "82920", "82990"
        }
