#!/usr/bin/env python3
"""
Ingest test data into Weaviate for DVA KG infrastructure validation.

This script creates sample code entities and documents to test the
Weaviate infrastructure.
"""

import weaviate
import os
from dotenv import load_dotenv
import uuid
import numpy as np
import weaviate.classes as wvc

# Load environment variables
load_dotenv()

# Weaviate configuration
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "localhost")
WEAVIATE_PORT = os.getenv("WEAVIATE_PORT", "8080")
WEAVIATE_URL = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"

def ingest_code_entities(client):
    """Ingest sample code entities."""
    
    code_entities = [
        {
            "name": "calculate_patient_dosage",
            "content": "Function to calculate medication dosage based on patient weight and age. Takes patient object and returns recommended dosage.",
            "entityType": "function",
            "filePath": "src/dosage/calculator.py",
            "language": "python",
            "domain": "cwow-facility",
            "repo": "clinical-workflow",
            "lineNumber": 42
        },
        {
            "name": "Patient",
            "content": "Patient class representing a patient in the clinical system. Contains properties for demographics, medical history, and current medications.",
            "entityType": "class",
            "filePath": "src/models/patient.py",
            "language": "python",
            "domain": "cwow-facility",
            "repo": "clinical-workflow",
            "lineNumber": 15
        },
        {
            "name": "validate_medication_order",
            "content": "Validates medication orders against patient allergies and drug interactions. Returns validation result with warnings and errors.",
            "entityType": "function",
            "filePath": "src/medication/validator.py",
            "language": "python",
            "domain": "cwow-facility",
            "repo": "clinical-workflow",
            "lineNumber": 78
        },
        {
            "name": "FacilityService",
            "content": "Service class for managing facility-related operations including room assignments, bed management, and facility status tracking.",
            "entityType": "class",
            "filePath": "src/services/facility.py",
            "language": "python",
            "domain": "cwow-facility",
            "repo": "clinical-workflow",
            "lineNumber": 23
        },
        {
            "name": "get_available_beds",
            "content": "Retrieves list of available beds in a facility based on department and bed type. Filters by occupancy status and cleanliness.",
            "entityType": "function",
            "filePath": "src/services/facility.py",
            "language": "python",
            "domain": "cwow-facility",
            "repo": "clinical-workflow",
            "lineNumber": 156
        }
    ]
    
    print(f"Ingesting {len(code_entities)} code entities...")
    
    collection = client.collections.get("CodeEntity")
    
    for entity in code_entities:
        try:
            # Generate a dummy vector (in production, this would come from Vertex AI)
            vector = np.random.rand(768).tolist()
            
            collection.data.insert(
                properties=entity,
                vector=vector,
                uuid=uuid.uuid4()
            )
            print(f"  ✓ Ingested: {entity['name']}")
        except Exception as e:
            print(f"  ✗ Failed to ingest {entity['name']}: {e}")

def ingest_documents(client):
    """Ingest sample documents."""
    
    documents = [
        {
            "name": "Medication Dosage Calculation Requirements",
            "content": "This document specifies the requirements for medication dosage calculation in the clinical workflow system. Dosage must be calculated based on patient weight, age, and renal function. Maximum dosage limits must be enforced for elderly patients.",
            "documentType": "requirement",
            "domain": "cwow-facility",
            "source": "Confluence",
            "url": "https://confluence.example.com/pages/12345",
            "author": "Clinical Team"
        },
        {
            "name": "Patient Data Model Specification",
            "content": "Specification for the patient data model including demographics, medical history, allergies, and current medications. All patient data must be HIPAA compliant and encrypted at rest.",
            "documentType": "specification",
            "domain": "cwow-facility",
            "source": "Confluence",
            "url": "https://confluence.example.com/pages/67890",
            "author": "Data Team"
        },
        {
            "name": "Medication Order Validation Rules",
            "content": "Defines validation rules for medication orders including drug-drug interaction checking, allergy checking, and dosage range validation. All orders must be validated before being sent to the pharmacy system.",
            "documentType": "requirement",
            "domain": "cwow-facility",
            "source": "Jira",
            "url": "https://jira.example.com/browse/CWOW-1234",
            "author": "Pharmacy Team"
        },
        {
            "name": "Facility Bed Management Requirements",
            "content": "Requirements for facility bed management including room assignments, bed status tracking, and availability reporting. System must provide real-time bed availability across all facilities.",
            "documentType": "requirement",
            "domain": "cwow-facility",
            "source": "Confluence",
            "url": "https://confluence.example.com/pages/54321",
            "author": "Operations Team"
        }
    ]
    
    print(f"\nIngesting {len(documents)} documents...")
    
    collection = client.collections.get("Document")
    
    for doc in documents:
        try:
            # Generate a dummy vector (in production, this would come from Vertex AI)
            vector = np.random.rand(768).tolist()
            
            collection.data.insert(
                properties=doc,
                vector=vector,
                uuid=uuid.uuid4()
            )
            print(f"  ✓ Ingested: {doc['name']}")
        except Exception as e:
            print(f"  ✗ Failed to ingest {doc['name']}: {e}")

def ingest_relationships(client):
    """Ingest sample relationships."""
    
    # Get code entities and documents
    code_entities = list(client.collections.get("CodeEntity").iterator())
    documents = list(client.collections.get("Document").iterator())
    
    if not code_entities or not documents:
        print("No code entities or documents found. Skipping relationship ingestion.")
        return
    
    # Create relationships between first code entity and first document
    relationships = [
        {
            "relationshipType": "implements",
            "confidence": 0.92,
            "source": "llm_evaluation"
        },
        {
            "relationshipType": "references",
            "confidence": 0.88,
            "source": "vector_search"
        }
    ]
    
    print(f"\nIngesting {len(relationships)} relationships...")
    
    collection = client.collections.get("Relationship")
    
    for rel in relationships:
        try:
            # Generate a dummy vector
            vector = np.random.rand(768).tolist()
            
            collection.data.insert(
                properties=rel,
                vector=vector,
                uuid=uuid.uuid4()
            )
            print(f"  ✓ Ingested: {rel['relationshipType']}")
        except Exception as e:
            print(f"  ✗ Failed to ingest {rel['relationshipType']}: {e}")

def main():
    """Main ingestion function."""
    
    print("Ingesting test data into Weaviate...")
    print(f"Weaviate URL: {WEAVIATE_URL}")
    print()
    
    # Connect using standard connection with gRPC on port 50051
    client = weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=int(WEAVIATE_PORT),
        grpc_port=50051,
        skip_init_checks=True
    )
    
    # Ingest data
    ingest_code_entities(client)
    ingest_documents(client)
    ingest_relationships(client)
    
    print("\n✓ Test data ingestion complete!")
    
    # Print statistics
    print("\nStatistics:")
    code_count = len(list(client.collections.get("CodeEntity").iterator()))
    doc_count = len(list(client.collections.get("Document").iterator()))
    rel_count = len(list(client.collections.get("Relationship").iterator()))
    
    print(f"  Code Entities: {code_count}")
    print(f"  Documents: {doc_count}")
    print(f"  Relationships: {rel_count}")
    
    client.close()

if __name__ == "__main__":
    main()
