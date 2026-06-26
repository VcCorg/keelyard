"""Setup Weaviate schema for Code, Requirement, and Relationship classes."""

import httpx

# Weaviate connection
WEAVIATE_URL = "http://localhost:8080"

def create_schema():
    """Create Weaviate schema for code+requirements mapping."""
    
    client = httpx.Client(base_url=WEAVIATE_URL)
    
    # First, check existing schema
    response = client.get("/v1/schema")
    existing_classes = response.json().get("classes", [])
    existing_class_names = [c["class"] for c in existing_classes]
    
    print(f"Existing classes: {existing_class_names}")
    
    # Delete existing test classes if they exist
    for class_name in ["Code", "Requirement", "CodeRequirement"]:
        if class_name in existing_class_names:
            print(f"Deleting existing class: {class_name}")
            response = client.delete(f"/v1/schema/objects/{class_name}")
            print(f"  Status: {response.status_code}")
    
    # Delete classes from schema
    for class_name in ["Code", "Requirement", "CodeRequirement"]:
        if class_name in existing_class_names:
            print(f"Deleting class from schema: {class_name}")
            response = client.delete(f"/v1/schema/{class_name}")
            print(f"  Status: {response.status_code}")
    
    # Create Code class
    code_class = {
        "class": "Code",
        "description": "Code entities (functions, classes, modules)",
        "properties": [
            {
                "name": "name",
                "dataType": ["string"],
                "description": "Code entity name"
            },
            {
                "name": "type",
                "dataType": ["string"],
                "description": "Type (function, class, module)"
            },
            {
                "name": "file",
                "dataType": ["string"],
                "description": "Source file path"
            },
            {
                "name": "description",
                "dataType": ["text"],
                "description": "Code description"
            },
            {
                "name": "language",
                "dataType": ["string"],
                "description": "Programming language"
            },
            {
                "name": "_source",
                "dataType": ["string"],
                "description": "Data source identifier"
            }
        ],
        "vectorizer": "none"  # We'll add embeddings later if needed
    }
    
    print("\nCreating Code class...")
    response = client.post("/v1/schema", json=code_class)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text}")
    
    # Create Requirement class
    requirement_class = {
        "class": "Requirement",
        "description": "Business requirement entities",
        "properties": [
            {
                "name": "reqId",
                "dataType": ["string"],
                "description": "Requirement ID"
            },
            {
                "name": "title",
                "dataType": ["string"],
                "description": "Requirement title"
            },
            {
                "name": "description",
                "dataType": ["text"],
                "description": "Requirement description"
            },
            {
                "name": "priority",
                "dataType": ["string"],
                "description": "Priority level"
            },
            {
                "name": "category",
                "dataType": ["string"],
                "description": "Requirement category"
            },
            {
                "name": "_source",
                "dataType": ["string"],
                "description": "Data source identifier"
            }
        ],
        "vectorizer": "none"
    }
    
    print("\nCreating Requirement class...")
    response = client.post("/v1/schema", json=requirement_class)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text}")
    
    # Create CodeRequirement relationship class
    relationship_class = {
        "class": "CodeRequirement",
        "description": "Relationship between Code and Requirement",
        "properties": [
            {
                "name": "codeName",
                "dataType": ["string"],
                "description": "Reference to Code entity name"
            },
            {
                "name": "requirementId",
                "dataType": ["string"],
                "description": "Reference to Requirement entity ID"
            },
            {
                "name": "type",
                "dataType": ["string"],
                "description": "Relationship type (IMPLEMENTS, REFERENCES, etc.)"
            },
            {
                "name": "notes",
                "dataType": ["text"],
                "description": "Additional notes"
            },
            {
                "name": "_source",
                "dataType": ["string"],
                "description": "Data source identifier"
            }
        ],
        "vectorizer": "none"
    }
    
    print("\nCreating CodeRequirement class...")
    response = client.post("/v1/schema", json=relationship_class)
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text}")
    
    # Verify schema
    print("\nVerifying schema...")
    response = client.get("/v1/schema")
    schema = response.json()
    print(f"Classes: {[c['class'] for c in schema['classes']]}")
    
    client.close()
    print("\n✓ Weaviate schema setup complete")

if __name__ == "__main__":
    create_schema()
