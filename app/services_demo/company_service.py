"""
Company Service - Clean Business Logic Layer

This service demonstrates how business logic becomes clean and testable
when separated from data access using the repository pattern.

Compare this to the mixed data access + business logic in flask_main.py.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from app.repositories.interfaces.company_repository_interface import CompanyRepositoryInterface

class CompanyService:
    """
    Clean business logic service for company operations.
    
    Notice: This service has NO knowledge of files, databases, or storage.
    It only knows about the CompanyRepositoryInterface contract.
    """
    
    def __init__(self, company_repository: CompanyRepositoryInterface):
        """
        Initialize service with repository dependency.
        
        The repository can be FileCompanyRepository, SQLiteCompanyRepository,
        or any other implementation - this service doesn't care!
        """
        self.company_repo = company_repository
    
    def get_all_companies(self) -> Dict[str, Any]:
        """
        Get all companies with business logic processing.
        
        This is pure business logic - no file I/O mixed in!
        """
        try:
            # Get data from repository (interface - could be files or database)
            companies = self.company_repo.get_all_companies()
            
            # Apply business logic
            processed_companies = self._add_business_calculations(companies)
            enhanced_companies = self._add_risk_indicators(processed_companies)
            
            return {
                'success': True,
                'data': enhanced_companies.to_dict('records'),
                'total_count': len(enhanced_companies),
                'summary_stats': self._calculate_summary_statistics(enhanced_companies),
                'data_source': self._get_data_source_info()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'total_count': 0
            }
    
    def get_company_details(self, registration: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific company.
        
        Pure business logic - repository handles the data access.
        """
        try:
            # Get company data (could come from files or database)
            company = self.company_repo.get_company_by_registration(registration)
            
            if not company:
                return {
                    'success': False,
                    'error': f'Company {registration} not found',
                    'data': None
                }
            
            # Apply business logic enhancements
            enhanced_company = self._enhance_company_data(company)
            risk_analysis = self._calculate_risk_metrics(company)
            similar_companies = self._find_similar_companies(company)
            
            return {
                'success': True,
                'data': enhanced_company,
                'risk_analysis': risk_analysis,
                'similar_companies': similar_companies,
                'recommendations': self._generate_recommendations(company)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def predict_company_sic(self, registration: str, business_description: str) -> Dict[str, Any]:
        """
        Predict SIC code for a company.
        
        Business logic for SIC prediction - repository handles storage.
        """
        try:
            # Verify company exists (repository handles lookup)
            company = self.company_repo.get_company_by_registration(registration)
            if not company:
                return {
                    'success': False,
                    'error': f'Company {registration} not found'
                }
            
            # Business logic: SIC prediction algorithm
            prediction_result = self._run_sic_prediction_algorithm(business_description)
            
            # Business logic: confidence validation
            if prediction_result['confidence'] < 0.5:
                return {
                    'success': False,
                    'error': 'SIC prediction confidence too low',
                    'prediction': prediction_result
                }
            
            # Update via repository (could save to files or database)
            success = self.company_repo.update_company_sic_prediction(
                registration,
                prediction_result['sic_code'],
                prediction_result['confidence'],
                'neural_network_v2'
            )
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to update company SIC prediction'
                }
            
            return {
                'success': True,
                'prediction': prediction_result,
                'company_registration': registration,
                'updated': True,
                'data_source': self._get_data_source_info()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_companies(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search companies with business logic filtering.
        
        Repository handles data access, service handles business rules.
        """
        try:
            # Get search results from repository
            if filters and 'sic_code' in filters:
                companies = self.company_repo.get_companies_by_sic_code(filters['sic_code'])
            else:
                companies = self.company_repo.search_companies_by_name(query)
            
            # Apply business logic filtering
            filtered_companies = self._apply_business_filters(companies, filters or {})
            ranked_companies = self._rank_search_results(filtered_companies, query)
            
            return {
                'success': True,
                'data': ranked_companies.to_dict('records'),
                'total_count': len(ranked_companies),
                'search_query': query,
                'filters_applied': filters or {},
                'data_source': self._get_data_source_info()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    def get_revenue_insights(self) -> Dict[str, Any]:
        """
        Get revenue insights and analytics.
        
        Pure business intelligence logic - no data access concerns.
        """
        try:
            # Get revenue statistics from repository
            revenue_stats = self.company_repo.get_revenue_statistics()
            all_companies = self.company_repo.get_all_companies()
            
            # Apply business intelligence algorithms
            revenue_distribution = self._analyze_revenue_distribution(all_companies)
            growth_predictions = self._predict_revenue_growth_trends(all_companies)
            industry_benchmarks = self._calculate_industry_benchmarks(all_companies)
            
            return {
                'success': True,
                'statistics': revenue_stats,
                'distribution': revenue_distribution,
                'growth_predictions': growth_predictions,
                'industry_benchmarks': industry_benchmarks,
                'insights': self._generate_revenue_insights(revenue_stats)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Private business logic methods (no data access!)
    
    def _add_business_calculations(self, companies: pd.DataFrame) -> pd.DataFrame:
        """Add calculated business metrics"""
        enhanced = companies.copy()
        
        # Business logic: Calculate revenue per employee
        if 'Sales (USD)' in enhanced.columns and 'Employees (Total)' in enhanced.columns:
            enhanced['Revenue_Per_Employee'] = (
                enhanced['Sales (USD)'] / enhanced['Employees (Total)']
            ).fillna(0)
        
        # Business logic: Categorize company size
        if 'Employees (Total)' in enhanced.columns:
            enhanced['Company_Size'] = enhanced['Employees (Total)'].apply(
                lambda x: 'Large' if x > 500 else 'Medium' if x > 50 else 'Small'
            )
        
        return enhanced
    
    def _add_risk_indicators(self, companies: pd.DataFrame) -> pd.DataFrame:
        """Add risk assessment indicators"""
        enhanced = companies.copy()
        
        # Business logic: Risk score calculation
        enhanced['Risk_Score'] = 50  # Base risk score
        
        # Adjust based on SIC prediction confidence
        if 'Old_Accuracy' in enhanced.columns:
            enhanced['Risk_Score'] += (enhanced['Old_Accuracy'] - 70) * 0.5
        
        # Risk category
        enhanced['Risk_Category'] = enhanced['Risk_Score'].apply(
            lambda x: 'Low' if x < 40 else 'Medium' if x < 70 else 'High'
        )
        
        return enhanced
    
    def _run_sic_prediction_algorithm(self, business_description: str) -> Dict[str, Any]:
        """Business logic: SIC prediction algorithm"""
        # This is where your actual SIC prediction logic would go
        # For demo purposes, return mock prediction
        return {
            'sic_code': '72110',  # Computer programming activities
            'confidence': 0.87,
            'alternatives': [
                {'sic_code': '72200', 'confidence': 0.76},
                {'sic_code': '62020', 'confidence': 0.69}
            ],
            'algorithm': 'neural_network_v2'
        }
    
    def _get_data_source_info(self) -> str:
        """Get information about current data source"""
        # This could check configuration to determine if using files or database
        return "file_based"  # For now, since we're using file repository
    
    def _enhance_company_data(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance company data with additional calculations"""
        enhanced = company.copy()
        # Add business logic enhancements here
        return enhanced
    
    def _calculate_risk_metrics(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk metrics for company"""
        # Business logic for risk calculation
        return {
            'credit_score': 85,
            'financial_stability': 'Good',
            'industry_risk': 'Medium'
        }
    
    def _find_similar_companies(self, company: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar companies"""
        # Business logic to find similar companies
        return []
    
    def _generate_recommendations(self, company: Dict[str, Any]) -> List[str]:
        """Generate business recommendations"""
        return [
            "Consider expanding into related SIC categories",
            "Monitor revenue growth trends",
            "Review risk assessment quarterly"
        ]
    
    def _calculate_summary_statistics(self, companies: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics"""
        return {
            'total_companies': len(companies),
            'average_employees': companies['Employees (Total)'].mean() if 'Employees (Total)' in companies.columns else 0,
            'industries_covered': companies['SIC_Code'].nunique() if 'SIC_Code' in companies.columns else 0
        }
    
    def _apply_business_filters(self, companies: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply business logic filters"""
        filtered = companies.copy()
        
        if filters:
            if 'min_employees' in filters:
                filtered = filtered[filtered['Employees (Total)'] >= filters['min_employees']]
            if 'max_employees' in filters:
                filtered = filtered[filtered['Employees (Total)'] <= filters['max_employees']]
        
        return filtered
    
    def _rank_search_results(self, companies: pd.DataFrame, query: str) -> pd.DataFrame:
        """Rank search results by relevance"""
        # Business logic for ranking
        return companies.head(50)  # Return top 50 results
    
    def _analyze_revenue_distribution(self, companies: pd.DataFrame) -> Dict[str, Any]:
        """Analyze revenue distribution patterns"""
        return {'distribution_type': 'normal', 'skewness': 1.2}
    
    def _predict_revenue_growth_trends(self, companies: pd.DataFrame) -> Dict[str, Any]:
        """Predict revenue growth trends"""
        return {'predicted_growth': 5.2, 'confidence': 0.78}
    
    def _calculate_industry_benchmarks(self, companies: pd.DataFrame) -> Dict[str, Any]:
        """Calculate industry benchmarks"""
        return {'industry_avg_revenue': 2500000, 'top_quartile': 8500000}
    
    def _generate_revenue_insights(self, revenue_stats: Dict[str, Any]) -> List[str]:
        """Generate revenue insights"""
        return [
            "Revenue distribution shows healthy diversity",
            "Top performers significantly outpace average",
            "Consider focusing on high-growth sectors"
        ]