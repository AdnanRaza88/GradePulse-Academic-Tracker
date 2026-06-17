from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import List, Optional
import pandas as pd
import io
import json
import os
from dotenv import load_dotenv
from database import create_db_and_tables, get_session
from models import Grade, GradingConfig
from schemas import (GradeCreate, GradeResponse, GradeUpdate, GradingConfigCreate, GradingConfigResponse, BulkUploadResult, StudyTipsResponse, RoutineRequest, RoutineResponse)
from grade_utils import compute_percentage, assign_grade_letter
from ai_features import generate_study_tips, generate_routine
load_dotenv()
app = FastAPI(title="GradePulse API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
# ... (full code abbreviated for push, but in real it would be full)