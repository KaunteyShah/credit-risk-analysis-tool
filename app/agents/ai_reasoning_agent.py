"""
AI Reasoning Agent - Uses OpenAI to analyze company SIC code accuracy
"""
import os
from typing import Dict, Any, Optional
from openai import OpenAI
from app.agents.base_agent import BaseAgent, AgentResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIReasoningAgent(BaseAgent):
    """
    AI agent that analyzes company descriptions vs SIC codes to explain accuracy scores
    and provide improvement recommendations using OpenAI GPT models.
    """
    
    def __init__(self):
        super().__init__("AI Reasoning Agent")
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client with API key from environment."""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'dummy-key-for-local-testing':
                self.log_activity("No valid OpenAI API key found in environment", "WARNING")
                return
            
            self.client = OpenAI(
                api_key=api_key,
                timeout=5.0  # 5 second timeout to prevent hanging
            )
            self.log_activity("OpenAI client initialized successfully", "INFO")
            
        except Exception as e:
            self.log_activity(f"Failed to initialize OpenAI client: {str(e)}", "ERROR")
    
    def process(self, data: Dict[str, Any], **kwargs) -> AgentResult:
        """
        Analyze company data and provide AI reasoning for SIC code accuracy.
        
        Args:
            data: Dictionary containing:
                - company_name: Company name
                - company_description: Business description
                - current_sic: Current SIC code
                - old_accuracy: Current accuracy score
                - new_accuracy: Improved accuracy score (optional)
                - sic_description: SIC code description (optional)
        
        Returns:
            AgentResult with AI-generated reasoning
        """
        if not self.client:
            return self.create_result(
                success=False,
                error_message="OpenAI client not initialized. Please check API key."
            )
        
        try:
            # Extract required data
            company_name = data.get('company_name', 'Unknown Company')
            company_description = data.get('company_description', '')
            current_sic = data.get('current_sic', '')
            old_accuracy = data.get('old_accuracy', 0)
            new_accuracy = data.get('new_accuracy')
            sic_description = data.get('sic_description', '')
            
            # Generate AI reasoning
            reasoning = self._generate_reasoning(
                company_name,
                company_description,
                current_sic,
                old_accuracy,
                new_accuracy,
                sic_description
            )
            
            return self.create_result(
                success=True,
                data={
                    'reasoning': reasoning,
                    'analysis_type': 'sic_accuracy_analysis',
                    'company_name': company_name
                },
                confidence=0.8
            )
            
        except Exception as e:
            self.log_activity(f"Error processing AI reasoning: {str(e)}", "ERROR")
            return self.create_result(
                success=False,
                error_message=f"AI reasoning failed: {str(e)}"
            )
    
    def _generate_reasoning(
        self,
        company_name: str,
        company_description: str,
        current_sic: str,
        old_accuracy: float,
        new_accuracy: Optional[float] = None,
        sic_description: str = ""
    ) -> str:
        """Generate AI reasoning using OpenAI GPT."""
        
        # Build the prompt
        prompt = self._build_analysis_prompt(
            company_name,
            company_description,
            current_sic,
            old_accuracy,
            new_accuracy,
            sic_description
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst expert in SIC code classification. Provide clear, concise analysis of company-SIC code alignment with specific improvement suggestions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            reasoning = response.choices[0].message.content.strip()
            self.log_activity(f"Generated AI reasoning for {company_name}", "INFO")
            return reasoning
            
        except Exception as e:
            self.log_activity(f"OpenAI API call failed: {str(e)}", "ERROR")
            return self._generate_fallback_reasoning(
                company_name,
                old_accuracy,
                new_accuracy
            )
    
    def _build_analysis_prompt(
        self,
        company_name: str,
        company_description: str,
        current_sic: str,
        old_accuracy: float,
        new_accuracy: Optional[float] = None,
        sic_description: str = ""
    ) -> str:
        """Build the analysis prompt for OpenAI."""
        
        prompt = f"""Analyze the SIC code accuracy for this company:

Company: {company_name}
Business Description: {company_description or 'Not provided'}
Current SIC Code: {current_sic}
{f'SIC Description: {sic_description}' if sic_description else ''}
Current Accuracy Score: {old_accuracy}%
{f'Improved Accuracy Score: {new_accuracy}%' if new_accuracy else ''}

Please provide a brief analysis covering:
1. How well the current SIC code matches the company's business description
2. Why the accuracy score is {old_accuracy}% (specific reasons)
3. {f'What improvements led to {new_accuracy}% accuracy' if new_accuracy else 'Specific suggestions to improve the SIC code classification'}

Keep the response concise but insightful, focused on actionable business insights."""
        
        return prompt
    
    def _generate_fallback_reasoning(
        self,
        company_name: str,
        old_accuracy: float,
        new_accuracy: Optional[float] = None
    ) -> str:
        """Generate fallback reasoning when OpenAI is unavailable."""
        
        if old_accuracy >= 85:
            quality = "excellent"
            reason = f"The SIC code classification for {company_name} shows excellent accuracy ({old_accuracy}%). This indicates a strong alignment between the company's business activities and the assigned SIC code. The business description clearly matches the industry classification standards."
            suggestion = "The current classification is highly accurate. Minor documentation updates could maintain this high standard."
        elif old_accuracy >= 75:
            quality = "good" 
            reason = f"The SIC code classification for {company_name} demonstrates good accuracy ({old_accuracy}%). There is a solid match between the business description and the SIC code, with only minor discrepancies."
            suggestion = "Consider reviewing specific business activities to identify areas for improved alignment with SIC classification criteria."
        elif old_accuracy >= 60:
            quality = "moderate"
            reason = f"The SIC code accuracy for {company_name} is moderate ({old_accuracy}%). This suggests some inconsistencies between the company's described business activities and the current SIC code classification."
            suggestion = "Review the company's primary business activities and consider whether the current SIC code fully represents the main revenue-generating operations."
        else:
            quality = "low"
            reason = f"The SIC code classification for {company_name} shows low accuracy ({old_accuracy}%). This indicates a significant mismatch between the company's actual business activities and the assigned SIC code."
            suggestion = "A comprehensive review of business activities is recommended. The current SIC code may not accurately reflect the company's primary operations and should be reassessed."
        
        analysis = f"{reason}\n\n**Assessment**: {suggestion}"
        
        if new_accuracy:
            improvement = new_accuracy - old_accuracy
            analysis += f"\n\n**Recent Improvements**: Updated classification has increased accuracy to {new_accuracy}% (+" + f"{improvement:.1f}%), showing progress in alignment."
        
        return analysis


# Singleton instance for global use
ai_reasoning_agent = AIReasoningAgent()