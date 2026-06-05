from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from tools import search_tool, wiki_tool
import json
import sys
import os
import streamlit as st

api_key = os.environ.get("GOOGLE_API_KEY")

class QuizQuestion(BaseModel):
    """A single question for a quiz."""
    question: str = Field(description="The full text of the quiz question.")
    options: list[str] = Field(description="A list of possible answers for the user to choose from.")
    answer: str = Field(description="The exact text of the correct answer from the options list.")

class Quiz(BaseModel):
    """A complete quiz on a specific topic."""
    topic: str = Field(description="The subject of the quiz.")
    questions: list[QuizQuestion] = Field(description="A list of 5 generated quiz questions.")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
research_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an expert quiz generator. Your sole task is to gather
            detailed information about the user's topic using the available tools.
            You must provide a comprehensive summary of facts, names, dates,
            and key concepts related to the topic.
            """,
        ),
        ("human", "Please resarch this topic: {topic}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

tools = [search_tool, wiki_tool]
research_agent = create_tool_calling_agent(llm, tools, research_prompt)
research_executor = AgentExecutor(
    agent=research_agent,
    tools=tools,
    verbose=False
)

quiz_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an expert quiz generator. Given the following research,
            create a 5-question multiple-choice quiz based *only* on that information.
            The topic of the quiz should be the user's original requested topic.
            """ 
        ),
        ("human", "Topic: {topic}\n\nResarch Information:\n{research_content}"),
    ]
)

quiz_generator = quiz_gen_prompt | llm.with_structured_output(Quiz)

chain = (
    RunnablePassthrough.assign(
        research_content = lambda inputs: research_executor.invoke(
            {"topic": inputs["topic"]}
            )["output"])
            | quiz_generator
)

hide_input_instructions_style = """
<style>
[data-testid="InputInstructions"] {
    display: none;
}
</style>
"""

st.title("🧠 QuizGen")
st.markdown("Generate a multiple-choice quiz of your desired topic!")
st.markdown(hide_input_instructions_style, unsafe_allow_html=True)

if 'quiz' in st.session_state:
    if st.button("Generate New Quiz"):
        answer_keys = [key for key in st.session_state.keys() if key.startswith("q_")]

        for key in answer_keys:
            st.session_state.pop(key, None)

        st.session_state.pop('quiz', None)
        st.session_state.pop('score', None)
        st.rerun()

if 'quiz' not in st.session_state:
    with st.form(key="quiz_form"):
        topic = st.text_input("Enter a quiz topic:", placeholder="e.g., 'The War of 1812'")

        submit_button = st.form_submit_button("Generate Quiz")

    if submit_button:
        if topic:
            with st.spinner(f"Researching '{topic}' and building your quiz..."):
                try:
                    final_quiz: Quiz = chain.invoke({"topic": topic})
                    st.session_state['quiz'] = final_quiz
                except Exception as e:
                    st.session_state['quiz'] = None
                    st.error(f"An error occurred: {e}")
        else:
            st.error("Please enter a topic.")
    

if 'quiz' in st.session_state and st.session_state['quiz']:
    final_quiz = st.session_state['quiz']
    
    st.divider()
    if 'score' not in st.session_state:

        with st.form(key="quiz_answer_form"):
            for index, question in enumerate(final_quiz.questions):
                st.subheader(f"Question {index + 1}:")
                st.write(question.question)

                st.radio(
                    "Select an answer:",
                    options=question.options,
                    key=f"q_{index}_options",
                    label_visibility="collapsed"
                )
                st.divider()
        
            submitted = st.form_submit_button("Submit Quiz")

        if submitted:
            score = 0
            total_questions = len(final_quiz.questions)

            for index, question in enumerate(final_quiz.questions):
                user_answer = st.session_state[f"q_{index}_options"]

                if user_answer == question.answer:
                    score += 1
                
            st.session_state['score'] = (score, total_questions)
            st.rerun()
    else:
        score_tuple = st.session_state['score']

        user_score = score_tuple[0]
        total_questions = score_tuple[1]

        final_score_decimal = user_score / total_questions 
        passing_score_decimal = (len(final_quiz.questions) / 2 + 1) / total_questions
        max_score_decimal = total_questions / total_questions
        score_fraction = f"{user_score} / {total_questions}"

        if final_score_decimal < passing_score_decimal:
            st.error(f"Your Final Score: {score_fraction}. You failed. ☹️")
        elif final_score_decimal == max_score_decimal:
            st.balloons()
            st.success(f"Your final score: {score_fraction}. Perfect Score! 🥳")
        else:
            st.success(f"Your final score: {user_score}. You passed. 🙂")
        
        st.divider()
        st.header("Review Your Answers")

        for index, question in enumerate(final_quiz.questions):
            user_answer = st.session_state[f"q_{index}_options"]

            st.subheader(f"Question {index + 1}:")
            st.write(question.question)

            st.radio(
                    "Select an answer:",
                    options=question.options,
                    key=f"q_{index}_options",
                    label_visibility="collapsed"
                )
            
            st.divider()
            
            if user_answer == question.answer:
                st.success(f"Your answer: {user_answer} (Correct!)")
            else:
                st.error(f"Your answer: {user_answer} (Incorrect)")
                st.success(f"Correct answer: {question.answer}")
            
            st.divider()