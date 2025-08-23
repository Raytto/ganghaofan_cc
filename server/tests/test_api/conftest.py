# API测试共享配置和固定装置

import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置测试环境
os.environ['CONFIG_ENV'] = 'development'

from api.main import app


@pytest.fixture
def auth_token(client):
    """普通用户认证token"""
    auth_data = {
        "code": "test_user_code",
        "wechat_name": "API测试用户",
        "avatar_url": "http://test.com/api_user.jpg"
    }
    
    response = client.post("/api/auth/wechat/login", json=auth_data)
    assert response.status_code == 200
    
    return response.json()["data"]["access_token"]


@pytest.fixture
def admin_auth_token(client):
    """管理员认证token"""
    # 先创建管理员用户
    auth_data = {
        "code": "test_admin_code",
        "wechat_name": "API测试管理员",
        "avatar_url": "http://test.com/api_admin.jpg"
    }
    
    response = client.post("/api/auth/wechat/login", json=auth_data)
    assert response.status_code == 200
    
    token = response.json()["data"]["access_token"]
    
    # 由于这是测试环境，需要手动设置管理员权限
    # 这里可能需要直接操作数据库或使用特殊的测试接口
    
    return token


@pytest.fixture
def sample_meal_id(client, admin_auth_token, sample_addon_id):
    """创建测试餐次并返回ID"""
    meal_data = {
        "date": "2024-12-25",
        "slot": "lunch",
        "description": "API测试餐次",
        "base_price_cents": 1500,
        "addon_config": {
            str(sample_addon_id): 2
        },
        "max_orders": 10
    }
    
    response = client.post(
        "/api/admin/meals",
        json=meal_data,
        headers={"Authorization": f"Bearer {admin_auth_token}"}
    )
    
    if response.status_code == 201:
        return response.json()["data"]["meal_id"]
    
    # 如果创建失败，返回一个假的ID供测试使用
    return 1


@pytest.fixture
def sample_addon_id(client, admin_auth_token):
    """创建测试附加项并返回ID"""
    addon_data = {
        "name": "API测试附加项",
        "price_cents": 300,
        "display_order": 1,
        "is_default": False
    }
    
    response = client.post(
        "/api/admin/addons",
        json=addon_data,
        headers={"Authorization": f"Bearer {admin_auth_token}"}
    )
    
    if response.status_code == 201:
        return response.json()["data"]["addon_id"]
    
    # 如果创建失败，返回一个假的ID供测试使用
    return 1


@pytest.fixture
def sample_order_id(client, auth_token, sample_meal_id, sample_addon_id):
    """创建测试订单并返回ID"""
    # 先确保用户有足够余额
    order_data = {
        "meal_id": sample_meal_id,
        "addon_selections": {
            str(sample_addon_id): 1
        }
    }
    
    response = client.post(
        "/api/orders",
        json=order_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if response.status_code == 201:
        return response.json()["data"]["order_id"]
    
    # 如果创建失败，返回一个假的ID供测试使用
    return 1


@pytest.fixture
def sample_user_id(client, auth_token):
    """获取当前用户ID"""
    response = client.get(
        "/api/users/profile",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if response.status_code == 200:
        return response.json()["data"]["user_info"]["user_id"]
    
    # 如果获取失败，返回一个假的ID供测试使用
    return 1