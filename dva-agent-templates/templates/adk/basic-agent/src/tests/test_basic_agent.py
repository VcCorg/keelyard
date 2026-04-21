"""Tests for Basic Agent."""

import pytest
from unittest.mock import AsyncMock, patch

from basic_agent.agents.basic_agent import BasicAgent
from basic_agent.tools.calculator import CalculatorTool
from basic_agent.tools.text_analyzer import TextAnalyzerTool
from basic_agent.tools.file_reader import FileReaderTool


class TestCalculatorTool:
    """Test cases for CalculatorTool."""
    
    def test_init(self):
        """Test calculator tool initialization."""
        tool = CalculatorTool()
        assert tool.name == "calculator"
        assert "mathematical operations" in tool.description
    
    @pytest.mark.asyncio
    async def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        tool = CalculatorTool()
        
        # Addition
        result = await tool.run("15 + 23")
        assert result == 38.0
        
        # Multiplication
        result = await tool.run("5 * 6")
        assert result == 30.0
        
        # Division
        result = await tool.run("100 / 4")
        assert result == 25.0
    
    @pytest.mark.asyncio
    async def test_power_operations(self):
        """Test power operations."""
        tool = CalculatorTool()
        
        # Power with ^ (converted to **)
        result = await tool.run("2^3")
        assert result == 8.0
        
        # Power with **
        result = await tool.run("3**2")
        assert result == 9.0
    
    @pytest.mark.asyncio
    async def test_functions(self):
        """Test mathematical functions."""
        tool = CalculatorTool()
        
        # Absolute value
        result = await tool.run("abs(-5)")
        assert result == 5.0
        
        # Square root (converted to **0.5)
        result = await tool.run("sqrt(16)")
        assert result == 4.0
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling."""
        tool = CalculatorTool()
        
        # Invalid expression
        result = await tool.run("invalid expression")
        assert "Error:" in result
        
        # Division by zero
        result = await tool.run("5 / 0")
        assert "Error:" in result


class TestTextAnalyzerTool:
    """Test cases for TextAnalyzerTool."""
    
    def test_init(self):
        """Test text analyzer tool initialization."""
        tool = TextAnalyzerTool()
        assert tool.name == "text_analyzer"
        assert "analyzing text content" in tool.description
    
    @pytest.mark.asyncio
    async def test_word_count_analysis(self):
        """Test word count analysis."""
        tool = TextAnalyzerTool()
        text = "Hello world! This is a test sentence."
        
        result = await tool.run(text, "word_count")
        
        assert result["word_count"] == 7
        assert result["sentence_count"] == 2
        assert result["character_count"] == len(text)
        assert result["character_count_no_spaces"] == len(text.replace(" ", ""))
        assert result["average_word_length"] > 0
        assert result["average_sentence_length"] > 0
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self):
        """Test sentiment analysis."""
        tool = TextAnalyzerTool()
        
        # Positive sentiment
        positive_text = "This is a great and amazing product!"
        result = await tool.run(positive_text, "sentiment")
        assert result["sentiment"] == "positive"
        assert result["score"] > 0
        assert result["positive_words"] > 0
        
        # Negative sentiment
        negative_text = "This is terrible and awful."
        result = await tool.run(negative_text, "sentiment")
        assert result["sentiment"] == "negative"
        assert result["score"] < 0
        assert result["negative_words"] > 0
        
        # Neutral sentiment
        neutral_text = "This is a statement about the system."
        result = await tool.run(neutral_text, "sentiment")
        assert result["sentiment"] == "neutral"
    
    @pytest.mark.asyncio
    async def test_key_phrases_analysis(self):
        """Test key phrases analysis."""
        tool = TextAnalyzerTool()
        text = "The System process uses a new Method for data analysis."
        
        result = await tool.run(text, "key_phrases")
        
        assert "key_phrases" in result
        assert "phrase_count" in result
        assert isinstance(result["key_phrases"], list)
    
    @pytest.mark.asyncio
    async def test_summary_analysis(self):
        """Test summary analysis."""
        tool = TextAnalyzerTool()
        text = "This is the first sentence. This is the middle sentence. This is the last sentence."
        
        result = await tool.run(text, "summary")
        
        assert "summary" in result
        assert "original_length" in result
        assert "summary_length" in result
        assert "compression_ratio" in result
        assert len(result["summary"]) <= len(text)
    
    @pytest.mark.asyncio
    async def test_empty_text(self):
        """Test empty text handling."""
        tool = TextAnalyzerTool()
        
        result = await tool.run("", "word_count")
        assert "Error:" in result
        
        result = await tool.run("   ", "word_count")
        assert "Error:" in result


class TestFileReaderTool:
    """Test cases for FileReaderTool."""
    
    def test_init(self):
        """Test file reader tool initialization."""
        tool = FileReaderTool()
        assert tool.name == "file_reader"
        assert "reading file contents" in tool.description
    
    @pytest.mark.asyncio
    async def test_get_file_type(self):
        """Test file type detection."""
        tool = FileReaderTool()
        
        assert tool._get_file_type('.txt') == 'text'
        assert tool._get_file_type('.py') == 'python'
        assert tool._get_file_type('.json') == 'json'
        assert tool._get_file_type('.unknown') == 'unknown'
    
    def test_list_directory(self):
        """Test directory listing."""
        tool = FileReaderTool()
        
        # Test with current directory
        result = tool.list_directory('.')
        
        assert "directory" in result
        assert "files" in result
        assert "directories" in result
        assert "total_files" in result
        assert "total_directories" in result
        assert isinstance(result["files"], list)
        assert isinstance(result["directories"], list)


class TestBasicAgent:
    """Test cases for BasicAgent."""
    
    @patch('basic_agent.agents.basic_agent.aiplattform.init')
    def test_init_without_config(self, mock_init):
        """Test agent initialization without proper configuration."""
        # This test would require mocking the settings
        # For now, we'll test the structure
        with patch('basic_agent.agents.basic_agent.settings') as mock_settings:
            mock_settings.is_configured = False
            
            with pytest.raises(Exception):
                BasicAgent()
    
    def test_get_tool_names(self):
        """Test getting tool names."""
        # Mock the agent to avoid initialization issues
        with patch('basic_agent.agents.basic_agent.BasicAgent._initialize'):
            agent = BasicAgent()
            agent.tools = [
                CalculatorTool(),
                TextAnalyzerTool(),
                FileReaderTool(),
            ]
            
            tool_names = agent.get_tool_names()
            assert "calculator" in tool_names
            assert "text_analyzer" in tool_names
            assert "file_reader" in tool_names
            assert len(tool_names) == 3
    
    def test_get_agent_info(self):
        """Test getting agent information."""
        # Mock the agent to avoid initialization issues
        with patch('basic_agent.agents.basic_agent.BasicAgent._initialize'):
            agent = BasicAgent()
            agent.tools = [CalculatorTool()]
            
            info = agent.get_agent_info()
            
            assert "name" in info
            assert "description" in info
            assert "model" in info
            assert "project" in info
            assert "location" in info
            assert "tools" in info
            assert "configured" in info
