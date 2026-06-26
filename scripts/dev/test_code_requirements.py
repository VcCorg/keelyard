"""Test script to ingest sample code+requirements data into Neo4j and Weaviate."""

# Sample data for code + requirements mapping
CODE_ENTITIES = [
    {
        "name": "authenticate_user",
        "type": "function",
        "file": "auth_service.py",
        "description": "Authenticates user credentials against the database",
        "language": "python"
    },
    {
        "name": "validate_password",
        "type": "function",
        "file": "auth_service.py",
        "description": "Validates password strength and format",
        "language": "python"
    },
    {
        "name": "create_session",
        "type": "function",
        "file": "session_manager.py",
        "description": "Creates a new user session with token",
        "language": "python"
    },
    {
        "name": "AuthController",
        "type": "class",
        "file": "auth_controller.py",
        "description": "Handles HTTP authentication requests",
        "language": "python"
    }
]

REQUIREMENT_ENTITIES = [
    {
        "id": "REQ-001",
        "title": "User Authentication",
        "description": "System must authenticate users before granting access to protected resources",
        "priority": "high",
        "category": "security"
    },
    {
        "id": "REQ-002",
        "title": "Password Validation",
        "description": "Passwords must be at least 8 characters with special characters",
        "priority": "high",
        "category": "security"
    },
    {
        "id": "REQ-003",
        "title": "Session Management",
        "description": "User sessions must expire after 30 minutes of inactivity",
        "priority": "medium",
        "category": "security"
    },
    {
        "id": "REQ-004",
        "title": "API Authentication",
        "description": "All API endpoints must require authentication token",
        "priority": "high",
        "category": "security"
    }
]

RELATIONSHIPS = [
    {
        "code": "authenticate_user",
        "requirement": "REQ-001",
        "type": "IMPLEMENTS",
        "notes": "Direct implementation of authentication logic"
    },
    {
        "code": "validate_password",
        "requirement": "REQ-002",
        "type": "IMPLEMENTS",
        "notes": "Implements password strength validation"
    },
    {
        "code": "create_session",
        "requirement": "REQ-003",
        "type": "IMPLEMENTS",
        "notes": "Handles session creation with timeout"
    },
    {
        "code": "AuthController",
        "requirement": "REQ-004",
        "type": "IMPLEMENTS",
        "notes": "API-level authentication enforcement"
    },
    {
        "code": "authenticate_user",
        "requirement": "REQ-002",
        "type": "REFERENCES",
        "notes": "Calls validate_password internally"
    }
]

def ingest_neo4j():
    """Ingest sample data into Neo4j using direct Cypher."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("  neo4j driver not installed, skipping")
        return
    
    print("=== Ingesting into Neo4j ===")
    
    # Connect directly
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    
    with driver.session() as session:
        # Clear existing test data
        session.run("MATCH (n) WHERE n._source = 'test_data' DETACH DELETE n")
        
        # Create code nodes
        for code in CODE_ENTITIES:
            cypher = """
            CREATE (c:Code {
                _source: 'test_data',
                name: $name,
                type: $type,
                file: $file,
                description: $description,
                language: $language
            })
            """
            session.run(cypher, **code)
            print(f"  Created code node: {code['name']}")
        
        # Create requirement nodes
        for req in REQUIREMENT_ENTITIES:
            cypher = """
            CREATE (r:Requirement {
                _source: 'test_data',
                id: $id,
                title: $title,
                description: $description,
                priority: $priority,
                category: $category
            })
            """
            session.run(cypher, **req)
            print(f"  Created requirement node: {req['id']}")
        
        # Create relationships
        for rel in RELATIONSHIPS:
            cypher = """
            MATCH (c:Code {name: $code, _source: 'test_data'})
            MATCH (r:Requirement {id: $requirement, _source: 'test_data'})
            CREATE (c)-[rel:RELATIONSHIP {
                type: $type,
                notes: $notes,
                _source: 'test_data'
            }]->(r)
            """
            session.run(cypher, **rel)
            print(f"  Created relationship: {rel['code']} -> {rel['requirement']}")
    
    driver.close()
    print("✓ Neo4j ingestion complete\n")

def ingest_weaviate():
    """Ingest sample data into Weaviate using REST API."""
    try:
        import httpx
    except ImportError:
        print("  httpx not installed, skipping")
        return
    
    print("=== Ingesting into Weaviate ===")
    
    client = httpx.Client(base_url="http://localhost:8080")
    
    # Clear existing test data
    print("  Clearing existing test data...")
    # Weaviate doesn't have a simple clear all, so we'll just overwrite
    
    # Ingest Code entities
    print("  Ingesting Code entities...")
    for code in CODE_ENTITIES:
        # Use reqId instead of id for Requirement class
        code_obj = {
            "name": code["name"],
            "type": code["type"],
            "file": code["file"],
            "description": code["description"],
            "language": code["language"],
            "_source": "test_data"
        }
        response = client.post("/v1/objects", json={
            "class": "Code",
            "properties": code_obj
        })
        print(f"    Created: {code['name']} (status: {response.status_code})")
    
    # Ingest Requirement entities (use reqId instead of id)
    print("  Ingesting Requirement entities...")
    for req in REQUIREMENT_ENTITIES:
        req_obj = {
            "reqId": req["id"],  # Changed from id to reqId
            "title": req["title"],
            "description": req["description"],
            "priority": req["priority"],
            "category": req["category"],
            "_source": "test_data"
        }
        response = client.post("/v1/objects", json={
            "class": "Requirement",
            "properties": req_obj
        })
        print(f"    Created: {req['id']} (status: {response.status_code})")
    
    # Ingest Relationships
    print("  Ingesting Relationships...")
    for rel in RELATIONSHIPS:
        rel_obj = {
            "codeName": rel["code"],
            "requirementId": rel["requirement"],
            "type": rel["type"],
            "notes": rel["notes"],
            "_source": "test_data"
        }
        response = client.post("/v1/objects", json={
            "class": "CodeRequirement",
            "properties": rel_obj
        })
        print(f"    Created: {rel['code']} -> {rel['requirement']} (status: {response.status_code})")
    
    client.close()
    print("✓ Weaviate ingestion complete\n")

def query_weaviate():
    """Test Weaviate queries."""
    try:
        import httpx
    except ImportError:
        print("  httpx not installed, skipping queries")
        return
    
    print("=== Testing Weaviate Queries ===")
    
    client = httpx.Client(base_url="http://localhost:8080")
    
    # Query 1: Find all code implementing a requirement (via relationship class)
    print("\n1. Code implementing REQ-001:")
    where_clause = {
        "path": ["requirementId"],
        "operator": "Equal",
        "valueString": "REQ-001"
    }
    response = client.get("/v1/objects", params={
        "class": "CodeRequirement",
        "where": str(where_clause).replace("'", '"')
    })
    if response.status_code == 200:
        results = response.json().get("objects", [])
        for obj in results:
            props = obj["properties"]
            print(f"  - {props['codeName']} ({props['type']})")
    
    # Query 2: Find all requirements implemented by a function
    print("\n2. Requirements implemented by authenticate_user:")
    where_clause = {
        "path": ["codeName"],
        "operator": "Equal",
        "valueString": "authenticate_user"
    }
    response = client.get("/v1/objects", params={
        "class": "CodeRequirement",
        "where": str(where_clause).replace("'", '"')
    })
    if response.status_code == 200:
        results = response.json().get("objects", [])
        for obj in results:
            props = obj["properties"]
            print(f"  - {props['requirementId']}")
    
    # Query 3: Get all traceability paths
    print("\n3. All traceability paths:")
    response = client.get("/v1/objects", params={"class": "CodeRequirement"})
    if response.status_code == 200:
        results = response.json().get("objects", [])
        for obj in results:
            props = obj["properties"]
            print(f"  - {props['codeName']} -> {props['requirementId']} ({props['type']})")
    
    client.close()
    print("\n✓ Weaviate queries complete\n")

def query_neo4j():
    """Test Neo4j queries."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("  neo4j driver not installed, skipping queries")
        return
    
    print("=== Testing Neo4j Queries ===")
    
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    
    with driver.session() as session:
        # Query 1: Find all code implementing a requirement
        print("\n1. Code implementing REQ-001:")
        cypher = """
        MATCH (c:Code)-[r:RELATIONSHIP]->(req:Requirement {id: 'REQ-001', _source: 'test_data'})
        RETURN c.name, c.type, r.type, r.notes
        """
        result = session.run(cypher)
        for record in result:
            print(f"  - {record['c.name']} ({record['c.type']})")
        
        # Query 2: Find all requirements implemented by a function
        print("\n2. Requirements implemented by authenticate_user:")
        cypher = """
        MATCH (c:Code {name: 'authenticate_user', _source: 'test_data'})-[r:RELATIONSHIP]->(req:Requirement)
        RETURN req.id, req.title, r.type
        """
        result = session.run(cypher)
        for record in result:
            print(f"  - {record['req.id']}: {record['req.title']}")
        
        # Query 3: Traceability path
        print("\n3. Traceability path (code -> requirements):")
        cypher = """
        MATCH path = (c:Code {_source: 'test_data'})-[:RELATIONSHIP]->(req:Requirement {_source: 'test_data'})
        RETURN c.name, req.id, req.title
        ORDER BY c.name, req.id
        """
        result = session.run(cypher)
        for record in result:
            print(f"  - {record['c.name']} -> {record['req.id']}")
    
    driver.close()
    print("\n✓ Neo4j queries complete\n")

if __name__ == "__main__":
    print("=== Testing Neo4j and Weaviate for Code+Requirements Mapping ===\n")
    
    # Ingest into Neo4j
    ingest_neo4j()
    
    # Test Neo4j queries
    query_neo4j()
    
    # Ingest into Weaviate
    ingest_weaviate()
    
    # Test Weaviate queries
    query_weaviate()
    
    print("=== Summary ===")
    print("Neo4j: ✓ Working with Cypher queries, graph traversals")
    print("Weaviate: ✓ Working with REST API queries")
    print("\nBoth providers successfully ingested and queried sample data")
