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
LOG_DIR = Path.home() / ".agent-cli-agentic" / "logs"
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
    from agentic_cli.kg.async_ingest import JobQueue, JobStatus
    from agentic_cli.kg.config import KGConfig
    from agentic_cli.kg.ingest import ingest_data
    from agentic_cli.kg.lightrag_client import LightRAGClient
    from agentic_cli.kg.parsers import (
        parse_directory,
        parse_pdf,
        parse_text,
        parse_csv,
        parse_json,
        parse_git_repository
    )
    from agentic_cli.kg.ingest import detect_format
    
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
                if format == "confluence" and job.source.startswith("domain:"):
                    # Domain mode: fetch tracked docs
                    from agentic_cli.tracker import get_domain, get_domain_docs
                    from agentic_cli.kg.parsers import parse_confluence_tree
                    
                    domain_slug = job.source.replace("domain:", "")
                    logger.info(f"[{job_id}] Fetching tracked docs for domain: {domain_slug}")
                    
                    d = get_domain(domain_slug)
                    if not d:
                        raise ValueError(f"Domain '{domain_slug}' not found")
                    
                    domain_product = d.get("product", "")
                    docs = get_domain_docs(domain_slug)
                    
                    # Limit to top N pages if --top was specified
                    top = job.metadata.get("top")
                    if top:
                        docs = docs[:top]
                        logger.info(f"[{job_id}] Limiting to top {top} pages for testing/validation")
                    
                    if not docs:
                        logger.warning(f"[{job_id}] No tracked docs for domain '{domain_slug}'")
                        documents = []
                    else:
                        logger.info(f"[{job_id}] Found {len(docs)} tracked docs")
                        all_documents = []
                        
                        try:
                            conf_base = config.confluence_url or ""
                        except Exception:
                            conf_base = ""
                        
                        depth = job.metadata.get("depth", 3)
                        
                        for doc_rec in docs:
                            page_id = doc_rec.get("source_page_id")
                            title = doc_rec.get("title", page_id)
                            page_url = f"{conf_base}/pages/{page_id}"
                            try:
                                # Use MCP mode to bypass KG config check, include attachments by default
                                fetched = parse_confluence_tree(page_url, include_children=True, max_depth=depth, use_mcp=True, include_attachments=True)
                                all_documents.extend(fetched)
                                child_count = len(fetched) - 1 if len(fetched) > 1 else 0
                                suffix = f" (+{child_count} children)" if child_count else ""
                                logger.info(f"[{job_id}]   Fetched: {title}{suffix}")
                            except Exception as e:
                                logger.warning(f"[{job_id}]   Failed to fetch {title}: {e}")
                        
                        # Limit total documents if --top was specified
                        top = job.metadata.get("top")
                        if top and len(all_documents) > top:
                            all_documents = all_documents[:top]
                            logger.info(f"[{job_id}] Limiting to top {top} documents for testing/validation")
                        
                        # Deduplicate by page_id
                        seen_ids = set()
                        documents = []
                        for doc in all_documents:
                            pid = doc["metadata"].get("page_id", "")
                            if pid and pid in seen_ids:
                                continue
                            if pid:
                                seen_ids.add(pid)
                            documents.append(doc)
                        
                        # Add domain metadata to each document
                        for doc in documents:
                            doc_metadata = doc.get("metadata", {})
                            doc_metadata["domain"] = domain_slug
                            doc_metadata["product"] = domain_product
                            doc["metadata"] = doc_metadata
                
                elif format == "directory":
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
