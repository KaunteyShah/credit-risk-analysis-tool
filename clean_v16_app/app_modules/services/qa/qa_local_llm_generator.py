#!/usr/bin/env python3
"""
Cost-Effective Q&A Response Generator using FREE local LLM models.
Eliminates Azure OpenAI costs while maintaining quality responses.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import time
import logging
from app_modules.utils.config_manager import ConfigManager
from app_modules.utils.logger import get_logger
from qa_search_engine import QASearchEngine, QASearchResult

logger = get_logger(__name__)

# Use FREE local models for cost efficiency
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
    logger.info("✅ Transformers library available for local LLM")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠️ Transformers not available, will use fallback responses")

@dataclass 
class QAResponse:
    """Comprehensive Q&A response with sources."""
    question: str
    answer: str
    confidence_score: float
    sources: List[Dict[str, Any]]
    context_used: List[str]
    search_results_count: int
    processing_time: float
    cost_savings: str = "FREE - No API costs"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence_score": self.confidence_score,
            "sources": self.sources,
            "context_used": self.context_used,
            "search_results_count": self.search_results_count,
            "processing_time": self.processing_time,
            "cost_savings": self.cost_savings
        }

class CostEffectiveQAGenerator:
    """FREE Q&A Generator using local LLM models - NO API COSTS!"""
    
    def __init__(self):
        self.logger = get_logger("CostEffectiveQA")
        self.search_engine = QASearchEngine()
        self.config = ConfigManager()
        
        # Initialize FREE local LLM
        self.llm_pipeline = None
        self.model_info = {"name": "fallback", "cost": "FREE"}
        
        if TRANSFORMERS_AVAILABLE:
            self._initialize_local_llm()
        else:
            self.logger.info("📝 Using enhanced fallback responses (still FREE!)")
    
    def _initialize_local_llm(self):
        """Initialize cost-effective local LLM models."""
        try:
            # Option 1: Microsoft DialoGPT (FREE, conversational)
            model_name = "microsoft/DialoGPT-medium"
            
            # Option 2: GPT-2 (FREE, lightweight)
            # model_name = "gpt2"
            
            # Option 3: DistilGPT-2 (FREE, even lighter)
            # model_name = "distilgpt2"
            
            self.logger.info(f"🤖 Loading FREE local LLM: {model_name}")
            
            # Check if GPU is available for speed
            device = 0 if torch.cuda.is_available() else -1
            device_info = "GPU" if device == 0 else "CPU"
            
            self.llm_pipeline = pipeline(
                "text-generation",
                model=model_name,
                device=device,
                max_length=512,
                do_sample=True,
                temperature=0.7,
                pad_token_id=50256  # GPT-2 pad token
            )
            
            self.model_info = {
                "name": model_name,
                "device": device_info,
                "cost": "FREE - No API costs!",
                "vs_azure": "100% cost savings vs Azure OpenAI"
            }
            
            self.logger.info(f"✅ FREE LLM initialized on {device_info}")
            self.logger.info(f"💰 Cost savings: 100% vs Azure OpenAI!")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Local LLM initialization failed: {e}")
            self.logger.info("📝 Falling back to enhanced responses (still FREE!)")
    
    def generate_response(self, 
                         question: str,
                         company_number: Optional[str] = None,
                         document_id: Optional[str] = None,
                         max_sources: int = 5,
                         min_confidence: float = 0.3) -> QAResponse:
        """
        Generate FREE Q&A response with NO API costs!
        
        Uses same embedding model as vectorization system for consistency.
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🤔 Generating FREE Q&A response for: '{question}'")
            
            # Search for relevant content using SAME embedding model
            search_results = self.search_engine.search_documents(
                query=question,
                company_number=company_number,
                document_id=document_id,
                top_k=max_sources,
                min_similarity=min_confidence
            )
            
            if not search_results:
                return self._create_no_results_response(question, time.time() - start_time)
            
            # Generate response using FREE local LLM or enhanced fallback
            answer = self._generate_free_answer(question, search_results)
            
            # Create source attributions
            sources = self._create_source_attributions(search_results)
            
            # Calculate confidence
            confidence = self._calculate_confidence(search_results, answer)
            
            # Build context used
            context_used = [result.content[:200] + "..." for result in search_results[:3]]
            
            response = QAResponse(
                question=question,
                answer=answer,
                confidence_score=confidence,
                sources=sources,
                context_used=context_used,
                search_results_count=len(search_results),
                processing_time=time.time() - start_time,
                cost_savings=f"FREE using {self.model_info['name']} - 100% cost savings vs Azure OpenAI"
            )
            
            self.logger.info(f"✅ Generated FREE response in {response.processing_time:.2f}s")
            self.logger.info(f"💰 Cost: $0.00 (vs ~$0.002+ per call with Azure)")
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ FREE Q&A generation failed: {e}")
            return self._create_error_response(question, str(e), time.time() - start_time)
    
    def _generate_free_answer(self, question: str, search_results: List[QASearchResult]) -> str:
        """Generate answer using FREE local LLM or enhanced fallback."""
        
        if self.llm_pipeline:
            return self._generate_local_llm_answer(question, search_results)
        else:
            return self._generate_enhanced_fallback(question, search_results)
    
    def _generate_local_llm_answer(self, question: str, search_results: List[QASearchResult]) -> str:
        """Generate answer using FREE local LLM."""
        try:
            # Build context from top results
            context_parts = []
            for result in search_results[:3]:
                context_parts.append(f"Document: {result.document_title}")
                context_parts.append(f"Content: {result.content[:300]}")
            
            context = " ".join(context_parts)
            
            # Create prompt for local LLM
            prompt = f"""Question: {question}

Based on the following company document information:
{context}

Professional Answer:"""
            
            # Generate with local LLM
            outputs = self.llm_pipeline(
                prompt,
                max_length=len(prompt.split()) + 150,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )
            
            # Extract generated text after the prompt
            generated = outputs[0]['generated_text']
            answer = generated[len(prompt):].strip()
            
            # Clean up the response
            answer = self._clean_llm_response(answer)
            
            return answer if answer else self._generate_enhanced_fallback(question, search_results)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Local LLM failed: {e}")
            return self._generate_enhanced_fallback(question, search_results)
    
    def _generate_enhanced_fallback(self, question: str, search_results: List[QASearchResult]) -> str:
        """Generate enhanced fallback response - still FREE and professional."""
        
        if not search_results:
            return "I couldn't find relevant information to answer your question in the available documents."
        
        # Analyze question type for better responses
        question_lower = question.lower()
        
        # Financial metrics questions
        if any(word in question_lower for word in ['revenue', 'profit', 'turnover', 'sales', 'income']):
            return self._format_financial_response(search_results)
        
        # Company information questions  
        elif any(word in question_lower for word in ['company', 'business', 'activities', 'what does']):
            return self._format_company_response(search_results)
        
        # Date/time questions
        elif any(word in question_lower for word in ['when', 'date', 'year', 'period']):
            return self._format_temporal_response(search_results)
        
        # General response
        else:
            return self._format_general_response(search_results)
    
    def _format_financial_response(self, search_results: List[QASearchResult]) -> str:
        """Format financial information response."""
        financial_data = []
        
        for result in search_results[:3]:
            content = result.content
            doc_title = result.document_title or "Company Filing"
            
            # Extract financial context
            if any(term in content.lower() for term in ['£', '$', 'revenue', 'profit', 'million', 'thousand']):
                financial_data.append(f"According to {doc_title}: {content[:250]}...")
        
        if financial_data:
            intro = "Based on the company's financial filings:\n\n"
            return intro + "\n\n".join(financial_data)
        else:
            return f"The available documents contain relevant information: {search_results[0].content[:300]}..."
    
    def _format_company_response(self, search_results: List[QASearchResult]) -> str:
        """Format company information response."""
        company_info = []
        
        for result in search_results[:2]:
            doc_title = result.document_title or "Company Document"
            company_info.append(f"From {doc_title}: {result.content[:200]}...")
        
        intro = "Based on the company's official documents:\n\n"
        return intro + "\n\n".join(company_info)
    
    def _format_temporal_response(self, search_results: List[QASearchResult]) -> str:
        """Format date/time related response."""
        temporal_info = []
        
        for result in search_results[:2]:
            if result.filing_date:
                temporal_info.append(f"Filing date {result.filing_date}: {result.content[:150]}...")
            else:
                temporal_info.append(f"Document information: {result.content[:150]}...")
        
        return "\n\n".join(temporal_info)
    
    def _format_general_response(self, search_results: List[QASearchResult]) -> str:
        """Format general response."""
        response_parts = []
        
        for i, result in enumerate(search_results[:3], 1):
            doc_ref = f"Document {i}"
            if result.document_title:
                doc_ref += f" ({result.document_title})"
            
            response_parts.append(f"{doc_ref}: {result.content[:200]}...")
        
        return "\n\n".join(response_parts)
    
    def _clean_llm_response(self, response: str) -> str:
        """Clean up local LLM response."""
        # Remove common LLM artifacts
        response = response.strip()
        
        # Remove repetitive text
        lines = response.split('\n')
        clean_lines = []
        for line in lines:
            if line.strip() and line not in clean_lines:
                clean_lines.append(line.strip())
        
        return '\n'.join(clean_lines[:5])  # Limit to 5 lines
    
    def _create_source_attributions(self, search_results: List[QASearchResult]) -> List[Dict[str, Any]]:
        """Create source attributions (same as original)."""
        sources = []
        for result in search_results:
            source = {
                "document_id": result.document_id,
                "document_title": result.document_title or "Unknown Document",
                "page_number": result.page_number or 1,
                "section_title": result.section_title or "N/A",
                "similarity_score": round(result.similarity_score, 3),
                "company_name": result.company_name or "Unknown",
                "company_registration_number": result.company_registration_number or "N/A",
                "filing_date": result.filing_date or "N/A",
                "excerpt": result.content[:200] + ("..." if len(result.content) > 200 else "")
            }
            sources.append(source)
        return sources
    
    def _calculate_confidence(self, search_results: List[QASearchResult], answer: str) -> float:
        """Calculate confidence score."""
        if not search_results:
            return 0.0
        
        avg_similarity = sum(r.similarity_score for r in search_results) / len(search_results)
        answer_quality = min(0.2, len(answer) / 500)
        
        return min(1.0, avg_similarity + answer_quality)
    
    def _create_no_results_response(self, question: str, processing_time: float) -> QAResponse:
        """Create response when no results found."""
        return QAResponse(
            question=question,
            answer="I couldn't find relevant information in the available documents to answer your question.",
            confidence_score=0.0,
            sources=[],
            context_used=[],
            search_results_count=0,
            processing_time=processing_time,
            cost_savings="FREE - No API costs even for no-result responses"
        )
    
    def _create_error_response(self, question: str, error: str, processing_time: float) -> QAResponse:
        """Create error response."""
        return QAResponse(
            question=question,
            answer=f"An error occurred while processing your question: {error}",
            confidence_score=0.0,
            sources=[],
            context_used=[],
            search_results_count=0,
            processing_time=processing_time,
            cost_savings="FREE - No API costs even for error responses"
        )

# Cost comparison function
def get_cost_comparison():
    """Get cost comparison between free and paid approaches."""
    return {
        "free_approach": {
            "embedding_model": "all-mpnet-base-v2 (SentenceTransformers)",
            "llm_model": "Local DialoGPT/GPT-2/Fallback",
            "cost_per_query": "$0.00",
            "monthly_cost_1000_queries": "$0.00",
            "advantages": [
                "Zero API costs",
                "Same embedding model as vectorization",
                "No external dependencies",
                "Privacy - data stays local",
                "Consistent performance"
            ]
        },
        "azure_openai_approach": {
            "embedding_model": "all-mpnet-base-v2 (SentenceTransformers)", 
            "llm_model": "Azure OpenAI gpt-35-turbo",
            "cost_per_query": "$0.002-0.006",
            "monthly_cost_1000_queries": "$2-6",
            "advantages": [
                "Higher quality responses",
                "Better reasoning capabilities"
            ],
            "disadvantages": [
                "Ongoing API costs",
                "External service dependency",
                "Rate limiting",
                "Privacy concerns"
            ]
        },
        "recommendation": "Use FREE approach for cost-effective consistent results with same embedding model"
    }