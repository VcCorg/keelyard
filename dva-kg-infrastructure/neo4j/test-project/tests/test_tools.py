"""Tests for agent tools."""

import pytest
from src.tools.example_tools import calculator, text_analyzer, web_search


def test_calculator_success():
    """Test calculator with valid expression."""
    result = calculator("2 + 2")
    assert result["success"] is True
    assert result["result"] == 4


def test_calculator_complex():
    """Test calculator with complex expression."""
    result = calculator("(10 + 5) * 2")
    assert result["success"] is True
    assert result["result"] == 30


def test_calculator_error():
    """Test calculator with invalid expression."""
    result = calculator("invalid")
    assert result["success"] is False
    assert "error" in result


def test_text_analyzer():
    """Test text analyzer."""
    text = "This is a test. It has multiple sentences."
    result = text_analyzer(text)
    
    assert result["success"] is True
    assert result["word_count"] > 0
    assert result["sentence_count"] >= 2
    assert result["character_count"] == len(text)


def test_text_analyzer_empty():
    """Test text analyzer with empty text."""
    result = text_analyzer("")
    assert result["success"] is True
    assert result["word_count"] == 0


def test_web_search():
    """Test web search placeholder."""
    result = web_search("test query")
    assert result["success"] is True
    assert "results" in result
    assert len(result["results"]) > 0
