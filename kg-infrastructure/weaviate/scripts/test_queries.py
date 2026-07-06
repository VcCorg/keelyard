#!/usr/bin/env python3
"""
Test queries for Weaviate KEEL KG infrastructure validation.

This script runs test queries to validate vector search and graph
relationship functionality in Weaviate.
"""

import weaviate
import os
from dotenv import load_dotenv
import numpy as np
import weaviate.classes as wvc

# Load environment variables
load_dotenv()

# Weaviate configuration
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
WEAVIATE_PORT = os.getenv("WEAVIATE_PORT", "8080")
WEAVIATE_URL = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"

def test_vector_search(client):
    """Test vector search (semantic search)."""
    
    print("=" * 60)
    print("TEST 1: Vector Search (Semantic Search)")
    print("=" * 60)
    
    queries = [
        "medication dosage calculation",
        "patient data model",
        "bed management",
        "validation rules"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        try:
            # Generate a query vector (in production, this would come from Vertex AI)
            query_vector = np.random.rand(768).tolist()
            
            # Search in CodeEntity class
            code_collection = client.collections.get("CodeEntity")
            code_results = code_collection.query.near_vector(
                near_vector=query_vector,
                limit=3,
                return_properties=["name", "content", "entityType"]
            )
            
            if code_results.objects:
                print("Code Entities:")
                for result in code_results.objects:
                    print(f"  - {result.properties['name']} ({result.properties['entityType']})")
                    if result.metadata and result.metadata.distance is not None:
                        print(f"    Distance: {result.metadata.distance:.2f}")
            else:
                print("  No code entities found")
            
            # Search in Document class
            doc_collection = client.collections.get("Document")
            doc_results = doc_collection.query.near_vector(
                near_vector=query_vector,
                limit=3,
                return_properties=["name", "content", "documentType"]
            )
            
            if doc_results.objects:
                print("Documents:")
                for result in doc_results.objects:
                    print(f"  - {result.properties['name']} ({result.properties['documentType']})")
                    if result.metadata and result.metadata.distance is not None:
                        print(f"    Distance: {result.metadata.distance:.2f}")
            else:
                print("  No documents found")
                
        except Exception as e:
            print(f"Error: {e}")

def test_property_filters(client):
    """Test property filters (exact match)."""
    
    print("\n" + "=" * 60)
    print("TEST 2: Property Filters (Exact Match)")
    print("=" * 60)
    
    filters = [
        ("entityType", "function", "CodeEntity"),
        ("documentType", "requirement", "Document"),
        ("language", "python", "CodeEntity")
    ]
    
    for prop, value, class_name in filters:
        print(f"\nFilter: {prop} = '{value}' in {class_name}")
        print("-" * 40)
        
        try:
            collection = client.collections.get(class_name)
            results = collection.query.fetch_objects(
                filters=wvc.query.Filter.by_property(prop).equal(value),
                limit=5
            )
            
            if results.objects:
                for result in results.objects:
                    print(f"  - {result.properties['name']}")
            else:
                print("  No results found")
                
        except Exception as e:
            print(f"Error: {e}")

def test_graph_traversal(client):
    """Test graph traversal (relationships)."""
    
    print("\n" + "=" * 60)
    print("TEST 3: Graph Traversal (Relationships)")
    print("=" * 60)
    
    try:
        # Get all relationships
        collection = client.collections.get("Relationship")
        results = collection.query.fetch_objects(limit=10)
        
        print("\nRelationships:")
        if results.objects:
            for rel in results.objects:
                props = rel.properties
                print(f"  - Type: {props['relationshipType']}")
                print(f"    Confidence: {props['confidence']}")
                print(f"    Source: {props['source']}")
        else:
            print("  No relationships found")
            
    except Exception as e:
        print(f"Error: {e}")

def test_hybrid_search(client):
    """Test hybrid search (vector + filters)."""
    
    print("\n" + "=" * 60)
    print("TEST 4: Hybrid Search (Vector + Filters)")
    print("=" * 60)
    
    print("\nQuery: 'medication' filtered by entityType='function'")
    print("-" * 40)
    
    try:
        query_vector = np.random.rand(768).tolist()
        
        collection = client.collections.get("CodeEntity")
        results = collection.query.near_vector(
            near_vector=query_vector,
            limit=5,
            return_properties=["name", "entityType", "content"],
            filters=wvc.query.Filter.by_property("entityType").equal("function")
        )
        
        if results.objects:
            for result in results.objects:
                print(f"  - {result.properties['name']} ({result.properties['entityType']})")
                if result.metadata and result.metadata.distance is not None:
                    print(f"    Distance: {result.metadata.distance:.2f}")
        else:
            print("  No results found")
            
    except Exception as e:
        print(f"Error: {e}")

def test_statistics(client):
    """Test statistics and aggregation."""
    
    print("\n" + "=" * 60)
    print("TEST 5: Statistics and Aggregation")
    print("=" * 60)
    
    try:
        # Count objects in each class
        for class_name in ["CodeEntity", "Document", "Relationship"]:
            collection = client.collections.get(class_name)
            count = len(list(collection.iterator()))
            print(f"{class_name}: {count} objects")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main test function."""
    
    print("Running Weaviate test queries...")
    print(f"Weaviate URL: {WEAVIATE_URL}")
    print()
    
    # Connect using standard connection with gRPC on port 50051
    client = weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=int(WEAVIATE_PORT),
        grpc_port=50051,
        skip_init_checks=True
    )
    
    # Run tests
    test_vector_search(client)
    test_property_filters(client)
    test_graph_traversal(client)
    test_hybrid_search(client)
    test_statistics(client)
    
    print("\n" + "=" * 60)
    print("✓ All tests completed!")
    print("=" * 60)
    
    client.close()

if __name__ == "__main__":
    main()
