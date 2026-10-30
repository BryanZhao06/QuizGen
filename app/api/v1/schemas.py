from pydantic import BaseModel, Field
from typing import List

class QuestionOption(BaseModel):
    label: str = Field(..., description="Option label, e.g., 'A', 'B', 'C', 'D'")
    text: str = Field(..., description="The option answer text")

class GeneratedQuestion(BaseModel):
    question_text: str
    options: List[QuestionOption] = Field(..., min_length=4, max_length=4)
    correct_option: str = Field(..., description="The label corresponding to the correct answer (e.g. 'A')")
    explanation: str = Field(..., description="Detailed rationale explaining why the answer is correct")
    source_quote: str = Field(..., description="Exact substring from the source context supporting the answer")
    difficulty: str = Field(..., description="'easy', 'medium', or 'hard'")

class QuizResponse(BaseModel):
    quiz_id: str
    topic: str
    total_questions: int
    questions: List[GeneratedQuestion]
