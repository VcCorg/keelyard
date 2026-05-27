"""Test LightRAG stability with sample code+requirements data."""

import httpx
import json

# Sample data
CODE_ENTITIES = [
    {
        "name": "authenticate_user",
        "type": "function",
        "file": "auth_service.py",
        "description": "Authenticates user credentials against the database"
    },
    {
        "name": "validate_password",
        "type": "function",
        "file": "auth_service.py",
        "description": "Validates password strength and format"
    }
]

REQUIREMENT_ENTITIES = [
    {
        "id": "REQ-001",
        "title": "User Authentication",
        "description": "System must authenticate users before granting access to protected resources"
    },
    {
        "id": "REQ-002",
        "title": "Password Validation",
        "description": "Passwords must be at least 8 characters with special characters"
    }
]

def test_lightrag():
    """Test LightRAG connectivity and operations."""
    base_url = "http://localhost:8001"
    
    print("=== Testing LightRAG ===\n")
    
    try:
        client = httpx.Client(base_url=base_url, timeout=30.0)
        
        # Test 1: Health check
        print("1. Health Check:")
        try:
            response = client.get("/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.json()}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ✗ Health check failed: {e}")
            return
        
        # Test 2: Insert code entity
        print("\n2. Insert Code Entity:")
        for code in CODE_ENTITIES:
            text = f"Code: {code['name']} ({code['type']}) in {code['file']}\nDescription: {code['description']}"
            try:
                response = client.post("/insert", json={"text": text})
                print(f"   {code['name']}: Status {response.status_code}")
                if response.status_code == 200:
                    print(f"      {response.json()}")
                else:
                    print(f"      Error: {response.text}")
            except Exception as e:
                print(f"   ✗ Insert failed for {code['name']}: {e}")
        
        # Test 3: Insert requirement entity
        print("\n3. Insert Requirement Entity:")
        for req in REQUIREMENT_ENTITIES:
            text = f"Requirement: {req['id']} - {req['title']}\nDescription: {req['description']}"
            try:
                response = client.post("/insert", json={"text": text})
                print(f"   {req['id']}: Status {response.status_code}")
                if response.status_code == 200:
                    print(f"      {response.json()}")
                else:
                    print(f"      Error: {response.text}")
            except Exception as e:
                print(f"   ✗ Insert failed for {req['id']}: {e}")
        
        # Test 4: Query
        print("\n4. Query Test:")
        query = "authentication function"
        try:
            response = client.post("/query", json={
                "query": query,
                "mode": "hybrid",
                "top_k": 5
            })
            print(f"   Query: {query}")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   Result: {result.get('result', result)}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ✗ Query failed: {e}")
        
        # Test 5: Get stats
        print("\n5. Statistics:")
        try:
            response = client.get("/stats")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                stats = response.json()
                print(f"   Stats: {json.dumps(stats, indent=2)}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   ✗ Stats retrieval failed: {e}")
        
        client.close()
        print("\n✓ LightRAG test complete\n")
        
    except Exception as e:
        print(f"✗ LightRAG test failed: {e}\n")

if __name__ == "__main__":
    test_lightrag()
