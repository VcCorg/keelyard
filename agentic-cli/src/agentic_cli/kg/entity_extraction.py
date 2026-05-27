"""Entity extraction using Vertex AI."""

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from agentic_cli.kg.config import KGConfig
from agentic_cli.config import CLI_NAME

# Cache for Vertex AI initialization
_vertexai_initialized = False


def _retry_with_backoff(func, max_retries=3, initial_delay=1.0):
    """
    Retry function with exponential backoff for rate limit errors.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
    
    Returns:
        Function result
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Resource exhausted" in error_str:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"[DEBUG] Rate limited, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"[DEBUG] Max retries exceeded for rate limit error")
                    raise
            else:
                raise
    return None


def extract_entities_from_documents(
    documents: List[Dict[str, Any]],
    build_relationships: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract entities and relationships from documents using Vertex AI.
    
    Args:
        documents: List of document dictionaries
        build_relationships: Whether to extract relationships
    
    Returns:
        Tuple of (entities, relationships)
    """
    config = KGConfig.load()
    
    if not config.is_vertex_ai_configured():
        raise ValueError(
            "Vertex AI is not configured. Run f'{CLI_NAME} init vertex-ai' first.\n"
            f"Current config: project_id={config.google_project_id}, "
            f"location={config.google_location}"
        )
    
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
    except ImportError:
        raise ImportError(
            "Vertex AI packages not installed. Install with: pip install google-cloud-aiplatform"
        )
    
    # Initialize Vertex AI (cached)
    global _vertexai_initialized
    if not _vertexai_initialized:
        try:
            print(f"[DEBUG] Initializing Vertex AI with project={config.google_project_id}, location={config.google_location}")
            vertexai.init(
                project=config.google_project_id,
                location=config.google_location,
            )
            _vertexai_initialized = True
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Vertex AI: {str(e)}\n"
                "Make sure you're authenticated with Google Cloud:\n"
                "  gcloud auth application-default login\n"
                "Or set GOOGLE_APPLICATION_CREDENTIALS environment variable."
            )
    
    # Use gemini-2.5-flash-lite model
    model_name = "gemini-2.5-flash-lite"
    print(f"[DEBUG] Using model: {model_name}")
    model = GenerativeModel(model_name)
    
    all_entities = []
    all_relationships = []
    
    for doc in documents:
        content = doc.get("content", "")
        
        if not content.strip():
            continue
        
        # Extract entities
        entities = extract_entities_from_text(model, content, doc)
        all_entities.extend(entities)
        
        # Extract relationships if requested
        if build_relationships and len(entities) > 1:
            relationships = extract_relationships_from_text(
                model, content, entities
            )
            all_relationships.extend(relationships)
    
    return all_entities, all_relationships


def extract_entities_from_text(
    model: Any,
    text: str,
    document: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract entities from text using Vertex AI.
    
    Args:
        model: Vertex AI model
        text: Text content
        document: Source document metadata
    
    Returns:
        List of entity dictionaries
    """
    prompt = f"""
Extract entities from the following text. For each entity, identify:
- name: The entity name
- type: Entity type (Patient, Facility, Provider, Assessment, PlanOfCare, Medication, CarePlan, Encounter etc.,)
- description: Brief description of the entity

Return the result as a JSON array of objects with these fields.

Text:
{text[:3000]}  # Limit to first 3000 chars to avoid token limits

Return ONLY the JSON array, no other text.
"""
    
    try:
        def _call_model():
            return model.generate_content(prompt)
        
        response = _retry_with_backoff(_call_model)
        result_text = response.text.strip()
        
        # Try to parse JSON
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        entities_data = json.loads(result_text)
        
        # Convert to our entity format
        entities = []
        for entity_data in entities_data:
            # Preserve original document metadata
            doc_metadata = document.get("metadata", {})
            entity_metadata = {
                "source": doc_metadata.get("source", ""),
                "document_title": doc_metadata.get("document_title", document.get("title", "")),
                "extraction_method": "vertex-ai",
            }
            
            # Preserve domain, product, and persona if present
            if "domain" in doc_metadata:
                entity_metadata["domain"] = doc_metadata["domain"]
            if "product" in doc_metadata:
                entity_metadata["product"] = doc_metadata["product"]
            if "persona" in doc_metadata:
                entity_metadata["persona"] = doc_metadata["persona"]
            
            # Preserve attachment-specific metadata if present
            if "attachment_filename" in doc_metadata:
                entity_metadata["attachment_filename"] = doc_metadata["attachment_filename"]
            if "attachment_page_id" in doc_metadata:
                entity_metadata["attachment_page_id"] = doc_metadata["attachment_page_id"]
            if "parent_page_id" in doc_metadata:
                entity_metadata["parent_page_id"] = doc_metadata["parent_page_id"]
            if "parent_page_title" in doc_metadata:
                entity_metadata["parent_page_title"] = doc_metadata["parent_page_title"]
            if "page_id" in doc_metadata:
                entity_metadata["page_id"] = doc_metadata["page_id"]
            
            entity = {
                "id": str(uuid.uuid4()),
                "name": entity_data.get("name", ""),
                "type": entity_data.get("type", "KGEntity"),
                "content": entity_data.get("description", ""),
                "metadata": entity_metadata,
            }
            entities.append(entity)
        
        return entities
    
    except Exception as e:
        print(f"Error extracting entities: {e}")
        return []


def extract_relationships_from_text(
    model: Any,
    text: str,
    entities: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Extract relationships between entities using Vertex AI.
    
    Args:
        model: Vertex AI model
        text: Text content
        entities: List of extracted entities
    
    Returns:
        List of relationship dictionaries
    """
    if len(entities) < 2:
        return []
    
    # Create entity reference for the prompt
    entity_list = "\n".join([
        f"- {e['name']} (ID: {e['id']}, Type: {e['type']})"
        for e in entities
    ])
    
    prompt = f"""
Given the following text and entities, identify relationships between the entities.

Entities:
{entity_list}

Text:
{text[:2000]}

For each relationship, provide:
- from: The ID of the source entity
- to: The ID of the target entity
- type: The relationship type (e.g., WORKS_FOR, LOCATED_IN, RELATED_TO, PART_OF, etc.)
- description: Brief description of the relationship

Return the result as a JSON array of objects with these fields.
Return ONLY the JSON array, no other text.
"""
    
    try:
        def _call_model():
            return model.generate_content(prompt)
        
        response = _retry_with_backoff(_call_model)
        result_text = response.text.strip()
        
        # Try to parse JSON
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        relationships_data = json.loads(result_text)
        
        # Convert to our relationship format
        relationships = []
        for rel_data in relationships_data:
            relationship = {
                "from": rel_data.get("from", ""),
                "to": rel_data.get("to", ""),
                "type": rel_data.get("type", "RELATED_TO"),
                "properties": {
                    "description": rel_data.get("description", ""),
                },
            }
            relationships.append(relationship)
        
        return relationships
    
    except Exception as e:
        print(f"Error extracting relationships: {e}")
        return []


def generate_embeddings(texts: List[str], config: Optional[KGConfig] = None) -> List[List[float]]:
    """
    Generate embeddings for texts using Vertex AI.
    
    Args:
        texts: List of text strings
        config: KG configuration (loads default if None)
    
    Returns:
        List of embedding vectors
    """
    if config is None:
        config = KGConfig.load()
    
    if not config.is_vertex_ai_configured():
        raise ValueError(
            "Vertex AI is not configured. Run f'{CLI_NAME} init vertex-ai' first."
        )
    
    try:
        import vertexai
        from vertexai.language_models import TextEmbeddingModel
    except ImportError:
        raise ImportError(
            "Vertex AI packages not installed. Install with: pip install google-cloud-aiplatform"
        )
    
    # Initialize Vertex AI (cached)
    global _vertexai_initialized
    if not _vertexai_initialized:
        vertexai.init(
            project=config.google_project_id,
            location=config.google_location,
        )
        _vertexai_initialized = True
    
    model = TextEmbeddingModel.from_pretrained(config.vertex_ai_model)
    
    # Generate embeddings in batches
    embeddings = []
    batch_size = 5  # Vertex AI has rate limits
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = model.get_embeddings(batch)
        embeddings.extend([emb.values for emb in batch_embeddings])
    
    return embeddings
