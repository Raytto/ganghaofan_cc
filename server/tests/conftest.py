# 参考文档: doc/server_structure.md 测试套件部分
# 测试配置和固定装置

import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置测试环境
os.environ['CONFIG_ENV'] = 'development'

from api.main import app
from db.manager import DatabaseManager
from db.core_operations import CoreOperations
from db.query_operations import QueryOperations
from db.supporting_operations import SupportingOperations


@pytest.fixture
def client():
    """FastAPI测试客户端"""
    return TestClient(app)


@pytest.fixture
def test_db():
    """测试数据库实例（内存数据库）"""
    db = DatabaseManager(":memory:", auto_connect=True)
    
    # 创建测试表结构
    create_test_tables(db)
    
    yield db
    db.close()


@pytest.fixture
def core_ops(test_db):
    """核心业务操作实例"""
    return CoreOperations(test_db)


@pytest.fixture
def query_ops(test_db):
    """查询业务操作实例"""
    return QueryOperations(test_db)


@pytest.fixture
def support_ops(test_db):
    """支持业务操作实例"""
    return SupportingOperations(test_db)


def create_test_tables(db: DatabaseManager):
    """创建测试表结构"""
    tables_sql = [
        # 用户表
        """
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
        """,
        
        # 附加项表
        """
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
        """,
        
        # 餐次表
        """
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
        """,
        
        # 订单表
        """
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
        """,
        
        # 账本表
        """
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
        """
    ]
    
    for sql in tables_sql:
        db.execute_single(sql)


@pytest.fixture
def sample_admin_user(support_ops):
    """创建测试管理员用户"""
    result = support_ops.register_user(
        open_id="test_admin_openid",
        wechat_name="测试管理员",
        avatar_url="http://test.com/admin.jpg"
    )
    admin_id = result['user_id']
    
    # 设置管理员权限
    support_ops.db.execute_single(
        "UPDATE users SET is_admin = TRUE WHERE user_id = ?", 
        [admin_id]
    )
    
    return admin_id


@pytest.fixture
def sample_user(support_ops):
    """创建测试普通用户"""
    result = support_ops.register_user(
        open_id="test_user_openid",
        wechat_name="测试用户",
        avatar_url="http://test.com/user.jpg"
    )
    return result['user_id']


@pytest.fixture
def sample_addon(core_ops, sample_admin_user):
    """创建测试附加项"""
    result = core_ops.admin_create_addon(
        admin_user_id=sample_admin_user,
        name="测试附加项",
        price_cents=300,
        display_order=1
    )
    return result['addon_id']


@pytest.fixture
def sample_meal(core_ops, sample_admin_user, sample_addon):
    """创建测试餐次"""
    result = core_ops.admin_publish_meal(
        admin_user_id=sample_admin_user,
        date="2024-12-25",
        slot="lunch",
        description="测试餐次",
        base_price_cents=1500,
        addon_config={sample_addon: 2},
        max_orders=10
    )
    return result['meal_id']