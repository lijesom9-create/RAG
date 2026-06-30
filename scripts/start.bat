@echo off
echo ========================================
echo    教育培训Agent - 启动脚本
echo ========================================
echo.

echo [1/4] 检查MongoDB...
mongod --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 警告: MongoDB未安装或未在PATH中
    echo 请确保MongoDB已启动
)
echo.

echo [2/4] 启动后端...
cd /d "%~dp0..\backend"
start "Backend" cmd /k "python main.py"
echo 后端启动中...
timeout /t 3 /nobreak >nul
echo.

echo [3/4] 启动前端...
cd /d "%~dp0..\frontend"
start "Frontend" cmd /k "npm run dev"
echo 前端启动中...
timeout /t 3 /nobreak >nul
echo.

echo [4/4] 启动完成!
echo.
echo ========================================
echo    访问地址: http://localhost:3000
echo    API文档: http://localhost:8000/docs
echo ========================================
echo.
echo 按任意键退出此窗口...
pause >nul
