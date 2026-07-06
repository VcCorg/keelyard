#!/usr/bin/env python3
"""
Weaviate schema setup for KEEL Knowledge Graph.

This script creates the schema for code entities, documents, and relationships
in Weaviate for the KEEL knowledge graph infrastructure.
"""

import weaviate
import os
from dotenv import load_dotenv
from weaviate.classes.config import Configure, Property, DataType

# Load environment variables
load_dotenv()

# Weaviate configuration
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
WEAVIATE_PORT = os.getenv("WEAVIATE_PORT", "8080")
WEAVIATE_URL = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"

def create_schema():
    """Create Weaviate schema for KEEL KG."""
    
    # Connect using standard connection with gRPC on port 50051
    client = weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=int(WEAVIATE_PORT),
        grpc_port=50051,
        skip_init_checks=True
    )
    
    # Delete existing schema if it exists
    try:
        existing_classes = client.collections.list_all()
        for class_name in existing_classes:
            print(f"Deleting existing class: {class_name}")
            client.collections.delete(class_name)
    except Exception as e:
        print(f"No existing schema to delete: {e}")
    
    # Create classes
    try:
        client.collections.create(
            name="CodeEntity",
            description="Code entities (functions, classes, modules) from code repositories",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="name", data_type=DataType.TEXT, description="Name of the code entity"),
                Property(name="content", data_type=DataType.TEXT, description="Code content or documentation"),
                Property(name="entityType", data_type=DataType.TEXT, description="Type of entity (function, class, module, etc.)"),
                Property(name="filePath", data_type=DataType.TEXT, description="File path in the repository"),
                Property(name="language", data_type=DataType.TEXT, description="Programming language"),
                Property(name="domain", data_type=DataType.TEXT, description="Domain the code belongs to"),
                Property(name="repo", data_type=DataType.TEXT, description="Repository name"),
                Property(name="lineNumber", data_type=DataType.INT, description="Line number in the file")
            ]
        )
        print("✓ Created CodeEntity class")
        
        client.collections.create(
            name="Document",
            description="Business requirement documents and specifications",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="name", data_type=DataType.TEXT, description="Document name or title"),
                Property(name="content", data_type=DataType.TEXT, description="Document content"),
                Property(name="documentType", data_type=DataType.TEXT, description="Type of document (requirement, spec, etc.)"),
                Property(name="domain", data_type=DataType.TEXT, description="Domain the document belongs to"),
                Property(name="source", data_type=DataType.TEXT, description="Source of the document (Confluence, Jira, etc.)"),
                Property(name="url", data_type=DataType.TEXT, description="URL to the original document"),
                Property(name="author", data_type=DataType.TEXT, description="Document author"),
                Property(name="lastModified", data_type=DataType.DATE, description="Last modification date")
            ]
        )
        print("✓ Created Document class")
        
        client.collections.create(
            name="Relationship",
            description="Relationships between code entities and documents",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="relationshipType", data_type=DataType.TEXT, description="Type of relationship (implements, references, related_to, etc.)"),
                Property(name="confidence", data_type=DataType.NUMBER, description="Confidence score for the relationship"),
                Property(name="source", data_type=DataType.TEXT, description="Source of the relationship (LLM, vector_search, etc.)")
            ]
        )
        print("✓ Created Relationship class")
        
        print("\nSchema created successfully!")
        
        # Print schema
        schema = client.collections.list_all()
        print("\nCurrent schema:")
        for class_name in schema:
            print(f"  - {class_name}")
            
    except Exception as e:
        print(f"Error creating schema: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    print("Setting up Weaviate schema for KEEL KG...")
    print(f"Weaviate URL: {WEAVIATE_URL}")
    print()
    create_schema()
