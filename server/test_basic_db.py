#!/usr/bin/env python3
# 基本数据库测试脚本 - 测试核心数据库功能

import os
import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db.manager import DatabaseManager
from db.core_operations import CoreOperations
from db.query_operations import QueryOperations
from db.supporting_operations import SupportingOperations

def test_database_basic():
    """测试基本数据库功能"""
    print("=" * 50)
    print("开始基本数据库测试")
    print("=" * 50)
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 使用内存数据库进行测试
    db_path = ":memory:"
    
    try:
        # 1. 初始化数据库管理器
        print("1. 初始化数据库管理器...")
        db_manager = DatabaseManager(db_path, auto_connect=True)
        print("✓ 数据库连接成功")
        
        # 2. 创建表结构（简化版）
        print("2. 创建基础表结构...")
        
        # 创建用户表  
        db_manager.execute_single("""
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                open_id VARCHAR(128) UNIQUE NOT NULL,
                wechat_name VARCHAR(100),
                avatar_url VARCHAR(500),
                balance_cents INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active'
            )
        """)
        
        # 创建附加项表
        db_manager.execute_single("""
            CREATE TABLE addons (
                addon_id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price_cents INTEGER NOT NULL,
                display_order INTEGER DEFAULT 0,
                is_default BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建餐次表
        db_manager.execute_single("""
            CREATE TABLE meals (
                meal_id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                slot VARCHAR(20) NOT NULL,
                description TEXT,
                base_price_cents INTEGER NOT NULL,
                addon_config JSON,
                max_orders INTEGER DEFAULT 50,
                current_orders INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'published',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                canceled_at TIMESTAMP,
                canceled_by INTEGER,
                canceled_reason TEXT,
                UNIQUE(date, slot)
            )
        """)
        
        # 创建订单表
        db_manager.execute_single("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                meal_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL,
                addon_selections JSON,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                canceled_at TIMESTAMP,
                canceled_reason TEXT,
                UNIQUE(user_id, meal_id)
            )
        """)
        
        # 创建账本表
        db_manager.execute_single("""
            CREATE TABLE ledger (
                ledger_id INTEGER PRIMARY KEY,
                transaction_no VARCHAR(32) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                type VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                amount_cents INTEGER NOT NULL,
                balance_before_cents INTEGER NOT NULL,
                balance_after_cents INTEGER NOT NULL,
                order_id INTEGER,
                description VARCHAR(200),
                operator_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("✓ 基础表结构创建成功")
        
        # 3. 初始化业务操作类
        print("3. 初始化业务操作类...")
        core_ops = CoreOperations(db_manager)
        query_ops = QueryOperations(db_manager)
        support_ops = SupportingOperations(db_manager)
        print("✓ 业务操作类初始化成功")
        
        # 4. 测试用户注册
        print("4. 测试用户注册...")
        admin_result = support_ops.register_user("admin_test", "测试管理员", "http://test.com/avatar1.jpg")
        user_result = support_ops.register_user("user_test", "测试用户", "http://test.com/avatar2.jpg")
        print(f"✓ 管理员注册成功: {admin_result['message']}")
        print(f"✓ 普通用户注册成功: {user_result['message']}")
        
        # 设置管理员权限
        admin_id = admin_result['user_id']
        user_id = user_result['user_id']
        
        # 手动设置管理员权限（因为第一个用户需要手动设置）
        db_manager.execute_single("UPDATE users SET is_admin = TRUE WHERE user_id = ?", [admin_id])
        
        # 5. 测试附加项管理
        print("5. 测试附加项管理...")
        addon_result = core_ops.admin_create_addon(admin_id, "加鸡腿", 300, 1)
        print(f"✓ 附加项创建成功: {addon_result['message']}")
        addon_id = addon_result['addon_id']
        
        # 6. 测试餐次管理
        print("6. 测试餐次管理...")
        meal_result = core_ops.admin_publish_meal(
            admin_id, "2024-12-25", "lunch", "圣诞节特餐", 1500, {addon_id: 2}, 10
        )
        print(f"✓ 餐次发布成功: {meal_result['message']}")
        meal_id = meal_result['meal_id']
        
        # 7. 测试用户充值
        print("7. 测试用户余额调整...")
        balance_result = core_ops.admin_adjust_balance(admin_id, user_id, 5000, "测试充值")
        print(f"✓ 用户充值成功: {balance_result['message']}")
        
        # 8. 测试下单
        print("8. 测试下单功能...")
        order_result = core_ops.create_order(user_id, meal_id, {addon_id: 1})
        print(f"✓ 下单成功: {order_result['message']}")
        order_id = order_result['order_id']
        
        # 9. 测试查询功能
        print("9. 测试查询功能...")
        meals_result = query_ops.query_meals_by_date_range("2024-12-24", "2024-12-26")
        print(f"✓ 餐次查询成功，找到 {len(meals_result['data']['meals'])} 个餐次")
        
        meal_detail = query_ops.query_meal_detail(meal_id)
        print(f"✓ 餐次详情查询成功，已有 {len(meal_detail['data']['ordered_users'])} 个订单")
        
        # 10. 测试订单取消
        print("10. 测试订单取消...")
        cancel_result = core_ops.cancel_order(user_id, order_id, "测试取消")
        print(f"✓ 订单取消成功: {cancel_result['message']}")
        
        print("=" * 50)
        print("✓ 所有基础功能测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'db_manager' in locals():
            db_manager.close()
    
    return True

if __name__ == "__main__":
    success = test_database_basic()
    sys.exit(0 if success else 1)