"""
Companies House SIC Retrieval Node

This node implements intelligent Companies House SIC code retrieval using the existing
dual-strategy approach with enhanced agentic decision-making capabilities.

Dual Strategy Implementation:
1. Company Number Lookup (Primary) - Direct API call using company registration number
2. Name + Address Matching (Fallback) - Search by company name with address filtering
3. "Not Available" (Final Fallback) - Graceful handling when CH data is unavailable

Integration Points:
- CompaniesHouseClient.get_company_by_number() 
- CompaniesHouseClient.get_company_by_name_and_address()
- Existing dual-strategy pattern from SQLiteSICPredictionRepository
- Real-time CH SIC fetching capabilities

Agentic Enhancements:
- Intelligent strategy selection based on data quality
- Confidence scoring for retrieval methods
- Real-time decision-making about fallback triggers
- Integration with workflow state management
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..workflow_state import AgenticWorkflowState, CompaniesHouseSICData, WorkflowDecision, CompanyData

logger = logging.getLogger(__name__)


class CHSICRetrievalNode:
    """
    Intelligent Companies House SIC retrieval node with dual-strategy approach.
    
    This node wraps existing CompaniesHouseClient methods with enhanced agentic 
    decision-making about which retrieval strategy to use and when to fallback.
    """
    
    def __init__(self, companies_house_client=None):
        """
        Initialize with existing Companies House client.
        
        Args:
            companies_house_client: CompaniesHouseClient instance
        """
        self.ch_client = companies_house_client
        self.logger = logger.getChild(self.__class__.__name__)
    
    def __call__(self, state: AgenticWorkflowState) -> AgenticWorkflowState:
        """
        Execute intelligent Companies House SIC retrieval.
        
        Args:
            state: Current workflow state with company data
            
        Returns:
            Enhanced state with Companies House SIC data and retrieval decisions
        """
        start_time = datetime.now()
        
        try:
            company_data = state.get('company_data')
            if not company_data:
                return self._handle_error(state, "No company data available for CH lookup", start_time)
            
            company_name = company_data.get('company_name', '')
            self.logger.info(f"🔍 CH SIC Retrieval Node: Processing {company_name}")
            
            # Check if CH lookup is enabled in workflow config
            workflow_config = state.get('workflow_config', {})
            if not workflow_config.get('enable_ch_lookup', True):
                return self._handle_disabled_lookup(state, start_time)
            
            # Intelligent strategy selection based on available data
            retrieval_strategy = self._select_retrieval_strategy(company_data)
            
            # Execute dual-strategy retrieval with agentic decision-making
            ch_sic_data = self._execute_dual_strategy_retrieval(company_data, retrieval_strategy)
            
            # Assess retrieval quality and confidence
            quality_assessment = self._assess_retrieval_quality(ch_sic_data, company_data)
            
            # Create workflow decision record
            decision = self._create_workflow_decision(
                "ch_sic_retrieval",
                f"CH SIC retrieval completed using {ch_sic_data.get('retrieval_method', 'unknown')} method",
                quality_assessment['confidence']
            )
            
            # Update workflow state
            updated_state = state.copy()
            updated_state.update({
                'ch_sic_data': ch_sic_data,
                'workflow_decisions': state.get('workflow_decisions', []) + [decision],
                'node_confidence_scores': {
                    **state.get('node_confidence_scores', {}),
                    'ch_sic_retrieval': quality_assessment['confidence']
                },
                'current_node': 'ch_sic_retrieval',
                'warnings': state.get('warnings', []) + quality_assessment.get('warnings', []),
                'node_execution_times': {
                    **state.get('node_execution_times', {}),
                    'ch_sic_retrieval': (datetime.now() - start_time).total_seconds()
                },
                'workflow_steps': state.get('workflow_steps', []) + [
                    self._create_workflow_step("Companies House SIC Retrieval", "completed", ch_sic_data, quality_assessment)
                ]
            })
            
            success_msg = f"✅ CH SIC Retrieval Node: {ch_sic_data.get('retrieval_method', 'unknown')} method successful"
            self.logger.info(success_msg)
            return updated_state
            
        except Exception as e:
            self.logger.error(f"❌ CH SIC Retrieval Node: Error during retrieval: {e}")
            return self._handle_error(state, f"CH SIC retrieval failed: {str(e)}", start_time)
    
    def _select_retrieval_strategy(self, company_data: CompanyData) -> Dict[str, Any]:
        """
        Intelligent selection of optimal retrieval strategy based on available data.
        
        Strategy Priority:
        1. Company number lookup (if company_number available and valid)
        2. Name + address matching (if company name and some address data available)
        3. Name-only search (if only company name available)
        4. Skip CH lookup (if insufficient data)
        """
        strategy = {
            'primary_method': None,
            'fallback_method': None,
            'confidence': 0.0,
            'reasoning': ''
        }
        
        company_number = (company_data.get('company_number') or '').strip()
        company_name = (company_data.get('company_name') or '').strip()
        registered_address = (company_data.get('registered_office_address') or '').strip()  # Exact database field
        jurisdiction = (company_data.get('jurisdiction') or '').strip()  # Exact database field
        
        # Strategy 1: Company number lookup (highest confidence)
        if company_number and len(company_number) >= 6:  # Typical UK company number length
            strategy['primary_method'] = 'company_number'
            strategy['confidence'] = 0.9
            strategy['reasoning'] = f"Company number {company_number} available for direct lookup"
            
            # Fallback to name+address if number lookup fails
            if company_name and (registered_address or jurisdiction):
                strategy['fallback_method'] = 'name_address'
            elif company_name:
                strategy['fallback_method'] = 'name_only'
        
        # Strategy 2: Name + address matching (medium confidence)
        elif company_name and (registered_address or jurisdiction):
            strategy['primary_method'] = 'name_address'
            strategy['confidence'] = 0.7
            strategy['reasoning'] = f"Company name '{company_name}' with address data available"
            
            # Fallback to name-only if address matching fails
            strategy['fallback_method'] = 'name_only'
        
        # Strategy 3: Name-only search (lower confidence)
        elif company_name:
            strategy['primary_method'] = 'name_only'
            strategy['confidence'] = 0.5
            strategy['reasoning'] = f"Only company name '{company_name}' available"
        
        # Strategy 4: Insufficient data
        else:
            strategy['confidence'] = 0.0
            strategy['reasoning'] = "Insufficient data for Companies House lookup"
        
        return strategy
    
    def _execute_dual_strategy_retrieval(self, company_data: CompanyData, strategy: Dict[str, Any]) -> CompaniesHouseSICData:
        """
        Execute dual-strategy retrieval with intelligent fallback decisions.
        
        Leverages existing CompaniesHouseClient methods:
        - get_company_by_number() for direct company number lookup
        - get_company_by_name_and_address() for name + address matching
        """
        if not self.ch_client:
            return self._create_not_available_result("Companies House client not configured")
        
        primary_method = strategy['primary_method']
        fallback_method = strategy['fallback_method']
        
        # Method 1: Company number lookup (existing implementation)
        if primary_method == 'company_number':
            company_number = (company_data.get('company_number') or '').strip()
            self.logger.info(f"🔍 Method 1: Trying company number lookup for {company_number}")
            
            result = self._try_company_number_lookup(company_number)
            if result and result.get('success'):
                return result
            
            self.logger.info(f"⚠️ Company number lookup failed, attempting fallback method: {fallback_method}")
        
        # Method 2: Name + address matching (existing implementation)  
        if primary_method == 'name_address' or fallback_method == 'name_address':
            company_name = (company_data.get('company_name') or '').strip()
            address = self._build_address_string(company_data)
            
            self.logger.info(f"🔍 Method 2: Trying name + address matching for '{company_name}'")
            
            result = self._try_name_address_lookup(company_name, address)
            if result and result.get('success'):
                return result
            
            self.logger.info(f"⚠️ Name + address lookup failed, trying DB cache")
        
        # All live API methods failed - try DB cache as last resort
        company_name = (company_data.get('company_name') or '').strip()
        self.logger.info(f"⚠️ All live CH API lookups failed for '{company_name}', trying DB cache")
        cached = self._try_db_cache_lookup(company_name)
        if cached and cached.get('success'):
            self.logger.info(f"✅ DB cache fallback succeeded for '{company_name}'")
            return cached

        # All methods failed - return "Not Available" result
        return self._create_not_available_result("All Companies House lookup methods failed")
    
    def _try_db_cache_lookup(self, company_name: str) -> Optional[CompaniesHouseSICData]:
        """Last-resort fallback: check sic_prediction_history for previously saved ch_sic_codes."""
        if not company_name:
            return None
        try:
            from app_modules.database.connection import DatabaseConnection
            db = DatabaseConnection()
            rows = db.execute_query(
                """
                SELECT ch_sic_codes, ch_sic_description
                FROM sic_prediction_history
                WHERE LOWER(company_name) = LOWER(?)
                  AND ch_sic_codes IS NOT NULL
                  AND ch_sic_codes != ''
                ORDER BY prediction_timestamp DESC
                LIMIT 1
                """,
                (company_name,)
            )
            if not rows:
                return None

            row = dict(rows[0])
            raw_codes = row.get('ch_sic_codes', '')
            description = row.get('ch_sic_description', '')
            comp_number = ''  # sic_prediction_history does not store company_number

            # ch_sic_codes may be comma-separated (e.g. "52290,49410") or a single value
            sic_list = [c.strip() for c in str(raw_codes).split(',') if c.strip()]
            if not sic_list:
                return None

            desc_list = [d.strip() for d in str(description).split(',') if d.strip()] if description else []
            while len(desc_list) < len(sic_list):
                desc_list.append('')

            self.logger.info(f"📦 DB cache hit for '{company_name}': ch_sic_codes={sic_list}")
            return CompaniesHouseSICData(
                success=True,
                sic_codes=sic_list,
                sic_descriptions=desc_list,
                company_number=comp_number or '',
                company_name=company_name,
                retrieval_method='db_cache',
                confidence=0.85,
                raw_data={'source': 'sic_prediction_history', 'ch_sic_codes': raw_codes}
            )
        except Exception as e:
            self.logger.warning(f"DB cache lookup failed for '{company_name}': {e}")
            return None

    def _try_company_number_lookup(self, company_number: str) -> Optional[CompaniesHouseSICData]:
        """Execute company number lookup using existing CompaniesHouseClient method"""
        try:
            # Use existing get_company_by_number method
            raw_data = self.ch_client.get_company_by_number(company_number)
            
            if raw_data:
                return self._normalize_ch_response(raw_data, "company_number", 0.9)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Company number lookup error: {e}")
            return None
    
    def _try_name_address_lookup(self, company_name: str, address: str) -> Optional[CompaniesHouseSICData]:
        """Execute name + address lookup using existing CompaniesHouseClient method"""
        try:
            # Use existing get_company_by_name_and_address method
            raw_data = self.ch_client.get_company_by_name_and_address(
                company_name=company_name,
                address=address,
                status="active"
            )
            
            if raw_data:
                return self._normalize_ch_response(raw_data, "name_address", 0.7)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Name + address lookup error: {e}")
            return None
    
    def _try_name_only_lookup(self, company_name: str) -> Optional[CompaniesHouseSICData]:
        """Execute name-only lookup (fallback with no address filtering)"""
        try:
            # Use name_address method but without address filtering
            raw_data = self.ch_client.get_company_by_name_and_address(
                company_name=company_name,
                address=None,
                status="active"
            )
            
            if raw_data:
                return self._normalize_ch_response(raw_data, "name_only", 0.5)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Name-only lookup error: {e}")
            return None
    
    def _normalize_ch_response(self, raw_data: Dict[str, Any], method: str, confidence: float) -> CompaniesHouseSICData:
        """Normalize Companies House response to standard format"""
        sic_codes = raw_data.get('sic_codes', [])
        
        # Extract SIC descriptions (if available in response)
        sic_descriptions = []
        if isinstance(sic_codes, list):
            for sic in sic_codes:
                if isinstance(sic, dict):
                    sic_descriptions.append(sic.get('description', ''))
                else:
                    sic_descriptions.append('')  # Will be filled by SIC matcher later
        
        return CompaniesHouseSICData(
            success=True,
            sic_codes=sic_codes if isinstance(sic_codes, list) else [str(sic_codes)] if sic_codes else [],
            sic_descriptions=sic_descriptions,
            company_number=raw_data.get('company_number', ''),
            company_name=raw_data.get('company_name', ''),
            retrieval_method=method,
            confidence=confidence,
            raw_data=raw_data
        )
    
    def _create_not_available_result(self, reason: str) -> CompaniesHouseSICData:
        """Create standardized 'Not Available' result for failed lookups"""
        return CompaniesHouseSICData(
            success=False,
            sic_codes=[],
            sic_descriptions=[],
            company_number='',
            company_name='',
            retrieval_method='not_available',
            confidence=0.0,
            raw_data={'error': reason}
        )
    
    def _build_address_string(self, company_data: CompanyData) -> str:
        """Build address string using exact database fields"""
        address_parts = []
        
        # Use exact database field names
        registered_address = (company_data.get('registered_office_address') or '').strip()
        jurisdiction = (company_data.get('jurisdiction') or '').strip()
        
        if registered_address and registered_address.lower() not in ['nan', 'null', 'none']:
            address_parts.append(registered_address)
        
        if jurisdiction and jurisdiction.lower() not in ['nan', 'null', 'none']:
            address_parts.append(jurisdiction)
        
        return ' '.join(address_parts)
    
    def _assess_retrieval_quality(self, ch_data: CompaniesHouseSICData, company_data: CompanyData) -> Dict[str, Any]:
        """Assess quality and confidence of Companies House retrieval"""
        assessment = {
            'confidence': ch_data.get('confidence', 0.0),
            'warnings': [],
            'quality_indicators': {}
        }
        
        if ch_data.get('success'):
            sic_codes = ch_data.get('sic_codes', [])
            
            # Assess SIC data quality
            if not sic_codes:
                assessment['warnings'].append("No SIC codes found in Companies House data")
                assessment['confidence'] *= 0.5
            elif len(sic_codes) == 1:
                assessment['quality_indicators']['sic_specificity'] = 'high'
            else:
                assessment['quality_indicators']['sic_specificity'] = 'medium'
                assessment['warnings'].append(f"Multiple SIC codes found ({len(sic_codes)})")
            
            # Assess company name matching
            ch_name = (ch_data.get('company_name') or '').lower()
            input_name = (company_data.get('company_name') or '').lower()
            if ch_name and input_name:
                if ch_name == input_name:
                    assessment['quality_indicators']['name_match'] = 'exact'
                elif input_name in ch_name or ch_name in input_name:
                    assessment['quality_indicators']['name_match'] = 'partial'
                    assessment['confidence'] *= 0.9
                else:
                    assessment['quality_indicators']['name_match'] = 'different'
                    assessment['confidence'] *= 0.7
                    assessment['warnings'].append("Company name mismatch with CH data")
        else:
            assessment['warnings'].append("Companies House lookup failed")
        
        return assessment
    
    def _create_workflow_decision(self, node_name: str, decision: str, confidence: float) -> WorkflowDecision:
        """Create standardized workflow decision record"""
        return WorkflowDecision(
            node_name=node_name,
            timestamp=datetime.now(),
            decision=decision,
            reasoning=f"Companies House retrieval completed with confidence {confidence:.2f}",
            confidence=confidence,
            fallback_triggered=confidence < 0.5
        )
    
    def _create_workflow_step(self, step_name: str, status: str, ch_data: CompaniesHouseSICData, 
                            assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Create workflow step for frontend visualization"""
        return {
            'step': step_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'retrieval_method': ch_data.get('retrieval_method', 'unknown'),
                'sic_codes_found': len(ch_data.get('sic_codes', [])),
                'confidence': assessment['confidence'],
                'quality_indicators': assessment.get('quality_indicators', {}),
                'warnings': assessment.get('warnings', [])
            },
            'icon': '🏢' if ch_data.get('success') else '⚠️',
            'duration_ms': 0
        }
    
    def _handle_disabled_lookup(self, state: AgenticWorkflowState, start_time: datetime) -> AgenticWorkflowState:
        """Handle case where CH lookup is disabled in workflow config"""
        self.logger.info("🔇 CH SIC lookup disabled by workflow configuration")
        
        ch_data = self._create_not_available_result("Companies House lookup disabled by configuration")
        
        decision = WorkflowDecision(
            node_name="ch_sic_retrieval",
            timestamp=datetime.now(),
            decision="CH lookup disabled",
            reasoning="Workflow configuration disabled Companies House lookup",
            confidence=0.0,
            fallback_triggered=True
        )
        
        updated_state = state.copy()
        updated_state.update({
            'ch_sic_data': ch_data,
            'workflow_decisions': state.get('workflow_decisions', []) + [decision],
            'node_confidence_scores': {
                **state.get('node_confidence_scores', {}),
                'ch_sic_retrieval': 0.0
            },
            'current_node': 'ch_sic_retrieval',
            'fallback_triggers': state.get('fallback_triggers', []) + ['ch_lookup_disabled'],
            'node_execution_times': {
                **state.get('node_execution_times', {}),
                'ch_sic_retrieval': (datetime.now() - start_time).total_seconds()
            },
            'workflow_steps': state.get('workflow_steps', []) + [
                self._create_disabled_workflow_step()
            ]
        })
        
        return updated_state
    
    def _create_disabled_workflow_step(self) -> Dict[str, Any]:
        """Create workflow step for disabled CH lookup"""
        return {
            'step': 'Companies House SIC Retrieval',
            'status': 'skipped',
            'timestamp': datetime.now().isoformat(),
            'details': {'reason': 'Disabled by configuration'},
            'icon': '🔇',
            'duration_ms': 0
        }
    
    def _handle_error(self, state: AgenticWorkflowState, error_message: str, start_time: datetime) -> AgenticWorkflowState:
        """Handle errors with fallback to next workflow node"""
        self.logger.error(f"❌ CH SIC Retrieval Error: {error_message}")
        
        ch_data = self._create_not_available_result(f"Error: {error_message}")
        
        updated_state = state.copy()
        updated_state.update({
            'ch_sic_data': ch_data,
            'errors': state.get('errors', []) + [error_message],
            'fallback_triggers': state.get('fallback_triggers', []) + ['ch_retrieval_error'],
            'current_node': 'ch_sic_retrieval',
            'node_execution_times': {
                **state.get('node_execution_times', {}),
                'ch_sic_retrieval': (datetime.now() - start_time).total_seconds()
            },
            'workflow_steps': state.get('workflow_steps', []) + [
                self._create_error_workflow_step(error_message)
            ]
        })
        
        return updated_state
    
    def _create_error_workflow_step(self, error_message: str) -> Dict[str, Any]:
        """Create error workflow step for frontend display"""
        return {
            'step': 'Companies House SIC Retrieval',
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'details': {'error': error_message},
            'icon': '❌',
            'duration_ms': 0
        }