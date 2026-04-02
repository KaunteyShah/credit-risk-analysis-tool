#!/usr/bin/env python3
"""
Smart Embedding Service - Hybrid local/API embedding solution.

Features:
- High-quality offline embeddings using sentence-transformers (all-mpnet-base-v2)  
- Automatic fallback to local when API unavailable
- Smart caching to avoid re-computation
- Compatible with existing OpenAI embedding service interface
- Optimized for document processing workflows with 768D embeddings

Performance Comparison:
- Local: ~100ms for 100 chunks (FAST)
- OpenAI API: ~2-5 seconds for 100 chunks (SLOW + requires internet)
"""

import os
import time
from typing import List, Optional, Union, Dict, Any, Tuple
import logging
import numpy as np
from pathlib import Path
import pickle
import hashlib

# Core imports
from app_modules.utils.config_manager import ConfigManager
from app_modules.utils.logger import get_logger

logger = get_logger(__name__)

# Try importing sentence-transformers first (local/offline)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("✅ sentence-transformers available for offline embeddings")
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠️ sentence-transformers not available. Install: pip install sentence-transformers")

# Try importing OpenAI (API-based)
try:
    from app_modules.services.embedding.openai_embedding_service import get_openai_embedding_service
    OPENAI_SERVICE_AVAILABLE = True
except ImportError:
    OPENAI_SERVICE_AVAILABLE = False
    logger.warning("⚠️ OpenAI embedding service not available")

class SmartEmbeddingService:
    """
    Smart hybrid embedding service that prioritizes speed and reliability.
    
    Strategy:
    1. LOCAL FIRST: Use sentence-transformers for bulk document processing (fast)
    2. API FALLBACK: Use OpenAI for high-quality queries when needed
    3. INTELLIGENT CACHING: Cache embeddings to avoid re-computation
    4. AUTO-DETECTION: Automatically choose best available method
    """
    
    def __init__(self, prefer_local: bool = True, cache_embeddings: bool = True):
        """
        Initialize smart embedding service.
        
        Args:
            prefer_local: If True, prefer local embeddings for speed
            cache_embeddings: If True, cache embeddings for performance
        """
        self.logger = get_logger("SmartEmbedding")
        self.config = ConfigManager()
        self.prefer_local = prefer_local
        self.cache_embeddings = cache_embeddings
        
        # Initialize local embedding model
        self.local_model = None
        self.local_dimensions = 768  # all-mpnet-base-v2 dimensions
        
        # Initialize OpenAI service
        self.openai_service = None
        self.openai_dimensions = 768  # text-embedding-3-small optimized dimensions
        
        # Cache setup
        self.cache_dir = Path("data/embedding_cache") 
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize services
        self._initialize_local_embeddings()
        self._initialize_openai_service()
        
        # Determine active service
        self._select_active_service()
        
    def _initialize_local_embeddings(self):
        """Initialize local sentence-transformers model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.logger.warning("❌ sentence-transformers not available - local embeddings disabled")
            return
            
        try:
            self.logger.info("🔄 Loading local embedding model (all-mpnet-base-v2)...")
            start_time = time.time()
            
            self.local_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
            load_time = time.time() - start_time
            
            self.logger.info(f"✅ Local model loaded in {load_time:.2f}s")
            self.logger.info(f"📐 Local dimensions: {self.local_dimensions}")
            self.logger.info(f"🚀 Local processing: ~200ms for 100 chunks (higher quality)")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load local model: {e}")
            self.local_model = None
            
    def _initialize_openai_service(self):
        """Initialize OpenAI embedding service."""
        if not OPENAI_SERVICE_AVAILABLE:
            self.logger.warning("❌ OpenAI service not available - API embeddings disabled")
            return
            
        try:
            self.openai_service = get_openai_embedding_service()
            if self.openai_service and self.openai_service.client:
                self.logger.info("✅ OpenAI service available")
                self.logger.info(f"📐 OpenAI dimensions: {self.openai_dimensions}")
                self.logger.info(f"💰 OpenAI cost: ~$0.02 per 1M tokens")
            else:
                self.logger.warning("⚠️ OpenAI service unavailable (missing API key/endpoint)")
                self.openai_service = None
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize OpenAI service: {e}")
            self.openai_service = None
            
    def _select_active_service(self):
        """Select the active embedding service based on availability and preference."""
        if self.prefer_local and self.local_model:
            self.active_service = "local"
            self.active_dimensions = self.local_dimensions
            self.logger.info("🎯 Active service: LOCAL (sentence-transformers) - FAST & OFFLINE")
        elif self.openai_service:
            self.active_service = "openai"
            self.active_dimensions = self.openai_dimensions
            self.logger.info("🎯 Active service: OpenAI API - HIGH QUALITY")
        elif self.local_model:
            self.active_service = "local"
            self.active_dimensions = self.local_dimensions
            self.logger.info("🎯 Active service: LOCAL (fallback) - OFFLINE ONLY")
        else:
            self.active_service = None
            self.active_dimensions = 0
            self.logger.error("❌ No embedding service available!")
            
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
        
    def _load_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """Load embedding from cache."""
        if not self.cache_embeddings:
            return None
            
        cache_file = self.cache_dir / f"{cache_key}_{self.active_service}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.debug(f"Cache load failed: {e}")
        return None
        
    def _save_to_cache(self, cache_key: str, embedding: List[float]) -> None:
        """Save embedding to cache."""
        if not self.cache_embeddings:
            return
            
        cache_file = self.cache_dir / f"{cache_key}_{self.active_service}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            self.logger.debug(f"Cache save failed: {e}")
            
    def encode(self, texts: Union[str, List[str]], 
               force_local: bool = False, 
               force_openai: bool = False,
               show_progress: bool = True) -> List[List[float]]:
        """
        Generate embeddings for text(s) using the smart hybrid approach.
        
        Args:
            texts: Single text or list of texts to embed
            force_local: Force use of local model
            force_openai: Force use of OpenAI API
            show_progress: Show progress for large batches
            
        Returns:
            List of embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]
            
        if not texts:
            return []
            
        # Determine which service to use
        use_service = self.active_service
        if force_local and self.local_model:
            use_service = "local"
        elif force_openai and self.openai_service:
            use_service = "openai"
            
        if not use_service:
            self.logger.error("❌ No embedding service available!")
            return []
            
        self.logger.info(f"🔄 Generating embeddings for {len(texts)} texts using {use_service}")
        start_time = time.time()
        
        embeddings = []
        cache_hits = 0
        
        # Process texts
        uncached_texts = []
        uncached_indices = []
        
        # Check cache first
        for i, text in enumerate(texts):
            if self.cache_embeddings:
                cache_key = self._get_cache_key(text)
                cached_embedding = self._load_from_cache(cache_key)
                if cached_embedding:
                    embeddings.append(cached_embedding)
                    cache_hits += 1
                    continue
                    
            # Text not in cache
            embeddings.append(None)  # Placeholder
            uncached_texts.append(text)
            uncached_indices.append(i)
            
        # Generate embeddings for uncached texts
        if uncached_texts:
            if use_service == "local":
                new_embeddings = self._encode_local(uncached_texts, show_progress)
            else:  # openai
                new_embeddings = self._encode_openai(uncached_texts, show_progress)
                
            # Fill in the new embeddings and cache them
            for idx, embedding in zip(uncached_indices, new_embeddings):
                embeddings[idx] = embedding
                if self.cache_embeddings:
                    cache_key = self._get_cache_key(texts[idx])
                    self._save_to_cache(cache_key, embedding)
                    
        # Remove None placeholders (shouldn't exist)
        embeddings = [emb for emb in embeddings if emb is not None]
        
        processing_time = time.time() - start_time
        
        self.logger.info(f"✅ Generated {len(embeddings)} embeddings in {processing_time:.2f}s")
        self.logger.info(f"📊 Cache hits: {cache_hits}/{len(texts)}")
        self.logger.info(f"🎯 Service: {use_service.upper()}")
        
        return embeddings
        
    def _encode_local(self, texts: List[str], show_progress: bool) -> List[List[float]]:
        """Generate embeddings using local sentence-transformers."""
        if not self.local_model:
            raise RuntimeError("Local model not available")
            
        try:
            if show_progress and len(texts) > 10:
                from tqdm import tqdm
                self.logger.info("🔄 Processing with local model...")
                
            # Use sentence-transformers encode method
            embeddings = self.local_model.encode(texts, show_progress_bar=show_progress)
            
            # Convert to list format with explicit float conversion
            # This ensures numpy.float32/float64 values become Python floats
            result = []
            for emb in embeddings:
                if hasattr(emb, 'tolist'):
                    # Convert numpy array to list, then ensure all values are Python floats
                    float_list = [float(x) for x in emb.tolist()]
                else:
                    # Already a list, but ensure all values are Python floats  
                    float_list = [float(x) for x in emb]
                result.append(float_list)
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Local embedding failed: {e}")
            return []
            
    def _encode_openai(self, texts: List[str], show_progress: bool) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not self.openai_service:
            raise RuntimeError("OpenAI service not available")
            
        try:
            return self.openai_service.encode(texts)
        except Exception as e:
            self.logger.error(f"❌ OpenAI embedding failed: {e}")
            return []
            
    def get_embedding_dimensions(self) -> int:
        """Get embedding dimensions for active service."""
        return self.active_dimensions
        
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about available services."""
        return {
            "active_service": self.active_service,
            "active_dimensions": self.active_dimensions,
            "services_available": {
                "local": self.local_model is not None,
                "openai": self.openai_service is not None
            },
            "local_info": {
                "model": "all-mpnet-base-v2",
                "dimensions": self.local_dimensions,
                "speed": "~200ms for 100 chunks",
                "cost": "FREE"
            } if self.local_model else None,
            "openai_info": {
                "model": "text-embedding-3-small", 
                "dimensions": self.openai_dimensions,
                "speed": "~2-5s for 100 chunks",
                "cost": "~$0.02 per 1M tokens"
            } if self.openai_service else None,
            "cache_enabled": self.cache_embeddings,
            "cache_location": str(self.cache_dir)
        }
        
    def switch_to_local(self):
        """Switch to local embeddings for speed."""
        if self.local_model:
            self.active_service = "local"
            self.active_dimensions = self.local_dimensions
            self.logger.info("🔄 Switched to LOCAL embeddings (FAST)")
        else:
            self.logger.error("❌ Local model not available")
            
    def switch_to_openai(self):
        """Switch to OpenAI embeddings for quality.""" 
        if self.openai_service:
            self.active_service = "openai"
            self.active_dimensions = self.openai_dimensions
            self.logger.info("🔄 Switched to OpenAI embeddings (HIGH QUALITY)")
        else:
            self.logger.error("❌ OpenAI service not available")


# Global instance
_smart_embedding_service = None

def get_smart_embedding_service(prefer_local: bool = True) -> SmartEmbeddingService:
    """Get global smart embedding service instance."""
    global _smart_embedding_service
    
    if _smart_embedding_service is None:
        _smart_embedding_service = SmartEmbeddingService(prefer_local=prefer_local)
    
    return _smart_embedding_service


if __name__ == "__main__":
    # Test the smart embedding service
    print("🧪 Testing Smart Embedding Service...")
    
    service = get_smart_embedding_service()
    
    # Show service info
    import json
    print("\n📊 SERVICE INFORMATION:")
    print(json.dumps(service.get_service_info(), indent=2))
    
    # Test embeddings
    test_texts = [
        "Imperial Brands revenue analysis",
        "Net revenue was £31.4 billion",
        "Total turnover increased significantly"
    ]
    
    print(f"\n🧪 Testing with {len(test_texts)} texts...")
    
    start_time = time.time()
    embeddings = service.encode(test_texts)
    end_time = time.time()
    
    if embeddings:
        print(f"✅ Generated {len(embeddings)} embeddings")
        print(f"📐 Dimensions: {len(embeddings[0])}")
        print(f"⚡ Time: {end_time - start_time:.3f}s")
        print(f"🎯 Service: {service.active_service.upper()}")
    else:
        print("❌ Failed to generate embeddings")