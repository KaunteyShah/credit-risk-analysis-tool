#!/usr/bin/env python3
"""
Cost-Effective Q&A API endpoints with cost comparison features.
Provides FREE alternatives to expensive LLM services.
"""

from flask import Blueprint, request, jsonify
from app_modules.utils.logger import get_logger

logger = get_logger(__name__)

# Create Blueprint
cost_effective_qa_bp = Blueprint('cost_effective_qa', __name__)

# Import cost-effective generator
try:
    from .qa_local_llm_generator import CostEffectiveQAGenerator, get_cost_comparison
    COST_EFFECTIVE_AVAILABLE = True
except ImportError:
    COST_EFFECTIVE_AVAILABLE = False
    logger.warning("⚠️ Cost-effective Q&A not available")

# Initialize generator
cost_effective_generator = None
if COST_EFFECTIVE_AVAILABLE:
    try:
        cost_effective_generator = CostEffectiveQAGenerator()
        logger.info("💰 Cost-effective Q&A API initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize cost-effective generator: {e}")

@cost_effective_qa_bp.route('/api/qa/cost-comparison', methods=['GET'])
def get_qa_cost_comparison():
    """Get cost comparison between free and paid Q&A approaches."""
    try:
        if not COST_EFFECTIVE_AVAILABLE:
            return jsonify({
                "error": "Cost-effective Q&A not available",
                "recommendation": "Install transformers library for FREE local LLM support"
            }), 500
        
        comparison = get_cost_comparison()
        return jsonify(comparison)
        
    except Exception as e:
        logger.error(f"❌ Cost comparison failed: {e}")
        return jsonify({"error": str(e)}), 500

@cost_effective_qa_bp.route('/api/qa/free', methods=['POST'])
def generate_free_qa_response():
    """Generate Q&A response using FREE local models."""
    try:
        if not cost_effective_generator:
            return jsonify({
                "error": "Free Q&A generator not available",
                "suggestion": "Check server logs for initialization issues"
            }), 500
        
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Question is required"}), 400
        
        question = data['question']
        company_number = data.get('company_number')
        document_id = data.get('document_id')
        max_sources = data.get('max_sources', 5)
        min_confidence = data.get('min_confidence', 0.3)
        
        logger.info(f"💰 Processing FREE Q&A request: {question}")
        
        response = cost_effective_generator.generate_response(
            question=question,
            company_number=company_number,
            document_id=document_id,
            max_sources=max_sources,
            min_confidence=min_confidence
        )
        
        return jsonify(response.to_dict())
        
    except Exception as e:
        logger.error(f"❌ Free Q&A generation failed: {e}")
        return jsonify({"error": str(e)}), 500

@cost_effective_qa_bp.route('/api/qa/cost-status', methods=['GET'])
def get_cost_status():
    """Get current Q&A cost configuration status."""
    try:
        status = {
            "cost_effective_available": COST_EFFECTIVE_AVAILABLE,
            "generator_ready": cost_effective_generator is not None,
            "embedding_model": "all-mpnet-base-v2 (FREE)",
            "cost_per_query": "$0.00",
            "monthly_savings_1000_queries": "$2-6 vs Azure OpenAI"
        }
        
        if cost_effective_generator:
            status.update({
                "model_info": cost_effective_generator.model_info,
                "status": "Ready for FREE Q&A generation",
                "recommendation": "Using cost-effective approach ✅"
            })
        else:
            status.update({
                "status": "Cost-effective generator not ready",
                "recommendation": "Check dependencies and configuration"
            })
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"❌ Cost status check failed: {e}")
        return jsonify({"error": str(e)}), 500

@cost_effective_qa_bp.route('/api/qa/install-guide', methods=['GET'])
def get_installation_guide():
    """Get installation guide for cost-effective Q&A."""
    guide = {
        "title": "Cost-Effective Q&A Installation Guide",
        "requirements": {
            "python_packages": [
                "transformers",
                "torch",
                "sentence-transformers"
            ],
            "system_requirements": [
                "Python 3.8+",
                "4GB+ RAM recommended",
                "GPU optional (for speed)"
            ]
        },
        "installation_commands": [
            "pip install transformers torch torchvision torchaudio",
            "pip install sentence-transformers",
            "# GPU support (optional):",
            "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
        ],
        "benefits": [
            "Zero API costs",
            "Same embedding model as vectorization system",
            "No external service dependencies",
            "Better privacy - data stays local",
            "Consistent performance"
        ],
        "cost_savings": {
            "per_query": "$0.002-0.006 saved vs Azure OpenAI",
            "monthly_1000_queries": "$2-6 saved",
            "annual_10000_queries": "$20-60 saved"
        }
    }
    
    return jsonify(guide)

# Health check
@cost_effective_qa_bp.route('/api/qa/health', methods=['GET'])
def health_check():
    """Health check for cost-effective Q&A system."""
    try:
        status = {
            "service": "Cost-Effective Q&A",
            "status": "healthy" if cost_effective_generator else "degraded",
            "cost_effective_available": COST_EFFECTIVE_AVAILABLE,
            "generator_ready": cost_effective_generator is not None,
            "embedding_consistency": "✅ Uses same all-mpnet-base-v2 as vectorization",
            "cost": "$0.00 per query"
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return jsonify({"error": str(e)}), 500