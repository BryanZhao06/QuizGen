import json
import os
import time
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError, ClientError
from app.services.generator import generate_quiz_with_self_correction

client = genai.Client()

class QuestionAudit(BaseModel):
    question_index: int
    is_faithful: bool = Field(..., description="True if question and answer are strictly supported by the text with zero hallucinated facts.")
    is_unambiguous: bool = Field(..., description="True if exactly one option is logically correct based on the text.")
    feedback: str

class BatchJudgeEvaluation(BaseModel):
    audits: List[QuestionAudit]

def judge_quiz_batch(questions: list, context: str, max_retries: int = 3) -> BatchJudgeEvaluation:
    """Evaluates an entire quiz in a single LLM call to conserve API quota."""
    serialized_q = []
    for idx, q in enumerate(questions, start=1):
        serialized_q.append({
            "question_index": idx,
            "question_text": q.question_text,
            "options": [opt.model_dump() for opt in q.options],
            "correct_option": q.correct_option,
            "source_quote": q.source_quote
        })

    prompt = f"""
Evaluate all generated multiple-choice questions against the reference context.

Reference Context:
{context}

Questions to Audit:
{json.dumps(serialized_q, indent=2)}

For each question:
1. Verify faithfulness (is it 100% grounded in the text?).
2. Verify unambiguity (is exactly one choice correct?).
"""
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a strict, adversarial academic evaluator auditing quiz quality.",
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=BatchJudgeEvaluation,
                )
            )
            data = json.loads(response.text)
            return BatchJudgeEvaluation(**data)
        except (ServerError, APIError) as e:
            if attempt == max_retries:
                raise e
            time.sleep(delay)
            delay *= 2

def run_benchmarks(dataset_path: str = "benchmarks/golden_dataset.json"):
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    total_questions = 0
    faithful_count = 0
    unambiguous_count = 0

    print(f"\n================ STARTING EVALUATION BENCHMARK ================")
    print(f"Loaded {len(samples)} benchmark documents (Batch Mode: 2 calls/doc).\n")

    for idx, sample in enumerate(samples, start=1):
        print(f"[{idx}/{len(samples)}] Testing '{sample['topic']}'...")
        
        quiz = generate_quiz_with_self_correction(
            context=sample["context"],
            num_questions=3,
            topic=sample["topic"]
        )

        # Single batch judge call per document
        time.sleep(1.0)
        batch_audit = judge_quiz_batch(quiz.questions, sample["context"])

        for audit in batch_audit.audits:
            total_questions += 1
            if audit.is_faithful:
                faithful_count += 1
            if audit.is_unambiguous:
                unambiguous_count += 1
            else:
                print(f"  [FLAGGED] Question {audit.question_index}: {audit.feedback}")

        time.sleep(1.0)

    faithfulness_rate = (faithful_count / total_questions) * 100 if total_questions else 0.0
    unambiguity_rate = (unambiguous_count / total_questions) * 100 if total_questions else 0.0

    print(f"\n================ EVALUATION SUMMARY ================")
    print(f"Total Evaluated Questions: {total_questions}")
    print(f"Faithfulness Score:        {faithfulness_rate:.2f}% (Target: >95%)")
    print(f"Unambiguity Score:         {unambiguity_rate:.2f}% (Target: >95%)")
    print(f"Hallucination Rate:        {100 - faithfulness_rate:.2f}% (Target: <5%)")
    print(f"====================================================\n")

if __name__ == "__main__":
    run_benchmarks()
