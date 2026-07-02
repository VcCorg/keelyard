"""File reader tool."""

from pathlib import Path

def read_file(file_path: str) -> str:
    """Read and return file contents."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text()
