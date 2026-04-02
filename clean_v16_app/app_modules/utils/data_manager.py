"""
Application Data Manager - Handles global application state properly
"""
import pandas as pd
import os
from typing import Optional, Any
from app_modules.utils.centralized_logging import get_logger
from app_modules.utils.enhanced_sic_matcher import get_enhanced_sic_matcher
from app_modules.utils.simulation import simulation_service
from app_modules.agents.orchestrator import MultiAgentOrchestrator
# from app_modules.agents.sector_classification_agent import SectorClassificationAgent  # COMMENTED OUT - missing file

logger = get_logger('app.utils.data_manager')


class ApplicationDataManager:
    """Manages application data and services in a type-safe manner"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self._company_data: Optional[pd.DataFrame] = None
        self._sic_codes: Optional[pd.DataFrame] = None
        self._sic_matcher = None
        self._orchestrator: Optional[MultiAgentOrchestrator] = None
        self._sector_agent: Optional[Any] = None  # SectorClassificationAgent not available
        
        # Initialize agents
        self._init_agents()
        
    def _init_agents(self):
        """Initialize multi-agent orchestrator and sector agent"""
        try:
            self._orchestrator = MultiAgentOrchestrator()
            # self._sector_agent = SectorClassificationAgent()  # Commented out - missing file
            self._sector_agent = None
            logger.info("Multi-agent orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
    
    @property
    def company_data(self) -> pd.DataFrame:
        """Get company data, loading if necessary"""
        if self._company_data is None:
            self.load_company_data()
        return self._company_data if self._company_data is not None else pd.DataFrame()
    
    @property
    def sic_codes(self) -> pd.DataFrame:
        """Get SIC codes data"""
        return self._sic_codes if self._sic_codes is not None else pd.DataFrame()
    
    @property
    def sic_matcher(self):
        """Get SIC matcher instance"""
        return self._sic_matcher
    
    @property
    def orchestrator(self) -> Optional[MultiAgentOrchestrator]:
        """Get orchestrator instance"""
        return self._orchestrator
    
    @property
    def sector_agent(self) -> Optional[Any]:  # SectorClassificationAgent not available
        """Get sector agent instance"""
        return self._sector_agent
    
    def clean_numeric_column(self, series: pd.Series) -> pd.Series:
        """Clean and convert a series to numeric values"""
        # Convert to string first, then clean
        cleaned = series.astype(str).str.replace(',', '').str.replace('$', '').str.replace('€', '')
        # Convert to numeric, replacing non-numeric with NaN
        return pd.to_numeric(cleaned, errors='coerce')
    
    def load_company_data(self) -> bool:
        """Load and prepare company data"""
        try:
            # Load company data
            company_file = os.path.join(self.project_root, 'data', 'Sample_data2.csv')
            if os.path.exists(company_file):
                self._company_data = pd.read_csv(company_file)
                logger.info(f"Loaded {len(self._company_data)} companies from CSV")
                
                # Clean numeric columns
                numeric_columns = ['Employees (Total)', 'Sales (GBP)', 'Pre Tax Profit (USD)']
                for col in numeric_columns:
                    if col in self._company_data.columns:
                        self._company_data[col] = self.clean_numeric_column(self._company_data[col])
                
                # Load SIC codes and initialize enhanced fuzzy matching
                sic_file = os.path.join(self.project_root, 'data', 'SIC_codes.xlsx')
                if os.path.exists(sic_file):
                    # Initialize enhanced SIC matcher
                    self._sic_matcher = get_enhanced_sic_matcher(sic_file)
                    
                    # Calculate dual accuracy using enhanced fuzzy matching
                    logger.info("Calculating dual SIC accuracy using enhanced fuzzy matching...")
                    self._company_data = self._sic_matcher.batch_calculate_dual_accuracy(self._company_data)
                    
                    # Legacy CSV merge removed - now using SQLite for approved predictions
                    logger.info("Enhanced SIC accuracy calculation completed")
                    
                else:
                    logger.warning(f"SIC codes file not found: {sic_file}")
                    # Fallback: generate demo accuracy data for Azure deployment
                    logger.info("Generating demo SIC accuracy data...")
                    self._company_data['SIC_Accuracy'] = simulation_service.generate_sic_accuracy(len(self._company_data))
                
                # Add helper columns
                self._company_data['Needs_Revenue_Update'] = self._company_data['Sales (GBP)'].isna()
                
                # Load SIC codes for reference
                if os.path.exists(sic_file):
                    self._sic_codes = pd.read_excel(sic_file)
                    logger.info(f"Loaded {len(self._sic_codes)} SIC codes")
                else:
                    logger.warning(f"SIC codes file not found: {sic_file}")
                    self._sic_codes = pd.DataFrame()
                
                return True
                
            else:
                logger.error(f"Company data file not found: {company_file}")
                logger.warning("Data files missing - this should not happen in production deployment")
                self._company_data = pd.DataFrame()
                self._sic_codes = pd.DataFrame()
                return False
                
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self._company_data = pd.DataFrame()
            self._sic_codes = pd.DataFrame()
            return False
    
    def get_company_by_index(self, index: int) -> Optional[dict]:
        """Get company data by index"""
        if self._company_data is None or index >= len(self._company_data):
            return None
        return self._company_data.iloc[index].to_dict()
    
    def is_data_loaded(self) -> bool:
        """Check if data is loaded"""
        return self._company_data is not None and not self._company_data.empty
    
    def save_sic_update(self, company_index: int, new_sic: str) -> dict:
        """Save SIC update using the matcher - now uses SQLite database directly"""
        if not self._sic_matcher:
            return {'success': False, 'error': 'SIC matcher not initialized'}
        
        company = self.get_company_by_index(company_index)
        if not company:
            return {'success': False, 'error': 'Company not found'}
        
        try:
            # Use save_prediction_to_db instead of removed save_sic_update method
            success = self._sic_matcher.save_prediction_to_db(
                company_id=company_index + 1,  # Approximate company ID
                company_name=company.get('Company Name', ''),
                business_description=company.get('Business Description', ''),
                predicted_sic_code=new_sic,
                predicted_sic_description=self._sic_matcher.get_sic_description(new_sic),
                confidence_score=85.0,  # Default accuracy for user updates
                existing_sic_confidence=company.get('Old_Accuracy', 0),
                model_version="1.0",
                prediction_method="DATA_MANAGER_MANUAL",
                ai_reasoning=f"SIC code manually updated to {new_sic}"
            )
            
            if success:
                # Reload data to reflect changes
                self.load_company_data()
                return {
                    'success': True,
                    'company_name': company.get('Company Name', ''),
                    'new_sic': new_sic,
                    'new_accuracy': 85.0
                }
            else:
                return {'success': False, 'error': 'Failed to save SIC update to database'}
                
        except Exception as e:
            logger.error(f"Error saving SIC update: {e}")
            return {'success': False, 'error': str(e)}