# 参考文档: doc/api.md
# 管理员API测试

import pytest
import json
from fastapi.testclient import TestClient


class TestAdminAddons:
    """管理员附加项管理测试"""
    
    def test_create_addon_success(self, client, admin_auth_token):
        """测试成功创建附加项"""
        addon_data = {
            "name": "测试附加项",
            "price_cents": 300,
            "display_order": 1,
            "is_default": False
        }
        
        response = client.post(
            "/api/admin/addons",
            json=addon_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "addon_id" in data["data"]
        assert data["data"]["name"] == "测试附加项"
        assert data["data"]["price_cents"] == 300
    
    def test_create_addon_duplicate_name(self, client, admin_auth_token):
        """测试创建重复名称的附加项"""
        addon_data = {
            "name": "重复附加项",
            "price_cents": 200,
            "display_order": 1
        }
        
        # 第一次创建
        response1 = client.post(
            "/api/admin/addons",
            json=addon_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        # 第二次创建相同名称应该失败
        if response1.status_code == 201:
            response2 = client.post(
                "/api/admin/addons",
                json=addon_data,
                headers={"Authorization": f"Bearer {admin_auth_token}"}
            )
            
            assert response2.status_code == 400
            data = response2.json()
            assert data["success"] is False
            assert "已存在" in data.get("error", "")
    
    def test_create_addon_unauthorized(self, client, auth_token):
        """测试非管理员创建附加项"""
        addon_data = {
            "name": "非法附加项",
            "price_cents": 100
        }
        
        response = client.post(
            "/api/admin/addons",
            json=addon_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False
    
    def test_deactivate_addon_success(self, client, admin_auth_token, sample_addon_id):
        """测试成功停用附加项"""
        response = client.patch(
            f"/api/admin/addons/{sample_addon_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["addon_id"] == sample_addon_id
        assert "已停用" in data["message"]
    
    def test_deactivate_addon_nonexistent(self, client, admin_auth_token):
        """测试停用不存在的附加项"""
        response = client.patch(
            "/api/admin/addons/99999/deactivate",
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False


class TestAdminMeals:
    """管理员餐次管理测试"""
    
    def test_publish_meal_success(self, client, admin_auth_token, sample_addon_id):
        """测试成功发布餐次"""
        meal_data = {
            "date": "2024-12-30",
            "slot": "lunch",
            "description": "测试午餐",
            "base_price_cents": 1500,
            "addon_config": {
                str(sample_addon_id): 2
            },
            "max_orders": 20
        }
        
        response = client.post(
            "/api/admin/meals",
            json=meal_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "meal_id" in data["data"]
        assert data["data"]["date"] == "2024-12-30"
        assert data["data"]["slot"] == "lunch"
    
    def test_publish_meal_duplicate_slot(self, client, admin_auth_token):
        """测试发布重复时段的餐次"""
        meal_data = {
            "date": "2024-12-30",
            "slot": "lunch",
            "description": "重复午餐",
            "base_price_cents": 1200,
            "addon_config": {},
            "max_orders": 15
        }
        
        # 第一次发布
        response1 = client.post(
            "/api/admin/meals",
            json=meal_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        # 第二次发布相同日期时段应该失败
        if response1.status_code == 201:
            response2 = client.post(
                "/api/admin/meals",
                json=meal_data,
                headers={"Authorization": f"Bearer {admin_auth_token}"}
            )
            
            assert response2.status_code == 400
            data = response2.json()
            assert data["success"] is False
    
    def test_lock_meal_success(self, client, admin_auth_token, sample_meal_id):
        """测试成功锁定餐次"""
        response = client.patch(
            f"/api/admin/meals/{sample_meal_id}/lock",
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["meal_id"] == sample_meal_id
        assert "已锁定" in data["message"]
    
    def test_complete_meal_success(self, client, admin_auth_token, sample_meal_id):
        """测试成功完成餐次"""
        response = client.patch(
            f"/api/admin/meals/{sample_meal_id}/complete",
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["meal_id"] == sample_meal_id
        assert "已完成" in data["message"]
    
    def test_cancel_meal_success(self, client, admin_auth_token, sample_meal_id):
        """测试成功取消餐次"""
        cancel_data = {
            "cancel_reason": "管理员测试取消"
        }
        
        response = client.delete(
            f"/api/admin/meals/{sample_meal_id}",
            json=cancel_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["meal_id"] == sample_meal_id
        assert data["data"]["cancel_reason"] == "管理员测试取消"


class TestAdminUsers:
    """管理员用户管理测试"""
    
    def test_get_users_list(self, client, admin_auth_token):
        """测试获取用户列表"""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "users" in data["data"]
        assert "pagination" in data["data"]
        assert isinstance(data["data"]["users"], list)
    
    def test_get_users_list_with_filters(self, client, admin_auth_token):
        """测试带筛选的用户列表"""
        response = client.get(
            "/api/admin/users?is_admin=true&status=active&offset=0&limit=10",
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        # 验证筛选条件
        for user in data["data"]["users"]:
            assert user["is_admin"] is True
            assert user["status"] == "active"
    
    def test_set_user_admin_status(self, client, admin_auth_token, sample_user_id):
        """测试设置用户管理员状态"""
        admin_data = {
            "is_admin": True
        }
        
        response = client.patch(
            f"/api/admin/users/{sample_user_id}/admin",
            json=admin_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["target_user_id"] == sample_user_id
        assert data["data"]["is_admin"] is True
    
    def test_set_user_status(self, client, admin_auth_token, sample_user_id):
        """测试设置用户账户状态"""
        status_data = {
            "status": "suspended",
            "reason": "测试停用"
        }
        
        response = client.patch(
            f"/api/admin/users/{sample_user_id}/status",
            json=status_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["target_user_id"] == sample_user_id
        assert data["data"]["status"] == "suspended"
    
    def test_adjust_user_balance(self, client, admin_auth_token, sample_user_id):
        """测试调整用户余额"""
        balance_data = {
            "amount_cents": 1000,
            "reason": "测试充值"
        }
        
        response = client.patch(
            f"/api/admin/users/{sample_user_id}/balance",
            json=balance_data,
            headers={"Authorization": f"Bearer {admin_auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["target_user_id"] == sample_user_id
        assert data["data"]["adjustment_amount"] == 1000


class TestAdminPermissions:
    """管理员权限测试"""
    
    def test_non_admin_access_denied(self, client, auth_token):
        """测试非管理员访问管理员接口被拒绝"""
        # 测试各种管理员接口
        endpoints = [
            "/api/admin/users",
            "/api/admin/addons",
            "/api/admin/meals"
        ]
        
        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response.status_code == 403
            data = response.json()
            assert data["success"] is False
    
    def test_unauthenticated_access_denied(self, client):
        """测试未认证访问管理员接口被拒绝"""
        endpoints = [
            "/api/admin/users",
            "/api/admin/addons",
            "/api/admin/meals"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            
            assert response.status_code == 401
            data = response.json()
            assert data["success"] is False