"""
Default AI prompt configurations for user profiles.
These prompts can be customized by users through their profile settings.
"""

DEFAULT_AI_PROMPTS = {
    "review": "Review this card",
    "generate": "Generate a card",
    "summarize": "Summarize this topic"
}
# Card format prompt for AI card generation
# This prompt instructs AI to return cards in the correct JSON format
CARD_FORMAT_PROMPT = """
# Output Format (STRICT JSON)
You must return a JSON object with a "cards" array. Each card must be one of two types:

1. QA with Hint (qa_hint):
{
  "card_type": "qa_hint",
  "question": "The question text (can include markdown formatting, no big headings)",
  "answer": "The answer text (should include markdown formatting)",
  "hint": "" // Optional hint text (can include markdown formatting)
}

2. Multiple Choice (multiple_choice):
{
  "card_type": "multiple_choice",
  "question": "The question text (can include markdown formatting, no big headings)",
  "choices": ["Option A", "Option B", "Option C", "Option D"],
  "correct_index": 0,
  "explanation": "Explanation of why the correct answer is right and others are wrong (optional, can include markdown formatting)"
}

Return ONLY valid JSON in this format:
{
  "cards": [...]
}
"""