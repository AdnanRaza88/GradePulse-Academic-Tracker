from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not set in environment")
llm = ChatGroq(
    temperature=0.3,
    model_name="llama-3.3-70b-versatile",
    api_key=groq_api_key
)
study_tips_prompt = PromptTemplate.from_template(
    """You are an academic advisor. A student named {student_name} received a {grade_letter} grade with {percentage}% in {subject}.
    Provide exactly 5 actionable, specific study tips to improve in {subject}. Format:
    - Tip 1: ...
    - Tip 2: ...
    Keep them encouraging and practical. Return only the tips."""
)
routine_prompt = PromptTemplate.from_template(
    """You are a health and study routine planner. Create a detailed daily routine for {student_name} who has {free_hours} free hours per day.
    They are weak in {weak_subject}. Physical activity: {physical_activity}. Sleep: {sleep_hours} hours. Water intake: {water_intake}.
    Their subjects and recent percentages: {marks_summary}.
    Return a JSON with sections: "morning", "study_blocks" (list of time blocks with subject and duration), "breaks", "evening", "sleep".
    Make sure the schedule is realistic and includes water reminders and quick exercises if applicable. Output only valid JSON."""
)
study_chain = study_tips_prompt | llm | StrOutputParser()
routine_chain = routine_prompt | llm | StrOutputParser()
def generate_study_tips(student_name: str, subject: str, percentage: float, grade_letter: str) -> str:
    return study_chain.invoke({
        "student_name": student_name,
        "subject": subject,
        "percentage": percentage,
        "grade_letter": grade_letter
    })
def generate_routine(data: dict) -> str:
    # marks_summary is a string like "Math:78%, English:65%"
    return routine_chain.invoke(data)