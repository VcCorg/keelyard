"""Generate tool files."""

from pathlib import Path
from dva_agentic_cli.templates.config import TemplateConfig
from dva_agentic_cli.templates.enums import Tool


TOOL_TEMPLATES = {
    Tool.CALCULATOR: '''"""Calculator tool."""

def calculate(expression: str) -> float:
    """Evaluate a mathematical expression."""
    try:
        return eval(expression, {"__builtins__": {}}, {})
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")
''',
    Tool.TEXT_ANALYZER: '''"""Text analyzer tool."""

def analyze_text(text: str) -> dict:
    """Analyze text and return statistics."""
    words = text.split()
    return {
        "char_count": len(text),
        "word_count": len(words),
        "sentence_count": text.count('.') + text.count('!') + text.count('?'),
        "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
    }
''',
    Tool.FILE_READER: '''"""File reader tool."""

from pathlib import Path

def read_file(file_path: str) -> str:
    """Read and return file contents."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text()
''',
    Tool.FILE_WRITER: '''"""File writer tool."""

from pathlib import Path

def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"Written {len(content)} bytes to {file_path}"
''',
    Tool.WEB_SEARCH: '''"""Web search tool."""

import httpx

async def web_search(query: str, num_results: int = 5) -> list:
    """Search the web for information."""
    # Placeholder - implement with actual search API
    return [{"title": "Result", "url": "https://example.com", "snippet": query}]
''',
    Tool.VECTOR_SEARCH: '''"""Vector search tool."""

def vector_search(query: str, collection: str = "default", top_k: int = 5) -> list:
    """Search for similar documents using vector embeddings."""
    # Placeholder - implement with ChromaDB or similar
    return []
''',
    Tool.DOCUMENT_LOADER: '''"""Document loader tool."""

from pathlib import Path

def load_document(file_path: str) -> dict:
    """Load and parse a document."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    if suffix == ".txt":
        return {"content": path.read_text(), "type": "text"}
    elif suffix == ".pdf":
        # Implement PDF loading
        return {"content": "", "type": "pdf"}
    else:
        return {"content": path.read_text(), "type": "unknown"}
''',
    Tool.KG_QUERY: '''"""Knowledge graph query tool."""

def kg_query(cypher: str) -> list:
    """Execute a Cypher query against Neo4j."""
    # Placeholder - implement with neo4j driver
    return []
''',
    Tool.KG_INGEST: '''"""Knowledge graph ingest tool."""

def kg_ingest(entities: list, relationships: list) -> dict:
    """Ingest entities and relationships into the knowledge graph."""
    # Placeholder - implement with neo4j driver
    return {"entities_created": 0, "relationships_created": 0}
''',
    Tool.MEMORY: '''"""Conversation memory tool with configurable persistence."""

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class BaseMemory(ABC):
    """Abstract base class for memory implementations."""
    
    @abstractmethod
    def add(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to memory."""
        pass
    
    @abstractmethod
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from memory."""
        pass
    
    @abstractmethod
    def get_context(self, limit: int = 10) -> str:
        """Get formatted context string."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all messages."""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search messages containing query."""
        pass


class InMemoryStorage(BaseMemory):
    """In-memory storage (default). Data lost on restart."""
    
    def __init__(self, max_messages: int = 100):
        self.messages: List[Dict[str, Any]] = []
        self.max_messages = max_messages
    
    def add(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def get_context(self, limit: int = 10) -> str:
        recent = self.get_messages(limit)
        return "\\n".join(f"{m['role']}: {m['content']}" for m in recent)
    
    def clear(self) -> None:
        self.messages = []
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        matches = [m for m in self.messages if query_lower in m["content"].lower()]
        return matches[-limit:]


class SQLiteMemory(BaseMemory):
    """SQLite-based persistent memory. Survives restarts."""
    
    def __init__(self, db_path: str = "memory.db", session_id: str = "default"):
        self.db_path = Path(db_path)
        self.session_id = session_id
        self._init_db()
    
    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id)")
    
    def add(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (self.session_id, role, content, datetime.now().isoformat(), json.dumps(metadata or {}))
            )
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT role, content, timestamp, metadata FROM messages WHERE session_id = ? ORDER BY id"
            if limit:
                query += f" DESC LIMIT {limit}"
                rows = conn.execute(query, (self.session_id,)).fetchall()
                rows = list(reversed(rows))
            else:
                rows = conn.execute(query, (self.session_id,)).fetchall()
            return [
                {"role": r[0], "content": r[1], "timestamp": r[2], "metadata": json.loads(r[3])}
                for r in rows
            ]
    
    def get_context(self, limit: int = 10) -> str:
        messages = self.get_messages(limit)
        return "\\n".join(f"{m['role']}: {m['content']}" for m in messages)
    
    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (self.session_id,))
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp, metadata FROM messages WHERE session_id = ? AND content LIKE ? ORDER BY id DESC LIMIT ?",
                (self.session_id, f"%{query}%", limit)
            ).fetchall()
            return [
                {"role": r[0], "content": r[1], "timestamp": r[2], "metadata": json.loads(r[3])}
                for r in reversed(rows)
            ]
    
    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT session_id FROM messages").fetchall()
            return [r[0] for r in rows]


class ConversationMemory:
    """
    Configurable conversation memory.
    
    Usage:
        # In-memory (default)
        memory = ConversationMemory()
        
        # Persistent SQLite
        memory = ConversationMemory(persistent=True, db_path="./data/memory.db")
        
        # With session ID for multi-conversation support
        memory = ConversationMemory(persistent=True, session_id="user-123")
    """
    
    def __init__(
        self,
        persistent: bool = False,
        db_path: str = "memory.db",
        session_id: str = "default",
        max_messages: int = 100,
    ):
        if persistent:
            self._storage = SQLiteMemory(db_path=db_path, session_id=session_id)
        else:
            self._storage = InMemoryStorage(max_messages=max_messages)
        self.persistent = persistent
    
    def add(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to memory."""
        self._storage.add(role, content, metadata)
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from memory."""
        return self._storage.get_messages(limit)
    
    def get_context(self, limit: int = 10) -> str:
        """Get formatted context string for LLM prompts."""
        return self._storage.get_context(limit)
    
    def clear(self) -> None:
        """Clear all messages in current session."""
        self._storage.clear()
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search messages containing query."""
        return self._storage.search(query, limit)
''',
}


def generate_tool_files(tools_dir: Path, config: TemplateConfig) -> None:
    """Generate tool files based on selected tools."""
    for tool in config.tools:
        if tool in TOOL_TEMPLATES:
            filename = f"{tool.value}.py"
            (tools_dir / filename).write_text(TOOL_TEMPLATES[tool])
