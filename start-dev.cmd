@echo off
set BACKEND_PORT=8012
echo Starting Coin Lab Development Servers...
echo Backend port: %BACKEND_PORT%
start "Backend" cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT%"
start "Frontend" cmd /k "cd frontend && npm.cmd run dev"
echo Both servers started in separate windows.
