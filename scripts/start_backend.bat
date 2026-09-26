@echo off
cd /d "%~dp0\.."
echo Starting Cultural Heritage Deterioration Monitoring FastAPI Backend...
call backend\venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
