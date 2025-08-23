# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

罡好饭 (Gang Hao Fan) - Internal company meal ordering system designed for ~50 employees. This is a fully functional FastAPI-based backend with comprehensive testing and database operations implemented.

## Technology Stack

- **Backend**: Python FastAPI with DuckDB embedded database
- **Frontend**: WeChat Mini Program (TypeScript + Skyline rendering)
- **Database**: DuckDB (single-file embedded database)
- **Authentication**: JWT tokens with WeChat OAuth
- **Testing**: pytest with comprehensive API and database tests
- **Environment Management**: Conda with multi-environment support
- **Deployment**: Single Python process on cloud server

## Development Commands

### Backend Development
```bash
# Start development server (Linux/Mac)
cd server && ./scripts/start_dev.sh

# Start development server (Windows)
cd server && scripts\start_dev.bat

# Start remote development server (accessible externally)
cd server && ./scripts/start_dev_remote.sh

# Initialize/reset database
cd server && python scripts/init_db.py

# Run comprehensive tests
cd server && ./scripts/test.sh

# Run specific test suites
cd server && python -m pytest tests/test_db/ -v
cd server && python -m pytest tests/test_api/ -v
cd server && python tests/scenario_test.py
```

### Environment Setup
```bash
# The startup scripts automatically manage conda environments:
# - ganghaofan_dev: Development environment with testing tools
# - ganghaofan_test: Isolated testing environment

# Manual environment creation (if needed)
cd server && conda env create -f environments/environment-dev.yml
```

## Architecture

### Project Structure
```
server/
├── api/                    # FastAPI application layer
│   ├── main.py            # Application entry point
│   ├── auth/              # WeChat authentication and JWT
│   ├── users/             # User management endpoints
│   ├── meals/             # Meal CRUD operations
│   ├── orders/            # Order placement and management
│   ├── admin/             # Admin-only operations
│   └── middleware/        # CORS, logging, security middleware
├── db/                    # Data access layer
│   ├── manager.py         # Database connection management
│   ├── core_operations.py # Core business operations (meals, orders, etc.)
│   ├── query_operations.py # Query and read operations
│   └── supporting_operations.py # Supporting operations
├── utils/                 # Shared utilities
│   ├── config.py          # Configuration management
│   ├── logger.py          # Logging setup
│   ├── security.py        # JWT and security utilities
│   └── response.py        # Standardized API responses
├── config/                # Environment-specific configurations
│   ├── config-dev.json    # Development settings
│   └── config-prod.json   # Production settings
├── scripts/               # Operational scripts
│   ├── start_dev.sh       # Development server startup
│   ├── test.sh            # Comprehensive test runner
│   └── init_db.py         # Database initialization
└── tests/                 # Test suites
    ├── test_api/          # API endpoint tests
    ├── test_db/           # Database operation tests
    └── scenario_test.py   # End-to-end business scenarios
```

### Database Design
- **5 core tables**: users, meals, addons, orders, ledger
- **Financial integrity**: All amounts in cents, with full ledger audit trail
- **Business constraints**: One order per user per meal, meal capacity limits
- **Addon system**: JSON-based configuration allowing flexible meal customization
- **Transaction safety**: All balance operations use database transactions

### API Architecture
- **Modular design**: Each domain (auth, meals, orders, etc.) in separate modules
- **Standardized responses**: Consistent JSON response format across all endpoints
- **Middleware stack**: CORS, logging, security, and error handling
- **Type safety**: Pydantic models for request/response validation

## Database Operations Architecture

### Core Operations (`server/db/core_operations.py`)
The database layer follows a strict transaction-based approach with comprehensive validation:

- **Admin Operations**: 
  - `admin_create_addon()` - Create new meal addons
  - `admin_deactivate_addon()` - Deactivate addons (with active meal checks)
  - `admin_publish_meal()` - Publish new meals with addon configurations
  - `admin_lock_meal()` - Lock meals to prevent new orders
  - `admin_complete_meal()` - Mark meals as completed
  - `admin_cancel_meal()` - Cancel meals with automatic refunds

- **User Operations**:
  - `create_order()` - Place orders with balance validation and addon selections
  - `cancel_order()` - Cancel orders with automatic refunds

### Transaction Safety
- All balance changes are atomic (update users.balance_cents + create ledger record)
- Transaction numbers: `TXN + YYYYMMDD + 6-digit sequence`
- Order validation includes balance sufficiency, meal capacity, and addon limits
- Comprehensive error handling with specific validation messages

### Business Rules Implementation
- **One order per user per meal**: Database constraint enforcement
- **Pre-payment model**: Balance validation before order creation
- **Addon quantity limits**: JSON-based configuration in meals.addon_config
- **Meal capacity management**: Real-time tracking in meals.current_orders
- **Audit trail**: Complete transaction history in ledger table

## Testing Strategy

### Test Coverage
The system includes comprehensive test suites covering all layers:

```bash
# Database Operations Tests
tests/test_db/
├── test_core_operations.py      # Core business logic tests
├── test_query_operations.py     # Query operation tests
└── test_supporting_operations.py # Supporting function tests

# API Endpoint Tests  
tests/test_api/
├── test_auth.py                 # Authentication endpoints
├── test_meals.py                # Meal management APIs
├── test_orders.py               # Order placement APIs
├── test_admin.py                # Admin operation APIs
└── test_users.py                # User management APIs

# End-to-End Tests
tests/scenario_test.py           # Complete business workflows
```

### Test Execution
- **Automated environment setup**: Tests create isolated conda environments
- **Database isolation**: Each test run uses fresh database instances
- **API server testing**: Automated server startup/shutdown for integration tests
- **Comprehensive reporting**: Detailed test reports generated in `tests/report/`

## Configuration Management

### Environment-Specific Settings
- **Development**: `config/config-dev.json` - Local development with debug enabled
- **Production**: `config/config-prod.json` - Production optimizations and security
- **Environment Variables**: JWT secrets, WeChat credentials via environment variables

### Key Configuration Areas
- **Database**: Connection settings, memory limits, backup schedules
- **Authentication**: JWT settings, WeChat OAuth configuration
- **Business Rules**: Order deadlines, meal capacity defaults, timezone settings
- **Logging**: Structured logging with rotation and retention policies

## Important Constraints

- **Scale**: Designed for ~50 users (internal company use)
- **Deployment**: Single-machine deployment (no distributed systems needed)
- **Frontend**: WeChat Mini Program only (no web or other mobile apps)
- **Database**: DuckDB file stored locally with automated backups
- **Timezone**: All times in China Standard Time (UTC+8)
- **Addon Deactivation**: Cannot deactivate addons used by active meals (business rule)
- **Balance Operations**: All financial operations require transaction logging