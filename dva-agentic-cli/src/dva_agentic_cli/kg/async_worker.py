#!/usr/bin/env python3
"""
Background worker for async ingestion jobs.

This script runs as a detached subprocess to process ingestion jobs
independently of the CLI process.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
LOG_DIR = Path.home() / ".dva-agentic" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "async_ingestion.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_ingestion_job(job_id: str):
    """
    Run a single ingestion job.
    
    Args:
        job_id: Job ID to process
    """
    from dva_agentic_cli.kg.async_ingest import JobQueue, JobStatus
    from dva_agentic_cli.kg.config import KGConfig
    from dva_agentic_cli.kg.ingest import ingest_data
    from dva_agentic_cli.kg.lightrag_client import LightRAGClient
    from dva_agentic_cli.kg.parsers import (
        parse_directory,
        parse_pdf,
        parse_text,
        parse_csv,
        parse_json,
        parse_git_repository
    )
    from dva_agentic_cli.kg.ingest import detect_format
    
    logger.info(f"Worker started for job {job_id}")
    
    # Load job
    queue = JobQueue()
    job = queue.get_job(job_id)
    
    if not job:
        logger.error(f"Job {job_id} not found")
        return 1
    
    if job.status != JobStatus.PENDING:
        logger.warning(f"Job {job_id} is not pending (status: {job.status})")
        return 1
    
    # Update to running
    queue.update_job(
        job_id,
        status=JobStatus.RUNNING,
        started_at=datetime.utcnow()
    )
    
    logger.info(f"Processing job {job_id}")
    logger.info(f"  Source: {job.source}")
    logger.info(f"  Provider: {job.provider}")
    
    try:
        config = KGConfig.load()
        results = {}
        
        # Get job parameters from metadata
        extract_entities = job.metadata.get('extract_entities', True)
        build_relationships = job.metadata.get('build_relationships', True)
        recursive = job.metadata.get('recursive', True)
        
        # Ingest to Neo4j
        if job.provider in ["neo4j", "both"]:
            logger.info(f"[{job_id}] Starting Neo4j ingestion...")
            queue.update_job(
                job_id,
                progress={"stage": "neo4j", "status": "running"}
            )
            
            try:
                neo4j_result = ingest_data(
                    source=job.source,
                    format=job.format,
                    persona=job.metadata.get("persona"),
                    metadata=job.metadata,
                    extract_entities=extract_entities,
                    build_relationships=build_relationships,
                    recursive=recursive
                )
                results['neo4j'] = neo4j_result
                logger.info(f"[{job_id}] Neo4j ingestion completed: {neo4j_result}")
            except Exception as e:
                logger.error(f"[{job_id}] Neo4j ingestion failed: {e}", exc_info=True)
                raise
        
        # Ingest to LightRAG
        if job.provider in ["lightrag", "both"]:
            logger.info(f"[{job_id}] Starting LightRAG ingestion...")
            queue.update_job(
                job_id,
                progress={"stage": "lightrag", "status": "running"}
            )
            
            try:
                # Detect format
                format = job.format or detect_format(job.source)
                
                # Parse documents
                if format == "directory":
                    documents = parse_directory(job.source, recursive=recursive)
                elif format == "git":
                    git_metadata = job.metadata or {}
                    documents = parse_git_repository(
                        repo_url=job.source,
                        branch=git_metadata.get("branch"),
                        tag=git_metadata.get("tag"),
                        repo_metadata={
                            "name": git_metadata.get("name", ""),
                            "domain": git_metadata.get("domain", ""),
                            "purpose": git_metadata.get("purpose", ""),
                        }
                    )
                elif format == "pdf":
                    documents = parse_pdf(job.source)
                elif format == "text":
                    documents = parse_text(job.source)
                elif format == "csv":
                    documents = parse_csv(job.source)
                elif format == "json":
                    documents = parse_json(job.source)
                else:
                    raise ValueError(f"Unsupported format: {format}")
                
                logger.info(f"[{job_id}] Parsed {len(documents)} documents")
                
                # Insert into LightRAG with rate limiting
                import time
                client = LightRAGClient(base_url=config.lightrag_url, timeout=600.0)
                inserted_count = 0
                failed_count = 0
                batch_size = 10  # Process in small batches
                retry_delay = 2.0  # Delay between batches to avoid overwhelming server
                
                for i, doc in enumerate(documents):
                    try:
                        text = f"{doc.get('title', '')}\n\n{doc.get('content', '')}"
                        doc_metadata = doc.get('metadata', {})
                        
                        if job.metadata:
                            doc_metadata.update(job.metadata)
                        
                        client.insert(text=text, metadata=doc_metadata)
                        inserted_count += 1
                        
                        # Add delay every batch_size documents to avoid event loop conflicts
                        if (i + 1) % batch_size == 0:
                            logger.info(f"[{job_id}] Inserted {i + 1}/{len(documents)} documents")
                            time.sleep(retry_delay)  # Give LightRAG time to process
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"[{job_id}] Failed to insert document {i}: {e}")
                        # Add small delay after failures to let server recover
                        if "event loop" in str(e).lower() or "500" in str(e):
                            time.sleep(1.0)
                
                client.close()
                
                results['lightrag'] = {
                    "documents_count": len(documents),
                    "inserted_count": inserted_count,
                    "source": job.source,
                    "format": format
                }
                logger.info(f"[{job_id}] LightRAG ingestion completed: {results['lightrag']}")
            except Exception as e:
                logger.error(f"[{job_id}] LightRAG ingestion failed: {e}", exc_info=True)
                raise
        
        # Mark as completed
        queue.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            result=results,
            progress={"stage": "completed", "status": "success"}
        )
        
        logger.info(f"[{job_id}] Job completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"[{job_id}] Job failed: {e}", exc_info=True)
        queue.update_job(
            job_id,
            status=JobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error=str(e),
            progress={"stage": "failed", "error": str(e)}
        )
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: async_worker.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    sys.exit(run_ingestion_job(job_id))
