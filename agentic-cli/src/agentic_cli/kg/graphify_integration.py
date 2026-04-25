"""Graphify integration for enhanced code structure analysis.

This module provides integration with Graphify (https://github.com/safishamsi/graphify)
to generate detailed code structure analysis including relationships, communities,
 and architectural insights.

Graphify complements gitingest by providing:
- Function-level relationships (calls, imports, uses)
- Community detection (code modules)
- Architectural insights (surprises, anomalies)
- Interactive graph exports
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from agentic_cli.analyzer.detector import ProjectAnalysis


def generate_graphify_analysis(
    project_path: Path, 
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Generate code structure analysis using Graphify.
    
    Args:
        project_path: Path to the project directory
        output_dir: Directory to save Graphify outputs (defaults to .skills/project-context)
        
    Returns:
        Dictionary containing Graphify analysis results
        
    Raises:
        ImportError: If Graphify is not installed
        Exception: If Graphify analysis fails
    """
    try:
        import graphify
    except ImportError as e:
        raise ImportError(
            "Graphify not installed. Install with: pip install graphifyy"
        ) from e
    
    if output_dir is None:
        output_dir = project_path / ".skills" / "project-context"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary directory for Graphify output
    with tempfile.TemporaryDirectory(prefix="graphify_") as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Run Graphify analysis
            console.print(f"[dim]Running Graphify analysis on {project_path.name}...[/dim]")
            
            # Graphify pipeline: detect -> extract -> build_graph -> cluster -> analyze
            graph_data = _run_graphify_pipeline(project_path, temp_path)
            
            # Save Graphify outputs for reference
            _save_graphify_outputs(graph_data, output_dir, project_path.name)
            
            return graph_data
            
        except Exception as e:
            console.print(f"[yellow]Graphify analysis failed: {e}[/yellow]")
            raise


def _run_graphify_pipeline(project_path: Path, temp_dir: Path) -> Dict[str, Any]:
    """Run the complete Graphify pipeline."""
    import graphify
    
    # Step 1: Detect files
    files = graphify.detect.collect_files(str(project_path))
    console.print(f"[dim]Graphify detected {len(files)} files[/dim]")
    
    # Step 2: Extract nodes and edges
    extractions = []
    for file_path in files[:50]:  # Limit for performance
        try:
            extraction = graphify.extract.extract(file_path)
            if extraction and (extraction.get("nodes") or extraction.get("edges")):
                extractions.append(extraction)
        except Exception as e:
            console.print(f"[dim]Warning: Failed to extract from {file_path}: {e}[/dim]")
    
    console.print(f"[dim]Extracted data from {len(extractions)} files[/dim]")
    
    # Step 3: Build graph
    graph = graphify.build.build_graph(extractions)
    
    # Step 4: Detect communities
    graph = graphify.cluster.cluster(graph)
    
    # Step 5: Analyze graph
    analysis = graphify.analyze.analyze(graph)
    
    # Step 6: Export results
    outputs = graphify.export.export(
        graph, 
        out_dir=str(temp_dir),
        formats=["json"]
    )
    
    # Combine all results
    result = {
        "files_analyzed": len(extractions),
        "total_files": len(files),
        "nodes": [{"id": n, **graph.nodes[n]} for n in graph.nodes()],
        "edges": [{"source": u, "target": v, **graph[u][v]} for u, v in graph.edges()],
        "communities": _extract_communities(graph),
        "analysis": analysis,
        "outputs": outputs
    }
    
    return result


def _extract_communities(graph) -> list[Dict[str, Any]]:
    """Extract community information from NetworkX graph."""
    communities = []
    
    # Group nodes by community attribute
    community_groups = {}
    for node, data in graph.nodes(data=True):
        community_id = data.get("community", 0)
        if community_id not in community_groups:
            community_groups[community_id] = []
        community_groups[community_id].append({
            "id": node,
            "label": data.get("label", node),
            "type": data.get("type", "unknown")
        })
    
    # Create community summaries
    for comm_id, nodes in community_groups.items():
        if len(nodes) >= 2:  # Only include communities with 2+ nodes
            communities.append({
                "id": comm_id,
                "name": _generate_community_name(nodes),
                "size": len(nodes),
                "nodes": nodes[:5],  # Limit for display
                "has_more": len(nodes) > 5
            })
    
    return sorted(communities, key=lambda c: c["size"], reverse=True)


def _generate_community_name(nodes: list[Dict[str, Any]]) -> str:
    """Generate a meaningful name for a community based on its nodes."""
    # Extract common patterns from node names
    node_names = [n["id"] for n in nodes]
    
    # Common patterns
    patterns = {
        "test": any("test" in name.lower() for name in node_names),
        "api": any("api" in name.lower() for name in node_names),
        "model": any("model" in name.lower() for name in node_names),
        "service": any("service" in name.lower() for name in node_names),
        "util": any("util" in name.lower() for name in node_names),
        "config": any("config" in name.lower() for name in node_names),
        "database": any("db" in name.lower() or "database" in name.lower() for name in node_names),
        "auth": any("auth" in name.lower() for name in node_names),
    }
    
    # Find the most common pattern
    for pattern, present in patterns.items():
        if present:
            return f"{pattern.title()} Module"
    
    # Fallback: use first node's directory
    first_node = node_names[0]
    parts = first_node.split("/")
    if len(parts) > 1:
        return f"{parts[0].title()} Module"
    
    return "Code Module"


def _save_graphify_outputs(
    graph_data: Dict[str, Any], 
    output_dir: Path, 
    project_name: str
) -> None:
    """Save Graphify outputs for reference."""
    
    # Save full graph data
    graph_file = output_dir / "graphify-graph.json"
    graph_file.write_text(json.dumps(graph_data, indent=2))
    
    # Save summary
    summary = {
        "project": project_name,
        "files_analyzed": graph_data["files_analyzed"],
        "total_files": graph_data["total_files"],
        "nodes_count": len(graph_data["nodes"]),
        "edges_count": len(graph_data["edges"]),
        "communities_count": len(graph_data["communities"]),
        "analysis": graph_data.get("analysis", {})
    }
    
    summary_file = output_dir / "graphify-summary.json"
    summary_file.write_text(json.dumps(summary, indent=2))


def format_graphify_insights(
    graph_data: Dict[str, Any], 
    max_items: int = 15
) -> str:
    """Format Graphify analysis for inclusion in KG context document.
    
    Args:
        graph_data: Graphify analysis results
        max_items: Maximum number of items to show per section
        
    Returns:
        Formatted markdown string
    """
    sections = []
    
    # Key Relationships
    edges = graph_data.get("edges", [])
    if edges:
        sections.append("### Key Code Relationships\n")
        
        # Group by relationship type
        relationships = {}
        for edge in edges[:max_items]:
            rel_type = edge.get("relation", "related")
            if rel_type not in relationships:
                relationships[rel_type] = []
            relationships[rel_type].append(
                f"**{edge['source']}** -> **{edge['target']}**"
            )
        
        for rel_type, items in relationships.items():
            sections.append(f"#### {rel_type.title()}\n")
            for item in items[:5]:  # Limit per type
                sections.append(f"- {item}")
            if len(items) > 5:
                sections.append(f"- _... and {len(items) - 5} more_")
            sections.append("")
    
    # Code Communities/Modules
    communities = graph_data.get("communities", [])
    if communities:
        sections.append("### Code Modules\n")
        for community in communities[:8]:  # Limit communities
            name = community["name"]
            size = community["size"]
            nodes = community["nodes"]
            
            sections.append(f"#### {name} ({size} files)\n")
            for node in nodes:
                sections.append(f"- `{node['id']}`")
            if community["has_more"]:
                sections.append(f"- _... and {size - 5} more_")
            sections.append("")
    
    # Architectural Insights
    analysis = graph_data.get("analysis", {})
    if analysis:
        sections.append("### Architectural Insights\n")
        
        # God nodes (highly connected)
        god_nodes = analysis.get("god_nodes", [])
        if god_nodes:
            sections.append("#### Highly Connected Components\n")
            for node in god_nodes[:5]:
                sections.append(f"- `{node}` (many dependencies)")
            sections.append("")
        
        # Surprises/anomalies
        surprises = analysis.get("surprises", [])
        if surprises:
            sections.append("#### Notable Patterns\n")
            for surprise in surprises[:5]:
                sections.append(f"- {surprise}")
            sections.append("")
        
        # Questions for review
        questions = analysis.get("questions", [])
        if questions:
            sections.append("#### Architecture Questions\n")
            for question in questions[:3]:
                sections.append(f"- {question}")
            sections.append("")
    
    # Statistics Summary
    sections.append("### Analysis Statistics\n")
    sections.append(f"- **Files analyzed**: {graph_data.get('files_analyzed', 0)}")
    sections.append(f"- **Total files**: {graph_data.get('total_files', 0)}")
    sections.append(f"- **Code nodes**: {len(graph_data.get('nodes', []))}")
    sections.append(f"- **Relationships**: {len(graph_data.get('edges', []))}")
    sections.append(f"- **Modules detected**: {len(communities)}")
    sections.append("")
    
    return "\n".join(sections)


def is_graphify_available() -> bool:
    """Check if Graphify is available."""
    try:
        import graphify
        return True
    except ImportError:
        return False


def validate_graphify_compatibility(project_path: Path) -> Dict[str, Any]:
    """Validate if project is compatible with Graphify analysis.
    
    Args:
        project_path: Path to project directory
        
    Returns:
        Validation result with recommendations
    """
    result = {
        "compatible": False,
        "reason": "",
        "recommendations": []
    }
    
    # Check if Graphify is installed
    if not is_graphify_available():
        result["reason"] = "Graphify not installed"
        result["recommendations"].append("Install with: pip install graphifyy")
        return result
    
    # Check project size
    try:
        import graphify
        
        files = graphify.detect.collect_files(str(project_path))
        if len(files) > 1000:
            result["compatible"] = False
            result["reason"] = "Project too large"
            result["recommendations"].append(
                f"Consider analyzing a submodule (found {len(files)} files)"
            )
        elif len(files) < 5:
            result["compatible"] = False
            result["reason"] = "Project too small"
            result["recommendations"].append(
                "Graphify works best with projects having 5+ files"
            )
        else:
            result["compatible"] = True
            result["reason"] = f"Suitable for analysis ({len(files)} files)"
            
    except Exception as e:
        result["reason"] = f"Error checking compatibility: {e}"
        result["recommendations"].append("Check project directory permissions")
    
    return result
