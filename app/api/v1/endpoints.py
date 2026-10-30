import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.api.v1.schemas import QuizResponse
from app.core.cache import fetch_cached_quiz, set_cached_quiz
from app.services.generator import generate_quiz_with_self_correction

router = APIRouter()

class GenerateQuizRequest(BaseModel):
    topic: str = Field(..., example="Operating Systems")
    num_questions: int = Field(default=3, ge=1, le=10)
    context: str = Field(..., min_length=20)

@router.post("/generate", response_model=QuizResponse)
def generate_quiz(req: GenerateQuizRequest):
    start_time = time.time()
    
    # 1. Check Redis Cache
    cached_payload = fetch_cached_quiz(req.context, req.num_questions, req.topic)
    if cached_payload:
        response = QuizResponse(**cached_payload)
        return response

    # 2. Run Self-Correcting Generator Agent
    try:
        quiz = generate_quiz_with_self_correction(
            context=req.context,
            num_questions=req.num_questions,
            topic=req.topic
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    # 3. Store in Redis (24-hour TTL)
    set_cached_quiz(req.context, req.num_questions, req.topic, quiz.model_dump())

    return quiz
