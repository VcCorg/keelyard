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


def extract_freq_id(doc: Dict[str, Any]) -> Optional[str]:
    """
    Extract FREQ (Functional Requirement) ID from a document.
    
    FREQ IDs are typically in formats like CWOW-XXXXXX, CWOW-XXXXXX Manage X, etc.
    
    Args:
        doc: Document dictionary with metadata
        
    Returns:
        FREQ ID if found, None otherwise
    """
    metadata = doc.get("metadata", {})
    title = metadata.get("title", "")
    source = metadata.get("source", "")
    
    # Try to extract from title first (e.g., "CWOW-278922 Manage HDF Treatment Standards")
    import re
    freq_pattern = r'(CWOW-\d+)'
    match = re.search(freq_pattern, title)
    if match:
        return match.group(1)
    
    # Try to extract from source URL
    match = re.search(freq_pattern, source)
    if match:
        return match.group(1)
    
    return None


def ingest_data(
    source: str,
    format: Optional[str] = None,
    persona: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    extract_entities: bool = True,
    build_relationships: bool = True,
    recursive: bool = True,
    detailed_analysis: bool = False,
    dedup_freq: bool = True,
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
        dedup_freq: Whether to deduplicate FREQ documents (latest takes precedence)
    
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
        documents = parse_text(source, metadata=metadata)
    elif format == "csv":
        documents = parse_csv(source)
    elif format == "json":
        documents = parse_json(source)
    elif format == "confluence":
        # Use tree parser with MCP to handle cross-space links and attachments
        from agentic_cli.kg.parsers import parse_confluence_tree
        documents = parse_confluence_tree(source, include_children=True, max_depth=3, use_mcp=True, include_attachments=True)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    # Deduplicate FREQ documents if requested
    if dedup_freq:
        freq_map = {}  # Maps FREQ ID to (document, version)
        deduped_documents = []
        
        for doc in documents:
            freq_id = extract_freq_id(doc)
            if freq_id:
                # Extract version from metadata if available
                metadata = doc.get("metadata", {})
                version = metadata.get("version", 0)
                
                if freq_id not in freq_map or version > freq_map[freq_id][1]:
                    freq_map[freq_id] = (doc, version)
                # Skip duplicate FREQ with lower version
            else:
                # Keep non-FREQ documents
                deduped_documents.append(doc)
        
        # Add the latest version of each FREQ
        for freq_id, (doc, version) in freq_map.items():
            deduped_documents.append(doc)
        
        documents = deduped_documents
        
        if len(freq_map) > 0:
            print(f"[INFO] Deduplicated {len(freq_map)} FREQ(s), kept latest versions")
    
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
            
            # Skip Release entities - they are created directly from domain_docs tracking
            # to avoid merge conflicts and ensure correct metadata
            if entity_type == "Release":
                continue
            
            # Flatten attachment-specific metadata to top-level properties
            node_properties = {
                "id": entity["id"],
                "name": entity["name"],
                "content": entity.get("content", ""),
                "persona": persona,
                "_source": "dva_kg",
                "metadata": json.dumps(entity_metadata),
            }
            
            # Extract attachment-specific metadata to top-level
            if "attachment_filename" in entity_metadata:
                node_properties["attachment_filename"] = entity_metadata["attachment_filename"]
            if "attachment_page_id" in entity_metadata:
                node_properties["attachment_page_id"] = entity_metadata["attachment_page_id"]
            if "parent_page_title" in entity_metadata:
                node_properties["parent_page_title"] = entity_metadata["parent_page_title"]
            if "type" in entity_metadata:
                node_properties["document_type"] = entity_metadata["type"]
            if "source" in entity_metadata:
                node_properties["source"] = entity_metadata["source"]
            if "page_id" in entity_metadata:
                node_properties["page_id"] = entity_metadata["page_id"]
            if "domain" in entity_metadata:
                node_properties["domain"] = entity_metadata["domain"]
            if "product" in entity_metadata:
                node_properties["product"] = entity_metadata["product"]
            
            client.create_node(
                label=entity_type,
                properties=node_properties,
            )
        
        # Create Release-Document relationships for Confluence attachments and child pages
        # Link Document nodes (from attachments/child pages) to their parent Release node
        for entity in entities:
            entity_metadata = entity.get("metadata", {})
            attachment_page_id = entity_metadata.get("attachment_page_id")
            page_id = entity_metadata.get("page_id")
            parent_page_id = entity_metadata.get("parent_page_id")
            
            # Use parent_page_id for attachments (points to release page), or attachment_page_id as fallback
            # parent_page_id is set correctly for attachments (points to release page)
            print(f"[DEBUG] Entity metadata: parent_page_id={parent_page_id}, attachment_page_id={attachment_page_id}")
            release_page_id = parent_page_id or attachment_page_id
            print(f"[DEBUG] Using release_page_id={release_page_id}")
            
            if release_page_id:
                # Find the parent Release node by page_id
                # The Release node should have page_id in its metadata
                release_nodes = client.find_nodes(
                    label="Release",
                    properties={"page_id": str(release_page_id)}
                )
                
                if release_nodes:
                    release_node = release_nodes[0]
                    # Create relationship: Release -> HAS_DOCUMENT -> Document
                    client.create_relationship(
                        from_node_id=release_node["id"],
                        to_node_id=entity["id"],
                        relationship_type="HAS_DOCUMENT",
                        properties={"source": "confluence"}
                    )
                    print(f"[DEBUG] Created HAS_DOCUMENT relationship: Release {release_node['name']} -> {entity['name']}")
                else:
                    print(f"[DEBUG] No Release node found with page_id={release_page_id}")
        
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
