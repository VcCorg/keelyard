"""File reader tool for Basic Agent."""

import logging
import os
from pathlib import Path
from typing import Dict, Union

from google.adk.tools import Tool

logger = logging.getLogger(__name__)


class FileReaderTool(Tool):
    """A file reader tool for reading file contents."""
    
    def __init__(self) -> None:
        """Initialize the file reader tool."""
        super().__init__(
            name="file_reader",
            description="A tool for reading file contents from the local filesystem",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8",
                },
                "max_size": {
                    "type": "integer",
                    "description": "Maximum file size in bytes (default: 1MB)",
                    "default": 1048576,
                }
            },
        )
    
    async def run(self, file_path: str, encoding: str = "utf-8", max_size: int = 1048576) -> Union[Dict[str, Union[str, int, bool]], str]:
        """Read file contents.
        
        Args:
            file_path: Path to the file to read
            encoding: File encoding
            max_size: Maximum file size in bytes
            
        Returns:
            File contents and metadata or error message
        """
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                return f"Error: File '{file_path}' does not exist"
            
            # Check if it's a file (not directory)
            if not path.is_file():
                return f"Error: '{file_path}' is not a file"
            
            # Check file size
            file_size = path.stat().st_size
            if file_size > max_size:
                return f"Error: File '{file_path}' is too large ({file_size} bytes > {max_size} bytes)"
            
            # Read file content
            try:
                content = path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                return f"Error: Could not decode file '{file_path}' with encoding '{encoding}'"
            
            # Determine file type
            file_extension = path.suffix.lower()
            file_type = self._get_file_type(file_extension)
            
            return {
                "content": content,
                "file_path": str(path.absolute()),
                "file_name": path.name,
                "file_size": file_size,
                "file_type": file_type,
                "encoding": encoding,
                "line_count": content.count('\n') + 1 if content else 0,
                "character_count": len(content),
                "is_binary": False,
            }
            
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {e}")
            return f"Error: Could not read file '{file_path}' - {str(e)}"
    
    def _get_file_type(self, extension: str) -> str:
        """Get file type based on extension."""
        type_map = {
            '.txt': 'text',
            '.md': 'markdown',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.sh': 'shell',
            '.csv': 'csv',
            '.log': 'log',
            '.conf': 'config',
            '.ini': 'config',
            '.toml': 'toml',
        }
        return type_map.get(extension, 'unknown')
    
    def list_directory(self, directory_path: str) -> Union[Dict[str, list], str]:
        """List files in a directory.
        
        Args:
            directory_path: Path to the directory to list
            
        Returns:
            Directory contents or error message
        """
        try:
            path = Path(directory_path)
            
            if not path.exists():
                return f"Error: Directory '{directory_path}' does not exist"
            
            if not path.is_dir():
                return f"Error: '{directory_path}' is not a directory"
            
            files = []
            directories = []
            
            for item in path.iterdir():
                if item.is_file():
                    files.append({
                        "name": item.name,
                        "size": item.stat().st_size,
                        "type": self._get_file_type(item.suffix.lower()),
                    })
                elif item.is_dir():
                    directories.append({
                        "name": item.name,
                        "item_count": len(list(item.iterdir())),
                    })
            
            return {
                "directory": str(path.absolute()),
                "files": files,
                "directories": directories,
                "total_files": len(files),
                "total_directories": len(directories),
            }
            
        except Exception as e:
            logger.error(f"Error listing directory '{directory_path}': {e}")
            return f"Error: Could not list directory '{directory_path}' - {str(e)}"
