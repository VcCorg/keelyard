"""LightRAG client wrapper for DVA Agentic CLI."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed. LightRAG support will be limited.")

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("PyPDF2 not installed. PDF support will be limited.")


class LightRAGClient:
    """Client for LightRAG API operations."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 30.0
    ):
        """
        Initialize LightRAG client.
        
        Args:
            base_url: Base URL of LightRAG API
            timeout: Request timeout in seconds
        """
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for LightRAG support. "
                "Install it with: pip install httpx"
            )
        
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        logger.info(f"LightRAG client initialized: {base_url}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if LightRAG service is healthy.
        
        Returns:
            Health status
        """
        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise
    
    def insert(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Insert a document into LightRAG.
        
        Args:
            text: Document text to insert
            metadata: Optional metadata
            
        Returns:
            Insert result
        """
        try:
            payload = {"text": text}
            if metadata:
                payload["metadata"] = metadata
            
            response = self.client.post(
                f"{self.base_url}/insert",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Inserted document: {result.get('characters', 0)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            raise
    
    def _extract_text(self, file_path: Path) -> str:
        """
        Extract text from various file types.
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted text content
        """
        suffix = file_path.suffix.lower()
        
        # PDF files
        if suffix == '.pdf':
            if not PDF_SUPPORT:
                raise ImportError("PyPDF2 is required for PDF support. Install with: pip install PyPDF2")
            
            try:
                reader = PdfReader(str(file_path))
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text())
                return "\n".join(text_parts)
            except Exception as e:
                raise ValueError(f"Failed to extract text from PDF: {e}")
        
        # Text-based files
        elif suffix in ['.txt', '.md', '.csv', '.json', '.log', '.py', '.js', '.html', '.xml', '.yaml', '.yml']:
            try:
                return file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with different encoding
                try:
                    return file_path.read_text(encoding='latin-1')
                except Exception as e:
                    raise ValueError(f"Failed to read text file: {e}")
        
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def insert_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Insert a file into LightRAG.
        
        Args:
            file_path: Path to file to insert
            metadata: Optional metadata
            
        Returns:
            Insert result
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Extract text based on file type
            text = self._extract_text(path)
            
            # Add file metadata
            file_metadata = metadata or {}
            file_metadata.update({
                "filename": path.name,
                "filepath": str(path.absolute()),
                "file_type": path.suffix
            })
            
            return self.insert(text, file_metadata)
            
        except Exception as e:
            logger.error(f"Insert file failed: {e}")
            raise
    
    def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Query LightRAG.
        
        Args:
            query: Query text
            mode: Query mode (naive, local, global, hybrid)
            top_k: Number of results to return
            
        Returns:
            Query results
        """
        try:
            payload = {
                "query": query,
                "mode": mode,
                "top_k": top_k
            }
            
            response = self.client.post(
                f"{self.base_url}/query",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Query executed: {query[:50]}... (mode: {mode})")
            return result
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def search(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Perform semantic search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Search results
        """
        try:
            payload = {
                "query": query,
                "top_k": top_k
            }
            
            response = self.client.post(
                f"{self.base_url}/search",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Search executed: {query[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get LightRAG statistics.
        
        Returns:
            Statistics
        """
        try:
            response = self.client.get(f"{self.base_url}/stats")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Stats retrieval failed: {e}")
            raise
    
    def get_document_status(self) -> Dict[str, Any]:
        """
        Get detailed document ingestion status.
        
        Returns:
            Document status information including processing state
        """
        try:
            response = self.client.get(f"{self.base_url}/document-status")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Document status retrieval failed: {e}")
            # Return empty status if endpoint doesn't exist
            return {
                "total_documents": 0,
                "completed": 0,
                "processing": 0,
                "failed": 0,
                "documents": []
            }
    
    def clear(self) -> Dict[str, Any]:
        """
        Clear all LightRAG data.
        
        Returns:
            Clear result
        """
        try:
            response = self.client.delete(f"{self.base_url}/clear")
            response.raise_for_status()
            result = response.json()
            
            logger.info("LightRAG data cleared")
            return result
            
        except Exception as e:
            logger.error(f"Clear failed: {e}")
            raise
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def check_lightrag_availability(base_url: str = "http://localhost:8001") -> tuple[bool, str]:
    """
    Check if LightRAG service is available.
    
    Args:
        base_url: Base URL of LightRAG API
        
    Returns:
        (is_available, message) tuple
    """
    if not HTTPX_AVAILABLE:
        return False, "httpx not installed. Install with: pip install httpx"
    
    try:
        client = LightRAGClient(base_url=base_url, timeout=5.0)
        health = client.health_check()
        client.close()
        
        if health.get("status") == "healthy":
            return True, f"LightRAG is available at {base_url}"
        else:
            return False, f"LightRAG is not healthy: {health}"
            
    except Exception as e:
        return False, f"Cannot connect to LightRAG at {base_url}: {str(e)}"
