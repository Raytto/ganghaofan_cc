# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

罡好饭 (Gang Hao Fan) - Internal company meal ordering system designed for ~50 employees. Currently in documentation phase with no code implementation yet.

## Technology Stack

- **Backend**: Python FastAPI with DuckDB embedded database
- **Frontend**: WeChat Mini Program (TypeScript + Skyline rendering)
- **Database**: DuckDB (single-file embedded database)
- **Authentication**: JWT tokens with WeChat OAuth
- **Deployment**: Single Python process on cloud server

## Development Commands

Since this is a greenfield project, standard commands will be:

### Backend (FastAPI)
```bash
# Development server (once implemented)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Database initialization
python scripts/init_db.py
```

### Frontend (WeChat Mini Program)
```bash
# Use WeChat Developer Tools for compilation and preview
# No CLI commands - use GUI tools
```

## Architecture

### Database Design
- 5 core tables: users, meals, orders, ledger, system_config
- All monetary amounts stored as integers in cents (avoid floating-point issues)
- Ledger table tracks all balance changes for audit trail
- Unique constraint: one order per user per meal

### Business Logic
1. **Pre-payment model**: Users must have sufficient balance before ordering
2. **Meal workflow**: draft → published → locked → completed
3. **Two daily sessions**: lunch and dinner with independent settings
4. **Order deadlines**: Configurable (default 10:30 for lunch, 16:30 for dinner)

### API Structure (Planned)
- `/api/auth/*` - WeChat login and JWT management
- `/api/meals/*` - Meal CRUD and listing
- `/api/orders/*` - Order placement and management  
- `/api/balance/*` - Recharge and balance queries
- `/api/admin/*` - Admin-only operations

## Key Implementation Notes

### When implementing database operations:
- Always use transactions for balance changes (update both users.balance_cents and create ledger record)
- Generate order numbers as: ORD + YYYYMMDD + 6-digit sequence
- Generate transaction numbers as: TXN + YYYYMMDD + 6-digit sequence
- Enforce meal capacity limits (check current_orders < max_orders)

### When implementing the frontend:
- Use calendar grid view similar to Google Calendar for meal display
- Implement pull-to-refresh for meal listings
- Show real-time remaining slots for each meal
- Color coding: green (available), yellow (limited), red (full/locked)

### When implementing authentication:
- WeChat login returns openid as unique identifier
- Generate JWT tokens with user_id and is_admin claims
- Admin status determined by users.is_admin field

## Development Phases

Follow the 5-phase MVP approach outlined in `/doc/start_from_scratch/MVP需求文档.md`:
1. Basic framework setup
2. User authentication
3. Meal display interface
4. Order placement functionality
5. Balance management system

## Important Constraints

- System designed for ~50 users (internal company use)
- Single-machine deployment (no distributed systems needed)
- WeChat Mini Program only (no web or other mobile apps)
- DuckDB file stored locally (implement regular backups)
- All times in China Standard Time (UTC+8)
- @doc/db/core_operations.md 停用附加项时检查是否有活跃状态的meal在用，在用则不允许停用