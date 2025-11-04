from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from tools import search_tool, wiki_tool
import json
import sys

load_dotenv()

class QuizQuestion(BaseModel):
    """A single question for a quiz."""
    question: str = Field(description="The full text of the quiz question.")
    options: list[str] = Field(description="A list of possible answers for the user to choose from.")
    answer: str = Field(description="The exact text of the correct answer from the options list.")

class Quiz(BaseModel):
    """A complete quiz on a specific topic."""
    topic: str = Field(description="The subject of the quiz.")
    questions: list[QuizQuestion] = Field(description="A list of 5 generated quiz questions.")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
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
    verbose=True
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

print("Enter quiz topic: ", flush=True)
topic = input()
if not topic:
    print("No topic provided. Exiting.")
    sys.exit(0)

try:
    final_quiz: Quiz = chain.invoke({"topic": topic})
    final_quiz_dict = final_quiz.model_dump()

    print("\n✅Here is your quiz!")
    print(json.dumps(final_quiz_dict, indent=4))
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)