"""
OpenAI Embedding Service Cache

Replaces SentenceTransformers with OpenAI text-embedding-3-small.
Provides same interface for backward compatibility while using OpenAI embeddings.
Cost: ~$0.02 per 1M tokens (very cheap!).
"""

import logging
from typing import Optional
from threading import Lock

# Import OpenAI embedding service instead of SentenceTransformers
try:
    from app_modules.services.optimized_embedding_service import get_openai_embedding_service, OpenAICompatibleModel
    OPENAI_EMBEDDING_AVAILABLE = True
except ImportError:
    OPENAI_EMBEDDING_AVAILABLE = False
    raise ImportError("Optimized embedding service required")


class OpenAIEmbeddingCache:
    """
    OpenAI embedding cache - replaces SentenceTransformers caching.
    
    Uses OpenAI text-embedding-3-small for all embedding operations.
    Provides same interface as original cache for backward compatibility.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self.logger = logging.getLogger(__name__)
            self._service = None
            self._usage_stats = 0
            self._initialized = True
            self.logger.info("✅ OpenAI embedding cache initialized")
    
    def get_model(self, model_name: Optional[str] = None) -> Optional[OpenAICompatibleModel]:
        """
        Get OpenAI embedding service (ignores model_name for compatibility).
        
        Args:
            model_name: Ignored (kept for backward compatibility)
            
        Returns:
            OpenAI-compatible embedding model
        """
        if not OPENAI_EMBEDDING_AVAILABLE:
            raise ImportError("OpenAI embedding service required - check openai_embedding_service.py")
        
        # Log usage
        self._usage_stats += 1
        
        if model_name and model_name != "text-embedding-3-small":
            self.logger.info(f"� Requested '{model_name}' → using OpenAI text-embedding-3-small")
        
        # Return OpenAI-compatible model
        try:
            compatible_model = OpenAICompatibleModel(model_name)
            self.logger.debug(f"� Using OpenAI embeddings (used {self._usage_stats} times)")
            return compatible_model
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get OpenAI embedding model: {e}")
            return None
    
    def get_openai_service(self):
        """Get the underlying OpenAI embedding service."""
        if self._service is None:
            self._service = get_openai_embedding_service()
        return self._service
    
    def clear_cache(self):
        """Clear cache (no-op for OpenAI service)."""
        self._usage_stats = 0
        self.logger.info("🧹 Reset OpenAI embedding usage stats")
    
    def get_cache_stats(self) -> dict:
        """
        Get usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        service = self.get_openai_service()
        return {
            'embedding_service': 'OpenAI text-embedding-3-small',
            'usage_count': self._usage_stats,
            'model_info': service.get_model_info() if service else {},
            'migration_status': '✅ Migrated from SentenceTransformers'
        }


# Global singleton instance (renamed but compatible)
embedding_cache = OpenAIEmbeddingCache()

# Backward compatibility alias
EmbeddingModelCache = OpenAIEmbeddingCache


def get_cached_embedding_model(model_name: str = "text-embedding-3-small") -> Optional[OpenAICompatibleModel]:
    """
    Convenience function to get OpenAI embedding model (replaces SentenceTransformers).
    
    Args:
        model_name: Ignored (kept for backward compatibility)
        
    Returns:
        OpenAI-compatible embedding model
    """
    if model_name != "text-embedding-3-small":
        logger = logging.getLogger(__name__)
        logger.info(f"🔄 get_cached_embedding_model('{model_name}') → OpenAI text-embedding-3-small")
    
    return embedding_cache.get_model(model_name)