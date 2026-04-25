#!/usr/bin/env python3
"""
Comprehensive test script for external registry functionality.

This script tests the complete workflow of the external agent template
and agent tool registry system.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List

def run_command(cmd: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {' '.join(cmd)}")
        return None
    except Exception as e:
        print(f"Error running command: {e}")
        return None

def test_agent_template_registry():
    """Test agent template registry functionality."""
    print("Testing Agent Template Registry...")
    
    # Test listing templates
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-template", "list", "--registry", "local-agent-templates"
    ])
    assert result.returncode == 0, f"Failed to list templates: {result.stderr}"
    assert "adk-basic-agent" in result.stdout, "Basic agent template not found"
    
    # Test showing template details
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-template", "show", "adk-basic-agent", "--registry", "local-agent-templates"
    ])
    assert result.returncode == 0, f"Failed to show template: {result.stderr}"
    assert "Basic agent template using Google ADK framework" in result.stdout, "Template description not found"
    
    # Test listing frameworks
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-template", "frameworks", "--registry", "local-agent-templates"
    ])
    assert result.returncode == 0, f"Failed to list frameworks: {result.stderr}"
    assert "adk" in result.stdout, "ADK framework not found"
    
    # Test listing use cases
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-template", "use-cases", "--registry", "local-agent-templates"
    ])
    assert result.returncode == 0, f"Failed to list use cases: {result.stderr}"
    assert "basic" in result.stdout, "Basic use case not found"
    
    print("  Agent Template Registry tests passed!")

def test_agent_tool_registry():
    """Test agent tool registry functionality."""
    print("Testing Agent Tool Registry...")
    
    # Test listing tools
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-tool", "list", "--registry", "local-agent-tools"
    ])
    assert result.returncode == 0, f"Failed to list tools: {result.stderr}"
    assert "jira-integration" in result.stdout, "Jira integration tool not found"
    
    # Test showing tool details
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-tool", "show", "jira-integration", "--registry", "local-agent-tools"
    ])
    assert result.returncode == 0, f"Failed to show tool: {result.stderr}"
    assert "Tool for integrating with Jira for issue tracking" in result.stdout, "Tool description not found"
    
    # Test listing categories
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-tool", "categories", "--registry", "local-agent-tools"
    ])
    assert result.returncode == 0, f"Failed to list categories: {result.stderr}"
    assert "integrations" in result.stdout, "Integrations category not found"
    
    print("  Agent Tool Registry tests passed!")

def test_project_creation():
    """Test project creation with external templates and tools."""
    print("Testing Project Creation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test project creation with external template only
        result = run_command([
            "python", "-m", "agentic_cli.main", 
            "project", "create", "test-template-only",
            "--agent-template", "adk-basic-agent",
            "--force"
        ], cwd=temp_path)
        
        assert result.returncode == 0, f"Failed to create project with template: {result.stderr}"
        assert "Template 'adk-basic-agent' installed successfully" in result.stdout
        
        project_path = temp_path / "test-template-only"
        assert project_path.exists(), "Project directory not created"
        assert (project_path / "src").exists(), "Source directory not created"
        assert (project_path / "pyproject.toml").exists(), "pyproject.toml not created"
        
        # Clean up
        shutil.rmtree(project_path)
        
        # Test project creation with external template and tools
        result = run_command([
            "python", "-m", "agentic_cli.main", 
            "project", "create", "test-full-external",
            "--agent-template", "adk-basic-agent",
            "--agent-tools", "jira-integration",
            "--force"
        ], cwd=temp_path)
        
        assert result.returncode == 0, f"Failed to create project with template and tools: {result.stderr}"
        assert "Template 'adk-basic-agent' installed successfully" in result.stdout
        assert "Tool 'jira-integration' installed successfully" in result.stdout
        
        project_path = temp_path / "test-full-external"
        assert project_path.exists(), "Project directory not created"
        assert (project_path / "src" / "tools" / "jira-integration").exists(), "Tool not installed"
        
        print("  Project Creation tests passed!")

def test_registry_management():
    """Test registry management functionality."""
    print("Testing Registry Management...")
    
    # Test listing registries
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-template", "registry", "list"
    ])
    assert result.returncode == 0, f"Failed to list agent template registries: {result.stderr}"
    assert "local-agent-templates" in result.stdout, "Local agent templates registry not found"
    
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-tool", "registry", "list"
    ])
    assert result.returncode == 0, f"Failed to list agent tool registries: {result.stderr}"
    assert "local-agent-tools" in result.stdout, "Local agent tools registry not found"
    
    print("  Registry Management tests passed!")

def test_error_handling():
    """Test error handling scenarios."""
    print("Testing Error Handling...")
    
    # Test invalid template name
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-template", "show", "invalid-template", "--registry", "local-agent-templates"
    ])
    assert result.returncode != 0, "Should have failed for invalid template"
    assert "not found" in result.stdout.lower(), "Should show not found message"
    
    # Test invalid tool name
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-tool", "show", "invalid-tool", "--registry", "local-agent-tools"
    ])
    assert result.returncode != 0, "Should have failed for invalid tool"
    assert "not found" in result.stdout.lower(), "Should show not found message"
    
    # Test invalid registry name
    result = run_command([
        "python", "-m", "agentic_cli.main", 
        "agent-template", "list", "--registry", "invalid-registry"
    ])
    assert result.returncode != 0, "Should have failed for invalid registry"
    assert "not found" in result.stdout.lower(), "Should show not found message"
    
    print("  Error Handling tests passed!")

def main():
    """Run all tests."""
    print("Starting External Registry Tests...")
    print("=" * 50)
    
    try:
        test_agent_template_registry()
        test_agent_tool_registry()
        test_project_creation()
        test_registry_management()
        test_error_handling()
        
        print("=" * 50)
        print("All tests passed! External registry system is working correctly.")
        
    except AssertionError as e:
        print(f"Test failed: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
