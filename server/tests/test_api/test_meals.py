# 参考文档: doc/api.md
# 餐次API测试

import pytest
import json
from fastapi.testclient import TestClient


class TestMealsList:
    """餐次列表测试"""
    
    def test_get_meals_list(self, client, auth_token):
        """测试获取餐次列表"""
        response = client.get(
            "/api/meals?start_date=2024-12-01&end_date=2024-12-31",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "meals" in data["data"]
        assert "pagination" in data["data"]
        assert isinstance(data["data"]["meals"], list)
    
    def test_get_meals_list_with_pagination(self, client, auth_token):
        """测试带分页的餐次列表"""
        response = client.get(
            "/api/meals?start_date=2024-12-01&end_date=2024-12-31&offset=0&limit=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        pagination = data["data"]["pagination"]
        assert "total_count" in pagination
        assert "per_page" in pagination
        assert "current_page" in pagination
        assert "has_next" in pagination
        assert "has_prev" in pagination
    
    def test_get_meals_missing_dates(self, client, auth_token):
        """测试缺少日期参数的餐次查询"""
        response = client.get(
            "/api/meals",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_meals_invalid_date_range(self, client, auth_token):
        """测试无效日期范围"""
        response = client.get(
            "/api/meals?start_date=2024-12-31&end_date=2024-12-01",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
    
    def test_get_meals_unauthorized(self, client):
        """测试未授权获取餐次列表"""
        response = client.get("/api/meals?start_date=2024-12-01&end_date=2024-12-31")
        
        assert response.status_code == 401


class TestMealDetail:
    """餐次详情测试"""
    
    def test_get_meal_detail(self, client, auth_token, sample_meal_id):
        """测试获取餐次详情"""
        response = client.get(
            f"/api/meals/{sample_meal_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        meal_data = data["data"]
        assert "meal_id" in meal_data
        assert "description" in meal_data
        assert "base_price_cents" in meal_data
        assert "available_addons" in meal_data
        assert "ordered_users" in meal_data
        assert "current_orders" in meal_data
        assert "max_orders" in meal_data
    
    def test_get_meal_detail_nonexistent(self, client, auth_token):
        """测试获取不存在餐次的详情"""
        response = client.get(
            "/api/meals/99999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    def test_get_meal_detail_unauthorized(self, client):
        """测试未授权获取餐次详情"""
        response = client.get("/api/meals/1")
        
        assert response.status_code == 401


class TestMealOrder:
    """餐次订单测试"""
    
    def test_check_user_meal_order(self, client, auth_token, sample_meal_id):
        """测试检查用户在特定餐次的订单"""
        response = client.get(
            f"/api/meals/{sample_meal_id}/order",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "has_order" in data["data"]
        assert isinstance(data["data"]["has_order"], bool)
        
        if data["data"]["has_order"]:
            assert "order_id" in data["data"]
            assert "order_status" in data["data"]
            assert "amount_cents" in data["data"]
    
    def test_check_user_meal_order_nonexistent_meal(self, client, auth_token):
        """测试检查不存在餐次的订单"""
        response = client.get(
            "/api/meals/99999/order",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    def test_check_user_meal_order_unauthorized(self, client):
        """测试未授权检查订单"""
        response = client.get("/api/meals/1/order")
        
        assert response.status_code == 401