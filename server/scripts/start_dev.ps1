# Reference: doc/server_structure.md startup script section
# PowerShell local development startup script - using conda environment management

# Stop execution on error
$ErrorActionPreference = "Stop"

Write-Host "=== Gang Hao Fan API Service - Local Development Mode (PowerShell) ===" -ForegroundColor Green

# Set working directory to server root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptPath "..")

# Environment configuration
$envName = "ganghaofan_dev"
$pythonVersion = "3.11"

Write-Host "Current working directory: $(Get-Location)" -ForegroundColor Cyan
Write-Host "Conda environment name: $envName" -ForegroundColor Cyan

try {
    # Check conda command
    Write-Host "Checking conda command..." -ForegroundColor Yellow
    $null = Get-Command conda -ErrorAction Stop
    Write-Host "Conda command check passed" -ForegroundColor Green
} catch {
    Write-Host "Error: conda command not found, please install Anaconda or Miniconda first" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    # Remove existing environment if exists
    Write-Host "Checking and removing existing conda environment..." -ForegroundColor Yellow
    $envList = conda env list | Out-String
    if ($envList -match "^$envName\s") {
        Write-Host "Removing existing environment: $envName" -ForegroundColor Yellow
        conda env remove -n $envName -y
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to remove conda environment"
        }
    }

    # Create new conda environment
    Write-Host "Creating new conda environment: $envName (Python $pythonVersion)" -ForegroundColor Yellow
    conda create -n $envName python=$pythonVersion -y
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create conda environment"
    }

    # Activate environment - PowerShell way
    Write-Host "Activating conda environment: $envName" -ForegroundColor Yellow
    
    # Get conda installation path
    $condaInfo = conda info --json | ConvertFrom-Json
    $condaPath = $condaInfo.conda_prefix
    
    # Initialize conda for PowerShell
    & "$condaPath\Scripts\conda.exe" "shell.powershell" "hook" | Out-String | Invoke-Expression
    
    # Activate environment
    conda activate $envName
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate conda environment"
    }

    # Install dependencies
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dependencies"
    }

    # Set environment variables
    $currentPath = Get-Location
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$env:PYTHONPATH;$currentPath"
    } else {
        $env:PYTHONPATH = "$currentPath"
    }
    $env:CONFIG_ENV = "development"

    Write-Host "Python path: $env:PYTHONPATH" -ForegroundColor Cyan
    Write-Host "Config environment: $env:CONFIG_ENV" -ForegroundColor Cyan
    
    $pythonVersionOutput = python --version
    Write-Host "Python version: $pythonVersionOutput" -ForegroundColor Cyan

    # Verify key dependencies
    Write-Host "Verifying key dependencies..." -ForegroundColor Yellow
    python -c "import fastapi, uvicorn, duckdb, pydantic, httpx, pytest"
    if ($LASTEXITCODE -ne 0) {
        throw "Dependencies installation incomplete"
    }
    Write-Host "Dependencies verification passed" -ForegroundColor Green

    # Database initialization
    Write-Host "Initializing database..." -ForegroundColor Yellow
    python scripts\init_db.py
    if ($LASTEXITCODE -ne 0) {
        throw "Database initialization failed"
    }
    Write-Host "Database initialization completed" -ForegroundColor Green

    # Start local development service (hot reload)
    Write-Host ""
    Write-Host "Starting Gang Hao Fan API service (local development mode)..." -ForegroundColor Green
    Write-Host "Access URL: http://127.0.0.1:8000" -ForegroundColor Cyan
    Write-Host "API Documentation: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop service" -ForegroundColor Yellow
    Write-Host ""

    uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug

} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Script execution failed, please check the error message above" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}