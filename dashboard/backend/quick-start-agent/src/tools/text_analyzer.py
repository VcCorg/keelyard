"""Text analyzer tool."""

def analyze_text(text: str) -> dict:
    """Analyze text and return statistics."""
    words = text.split()
    return {
        "char_count": len(text),
        "word_count": len(words),
        "sentence_count": text.count('.') + text.count('!') + text.count('?'),
        "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
    }
