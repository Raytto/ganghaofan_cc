# 参考文档: doc/api.md
# 认证API测试

import pytest
import json
from fastapi.testclient import TestClient


class TestAuthRoutes:
    """认证路由测试"""
    
    def test_wechat_auth_success(self, client):
        """测试微信认证成功"""
        auth_data = {
            "code": "test_code_12345",
            "wechat_name": "测试用户",
            "avatar_url": "http://test.com/avatar.jpg"
        }
        
        response = client.post("/api/auth/wechat/login", json=auth_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "user_info" in data["data"]
        assert data["data"]["user_info"]["wechat_name"] == "测试用户"
    
    def test_wechat_auth_missing_code(self, client):
        """测试缺少微信code的认证"""
        auth_data = {
            "wechat_name": "测试用户",
            "avatar_url": "http://test.com/avatar.jpg"
        }
        
        response = client.post("/api/auth/wechat/login", json=auth_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_token_refresh(self, client):
        """测试token刷新"""
        # 先获取token
        auth_data = {
            "code": "test_code_refresh",
            "wechat_name": "刷新测试用户",
            "avatar_url": "http://test.com/refresh_avatar.jpg"
        }
        
        login_response = client.post("/api/auth/wechat/login", json=auth_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["data"]["access_token"]
        
        # 刷新token
        refresh_response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        
        assert refresh_data["success"] is True
        assert "access_token" in refresh_data["data"]
        # 新token应该与旧token不同
        assert refresh_data["data"]["access_token"] != token
    
    def test_token_refresh_invalid_token(self, client):
        """测试无效token刷新"""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
    
    def test_token_refresh_missing_token(self, client):
        """测试缺少token的刷新请求"""
        response = client.post("/api/auth/refresh")
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False


class TestTokenValidation:
    """Token验证测试"""
    
    def test_valid_token_access(self, client):
        """测试有效token访问受保护的路由"""
        # 先登录获取token
        auth_data = {
            "code": "test_code_valid",
            "wechat_name": "有效token测试",
            "avatar_url": "http://test.com/valid.jpg"
        }
        
        login_response = client.post("/api/auth/wechat/login", json=auth_data)
        token = login_response.json()["data"]["access_token"]
        
        # 使用token访问受保护的路由（比如用户信息）
        response = client.get(
            "/api/users/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_invalid_token_access(self, client):
        """测试无效token访问受保护的路由"""
        response = client.get(
            "/api/users/profile",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
    
    def test_missing_token_access(self, client):
        """测试缺少token访问受保护的路由"""
        response = client.get("/api/users/profile")
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False