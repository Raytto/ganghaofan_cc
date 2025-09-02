#!/usr/bin/env python3
"""
直接修复数据库约束问题
"""

import os
import sys
from pathlib import Path
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db.manager import DatabaseManager

def fix_database_constraints():
    """修复数据库约束问题"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 连接数据库
    db_path = os.path.join(project_root.parent, "data/gang_hao_fan_dev.db")
    logger.info(f"连接数据库: {db_path}")
    
    db_manager = DatabaseManager(db_path)
    db_manager.connect()
    
    try:
        logger.info("=== 开始修复约束问题 ===")
        
        # 1. 备份现有数据
        logger.info("1. 备份现有数据...")
        
        # 获取所有表的数据
        tables_data = {}
        table_names = ['users', 'meals', 'addons', 'orders', 'ledger']
        
        for table in table_names:
            try:
                result = db_manager.execute_single(f"SELECT * FROM {table}").fetchall()
                tables_data[table] = result
                logger.info(f"   备份 {table}: {len(result)} 条记录")
            except Exception as e:
                logger.warning(f"   跳过表 {table}: {e}")
                tables_data[table] = []
        
        # 2. 删除所有表（按依赖关系顺序）
        logger.info("2. 删除现有表...")
        drop_order = ['ledger', 'orders', 'meals', 'users', 'addons']
        for table in drop_order:
            try:
                db_manager.execute_single(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"   删除表 {table}")
            except Exception as e:
                logger.warning(f"   删除表 {table} 失败: {e}")
        
        # 3. 重新创建表结构（确保约束正确）
        logger.info("3. 重新创建表结构...")
        
        # Users表
        db_manager.execute_single("""
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                open_id VARCHAR NOT NULL UNIQUE,
                wechat_name VARCHAR,
                avatar_url VARCHAR,
                balance_cents INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP,
                status VARCHAR DEFAULT 'active'
            )
        """)
        logger.info("   创建 users 表")
        
        # Addons表
        db_manager.execute_single("""
            CREATE TABLE addons (
                addon_id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                price_cents INTEGER NOT NULL,
                display_order INTEGER DEFAULT 0,
                is_default BOOLEAN DEFAULT FALSE,
                status VARCHAR DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("   创建 addons 表")
        
        # Meals表
        db_manager.execute_single("""
            CREATE TABLE meals (
                meal_id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                slot VARCHAR NOT NULL,
                description VARCHAR,
                base_price_cents INTEGER NOT NULL,
                addon_config JSON,
                max_orders INTEGER DEFAULT 50,
                current_orders INTEGER DEFAULT 0,
                status VARCHAR DEFAULT 'published',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                canceled_at TIMESTAMP,
                canceled_by INTEGER,
                canceled_reason VARCHAR,
                UNIQUE(date, slot)
            )
        """)
        logger.info("   创建 meals 表")
        
        # Orders表
        db_manager.execute_single("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                meal_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                addon_selections JSON,
                status VARCHAR DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                canceled_at TIMESTAMP,
                canceled_reason VARCHAR,
                UNIQUE(user_id, meal_id)
            )
        """)
        logger.info("   创建 orders 表")
        
        # Ledger表
        db_manager.execute_single("""
            CREATE TABLE ledger (
                ledger_id INTEGER PRIMARY KEY,
                transaction_no VARCHAR NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                type VARCHAR NOT NULL,
                direction VARCHAR NOT NULL,
                amount_cents INTEGER NOT NULL,
                balance_before_cents INTEGER NOT NULL,
                balance_after_cents INTEGER NOT NULL,
                order_id INTEGER,
                description VARCHAR,
                operator_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("   创建 ledger 表")
        
        # 4. 恢复数据
        logger.info("4. 恢复数据...")
        
        # 恢复 users 数据
        if tables_data['users']:
            for row in tables_data['users']:
                db_manager.execute_single("""
                    INSERT INTO users (user_id, open_id, wechat_name, avatar_url, balance_cents, 
                                     is_admin, created_at, updated_at, last_login_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, list(row))
            logger.info(f"   恢复 users: {len(tables_data['users'])} 条记录")
        
        # 恢复 addons 数据
        if tables_data['addons']:
            for row in tables_data['addons']:
                db_manager.execute_single("""
                    INSERT INTO addons (addon_id, name, price_cents, display_order, is_default,
                                      status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, list(row))
            logger.info(f"   恢复 addons: {len(tables_data['addons'])} 条记录")
        
        # 恢复 meals 数据
        if tables_data['meals']:
            for row in tables_data['meals']:
                db_manager.execute_single("""
                    INSERT INTO meals (meal_id, date, slot, description, base_price_cents,
                                     addon_config, max_orders, current_orders, status,
                                     created_at, updated_at, canceled_at, canceled_by, canceled_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, list(row))
            logger.info(f"   恢复 meals: {len(tables_data['meals'])} 条记录")
        
        # 恢复 orders 数据
        if tables_data['orders']:
            for row in tables_data['orders']:
                db_manager.execute_single("""
                    INSERT INTO orders (order_id, user_id, meal_id, amount_cents, addon_selections,
                                      status, created_at, updated_at, canceled_at, canceled_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, list(row))
            logger.info(f"   恢复 orders: {len(tables_data['orders'])} 条记录")
        
        # 恢复 ledger 数据
        if tables_data['ledger']:
            for row in tables_data['ledger']:
                db_manager.execute_single("""
                    INSERT INTO ledger (ledger_id, transaction_no, user_id, type, direction,
                                      amount_cents, balance_before_cents, balance_after_cents,
                                      order_id, description, operator_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, list(row))
            logger.info(f"   恢复 ledger: {len(tables_data['ledger'])} 条记录")
        
        # 5. 验证约束
        logger.info("5. 验证约束...")
        tables = ['users', 'meals', 'addons', 'orders', 'ledger']
        for table in tables:
            try:
                constraints = db_manager.execute_single(f"SELECT * FROM duckdb_constraints() WHERE table_name = '{table}'").fetchall()
                logger.info(f"   表 {table}: {len(constraints)} 个约束")
                for constraint in constraints:
                    logger.info(f"     - {constraint}")
            except Exception as e:
                logger.warning(f"   检查 {table} 约束失败: {e}")
        
        logger.info("✅ 数据库约束修复完成!")
        
    except Exception as e:
        logger.error(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_manager.close()

if __name__ == "__main__":
    fix_database_constraints()