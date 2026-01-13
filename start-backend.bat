@echo off
echo Starting Appointment Scheduling System Backend...
cd backend
call venv\Scripts\activate
uvicorn app.main:app --reload --port 8000