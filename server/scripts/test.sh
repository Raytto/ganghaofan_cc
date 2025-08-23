#!/bin/bash
# 一键测试脚本 - 使用conda环境管理

set -e

echo "=== 罡好饭API服务 - 一键测试脚本 ==="

# 设置工作目录
cd "$(dirname "$0")/.."

# 环境配置
ENV_NAME="ganghaofan_test"
PYTHON_VERSION="3.11"
TEST_PORT=8000

echo "当前工作目录: $(pwd)"
echo "测试环境名称: $ENV_NAME"
echo "测试端口: $TEST_PORT"

# 创建测试报告目录
mkdir -p tests/report

# 检查conda命令
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到conda命令，请先安装Anaconda或Miniconda"
    exit 1
fi

# 检查端口占用并强制释放
echo "检查并释放端口 $TEST_PORT..."
if lsof -ti:$TEST_PORT &> /dev/null; then
    echo "端口 $TEST_PORT 被占用，强制杀死占用进程..."
    lsof -ti:$TEST_PORT | xargs kill -9
    sleep 2
fi

# 删除已存在的环境（如果存在）
echo "检查并删除已存在的conda环境..."
if conda env list | grep -q "^$ENV_NAME "; then
    echo "删除已存在的环境: $ENV_NAME"
    conda env remove -n $ENV_NAME -y
fi

# 创建新的conda环境
echo "创建新的conda环境: $ENV_NAME (Python $PYTHON_VERSION)"
conda create -n $ENV_NAME python=$PYTHON_VERSION -y

# 激活环境
echo "激活conda环境: $ENV_NAME"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate $ENV_NAME

# 安装依赖包
echo "安装Python依赖包..."
pip install -r requirements.txt

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export CONFIG_ENV="development"

echo "Python路径: $PYTHONPATH"
echo "配置环境: $CONFIG_ENV"
echo "Python版本: $(python --version)"

# 验证关键依赖
echo "验证关键依赖包..."
python -c "import fastapi, uvicorn, duckdb, pydantic, httpx, pytest" || {
    echo "错误: 依赖包安装不完整"
    exit 1
}

# 清理并重新创建数据库
echo "清理并重新创建数据库..."
rm -f data/gang_hao_fan.db
python scripts/init_db.py

echo ""
echo "=== 开始测试 ==="

# 1. 运行数据库测试
echo "1. 运行数据库操作测试..."
python -m pytest tests/test_db/ -v --tb=short > tests/report/db_test_results.txt 2>&1
DB_TEST_RESULT=$?

if [ $DB_TEST_RESULT -eq 0 ]; then
    echo "✅ 数据库测试通过"
else
    echo "❌ 数据库测试失败"
fi

# 2. 启动测试服务器（后台运行）
echo "2. 启动测试服务器..."
uvicorn api.main:app --host 127.0.0.1 --port $TEST_PORT --log-level error &
SERVER_PID=$!

# 等待服务器启动
echo "等待服务器启动..."
sleep 5

# 检查服务器是否启动成功
if curl -s http://127.0.0.1:$TEST_PORT/health &> /dev/null; then
    echo "✅ 测试服务器启动成功"
else
    echo "❌ 测试服务器启动失败"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# 3. 运行API测试
echo "3. 运行API接口测试..."
python -m pytest tests/test_api/ -v --tb=short > tests/report/api_test_results.txt 2>&1
API_TEST_RESULT=$?

if [ $API_TEST_RESULT -eq 0 ]; then
    echo "✅ API测试通过"
else
    echo "❌ API测试失败"
fi

# 4. 运行情景测试
echo "4. 运行业务情景测试..."
python tests/scenario_test.py > tests/report/scenario_test_results.txt 2>&1
SCENARIO_TEST_RESULT=$?

if [ $SCENARIO_TEST_RESULT -eq 0 ]; then
    echo "✅ 情景测试通过"
else
    echo "❌ 情景测试失败"
fi

# 停止测试服务器
echo "停止测试服务器..."
kill $SERVER_PID 2>/dev/null || true
sleep 2

# 生成测试报告
echo "5. 生成测试报告..."
python scripts/generate_test_report.py

echo ""
echo "=== 测试完成 ==="

# 显示测试结果汇总
if [ $DB_TEST_RESULT -eq 0 ] && [ $API_TEST_RESULT -eq 0 ] && [ $SCENARIO_TEST_RESULT -eq 0 ]; then
    echo "🎉 所有测试通过！"
    echo "📊 详细报告: tests/report/test_report.md"
    exit 0
else
    echo "💥 部分测试失败"
    echo "📊 详细报告: tests/report/test_report.md"
    echo ""
    echo "失败的测试:"
    [ $DB_TEST_RESULT -ne 0 ] && echo "  - 数据库测试"
    [ $API_TEST_RESULT -ne 0 ] && echo "  - API测试"  
    [ $SCENARIO_TEST_RESULT -ne 0 ] && echo "  - 情景测试"
    exit 1
fi