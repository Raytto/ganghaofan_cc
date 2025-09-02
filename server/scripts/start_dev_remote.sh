#!/bin/bash
# Reference: doc/server_structure.md startup script section
# Linux remote development/testing startup script - for public deployment testing
# Domain: us.pangruitao.com

# Stop execution on error
set -e

# Color definitions for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Gang Hao Fan API Service - Remote Testing Mode ===${NC}"
echo -e "${CYAN}Deployment domain: us.pangruitao.com${NC}"

# Set working directory to server root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Environment configuration
ENV_NAME="ganghaofan_remote"
PYTHON_VERSION="3.11"

echo -e "${CYAN}Current working directory: $(pwd)${NC}"
echo -e "${CYAN}Conda environment name: $ENV_NAME${NC}"

# Function to find and initialize conda
initialize_conda() {
    local conda_paths=(
        "/home/pp/miniconda3"
        "$HOME/miniconda3"
        "$HOME/anaconda3"
        "/opt/conda"
        "/usr/local/miniconda3"
    )
    
    for conda_path in "${conda_paths[@]}"; do
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

# Remove existing environment if exists
echo -e "${YELLOW}Checking and removing existing conda environment...${NC}"
if conda env list | grep -q "^$ENV_NAME "; then
    echo -e "${YELLOW}Removing existing environment: $ENV_NAME${NC}"
    conda env remove -n $ENV_NAME -y || {
        echo -e "${RED}Failed to remove conda environment${NC}"
        exit 1
    }
fi

# Create new conda environment
echo -e "${YELLOW}Creating new conda environment: $ENV_NAME (Python $PYTHON_VERSION)${NC}"
conda create -n $ENV_NAME python=$PYTHON_VERSION -y || {
    echo -e "${RED}Failed to create conda environment${NC}"
    exit 1
}

# Activate environment
echo -e "${YELLOW}Activating conda environment: $ENV_NAME${NC}"
conda activate $ENV_NAME || {
    echo -e "${RED}Failed to activate conda environment${NC}"
    exit 1
}

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt || {
    echo -e "${RED}Failed to install dependencies${NC}"
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

# Verify key dependencies
echo -e "${YELLOW}Verifying key dependencies...${NC}"
python -c "import fastapi, uvicorn, duckdb, pydantic, httpx, pytest" || {
    echo -e "${RED}Error: Dependencies installation incomplete${NC}"
    exit 1
}
echo -e "${GREEN}Dependencies verification passed${NC}"

# Database initialization
echo -e "${YELLOW}Initializing database...${NC}"
python scripts/init_db.py || {
    echo -e "${RED}Database initialization failed${NC}"
    exit 1
}
echo -e "${GREEN}Database initialization completed${NC}"

# Create SSL directory if needed (for future HTTPS support)
SSL_DIR="$(pwd)/ssl"
if [ ! -d "$SSL_DIR" ]; then
    echo -e "${YELLOW}Creating SSL directory for future HTTPS support...${NC}"
    mkdir -p "$SSL_DIR"
fi

# Start remote testing service
echo ""
echo -e "${GREEN}Starting Gang Hao Fan API service (remote testing mode)...${NC}"
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