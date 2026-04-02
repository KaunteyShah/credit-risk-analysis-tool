"""
AI Reasoning Agent - Uses Azure OpenAI to analyze company SIC code accuracy
"""
import os
import pandas as pd
from typing import Dict, Any, Optional
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False
    
from app_modules.agents.base_agent import BaseAgent, AgentResult
from app_modules.utils.logger import get_logger
from app_modules.utils.config_manager import ConfigManager

logger = get_logger(__name__)


class AIReasoningAgent(BaseAgent):
    """
    AI agent that analyzes company descriptions vs SIC codes to explain accuracy scores
    and provide improvement recommendations using OpenAI GPT models.
    """
    
    def __init__(self):
        super().__init__("AI Reasoning Agent")
        self.client = None
        self.config = ConfigManager()
        self.reasoning_cache = {}  # Simple cache for reasoning results
        self.sic_descriptions = {}  # Cache for SIC descriptions
        self._initialize_client()
        self._load_sic_descriptions()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client with API key from ConfigManager (Azure Key Vault)."""
        try:
            if not AZURE_OPENAI_AVAILABLE:
                self.log_activity("Azure OpenAI not available - AI reasoning disabled", "WARNING")
                return
                
            # Get Azure OpenAI configuration from ConfigManager and environment
            api_key = self.config.get('openai.api_key')
            azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT', 'https://data-risk-modernisation-oai.openai.azure.com/')
            api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
            
            if not api_key or api_key == 'dummy-key-for-local-testing' or len(api_key) < 20:
                self.log_activity("No valid OpenAI API key found in ConfigManager", "WARNING")
                return
            

            
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=api_version or "2024-02-15-preview",
                timeout=30.0
            )
            self.log_activity("Azure OpenAI client initialized successfully with ConfigManager key", "INFO")
            
        except Exception as e:
            self.log_activity(f"Failed to initialize Azure OpenAI client: {str(e)}", "ERROR")
    
    def _load_sic_descriptions(self):
        """Load SIC code descriptions from the Excel file."""
        try:
            sic_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'data', 'SIC_codes.xlsx'
            )
            
            if os.path.exists(sic_file_path):
                df = pd.read_excel(sic_file_path)
                # First column is SIC code, second column is description
                for _, row in df.iterrows():
                    sic_code = str(row.iloc[0])  # First column
                    description = str(row.iloc[1])  # Second column
                    self.sic_descriptions[sic_code] = description
                
                self.log_activity(f"Loaded {len(self.sic_descriptions)} SIC descriptions", "INFO")
            else:
                self.log_activity(f"SIC codes file not found at {sic_file_path}", "WARNING")
                
        except Exception as e:
            self.log_activity(f"Error loading SIC descriptions: {str(e)}", "ERROR")
    
    def _get_sic_description(self, sic_code: str) -> str:
        """Get description for a SIC code."""
        if not sic_code:
            return ""
        
        # Try exact match first
        sic_str = str(sic_code)
        if sic_str in self.sic_descriptions:
            return self.sic_descriptions[sic_str]
        
        # Try without leading zeros or with leading zeros
        try:
            sic_int = int(float(sic_code))
            sic_padded = f"{sic_int:05d}"  # 5-digit format
            sic_unpadded = str(sic_int)
            
            if sic_padded in self.sic_descriptions:
                return self.sic_descriptions[sic_padded]
            elif sic_unpadded in self.sic_descriptions:
                return self.sic_descriptions[sic_unpadded]
        except (ValueError, TypeError):
            pass
        
        return f"Description not found for SIC code {sic_code}"
    
    def process(self, data: Dict[str, Any], **kwargs) -> AgentResult:
        """
        Analyze company data and provide AI reasoning for SIC code accuracy.
        
        Args:
            data: Dictionary containing:
                - company_name: Company name
                - company_description: Business description
                - current_sic: Current/old SIC code
                - new_sic: New/updated SIC code (if available)
                - old_accuracy: Current accuracy score
                - new_accuracy: Updated accuracy score (if available)
                - analysis_focus: 'new_classification' or 'original_classification'
        
        Returns:
            AgentResult with AI-generated reasoning
        """
        try:
            # Extract required data
            company_name = data.get('company_name', 'Unknown Company')
            company_description = data.get('company_description', '')
            current_sic = data.get('current_sic', '')
            new_sic = data.get('new_sic')
            old_accuracy = data.get('old_accuracy', 0)
            new_accuracy = data.get('new_accuracy')
            analysis_focus = data.get('analysis_focus', 'original_classification')
            
            # Determine which SIC code to focus on
            focus_sic = new_sic if new_sic and analysis_focus == 'new_classification' else current_sic
            focus_accuracy = new_accuracy if new_accuracy and analysis_focus == 'new_classification' else old_accuracy
            
            # Get SIC descriptions
            current_sic_desc = self._get_sic_description(current_sic)
            new_sic_desc = self._get_sic_description(new_sic) if new_sic else ""
            
            # Create cache key
            cache_key = f"{company_name}_{focus_sic}_{focus_accuracy}_{analysis_focus}"
            
            # DISABLE CACHE for real-time generation - always generate fresh reasoning
            # Clear cache to ensure fresh generation
            if cache_key in self.reasoning_cache:
                self.log_activity(f"Bypassing cache for real-time generation: {company_name}", "INFO")
                # Remove from cache to force regeneration
                del self.reasoning_cache[cache_key]
            # Generate AI reasoning (try OpenAI first, fallback if needed) - ALWAYS FRESH
            if self.client:
                reasoning = self._generate_reasoning(
                    company_name,
                    company_description,
                    current_sic,
                    new_sic,
                    old_accuracy,
                    new_accuracy,
                    current_sic_desc,
                    new_sic_desc,
                    analysis_focus
                )
                self.log_activity(f"Generated FRESH AI reasoning for {company_name}", "INFO")
            else:
                self.log_activity("Using fallback reasoning - OpenAI client not available", "INFO")
                reasoning = self._generate_fallback_reasoning(
                    company_name,
                    company_description,
                    current_sic,
                    new_sic,
                    old_accuracy,
                    new_accuracy,
                    current_sic_desc,
                    new_sic_desc,
                    analysis_focus
                )
            
            # DO NOT CACHE - always generate fresh for real-time behavior
            # self.reasoning_cache[cache_key] = reasoning  # DISABLED
            
            return self.create_result(
                success=True,
                data={
                    'reasoning': reasoning,
                    'analysis_type': f'{analysis_focus}_sic_analysis',
                    'company_name': company_name,
                    'focus_sic': focus_sic,
                    'focus_accuracy': focus_accuracy
                },
                confidence=0.8 if self.client else 0.6  # Lower confidence for fallback
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
        new_sic: Optional[str] = None,
        old_accuracy: float = 0,
        new_accuracy: Optional[float] = None,
        current_sic_desc: str = "",
        new_sic_desc: str = "",
        analysis_focus: str = "original_classification"
    ) -> str:
        """Generate AI reasoning using OpenAI GPT."""
        
        # Build the prompt
        prompt = self._build_analysis_prompt(
            company_name,
            company_description,
            current_sic,
            new_sic,
            old_accuracy,
            new_accuracy,
            current_sic_desc,
            new_sic_desc,
            analysis_focus
        )
        
        # Debug: Print the prompt and old_accuracy value
        print(f"🔍 DEBUG AI Agent - old_accuracy value: {old_accuracy} (type: {type(old_accuracy)})")
        print(f"🔍 DEBUG AI Agent - Prompt being sent:\n{prompt[:500]}...")
        
        try:
            if self.client is None:
                raise Exception("OpenAI client not initialized")
                
            response = self.client.chat.completions.create(
                model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo'),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst expert in UK SIC code classification. Provide natural, conversational analysis of company business models and how they align with different SIC classifications. Write in a professional but varied style, avoiding repetitive phrases or templates. Focus on the specific business activities and why certain classifications are more suitable."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            if response.choices and response.choices[0].message.content:
                reasoning = response.choices[0].message.content.strip()
                self.log_activity(f"Generated AI reasoning for {company_name}", "INFO")
                return reasoning
            else:
                raise Exception("Empty response from OpenAI")
            
        except Exception as e:
            self.log_activity(f"OpenAI API call failed: {str(e)}", "ERROR")
            return self._generate_fallback_reasoning(
                company_name,
                company_description,
                current_sic,
                new_sic,
                old_accuracy,
                new_accuracy,
                current_sic_desc,
                new_sic_desc,
                analysis_focus
            )
    
    def _build_analysis_prompt(
        self,
        company_name: str,
        company_description: str,
        current_sic: str,
        new_sic: Optional[str] = None,
        old_accuracy: float = 0,
        new_accuracy: Optional[float] = None,
        current_sic_desc: str = "",
        new_sic_desc: str = "",
        analysis_focus: str = "original_classification"
    ) -> str:
        """Build the analysis prompt for OpenAI."""
        
        if analysis_focus == 'new_classification' and new_sic and new_accuracy:
            # Focus on explaining why the predicted SIC code is more appropriate
            prompt = f"""Analyze the SIC code classification for {company_name}:

Business Description: {company_description or 'Not provided'}

Current Classification: SIC {current_sic} - {current_sic_desc} (Confidence: {old_accuracy}%)
Recommended Classification: SIC {new_sic} - {new_sic_desc} (Confidence: {new_accuracy}%)

Based on the business description, explain why SIC code {new_sic} would be more appropriate than the current {current_sic} classification. Consider:
- Which business activities align better with the recommended classification
- How the company's operations fit the new SIC category
- What makes the recommended SIC code a better match for this business model

Provide a natural, conversational analysis without using formulaic phrases like "NEW SIC" or "previous SIC"."""

        else:
            # Focus on explaining WHY the current SIC accuracy is what it is
            if old_accuracy < 70:
                focus_instruction = f"""The accuracy is relatively low at {old_accuracy}%. Focus on explaining:
1. Specific misalignments between the business description and SIC classification
2. Which business activities don't fit well with the current SIC code
3. What aspects of the company's operations suggest a different industry classification
4. Why this SIC code creates uncertainty in classification"""
            elif old_accuracy < 85:
                focus_instruction = f"""The accuracy is moderate at {old_accuracy}%. Focus on explaining:
1. Areas where the business description partially aligns with the SIC classification
2. Which aspects of the business fit well vs. which don't
3. Specific business activities that create classification uncertainty
4. Why the SIC code is somewhat but not perfectly suited"""
            else:
                focus_instruction = f"""The accuracy is high at {old_accuracy}%. Focus on explaining:
1. Strong alignments between the business description and SIC classification
2. Which business activities clearly match the SIC code category
3. Why this SIC code is well-suited for this company
4. What makes this classification confident and accurate"""

            prompt = f"""Analyze WHY the SIC code accuracy is {old_accuracy}% for this company:

Company: {company_name}
Business Description: {company_description or 'Not provided'}
Current SIC Code: {current_sic}
SIC Description: {current_sic_desc}
Current Accuracy Score: {old_accuracy}%

{focus_instruction}

Provide a 4-5 line analysis that explains the reasoning behind the accuracy score, focusing on specific business alignment factors."""
        
        return prompt
    
    def _generate_fallback_reasoning(
        self,
        company_name: str,
        company_description: str = "",
        current_sic: str = "",
        new_sic: Optional[str] = None,
        old_accuracy: float = 0,
        new_accuracy: Optional[float] = None,
        current_sic_desc: str = "",
        new_sic_desc: str = "",
        analysis_focus: str = "original_classification"
    ) -> str:
        """Generate fallback reasoning when OpenAI is unavailable."""
        
        if analysis_focus == 'new_classification' and new_sic and new_accuracy:
            # Focus on the NEW SIC code improvement
            improvement = new_accuracy - old_accuracy
            
            if improvement >= 15:
                improvement_level = "significant"
            elif improvement >= 10:
                improvement_level = "substantial" 
            elif improvement >= 5:
                improvement_level = "moderate"
            else:
                improvement_level = "minor"
            
            analysis = f"""The updated SIC classification for {company_name} shows {improvement_level} improvement (from {old_accuracy}% to {new_accuracy}%).

**NEW SIC Code**: {new_sic} - {new_sic_desc}

**Why it's more accurate**: The new classification better captures the company's primary business activities. The updated SIC code aligns more closely with the business description, particularly in terms of industry sector and operational focus.

**Key improvement**: The {improvement:.1f} percentage point increase in accuracy indicates that the new SIC code ({new_sic}) provides a more precise classification than the previous code ({current_sic}), resulting in better business categorization for regulatory and analytical purposes."""

        else:
            # Focus on WHY the current/original SIC accuracy is what it is
            if old_accuracy >= 85:
                quality = "excellent"
                reason = f"The SIC code classification for {company_name} shows excellent accuracy ({old_accuracy}%). The business description strongly aligns with the SIC classification, indicating clear industry sector alignment and well-defined operational focus."
                analysis_detail = "Key business activities directly correspond to the SIC code definition, creating high confidence in classification."
                suggestion = "The current classification demonstrates strong business-to-code alignment with minimal ambiguity."
            elif old_accuracy >= 75:
                quality = "good" 
                reason = f"The SIC code classification for {company_name} demonstrates good accuracy ({old_accuracy}%). Most business activities align well with the SIC code, but some secondary operations may create minor classification uncertainty."
                analysis_detail = "The primary business focus matches the SIC category, though some diversified activities may not be fully captured."
                suggestion = "Consider reviewing secondary business activities that may not fit perfectly within the current SIC scope."
            elif old_accuracy >= 60:
                quality = "moderate"
                reason = f"The SIC code accuracy for {company_name} is moderate ({old_accuracy}%). This suggests mixed alignment - some business activities fit well within the SIC classification while others indicate potential cross-industry operations."
                analysis_detail = "The company likely operates across multiple business segments, making single SIC classification challenging."
                suggestion = "Review the company's primary vs. secondary revenue streams to identify the most dominant business activities for SIC alignment."
            else:
                quality = "low"
                reason = f"The SIC code classification for {company_name} shows low accuracy ({old_accuracy}%). This indicates significant misalignment between the company's actual business activities and the assigned SIC code classification."
                analysis_detail = "The business description suggests operations that don't clearly fit within the current SIC category, indicating either business evolution, diversification, or initial misclassification."
                suggestion = "A comprehensive business activity analysis is needed to identify the correct primary industry classification and SIC code alignment."
            
            analysis = f"""{reason}

**Current SIC**: {current_sic} - {current_sic_desc}

**Why this accuracy**: {analysis_detail}

**Next steps**: {suggestion}

The {quality} accuracy rating reflects specific alignment factors between the company's described operations and the SIC classification requirements."""
        
        return analysis


# Singleton instance for global use
ai_reasoning_agent = AIReasoningAgent()