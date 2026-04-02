"""
Vectorization Status API
Provides endpoints to check if documents have been vectorized for Q&A functionality.
"""

from flask import Blueprint, jsonify, request
from app_modules.database.vector_connection import VectorDatabaseConnection
from app_modules.config.app_config import get_config
import sqlite3
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
vectorization_api = Blueprint('vectorization_api', __name__)

@vectorization_api.route('/api/vectorization/check/<company_number>', methods=['GET'])
def check_vectorization_status(company_number):
    """
    Check if a company's documents have been vectorized for Q&A.
    
    Args:
        company_number: Company registration number
        
    Returns:
        JSON response with vectorization status
    """
    try:
        logger.info(f"Checking vectorization status for company {company_number}")
        
        vector_db = VectorDatabaseConnection()
        
        with vector_db.get_connection() as conn:
            # Check if company has any vectorized documents
            cursor = conn.execute('''
                SELECT 
                    COUNT(DISTINCT d.document_id) as document_count,
                    COUNT(c.chunk_id) as chunk_count,
                    MAX(d.updated_at) as last_updated,
                    d.company_name
                FROM documents_v2 d 
                LEFT JOIN document_chunks_v2 c ON d.document_id = c.document_id 
                WHERE d.company_number = ?
                GROUP BY d.company_number, d.company_name
            ''', (company_number,))
            
            result = cursor.fetchone()
            
            if result and result[0] > 0 and result[1] > 0:
                document_count, chunk_count, last_updated, company_name = result
                
                return jsonify({
                    'success': True,
                    'vectorized': True,
                    'company_number': company_number,
                    'company_name': company_name,
                    'document_count': document_count,
                    'chunk_count': chunk_count,
                    'last_updated': last_updated,
                    'message': f'Company has {document_count} vectorized documents with {chunk_count} chunks'
                })
            else:
                # Check if company exists but not vectorized
                cursor = conn.execute('''
                    SELECT company_name FROM documents_v2 
                    WHERE company_number = ? 
                    LIMIT 1
                ''', (company_number,))
                
                company_result = cursor.fetchone()
                company_name = company_result[0] if company_result else 'Unknown Company'
                
                return jsonify({
                    'success': True,
                    'vectorized': False,
                    'company_number': company_number,
                    'company_name': company_name,
                    'document_count': 0,
                    'chunk_count': 0,
                    'message': 'No vectorized documents found for this company'
                })
                
    except Exception as e:
        logger.error(f"Error checking vectorization status for {company_number}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to check vectorization status'
        }), 500


@vectorization_api.route('/api/vectorization/revenue-precheck/<company_number>', methods=['GET'])
def check_revenue_precheck_status(company_number):
    """
    Check if documents are vectorized for revenue update and estimate processing time.
    
    Args:
        company_number: Company registration number
        
    Returns:
        JSON response with vectorization status and time estimation
    """
    try:
        logger.info(f"Revenue pre-check for company {company_number}")
        
        # Check vector database status
        try:
            vector_db = VectorDatabaseConnection()
            vec_conn_ok = True
        except Exception as vec_init_err:
            logger.warning(f"⚠️ Vector DB init failed in precheck: {vec_init_err} — treating as not vectorized")
            vec_conn_ok = False

        if not vec_conn_ok:
            return jsonify({
                'success': True,
                'vectorized': False,
                'company_number': company_number,
                'estimated_time_minutes': 5,
                'processing_type': 'full',
                'message': 'Vector database unavailable — full extraction will run'
            })

        try:
            conn_ctx = vector_db.get_connection()
        except Exception as vec_conn_err:
            logger.warning(f"⚠️ Vector DB connection failed in precheck: {vec_conn_err} — treating as not vectorized")
            return jsonify({
                'success': True,
                'vectorized': False,
                'company_number': company_number,
                'estimated_time_minutes': 5,
                'processing_type': 'full',
                'message': 'Vector database unavailable — full extraction will run'
            })

        try:
            with conn_ctx as conn:
                # Check if company has any vectorized documents
                cursor = conn.execute('''
                    SELECT 
                        COUNT(DISTINCT d.document_id) as document_count,
                        COUNT(c.chunk_id) as chunk_count,
                        MAX(d.updated_at) as last_updated,
                        d.company_name
                    FROM documents_v2 d 
                    LEFT JOIN document_chunks_v2 c ON d.document_id = c.document_id 
                    WHERE d.company_number = ?
                    GROUP BY d.company_number, d.company_name
                ''', (company_number,))

                result = cursor.fetchone()
                is_vectorized = result and result[0] > 0 and result[1] > 0
        except Exception as vec_query_err:
            logger.warning(f"⚠️ Vector DB query failed in precheck: {vec_query_err} — treating as not vectorized")
            return jsonify({
                'success': True,
                'vectorized': False,
                'company_number': company_number,
                'estimated_time_minutes': 5,
                'processing_type': 'full',
                'message': 'Vector database query failed — full extraction will run'
            })
        is_vectorized = is_vectorized  # keep reference outside try block

        if is_vectorized:
            document_count, chunk_count, last_updated, company_name = result
            return jsonify({
                'success': True,
                'vectorized': True,
                'company_number': company_number,
                'company_name': company_name,
                'document_count': document_count,
                'chunk_count': chunk_count,
                'estimated_time_minutes': 0,  # Already vectorized - fast processing
                'processing_type': 'fast',
                'message': f'Documents already processed ({chunk_count} chunks). Revenue extraction will be fast!'
            })

        # If not vectorized, estimate processing time based on document pages
        # Check if we have filing history with document information
        config = get_config()
        main_db_path = config.database_path

        with sqlite3.connect(main_db_path) as main_conn:
            cursor = main_conn.execute('''
                SELECT 
                    cf.company_name,
                    COUNT(cf.transaction_id) as filing_count,
                    cf.description,
                    cf.document_link
                FROM company_filing_history_accounts cf
                WHERE cf.company_registration_number = ?
                AND cf.document_link IS NOT NULL
                GROUP BY cf.company_name
                LIMIT 1
            ''', (company_number,))

            filing_result = cursor.fetchone()

            if filing_result:
                company_name, filing_count, description, document_link = filing_result

                # Estimate processing time:
                # Group accounts: ~5 minutes (typically 20+ pages)
                # Small company accounts: ~2 minutes (typically 8 pages)
                # Micro accounts: ~1 minute (typically 4 pages)
                # Standard accounts: ~3 minutes (typically 12 pages)

                if 'group' in description.lower():
                    estimated_minutes = 5
                    processing_note = "Group accounts - complex filings"
                elif 'micro' in description.lower():
                    estimated_minutes = 1
                    processing_note = "Micro entity accounts - simple filings"
                elif 'small' in description.lower():
                    estimated_minutes = 2
                    processing_note = "Small company accounts - moderate filings"
                else:
                    estimated_minutes = 3
                    processing_note = "Standard accounts - average filings"

                # Return the estimation for non-vectorized documents
                return jsonify({
                    'success': True,
                    'vectorized': False,
                    'company_number': company_number,
                    'company_name': company_name,
                    'document_count': filing_count,
                    'chunk_count': 0,
                    'estimated_time_minutes': estimated_minutes,
                    'processing_type': 'slow',
                    'processing_note': processing_note,
                    'filing_type': description,
                    'message': f'Document needs processing (~{estimated_minutes} minutes estimated based on {description}).'
                })
            else:
                # No filing information found
                return jsonify({
                    'success': True,
                    'vectorized': False,
                    'company_number': company_number,
                    'company_name': 'Unknown Company',
                    'document_count': 0,
                    'chunk_count': 0,
                    'estimated_time_minutes': 3,
                    'processing_type': 'slow',
                    'processing_note': 'Document information not available',
                    'message': 'Document needs processing (~3 minutes estimated).'
                })

    except Exception as e:
        logger.error(f"Error in revenue pre-check for {company_number}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to check revenue processing status'
        }), 500

@vectorization_api.route('/api/vectorization/stats', methods=['GET'])
def get_vectorization_stats():
    """
    Get overall vectorization statistics.
    
    Returns:
        JSON response with system-wide vectorization stats
    """
    try:
        logger.info("Getting vectorization statistics")
        
        vector_db = VectorDatabaseConnection()
        
        with vector_db.get_connection() as conn:
            # Get overall stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(DISTINCT d.document_id) as total_documents,
                    COUNT(DISTINCT d.company_number) as total_companies,
                    COUNT(c.chunk_id) as total_chunks,
                    AVG(CAST(chunks_per_doc.chunk_count AS FLOAT)) as avg_chunks_per_doc
                FROM documents_v2 d 
                LEFT JOIN document_chunks_v2 c ON d.document_id = c.document_id
                LEFT JOIN (
                    SELECT document_id, COUNT(*) as chunk_count
                    FROM document_chunks_v2 
                    GROUP BY document_id
                ) chunks_per_doc ON d.document_id = chunks_per_doc.document_id
            ''')
            
            result = cursor.fetchone()
            
            if result:
                total_documents, total_companies, total_chunks, avg_chunks = result
                
                # Get top companies by chunk count
                cursor = conn.execute('''
                    SELECT 
                        d.company_name,
                        d.company_number,
                        COUNT(c.chunk_id) as chunk_count,
                        COUNT(DISTINCT d.document_id) as document_count
                    FROM documents_v2 d 
                    LEFT JOIN document_chunks_v2 c ON d.document_id = c.document_id 
                    GROUP BY d.company_number, d.company_name
                    HAVING chunk_count > 0
                    ORDER BY chunk_count DESC
                    LIMIT 10
                ''')
                
                top_companies = []
                for row in cursor.fetchall():
                    top_companies.append({
                        'company_name': row[0],
                        'company_number': row[1],
                        'chunk_count': row[2],
                        'document_count': row[3]
                    })
                
                return jsonify({
                    'success': True,
                    'stats': {
                        'total_documents': total_documents or 0,
                        'total_companies': total_companies or 0,
                        'total_chunks': total_chunks or 0,
                        'avg_chunks_per_doc': round(avg_chunks or 0, 1),
                        'top_companies': top_companies
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'stats': {
                        'total_documents': 0,
                        'total_companies': 0,
                        'total_chunks': 0,
                        'avg_chunks_per_doc': 0,
                        'top_companies': []
                    }
                })
                
    except Exception as e:
        logger.error(f"Error getting vectorization statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get vectorization statistics'
        }), 500

@vectorization_api.route('/api/vectorization/health', methods=['GET'])
def vectorization_health():
    """
    Health check for vectorization API.
    
    Returns:
        JSON response with health status
    """
    try:
        vector_db = VectorDatabaseConnection()
        
        with vector_db.get_connection() as conn:
            # Simple connectivity test
            cursor = conn.execute('SELECT 1')
            cursor.fetchone()
            
        return jsonify({
            'success': True,
            'status': 'healthy',
            'message': 'Vectorization API is operational'
        })
        
    except Exception as e:
        logger.error(f"Vectorization health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Vectorization API health check failed'
        }), 500