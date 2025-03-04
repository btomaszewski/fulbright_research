import unicodedata
import contractions
import re

def clean_text(text: str) -> str:
    """
    Clean text consistently for both training and inference.
    
    This function performs the following operations:
    1. Unicode normalization (NFKC form)
    2. Contraction expansion (e.g., "don't" -> "do not")
    3. Whitespace normalization
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text string
    """
    # Handle None or empty input
    if not text:
        return ""
    
    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)
    
    # Normalize Unicode characters (fix encoding issues)
    text = unicodedata.normalize("NFKC", text)

    # Expand contractions (e.g., "I'm" -> "I am", "don't" -> "do not")
    text = contractions.fix(text)

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text