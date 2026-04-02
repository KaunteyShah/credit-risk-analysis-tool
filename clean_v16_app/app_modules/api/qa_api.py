"""
Q&A API endpoints for document question answering.
Provides REST endpoints for querying financial documents with LLM-powered responses.
"""

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from typing import Dict, Any, Optional
import time
import logging
import os
import sqlite3
from app_modules.utils.logger import get_logger
from app_modules.services.qa.qa_response_generator import QAResponseGenerator

logger = get_logger(__name__)

# Create Blueprint for Q&A API
qa_api = Blueprint('qa_api', __name__)

# Initialize Q&A response generator (singleton pattern)
_qa_generator: Optional[QAResponseGenerator] = None

def get_qa_generator() -> QAResponseGenerator:
    """Get or create Q&A response generator instance with OpenAI."""
    global _qa_generator
    if _qa_generator is None:
        logger.info("🔧 Initializing OpenAI Q&A response generator...")
        _qa_generator = QAResponseGenerator(use_openai=True)  # Use OpenAI with fallback
        logger.info("✅ OpenAI Q&A response generator initialized")
    return _qa_generator


@qa_api.route('/api/qa/ask', methods=['POST'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5000', 'http://localhost:5001', 'http://localhost:5002'])
def ask_question():
    """
    Answer questions about financial documents using LLM-powered Q&A.
    
    Request Body:
    {
        "question": "What is the company's revenue?",
        "company_registration_number": "07020023",  # Optional: filter by company
        "document_id": "document_123",              # Optional: filter by document
        "max_sources": 5                            # Optional: max number of sources to return
    }
    
    Response:
    {
        "success": true,
        "data": {
            "answer": "The company's revenue for 2024 was £12.5M...",
            "confidence": 0.87,
            "response_time_ms": 1250,
            "sources": [
                {
                    "document_title": "Annual Report 2024",
                    "page_number": 15,
                    "section_title": "Financial Performance",
                    "similarity_score": 0.92,
                    "start_char": 1250,
                    "end_char": 1450,
                    "text": "Revenue increased to £12.5M..."
                }
            ]
        },
        "error": null
    }
    """
    start_time = time.time()
    
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                "success": False,
                "data": None,
                "error": "Request must be JSON"
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        question = data.get('question', '').strip()
        if not question:
            return jsonify({
                "success": False,
                "data": None,
                "error": "Question is required"
            }), 400
        
        # Extract optional parameters
        company_registration_number = data.get('company_registration_number')
        document_id = data.get('document_id')
        max_sources = data.get('max_sources', 5)
        
        # Validate max_sources
        if not isinstance(max_sources, int) or max_sources < 1 or max_sources > 20:
            max_sources = 5
        
        logger.info(f"📝 Q&A Request: '{question}' (Company: {company_registration_number or 'All'})")
        
        # Get Q&A generator and generate response
        qa_generator = get_qa_generator()
        
        qa_response = qa_generator.generate_response(
            question=question,
            company_number=company_registration_number,
            document_id=document_id,
            max_sources=max_sources
        )
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Format response for API
        api_response = {
            "success": True,
            "data": {
                "answer": qa_response.answer,
                "confidence": qa_response.confidence_score,
                "response_time_ms": response_time_ms,
                "sources": []
            },
            "error": None
        }
        
        # Format sources for API response - sources are already dictionaries
        for source in qa_response.sources:
            formatted_source = {
                "document_title": source.get("document_title", "Unknown Document"),
                "page_number": source.get("page_number", 1),
                "section_title": source.get("section_title", "N/A"),
                "similarity_score": source.get("similarity_score", 0.0),
                "character_range": source.get("character_range", "N/A"),
                "excerpt": source.get("excerpt", "")
            }
            
            # Add optional fields if available
            if source.get("company_registration_number"):
                formatted_source["company_registration_number"] = source["company_registration_number"]
            
            if source.get("document_id"):
                formatted_source["document_id"] = source["document_id"]
            
            if source.get("filing_date"):
                formatted_source["filing_date"] = source["filing_date"]
            
            api_response["data"]["sources"].append(formatted_source)
        
        logger.info(f"✅ Q&A Response: {response_time_ms}ms, Confidence: {qa_response.confidence_score:.1%}, Sources: {len(qa_response.sources)}")
        
        return jsonify(api_response), 200
    
    except ValueError as e:
        logger.error(f"❌ Q&A Validation Error: {str(e)}")
        return jsonify({
            "success": False,
            "data": None,
            "error": f"Validation error: {str(e)}"
        }), 400
    
    except Exception as e:
        logger.error(f"❌ Q&A Server Error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "data": None,
            "error": "Internal server error"
        }), 500


@qa_api.route('/api/qa/health', methods=['GET'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5000', 'http://localhost:5001', 'http://localhost:5002'])
def qa_health():
    """
    Check Q&A system health and status.
    
    Response:
    {
        "success": true,
        "data": {
            "status": "healthy",
            "qa_generator_ready": true,
            "vector_db_connected": true,
            "embedding_model_loaded": true
        }
    }
    """
    try:
        # Check Q&A generator status
        qa_generator = get_qa_generator()
        
        # Perform basic health checks
        health_status = {
            "status": "healthy",
            "qa_generator_ready": qa_generator is not None,
            "vector_db_connected": hasattr(qa_generator, 'search_engine') and qa_generator.search_engine is not None,
            "embedding_model_loaded": False
        }
        
        # Check if embedding model is loaded
        try:
            if (hasattr(qa_generator, 'search_engine') and 
                hasattr(qa_generator.search_engine, 'document_processor') and
                hasattr(qa_generator.search_engine.document_processor, 'embedding_model')):
                health_status["embedding_model_loaded"] = qa_generator.search_engine.document_processor.embedding_model is not None
        except Exception:
            pass
        
        # Determine overall status
        if all([
            health_status["qa_generator_ready"],
            health_status["vector_db_connected"],
            health_status["embedding_model_loaded"]
        ]):
            health_status["status"] = "healthy"
        else:
            health_status["status"] = "degraded"
        
        logger.info(f"🏥 Q&A Health Check: {health_status['status']}")
        
        return jsonify({
            "success": True,
            "data": health_status,
            "error": None
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Q&A Health Check Error: {str(e)}")
        return jsonify({
            "success": False,
            "data": {
                "status": "unhealthy",
                "error": str(e)
            },
            "error": "Health check failed"
        }), 500


@qa_api.route('/api/qa/stats', methods=['GET'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5000', 'http://localhost:5001', 'http://localhost:5002'])
def qa_stats():
    """
    Get Q&A system statistics and metrics.
    
    Response:
    {
        "success": true,
        "data": {
            "total_documents": 15,
            "total_chunks": 342,
            "companies_indexed": 8,
            "embedding_dimensions": 768,
            "vector_db_size_mb": 12.5
        }
    }
    """
    try:
        qa_generator = get_qa_generator()
        
        # Get basic statistics
        stats = {
            "total_documents": 0,
            "total_chunks": 0,
            "companies_indexed": 0,
            "embedding_dimensions": 768,  # All-mpnet-base-v2 (configured for 768D)
            "vector_db_size_mb": 0.0
        }
        
        # Try to get real statistics from vector database
        try:
            if hasattr(qa_generator, 'search_engine') and qa_generator.search_engine:
                vector_db = qa_generator.search_engine.vector_db
                
                # Query document statistics using connection context
                with vector_db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Count total chunks (use correct table name)
                    result = cursor.execute("SELECT COUNT(*) FROM document_chunks_v2").fetchone()
                    if result:
                        stats["total_chunks"] = result[0]
                    
                    # Count unique documents (use correct table name)
                    result = cursor.execute("SELECT COUNT(DISTINCT document_id) FROM document_chunks_v2").fetchone()
                    if result:
                        stats["total_documents"] = result[0]
                    
                    # Count unique companies (use correct table name)
                    result = cursor.execute("SELECT COUNT(DISTINCT company_registration_number) FROM document_chunks_v2 WHERE company_registration_number IS NOT NULL").fetchone()
                    if result:
                        stats["companies_indexed"] = result[0]
        except Exception as e:
            logger.warning(f"⚠️  Could not get detailed stats: {str(e)}")
        
        logger.info(f"📊 Q&A Stats: {stats['total_chunks']} chunks, {stats['total_documents']} docs, {stats['companies_indexed']} companies")
        
        return jsonify({
            "success": True,
            "data": stats,
            "error": None
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Q&A Stats Error: {str(e)}")
        return jsonify({
            "success": False,
            "data": None,
            "error": "Could not retrieve statistics"
        }), 500


@qa_api.route('/api/qa/save-history', methods=['POST'])
def save_qa_history():
    """
    Save a Q&A exchange to the qa_history table.
    Called automatically by the frontend after every successful Q&A response.
    """
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Request must be JSON"}), 400

        data = request.get_json()

        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        if not question or not answer:
            return jsonify({"success": False, "error": "question and answer are required"}), 400

        company_id = data.get('company_id') or 0  # FK — default 0 if unknown
        company_number = data.get('company_number', '')
        company_name = data.get('company_name', '')
        document_id = data.get('document_id')
        confidence_score = float(data.get('confidence_score') or 0.0)
        sources_count = int(data.get('sources_count') or 0)
        response_time_ms = int(data.get('response_time_ms') or 0)
        session_id = data.get('session_id', '')

        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'credit_risk.db'
        )

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO qa_history
                    (company_id, company_number, company_name, document_id,
                     question, answer, confidence_score, sources_count,
                     response_time_ms, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, company_number, company_name, document_id,
                   question, answer, confidence_score, sources_count,
                   response_time_ms, session_id))
            row_id = cursor.lastrowid

        logger.info(f"Q&A history saved: row {row_id} — '{question[:60]}'")
        return jsonify({"success": True, "id": row_id}), 200

    except Exception as e:
        logger.error(f"Error saving Q&A history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500