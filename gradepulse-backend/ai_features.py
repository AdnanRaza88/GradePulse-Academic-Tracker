# GradePulse Backend

FastAPI-based backend for GradePulse - AI Powered Academic Performance Tracker.

## Features
- CRUD for student grades
- Bulk upload (CSV/Excel)
- AI Study Tips using Groq + LangChain
- Custom grading configurations
- Data export

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY
uvicorn main:app --reload
```

## Deployment
Ready for Railway / Render / Fly.io with nixpacks.toml