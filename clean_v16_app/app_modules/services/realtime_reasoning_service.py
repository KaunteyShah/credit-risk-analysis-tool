"""
Real-time SIC Reasoning Service
Provides on-demand existing SIC reasoning generation for company modals
Reuses the existing AI reasoning agent from auto_sic_confidence_calculator.py
"""

import os
import sys
import sqlite3
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app_modules.utils.logger import logger

# Try to import OpenAI client and MultiAgentOrchestrator
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ OpenAI client not available for real-time reasoning")

# Try to import MultiAgentOrchestrator
try:
    from app_modules.agents.orchestrator import MultiAgentOrchestrator
    ORCHESTRATOR_AVAILABLE = True
    logger.info("✅ MultiAgentOrchestrator available for real-time reasoning")
except ImportError as e:
    ORCHESTRATOR_AVAILABLE = False
    logger.warning(f"⚠️ MultiAgentOrchestrator not available for real-time reasoning: {e}")


class RealtimeReasoningService:
    """Service for generating existing SIC reasoning on-demand when company modals are opened"""
    
    def __init__(self):
        self.client = None
        self.orchestrator = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize OpenAI client and MultiAgentOrchestrator for real-time reasoning"""
        # Initialize MultiAgentOrchestrator (preferred method)
        if ORCHESTRATOR_AVAILABLE:
            try:
                self.orchestrator = MultiAgentOrchestrator()
                logger.info("✅ Real-time reasoning service initialized with MultiAgentOrchestrator")
                return
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize MultiAgentOrchestrator: {e}")
        
        # Fallback to direct OpenAI client
        if not OPENAI_AVAILABLE:
            logger.warning("⚠️ Neither orchestrator nor OpenAI available - real-time reasoning disabled")
            return
        
        self._initialize_openai_client()
    
    def _initialize_openai_client(self):
        """Initialize OpenAI client for real-time reasoning (fallback method)"""
        if not OPENAI_AVAILABLE:
            logger.warning("⚠️ OpenAI not available - real-time reasoning disabled")
            return
            
        try:
            # Get OpenAI API key using ConfigManager (like the successful AI agent)
            from app_modules.utils.config_manager import ConfigManager
            config = ConfigManager()
            api_key = config.get('openai.api_key')
            
            if not api_key or api_key == 'dummy-key-for-local-testing' or len(api_key) < 20:
                logger.warning("⚠️ No valid OpenAI API key found in ConfigManager - real-time reasoning disabled")
                return
                
            # Since we have an Azure OpenAI key, use Azure OpenAI client directly
            api_base = os.getenv('AZURE_OPENAI_ENDPOINT', 'https://gpt-sweden-central.openai.azure.com/')
            api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=api_base
            )
            logger.info(f"✅ Real-time reasoning service initialized with Azure OpenAI endpoint: {api_base}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def generate_realtime_reasoning(self, company_id):
        """Generate real-time reasoning for existing SIC confidence with guaranteed fallback."""
        try:
            # Get company data from database
            company_data = self._get_company_data(company_id)
            if not company_data:
                return {"success": False, "error": "Company not found"}
            
            # Always attempt real-time generation for existing SIC reasoning
            reasoning = self._generate_existing_sic_reasoning(company_data)
            
            if reasoning:
                # Save the generated reasoning to database
                from app_modules.factory import get_credit_risk_config
                config = get_credit_risk_config()
                conn = config.get_database_connection()
                self._save_generated_reasoning(company_id, reasoning, conn, "existing_sic")
                conn.close()
                return {"success": True, "reasoning": reasoning, "source": "generated"}
            else:
                # If real-time generation failed, check if we have existing reasoning in database
                existing_reasoning = company_data.get('existing_sic_reasoning')
                if existing_reasoning and existing_reasoning.strip():
                    return {"success": True, "reasoning": existing_reasoning, "source": "database_fallback"}
                
                # If no existing reasoning, generate a basic fallback and save it
                fallback_reasoning = self._generate_basic_fallback(company_data)
                if fallback_reasoning:
                    from app_modules.factory import get_credit_risk_config
                    config = get_credit_risk_config()
                    conn = config.get_database_connection()
                    self._save_generated_reasoning(company_id, fallback_reasoning, conn, "existing_sic")
                    conn.close()
                    return {"success": True, "reasoning": fallback_reasoning, "source": "fallback_generated"}
                
                return {"success": False, "error": "Failed to generate any reasoning"}
                
        except Exception as e:
            logger.error(f"Error generating real-time reasoning: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_existing_sic_reasoning_for_company(self, company_id, db_connection):
        """Compatibility method for Flask routes - generates existing SIC reasoning."""
        try:
            result = self.generate_realtime_reasoning(company_id)
            if result.get("success"):
                return result.get("reasoning")
            else:
                logger.error(f"Failed to generate reasoning: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"Error in generate_existing_sic_reasoning_for_company: {e}")
            return None

    def generate_predicted_sic_reasoning_for_company(self, company_id, db_connection):
        """Generate AI reasoning for predicted SIC codes - explains why predicted SIC is better."""
        try:
            result = self.generate_predicted_sic_reasoning(company_id)
            if result.get("success"):
                return result.get("reasoning")
            else:
                logger.error(f"Failed to generate predicted SIC reasoning: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"Error in generate_predicted_sic_reasoning_for_company: {e}")
            return None

    def generate_predicted_sic_reasoning(self, company_id):
        """Generate AI reasoning comparing predicted SIC vs existing SIC."""
        try:
            # Get company data from database
            company_data = self._get_company_data(company_id)
            if not company_data:
                return {"success": False, "error": "Company not found"}
            
            # Generate reasoning for predicted SIC vs existing SIC
            reasoning = self._generate_predicted_sic_ai_reasoning(company_data)
            
            if reasoning:
                # Save the generated reasoning to ai_reasoning field
                from app_modules.factory import get_credit_risk_config
                config = get_credit_risk_config()
                conn = config.get_database_connection()
                self._save_generated_reasoning(company_id, reasoning, conn, "predicted")
                conn.close()
                return {"success": True, "reasoning": reasoning, "source": "generated_predicted"}
            else:
                # Fallback reasoning for predicted SIC
                fallback_reasoning = self._generate_predicted_sic_fallback(company_data)
                if fallback_reasoning:
                    from app_modules.factory import get_credit_risk_config
                    config = get_credit_risk_config()
                    conn = config.get_database_connection()
                    self._save_generated_reasoning(company_id, fallback_reasoning, conn, "predicted")
                    conn.close()
                    return {"success": True, "reasoning": fallback_reasoning, "source": "fallback_predicted"}
                
                return {"success": False, "error": "Failed to generate predicted SIC reasoning"}
                
        except Exception as e:
            print(f"Error generating predicted SIC reasoning: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_company_data(self, company_id):
        """Get company data from database including existing reasoning."""
        try:
            from app_modules.factory import get_credit_risk_config
            config = get_credit_risk_config()
            
            # Query company_portal_view for the correct data
            query = """
            SELECT company_name, business_description, uk_sic_2007_code, uk_sic_2007_description, 
                   existing_sic_confidence, predicted_sic_code, confidence_score
            FROM company_portal_view 
            WHERE company_id = ?
            """
            
            conn = config.get_database_connection()
            cursor = conn.execute(query, (company_id,))
            result = cursor.fetchall()
            
            if result and len(result) > 0:
                row = result[0]
                company_data = {
                    'company_name': row[0],
                    'business_description': row[1],
                    'existing_sic_code': row[2],
                    'existing_sic_description': row[3], 
                    'existing_sic_confidence': row[4],
                    'predicted_sic_code': row[5],
                    'confidence_score': row[6],
                    'existing_sic_reasoning': None,  # Will be generated
                    'ai_reasoning': None  # Will be generated
                }
                
                # Try to get existing reasoning from sic_prediction_history if available
                reasoning_query = """
                SELECT existing_sic_reasoning, ai_reasoning 
                FROM sic_prediction_history 
                WHERE company_id = ?
                ORDER BY prediction_timestamp DESC
                LIMIT 1
                """
                reasoning_cursor = conn.execute(reasoning_query, (company_id,))
                reasoning_result = reasoning_cursor.fetchall()
                
                if reasoning_result and len(reasoning_result) > 0:
                    reasoning_row = reasoning_result[0]
                    if reasoning_row[0]:  # existing_sic_reasoning
                        company_data['existing_sic_reasoning'] = reasoning_row[0]
                    if reasoning_row[1]:  # ai_reasoning
                        company_data['ai_reasoning'] = reasoning_row[1]
                
                conn.close()
                return company_data
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error getting company data: {e}")
            return None
    
    def _generate_existing_sic_reasoning(self, company_data):
        """Generate reasoning for existing SIC confidence."""
        try:
            # First, try to use MultiAgentOrchestrator with full company data (preferred method)
            if self.orchestrator:
                try:
                    company_name = company_data.get('company_name', 'Unknown Company')
                    logger.info(f"🤖 Using MultiAgentOrchestrator for reasoning generation for {company_name}")
                    
                    # Prepare company data for orchestrator with all available information
                    orchestrator_data = {
                        'company_name': company_data.get('company_name', ''),
                        'business_description': company_data.get('business_description', ''),
                        'uk_sic_2007_code': company_data.get('existing_sic_code', ''),
                        'uk_sic_2007_description': company_data.get('existing_sic_description', ''),
                        'existing_sic_confidence': company_data.get('existing_sic_confidence', 0),
                        'predicted_sic_code': company_data.get('predicted_sic_code', ''),
                        'confidence_score': company_data.get('confidence_score', 0)
                    }
                    
                    # Use orchestrator to generate AI reasoning
                    result = self.orchestrator.generate_ai_reasoning(orchestrator_data)
                    
                    if result and len(result.strip()) > 50:
                        logger.info(f"✅ Successfully generated AI reasoning using MultiAgentOrchestrator for {company_name}")
                        return result
                    else:
                        logger.warning(f"⚠️ MultiAgentOrchestrator returned insufficient reasoning, falling back to individual parameters")
                        
                except Exception as orchestrator_error:
                    logger.warning(f"⚠️ MultiAgentOrchestrator failed for {company_name}: {orchestrator_error}")
                    # Continue to fallback method
            
            # Fallback to individual parameter method
            company_name = company_data.get('company_name', 'Unknown Company')
            business_desc = company_data.get('business_description', 'No description available')
            sic_code = company_data.get('existing_sic_code', 'Unknown')
            sic_desc = company_data.get('existing_sic_description', 'Unknown')
            confidence = company_data.get('existing_sic_confidence', 0)
            
            return self._generate_ai_reasoning(
                company_name, business_desc, sic_code, sic_desc, confidence
            )
            
        except Exception as e:
            logger.error(f"Error generating existing SIC reasoning: {e}")
            return None

    def _generate_predicted_sic_ai_reasoning(self, company_data):
        """Generate AI reasoning for predicted SIC compared to existing SIC."""
        try:
            company_name = company_data.get('company_name', 'Unknown Company')
            business_desc = company_data.get('business_description', 'No description available')
            predicted_sic = company_data.get('predicted_sic_code', 'Unknown')
            existing_sic = company_data.get('existing_sic_code', 'Unknown')
            
            return self._generate_predicted_sic_comparison_reasoning(
                company_name, business_desc, predicted_sic, existing_sic
            )
            
        except Exception as e:
            logger.error(f"Error generating predicted SIC fallback: {e}")
            return None

    def _generate_predicted_sic_fallback(self, company_data):
        """Generate fallback reasoning for predicted SIC when AI fails."""
        try:
            company_name = company_data.get('company_name', 'Unknown Company')
            predicted_sic = company_data.get('predicted_sic_code', 'Unknown')
            existing_sic = company_data.get('existing_sic_code', 'Unknown')
            
            reasoning = f"**Predicted SIC Analysis for {company_name}**\n\n"
            reasoning += f"**Recommended SIC Code:** {predicted_sic}\n"
            reasoning += f"**Current SIC Code:** {existing_sic}\n\n"
            reasoning += f"**Assessment:** Our AI analysis suggests that SIC code {predicted_sic} would be more appropriate than the current classification {existing_sic} based on the company's business activities.\n\n"
            reasoning += f"**Recommendation:** Consider updating to the predicted SIC code for improved classification accuracy.\n\n"
            reasoning += f"*Note: This analysis was generated using rule-based assessment due to AI service availability. For detailed comparison analysis, please retry when the AI reasoning service is restored.*"
            
            return reasoning
            
        except Exception as e:
            logger.error(f"Error generating predicted SIC AI reasoning: {e}")
            return None
    
    def _generate_basic_fallback(self, company_data):
        """Generate basic fallback reasoning when AI generation fails."""
        try:
            company_name = company_data.get('company_name', 'Unknown Company')
            sic_code = company_data.get('existing_sic_code', 'Unknown')
            sic_desc = company_data.get('existing_sic_description', 'Unknown')
            confidence = company_data.get('existing_sic_confidence', 0)
            
            # Create basic reasoning from available data
            reasoning = f"SIC Analysis for {company_name}:\n\n"
            reasoning += f"Current SIC Code: {sic_code}\n"
            reasoning += f"SIC Description: {sic_desc}\n"
            reasoning += f"Confidence Score: {confidence:.1f}%\n\n"
            
            if confidence >= 85:
                reasoning += "Assessment: High confidence - The existing SIC code appears well-aligned with the business activities."
            elif confidence >= 65:
                reasoning += "Assessment: Moderate confidence - The existing SIC code is reasonably appropriate but could potentially be refined."
            else:
                reasoning += "Assessment: Lower confidence - The existing SIC code may benefit from review to ensure optimal classification."
                
            return reasoning
            
        except Exception as e:
            logger.error(f"Error generating basic fallback: {e}")
            return None
    
    def _generate_predicted_sic_comparison_reasoning(self, company_name: str, business_desc: str, 
                                                   predicted_sic: str, existing_sic: str) -> Optional[str]:
        """Generate AI reasoning comparing predicted SIC vs existing SIC"""
        try:
            # Create the prompt for predicted SIC reasoning
            prompt = f"""
            Analyze why the predicted SIC code is more accurate for this UK company:

            Company: {company_name}
            Business Description: {business_desc}
            Current SIC Code: {existing_sic}
            Predicted SIC Code: {predicted_sic}

            Provide concise analysis explaining:
            1. Why the predicted SIC ({predicted_sic}) is more appropriate
            2. What activities make it better than current SIC ({existing_sic})
            3. Specific business alignment with predicted classification
            4. Recommendation for SIC code update

            Keep response under 200 words, professional tone.
            """

            # Call Azure OpenAI with retry logic
            max_retries = 3
            retry_delay = 1
            
            # Check if client is available
            if not self.client:
                logger.warning("OpenAI client not initialized for predicted SIC reasoning")
                return self._generate_predicted_sic_intelligent_fallback(company_name, business_desc, predicted_sic, existing_sic)
            
            for attempt in range(max_retries):
                try:
                    deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo')
                    response = self.client.chat.completions.create(
                        model=deployment_name,
                        messages=[
                            {"role": "system", "content": "You are a UK SIC code analyst. Explain why a predicted SIC code is more accurate than the current one. Be concise and professional, under 150 words."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.3,
                        timeout=10.0
                    )
                    
                    if response and response.choices and response.choices[0].message.content:
                        reasoning = response.choices[0].message.content.strip()
                        
                        if reasoning and len(reasoning) > 50:
                            return reasoning
                        else:
                            logger.warning("Generated predicted SIC reasoning too short, retrying...")
                    else:
                        logger.warning("Empty response from OpenAI for predicted SIC, retrying...")
                        
                except Exception as api_error:
                    logger.warning(f"OpenAI API attempt {attempt + 1} failed for predicted SIC: {api_error}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"All OpenAI attempts failed for predicted SIC, using fallback reasoning")
                        return self._generate_predicted_sic_intelligent_fallback(company_name, business_desc, predicted_sic, existing_sic)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in predicted SIC AI reasoning generation: {e}")
            return None

    def _generate_predicted_sic_intelligent_fallback(self, company_name: str, business_desc: str, 
                                                   predicted_sic: str, existing_sic: str) -> str:
        """Generate intelligent fallback reasoning for predicted SIC when AI service is unavailable"""
        try:
            reasoning_parts = [
                f"**Predicted SIC Analysis for {company_name}**",
                f"",
                f"**Current SIC Code:** {existing_sic}",
                f"**Recommended SIC Code:** {predicted_sic}",
                f"",
                f"**Analysis Summary:**",
                f"Our AI classification system has identified SIC code {predicted_sic} as more appropriate than the current classification {existing_sic} for this company's business activities.",
                f"",
                f"**Business Profile Assessment:**"
            ]
            
            if business_desc and len(business_desc.strip()) > 10:
                desc_lower = business_desc.lower()
                # Analyze business description for key activities
                if any(word in desc_lower for word in ['retail', 'shop', 'store']):
                    reasoning_parts.append("The business description indicates retail operations that may be better classified under the predicted SIC category.")
                elif any(word in desc_lower for word in ['manufacture', 'production']):
                    reasoning_parts.append("Manufacturing activities described suggest the predicted SIC code provides more accurate industrial classification.")
                elif any(word in desc_lower for word in ['service', 'consult']):
                    reasoning_parts.append("Service-oriented business activities align better with the predicted SIC classification framework.")
                else:
                    reasoning_parts.append("Business activities described are better captured by the predicted SIC code classification.")
            else:
                reasoning_parts.append("Based on available company information, the predicted SIC code offers improved classification accuracy.")
            
            reasoning_parts.extend([
                f"",
                f"**Recommendation:** Update to SIC code {predicted_sic} for enhanced classification accuracy and better industry alignment.",
                f"",
                f"*Note: This analysis was generated using intelligent rule-based assessment due to AI service availability. For detailed comparison analysis, please retry when the AI reasoning service is restored.*"
            ])
            
            return "\n".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"Error generating predicted SIC fallback reasoning: {e}")
            return f"**Predicted SIC Analysis for {company_name}**\n\nRecommended SIC: {predicted_sic} (Current: {existing_sic})\n\nOur analysis suggests the predicted SIC code {predicted_sic} would provide more accurate classification than the current SIC {existing_sic} based on the company's business profile. Consider updating the SIC classification for improved accuracy."

    def _generate_ai_reasoning(self, company_name: str, business_desc: str, 
                              sic_code: str, sic_desc: str, confidence_score: float) -> Optional[str]:
        """Generate AI reasoning using MultiAgentOrchestrator or fallback to direct OpenAI"""
        try:
            # First, try to use MultiAgentOrchestrator (preferred method)
            if self.orchestrator:
                try:
                    logger.info(f"🤖 Using MultiAgentOrchestrator for reasoning generation for {company_name}")
                    
                    # Prepare company data for orchestrator
                    company_data = {
                        'company_name': company_name,
                        'business_description': business_desc,
                        'uk_sic_2007_code': sic_code,
                        'uk_sic_2007_description': sic_desc,
                        'existing_sic_confidence': confidence_score
                    }
                    
                    # Use orchestrator to generate AI reasoning
                    result = self.orchestrator.generate_ai_reasoning(company_data)
                    
                    if result and len(result.strip()) > 50:
                        logger.info(f"✅ Successfully generated AI reasoning using MultiAgentOrchestrator for {company_name}")
                        return result
                    else:
                        logger.warning(f"⚠️ MultiAgentOrchestrator returned insufficient reasoning, falling back to direct OpenAI")
                        
                except Exception as orchestrator_error:
                    logger.warning(f"⚠️ MultiAgentOrchestrator failed for {company_name}: {orchestrator_error}")
                    # Continue to fallback method
            
            # Fallback to direct OpenAI client
            logger.info(f"🔄 Using direct OpenAI client as fallback for {company_name}")
            
            # Create the prompt for AI reasoning generation
            prompt = f"""
            Analyze the SIC code assignment for this UK company:

            Company: {company_name}
            Business Description: {business_desc}
            SIC Code: {sic_code} - {sic_desc}
            Confidence: {confidence_score:.1f}%

            Provide concise analysis:
            1. Business-SIC alignment assessment
            2. Key supporting/conflicting activities
            3. Confidence level evaluation
            4. Brief recommendation

            Keep response under 200 words, professional tone.
            """

            # Call Azure OpenAI with retry logic
            max_retries = 3
            retry_delay = 1
            
            # Check if client is available
            if not self.client:
                logger.warning("OpenAI client not initialized, falling back to intelligent fallback")
                return self._generate_intelligent_fallback(company_name, business_desc, sic_code, sic_desc, confidence_score)
            
            for attempt in range(max_retries):
                try:
                    deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo')
                    response = self.client.chat.completions.create(
                        model=deployment_name,
                        messages=[
                            {"role": "system", "content": "You are a UK SIC code analyst. Provide concise, professional business classification analysis in under 150 words."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150,
                        temperature=0.3,
                        timeout=10.0
                    )
                    
                    if response and response.choices and response.choices[0].message.content:
                        reasoning = response.choices[0].message.content.strip()
                        
                        if reasoning and len(reasoning) > 50:
                            return reasoning
                        else:
                            logger.warning("Generated reasoning too short, retrying...")
                    else:
                        logger.warning("Empty response from OpenAI, retrying...")
                        
                except Exception as api_error:
                    logger.warning(f"OpenAI API attempt {attempt + 1} failed: {api_error}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"All OpenAI attempts failed, using fallback reasoning")
                        return self._generate_intelligent_fallback(company_name, business_desc, sic_code, sic_desc, confidence_score)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in AI reasoning generation: {e}")
            return None

    def _generate_intelligent_fallback(self, company_name: str, business_desc: str, 
                                      sic_code: str, sic_desc: str, confidence_score: float) -> str:
        """Generate intelligent fallback reasoning when AI service is unavailable"""
        try:
            # Analyze key business indicators
            desc_lower = business_desc.lower() if business_desc else ""
            
            # Identify key business activities
            key_activities = []
            if any(word in desc_lower for word in ['retail', 'shop', 'store', 'sell']):
                key_activities.append("retail operations")
            if any(word in desc_lower for word in ['manufacture', 'production', 'factory']):
                key_activities.append("manufacturing activities")
            if any(word in desc_lower for word in ['service', 'consult', 'advice']):
                key_activities.append("service provision")
            if any(word in desc_lower for word in ['technology', 'software', 'digital']):
                key_activities.append("technology services")
            if any(word in desc_lower for word in ['construction', 'building', 'property']):
                key_activities.append("construction/property services")
            
            # Generate confidence assessment
            if confidence_score >= 80:
                confidence_level = "High"
                confidence_explanation = "Strong alignment between business activities and SIC classification"
            elif confidence_score >= 60:
                confidence_level = "Medium-High"
                confidence_explanation = "Good match with some minor discrepancies expected"
            elif confidence_score >= 40:
                confidence_level = "Medium"
                confidence_explanation = "Moderate alignment requiring closer examination"
            else:
                confidence_level = "Low"
                confidence_explanation = "Limited alignment suggesting potential reclassification needs"
            
            # Build reasoning
            reasoning_parts = [
                f"**SIC Classification Analysis for {company_name}**",
                f"",
                f"**Current Assignment:** {sic_code} - {sic_desc}",
                f"**Confidence Level:** {confidence_level} ({confidence_score:.1f}%)",
                f"",
                f"**Business Profile Analysis:**"
            ]
            
            if business_desc and len(business_desc.strip()) > 10:
                reasoning_parts.extend([
                    f"The company description indicates focus on {', '.join(key_activities) if key_activities else 'general business activities'}.",
                    f""
                ])
            
            reasoning_parts.extend([
                f"**Assessment Summary:**",
                f"{confidence_explanation}. "
            ])
            
            if confidence_score >= 70:
                reasoning_parts.append("The current SIC code appears appropriate for the described business activities.")
            elif confidence_score >= 50:
                reasoning_parts.append("The SIC code is generally suitable but may benefit from review to ensure optimal classification.")
            else:
                reasoning_parts.append("Consider reviewing the SIC classification as the current code may not fully represent the business activities.")
            
            reasoning_parts.extend([
                f"",
                f"*Note: This analysis was generated using rule-based assessment due to AI service availability. For more detailed analysis, please retry when the AI reasoning service is restored.*"
            ])
            
            return "\n".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"Error generating fallback reasoning: {e}")
            return f"**SIC Analysis for {company_name}**\n\nCurrent SIC: {sic_code} - {sic_desc}\nConfidence Score: {confidence_score:.1f}%\n\nA detailed analysis is temporarily unavailable. The existing SIC classification should be reviewed for accuracy based on current business activities."

    def _save_generated_reasoning(self, company_id: int, reasoning: str, db_connection, reasoning_type: str = "existing"):
        """
        Save the generated reasoning to database for future use
        
        Args:
            company_id: Company ID to save reasoning for
            reasoning: Generated reasoning text
            db_connection: Database connection
            reasoning_type: Type of reasoning ("existing" or "predicted")
        """
        try:
            cursor = db_connection.cursor()
            timestamp = datetime.now().isoformat()
            
            # Check if company has predicted SIC to determine field to update
            cursor.execute("""
                SELECT id, predicted_sic_code, existing_sic_reasoning, ai_reasoning 
                FROM sic_prediction_history 
                WHERE company_id = ? 
                ORDER BY prediction_timestamp DESC
                LIMIT 1
            """, (company_id,))
            
            result = cursor.fetchone()
            
            if result:
                record_id, predicted_sic, existing_reasoning, ai_reasoning = result
                
                # Determine which field to update based on company's SIC prediction status
                if predicted_sic:
                    # Company has predicted SIC - save to ai_reasoning field (Enhanced SIC Matcher AI field)
                    update_query = """
                        UPDATE sic_prediction_history 
                        SET ai_reasoning = ?,
                            prediction_timestamp = ?
                        WHERE id = ?
                    """
                    cursor.execute(update_query, (reasoning, timestamp, record_id))
                    logger.info(f"💾 Saved real-time reasoning to ai_reasoning field for company {company_id}")
                else:
                    # Company has no predicted SIC - save to existing_sic_reasoning field
                    update_query = """
                        UPDATE sic_prediction_history 
                        SET existing_sic_reasoning = ?,
                            existing_sic_calculation_timestamp = ?
                        WHERE id = ?
                    """
                    cursor.execute(update_query, (reasoning, timestamp, record_id))
                    logger.info(f"💾 Saved real-time reasoning to existing_sic_reasoning field for company {company_id}")
            else:
                # No existing record - don't create one, only enhanced_sic_matcher should create records
                logger.info(f"⏭️ No existing prediction record found for company {company_id} - skipping reasoning save (will be saved during prediction approval)")
            
            db_connection.commit()
            logger.info(f"✅ Successfully saved real-time reasoning to database for company {company_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving reasoning for company {company_id}: {e}")
            db_connection.rollback()
    
    def is_available(self) -> bool:
        """Check if the reasoning service is available"""
        return self.client is not None


# Global service instance
realtime_reasoning_service = RealtimeReasoningService()