#!/bin/bash
# Scene2测试环境控制脚本
# 参考: doc/test/scene2.md

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# TMUX会话名
SESSION_NAME="scene2_test_server"

echo -e "${GREEN}=== Scene2 情景测试 - 完整流程测试 ===${NC}"

# 函数：清理并初始化数据库
cleanup_database() {
    echo -e "${YELLOW}🗂️  清理并初始化数据库...${NC}"
    
    # 删除现有数据库
    DB_PATH="data/gang_hao_fan_dev.db"
    if [ -f "$DB_PATH" ]; then
        rm -f "$DB_PATH"
        echo -e "${CYAN}已删除现有数据库${NC}"
    fi
    
    # 重新初始化
    python scripts/init_db.py
    echo -e "${GREEN}✅ 数据库初始化完成${NC}"
}

# 函数：启动服务器
start_server() {
    echo -e "${YELLOW}🚀 启动测试服务器...${NC}"
    
    # 检查是否已有运行的会话
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${YELLOW}发现现有服务器会话，正在停止...${NC}"
        tmux kill-session -t "$SESSION_NAME"
        sleep 2
    fi
    
    # 启动新的服务器会话
    tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR" './scripts/start_dev_remote_quick.sh'
    
    # 等待服务器启动
    echo -e "${CYAN}等待服务器启动...${NC}"
    sleep 8
    
    # 检查服务器状态
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${GREEN}✅ 服务器启动成功${NC}"
        echo -e "${CYAN}服务器地址: http://0.0.0.0:8000${NC}"
        echo -e "${CYAN}远程地址: http://us.pangruitao.com:8000${NC}"
    else
        echo -e "${RED}❌ 服务器启动失败${NC}"
        exit 1
    fi
}

# 函数：停止服务器
stop_server() {
    echo -e "${YELLOW}🛑 停止测试服务器...${NC}"
    
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        tmux kill-session -t "$SESSION_NAME"
        echo -e "${GREEN}✅ 服务器已停止${NC}"
    else
        echo -e "${CYAN}服务器未运行${NC}"
    fi
}

# 函数：运行测试
run_tests() {
    echo -e "${YELLOW}🧪 开始运行Scene2测试...${NC}"
    
    # 运行Python测试脚本
    python test_scene2.py
    
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "${GREEN}🎉 Scene2测试全部通过！${NC}"
    else
        echo -e "${RED}❌ Scene2测试失败${NC}"
        
        # 显示服务器日志
        echo -e "${YELLOW}📋 显示服务器日志:${NC}"
        if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            tmux capture-pane -t "$SESSION_NAME" -p | tail -30
        fi
        
        return $TEST_RESULT
    fi
}

# 主执行流程
main() {
    echo -e "${CYAN}开始时间: $(date)${NC}"
    
    # 1. 清理并初始化数据库
    cleanup_database
    
    # 2. 启动服务器
    start_server
    
    # 3. 运行测试
    if run_tests; then
        echo -e "${GREEN}🏆 Scene2测试完成 - 全部通过${NC}"
        FINAL_RESULT=0
    else
        echo -e "${RED}💥 Scene2测试完成 - 有失败项${NC}"
        FINAL_RESULT=1
    fi
    
    # 4. 停止服务器
    stop_server
    
    echo -e "${CYAN}结束时间: $(date)${NC}"
    
    exit $FINAL_RESULT
}

# 处理Ctrl+C信号
trap 'echo -e "\n${YELLOW}收到中断信号，正在清理...${NC}"; stop_server; exit 1' INT TERM

# 检查参数
case "${1:-}" in
    "start")
        cleanup_database
        start_server
        echo -e "${GREEN}环境已准备就绪，可以手动运行测试${NC}"
        echo -e "${CYAN}运行测试: python test_scene2.py${NC}"
        echo -e "${CYAN}停止服务器: $0 stop${NC}"
        ;;
    "stop")
        stop_server
        ;;
    "test-only")
        run_tests
        ;;
    *)
        main
        ;;
esac