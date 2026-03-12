@echo off
echo Starting Coin Lab Development Servers...
start "Backend" cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
start "Frontend" cmd /k "cd frontend && npm.cmd run dev"
echo Both servers started in separate windows.
