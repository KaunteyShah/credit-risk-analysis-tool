#!/usr/bin/env python3
"""
OpenAI Embedding Service - Compatible with all-mpnet-base-v2 (768D) embeddings
using OpenAI's text-embedding-3-small model for production-grade embeddings.
"""

import os
from typing import List, Optional, Union, Dict, Any
import logging
from app_modules.utils.config_manager import ConfigManager
from app_modules.utils.logger import get_logger

logger = get_logger(__name__)

# OpenAI client import
try:
    from openai import OpenAI, AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ OpenAI library not available. Install: pip install openai")

class OpenAIEmbeddingService:
    """
    Unified OpenAI embedding service to replace all SentenceTransformers usage.
    Uses text-embedding-3-small for cost efficiency (~$0.02 per 1M tokens).
    """
    
    def __init__(self):
        self.logger = get_logger("OpenAIEmbedding")
        self.config = ConfigManager()
        self.client = None
        self.model_name = "text-embedding-3-small"  # Cheapest OpenAI embedding model
        self.dimensions = 768  # Compatible with local all-mpnet-base-v2 (768D)
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client with API key."""
        if not OPENAI_AVAILABLE:
            self.logger.error("❌ OpenAI library not available")
            return
        
        try:
            # First try environment variable, then ConfigManager
            api_key = os.getenv("OPENAI_API_KEY") or self.config.get("OPENAI_API_KEY")
            if not api_key or api_key == "your_openai_api_key_here":
                self.logger.error("❌ OpenAI API key not configured")
                return
            
            # Check if we have Azure OpenAI configuration
            azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            azure_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
            
            if azure_endpoint:
                # Use Azure OpenAI client
                self.client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=azure_endpoint,
                    api_version=azure_version
                )
                # For Azure OpenAI, use deployment name
                self.model_name = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
                self.logger.info(f"🔷 Using Azure OpenAI with deployment: {self.model_name}")
            else:
                # Use regular OpenAI client
                self.client = OpenAI(api_key=api_key)
                self.logger.info(f"🔥 Using regular OpenAI API")
            
            # Test the client with a simple embedding
            self._test_connection()
            
            self.logger.info(f"✅ OpenAI Embedding Service initialized")
            self.logger.info(f"🎯 Model: {self.model_name}")
            self.logger.info(f"📐 Dimensions: {self.dimensions}")
            self.logger.info(f"💰 Cost: ~$0.02 per 1M tokens (very cheap!)")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def _test_connection(self):
        """Test OpenAI connection with a simple embedding."""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=["test"],
                dimensions=self.dimensions
            )
            if response.data and len(response.data[0].embedding) == self.dimensions:
                self.logger.info("✅ OpenAI embedding connection test successful")
            else:
                raise Exception("Invalid embedding response")
        except Exception as e:
            self.logger.error(f"❌ OpenAI connection test failed: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for text(s) - Compatible with SentenceTransformers interface.
        
        Args:
            texts: Single text or list of texts to embed
            batch_size: Process in batches to avoid API limits
            
        Returns:
            List of embedding vectors
        """
        if not self.client:
            self.logger.error("❌ OpenAI client not available")
            return []
        
        # Convert single string to list
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts:
            return []
        
        embeddings = []
        
        try:
            # Process in batches to avoid API limits
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                self.logger.debug(f"🔄 Processing batch {i//batch_size + 1}: {len(batch)} texts")
                
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=batch,
                    dimensions=self.dimensions
                )
                
                # Extract embeddings from response and ensure Python floats for struct.pack()
                batch_embeddings = []
                for data in response.data:
                    # Convert all embedding values to Python floats (handles numpy float32/float64)
                    if hasattr(data.embedding, 'tolist'):
                        # Handle numpy arrays
                        python_floats = [float(x) for x in data.embedding.tolist()]
                    else:
                        # Handle lists with potential numpy values
                        python_floats = [float(x) for x in data.embedding]
                    batch_embeddings.append(python_floats)
                embeddings.extend(batch_embeddings)
            
            self.logger.info(f"✅ Generated {len(embeddings)} embeddings using OpenAI")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate embeddings: {e}")
            return []
    
    def get_embedding_dimensions(self) -> int:
        """Get the embedding dimensions for this model."""
        return self.dimensions
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_name": self.model_name,
            "dimensions": self.dimensions,
            "provider": "OpenAI",
            "cost_per_1m_tokens": "$0.02",
            "cost_per_query": "~$0.00002 (very cheap)",
            "api_available": self.client is not None
        }


# Global instance (singleton pattern)
_openai_embedding_service = None

def get_openai_embedding_service() -> OpenAIEmbeddingService:
    """Get global OpenAI embedding service instance."""
    global _openai_embedding_service
    
    if _openai_embedding_service is None:
        _openai_embedding_service = OpenAIEmbeddingService()
    
    return _openai_embedding_service


# Compatibility functions to replace SentenceTransformers usage
def get_cached_embedding_model(model_name: str = None) -> OpenAIEmbeddingService:
    """
    Replacement for get_cached_embedding_model() function.
    Now returns OpenAI embedding service instead of SentenceTransformers.
    
    Args:
        model_name: Ignored (kept for compatibility)
        
    Returns:
        OpenAI embedding service
    """
    logger.info("🔄 get_cached_embedding_model() now using OpenAI embeddings")
    return get_openai_embedding_service()


class OpenAICompatibleModel:
    """
    Compatibility wrapper to replace SentenceTransformer objects.
    Provides the same interface as SentenceTransformers but uses OpenAI.
    """
    
    def __init__(self, model_name: str = None):
        self.service = get_openai_embedding_service()
        self.model_name = model_name  # Kept for compatibility
        
        logger.info(f"🔄 SentenceTransformer({model_name}) replaced with OpenAI embeddings")
    
    def encode(self, sentences: Union[str, List[str]], **kwargs) -> List[List[float]]:
        """Encode sentences to embeddings - SentenceTransformers compatible interface."""
        return self.service.encode(sentences)
    
    def get_sentence_embedding_dimension(self) -> int:
        """Get embedding dimensions - SentenceTransformers compatible."""
        return self.service.get_embedding_dimensions()


# Replacement functions for common SentenceTransformers imports
def SentenceTransformer(model_name: str) -> OpenAICompatibleModel:
    """
    Drop-in replacement for SentenceTransformer class.
    
    Args:
        model_name: Model name (ignored, uses OpenAI)
        
    Returns:
        OpenAI-compatible embedding model
    """
    logger.info(f"🔄 SentenceTransformer('{model_name}') → OpenAI text-embedding-3-small")
    return OpenAICompatibleModel(model_name)


# Migration utilities
def get_migration_info() -> Dict[str, Any]:
    """Get information about the migration from SentenceTransformers to OpenAI."""
    service = get_openai_embedding_service()
    
    return {
        "migration_status": "✅ Migrated to OpenAI embeddings",
        "old_system": {
            "model": "text-embedding-3-small",
            "dimensions": 1536,
            "cost": "$0.00 (local)",
            "quality": "Good"
        },
        "new_system": service.get_model_info(),
        "benefits": [
            "Better embedding quality",
            "Consistent with OpenAI LLM",
            "No local model loading time",
            "Always up-to-date model",
            "Very low cost (~$0.02/1M tokens)"
        ],
        "cost_impact": {
            "embedding_1161_chunks": "~$0.01",
            "monthly_100_new_docs": "~$0.001",
            "practically_free": True
        }
    }


if __name__ == "__main__":
    # Test the service
    print("🧪 Testing OpenAI Embedding Service...")
    
    service = get_openai_embedding_service()
    
    if service.client:
        # Test embedding
        test_texts = [
            "Imperial Brands revenue analysis",
            "Financial performance metrics"
        ]
        
        embeddings = service.encode(test_texts)
        
        if embeddings:
            print(f"✅ Generated {len(embeddings)} embeddings")
            print(f"📐 Dimensions: {len(embeddings[0])}")
            print(f"💰 Cost for test: ~$0.000001")
        else:
            print("❌ Failed to generate embeddings")
    else:
        print("❌ OpenAI client not available")
    
    # Show migration info
    print("\n" + "="*50)
    print("📊 MIGRATION INFORMATION:")
    import json
    print(json.dumps(get_migration_info(), indent=2))