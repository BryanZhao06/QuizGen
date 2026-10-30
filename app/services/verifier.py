import re
from typing import Tuple
from app.api.v1.schemas import GeneratedQuestion

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())

def verify_question_grounding(question: GeneratedQuestion, source_context: str) -> Tuple[bool, str]:
    option_labels = [opt.label.upper().strip() for opt in question.options]
    if question.correct_option.upper().strip() not in option_labels:
        return False, f"Correct option '{question.correct_option}' is not among choices {option_labels}."

    option_texts = [clean_text(opt.text) for opt in question.options]
    if len(set(option_texts)) < len(option_texts):
        return False, "Duplicate options detected in the generated choices."

    normalized_context = clean_text(source_context)
    normalized_quote = clean_text(question.source_quote)

    if not normalized_quote or len(normalized_quote) < 10:
        return False, "Source citation quote is empty or too short to verify grounding."

    if normalized_quote not in normalized_context:
        quote_words = set(normalized_quote.split())
        context_words = set(normalized_context.split())
        overlap_ratio = len(quote_words & context_words) / len(quote_words)
        
        if overlap_ratio < 0.85:
            return False, f"Citation quote '{question.source_quote[:50]}...' cannot be grounded in the context."

    return True, "Passed"
