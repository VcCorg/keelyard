"""File writer tool."""

from pathlib import Path

def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"Written {len(content)} bytes to {file_path}"
