#!/usr/bin/env python3
"""
Test script for pgvector vector search capabilities.
This script demonstrates how to use pgvector for semantic search.
"""

import psycopg2
import numpy as np
from psycopg2.extras import execute_values
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


def setup_test_table(conn):
    """Create test table with vector column."""
    with conn.cursor() as cur:
        # Drop table if exists
        cur.execute("DROP TABLE IF EXISTS code_entities CASCADE")
        
        # Create table with vector column
        cur.execute("""
            CREATE TABLE code_entities (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT,
                entity_type TEXT,
                embedding vector(768)
            )
        """)
        
        # Create HNSW index for vector search
        cur.execute("""
            CREATE INDEX code_entities_embedding_idx 
            ON code_entities 
            USING hnsw (embedding vector_cosine_ops)
        """)
        
        print("✓ Created code_entities table with vector index")


def insert_test_data(conn):
    """Insert test data with embeddings."""
    with conn.cursor() as cur:
        # Test code entities
        test_data = [
            ('calculate_dosage', 'function to calculate medication dosage', 'function'),
            ('validate_patient', 'function to validate patient data', 'function'),
            ('process_claim', 'function to process insurance claims', 'function'),
            ('Patient', 'class representing patient data', 'class'),
            ('Claim', 'class representing insurance claim', 'class'),
            ('DosageCalculator', 'utility class for dosage calculations', 'class'),
        ]
        
        # Generate random embeddings (in production, use actual embeddings)
        for name, content, entity_type in test_data:
            embedding = np.random.rand(768).tolist()
            cur.execute(
                """
                INSERT INTO code_entities (name, content, entity_type, embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (name, content, entity_type, embedding)
            )
        
        print(f"✓ Inserted {len(test_data)} test records")


def test_vector_search(conn):
    """Test vector similarity search."""
    with conn.cursor() as cur:
        # Generate a query vector
        query_vector = np.random.rand(768).tolist()
        
        # Perform vector search
        cur.execute("""
            SELECT name, content, entity_type,
                   1 - (embedding <=> %s) as similarity
            FROM code_entities
            ORDER BY embedding <=> %s
            LIMIT 5
        """, (query_vector, query_vector))
        
        results = cur.fetchall()
        
        print("\n--- Vector Search Results ---")
        print(f"Query vector dimension: 768")
        print(f"Found {len(results)} similar entities:\n")
        
        for name, content, entity_type, similarity in results:
            print(f"  {name} ({entity_type})")
            print(f"    Content: {content}")
            print(f"    Similarity: {similarity:.4f}\n")


def test_filtered_vector_search(conn):
    """Test vector search with filters."""
    with conn.cursor() as cur:
        query_vector = np.random.rand(768).tolist()
        
        # Perform vector search with entity_type filter
        cur.execute("""
            SELECT name, content, entity_type,
                   1 - (embedding <=> %s) as similarity
            FROM code_entities
            WHERE entity_type = 'function'
            ORDER BY embedding <=> %s
            LIMIT 3
        """, (query_vector, query_vector))
        
        results = cur.fetchall()
        
        print("\n--- Filtered Vector Search (functions only) ---")
        print(f"Found {len(results)} similar functions:\n")
        
        for name, content, entity_type, similarity in results:
            print(f"  {name} ({entity_type})")
            print(f"    Content: {content}")
            print(f"    Similarity: {similarity:.4f}\n")


def main():
    """Main test function."""
    print("=== Testing pgvector Vector Search ===\n")
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = connect_db()
        print("✓ Connected to database\n")
        
        # Setup test table
        setup_test_table(conn)
        
        # Insert test data
        insert_test_data(conn)
        
        # Test vector search
        test_vector_search(conn)
        
        # Test filtered vector search
        test_filtered_vector_search(conn)
        
        # Close connection
        conn.close()
        print("✓ Tests completed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
