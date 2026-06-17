from sqlmodel import Session, select
from models import GradingConfig
from typing import Optional
def compute_percentage(marks_obtained: float, total_marks: float) -> float:
    return round((marks_obtained / total_marks) * 100, 2)
def assign_grade_letter(percentage: float, session: Session) -> str:
    # Fetch grading config from DB
    configs = session.exec(select(GradingConfig)).all()
    if not configs:
        # Default fallback
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
    # Sort configs by max_percentage (or just check ranges)
    for config in configs:
        if config.min_percentage <= percentage <= config.max_percentage:
            return config.label
    # If no match, return "F" or lowest passing?
    # But we assume ranges cover 0-100. If not, default F.
    return "F"