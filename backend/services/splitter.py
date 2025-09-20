from typing import List
import re

def split_prompt(user_query: str) -> List[str]:
    """
    A simple prompt splitter.
    
    This implementation splits a query by sentences.
    A more advanced version could use NLP libraries like spaCy or NLTK
    to split based on clauses, questions, or logical units.
    
    Args:
        user_query: The raw query string from the user.
        
    Returns:
        A list of non-empty micro-prompts.
    """
    if not user_query:
        return []
    
    # Split by periods, question marks, and exclamation marks, followed by a space.
    # The regex keeps the delimiters.
    sentences = re.split(r'(?<=[.?!])\s+', user_query)
    
    # Filter out any empty strings that might result from the split
    return [sentence.strip() for sentence in sentences if sentence.strip()]

