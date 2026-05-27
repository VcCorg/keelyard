"""LightRAG API Server."""

import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=os.getenv("LIGHTRAG_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LightRAG API", version="1.0.0")

# Global LightRAG instance
rag_instance = None

# Thread pool for running sync LightRAG operations
executor = ThreadPoolExecutor(max_workers=4)


class InsertRequest(BaseModel):
    """Request model for inserting documents."""
    text: str
    metadata: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    """Request model for querying."""
    query: str
    mode: str = "hybrid"  # Options: naive, local, global, hybrid
    top_k: int = 10


class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str
    top_k: int = 10


async def initialize_lightrag():
    """Initialize LightRAG instance with provider-specific configuration."""
    global rag_instance
    
    try:
        from lightrag import LightRAG, QueryParam
        
        # Patch LightRAG library bug: replace() should be called on dataclass instances
        # This monkey-patches the __post_init__ method to avoid the TypeError
        import lightrag.lightrag as lightrag_module
        original_post_init = lightrag_module.LightRAG.__post_init__
        
        def patched_post_init(self):
            """Patched __post_init__ that skips the problematic replace() call."""
            # Skip the problematic line that causes: TypeError: replace() should be called on dataclass instances
            # The original code tries to use dataclasses.replace() on a function object
            # We'll manually set the func attribute instead
            if hasattr(self.embedding_func, 'func'):
                # Already has the func attribute, skip the replace call
                pass
            else:
                # Add func attribute manually instead of using replace()
                self.embedding_func.func = self.embedding_func
        
        # Apply the patch
        lightrag_module.LightRAG.__post_init__ = patched_post_init
        logger.info("Applied LightRAG library bug patch")
        
        working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "/data/lightrag")
        os.makedirs(working_dir, exist_ok=True)
        
        # Determine LLM and embedding providers
        llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        
        logger.info(f"Initializing LightRAG with working_dir: {working_dir}")
        logger.info(f"LLM Provider: {llm_provider}, Embedding Provider: {embedding_provider}")
        
        # Configure LLM function based on provider
        if llm_provider == "gemini":
            # Gemini API (requires GEMINI_API_KEY from Google AI Studio)
            from lightrag.llm.gemini import gemini_complete_if_cache as _gemini_complete
            
            llm_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            
            if not gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY not set. Get your API key from: "
                    "https://makersuite.google.com/app/apikey"
                )
            
            # LightRAG calls: func(prompt, system_prompt=..., **kwargs)
            # But Gemini expects: func(model, prompt, system_prompt=..., **kwargs)
            # We need to inject the model parameter and api_key
            import functools
            
            @functools.wraps(_gemini_complete)
            async def gemini_wrapper(*args, **kwargs):
                """Wrapper that injects model parameter and API key for Gemini."""
                if 'api_key' not in kwargs:
                    kwargs['api_key'] = gemini_api_key
                return await _gemini_complete(llm_model_name, *args, **kwargs)
            
            # Add func attribute for compatibility with LightRAG's caching
            gemini_wrapper.func = gemini_wrapper
            
            llm_model_func = gemini_wrapper
            logger.info(f"Using Gemini API LLM: {llm_model_name}")
            
        elif llm_provider == "vertex_ai":
            # Vertex AI (requires GCP credentials via ADC or service account)
            # Note: LightRAG's gemini module uses Gemini API, not Vertex AI
            # For true Vertex AI support, we need to use a custom implementation
            from lightrag.llm.openai import openai_complete_if_cache
            from vertexai.preview.generative_models import GenerativeModel
            import vertexai
            import functools
            from google.auth import default
            from google.auth.transport.requests import Request
            
            project_id = os.getenv("GOOGLE_PROJECT_ID")
            location = os.getenv("GOOGLE_LOCATION", "us-central1")
            llm_model_name = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")
            
            if not project_id:
                raise ValueError("GOOGLE_PROJECT_ID not set for Vertex AI")
            
            # Explicitly load Application Default Credentials
            credentials, _ = default()
            # Refresh credentials to ensure they're valid
            if hasattr(credentials, 'refresh') and hasattr(credentials, 'token'):
                credentials.refresh(Request())
            
            # Initialize Vertex AI with explicit credentials
            vertexai.init(project=project_id, location=location, credentials=credentials)
            
            # Create custom wrapper for Vertex AI
            @functools.wraps(openai_complete_if_cache)
            async def vertex_ai_wrapper(prompt: str, system_prompt: str = None, **kwargs):
                """Custom wrapper for Vertex AI Gemini models."""
                model = GenerativeModel(llm_model_name)
                
                # Combine system prompt and user prompt
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                
                # Generate response
                response = await asyncio.to_thread(
                    model.generate_content,
                    full_prompt,
                    generation_config=kwargs.get('generation_config')
                )
                
                return response.text
            
            # Add func attribute for compatibility with LightRAG's caching
            vertex_ai_wrapper.func = vertex_ai_wrapper
            
            llm_model_func = vertex_ai_wrapper
            logger.info(f"Using Vertex AI LLM: {llm_model_name} (project: {project_id}, location: {location})")
        elif llm_provider == "anthropic":
            from lightrag.llm.anthropic import anthropic_complete_if_cache
            llm_model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            llm_model_func = anthropic_complete_if_cache
            logger.info(f"Using Anthropic LLM: {llm_model_name}")
        else:  # Default to OpenAI
            from lightrag.llm.openai import openai_complete_if_cache
            llm_model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            llm_model_func = openai_complete_if_cache
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set, LightRAG may not work properly")
            logger.info(f"Using OpenAI LLM: {llm_model_name}")
        
        # Configure embedding function based on provider
        if embedding_provider == "gemini":
            # Gemini API embeddings (uses same API key as Gemini LLM)
            logger.info("Note: Gemini API doesn't have dedicated embedding endpoint")
            logger.info("Falling back to OpenAI embeddings for now")
            from lightrag.llm.openai import openai_embed
            embedding_func = openai_embed
            
        elif embedding_provider == "vertex_ai":
            # Vertex AI embeddings
            try:
                logger.info("Attempting to use Vertex AI embeddings via custom implementation")
                import vertexai
                from vertexai.language_models import TextEmbeddingModel
                from google.auth import default
                from google.auth.transport.requests import Request
                
                # Initialize Vertex AI
                project_id = os.getenv("GOOGLE_PROJECT_ID")
                location = os.getenv("GOOGLE_LOCATION", "us-central1")
                embedding_model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-005")
                
                if not project_id:
                    raise ValueError("GOOGLE_PROJECT_ID not set for Vertex AI embeddings")
                
                # Explicitly load Application Default Credentials
                credentials, _ = default()
                # Refresh credentials to ensure they're valid
                if hasattr(credentials, 'refresh') and hasattr(credentials, 'token'):
                    credentials.refresh(Request())
                
                vertexai.init(project=project_id, location=location, credentials=credentials)
                
                # Create custom embedding function for Vertex AI
                async def vertex_ai_embed(texts: list[str]) -> list[list[float]]:
                    """Custom Vertex AI embedding function."""
                    model = TextEmbeddingModel.from_pretrained(embedding_model_name)
                    embeddings = []
                    for text in texts:
                        embedding = await asyncio.to_thread(
                            lambda t: model.get_embeddings([t])[0].values,
                            text
                        )
                        embeddings.append(embedding)
                    return embeddings
                
                # Add required attributes to the function
                vertex_ai_embed.embedding_dim = 768
                vertex_ai_embed.max_token_size = 2048
                vertex_ai_embed.func = vertex_ai_embed  # Add func attribute for LightRAG compatibility
                embedding_func = vertex_ai_embed
                logger.info(f"Using Vertex AI embeddings: {embedding_model_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize Vertex AI embeddings: {e}")
                logger.info("Falling back to OpenAI embeddings")
                from lightrag.llm.openai import openai_embed
                embedding_func = openai_embed
                
        elif embedding_provider == "anthropic":
            from lightrag.llm.anthropic import anthropic_embed
            embedding_func = anthropic_embed
            logger.info("Using Anthropic embeddings")
        else:  # Default to OpenAI
            from lightrag.llm.openai import openai_embed
            embedding_func = openai_embed
            logger.info("Using OpenAI embeddings")
        
        # Initialize LightRAG with configured functions
        rag_instance = LightRAG(
            working_dir=working_dir,
            llm_model_name=llm_model_name,
            llm_model_func=llm_model_func,
            embedding_func=embedding_func,
            embedding_batch_num=10,
        )
        
        # Initialize storages (required for LightRAG to work properly)
        await rag_instance.initialize_storages()
        
        # Add missing doc_status attribute to fix LightRAG library bug
        # LightRAG 1.4.16 expects this attribute but doesn't initialize it
        if not hasattr(rag_instance, 'doc_status'):
            rag_instance.doc_status = {}
        
        # Skip pipeline status initialization due to library compatibility issues
        # The basic insert/query functionality should work without it
        
        logger.info(f"LightRAG initialized successfully with {llm_provider} LLM and {embedding_provider} embeddings")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize LightRAG: {e}")
        logger.exception(e)
        return False


@app.on_event("startup")
async def startup_event():
    """Initialize LightRAG on startup."""
    success = await initialize_lightrag()
    if not success:
        logger.warning("LightRAG initialization failed, some endpoints may not work")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "lightrag_initialized": rag_instance is not None
    }


@app.post("/insert")
async def insert_document(request: InsertRequest) -> Dict[str, Any]:
    """
    Insert a document into LightRAG.
    
    Args:
        request: InsertRequest with text and optional metadata
        
    Returns:
        Success status and message
    """
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="LightRAG not initialized")
    
    try:
        # Run sync insert in thread pool to avoid event loop conflicts
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, rag_instance.insert, request.text)
        
        logger.info(f"Inserted document: {len(request.text)} characters")
        
        return {
            "success": True,
            "message": "Document inserted successfully",
            "characters": len(request.text)
        }
        
    except Exception as e:
        logger.error(f"Insert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_rag(request: QueryRequest) -> Dict[str, Any]:
    """
    Query LightRAG.
    
    Args:
        request: QueryRequest with query text and mode
        
    Returns:
        Query results
    """
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="LightRAG not initialized")
    
    try:
        from lightrag import QueryParam
        
        # Run sync query in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: rag_instance.query(
                request.query,
                param=QueryParam(mode=request.mode, top_k=request.top_k)
            )
        )
        
        logger.info(f"Query executed: {request.query[:50]}... (mode: {request.mode})")
        
        return {
            "success": True,
            "query": request.query,
            "mode": request.mode,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def semantic_search(request: SearchRequest) -> Dict[str, Any]:
    """
    Perform semantic search.
    
    Args:
        request: SearchRequest with query and top_k
        
    Returns:
        Search results
    """
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="LightRAG not initialized")
    
    try:
        # Use hybrid mode for semantic search
        from lightrag import QueryParam
        
        # Run sync query in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: rag_instance.query(
                request.query,
                param=QueryParam(mode="hybrid", top_k=request.top_k)
            )
        )
        
        logger.info(f"Semantic search: {request.query[:50]}...")
        
        return {
            "success": True,
            "query": request.query,
            "top_k": request.top_k,
            "results": result
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Get LightRAG statistics.
    
    Returns:
        Statistics about the knowledge graph
    """
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="LightRAG not initialized")
    
    try:
        working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "/data/lightrag")
        
        # Basic stats
        stats = {
            "working_dir": working_dir,
            "initialized": True,
            "vector_store": os.getenv("VECTOR_STORE", "nano-vectordb"),
            "graph_store": os.getenv("GRAPH_STORE", "networkx"),
        }
        
        # Check for data files
        if os.path.exists(working_dir):
            files = os.listdir(working_dir)
            stats["data_files"] = len(files)
            stats["files"] = files
        
        return stats
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/document-status")
async def get_document_status() -> Dict[str, Any]:
    """
    Get detailed document ingestion status.
    
    Returns:
        Document processing status with counts and details
    """
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="LightRAG not initialized")
    
    try:
        working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "/data/lightrag")
        doc_status_file = os.path.join(working_dir, "kv_store_doc_status.json")
        
        if not os.path.exists(doc_status_file):
            return {
                "total_documents": 0,
                "completed": 0,
                "processing": 0,
                "pending": 0,
                "failed": 0,
                "documents": []
            }
        
        # Read document status
        import json
        with open(doc_status_file, 'r') as f:
            doc_status = json.load(f)
        
        # Count statuses
        # Note: LightRAG uses "processed" (not "completed") and "processing" statuses
        total = len(doc_status)
        completed = sum(1 for doc in doc_status.values() if doc.get("status") in ["completed", "processed"])
        processing = sum(1 for doc in doc_status.values() if doc.get("status") == "processing")
        failed = sum(1 for doc in doc_status.values() if doc.get("status") == "failed")
        pending = sum(1 for doc in doc_status.values() if doc.get("status") == "pending")
        
        # Get document details
        documents = []
        for doc_id, doc_info in doc_status.items():
            documents.append({
                "id": doc_id,
                "status": doc_info.get("status", "unknown"),
                "content_length": doc_info.get("content_length", 0),
                "chunks_count": doc_info.get("chunks_count", 0),
                "error": doc_info.get("error_msg", "")[:100] if doc_info.get("error_msg") else None,
                "created_at": doc_info.get("created_at"),
                "updated_at": doc_info.get("updated_at")
            })
        
        return {
            "total_documents": total,
            "completed": completed,
            "processing": processing,
            "pending": pending,
            "failed": failed,
            "documents": documents
        }
        
    except Exception as e:
        logger.error(f"Document status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/clear")
async def clear_data() -> Dict[str, Any]:
    """
    Clear all LightRAG data.
    
    Returns:
        Success status
    """
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="LightRAG not initialized")
    
    try:
        import shutil
        from pathlib import Path
        
        working_dir = os.getenv("LIGHTRAG_WORKING_DIR", "/data/lightrag")
        working_path = Path(working_dir)
        
        # Delete all data files in the working directory
        if working_path.exists():
            for item in working_path.iterdir():
                if item.is_file():
                    item.unlink()
                    logger.info(f"Deleted file: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"Deleted directory: {item.name}")
        
        # Reinitialize LightRAG with clean state
        await initialize_lightrag()
        
        logger.info("LightRAG data cleared successfully")
        
        return {
            "success": True,
            "message": "Data cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8001"))
    
    logger.info(f"Starting LightRAG API server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LIGHTRAG_LOG_LEVEL", "info").lower()
    )
