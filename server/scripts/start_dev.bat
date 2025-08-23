@echo off
REM 参考文档: doc/server_structure.md 启动脚本部分
REM Windows本地开发启动脚本 - 使用conda环境管理

echo === 罡好饭API服务 - 本地开发模式启动（Windows） ===

REM 设置工作目录到server根目录
cd /d "%~dp0\.."

REM 环境配置
set ENV_NAME=ganghaofan_dev
set PYTHON_VERSION=3.11

echo 当前工作目录: %CD%
echo conda环境名称: %ENV_NAME%

REM 检查conda命令
conda --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到conda命令，请先安装Anaconda或Miniconda
    pause
    exit /b 1
)

REM 删除已存在的环境（如果存在）
echo 检查并删除已存在的conda环境...
conda env list | findstr /b "%ENV_NAME% " >nul 2>&1
if %errorlevel% equ 0 (
    echo 删除已存在的环境: %ENV_NAME%
    conda env remove -n %ENV_NAME% -y
)

REM 创建新的conda环境
echo 创建新的conda环境: %ENV_NAME% ^(Python %PYTHON_VERSION%^)
conda create -n %ENV_NAME% python=%PYTHON_VERSION% -y
if %errorlevel% neq 0 (
    echo 错误: conda环境创建失败
    pause
    exit /b 1
)

REM 激活环境
echo 激活conda环境: %ENV_NAME%
call conda activate %ENV_NAME%
if %errorlevel% neq 0 (
    echo 错误: conda环境激活失败
    pause
    exit /b 1
)

REM 安装依赖包
echo 安装Python依赖包...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖包安装失败
    pause
    exit /b 1
)

REM 设置环境变量
set PYTHONPATH=%PYTHONPATH%;%CD%
set CONFIG_ENV=development

echo Python路径: %PYTHONPATH%
echo 配置环境: %CONFIG_ENV%
python --version

REM 验证关键依赖
echo 验证关键依赖包...
python -c "import fastapi, uvicorn, duckdb, pydantic, httpx, pytest"
if %errorlevel% neq 0 (
    echo 错误: 依赖包安装不完整
    pause
    exit /b 1
)

REM 数据库初始化
echo 初始化数据库...
python scripts\init_db.py
if %errorlevel% neq 0 (
    echo 错误: 数据库初始化失败
    pause
    exit /b 1
)

REM 启动本地开发服务（热重载）
echo.
echo 启动罡好饭API服务（本地开发模式）...
echo 访问地址: http://127.0.0.1:8000
echo API文档: http://127.0.0.1:8000/docs
echo 按 Ctrl+C 停止服务
echo.

uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug

pause