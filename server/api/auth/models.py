# 参考文档: doc/api.md 认证模块
# 认证相关的数据模型

from typing import Optional
from pydantic import BaseModel, Field


class WeChatLoginRequest(BaseModel):
    """微信登录请求模型"""
    code: str = Field(..., description="微信授权码")
    wechat_name: str = Field(..., min_length=1, max_length=100, description="微信昵称")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")


class UserInfo(BaseModel):
    """用户信息模型"""
    user_id: int
    open_id: str
    wechat_name: str
    avatar_url: Optional[str] = None
    balance_cents: int
    balance_yuan: float
    is_admin: bool
    is_new_user: bool = False


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 86400  # 24小时
    user_info: UserInfo


class RefreshTokenResponse(BaseModel):
    """刷新Token响应模型"""
    access_token: str
    expires_in: int = 86400


class TokenData(BaseModel):
    """JWT Token数据模型"""
    user_id: int
    open_id: str
    is_admin: bool = False
    exp: Optional[int] = None  # 过期时间戳