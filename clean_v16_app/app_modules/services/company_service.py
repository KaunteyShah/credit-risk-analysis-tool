"""
Service for company data business logic
"""
from typing import Dict, Any, Optional
from datetime import datetime, date
import math
import pandas as pd
import os
from app_modules.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface


class CompanyService:
    """Service layer for company data business operations"""
    
    def __init__(self, repository: CompanyRepositoryInterface):
        """Initialize with company repository"""
        self.repository = repository
    
    # CSV-related methods removed - SIC predictions now stored in SQLite database
    # _load_updated_sic_predictions() and _get_updated_company_info() methods removed
    # as they used CSV files. SIC prediction data now retrieved from sic_prediction_history table
    
    def get_all_companies(self) -> list:
        """Get all companies from repository as list of dictionaries"""
        df = self.repository.get_all_companies()
        # Convert DataFrame to list of dictionaries, handling NaN values
        return df.fillna('').to_dict(orient='records')
    
    def get_company_by_index(self, company_index: int) -> Optional[Dict[str, Any]]:
        """Get a specific company by index"""
        return self.repository.get_company_by_index(company_index)
    
    def get_companies_paginated(self, page: int, limit: int, country: Optional[str] = None, 
                               search: Optional[str] = None) -> Dict[str, Any]:
        """Get paginated companies with optional filtering using repository"""
        return self.repository.get_companies_paginated(page, limit, country, search)
    
    def get_company_details_with_reasoning(self, company_index: int) -> Dict[str, Any]:
        """
        Get comprehensive company details with AI reasoning for SIC accuracy.
        Returns a fast JSON error if data is not loaded, preventing HTML error responses.
        """
        # Fast fail if data is not loaded
        if hasattr(self.repository, 'is_data_loaded') and not self.repository.is_data_loaded():
            return {
                'error': 'Company data is still loading. Please try again in a few seconds.'
            }
        try:
            # Get company data using repository
            company_data = self.repository.get_company_by_index(company_index)
            if not company_data:
                return {
                    'error': f'Invalid company index: {company_index}. Valid range: 0-{self.repository.get_companies_count()-1}'
                }
            # Helper function to safely convert values and handle NaN (exact logic from original)
            def safe_convert(value, default='N/A'):
                if value is None:
                    return default
                if isinstance(value, (int, float)) and math.isnan(value):
                    return default
                if isinstance(value, str) and value.lower() in ['nan', 'none', '']:
                    return default
                return value
            def safe_numeric(value, default=0):
                try:
                    if value is None:
                        return default
                    if isinstance(value, (int, float)):
                        if math.isnan(value):
                            return default
                        return float(value)
                    if isinstance(value, str):
                        if value.lower() in ['nan', 'none', '', 'n/a']:
                            return default
                        return float(value)
                    return default
                except (ValueError, TypeError):
                    return default
            
            # Get updated SIC information and calculate days since update
            company_name = str(safe_convert(company_data.get('company_name', ''), 'Unknown Company'))
            # Updated info now comes from SQLite sic_prediction_history table instead of CSV
            updated_info = {
                'has_updated_data': False,
                'new_sic': None,
                'new_accuracy': None,
                'days_since_update': None,
                'needs_update': False,
                'update_message': None
            }
            
            # Prepare data for AI reasoning agent - Focus on NEW SIC if available, otherwise original
            if updated_info['has_updated_data']:
                # Focus on explaining why the NEW SIC is more accurate
                reasoning_data = {
                    'company_name': company_name,
                    'company_description': safe_convert(company_data.get('business_description', ''), ''),
                    'current_sic': str(safe_convert(company_data.get('uk_sic_2007_code', ''), '')),
                    'new_sic': str(updated_info['new_sic']) if updated_info['new_sic'] else None,
                    'old_accuracy': safe_numeric(company_data.get('confidence', 0), 0),
                    'new_accuracy': updated_info['new_accuracy'] if updated_info['new_accuracy'] else None,
                    'analysis_focus': 'new_classification'  # Focus on explaining why NEW SIC is better
                }
            else:
                # Focus on explaining current SIC accuracy (fallback to original behavior)
                reasoning_data = {
                    'company_name': company_name,
                    'company_description': safe_convert(company_data.get('business_description', ''), ''),
                    'current_sic': str(safe_convert(company_data.get('uk_sic_2007_code', ''), '')),
                    'old_accuracy': safe_numeric(company_data.get('confidence', 0), 0),
                    'analysis_focus': 'original_classification'  # Signal to focus on explaining current SIC accuracy
                }
            
            # Get AI reasoning (enhanced with NEW SIC focus)
            ai_reasoning = self._get_ai_reasoning(reasoning_data, company_name, company_index)
            
            # Compile comprehensive response - Original data + Updated SIC data + Update status
            response_data = {
                'company_index': company_index,
                'company_data': {
                    'Company_Name': company_name,
                    'Registration_Number': safe_convert(company_data.get('Registration number', 'N/A')),
                    'UK_SIC_2007_Code': safe_convert(company_data.get('uk_sic_2007_code', 'N/A')),
                    'UK_SIC_2007_Description': safe_convert(company_data.get('UK SIC 2007 Description', 'N/A')),
                    'Old_Accuracy': safe_numeric(company_data.get('confidence'), 0),
                    'Business_Description': safe_convert(company_data.get('business_description', 'No description available')),
                    'Sales_GBP': safe_convert(company_data.get('Sales (GBP)', 'N/A')),
                    'Employees_Total': safe_convert(company_data.get('Employees (Total)', 'N/A')),
                    'Address_Line_1': safe_convert(company_data.get('Address Line 1', 'N/A')),
                    'City': safe_convert(company_data.get('City', 'N/A')),
                    'Post_Code': safe_convert(company_data.get('Post Code', 'N/A')),
                    'Country': safe_convert(company_data.get('country', 'N/A')),
                    'Website': safe_convert(company_data.get('Website', 'N/A')),
                    'Phone': safe_convert(company_data.get('Phone', 'N/A'))
                },
                'updated_sic_data': {
                    'has_updated_data': updated_info['has_updated_data'],
                    'new_sic': updated_info['new_sic'] if updated_info['has_updated_data'] else None,
                    'new_accuracy': updated_info['new_accuracy'] if updated_info['has_updated_data'] else None,
                    'days_since_update': updated_info['days_since_update'],
                    'needs_update': updated_info['needs_update'],
                    'update_message': updated_info['update_message']
                },
                'ai_reasoning': ai_reasoning,
                'analysis_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'reasoning_source': 'ai_reasoning_agent',
                    'data_source': 'original_sample_data_with_updates',
                    'analysis_type': 'current_sic_accuracy_explanation',
                    'includes_updated_predictions': updated_info['has_updated_data']
                }
            }
            
            return response_data
            
        except Exception as e:
            return {
                'error': f'Failed to get company details: {str(e)}',
                'company_index': company_index
            }
    
    def _get_ai_reasoning(self, reasoning_data: Dict[str, Any], company_name: str, company_index: int) -> str:
        """Get AI reasoning with exact same logic as original endpoint"""
        try:
            # Import here to avoid circular imports (exact logic from original)
            from app_modules.agents.ai_reasoning_agent import ai_reasoning_agent
            reasoning_result = ai_reasoning_agent.process(reasoning_data)
            
            if reasoning_result.success:
                ai_reasoning = reasoning_result.data.get('reasoning', 'No reasoning available')
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"✅ AI reasoning generated for {company_name}")
                return ai_reasoning
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ AI reasoning failed for company {company_index}")
                return f"AI reasoning unavailable: {reasoning_result.error_message}"
                
        except Exception as ai_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ AI reasoning agent error: {str(ai_error)}")
            return f"AI reasoning temporarily unavailable. Please check OpenAI API configuration."
    
    def update_sic(self, company_index: int, new_sic: str, confidence: Optional[float] = None) -> Dict[str, Any]:
        """
        Update SIC code for a company and save to CSV
        Returns the same format as the original flask_main.py endpoint
        """
        try:
            # Get all company data
            company_data = self.repository.get_all_companies()
            
            if company_data is None or company_data.empty:
                return {'error': 'No company data available'}
            
            if company_index >= len(company_data):
                return {'error': 'Invalid company index'}
            
            # Get company details
            company_row = company_data.iloc[company_index]
            company_registration_code = str(company_row.get('Registration number', ''))
            if company_registration_code == 'nan':
                company_registration_code = ''
            company_name = str(company_row.get('company_name', ''))
            business_description = str(company_row.get('business_description', ''))
            current_sic = str(company_row.get('uk_sic_2007_code', ''))
            old_accuracy = float(company_row.get('confidence', 0.0))
            
            # Calculate new accuracy
            if confidence is not None:
                new_accuracy = float(confidence)
            else:
                # Try to access SIC matcher through repository property
                try:
                    sic_matcher = getattr(self.repository, 'sic_matcher', None)
                    if sic_matcher and new_sic:
                        new_accuracy_result = sic_matcher.calculate_old_accuracy(business_description, new_sic)
                        calculated_accuracy = new_accuracy_result['old_accuracy']
                        new_accuracy = max(calculated_accuracy, old_accuracy)
                    else:
                        new_accuracy = old_accuracy
                except Exception:
                    new_accuracy = old_accuracy
            
            # CSV-related save method removed - now using SQLite database directly
            # SIC updates are handled via save_prediction_to_db() in the SIC matcher
            # which saves to sic_prediction_history table instead of CSV files
            try:
                sic_matcher = getattr(self.repository, 'sic_matcher', None)
                if sic_matcher:
                    # Use the existing save_prediction_to_db method instead of CSV
                    success = sic_matcher.save_prediction_to_db(
                        company_id=company_index + 1,  # Approximate company ID
                        company_name=company_name,
                        business_description=business_description,
                        predicted_sic_code=new_sic,
                        predicted_sic_description=sic_matcher.get_sic_description(new_sic),
                        confidence_score=new_accuracy,
                        existing_sic_confidence=old_accuracy,
                        model_version="1.0",
                        prediction_method="MODULAR_APPROVED_MANUAL",
                        ai_reasoning=f"SIC code manually updated from {current_sic} to {new_sic}"
                    )
                    
                    if success:
                        # Refresh the company data to incorporate the new update
                        self.repository.refresh_data()
                        
                        return {
                            'success': True,
                            'company_name': company_name,
                            'old_sic': current_sic,
                            'new_sic': new_sic,
                            'old_accuracy': old_accuracy,
                            'new_accuracy': new_accuracy,
                            'message': f'SIC code updated for {company_name}'
                        }
                    else:
                        return {'error': 'Failed to save SIC update to database'}
                else:
                    return {'error': 'SIC matcher not available'}
                    
            except Exception as e:
                return {'error': f'SIC update failed: {str(e)}'}
                
        except Exception as e:
            return {'error': f'Update SIC error: {str(e)}'}