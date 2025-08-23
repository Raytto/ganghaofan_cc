# 参考文档: doc/api.md
# 用户API测试

import pytest
import json
from fastapi.testclient import TestClient


class TestUserProfile:
    """用户档案测试"""
    
    def test_get_profile_success(self, client, auth_token):
        """测试获取用户档案成功"""
        response = client.get(
            "/api/users/profile",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "user_info" in data["data"]
        assert "wechat_name" in data["data"]["user_info"]
        assert "balance_yuan" in data["data"]["user_info"]
    
    def test_get_profile_unauthorized(self, client):
        """测试未授权获取用户档案"""
        response = client.get("/api/users/profile")
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False


class TestUserBalance:
    """用户余额测试"""
    
    def test_get_balance(self, client, auth_token):
        """测试获取用户余额"""
        response = client.get(
            "/api/users/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "balance_yuan" in data["data"]
        assert "balance_cents" in data["data"]
        assert isinstance(data["data"]["balance_yuan"], (int, float))
        assert isinstance(data["data"]["balance_cents"], int)
    
    def test_get_balance_unauthorized(self, client):
        """测试未授权获取余额"""
        response = client.get("/api/users/balance")
        
        assert response.status_code == 401


class TestUserLedger:
    """用户账本测试"""
    
    def test_get_ledger_history(self, client, auth_token):
        """测试获取账本历史"""
        response = client.get(
            "/api/users/ledger",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "user_info" in data["data"]
        assert "ledger_records" in data["data"]
        assert isinstance(data["data"]["ledger_records"], list)
    
    def test_get_ledger_history_with_pagination(self, client, auth_token):
        """测试带分页的账本历史"""
        response = client.get(
            "/api/users/ledger?offset=0&limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "pagination" in data["data"]
        pagination = data["data"]["pagination"]
        assert "total_count" in pagination
        assert "per_page" in pagination
        assert "current_page" in pagination
    
    def test_get_ledger_unauthorized(self, client):
        """测试未授权获取账本"""
        response = client.get("/api/users/ledger")
        
        assert response.status_code == 401


class TestUserOrders:
    """用户订单测试"""
    
    def test_get_user_orders(self, client, auth_token):
        """测试获取用户订单"""
        response = client.get(
            "/api/users/orders",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "user_info" in data["data"]
        assert "orders" in data["data"]
        assert isinstance(data["data"]["orders"], list)
    
    def test_get_user_orders_with_pagination(self, client, auth_token):
        """测试带分页的用户订单"""
        response = client.get(
            "/api/users/orders?offset=0&limit=5",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "pagination" in data["data"]
    
    def test_get_user_orders_unauthorized(self, client):
        """测试未授权获取订单"""
        response = client.get("/api/users/orders")
        
        assert response.status_code == 401


class TestUserStatistics:
    """用户统计测试"""
    
    def test_get_order_statistics(self, client, auth_token):
        """测试获取订单统计"""
        response = client.get(
            "/api/users/statistics/orders",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        stats = data["data"]
        assert "total_orders" in stats
        assert "active_orders" in stats
        assert "completed_orders" in stats
        assert "canceled_orders" in stats
        assert "total_spent_yuan" in stats
    
    def test_get_transaction_statistics(self, client, auth_token):
        """测试获取交易统计"""
        response = client.get(
            "/api/users/statistics/transactions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        stats = data["data"]
        assert "total_transactions" in stats
        assert "recharge_count" in stats
        assert "total_recharged_yuan" in stats
    
    def test_get_statistics_unauthorized(self, client):
        """测试未授权获取统计"""
        response = client.get("/api/users/statistics/orders")
        assert response.status_code == 401
        
        response = client.get("/api/users/statistics/transactions")
        assert response.status_code == 401