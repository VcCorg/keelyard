"""Text analyzer tool for Basic Agent."""

import logging
import re
from typing import Dict, List, Union

from google.adk.tools import Tool

logger = logging.getLogger(__name__)


class TextAnalyzerTool(Tool):
    """A text analyzer tool for analyzing text content."""
    
    def __init__(self) -> None:
        """Initialize the text analyzer tool."""
        super().__init__(
            name="text_analyzer",
            description="A tool for analyzing text content including word count, sentiment, and key phrases",
            parameters={
                "text": {
                    "type": "string",
                    "description": "Text to analyze",
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis to perform (word_count, sentiment, key_phrases, summary)",
                    "default": "word_count",
                }
            },
        )
    
    async def run(self, text: str, analysis_type: str = "word_count") -> Union[Dict[str, Union[int, float, str, List[str]]], str]:
        """Analyze text content.
        
        Args:
            text: Text to analyze
            analysis_type: Type of analysis to perform
            
        Returns:
            Analysis results or error message
        """
        try:
            if not text or not text.strip():
                return "Error: Empty text provided"
            
            text = text.strip()
            
            if analysis_type == "word_count":
                return self._word_count_analysis(text)
            elif analysis_type == "sentiment":
                return self._sentiment_analysis(text)
            elif analysis_type == "key_phrases":
                return self._key_phrases_analysis(text)
            elif analysis_type == "summary":
                return self._summary_analysis(text)
            else:
                return f"Error: Unknown analysis type '{analysis_type}'. Available: word_count, sentiment, key_phrases, summary"
                
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return f"Error: Could not analyze text - {str(e)}"
    
    def _word_count_analysis(self, text: str) -> Dict[str, Union[int, float]]:
        """Perform word count analysis."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        characters = len(text)
        characters_no_spaces = len(text.replace(' ', ''))
        
        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "character_count": characters,
            "character_count_no_spaces": characters_no_spaces,
            "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "average_sentence_length": len(words) / len(sentences) if sentences else 0,
        }
    
    def _sentiment_analysis(self, text: str) -> Dict[str, Union[str, float]]:
        """Perform basic sentiment analysis."""
        # Simple sentiment analysis based on positive and negative words
        positive_words = {
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'love', 'like', 'enjoy', 'happy', 'pleased', 'satisfied', 'delighted'
        }
        negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'angry',
            'sad', 'disappointed', 'frustrated', 'annoyed', 'upset', 'worried'
        }
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            sentiment = "neutral"
            score = 0.0
        else:
            score = (positive_count - negative_count) / total_sentiment_words
            if score > 0.1:
                sentiment = "positive"
            elif score < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "score": score,
            "positive_words": positive_count,
            "negative_words": negative_count,
        }
    
    def _key_phrases_analysis(self, text: str) -> Dict[str, List[str]]:
        """Extract key phrases from text."""
        # Simple key phrase extraction based on common patterns
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Extract noun phrases (simple heuristic)
        key_phrases = []
        for sentence in sentences:
            # Look for patterns like "adjective noun" or "noun noun"
            words = sentence.split()
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                # Simple heuristic: if first word is capitalized or second word is a noun
                if (words[i][0].isupper() or words[i+1].lower() in ['system', 'process', 'method', 'tool', 'data', 'result']):
                    key_phrases.append(phrase)
        
        # Remove duplicates and limit to top 10
        key_phrases = list(set(key_phrases))[:10]
        
        return {
            "key_phrases": key_phrases,
            "phrase_count": len(key_phrases),
        }
    
    def _summary_analysis(self, text: str) -> Dict[str, str]:
        """Generate a basic summary of the text."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 3:
            summary = " ".join(sentences)
        else:
            # Simple extractive summary: take first and last sentences, plus one middle sentence
            middle_idx = len(sentences) // 2
            summary_sentences = [sentences[0], sentences[middle_idx], sentences[-1]]
            summary = " ".join(summary_sentences)
        
        return {
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / len(text) if text else 0,
        }
