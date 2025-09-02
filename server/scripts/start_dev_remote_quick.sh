#!/bin/bash
# Reference: doc/server_structure.md startup script section
# Linux remote development/testing startup script (Quick start - no environment rebuild)
# Domain: us.pangruitao.com

# Stop execution on error
set -e

# Color definitions for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Gang Hao Fan API Service - Remote Testing Mode (Quick Start) ===${NC}"
echo -e "${CYAN}Deployment domain: us.pangruitao.com${NC}"

# Set working directory to server root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Environment configuration
ENV_NAME="ganghaofan_remote"

echo -e "${CYAN}Current working directory: $(pwd)${NC}"
echo -e "${CYAN}Conda environment name: $ENV_NAME${NC}"

# Function to find and initialize conda
initialize_conda() {
    # Check common conda installation paths
    for conda_path in "/home/pp/miniconda3" "$HOME/miniconda3" "$HOME/anaconda3" "/opt/conda" "/usr/local/miniconda3"; do
        if [ -f "$conda_path/etc/profile.d/conda.sh" ]; then
            echo -e "${YELLOW}Found conda at: $conda_path${NC}"
            source "$conda_path/etc/profile.d/conda.sh"
            return 0
        fi
    done
    
    echo -e "${RED}Error: Cannot find conda initialization script${NC}"
    echo -e "${RED}Please ensure conda is properly installed${NC}"
    return 1
}

# Initialize conda
echo -e "${YELLOW}Initializing conda environment...${NC}"
if ! initialize_conda; then
    exit 1
fi

# Check conda command
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda command not found after initialization${NC}"
    exit 1
fi
echo -e "${GREEN}Conda command check passed${NC}"

# Check if environment exists
echo -e "${YELLOW}Checking existing conda environment...${NC}"
if ! conda env list | grep -q "^$ENV_NAME "; then
    echo -e "${RED}Error: Conda environment '$ENV_NAME' not found${NC}"
    echo -e "${RED}Please run start_dev_remote.sh first to create the environment${NC}"
    exit 1
fi
echo -e "${GREEN}Found existing environment: $ENV_NAME${NC}"

# Activate environment
echo -e "${YELLOW}Activating conda environment: $ENV_NAME${NC}"
conda activate $ENV_NAME || {
    echo -e "${RED}Failed to activate conda environment${NC}"
    exit 1
}

# Set environment variables for remote deployment
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"
export CONFIG_ENV="development"  # Use development config for testing
export REMOTE_DEPLOYMENT="true"
export DEPLOYMENT_DOMAIN="us.pangruitao.com"

echo -e "${CYAN}Python path: $PYTHONPATH${NC}"
echo -e "${CYAN}Config environment: $CONFIG_ENV${NC}"
echo -e "${CYAN}Deployment domain: $DEPLOYMENT_DOMAIN${NC}"
echo -e "${CYAN}Python version: $(python --version)${NC}"

# Quick dependency verification (no installation)
echo -e "${YELLOW}Verifying key dependencies...${NC}"
python -c "import fastapi, uvicorn, duckdb, pydantic, httpx, pytest" || {
    echo -e "${RED}Error: Dependencies missing, please run start_dev_remote.sh to reinstall${NC}"
    exit 1
}
echo -e "${GREEN}Dependencies verification passed${NC}"

# Check if database exists (no initialization)
DB_PATH="$(pwd)/../data/gang_hao_fan_dev.db"
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}Database not found, running quick initialization...${NC}"
    python scripts/init_db.py || {
        echo -e "${RED}Database initialization failed${NC}"
        exit 1
    }
    echo -e "${GREEN}Database initialization completed${NC}"
else
    echo -e "${GREEN}Database found, skipping initialization${NC}"
fi

# Start remote testing service
echo ""
echo -e "${GREEN}Starting Gang Hao Fan API service (remote testing mode - quick start)...${NC}"
echo -e "${CYAN}Local access: http://0.0.0.0:8000${NC}"
echo -e "${CYAN}Remote access: http://us.pangruitao.com:8000${NC}"
echo -e "${CYAN}API Documentation: http://us.pangruitao.com:8000/docs${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop service${NC}"
echo ""

# Note: For production, you might want to use --ssl-keyfile and --ssl-certfile
# For now, using HTTP for testing (ensure firewall allows port 8000)
uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info \
    --access-log \
    --reload-dir api \
    --reload-dir db \
    --reload-dir utils