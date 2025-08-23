# 参考文档: doc/api.md 订单模块
# 订单相关的数据模型

from typing import Optional, Dict
from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    """创建订单请求模型"""
    meal_id: int = Field(..., description="餐次ID")
    addon_selections: Optional[Dict[str, int]] = Field(default_factory=dict, description="附加项选择")


class CancelOrderRequest(BaseModel):
    """取消订单请求模型"""
    cancel_reason: str = Field("用户主动取消", description="取消原因")


class MealInfo(BaseModel):
    """餐次信息模型"""
    meal_id: int
    date: str
    slot: str
    slot_text: str
    description: str
    base_price_yuan: Optional[float] = None
    meal_status: Optional[str] = None


class OrderInfo(BaseModel):
    """订单信息模型"""
    order_id: int
    meal_info: MealInfo
    amount_yuan: float
    addon_selections: Dict[str, int]
    status: str
    status_text: str
    created_at: str
    updated_at: Optional[str] = None
    canceled_at: Optional[str] = None
    canceled_reason: Optional[str] = None


class CreateOrderResponse(BaseModel):
    """创建订单响应模型"""
    order_id: int
    meal_id: int
    amount_cents: int
    amount_yuan: float
    addon_selections: Dict[str, int]
    transaction_no: str
    remaining_balance_yuan: float
    created_at: str


class CancelOrderResponse(BaseModel):
    """取消订单响应模型"""
    order_id: int
    meal_id: int
    refund_amount_yuan: float
    transaction_no: str
    cancel_reason: str


class UserInfo(BaseModel):
    """用户信息模型"""
    user_id: int
    wechat_name: str


class MealOrderDetail(BaseModel):
    """餐次订单详情模型"""
    order_id: int
    user_info: UserInfo
    meal_info: MealInfo
    amount_yuan: float
    addon_selections: Dict[str, int]
    status: str
    status_text: str
    created_at: str