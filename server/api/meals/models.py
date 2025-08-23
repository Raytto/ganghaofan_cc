# 参考文档: doc/api.md 餐次模块
# 餐次相关的数据模型

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import date


class AvailableAddon(BaseModel):
    """可选附加项模型"""
    addon_id: int
    name: str
    price_cents: int
    price_yuan: float
    max_quantity: int
    status: str
    is_active: bool


class OrderedUser(BaseModel):
    """已订餐用户模型"""
    order_id: int
    user_id: int
    wechat_name: str
    amount_yuan: float
    addon_selections: Dict[str, int]
    created_at: str


class MealBasic(BaseModel):
    """餐次基本信息模型"""
    meal_id: int
    date: str
    slot: str
    slot_text: str
    description: str
    base_price_cents: int
    base_price_yuan: float
    addon_config: Optional[Dict[str, int]] = None
    max_orders: int
    current_orders: int
    available_slots: int
    status: str
    status_text: str
    created_at: str


class MealDetail(BaseModel):
    """餐次详情模型"""
    meal_id: int
    date: str
    slot: str
    slot_text: str
    description: str
    base_price_cents: int
    base_price_yuan: float
    max_orders: int
    current_orders: int
    available_slots: int
    status: str
    status_text: str
    available_addons: List[AvailableAddon]
    ordered_users: List[OrderedUser]


class MealsListResponse(BaseModel):
    """餐次列表响应模型"""
    meals: List[MealBasic]


class UserMealOrder(BaseModel):
    """用户餐次订单模型"""
    meal_id: int
    order_id: Optional[int] = None
    order_status: Optional[str] = None
    amount_yuan: Optional[float] = None
    addon_selections: Optional[Dict[str, int]] = None
    ordered_at: Optional[str] = None