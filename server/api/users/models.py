# 参考文档: doc/api.md 用户模块
# 用户相关的数据模型

from typing import Optional, List
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """用户档案模型"""
    user_id: int
    open_id: str
    wechat_name: str
    avatar_url: Optional[str] = None
    balance_cents: int
    balance_yuan: float
    is_admin: bool
    created_at: str
    last_login_at: Optional[str] = None


class OrderStatistics(BaseModel):
    """订单统计模型"""
    total_orders: int
    active_orders: int
    completed_orders: int
    canceled_orders: int
    total_spent_yuan: float


class TransactionStatistics(BaseModel):
    """交易统计模型"""
    total_transactions: int
    recharge_count: int
    total_recharged_yuan: float


class UserProfileResponse(BaseModel):
    """用户档案响应模型"""
    user_id: int
    open_id: str
    wechat_name: str
    avatar_url: Optional[str] = None
    balance_cents: int
    balance_yuan: float
    is_admin: bool
    created_at: str
    last_login_at: Optional[str] = None
    order_statistics: OrderStatistics
    transaction_statistics: TransactionStatistics


class LedgerRecord(BaseModel):
    """账本记录模型"""
    ledger_id: int
    transaction_no: str
    type: str
    type_text: str
    direction: str
    direction_text: str
    amount_yuan: float
    balance_before_yuan: float
    balance_after_yuan: float
    balance_change: str
    description: Optional[str] = None
    created_at: str
    related_order: Optional[dict] = None


class UserLedgerInfo(BaseModel):
    """用户账本信息模型"""
    user_id: int
    wechat_name: str
    current_balance_yuan: float


class LedgerResponse(BaseModel):
    """账本历史响应模型"""
    user_info: UserLedgerInfo
    ledger_records: List[LedgerRecord]