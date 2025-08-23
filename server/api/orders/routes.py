# 参考文档: doc/api.md 订单模块
# 订单相关API路由

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path

from .models import (
    CreateOrderRequest, CancelOrderRequest, CreateOrderResponse, 
    CancelOrderResponse, OrderInfo, MealInfo
)
from api.auth.routes import get_current_user, get_database
from api.auth.models import TokenData
from db.manager import DatabaseManager
from db.core_operations import CoreOperations
from db.query_operations import QueryOperations
from utils.response import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["订单"])


@router.post("", response_model=Dict[str, Any])
async def create_order(
    order_request: CreateOrderRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    创建订单
    
    参考文档: doc/api.md - 4.1 创建订单
    """
    try:
        core_ops = CoreOperations(db)
        
        # 转换附加项选择格式（字符串键转整数键）
        addon_selections = {}
        if order_request.addon_selections:
            for addon_id_str, quantity in order_request.addon_selections.items():
                try:
                    addon_id = int(addon_id_str)
                    addon_selections[addon_id] = quantity
                except ValueError:
                    return create_error_response(f"无效的附加项ID: {addon_id_str}")
        
        # 创建订单
        order_result = core_ops.create_order(
            user_id=current_user.user_id,
            meal_id=order_request.meal_id,
            addon_selections=addon_selections
        )
        
        if not order_result.get("success", True):
            return create_error_response(order_result.get("message", "订单创建失败"))
        
        # 转换附加项选择格式（整数键转字符串键）
        formatted_addon_selections = {}
        if addon_selections:
            formatted_addon_selections = {str(k): v for k, v in addon_selections.items()}
        
        response_data = CreateOrderResponse(
            order_id=order_result["order_id"],
            meal_id=order_result["meal_id"],
            amount_cents=order_result["amount_cents"],
            amount_yuan=order_result["amount_cents"] / 100.0,
            addon_selections=formatted_addon_selections,
            transaction_no=order_result["transaction_no"],
            remaining_balance_yuan=order_result["remaining_balance"] / 100.0,
            created_at=order_result["created_at"]
        )
        
        return create_success_response(
            data=response_data.dict(),
            message=order_result.get("message", f"订单创建成功，金额 {order_result['amount_cents']/100:.2f} 元")
        )
        
    except Exception as e:
        logger.error(f"创建订单失败: {str(e)}")
        return create_error_response(f"创建订单失败: {str(e)}")


@router.delete("/{order_id}", response_model=Dict[str, Any])
async def cancel_order(
    order_id: int = Path(..., description="订单ID"),
    cancel_request: CancelOrderRequest = CancelOrderRequest(),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    取消订单
    
    参考文档: doc/api.md - 4.2 取消订单
    """
    try:
        core_ops = CoreOperations(db)
        
        # 取消订单
        cancel_result = core_ops.cancel_order(
            user_id=current_user.user_id,
            order_id=order_id,
            cancel_reason=cancel_request.cancel_reason
        )
        
        if not cancel_result.get("success", True):
            return create_error_response(cancel_result.get("message", "订单取消失败"))
        
        response_data = CancelOrderResponse(
            order_id=cancel_result["order_id"],
            meal_id=cancel_result["meal_id"],
            refund_amount_yuan=cancel_result["refund_amount"] / 100.0,
            transaction_no=cancel_result["transaction_no"],
            cancel_reason=cancel_result["cancel_reason"]
        )
        
        return create_success_response(
            data=response_data.dict(),
            message=cancel_result.get("message", f"订单已取消，退款 {cancel_result['refund_amount']/100:.2f} 元")
        )
        
    except Exception as e:
        logger.error(f"取消订单失败: {str(e)}")
        return create_error_response(f"取消订单失败: {str(e)}")


@router.get("/my", response_model=Dict[str, Any])
async def get_my_orders(
    status: Optional[str] = Query(None, description="订单状态过滤"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取用户订单列表
    
    参考文档: doc/api.md - 4.3 获取用户订单列表
    """
    try:
        query_ops = QueryOperations(db)
        
        # 查询用户订单列表
        orders_result = query_ops.query_user_orders(
            user_id=current_user.user_id,
            status=status,
            offset=offset,
            limit=limit
        )
        
        if not orders_result["success"]:
            return create_error_response(orders_result["message"])
        
        orders_data = orders_result["data"]
        
        # 格式化订单数据
        formatted_orders = []
        for order in orders_data["orders"]:
            # 状态文本
            status_text_map = {
                "active": "已下单",
                "completed": "已完成", 
                "canceled": "已取消"
            }
            
            # 格式化餐次信息
            meal_info = None
            if order.get("meal_info"):
                meal_info = {
                    "meal_id": order["meal_info"]["meal_id"],
                    "date": order["meal_info"]["date"],
                    "slot": order["meal_info"]["slot"],
                    "slot_text": order["meal_info"]["slot_text"],
                    "description": order["meal_info"]["description"]
                }
            
            formatted_order = {
                "order_id": order["order_id"],
                "meal_info": meal_info,
                "amount_yuan": order["amount_yuan"],
                "addon_selections": order.get("addon_selections", {}),
                "status": order["status"],
                "status_text": status_text_map.get(order["status"], order["status"]),
                "created_at": order["created_at"]
            }
            formatted_orders.append(formatted_order)
        
        response_data = {
            "orders": formatted_orders,
            "pagination": orders_data["pagination"]
        }
        
        return create_success_response(
            data=response_data,
            message="订单列表查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取订单列表失败: {str(e)}")
        return create_error_response(f"获取订单列表失败: {str(e)}")


@router.get("/meal/{meal_id}", response_model=Dict[str, Any])
async def get_meal_order(
    meal_id: int = Path(..., description="餐次ID"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取用户在指定餐次的订单详情
    
    参考文档: doc/api.md - 4.4 获取餐次订单详情
    """
    try:
        query_ops = QueryOperations(db)
        
        # 查询用户餐次订单
        order_result = query_ops.query_user_meal_order(current_user.user_id, meal_id)
        
        if not order_result["success"]:
            return create_error_response(order_result["message"])
        
        order_data = order_result["data"]
        
        if not order_data.get("has_order"):
            return create_error_response("该餐次没有订单")
        
        # 状态文本
        status_text_map = {
            "active": "已下单",
            "completed": "已完成", 
            "canceled": "已取消"
        }
        
        # 格式化响应数据
        response_data = {
            "order_id": order_data["order_id"],
            "user_info": {
                "user_id": current_user.user_id,
                "wechat_name": order_data.get("user_name", "")
            },
            "meal_info": {
                "meal_id": meal_id,
                "date": order_data.get("meal_date"),
                "slot": order_data.get("meal_slot"),
                "slot_text": "午餐" if order_data.get("meal_slot") == "lunch" else "晚餐" if order_data.get("meal_slot") == "dinner" else order_data.get("meal_slot"),
                "description": order_data.get("meal_description")
            },
            "amount_yuan": order_data["amount_cents"] / 100.0,
            "addon_selections": order_data.get("addon_selections", {}),
            "status": order_data["order_status"],
            "status_text": status_text_map.get(order_data["order_status"], order_data["order_status"]),
            "created_at": order_data["created_at"]
        }
        
        return create_success_response(
            data=response_data,
            message="餐次订单详情查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取餐次订单详情失败: {str(e)}")
        return create_error_response(f"获取餐次订单详情失败: {str(e)}")