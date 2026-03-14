@echo off
set BACKEND_PORT=8012
echo Starting Coin Lab Development Servers...
echo Backend port: %BACKEND_PORT%
start "Backend" cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT%"
start "Frontend" cmd /k "cd frontend && if not defined VITE_API_BASE_URL set VITE_API_BASE_URL=http://127.0.0.1:%BACKEND_PORT% && if not defined VITE_PROXY_TARGET set VITE_PROXY_TARGET=http://127.0.0.1:%BACKEND_PORT% && npm.cmd run dev"
echo Both servers started in separate windows.
