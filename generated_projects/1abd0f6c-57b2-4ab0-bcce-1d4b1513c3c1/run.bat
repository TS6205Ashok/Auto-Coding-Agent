@echo off
setlocal
start "Backend" cmd /k "cd backend && call run.bat"
start "Frontend" cmd /k "cd frontend && npm run dev"
