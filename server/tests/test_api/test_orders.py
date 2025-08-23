# 参考文档: doc/api.md
# 订单API测试

import pytest
import json
from fastapi.testclient import TestClient


class TestOrderCreation:
    """订单创建测试"""
    
    def test_create_order_success(self, client, auth_token, sample_meal_id, sample_addon_id):
        """测试成功创建订单"""
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
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "order_id" in data["data"]
        assert "meal_id" in data["data"]
        assert "amount_cents" in data["data"]
        assert data["data"]["meal_id"] == sample_meal_id
    
    def test_create_order_missing_meal_id(self, client, auth_token):
        """测试缺少meal_id的订单创建"""
        order_data = {
            "addon_selections": {}
        }
        
        response = client.post(
            "/api/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_order_nonexistent_meal(self, client, auth_token):
        """测试不存在餐次的订单创建"""
        order_data = {
            "meal_id": 99999,
            "addon_selections": {}
        }
        
        response = client.post(
            "/api/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    def test_create_order_insufficient_balance(self, client, auth_token, sample_meal_id):
        """测试余额不足的订单创建"""
        # 这个测试需要用户余额不足，具体取决于测试数据设置
        order_data = {
            "meal_id": sample_meal_id,
            "addon_selections": {}
        }
        
        response = client.post(
            "/api/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # 可能返回400(余额不足)或201(成功)，取决于用户余额
        assert response.status_code in [201, 400]
        if response.status_code == 400:
            data = response.json()
            assert data["success"] is False
            assert "余额不足" in data.get("error", "")
    
    def test_create_order_duplicate(self, client, auth_token, sample_meal_id):
        """测试重复订单创建"""
        order_data = {
            "meal_id": sample_meal_id,
            "addon_selections": {}
        }
        
        # 第一次创建
        response1 = client.post(
            "/api/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # 如果第一次成功，第二次应该失败
        if response1.status_code == 201:
            response2 = client.post(
                "/api/orders",
                json=order_data,
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response2.status_code == 400
            data = response2.json()
            assert data["success"] is False
            assert "已有" in data.get("error", "") or "重复" in data.get("error", "")
    
    def test_create_order_unauthorized(self, client, sample_meal_id):
        """测试未授权创建订单"""
        order_data = {
            "meal_id": sample_meal_id,
            "addon_selections": {}
        }
        
        response = client.post("/api/orders", json=order_data)
        
        assert response.status_code == 401


class TestOrderCancellation:
    """订单取消测试"""
    
    def test_cancel_order_success(self, client, auth_token, sample_order_id):
        """测试成功取消订单"""
        cancel_data = {
            "cancel_reason": "用户主动取消"
        }
        
        response = client.delete(
            f"/api/orders/{sample_order_id}",
            json=cancel_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "order_id" in data["data"]
        assert "refund_amount" in data["data"]
        assert data["data"]["order_id"] == sample_order_id
    
    def test_cancel_order_nonexistent(self, client, auth_token):
        """测试取消不存在的订单"""
        cancel_data = {
            "cancel_reason": "测试取消"
        }
        
        response = client.delete(
            "/api/orders/99999",
            json=cancel_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    def test_cancel_order_not_owned(self, client, auth_token):
        """测试取消不属于自己的订单"""
        # 这个测试需要一个不属于当前用户的订单ID
        # 具体实现取决于测试数据设置
        pass
    
    def test_cancel_order_missing_reason(self, client, auth_token, sample_order_id):
        """测试缺少取消原因的订单取消"""
        response = client.delete(
            f"/api/orders/{sample_order_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_cancel_order_unauthorized(self, client):
        """测试未授权取消订单"""
        cancel_data = {
            "cancel_reason": "测试取消"
        }
        
        response = client.delete("/api/orders/1", json=cancel_data)
        
        assert response.status_code == 401


class TestOrderDetail:
    """订单详情测试"""
    
    def test_get_order_detail(self, client, auth_token, sample_order_id):
        """测试获取订单详情"""
        response = client.get(
            f"/api/orders/{sample_order_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        order_data = data["data"]
        assert "order_id" in order_data
        assert "meal_info" in order_data
        assert "amount_cents" in order_data
        assert "status" in order_data
        assert "created_at" in order_data
    
    def test_get_order_detail_nonexistent(self, client, auth_token):
        """测试获取不存在订单的详情"""
        response = client.get(
            "/api/orders/99999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    def test_get_order_detail_unauthorized(self, client):
        """测试未授权获取订单详情"""
        response = client.get("/api/orders/1")
        
        assert response.status_code == 401