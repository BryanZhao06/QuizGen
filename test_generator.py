import os
from app.services.generator import generate_quiz_with_self_correction

sample_text = (
    "A race condition occurs when two or more threads can access shared data "
    "and try to change it simultaneously. To prevent race conditions, critical "
    "sections must be protected using synchronization mechanisms like mutexes."
)

print("Running generator with self-correction verification loop...")
quiz = generate_quiz_with_self_correction(
    context=sample_text,
    num_questions=2,
    topic="Operating Systems",
    max_retries=2
)

print(f"\nQuiz Generated Successfully! ID: {quiz.quiz_id}")
print(f"Total Verified Questions: {len(quiz.questions)}\n")

for i, q in enumerate(quiz.questions, start=1):
    print(f"Q{i}: {q.question_text}")
    for opt in q.options:
        print(f"   [{opt.label}] {opt.text}")
    print(f"Correct: [{q.correct_option}]")
    print(f"Source Quote: \"{q.source_quote}\"")
    print(f"Explanation: {q.explanation}\n")
