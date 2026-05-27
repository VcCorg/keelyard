#!/usr/bin/env python3
"""
Test script for hybrid vector + graph queries.
This script demonstrates the "bridge pattern" - using vector similarity
to create graph edges, then combining vector and graph queries.
"""

import psycopg2
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "knowledge_graph")


def connect_db():
    """Connect to PostgreSQL database."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    conn.autocommit = True
    return conn


def setup_hybrid_data(conn):
    """Setup tables with vectors and graph data."""
    with conn.cursor() as cur:
        # Set search path
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        # Create table with vectors
        cur.execute("""
            DROP TABLE IF EXISTS code_entities CASCADE
            CREATE TABLE code_entities (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT,
                entity_type TEXT,
                embedding vector(768)
            )
        """)
        
        # Create vector index
        cur.execute("""
            CREATE INDEX code_entities_embedding_idx 
            ON code_entities 
            USING hnsw (embedding vector_cosine_ops)
        """)
        
        # Insert test data with embeddings
        test_data = [
            ('calculate_dosage', 'function to calculate medication dosage', 'function'),
            ('validate_patient', 'function to validate patient data', 'function'),
            ('process_claim', 'function to process insurance claims', 'function'),
            ('get_patient_info', 'function to retrieve patient information', 'function'),
            ('Patient', 'class representing patient data', 'class'),
            ('Claim', 'class representing insurance claim', 'class'),
            ('DosageCalculator', 'utility class for dosage calculations', 'class'),
            ('PatientValidator', 'class for validating patient data', 'class'),
        ]
        
        for name, content, entity_type in test_data:
            embedding = np.random.rand(768).tolist()
            cur.execute(
                """
                INSERT INTO code_entities (name, content, entity_type, embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (name, content, entity_type, embedding)
            )
        
        # Create graph
        cur.execute("SELECT create_graph('knowledge_graph')")
        
        # Create nodes in graph
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                CREATE (f1:Function {name: 'calculate_dosage', content: 'function to calculate medication dosage'})
                CREATE (f2:Function {name: 'validate_patient', content: 'function to validate patient data'})
                CREATE (f3:Function {name: 'process_claim', content: 'function to process insurance claims'})
                CREATE (f4:Function {name: 'get_patient_info', content: 'function to retrieve patient information'})
                CREATE (c1:Class {name: 'Patient', content: 'class representing patient data'})
                CREATE (c2:Class {name: 'Claim', content: 'class representing insurance claim'})
            $$) as (result agtype)
        """)
        
        # Create relationships
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                MATCH (f:Function {name: 'calculate_dosage'}), (c:Class {name: 'Patient'})
                CREATE (f)-[:OPERATES_ON]->(c)
                
                MATCH (f:Function {name: 'validate_patient'}), (c:Class {name: 'Patient'})
                CREATE (f)-[:VALIDATES]->(c)
                
                MATCH (f:Function {name: 'process_claim'}), (c:Class {name: 'Claim'})
                CREATE (f)-[:PROCESSES]->(c)
                
                MATCH (f:Function {name: 'get_patient_info'}), (c:Class {name: 'Patient'})
                CREATE (f)-[:RETRIEVES]->(c)
            $$) as (result agtype)
        """)
        
        print("✓ Setup hybrid data (vectors + graph)")


def test_vector_to_graph_bridge(conn):
    """
    Test the bridge pattern: use vector similarity to find similar entities,
    then use graph traversal to find related entities.
    """
    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        query_vector = np.random.rand(768).tolist()
        
        # Step 1: Find similar functions using vector search
        cur.execute("""
            WITH similar_functions AS (
                SELECT id, name, 
                       1 - (embedding <=> %s) as similarity
                FROM code_entities
                WHERE entity_type = 'function'
                ORDER BY embedding <=> %s
                LIMIT 3
            )
            SELECT id, name, similarity
            FROM similar_functions
        """, (query_vector, query_vector))
        
        similar_results = cur.fetchall()
        
        print("\n--- Step 1: Vector Search (find similar functions) ---")
        print(f"Query vector: 768 dimensions")
        print(f"Found {len(similar_results)} similar functions:\n")
        
        for func_id, func_name, similarity in similar_results:
            print(f"  {func_name} (similarity: {similarity:.4f})")
        
        # Step 2: For each similar function, find what classes it relates to in the graph
        print("\n--- Step 2: Graph Traversal (find related classes) ---")
        
        for func_id, func_name, similarity in similar_results:
            # Find classes related to this function in the graph
            cur.execute("""
                SELECT * FROM cypher('knowledge_graph', $$
                    MATCH (f:Function {name: $func_name})-[r]->(c:Class)
                    RETURN type(r) as relationship_type, c.name as class_name
                $$, {'func_name': func_name}) as (relationship_type agtype, class_name agtype)
            """)
            
            graph_results = cur.fetchall()
            
            if graph_results:
                print(f"\n  {func_name} relates to:")
                for rel_type, class_name in graph_results:
                    print(f"    -> {class_name} ({rel_type})")
            else:
                print(f"\n  {func_name} has no graph relationships")


def test_hybrid_single_query(conn):
    """
    Test a single hybrid query that combines vector and graph operations.
    This demonstrates the power of having both in the same database.
    """
    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        query_vector = np.random.rand(768).tolist()
        
        # Hybrid query: Find similar functions, then filter by graph relationships
        cur.execute("""
            WITH similar_functions AS (
                SELECT id, name, content,
                       1 - (embedding <=> %s) as similarity
                FROM code_entities
                WHERE entity_type = 'function'
                ORDER BY embedding <=> %s
                LIMIT 10
            )
            SELECT sf.name, sf.content, sf.similarity
            FROM similar_functions sf
            WHERE sf.name IN (
                SELECT f.name::text 
                FROM cypher('knowledge_graph', $$
                    MATCH (f:Function)-[:OPERATES_ON|:VALIDATES]->(c:Class {name: 'Patient'})
                    RETURN f.name
                $$) as (name agtype)
            )
            ORDER BY sf.similarity DESC
        """, (query_vector, query_vector))
        
        results = cur.fetchall()
        
        print("\n--- Hybrid Query: Similar functions that operate on Patient ---")
        print(f"Found {len(results)} functions:\n")
        
        for name, content, similarity in results:
            print(f"  {name} (similarity: {similarity:.4f})")
            print(f"    Content: {content}")


def test_graph_similarity_edges(conn):
    """
    Test creating graph edges based on vector similarity.
    This is the core "bridge pattern" - converting vector scores to graph edges.
    """
    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        # Find pairs of functions with high similarity and create SIMILAR_TO edges
        cur.execute("""
            WITH similar_pairs AS (
                SELECT 
                    f1.id as id1,
                    f1.name as name1,
                    f2.id as id2,
                    f2.name as name2,
                    1 - (f1.embedding <=> f2.embedding) as similarity
                FROM code_entities f1, code_entities f2
                WHERE f1.id < f2.id
                AND f1.entity_type = 'function'
                AND f2.entity_type = 'function'
                AND (1 - (f1.embedding <=> f2.embedding)) > 0.5
                ORDER BY similarity DESC
                LIMIT 5
            )
            SELECT name1, name2, similarity
            FROM similar_pairs
        """)
        
        results = cur.fetchall()
        
        print("\n--- Vector Similarity Pairs (candidates for graph edges) ---")
        print(f"Found {len(results)} similar function pairs:\n")
        
        for name1, name2, similarity in results:
            print(f"  {name1} <-> {name2} (similarity: {similarity:.4f})")
        
        # Create SIMILAR_TO edges in the graph for these pairs
        print("\n--- Creating SIMILAR_TO edges in graph ---")
        
        for name1, name2, similarity in results:
            cur.execute("""
                SELECT * FROM cypher('knowledge_graph', $$
                    MATCH (f1:Function {name: $name1}), (f2:Function {name: $name2})
                    CREATE (f1)-[:SIMILAR_TO {score: $score}]->(f2)
                    CREATE (f2)-[:SIMILAR_TO {score: $score}]->(f1)
                $$, {'name1': name1, 'name2': name2, 'score': similarity}) as (result agtype)
            """)
            
            print(f"  Created edge: {name1} <-> {name2}")
        
        # Now traverse the similarity graph
        print("\n--- Traversing similarity graph ---")
        
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                MATCH (f:Function)-[:SIMILAR_TO]->(other:Function)
                RETURN f.name as function_name, other.name as similar_to, r.score as similarity
            $$) as (function_name agtype, similar_to agtype, similarity agtype)
        """)
        
        traversal_results = cur.fetchall()
        
        for func_name, similar_to, similarity in traversal_results:
            print(f"  {func_name} is similar to {similar_to} (score: {similarity})")


def main():
    """Main test function."""
    print("=== Testing Hybrid Vector + Graph Queries ===\n")
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = connect_db()
        print("✓ Connected to database\n")
        
        # Setup hybrid data
        setup_hybrid_data(conn)
        
        # Test vector to graph bridge
        test_vector_to_graph_bridge(conn)
        
        # Test hybrid single query
        test_hybrid_single_query(conn)
        
        # Test graph similarity edges
        test_graph_similarity_edges(conn)
        
        # Close connection
        conn.close()
        print("\n✓ Tests completed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
