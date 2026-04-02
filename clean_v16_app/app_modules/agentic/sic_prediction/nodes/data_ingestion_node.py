"""
Data Ingestion Node

This node handles the initial data preparation and validation for the agentic workflow.
It leverages existing repository infrastructure while adding agentic data quality assessment.

Responsibilities:
- Fetch company data using existing SQLiteSICPredictionRepository
- Validate and structure data for agentic processing
- Set workflow configuration and initial state
- Prepare data for intelligent decision-making

Integration Points:
- SQLiteSICPredictionRepository.get_company_by_index()
- CompanyService.get_company_details_with_reasoning()
- Existing data validation patterns
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..workflow_state import AgenticWorkflowState, CompanyData, WorkflowDecision

logger = logging.getLogger(__name__)


class DataIngestionNode:
    """
    Intelligent data ingestion node that prepares company data for agentic workflow.
    
    This node wraps existing repository methods with enhanced validation and structuring
    to ensure high-quality input for subsequent agentic decisions.
    """
    
    def __init__(self, repository=None, company_service=None):
        """
        Initialize with existing infrastructure dependencies.
        
        Args:
            repository: SQLiteSICPredictionRepository instance
            company_service: CompanyService instance
        """
        self.repository = repository
        self.company_service = company_service
        self.logger = logger.getChild(self.__class__.__name__)
    
    def __call__(self, state: AgenticWorkflowState) -> AgenticWorkflowState:
        """
        Execute data ingestion with intelligent quality assessment.
        
        Args:
            state: Current workflow state with company_index
            
        Returns:
            Enhanced state with validated company data and initial workflow setup
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🔄 Data Ingestion Node: Processing company ID {state.get('company_id', 'unknown')}")
            
            # Handle both existing companies (with company_id) and new companies (from API)
            company_id = state.get('company_id')
            existing_company_data = state.get('company_data', {})
            
            if company_id is not None:
                # Existing company in database - fetch full data
                company_data = self._fetch_company_data(company_id)
                if not company_data:
                    return self._handle_error(state, f"No company data found for ID {company_id}", start_time)
            elif existing_company_data:
                # Check if this company already exists in database by name
                company_name = existing_company_data.get('company_name', '')
                if company_name and self.repository:
                    # Try to find existing company by name
                    existing_db_company = self.repository.get_company_by_name(company_name)
                    if existing_db_company:
                        self.logger.info(f"🔍 Found existing company in database: {company_name}")
                        
                        # DEBUG: Log repository data before structuring
                        self.logger.info(f"🔍 REPOSITORY DATA for {company_name}:")
                        self.logger.info(f"   - existing_sic_code: {existing_db_company.get('existing_sic_code')}")
                        self.logger.info(f"   - uk_sic_2007_code: {existing_db_company.get('uk_sic_2007_code')}")
                        self.logger.info(f"   - existing_sic_confidence: {existing_db_company.get('existing_sic_confidence')}")
                        self.logger.info(f"   - all keys: {list(existing_db_company.keys())}")
                        
                        company_data = existing_db_company
                    else:
                        # New company from API request - use provided data
                        self.logger.info("🆕 Processing new company from API request")
                        # Ensure company_data is a dictionary
                        company_data = dict(existing_company_data) if hasattr(existing_company_data, '__dict__') else existing_company_data
                else:
                    # New company from API request - use provided data
                    self.logger.info("🆕 Processing new company from API request")
                    # Ensure company_data is a dictionary
                    company_data = dict(existing_company_data) if hasattr(existing_company_data, '__dict__') else existing_company_data
            else:
                return self._handle_error(state, "No company ID or company data provided", start_time)
            
            # Intelligent data quality assessment
            quality_assessment = self._assess_data_quality(company_data)
            
            # Structure company data for agentic workflow
            structured_data = self._structure_company_data(company_data, quality_assessment)
            
            # DEBUG: Log structured data contents
            self.logger.info(f"🔍 STRUCTURED DATA AFTER _structure_company_data:")
            self.logger.info(f"   - existing_sic_confidence: {structured_data.get('existing_sic_confidence')}")
            self.logger.info(f"   - sic_codes: {structured_data.get('sic_codes')}")
            self.logger.info(f"   - company_name: {structured_data.get('company_name')}")
            self.logger.info(f"   - all keys: {list(structured_data.keys())}")
            
            # Set workflow configuration based on data quality
            workflow_config = self._determine_workflow_config(quality_assessment)
            
            # Create workflow decision record
            decision = self._create_workflow_decision(
                "data_ingestion",
                f"Data ingestion completed with quality score: {quality_assessment['overall_score']:.2f}",
                quality_assessment['overall_score']
            )
            
            # Update state with processed data
            updated_state = state.copy()
            updated_state.update({
                'company_data': structured_data,
                'workflow_config': workflow_config,
                'workflow_decisions': [decision],
                'node_confidence_scores': {'data_ingestion': quality_assessment['overall_score']},
                'current_node': 'data_ingestion',
                'fallback_triggers': [],
                'errors': [],
                'warnings': quality_assessment.get('warnings', []),
                'node_execution_times': {'data_ingestion': (datetime.now() - start_time).total_seconds()},
                'workflow_steps': [self._create_workflow_step("Data Ingestion", "completed", quality_assessment)]
            })
            
            self.logger.info(f"✅ Data Ingestion Node: Successfully processed company: {structured_data.get('company_name', 'Unknown')}")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ Data Ingestion Node: Error processing company data: {e}")
            return self._handle_error(state, f"Data ingestion failed: {str(e)}", start_time)
    
    def _fetch_company_data(self, company_id: int) -> Dict[str, Any] | None:
        """
        Fetch company data using existing repository infrastructure.
        
        Leverages:
        - SQLiteSICPredictionRepository.get_company_by_company_id()
        - CompanyService.get_company_details_with_reasoning() (if available)
        """
        try:
            # Primary method: Use repository directly
            if self.repository:
                company_data = self.repository.get_company_by_company_id(company_id)
                if company_data:
                    self.logger.debug(f"📊 Repository fetch successful for company: {company_data.get('company_name', 'Unknown')}")
                    return company_data
            
            # Fallback method: Use company service if available  
            if self.company_service:
                company_details = self.company_service.get_company_details_with_reasoning(company_id)
                if company_details and not company_details.get('error'):
                    self.logger.debug("📊 Company service fetch successful")
                    return company_details
            
            self.logger.warning(f"No data source available for company ID {company_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching company data: {e}")
            return None
    
    def _assess_data_quality(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligent assessment of data quality for agentic decision-making.
        
        Evaluates:
        - Business description quality and length
        - Existing SIC code availability and validity
        - Company identification data completeness
        - Address information for Companies House lookup
        """
        assessment = {
            'overall_score': 0.0,
            'components': {},
            'warnings': [],
            'recommendations': []
        }
        
        # Business description quality (40% weight)
        business_desc = (company_data.get('business_description', '') or 
                        company_data.get('Business Description', ''))  # Handle legacy format
        desc_score = self._assess_business_description(business_desc)
        assessment['components']['business_description'] = desc_score
        
        # Company identification completeness (30% weight)
        id_score = self._assess_company_identification(company_data)
        assessment['components']['company_identification'] = id_score
        
        # Existing SIC data availability (20% weight)
        sic_score = self._assess_existing_sic_data(company_data)
        assessment['components']['existing_sic'] = sic_score
        
        # Address data for CH lookup (10% weight)
        address_score = self._assess_address_data(company_data)
        assessment['components']['address_data'] = address_score
        
        # Calculate overall score
        assessment['overall_score'] = (
            desc_score * 0.4 + 
            id_score * 0.3 + 
            sic_score * 0.2 + 
            address_score * 0.1
        )
        
        # Generate recommendations based on assessment
        if desc_score < 0.5:
            assessment['warnings'].append("Business description is too short or unclear")
            assessment['recommendations'].append("Consider requesting more detailed business description")
        
        if id_score < 0.3:
            assessment['warnings'].append("Limited company identification data")
            assessment['recommendations'].append("Companies House lookup may be challenging")
        
        return assessment
    
    def _assess_business_description(self, description: str) -> float:
        """Assess business description quality for AI prediction accuracy"""
        if not description or description.lower() in ['', 'nan', 'null', 'none']:
            return 0.0
        
        length_score = min(len(description) / 100, 1.0)  # Optimal around 100 chars
        word_count = len(description.split())
        word_score = min(word_count / 10, 1.0)  # Optimal around 10 words
        
        # Check for meaningful business terms
        business_terms = ['business', 'service', 'company', 'industry', 'market', 'product', 'customer']
        term_count = sum(1 for term in business_terms if term.lower() in description.lower())
        term_score = min(term_count / 3, 1.0)
        
        return (length_score + word_score + term_score) / 3
    
    def _assess_company_identification(self, company_data: Dict[str, Any]) -> float:
        """Assess company identification data completeness"""
        score = 0.0
        max_score = 0.0
        
        # Company name (essential for lookup)
        company_name = (company_data.get('company_name') or  # Exact database column
                       company_data.get('Company Name', ''))  # Legacy format support
        if company_name and company_name.lower() not in ['', 'nan', 'null']:
            score += 0.5
        max_score += 0.5
        
        # Company number (very valuable for CH lookup) - exact database column
        company_number = company_data.get('company_number', '')
        if company_number and company_number.lower() not in ['', 'nan', 'null']:
            score += 0.3
        max_score += 0.3
        
        # ID from database (unique identifier)
        company_id = company_data.get('id', '')  # Exact database primary key
        if company_id and str(company_id).lower() not in ['', 'nan', 'null']:
            score += 0.2
        max_score += 0.2
        
        return score / max_score if max_score > 0 else 0.0
    
    def _assess_existing_sic_data(self, company_data: Dict[str, Any]) -> float:
        """Assess existing SIC code data quality using exact database field names"""
        existing_sic = (
            company_data.get('sic_codes') or  # Exact database column name
            company_data.get('SIC Code (SIC 2007)') or  # Legacy format support
            company_data.get('existing_sic_code', '')  # Calculated field support
        )
        
        if not existing_sic or str(existing_sic).lower() in ['', 'nan', 'null', 'none']:
            return 0.0
        
        # Basic SIC code format validation
        sic_str = str(existing_sic).strip()
        if len(sic_str) >= 4 and sic_str.isdigit():
            return 1.0
        elif len(sic_str) >= 3:
            return 0.7
        else:
            return 0.3
    
    def _assess_address_data(self, company_data: Dict[str, Any]) -> float:
        """Assess address data completeness using exact database column names"""
        score = 0.0
        components = 0
        
        # Use exact database column name
        registered_address = company_data.get('registered_office_address', '')
        if registered_address and str(registered_address).lower() not in ['', 'nan', 'null']:
            score += 1
        components += 1
        
        # Jurisdiction is also available in database
        jurisdiction = company_data.get('jurisdiction', '')
        if jurisdiction and str(jurisdiction).lower() not in ['', 'nan', 'null']:
            score += 0.5
        components += 0.5
        
        return score / components if components > 0 else 0.0
    
    def _structure_company_data(self, raw_data: Dict[str, Any], quality_assessment: Dict[str, Any]) -> CompanyData:
        """Structure raw company data using EXACT database column names with dual-key validation"""
        return CompanyData(
            # EXACT database column names from companies table
            id=raw_data.get('id'),  # Primary key
            unique_id=raw_data.get('unique_id', ''),  # DUAL-KEY: Unique business identifier
            company_number=raw_data.get('company_number', ''),  # Exact column name
            company_name=raw_data.get('company_name') or raw_data.get('Company Name', ''),  # Handle legacy format
            business_description=raw_data.get('business_description') or raw_data.get('Business Description', ''),  # Handle legacy
            sic_codes=raw_data.get('sic_codes') or raw_data.get('SIC Code (SIC 2007)') or raw_data.get('existing_sic_code', ''),  # Repository returns 'SIC Code (SIC 2007)'
            status=raw_data.get('status', ''),  # Exact column name
            company_type=raw_data.get('company_type', ''),  # Exact column name
            jurisdiction=raw_data.get('jurisdiction', ''),  # Exact column name
            registered_office_address=raw_data.get('registered_office_address', ''),  # Exact column name
            
            # Additional workflow fields (not database columns)
            company_index=raw_data.get('company_index', 0),  # For batch processing
            existing_sic_confidence=raw_data.get('existing_sic_confidence', raw_data.get('Old_Accuracy', 0.0)),  # Use confidence field from repository
            existing_sic_code=raw_data.get('existing_sic_code') or raw_data.get('SIC Code (SIC 2007)', '')  # Current SIC for API response
        )
    
    def _determine_workflow_config(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Determine intelligent workflow configuration based on data quality"""
        overall_score = quality_assessment['overall_score']
        
        config = {
            'confidence_threshold': 0.7,  # Default confidence threshold
            'enable_ch_lookup': True,
            'enable_ai_prediction': True,
            'enable_reflection': True,
            'fallback_strategy': 'progressive',  # progressive, immediate, or disabled
            'max_iterations': 1
        }
        
        # Adjust configuration based on data quality
        if overall_score >= 0.8:
            # High quality data - use aggressive thresholds
            config['confidence_threshold'] = 0.8
            config['fallback_strategy'] = 'disabled'
        elif overall_score >= 0.5:
            # Medium quality data - balanced approach
            config['confidence_threshold'] = 0.7
            config['fallback_strategy'] = 'progressive'
        else:
            # Low quality data - conservative approach with fallbacks
            config['confidence_threshold'] = 0.6
            config['fallback_strategy'] = 'immediate'
            config['max_iterations'] = 2
        
        # Disable CH lookup if no company identification data
        if quality_assessment['components']['company_identification'] < 0.3:
            config['enable_ch_lookup'] = False
        
        return config
    
    def _create_workflow_decision(self, node_name: str, decision: str, confidence: float) -> WorkflowDecision:
        """Create standardized workflow decision record"""
        return WorkflowDecision(
            node_name=node_name,
            timestamp=datetime.now(),
            decision=decision,
            reasoning=f"Data quality assessment completed with score {confidence:.2f}",
            confidence=confidence,
            fallback_triggered=False
        )
    
    def _create_workflow_step(self, step_name: str, status: str, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Create workflow step for frontend visualization (compatible with existing format)"""
        return {
            'step': step_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'overall_score': assessment['overall_score'],
                'components': assessment['components'],
                'recommendations': assessment.get('recommendations', [])
            },
            'icon': '📊',
            'duration_ms': 0  # Will be calculated later
        }
    
    def _handle_error(self, state: AgenticWorkflowState, error_message: str, start_time: datetime) -> AgenticWorkflowState:
        """Handle errors with fallback to existing systems"""
        self.logger.error(f"❌ Data Ingestion Error: {error_message}")
        
        updated_state = state.copy()
        updated_state.update({
            'errors': [error_message],
            'fallback_triggers': ['data_ingestion_error'],
            'current_node': 'data_ingestion',
            'node_execution_times': {'data_ingestion': (datetime.now() - start_time).total_seconds()},
            'workflow_steps': [self._create_error_workflow_step(error_message)]
        })
        
        return updated_state
    
    def _create_error_workflow_step(self, error_message: str) -> Dict[str, Any]:
        """Create error workflow step for frontend display"""
        return {
            'step': 'Data Ingestion',
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'details': {'error': error_message},
            'icon': '❌',
            'duration_ms': 0
        }