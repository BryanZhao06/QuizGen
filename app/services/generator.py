import json
import time
import uuid
import os
from typing import List
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError
from app.api.v1.schemas import QuizResponse, GeneratedQuestion
from app.services.verifier import verify_question_grounding

# Ensure environment variables are loaded
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.5-flash-lite"

SYSTEM_INSTRUCTION = """
You are an expert educational assessment engine.
Your task is to generate rigorous, highly objective multiple-choice questions from the provided text.
Guidelines:
1. Every question must be fully grounded in the provided source text.
2. Provide an exact 'source_quote' directly extracted from the text that proves the correct answer.
3. Distractors (wrong answers) must be plausible but unambiguously incorrect based on the text.
4. Provide exactly 4 options labeled A, B, C, D.
"""

def generate_question_batch(context: str, num_questions: int, topic: str = "General", max_retries: int = 4) -> List[GeneratedQuestion]:
    prompt = f"Topic: {topic}\nTarget Count: {num_questions}\n\nSource Material:\n{context}"
    delay = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    response_mime_type="application/json",
                    response_schema=QuizResponse,
                )
            )
            quiz_data = json.loads(response.text)
            parsed_quiz = QuizResponse(**quiz_data)
            return parsed_quiz.questions
        except (ServerError, APIError) as e:
            if attempt == max_retries:
                raise e
            print(f"    [Generation Retry] Transient error ({e.__class__.__name__}). Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2

def regenerate_single_question(context: str, failed_question: GeneratedQuestion, error_reason: str, max_retries: int = 3) -> GeneratedQuestion:
    refinement_prompt = f"""
The following generated question failed our verification audit:
Question: {failed_question.question_text}
Reported Error: {error_reason}

Source Context:
{context}

Please regenerate a replacement question that resolves this error. Ensure 'source_quote' exists verbatim in the text.
"""
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=refinement_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=GeneratedQuestion,
                )
            )
            question_data = json.loads(response.text)
            return GeneratedQuestion(**question_data)
        except (ServerError, APIError) as e:
            if attempt == max_retries:
                raise e
            time.sleep(delay)
            delay *= 2

def generate_quiz_with_self_correction(context: str, num_questions: int, topic: str = "General", max_retries: int = 2) -> QuizResponse:
    raw_questions = generate_question_batch(context, num_questions, topic)
    validated_questions: List[GeneratedQuestion] = []

    for q in raw_questions:
        is_valid, reason = verify_question_grounding(q, context)
        
        retries = 0
        current_q = q
        while not is_valid and retries < max_retries:
            retries += 1
            current_q = regenerate_single_question(context, current_q, reason)
            is_valid, reason = verify_question_grounding(current_q, context)

        if is_valid:
            validated_questions.append(current_q)

    return QuizResponse(
        quiz_id=str(uuid.uuid4()),
        topic=topic,
        total_questions=len(validated_questions),
        questions=validated_questions
    )
