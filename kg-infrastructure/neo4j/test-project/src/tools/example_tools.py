"""Example tools that agents can use."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculator(expression: str) -> Dict[str, Any]:
    """
    Simple calculator tool for agents.

    Args:
        expression: Mathematical expression to evaluate

    Returns:
        Dictionary with result or error
    """
    try:
        # Safe evaluation (limited to basic math)
        result = eval(expression, {"__builtins__": {}}, {})
        logger.info(f"Calculator: {expression} = {result}")
        return {
            "success": True,
            "expression": expression,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Calculator error: {e}")
        return {
            "success": False,
            "expression": expression,
            "error": str(e),
        }


def text_analyzer(text: str) -> Dict[str, Any]:
    """
    Analyze text and return statistics.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with text statistics
    """
    words = text.split()
    sentences = text.split(".")
    
    stats = {
        "success": True,
        "character_count": len(text),
        "word_count": len(words),
        "sentence_count": len([s for s in sentences if s.strip()]),
        "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
        "unique_words": len(set(word.lower() for word in words)),
    }
    
    logger.info(f"Text analysis: {stats['word_count']} words, {stats['sentence_count']} sentences")
    return stats


# Add more tools as needed
def web_search(query: str) -> Dict[str, Any]:
    """
    Placeholder for web search tool.

    Args:
        query: Search query

    Returns:
        Search results (placeholder)
    """
    logger.info(f"Web search: {query}")
    return {
        "success": True,
        "query": query,
        "results": [
            {"title": "Example Result 1", "url": "https://example.com/1"},
            {"title": "Example Result 2", "url": "https://example.com/2"},
        ],
        "note": "This is a placeholder. Implement actual web search.",
    }


def file_reader(filepath: str) -> Dict[str, Any]:
    """
    Read file contents (with safety checks).

    Args:
        filepath: Path to file

    Returns:
        File contents or error
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"Read file: {filepath}")
        return {
            "success": True,
            "filepath": filepath,
            "content": content,
            "size": len(content),
        }
    except Exception as e:
        logger.error(f"File read error: {e}")
        return {
            "success": False,
            "filepath": filepath,
            "error": str(e),
        }
