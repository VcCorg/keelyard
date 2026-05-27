#!/usr/bin/env python3
"""
Test script for Apache AGE graph queries.
This script demonstrates how to use Apache AGE for graph traversal.
"""

import psycopg2
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


def setup_graph(conn):
    """Create graph and load test data."""
    with conn.cursor() as cur:
        # Set search path to include ag_catalog
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        # Create graph
        cur.execute("SELECT create_graph('knowledge_graph')")
        print("✓ Created knowledge_graph")
        
        # Create nodes using Cypher
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                CREATE (f1:Function {name: 'calculate_dosage', content: 'function to calculate medication dosage'})
                CREATE (f2:Function {name: 'validate_patient', content: 'function to validate patient data'})
                CREATE (f3:Function {name: 'process_claim', content: 'function to process insurance claims'})
                CREATE (c1:Class {name: 'Patient', content: 'class representing patient data'})
                CREATE (c2:Class {name: 'Claim', content: 'class representing insurance claim'})
                CREATE (c3:Class {name: 'DosageCalculator', content: 'utility class for dosage calculations'})
            $$) as (result agtype)
        """)
        print("✓ Created nodes")
        
        # Create relationships
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                MATCH (f:Function {name: 'calculate_dosage'}), (c:Class {name: 'DosageCalculator'})
                CREATE (f)-[:USES]->(c)
                
                MATCH (f:Function {name: 'validate_patient'}), (c:Class {name: 'Patient'})
                CREATE (f)-[:USES]->(c)
                
                MATCH (f:Function {name: 'process_claim'}), (c:Class {name: 'Claim'})
                CREATE (f)-[:USES]->(c)
                
                MATCH (f:Function {name: 'calculate_dosage'}), (c:Class {name: 'Patient'})
                CREATE (f)-[:OPERATES_ON]->(c)
            $$) as (result agtype)
        """)
        print("✓ Created relationships")


def test_simple_traversal(conn):
    """Test simple graph traversal."""
    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                MATCH (f:Function)-[:USES]->(c:Class)
                RETURN f.name as function_name, c.name as class_name
            $$) as (function_name agtype, class_name agtype)
        """)
        
        results = cur.fetchall()
        
        print("\n--- Simple Traversal: Functions using Classes ---")
        print(f"Found {len(results)} relationships:\n")
        
        for function_name, class_name in results:
            print(f"  {function_name} -> {class_name}")


def test_complex_traversal(conn):
    """Test complex graph traversal with multiple hops."""
    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        # Find functions that operate on Patient class
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                MATCH (f:Function)-[:OPERATES_ON]->(c:Class {name: 'Patient'})
                RETURN f.name as function_name, f.content as content
            $$) as (function_name agtype, content agtype)
        """)
        
        results = cur.fetchall()
        
        print("\n--- Complex Traversal: Functions operating on Patient ---")
        print(f"Found {len(results)} functions:\n")
        
        for function_name, content in results:
            print(f"  {function_name}")
            print(f"    Content: {content}")


def test_path_finding(conn):
    """Test path finding between nodes."""
    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        # Find all paths from calculate_dosage to Patient
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                MATCH path = (start:Function {name: 'calculate_dosage'})-[*]->(end:Class {name: 'Patient'})
                RETURN path
            $$) as (path agtype)
        """)
        
        results = cur.fetchall()
        
        print("\n--- Path Finding: calculate_dosage to Patient ---")
        print(f"Found {len(results)} paths:\n")
        
        for path, in results:
            print(f"  Path: {path}")


def test_aggregation(conn):
    """Test aggregation on graph data."""
    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, '$user', public")
        
        # Count relationships per function
        cur.execute("""
            SELECT * FROM cypher('knowledge_graph', $$
                MATCH (f:Function)-[r]->()
                RETURN f.name as function_name, count(r) as relationship_count
            $$) as (function_name agtype, relationship_count agtype)
        """)
        
        results = cur.fetchall()
        
        print("\n--- Aggregation: Relationship counts per function ---")
        print(f"Found {len(results)} functions:\n")
        
        for function_name, count in results:
            print(f"  {function_name}: {count} relationships")


def main():
    """Main test function."""
    print("=== Testing Apache AGE Graph Queries ===\n")
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = connect_db()
        print("✓ Connected to database\n")
        
        # Setup graph
        setup_graph(conn)
        
        # Test simple traversal
        test_simple_traversal(conn)
        
        # Test complex traversal
        test_complex_traversal(conn)
        
        # Test path finding
        test_path_finding(conn)
        
        # Test aggregation
        test_aggregation(conn)
        
        # Close connection
        conn.close()
        print("\n✓ Tests completed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
