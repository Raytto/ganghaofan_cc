# 参考文档: doc/api.md 用户模块
# 用户相关API路由

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from .models import UserProfileResponse, LedgerResponse, OrderStatistics, TransactionStatistics
from api.auth.routes import get_current_user, get_database
from api.auth.models import TokenData
from db.manager import DatabaseManager
from db.supporting_operations import SupportingOperations
from db.query_operations import QueryOperations
from utils.response import create_success_response, create_error_response, create_pagination_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取用户档案信息
    
    参考文档: doc/api.md - 2.1 获取用户信息
    """
    try:
        support_ops = SupportingOperations(db)
        query_ops = QueryOperations(db)
        
        # 获取用户基本信息
        user_info = support_ops.get_user_by_id(current_user.user_id)
        if not user_info:
            return create_error_response("用户不存在")
        
        # 获取订单统计
        order_stats = query_ops.query_user_order_statistics(current_user.user_id)
        order_statistics = OrderStatistics(
            total_orders=order_stats.get("total_orders", 0),
            active_orders=order_stats.get("active_orders", 0),
            completed_orders=order_stats.get("completed_orders", 0),
            canceled_orders=order_stats.get("canceled_orders", 0),
            total_spent_yuan=order_stats.get("total_spent_yuan", 0.0)
        )
        
        # 获取交易统计
        transaction_stats = query_ops.query_user_transaction_statistics(current_user.user_id)
        transaction_statistics = TransactionStatistics(
            total_transactions=transaction_stats.get("total_transactions", 0),
            recharge_count=transaction_stats.get("recharge_count", 0),
            total_recharged_yuan=transaction_stats.get("total_recharged_yuan", 0.0)
        )
        
        # 构建响应数据
        profile_data = UserProfileResponse(
            user_id=user_info["user_id"],
            open_id=user_info["open_id"],
            wechat_name=user_info.get("wechat_name") or "未注册用户",
            avatar_url=user_info.get("avatar_url"),
            balance_cents=user_info["balance_cents"],
            balance_yuan=user_info["balance_cents"] / 100.0,
            is_admin=user_info["is_admin"],
            created_at=user_info["created_at"] + "Z" if user_info["created_at"] else None,
            last_login_at=user_info["last_login_at"] + "Z" if user_info.get("last_login_at") else None,
            order_statistics=order_statistics,
            transaction_statistics=transaction_statistics
        )
        
        return create_success_response(
            data=profile_data.dict(),
            message="用户信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取用户档案失败: {str(e)}")
        return create_error_response(f"获取用户档案失败: {str(e)}")


@router.get("/ledger", response_model=Dict[str, Any])
async def get_user_ledger(
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(50, ge=1, le=200, description="每页条数"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取用户账单历史
    
    参考文档: doc/api.md - 2.2 获取账单历史
    """
    try:
        support_ops = SupportingOperations(db)
        query_ops = QueryOperations(db)
        
        # 获取用户基本信息
        user_info = support_ops.get_user_by_id(current_user.user_id)
        if not user_info:
            return create_error_response("用户不存在")
        
        # 获取账本历史
        ledger_result = query_ops.query_user_ledger_history(
            user_id=current_user.user_id,
            offset=offset,
            limit=limit
        )
        
        if not ledger_result["success"]:
            return create_error_response(ledger_result["message"])
        
        ledger_data = ledger_result["data"]
        
        # 格式化账本记录
        formatted_records = []
        for record in ledger_data["ledger_records"]:
            # 格式化余额变化显示
            balance_change = f"+{record['amount_yuan']:.2f}" if record['direction'] == 'in' else f"-{record['amount_yuan']:.2f}"
            
            # 类型文本映射
            type_text_map = {
                "recharge": "充值",
                "order": "订餐",
                "refund": "退款",
                "adjustment": "调整"
            }
            
            direction_text_map = {
                "in": "收入",
                "out": "支出"
            }
            
            formatted_record = {
                "ledger_id": record["ledger_id"],
                "transaction_no": record["transaction_no"],
                "type": record["type"],
                "type_text": type_text_map.get(record["type"], record["type"]),
                "direction": record["direction"],
                "direction_text": direction_text_map.get(record["direction"], record["direction"]),
                "amount_yuan": record["amount_yuan"],
                "balance_before_yuan": record["balance_before_yuan"],
                "balance_after_yuan": record["balance_after_yuan"],
                "balance_change": balance_change,
                "description": record.get("description"),
                "created_at": record["created_at"],
                "related_order": record.get("related_order")
            }
            formatted_records.append(formatted_record)
        
        # 构建响应数据
        response_data = {
            "user_info": {
                "user_id": user_info["user_id"],
                "wechat_name": user_info["wechat_name"],
                "current_balance_yuan": user_info["balance_cents"] / 100.0
            },
            "ledger_records": formatted_records,
            "pagination": ledger_data["pagination"]
        }
        
        return create_success_response(
            data=response_data,
            message="账单历史查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取账单历史失败: {str(e)}")
        return create_error_response(f"获取账单历史失败: {str(e)}")


@router.get("/orders", response_model=Dict[str, Any])
async def get_user_orders(
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    status: Optional[str] = Query(None, description="订单状态过滤"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取用户订单历史
    """
    try:
        query_ops = QueryOperations(db)
        
        # 获取用户订单列表
        orders_result = query_ops.query_user_orders(
            user_id=current_user.user_id,
            status=status,
            offset=offset,
            limit=limit
        )
        
        if not orders_result["success"]:
            return create_error_response(orders_result["message"])
        
        return create_success_response(
            data=orders_result["data"],
            message="订单历史查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取订单历史失败: {str(e)}")
        return create_error_response(f"获取订单历史失败: {str(e)}")