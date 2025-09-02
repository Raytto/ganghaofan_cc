#!/usr/bin/env python3
# 参考文档: doc/db/database_structure.md
# 数据库初始化脚本

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.manager import DatabaseManager

def create_tables(db_manager: DatabaseManager):
    """
    创建所有数据表
    严格按照 doc/db/database_structure.md 的表结构定义
    """
    
    # 1. 用户表（users） - 参考 doc/db/database_structure.md 2.1节
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        open_id VARCHAR(128) UNIQUE NOT NULL,      -- 微信OpenID，唯一标识
        wechat_name VARCHAR(100),                  -- 用户微信名
        avatar_url VARCHAR(500),                   -- 头像URL
        balance_cents INTEGER DEFAULT 0,           -- 账户余额（单位：分）
        is_admin BOOLEAN DEFAULT FALSE,            -- 是否管理员
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP,                   -- 最后登录时间
        status VARCHAR(20) DEFAULT 'active'        -- 账户状态: active/suspended
    )
    """
    
    # 2. 餐次表（meals） - 参考 doc/db/database_structure.md 2.2节
    create_meals_table = """
    CREATE TABLE IF NOT EXISTS meals (
        meal_id INTEGER PRIMARY KEY,
        date DATE NOT NULL,                        -- 餐次日期
        slot VARCHAR(20) NOT NULL,                 -- 时段: lunch/dinner
        description TEXT,                          -- 餐次描述（菜品信息等）
        base_price_cents INTEGER NOT NULL,         -- 不含附加项的基础价格（单位：分）
        addon_config TEXT,                         -- 附加项配置：{"addon_id": max_quantity, "addon_id2": max_quantity} (SQLite使用TEXT存储JSON)
        max_orders INTEGER DEFAULT 50,             -- 最大订餐数量
        current_orders INTEGER DEFAULT 0,          -- 当前已订数量
        status VARCHAR(20) DEFAULT 'published',    -- 状态: published/locked/completed/canceled
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        canceled_at TIMESTAMP,                     -- 取消时间
        canceled_by INTEGER,                       -- 取消操作者ID
        canceled_reason TEXT,                      -- 取消原因
        UNIQUE(date, slot)                         -- 每天每个时段只能有一个餐次
    )
    """
    
    # 3. 附加项表（addons） - 参考 doc/db/database_structure.md 2.3节
    create_addons_table = """
    CREATE TABLE IF NOT EXISTS addons (
        addon_id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,                -- 附加项名称（如"加鸡腿"、"不要鸡腿"、"加饮料"）
        price_cents INTEGER NOT NULL,              -- 附加项价格（单位：分，可以为负数）
        display_order INTEGER DEFAULT 0,           -- 显示顺序
        is_default BOOLEAN DEFAULT FALSE,          -- 是否默认选中
        status VARCHAR(20) DEFAULT 'active',       -- 状态: active/inactive
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # 4. 订单表（orders） - 参考 doc/db/database_structure.md 2.4节
    create_orders_table = """
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,                  -- 用户ID
        meal_id INTEGER NOT NULL,                  -- 餐次ID
        amount_cents INTEGER NOT NULL,             -- 订单金额（单位：分，包含基础价格和选中附加项的价格）
        addon_selections TEXT,                     -- 附加项选择：{"addon_id": quantity, "addon_id2": quantity} (SQLite使用TEXT存储JSON)
        status VARCHAR(20) DEFAULT 'active',       -- 状态: active/canceled/completed
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        canceled_at TIMESTAMP,                     -- 取消时间
        canceled_reason TEXT,                      -- 取消原因
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (meal_id) REFERENCES meals(meal_id),
        UNIQUE(user_id, meal_id)                   -- 每人每餐次只能订一份
    )
    """
    
    # 5. 账本表（ledger） - 参考 doc/db/database_structure.md 2.6节
    create_ledger_table = """
    CREATE TABLE IF NOT EXISTS ledger (
        ledger_id INTEGER PRIMARY KEY,
        transaction_no VARCHAR(32) UNIQUE NOT NULL, -- 交易号（格式：TXN20241125120001）
        user_id INTEGER NOT NULL,                   -- 用户ID
        type VARCHAR(20) NOT NULL,                  -- 类型: recharge/order/refund/adjustment
        direction VARCHAR(10) NOT NULL,             -- 方向: in/out
        amount_cents INTEGER NOT NULL,              -- 金额（单位：分，正数）
        balance_before_cents INTEGER NOT NULL,      -- 变动前余额
        balance_after_cents INTEGER NOT NULL,       -- 变动后余额
        order_id INTEGER,                           -- 关联订单ID（如果是订单相关）
        description VARCHAR(200),                   -- 交易描述
        operator_id INTEGER,                        -- 操作员ID（充值、调整时）
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (operator_id) REFERENCES users(user_id)
    )
    """
    
    # 执行建表语句
    tables = [
        ("users", create_users_table),
        ("addons", create_addons_table), 
        ("meals", create_meals_table),
        ("orders", create_orders_table),
        ("ledger", create_ledger_table)
    ]
    
    for table_name, create_sql in tables:
        try:
            db_manager.execute_single(create_sql)
            logging.info(f"成功创建表: {table_name}")
        except Exception as e:
            logging.error(f"创建表 {table_name} 失败: {e}")
            raise

def create_indexes(db_manager: DatabaseManager):
    """
    创建索引
    严格按照 doc/db/database_structure.md 的索引策略
    """
    
    indexes = [
        # 用户表索引
        "CREATE INDEX IF NOT EXISTS idx_users_open_id ON users(open_id)",
        
        # 餐次表索引  
        "CREATE INDEX IF NOT EXISTS idx_meals_date_slot ON meals(date, slot)",
        "CREATE INDEX IF NOT EXISTS idx_meals_status ON meals(status)",
        "CREATE INDEX IF NOT EXISTS idx_meals_date ON meals(date)",
        
        # 订单表索引
        "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_meal_id ON orders(meal_id)", 
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
        
        # 账本表索引
        "CREATE INDEX IF NOT EXISTS idx_ledger_user_id ON ledger(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_type ON ledger(type)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_created_at ON ledger(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_ledger_transaction_no ON ledger(transaction_no)",
        
        # 附加项表索引
        "CREATE INDEX IF NOT EXISTS idx_addons_status ON addons(status)",
        "CREATE INDEX IF NOT EXISTS idx_addons_display_order ON addons(display_order)"
    ]
    
    for index_sql in indexes:
        try:
            db_manager.execute_single(index_sql)
            logging.info(f"成功创建索引")
        except Exception as e:
            logging.error(f"创建索引失败: {e}")
            raise

def insert_initial_data(db_manager: DatabaseManager):
    """
    插入初始数据
    参考 doc/db/database_structure.md 第五节初始化脚本
    """
    
    # 创建默认管理员账户
    try:
        # 检查是否已存在管理员
        existing_admin = db_manager.execute_single(
            "SELECT user_id FROM users WHERE open_id = ?", 
            ['admin_openid_mock']
        ).fetchone()
        
        if not existing_admin:
            admin_id = db_manager.execute_single("SELECT COALESCE(MAX(user_id), 0) + 1 FROM users").fetchone()[0]
            db_manager.execute_single("""
                INSERT INTO users (user_id, open_id, wechat_name, is_admin, balance_cents, status) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, [admin_id, 'admin_openid_mock', '系统管理员', True, 0, 'active'])
            logging.info("成功创建默认管理员账户")
        else:
            logging.info("默认管理员账户已存在")
            
    except Exception as e:
        logging.error(f"创建默认管理员失败: {e}")
        raise

    # 插入示例附加项
    sample_addons = [
        ('加鸡腿', 300, 1, False),
        ('加饮料', 200, 2, False), 
        ('不要香菜', 0, 3, False),
        ('少放盐', 0, 4, False)
    ]
    
    for name, price, order, is_default in sample_addons:
        try:
            existing_addon = db_manager.execute_single(
                "SELECT addon_id FROM addons WHERE name = ?",
                [name]
            ).fetchone()
            
            if not existing_addon:
                addon_id = db_manager.execute_single("SELECT COALESCE(MAX(addon_id), 0) + 1 FROM addons").fetchone()[0]
                db_manager.execute_single("""
                    INSERT INTO addons (addon_id, name, price_cents, display_order, is_default, status)
                    VALUES (?, ?, ?, ?, ?, 'active')
                """, [addon_id, name, price, order, is_default])
                logging.info(f"成功创建示例附加项: {name}")
        except Exception as e:
            logging.error(f"创建示例附加项 {name} 失败: {e}")

def main():
    """
    主函数：初始化数据库
    """
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 获取配置环境
    config_env = os.getenv('CONFIG_ENV', 'development')
    
    # 根据环境选择数据库路径
    if config_env == 'production':
        db_path = "data/gang_hao_fan.db"
    elif config_env == 'development-remote':
        db_path = "data/gang_hao_fan_dev_remote.db"
    else:  # development
        db_path = "data/gang_hao_fan_dev.db"
    
    # 转换为绝对路径
    db_path = os.path.join(project_root, db_path)
    
    logging.info(f"开始初始化数据库: {db_path}")
    logging.info(f"配置环境: {config_env}")
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager(db_path)
        db_manager.connect()
        
        # 创建表结构
        logging.info("创建数据表...")
        create_tables(db_manager)
        
        # 创建索引
        logging.info("创建索引...")
        create_indexes(db_manager)
        
        # 插入初始数据
        logging.info("插入初始数据...")
        insert_initial_data(db_manager)
        
        # 执行数据库维护操作
        logging.info("执行数据库维护...")
        try:
            db_manager.perform_maintenance()
            logging.info("数据库维护完成")
        except Exception as e:
            logging.warning(f"数据库维护失败（不影响初始化）: {e}")
        
        # 获取数据库信息
        tables_info = []
        table_names = ['users', 'meals', 'addons', 'orders', 'ledger']
        for table_name in table_names:
            try:
                info = db_manager.get_table_info(table_name)
                tables_info.append(f"{table_name}: {info['record_count']} 条记录")
            except Exception as e:
                tables_info.append(f"{table_name}: 获取信息失败 - {e}")
        
        logging.info("数据库初始化完成!")
        logging.info("数据表状态:")
        for info in tables_info:
            logging.info(f"  - {info}")
            
    except Exception as e:
        logging.error(f"数据库初始化失败: {e}")
        sys.exit(1)
    finally:
        if 'db_manager' in locals():
            db_manager.close()

if __name__ == "__main__":
    main()