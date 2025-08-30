# 参考文档: doc/api.md 管理员模块
# 管理员相关的数据模型

from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from datetime import date


class CreateAddonRequest(BaseModel):
    """创建附加项请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="附加项名称")
    price_cents: int = Field(..., description="价格（分）")
    display_order: int = Field(0, description="显示顺序")
    is_default: bool = Field(False, description="是否默认选中")


class AddonInfo(BaseModel):
    """附加项信息模型"""
    addon_id: int
    name: str
    price_cents: int
    price_yuan: float
    display_order: int
    is_default: bool
    status: str
    created_at: str


class CreateMealRequest(BaseModel):
    """发布餐次请求模型"""
    date: str = Field(..., description="餐次日期 (YYYY-MM-DD)")
    slot: str = Field(..., description="时段 (lunch/dinner)")
    description: str = Field(..., min_length=1, description="餐次描述")
    base_price_cents: int = Field(..., ge=0, description="基础价格（分）")
    addon_config: Optional[Dict[str, int]] = Field(default_factory=dict, description="附加项配置")
    max_orders: int = Field(50, ge=1, description="最大订餐数量")


class UpdateMealRequest(BaseModel):
    """更新餐次请求模型"""
    description: str = Field(..., min_length=1, description="餐次描述")
    base_price_cents: int = Field(..., ge=0, description="基础价格（分）")
    addon_config: Optional[Dict[str, int]] = Field(default_factory=dict, description="附加项配置")
    max_orders: int = Field(50, ge=1, description="最大订餐数量")


class MealInfo(BaseModel):
    """餐次信息模型"""
    meal_id: int
    date: str
    slot: str
    description: str
    base_price_yuan: float
    addon_config: Optional[Dict[str, int]] = None
    max_orders: int
    status: str
    created_at: str


class AdjustBalanceRequest(BaseModel):
    """调整用户余额请求模型"""
    target_user_id: int = Field(..., description="目标用户ID")
    amount_cents: int = Field(..., description="调整金额（分），正数为增加，负数为减少")
    reason: str = Field("管理员调整", description="调整原因")


class SetUserAdminRequest(BaseModel):
    """设置用户管理员权限请求模型"""
    target_user_id: int = Field(..., description="目标用户ID")
    is_admin: bool = Field(..., description="是否设为管理员")


class SetUserStatusRequest(BaseModel):
    """设置用户状态请求模型"""
    target_user_id: int = Field(..., description="目标用户ID")
    status: str = Field(..., description="用户状态 (active/suspended)")
    reason: Optional[str] = Field(None, description="操作原因")


class CancelMealRequest(BaseModel):
    """取消餐次请求模型"""
    cancel_reason: str = Field("管理员取消", description="取消原因")


class UserListItem(BaseModel):
    """用户列表项模型"""
    user_id: int
    open_id: str
    wechat_name: str
    avatar_url: Optional[str] = None
    balance_yuan: float
    is_admin: bool
    is_admin_text: str
    status: str
    status_text: str
    created_at: str
    last_login_at: Optional[str] = None


class StatisticsData(BaseModel):
    """统计数据模型"""
    total_users: int
    active_users: int
    total_meals: int
    total_orders: int
    total_revenue_yuan: float