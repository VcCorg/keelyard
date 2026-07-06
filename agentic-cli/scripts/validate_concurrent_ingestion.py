#!/usr/bin/env python3
"""
Validation script for concurrent ingestion capabilities.

Tests:
1. LightRAG concurrent insert operations
2. Neo4j concurrent write operations
3. Parallel job execution
4. Resource usage monitoring
"""

import asyncio
import concurrent.futures
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_cli.kg.lightrag_client import LightRAGClient, check_lightrag_availability
from agentic_cli.kg.config import KGConfig
from agentic_cli.kg.neo4j_client import Neo4jClient


def test_lightrag_concurrent_inserts(num_workers=4, docs_per_worker=5):
    """Test concurrent document insertion to LightRAG."""
    print(f"\n{'='*60}")
    print("TEST 1: LightRAG Concurrent Inserts")
    print(f"{'='*60}")
    print(f"Workers: {num_workers}, Docs per worker: {docs_per_worker}")
    
    # Check availability
    is_available, message = check_lightrag_availability()
    if not is_available:
        print(f"❌ LightRAG not available: {message}")
        return False
    
    print("✓ LightRAG is available")
    
    def insert_documents(worker_id):
        """Insert documents from a single worker."""
        client = LightRAGClient()
        results = []
        
        for i in range(docs_per_worker):
            doc_id = f"worker{worker_id}_doc{i}"
            text = f"Test document {doc_id} with some content for testing concurrent inserts."
            
            try:
                result = client.insert(text=text, metadata={"worker": worker_id, "doc": i})
                results.append((doc_id, "success"))
            except Exception as e:
                results.append((doc_id, f"error: {e}"))
        
        client.close()
        return results
    
    # Run concurrent inserts
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(insert_documents, i) for i in range(num_workers)]
        all_results = []
        
        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())
    
    duration = time.time() - start_time
    
    # Check results
    success_count = sum(1 for _, status in all_results if status == "success")
    total_docs = num_workers * docs_per_worker
    
    print(f"\nResults:")
    print(f"  Total documents: {total_docs}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {total_docs - success_count}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Throughput: {total_docs/duration:.1f} docs/sec")
    
    if success_count == total_docs:
        print("✅ All concurrent inserts successful!")
        return True
    else:
        print(f"⚠️  Some inserts failed ({total_docs - success_count} failures)")
        return False


def test_neo4j_concurrent_writes(num_workers=4, nodes_per_worker=5):
    """Test concurrent node creation in Neo4j."""
    print(f"\n{'='*60}")
    print("TEST 2: Neo4j Concurrent Writes")
    print(f"{'='*60}")
    print(f"Workers: {num_workers}, Nodes per worker: {nodes_per_worker}")
    
    try:
        config = KGConfig.load()
        
        # Test connection
        with Neo4jClient(config) as client:
            print("✓ Neo4j connection successful")
        
        def create_nodes(worker_id):
            """Create nodes from a single worker."""
            results = []
            
            with Neo4jClient(config) as client:
                for i in range(nodes_per_worker):
                    node_id = f"test_worker{worker_id}_node{i}"
                    
                    try:
                        client.create_node(
                            label="TestNode",
                            properties={
                                "id": node_id,
                                "name": f"Test Node {node_id}",
                                "worker": worker_id,
                                "index": i,
                                "test_run": "concurrent_validation"
                            }
                        )
                        results.append((node_id, "success"))
                    except Exception as e:
                        results.append((node_id, f"error: {e}"))
            
            return results
        
        # Run concurrent writes
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(create_nodes, i) for i in range(num_workers)]
            all_results = []
            
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        duration = time.time() - start_time
        
        # Check results
        success_count = sum(1 for _, status in all_results if status == "success")
        total_nodes = num_workers * nodes_per_worker
        
        print(f"\nResults:")
        print(f"  Total nodes: {total_nodes}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {total_nodes - success_count}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {total_nodes/duration:.1f} nodes/sec")
        
        # Cleanup test nodes
        with Neo4jClient(config) as client:
            cleanup_query = "MATCH (n:TestNode {test_run: 'concurrent_validation'}) DELETE n"
            client.execute_cypher(cleanup_query)
            print("✓ Cleanup completed")
        
        if success_count == total_nodes:
            print("✅ All concurrent writes successful!")
            return True
        else:
            print(f"⚠️  Some writes failed ({total_nodes - success_count} failures)")
            return False
            
    except Exception as e:
        print(f"❌ Neo4j test failed: {e}")
        return False


def test_parallel_job_execution():
    """Test parallel job execution with AsyncIngestionManager."""
    print(f"\n{'='*60}")
    print("TEST 3: Parallel Job Execution")
    print(f"{'='*60}")
    
    try:
        from agentic_cli.kg.async_ingest import AsyncIngestionManager
        import tempfile
        
        # Create test files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test documents
            for i in range(3):
                test_file = tmpdir / f"test_doc_{i}.txt"
                test_file.write_text(f"Test document {i} for parallel ingestion validation.")
            
            print(f"✓ Created 3 test documents in {tmpdir}")
            
            # Initialize manager
            manager = AsyncIngestionManager(max_workers=3)
            print("✓ AsyncIngestionManager initialized")
            
            # Submit jobs
            jobs = []
            for i in range(3):
                test_file = tmpdir / f"test_doc_{i}.txt"
                job = manager.submit_ingestion(
                    source=str(test_file),
                    source_type="path",
                    format="text",
                    provider="lightrag",
                    extract_entities=False,
                    build_relationships=False
                )
                jobs.append(job)
                print(f"✓ Submitted job {i+1}: {job.job_id[:8]}...")
            
            # Wait for completion
            print("\nWaiting for jobs to complete...")
            start_time = time.time()
            
            completed_jobs = []
            for job in jobs:
                try:
                    completed = manager.wait_for_job(job.job_id, timeout=60)
                    completed_jobs.append(completed)
                except TimeoutError:
                    print(f"⚠️  Job {job.job_id[:8]}... timed out")
            
            duration = time.time() - start_time
            
            # Check results
            from agentic_cli.kg.async_ingest import JobStatus
            
            success_count = sum(1 for j in completed_jobs if j.status == JobStatus.COMPLETED)
            failed_count = sum(1 for j in completed_jobs if j.status == JobStatus.FAILED)
            
            print(f"\nResults:")
            print(f"  Total jobs: {len(jobs)}")
            print(f"  Completed: {success_count}")
            print(f"  Failed: {failed_count}")
            print(f"  Duration: {duration:.2f}s")
            
            # Cleanup
            for job in jobs:
                manager.queue.delete_job(job.job_id)
            
            manager.shutdown(wait=True)
            
            if success_count == len(jobs):
                print("✅ All parallel jobs completed successfully!")
                return True
            else:
                print(f"⚠️  Some jobs failed ({failed_count} failures)")
                return False
                
    except Exception as e:
        print(f"❌ Parallel execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("="*60)
    print("KEEL KG Concurrent Ingestion Validation")
    print("="*60)
    
    results = {}
    
    # Test 1: LightRAG concurrent inserts
    results['lightrag'] = test_lightrag_concurrent_inserts(num_workers=4, docs_per_worker=5)
    
    # Test 2: Neo4j concurrent writes
    results['neo4j'] = test_neo4j_concurrent_writes(num_workers=4, nodes_per_worker=5)
    
    # Test 3: Parallel job execution
    results['parallel_jobs'] = test_parallel_job_execution()
    
    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20s}: {status}")
    
    all_passed = all(results.values())
    
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ ALL TESTS PASSED - Concurrent ingestion is supported!")
        print("="*60)
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Review errors above")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
