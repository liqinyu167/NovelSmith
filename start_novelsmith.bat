@echo off
title NovelSmith 一键启动器
echo ===================================================
echo   NovelSmith 正在拉起前端与后端全部服务...
echo ===================================================
echo.

rem 获取当前批处理文件所在目录
set "ROOT_DIR=%~dp0"

rem 1. 启动后端服务
echo 正在启动后端服务 (Uvicorn)...
start "NovelSmith 后端服务" cmd /k "cd /d %ROOT_DIR%backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8765 --reload"

rem 2. 启动前端服务
echo 正在启动前端服务 (Vite)...
start "NovelSmith 前端服务" cmd /k "cd /d %ROOT_DIR%frontend && npm run dev"

echo.
echo ===================================================
echo   服务拉起成功！
echo   - 后端 API 地址: http://127.0.0.1:8765
echo   - 前端 Web 地址: http://127.0.0.1:5173
echo ===================================================
echo.
pause
