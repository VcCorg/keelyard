"""Data ingestion for knowledge graph."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentic_cli.kg.config import KGConfig
from agentic_cli.kg.neo4j_client import Neo4jClient
from agentic_cli.kg.parsers import (
    parse_confluence,
    parse_csv,
    parse_directory,
    parse_git_repository,
    parse_json,
    parse_pdf,
    parse_text,
)


def detect_format(source: str) -> str:
    """Auto-detect source format from file extension or URL."""
    # Check if it's a directory
    if Path(source).is_dir():
        return "directory"
    
    source_lower = source.lower()
    
    # Check for Git repository URLs
    if (source_lower.startswith("https://") or 
        source_lower.startswith("http://") or 
        source_lower.startswith("git@") or 
        source_lower.startswith("git://") or
        source_lower.startswith("ssh://")):
        # Check if it's a Git URL (ends with .git or contains git hosting domains)
        if (source_lower.endswith(".git") or 
            "github.com" in source_lower or 
            "gitlab.com" in source_lower or 
            "bitbucket" in source_lower):
            return "git"
    
    if source_lower.endswith(".pdf"):
        return "pdf"
    elif source_lower.endswith(".txt") or source_lower.endswith(".md"):
        return "text"
    elif source_lower.endswith(".csv"):
        return "csv"
    elif source_lower.endswith(".json"):
        return "json"
    elif "confluence" in source_lower or "wiki" in source_lower:
        return "confluence"
    else:
        return "text"  # Default to text


def ingest_data(
    source: str,
    format: Optional[str] = None,
    persona: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    extract_entities: bool = True,
    build_relationships: bool = True,
    recursive: bool = True,
    detailed_analysis: bool = False,
) -> Dict[str, Any]:
    """
    Ingest data from various sources into the knowledge graph.
    
    Args:
        source: Path to file, directory, or URL
        format: Source format (auto-detected if None)
        persona: Persona tag (e.g., 'developer', 'business', None for auto-detect)
        metadata: Additional metadata (for Git: name, domain, purpose, branch, tag)
        extract_entities: Whether to extract entities using LLM
        build_relationships: Whether to build relationships between entities
        recursive: Whether to recursively process subdirectories (for directories)
        detailed_analysis: Whether to perform detailed code analysis for Git repos (default: False, uses gitingest only)
    
    Returns:
        Dictionary with ingestion statistics
    """
    # Detect format if not specified
    if format is None:
        format = detect_format(source)
    
    # Auto-detect persona from format if not specified
    if persona is None:
        if format == "git":
            persona = "developer"
        else:
            persona = "business"  # Default for documents
    
    # Parse the source
    if format == "directory":
        print(f"[INFO] Scanning directory: {source}")
        print(f"[INFO] Recursive: {recursive}")
        documents = parse_directory(source, recursive=recursive)
        print(f"[INFO] Found {len(documents)} documents")
    elif format == "git":
        # Parse Git repository with metadata
        git_metadata = metadata or {}
        branch = git_metadata.get("branch")
        tag = git_metadata.get("tag")
        repo_metadata = {
            "name": git_metadata.get("name", ""),
            "domain": git_metadata.get("domain", ""),
            "purpose": git_metadata.get("purpose", ""),
        }
        documents = parse_git_repository(
            repo_url=source,
            branch=branch,
            tag=tag,
            repo_metadata=repo_metadata,
            detailed_analysis=detailed_analysis
        )
    elif format == "pdf":
        documents = parse_pdf(source)
    elif format == "text":
        documents = parse_text(source)
    elif format == "csv":
        documents = parse_csv(source)
    elif format == "json":
        documents = parse_json(source)
    elif format == "confluence":
        documents = parse_confluence(source)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    # Extract entities and relationships if requested
    if extract_entities:
        from agentic_cli.kg.entity_extraction import extract_entities_from_documents
        
        entities, relationships = extract_entities_from_documents(
            documents,
            build_relationships=build_relationships,
        )
    else:
        # Use documents as-is
        entities = [
            {
                "id": f"doc_{i}",
                "type": "Document",
                "name": doc.get("title", f"Document {i}"),
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {}),
            }
            for i, doc in enumerate(documents)
        ]
        relationships = []
    
    # Store in Neo4j
    config = KGConfig.load()
    
    with Neo4jClient(config) as client:
        # Create nodes with persona tag
        for entity in entities:
            # Add persona to entity metadata
            entity_metadata = entity.get("metadata", {})
            if persona:
                entity_metadata["persona"] = persona
            
            # Use namespace for code entities (Option D: Hybrid approach)
            entity_type = entity.get("type", "Entity")
            if persona == "developer" and format == "git":
                # Add Code:: namespace for developer persona
                if not entity_type.startswith("Code::"):
                    entity_type = f"Code::{entity_type}"
            
            client.create_node(
                label=entity_type,
                properties={
                    "id": entity["id"],
                    "name": entity["name"],
                    "content": entity.get("content", ""),
                    "persona": persona,
                    "_source": "dva_kg",
                    "metadata": json.dumps(entity_metadata),
                },
            )
        
        # Create relationships
        for rel in relationships:
            client.create_relationship(
                from_node_id=rel["from"],
                to_node_id=rel["to"],
                relationship_type=rel["type"],
                properties=rel.get("properties", {}),
            )
    
    return {
        "entities_count": len(entities),
        "relationships_count": len(relationships),
        "source": source,
        "format": format,
    }
