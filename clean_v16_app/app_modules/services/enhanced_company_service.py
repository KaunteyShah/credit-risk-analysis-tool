"""
Enhanced Service that integrates modular architecture with your existing agents

This demonstrates how the service layer COORDINATES your sophisticated 
AI agents with the modular repository pattern for better efficiency.
"""
import pandas as pd
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from app_modules.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface
from app_modules.agents.ai_reasoning_agent import AIReasoningAgent
from app_modules.agents.smart_financial_extraction_agent import SmartFinancialExtractionAgent
# Legacy orchestrator and sector agent removed - using pure agentic system instead

logger = logging.getLogger(__name__)


class EnhancedCompanyService:
    """
    Enhanced service that coordinates AI agents with modular architecture
    
    Benefits:
    - Uses sophisticated AI agents (reasoning, financial)
    - Clean dependency injection for better testing
    - Repository abstraction for flexible data access
    - Compatible with pure agentic SIC prediction system
    """
    
    def __init__(self, 
                 company_repository: CompanyRepositoryInterface,
                 reasoning_agent: AIReasoningAgent,
                 financial_agent: SmartFinancialExtractionAgent):
        """Initialize with active AI agents (legacy orchestrator removed)"""
        
        self.company_repo = company_repository
        self.reasoning_agent = reasoning_agent  
        self.financial_agent = financial_agent
        
        logger.info("EnhancedCompanyService initialized with active agents (pure agentic SIC system compatible)")
    
    def get_companies_data(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get companies data using modular repository + your existing agents
        
        Enhanced workflow:
        1. Repository provides clean data access
        2. Your agents enhance the data
        3. Clean response formatting
        """
        try:
            logger.info(f"Fetching companies data (limit: {limit})")
            
            # Step 1: Get data through repository interface
            companies_df = self.company_repo.get_all_companies()
            
            if limit:
                companies_df = companies_df.head(limit)
            
            # Step 2: Enhance with your existing agents
            enhanced_companies = []
            
            for _, company in companies_df.iterrows():
                try:
                    # Use your existing sector classification agent
                    sector_insights = self.sector_agent.process([company])
                    
                    # Use your existing reasoning agent for analysis
                    reasoning_result = self.reasoning_agent.analyze_company_context(company)
                    
                    enhanced_company = {
                        'registration': company.get('company_registration', ''),
                        'name': company.get('company_name', ''),
                        'address': company.get('company_address', ''),
                        'postcode': company.get('company_postcode', ''),
                        'current_sic': company.get('predicted_sic', ''),
                        'sic_confidence': company.get('sic_confidence', 0.0),
                        'algorithm_used': company.get('algorithm_used', ''),
                        
                        # Enhancements from your existing agents
                        'sector_insights': sector_insights,
                        'reasoning_analysis': reasoning_result,
                        'enhanced_at': datetime.utcnow().isoformat()
                    }
                    
                    enhanced_companies.append(enhanced_company)
                    
                except Exception as e:
                    logger.warning(f"Error enhancing company {company.get('company_name', 'Unknown')}: {e}")
                    # Include basic company data even if enhancement fails
                    enhanced_companies.append({
                        'registration': company.get('company_registration', ''),
                        'name': company.get('company_name', ''),
                        'address': company.get('company_address', ''),
                        'postcode': company.get('company_postcode', ''),
                        'current_sic': company.get('predicted_sic', ''),
                        'error': str(e)
                    })
            
            # Step 3: Get repository statistics
            statistics = self.company_repo.get_company_statistics()
            
            return {
                'success': True,
                'companies': enhanced_companies,
                'total_companies': len(enhanced_companies),
                'statistics': statistics,
                'enhanced_by_agents': True,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in get_companies_data: {e}")
            return {
                'success': False,
                'error': str(e),
                'companies': [],
                'total_companies': 0
            }
    
    def predict_company_sic_enhanced(self, company_registration: str) -> Dict[str, Any]:
        """
        Enhanced SIC prediction using your existing orchestrator + agents
        
        Workflow:
        1. Repository gets company data
        2. Your MultiAgentOrchestrator coordinates prediction
        3. Repository persists enhanced prediction
        4. Clean response with full agent insights
        """
        try:
            logger.info(f"Enhanced SIC prediction for company: {company_registration}")
            
            # Step 1: Get company data through repository
            company = self.company_repo.get_company_by_registration(company_registration)
            
            if company is None:
                return {
                    'success': False,
                    'error': f'Company not found: {company_registration}',
                    'prediction': None
                }
            
            # Step 2: Use your existing MultiAgentOrchestrator for coordination
            logger.info("Using MultiAgentOrchestrator for coordinated prediction")
            orchestrated_result = self.orchestrator.process_company(company)
            
            # Step 3: Extract prediction from orchestrated result
            if orchestrated_result and 'sic_prediction' in orchestrated_result:
                prediction_data = orchestrated_result['sic_prediction']
                
                suggested_sic = prediction_data.get('suggested_sic_code', '')
                confidence = prediction_data.get('confidence', 0.0)
                algorithm = prediction_data.get('algorithm', 'multi_agent_orchestrator')
                
                # Step 4: Persist enhanced prediction through repository
                update_success = self.company_repo.update_company_sic_prediction(
                    company_registration,
                    suggested_sic,
                    confidence,
                    algorithm
                )
                
                if update_success:
                    logger.info(f"Successfully updated SIC prediction: {suggested_sic} ({confidence:.2%})")
                    
                    return {
                        'success': True,
                        'company_registration': company_registration,
                        'company_name': company.get('company_name', ''),
                        'prediction': {
                            'suggested_sic_code': suggested_sic,
                            'confidence': confidence,
                            'algorithm': algorithm,
                            'previous_sic': company.get('predicted_sic', ''),
                            'previous_confidence': company.get('sic_confidence', 0.0)
                        },
                        'agent_insights': orchestrated_result,  # Full agent analysis
                        'updated_at': datetime.utcnow().isoformat(),
                        'enhanced_by_orchestrator': True
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to update SIC prediction in repository',
                        'prediction': prediction_data,
                        'agent_insights': orchestrated_result
                    }
            else:
                return {
                    'success': False,
                    'error': 'No SIC prediction generated by orchestrator',
                    'agent_insights': orchestrated_result
                }
                
        except Exception as e:
            logger.error(f"Error in enhanced SIC prediction: {e}")
            return {
                'success': False,
                'error': str(e),
                'prediction': None
            }
    
    def analyze_company_financials(self, company_registration: str, 
                                 company_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze company financials using your existing SmartFinancialExtractionAgent
        
        Benefits:
        - Uses your sophisticated financial extraction agent
        - Repository provides clean data access
        - Enhanced error handling and response formatting
        """
        try:
            logger.info(f"Analyzing financials for company: {company_registration}")
            
            # Step 1: Get company data if not provided
            if company_data is None:
                company = self.company_repo.get_company_by_registration(company_registration)
                if company is None:
                    return {
                        'success': False,
                        'error': f'Company not found: {company_registration}'
                    }
                company_data = company.to_dict()
            
            # Step 2: Use your existing SmartFinancialExtractionAgent
            logger.info("Using SmartFinancialExtractionAgent for financial analysis")
            financial_analysis = self.financial_agent.extract_financial_insights(company_data)
            
            # Step 3: Use your reasoning agent for additional context
            reasoning_analysis = self.reasoning_agent.analyze_financial_context(
                company_data, financial_analysis
            )
            
            return {
                'success': True,
                'company_registration': company_registration,
                'company_name': company_data.get('company_name', ''),
                'financial_insights': financial_analysis,
                'reasoning_analysis': reasoning_analysis,
                'analyzed_at': datetime.utcnow().isoformat(),
                'enhanced_by_agents': ['SmartFinancialExtractionAgent', 'AIReasoningAgent']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing company financials: {e}")
            return {
                'success': False,
                'error': str(e),
                'financial_insights': None
            }
    
    def search_companies_with_insights(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """
        Search companies with enhanced insights from your existing agents
        
        Workflow:
        1. Repository provides search capabilities
        2. Your agents enhance search results
        3. Clean response with agent insights
        """
        try:
            logger.info(f"Searching companies with insights: '{query}' (limit: {limit})")
            
            # Step 1: Search through repository
            search_results = self.company_repo.search_companies(query, limit)
            
            if search_results.empty:
                return {
                    'success': True,
                    'query': query,
                    'companies': [],
                    'total_found': 0,
                    'message': 'No companies found matching the query'
                }
            
            # Step 2: Enhance search results with your agents
            enhanced_results = []
            
            for _, company in search_results.iterrows():
                try:
                    # Basic company info
                    company_info = {
                        'registration': company.get('company_registration', ''),
                        'name': company.get('company_name', ''),
                        'address': company.get('company_address', ''),
                        'postcode': company.get('company_postcode', ''),
                        'current_sic': company.get('predicted_sic', ''),
                        'sic_confidence': company.get('sic_confidence', 0.0)
                    }
                    
                    # Enhance with sector insights if confidence is low
                    if company.get('sic_confidence', 0.0) < 0.8:
                        try:
                            sector_insights = self.sector_agent.quick_analysis(company)
                            company_info['sector_enhancement'] = sector_insights
                        except Exception as e:
                            logger.debug(f"Could not enhance sector insights: {e}")
                    
                    enhanced_results.append(company_info)
                    
                except Exception as e:
                    logger.warning(f"Error enhancing search result: {e}")
                    # Include basic result even if enhancement fails
                    enhanced_results.append({
                        'registration': company.get('company_registration', ''),
                        'name': company.get('company_name', ''),
                        'error': 'Enhancement failed'
                    })
            
            return {
                'success': True,
                'query': query,
                'companies': enhanced_results,
                'total_found': len(enhanced_results),
                'enhanced_by_agents': True,
                'searched_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced company search: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'companies': []
            }
    
    def get_sic_sector_analysis(self, sic_code: str) -> Dict[str, Any]:
        """
        Get sector analysis using your existing agents + repository data
        
        Benefits:
        - Repository provides SIC-filtered company data
        - Your agents provide sector insights and analysis
        - Clean aggregated response
        """
        try:
            logger.info(f"Getting SIC sector analysis for: {sic_code}")
            
            # Step 1: Get companies with this SIC code through repository
            companies_with_sic = self.company_repo.get_companies_by_sic_code(sic_code)
            
            if companies_with_sic.empty:
                return {
                    'success': True,
                    'sic_code': sic_code,
                    'companies_found': 0,
                    'message': f'No companies found with SIC code: {sic_code}'
                }
            
            # Step 2: Use your agents for sector analysis
            sector_analysis = self.sector_agent.analyze_sic_sector(
                sic_code, companies_with_sic
            )
            
            # Step 3: Use reasoning agent for insights
            reasoning_insights = self.reasoning_agent.analyze_sector_trends(
                sic_code, companies_with_sic, sector_analysis
            )
            
            return {
                'success': True,
                'sic_code': sic_code,
                'companies_found': len(companies_with_sic),
                'sector_analysis': sector_analysis,
                'reasoning_insights': reasoning_insights,
                'sample_companies': companies_with_sic.head(10).to_dict('records'),
                'analyzed_at': datetime.utcnow().isoformat(),
                'enhanced_by_agents': ['SectorClassificationAgent', 'AIReasoningAgent']
            }
            
        except Exception as e:
            logger.error(f"Error in SIC sector analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'sic_code': sic_code,
                'companies_found': 0
            }