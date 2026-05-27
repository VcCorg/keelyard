"""Asynchronous data ingestion for knowledge graph with background processing."""

import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)

# Setup file logging for background jobs
LOG_DIR = Path.home() / ".agent-cli-agentic" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create file handler for job logs
job_log_file = LOG_DIR / "async_ingestion.log"
file_handler = logging.FileHandler(job_log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)


class JobStatus(str, Enum):
    """Ingestion job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestionJob(BaseModel):
    """Ingestion job model (tracks both sync and async operations)."""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    source_type: str  # 'path', 'data_source', 'git'
    format: Optional[str] = None
    provider: str  # 'neo4j', 'lightrag', 'both'
    status: JobStatus = Field(default=JobStatus.PENDING, description="Job status")
    is_async: bool = Field(default=True, description="True for async, False for sync operations")
    workspace: Optional[str] = Field(None, description="Target workspace (LightRAG only)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Custom JSON serializer for datetime and JobStatus
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        return json_schema


class JobQueue:
    """Job queue manager for tracking ingestion jobs."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize job queue.
        
        Args:
            storage_path: Path to store job data (default: ~/.agent-cli-agentic/jobs/)
        """
        if storage_path is None:
            storage_path = Path.home() / ".agent-cli-agentic" / "jobs"
        
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, IngestionJob] = {}
        self._load_jobs()
    
    def _load_jobs(self):
        """Load existing jobs from storage."""
        for job_file in self.storage_path.glob("*.json"):
            try:
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    job = IngestionJob(**job_data)
                    self.jobs[job.job_id] = job
            except Exception as e:
                logger.error(f"Failed to load job {job_file}: {e}")
    
    def _save_job(self, job: IngestionJob):
        """Save job to storage."""
        job_file = self.storage_path / f"{job.job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job.dict(), f, indent=2, default=str)
    
    def create_job(
        self,
        source: str,
        source_type: str,
        format: Optional[str] = None,
        provider: str = "lightrag",
        is_async: bool = True,
        workspace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionJob:
        """Create a new ingestion job (sync or async)."""
        job = IngestionJob(
            source=source,
            source_type=source_type,
            format=format,
            provider=provider,
            is_async=is_async,
            workspace=workspace,
            metadata=metadata or {}
        )
        self.jobs[job.job_id] = job
        self._save_job(job)
        return job
    
    def update_job(self, job_id: str, **kwargs):
        """Update job status and properties."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        self._save_job(job)
    
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        """Get job by ID (supports partial ID matching)."""
        # Try exact match first
        if job_id in self.jobs:
            return self.jobs[job_id]
        
        # Try partial match (prefix)
        matches = [j for jid, j in self.jobs.items() if jid.startswith(job_id)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise ValueError(f"Ambiguous job ID '{job_id}' matches multiple jobs")
        
        return None
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50
    ) -> List[IngestionJob]:
        """List jobs with optional status filter."""
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[:limit]
    
    def delete_job(self, job_id: str):
        """Delete a job."""
        if job_id in self.jobs:
            job_file = self.storage_path / f"{job_id}.json"
            if job_file.exists():
                job_file.unlink()
            del self.jobs[job_id]
    
    def cleanup_old_jobs(self, days: int = 30):
        """Clean up jobs older than specified days."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        for job_id, job in list(self.jobs.items()):
            if job.created_at < cutoff and job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                self.delete_job(job_id)


class AsyncIngestionManager:
    """Manager for asynchronous ingestion operations."""
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize async ingestion manager.
        
        Args:
            max_workers: Maximum number of parallel ingestion workers
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.queue = JobQueue()
    
    def submit_ingestion(
        self,
        source: str,
        source_type: str = "path",
        format: Optional[str] = None,
        provider: str = "lightrag",
        extract_entities: bool = True,
        build_relationships: bool = True,
        recursive: bool = True,
        detailed_analysis: bool = False,
        workspace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionJob:
        """
        Submit an ingestion job for background processing.
        
        Args:
            source: Data source path or name
            source_type: Type of source ('path', 'data_source', 'git')
            format: Source format (auto-detected if None)
            provider: Target provider ('neo4j', 'lightrag', 'both')
            extract_entities: Whether to extract entities
            build_relationships: Whether to build relationships
            recursive: Whether to process directories recursively
            metadata: Additional metadata
        
        Returns:
            IngestionJob object with job_id for tracking
        """
        import subprocess
        import sys
        
        # Add job parameters to metadata
        if metadata is None:
            metadata = {}
        metadata['extract_entities'] = extract_entities
        metadata['build_relationships'] = build_relationships
        metadata['recursive'] = recursive
        metadata['detailed_analysis'] = detailed_analysis
        
        # Create job (async by default)
        job = self.queue.create_job(
            source=source,
            source_type=source_type,
            format=format,
            provider=provider,
            is_async=True,
            workspace=workspace,
            metadata=metadata
        )
        
        # Start worker as detached subprocess
        worker_script = Path(__file__).parent / "async_worker.py"
        
        # Use nohup and redirect output to log file
        log_file = Path.home() / ".agent-cli-agentic" / "logs" / f"job_{job.job_id}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Start subprocess detached from parent
        process = subprocess.Popen(
            [sys.executable, str(worker_script), job.job_id],
            stdout=open(log_file, 'w'),
            stderr=subprocess.STDOUT,
            start_new_session=True,  # Detach from parent process
            cwd=str(Path.home())  # Run from home directory
        )
        
        # Store process ID in metadata
        job.metadata['worker_pid'] = process.pid
        job.metadata['log_file'] = str(log_file)
        self.queue._save_job(job)
        
        logger.info(f"Submitted ingestion job {job.job_id} for {source} (PID: {process.pid})")
        logger.info(f"Worker log: {log_file}")
        
        return job
    
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        """Get a job by ID."""
        return self.queue.get_job(job_id)
    
    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 20) -> List[IngestionJob]:
        """List jobs with optional status filter."""
        return self.queue.list_jobs(status=status, limit=limit)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        return self.queue.cancel_job(job_id)
    
    def _run_ingestion(
        self,
        job_id: str,
        source: str,
        format: Optional[str],
        provider: str,
        extract_entities: bool,
        build_relationships: bool,
        recursive: bool,
        metadata: Optional[Dict[str, Any]]
    ):
        """Run ingestion in background thread."""
        from agentic_cli.kg.config import KGConfig
        from agentic_cli.kg.ingest import ingest_data
        from agentic_cli.kg.lightrag_client import LightRAGClient
        
        logger.info(f"[{job_id}] Starting ingestion job")
        logger.info(f"[{job_id}] Source: {source}")
        logger.info(f"[{job_id}] Provider: {provider}")
        logger.info(f"[{job_id}] Extract entities: {extract_entities}")
        logger.info(f"[{job_id}] Build relationships: {build_relationships}")
        
        # Update job status
        self.queue.update_job(
            job_id,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        try:
            config = KGConfig.load()
            results = {}
            
            # Ingest to Neo4j
            if provider in ["neo4j", "both"]:
                logger.info(f"[{job_id}] Starting Neo4j ingestion...")
                self.queue.update_job(
                    job_id,
                    progress={"stage": "neo4j", "status": "running"}
                )
                
                # Use existing ingest_data function for Neo4j
                logger.info(f"[{job_id}] Calling ingest_data for Neo4j...")
                neo4j_result = ingest_data(
                    source=source,
                    format=format,
                    persona=metadata.get("persona") if metadata else None,
                    metadata=metadata,
                    extract_entities=extract_entities,
                    build_relationships=build_relationships,
                    recursive=recursive
                )
                results['neo4j'] = neo4j_result
                logger.info(f"[{job_id}] Neo4j ingestion completed: {neo4j_result}")
            
            # Ingest to LightRAG
            if provider in ["lightrag", "both"]:
                logger.info(f"[{job_id}] Ingesting to LightRAG...")
                self.queue.update_job(
                    job_id,
                    progress={"stage": "lightrag", "status": "running"}
                )
                
                lightrag_result = self._ingest_to_lightrag(
                    source=source,
                    format=format,
                    recursive=recursive,
                    metadata=metadata,
                    config=config
                )
                results['lightrag'] = lightrag_result
                logger.info(f"[{job_id}] LightRAG ingestion completed")
            
            # Update job as completed
            self.queue.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                result=results,
                progress={"stage": "completed", "status": "success"}
            )
            
            logger.info(f"[{job_id}] Ingestion completed successfully")
            
        except Exception as e:
            logger.error(f"[{job_id}] Ingestion failed: {e}", exc_info=True)
            self.queue.update_job(
                job_id,
                status=JobStatus.FAILED,
                completed_at=datetime.utcnow(),
                error=str(e),
                progress={"stage": "failed", "error": str(e)}
            )
    
    def _ingest_to_lightrag(
        self,
        source: str,
        format: Optional[str],
        recursive: bool,
        metadata: Optional[Dict[str, Any]],
        config
    ) -> Dict[str, Any]:
        """Ingest documents to LightRAG."""
        from agentic_cli.kg.parsers import (
            parse_directory,
            parse_pdf,
            parse_text,
            parse_csv,
            parse_json,
            parse_git_repository
        )
        from agentic_cli.kg.ingest import detect_format
        
        # Detect format if not specified
        if format is None:
            format = detect_format(source)
        
        # Parse documents
        if format == "directory":
            documents = parse_directory(source, recursive=recursive)
        elif format == "git":
            git_metadata = metadata or {}
            documents = parse_git_repository(
                repo_url=source,
                branch=git_metadata.get("branch"),
                tag=git_metadata.get("tag"),
                repo_metadata={
                    "name": git_metadata.get("name", ""),
                    "domain": git_metadata.get("domain", ""),
                    "purpose": git_metadata.get("purpose", ""),
                }
            )
        elif format == "pdf":
            documents = parse_pdf(source)
        elif format == "text":
            documents = parse_text(source)
        elif format == "csv":
            documents = parse_csv(source)
        elif format == "json":
            documents = parse_json(source)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Insert documents into LightRAG
        client = LightRAGClient(base_url=config.lightrag_url)
        inserted_count = 0
        
        for doc in documents:
            try:
                # Combine title and content
                text = f"{doc.get('title', '')}\n\n{doc.get('content', '')}"
                doc_metadata = doc.get('metadata', {})
                
                # Add source metadata
                if metadata:
                    doc_metadata.update(metadata)
                
                client.insert(text=text, metadata=doc_metadata)
                inserted_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert document: {e}")
        
        client.close()
        
        return {
            "documents_count": len(documents),
            "inserted_count": inserted_count,
            "source": source,
            "format": format
        }
    
    def get_job_status(self, job_id: str) -> Optional[IngestionJob]:
        """Get status of an ingestion job."""
        return self.queue.get_job(job_id)
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50
    ) -> List[IngestionJob]:
        """List ingestion jobs."""
        return self.queue.list_jobs(status=status, limit=limit)
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.
        
        Note: Running jobs cannot be immediately cancelled,
        but will be marked for cancellation.
        """
        job = self.queue.get_job(job_id)
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        self.queue.update_job(job_id, status=JobStatus.CANCELLED)
        return True
    
    def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> IngestionJob:
        """
        Wait for a job to complete.
        
        Args:
            job_id: Job ID to wait for
            timeout: Maximum time to wait in seconds (None = wait forever)
        
        Returns:
            Completed IngestionJob
        """
        import time
        start_time = time.time()
        
        while True:
            job = self.queue.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return job
            
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
            
            time.sleep(1)
    
    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)


# Global instance
_manager: Optional[AsyncIngestionManager] = None


def get_manager(max_workers: int = 4) -> AsyncIngestionManager:
    """Get or create global async ingestion manager."""
    global _manager
    if _manager is None:
        _manager = AsyncIngestionManager(max_workers=max_workers)
    return _manager
