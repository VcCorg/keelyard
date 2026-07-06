#!/usr/bin/env python3
"""
Example demonstrating data source integration with knowledge graph ingestion.

This example shows how to:
1. Configure data sources using 'keel data create'
2. Ingest data using configured sources with 'keel kg ingest --source'
3. Compare with direct path ingestion
"""

import subprocess
import tempfile
from pathlib import Path

def run_command(cmd: str) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr

def main():
    """Demonstrate data source integration."""
    
    print("🚀 KEEL Data Source Integration Example")
    print("=" * 50)
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("""
        # Sample Document
        
        This is a sample document for testing data source integration.
        
        ## People
        - John Smith works at Acme Corp
        - Jane Doe is a researcher at Tech University
        
        ## Organizations
        - Acme Corp is a technology company
        - Tech University conducts AI research
        
        ## Concepts
        - Artificial Intelligence is transforming industries
        - Machine Learning enables intelligent automation
        """)
        temp_file = Path(f.name)
    
    try:
        print(f"📄 Created test file: {temp_file}")
        
        # Step 1: Configure a data source
        print("\n1️⃣ Configuring data source...")
        cmd = f'keel data create --name test-docs --source-type doc --source-location {temp_file.parent} --description "Test documents for integration"'
        exit_code, stdout, stderr = run_command(cmd)
        
        if exit_code == 0:
            print("✅ Data source configured successfully")
        else:
            print(f"❌ Failed to configure data source: {stderr}")
            return
        
        # Step 2: List data sources
        print("\n2️⃣ Listing configured data sources...")
        exit_code, stdout, stderr = run_command("keel data list")
        if exit_code == 0:
            print("📋 Configured data sources:")
            print(stdout)
        
        # Step 3: Show data source details
        print("\n3️⃣ Showing data source details...")
        exit_code, stdout, stderr = run_command("keel data show test-docs")
        if exit_code == 0:
            print("🔍 Data source details:")
            print(stdout)
        
        # Step 4: Demonstrate ingestion methods
        print("\n4️⃣ Knowledge Graph Ingestion Methods:")
        print("\n📝 Method 1: Direct path ingestion")
        print(f"Command: keel kg ingest --path {temp_file}")
        print("   - Directly specify file path")
        print("   - Good for one-off ingestion")
        
        print("\n📝 Method 2: Data source ingestion")
        print("Command: keel kg ingest --source test-docs")
        print("   - Use configured data source")
        print("   - Good for repeated ingestion")
        print("   - Centralized configuration")
        
        # Step 5: Show integration benefits
        print("\n5️⃣ Integration Benefits:")
        print("✨ Centralized configuration management")
        print("✨ Reusable data source definitions")
        print("✨ Support for multiple source types (local, GCS, Confluence)")
        print("✨ Consistent metadata and tagging")
        print("✨ Easy source discovery with 'keel data list'")
        
        # Step 6: Cleanup
        print("\n6️⃣ Cleaning up...")
        exit_code, stdout, stderr = run_command("keel data delete test-docs --yes")
        if exit_code == 0:
            print("🧹 Data source removed successfully")
        
    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            print(f"🗑️  Removed test file: {temp_file}")
    
    print("\n🎉 Example completed!")
    print("\nNext steps:")
    print("1. Configure your own data sources with 'keel data create'")
    print("2. Set up Neo4j and configure 'keel kg init'")
    print("3. Ingest data with 'keel kg ingest --source <name>'")
    print("4. Query and search your knowledge graph!")

if __name__ == "__main__":
    main()
