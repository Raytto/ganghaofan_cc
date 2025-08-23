#!/bin/bash
# 参考文档: doc/server_structure.md 启动脚本部分
# Linux生产环境启动脚本 - 使用conda环境管理

set -e

echo "=== 罡好饭API服务 - 生产模式启动 ==="

# 设置工作目录
cd "$(dirname "$0")/.."

# 环境配置
ENV_NAME="ganghaofan_prod"
PYTHON_VERSION="3.11"

echo "当前工作目录: $(pwd)"
echo "conda环境名称: $ENV_NAME"

# 检查conda命令
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到conda命令，请先安装Anaconda或Miniconda"
    exit 1
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
export CONFIG_ENV="production"

echo "Python路径: $PYTHONPATH"
echo "配置环境: $CONFIG_ENV"
echo "Python版本: $(python --version)"

# 验证关键依赖
echo "验证关键依赖包..."
python -c "import fastapi, uvicorn, duckdb, pydantic, httpx" || {
    echo "错误: 依赖包安装不完整"
    exit 1
}

# 数据库初始化检查
echo "检查数据库初始化..."
python scripts/init_db.py

# 创建日志目录
mkdir -p logs

# 启动生产服务
echo "启动罡好饭API服务（生产模式）..."
echo "服务地址: http://0.0.0.0:8000"
echo "工作进程: 4"
echo "日志文件: logs/"
echo ""

# 使用4个工作进程启动生产服务
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4 --no-reload --log-level info