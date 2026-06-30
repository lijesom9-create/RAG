#!/bin/bash

echo "========================================"
echo "    教育培训Agent - 启动脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[1/4] 检查MongoDB..."
if ! command -v mongod &> /dev/null; then
    echo "警告: MongoDB未安装或未在PATH中"
    echo "请确保MongoDB已启动"
fi
echo ""

echo "[2/4] 启动后端..."
cd "$PROJECT_DIR/backend"
source venv/bin/activate 2>/dev/null || echo "提示: 未找到虚拟环境，使用系统Python"
python main.py &
BACKEND_PID=$!
echo "后端PID: $BACKEND_PID"
sleep 3
echo ""

echo "[3/4] 启动前端..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "前端PID: $FRONTEND_PID"
sleep 3
echo ""

echo "[4/4] 启动完成!"
echo ""
echo "========================================"
echo "    访问地址: http://localhost:3000"
echo "    API文档: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号
trap "echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

# 等待
wait
