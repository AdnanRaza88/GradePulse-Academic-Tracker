from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import List, Optional
import pandas as pd
import io
import json
import os
from dotenv import load_dotenv
from database import create_db_and_tables, get_session, engine
from models import Grade, GradingConfig
from schemas import (
    GradeCreate, GradeResponse, GradeUpdate,
    GradingConfigCreate, GradingConfigResponse,
    BulkUploadResult, StudyTipsResponse, RoutineRequest, RoutineResponse
)
from grade_utils import compute_percentage, assign_grade_letter
from ai_features import generate_study_tips, generate_routine
load_dotenv()
app = FastAPI(title="GradePulse API", version="1.0.0")
# CORS for Streamlit frontend (adjust origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # restrict to your frontend URL on Railway
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
# ---------- CRUD ----------
@app.post("/grades", response_model=GradeResponse)
def create_grade(grade: GradeCreate, session: Session = Depends(get_session)):
    # Check if marks_obtained > total_marks (already done in validator but just in case)
    if grade.marks_obtained > grade.total_marks:
        raise HTTPException(status_code=400, detail="marks_obtained cannot exceed total_marks")
    percentage = compute_percentage(grade.marks_obtained, grade.total_marks)
    grade_letter = assign_grade_letter(percentage, session)
    db_grade = Grade(**grade.dict(), percentage=percentage, grade_letter=grade_letter)
    session.add(db_grade)
    session.commit()
    session.refresh(db_grade)
    return db_grade
@app.get("/grades", response_model=List[GradeResponse])
def list_grades(session: Session = Depends(get_session)):
    grades = session.exec(select(Grade)).all()
    return grades
@app.get("/grades/{grade_id}", response_model=GradeResponse)
def get_grade(grade_id: int, session: Session = Depends(get_session)):
    grade = session.get(Grade, grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    return grade
@app.put("/grades/{grade_id}", response_model=GradeResponse)
def update_grade(grade_id: int, grade_update: GradeUpdate, session: Session = Depends(get_session)):
    grade = session.get(Grade, grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    update_data = grade_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(grade, key, value)
    # Recompute percentage and grade if marks or total changed
    if 'marks_obtained' in update_data or 'total_marks' in update_data:
        grade.percentage = compute_percentage(grade.marks_obtained, grade.total_marks)
        grade.grade_letter = assign_grade_letter(grade.percentage, session)
    session.add(grade)
    session.commit()
    session.refresh(grade)
    return grade
@app.delete("/grades/{grade_id}")
def delete_grade(grade_id: int, session: Session = Depends(get_session)):
    grade = session.get(Grade, grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    session.delete(grade)
    session.commit()
    return {"detail": "Grade deleted"}
# ---------- Bonus: Student by Roll Number ----------
@app.get("/grades/student/{roll_number}", response_model=List[GradeResponse])
def get_grades_by_roll(roll_number: str, session: Session = Depends(get_session)):
    grades = session.exec(select(Grade).where(Grade.roll_number == roll_number.strip().upper())).all()
    return grades
# ---------- Bonus: Bulk Upload ----------
@app.post("/grades/bulk-upload", response_model=BulkUploadResult)
async def bulk_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Unsupported file format")
    content = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    required_cols = ['student_name', 'roll_number', 'subject', 'marks_obtained', 'total_marks', 'semester', 'date']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing)}")
    added = 0
    skipped = 0
    errors = []
    for idx, row in df.iterrows():
        row_errors = []
        # Normalize roll number
        roll = str(row['roll_number']).strip().upper()
        name = str(row['student_name']).strip()
        if not name or not roll:
            row_errors.append("Empty student_name or roll_number")
        try:
            marks = float(row['marks_obtained'])
            total = float(row['total_marks'])
            if marks > total:
                row_errors.append("marks_obtained > total_marks")
        except ValueError:
            row_errors.append("Invalid numeric marks/total")
            marks, total = 0, 1 # dummy to avoid crash
        if row_errors:
            errors.append(f"Row {idx+2}: {'; '.join(row_errors)}")
            skipped += 1
            continue
        percentage = compute_percentage(marks, total)
        grade_letter = assign_grade_letter(percentage, session)
        grade = Grade(
            student_name=name,
            roll_number=roll,
            subject=str(row['subject']),
            marks_obtained=marks,
            total_marks=total,
            semester=str(row['semester']),
            date=str(row['date']),
            percentage=percentage,
            grade_letter=grade_letter
        )
        session.add(grade)
        added += 1
    session.commit()
    return BulkUploadResult(rows_added=added, rows_skipped=skipped, errors=errors)
# ---------- AI: Study Tips (Required) ----------
@app.post("/grades/{grade_id}/study-tips", response_model=StudyTipsResponse)
def get_study_tips(grade_id: int, session: Session = Depends(get_session)):
    grade = session.get(Grade, grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    tips = generate_study_tips(
        student_name=grade.student_name,
        subject=grade.subject,
        percentage=grade.percentage,
        grade_letter=grade.grade_letter
    )
    return StudyTipsResponse(
        student_name=grade.student_name,
        subject=grade.subject,
        percentage=grade.percentage,
        grade_letter=grade.grade_letter,
        tips=tips
    )
# ---------- Bonus: Daily Routine AI ----------
@app.post("/grades/{grade_id}/routine", response_model=RoutineResponse)
def get_routine(grade_id: int, request: RoutineRequest, session: Session = Depends(get_session)):
    grade = session.get(Grade, grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    marks_summary = ", ".join([f"{s['subject']}:{s['percentage']}%" for s in request.marks])
    data = {
        "student_name": request.student_name,
        "free_hours": request.free_hours,
        "weak_subject": request.weak_subject,
        "physical_activity": request.physical_activity,
        "sleep_hours": request.sleep_hours,
        "water_intake": request.water_intake,
        "marks_summary": marks_summary
    }
    raw = generate_routine(data)
    try:
        routine_json = json.loads(raw)
    except json.JSONDecodeError:
        routine_json = {"raw_response": raw} # fallback
    return RoutineResponse(routine=routine_json)
# ---------- Grading Config ----------
@app.get("/grades/config", response_model=List[GradingConfigResponse])
def get_config(session: Session = Depends(get_session)):
    configs = session.exec(select(GradingConfig)).all()
    return configs
@app.post("/grades/config", response_model=GradingConfigResponse)
def create_config(config: GradingConfigCreate, session: Session = Depends(get_session)):
    # Check for overlapping ranges
    existing = session.exec(select(GradingConfig)).all()
    for c in existing:
        if (config.min_percentage <= c.max_percentage and config.max_percentage >= c.min_percentage):
            raise HTTPException(status_code=400, detail="Overlapping percentage range with existing config")
    db_config = GradingConfig(**config.dict())
    session.add(db_config)
    session.commit()
    session.refresh(db_config)
    return db_config
@app.delete("/grades/config/{config_id}")
def delete_config(config_id: int, session: Session = Depends(get_session)):
    config = session.get(GradingConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    session.delete(config)
    session.commit()
    return {"detail": "Config deleted"}
# ---------- Export Endpoint ----------
@app.get("/grades/export")
def export_grades(format: str = "json", session: Session = Depends(get_session)):
    grades = session.exec(select(Grade)).all()
    if format == "csv":
        df = pd.DataFrame([g.dict() for g in grades])
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=grades.csv"
        return response
    elif format == "excel":
        df = pd.DataFrame([g.dict() for g in grades])
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        stream.seek(0)
        response = StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = "attachment; filename=grades.xlsx"
        return response
    else:
        # JSON
        return [g.dict() for g in grades]