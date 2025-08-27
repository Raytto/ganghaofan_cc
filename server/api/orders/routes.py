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


@router.put("/{order_id}", response_model=Dict[str, Any])
async def update_order(
    order_id: int = Path(..., description="订单ID"),
    order_request: CreateOrderRequest = None,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    修改订单
    
    需求: 用户在餐次未锁定时应该能够修改自己的订单
    """
    try:
        # 转换附加项选择格式（字符串键转整数键）
        addon_selections = {}
        if order_request.addon_selections:
            for addon_id_str, quantity in order_request.addon_selections.items():
                try:
                    addon_id = int(addon_id_str)
                    addon_selections[addon_id] = quantity
                except ValueError:
                    return create_error_response(f"无效的附加项ID: {addon_id_str}")
        
        # 获取订单信息验证权限
        order_query = """
            SELECT o.order_id, o.user_id, o.meal_id, o.amount_cents, o.addon_selections, m.status as meal_status
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            WHERE o.order_id = ? AND o.status = 'active'
        """
        order_result = db.conn.execute(order_query, [order_id]).fetchone()
        
        if not order_result:
            return create_error_response("订单不存在或已取消")
        
        if order_result[1] != current_user.user_id:
            return create_error_response("只能修改自己的订单")
        
        if order_result[5] not in ['published']:  # meal_status
            return create_error_response("餐次已锁定，无法修改订单")
        
        meal_id = order_result[2]
        old_amount_cents = order_result[3]
        
        # 重新计算订单金额
        core_ops = CoreOperations(db)
        price_result = core_ops._calculate_order_price(meal_id, addon_selections)
        if not price_result["success"]:
            return create_error_response(price_result["message"])
        
        new_amount_cents = price_result["total_amount"]
        amount_difference = new_amount_cents - old_amount_cents
        
        # 检查余额（如果需要补费）
        if amount_difference > 0:
            user_query = "SELECT balance_cents FROM users WHERE user_id = ?"
            user_result = db.conn.execute(user_query, [current_user.user_id]).fetchone()
            if not user_result or user_result[0] < amount_difference:
                return create_error_response("余额不足，无法修改订单")
        
        # 更新订单
        import json
        update_query = """
            UPDATE orders 
            SET amount_cents = ?, addon_selections = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """
        db.conn.execute(update_query, [
            new_amount_cents,
            json.dumps(addon_selections),
            order_id
        ])
        
        # 更新用户余额（如果有差额）
        if amount_difference != 0:
            balance_query = """
                UPDATE users 
                SET balance_cents = balance_cents - ?
                WHERE user_id = ?
            """
            db.conn.execute(balance_query, [amount_difference, current_user.user_id])
            
            # 记录交易（如果有差额）
            from db.supporting_operations import SupportingOperations
            support_ops = SupportingOperations(db)
            
            transaction_no = support_ops.generate_transaction_number()
            transaction_type = "order_adjustment"
            direction = "out" if amount_difference > 0 else "in"
            
            # 获取更新后的余额
            balance_result = db.conn.execute(
                "SELECT balance_cents FROM users WHERE user_id = ?", 
                [current_user.user_id]
            ).fetchone()
            balance_after = balance_result[0] if balance_result else 0
            
            ledger_query = """
                INSERT INTO ledger (transaction_no, user_id, type, direction, amount_cents, 
                    balance_before_cents, balance_after_cents, order_id, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            db.conn.execute(ledger_query, [
                transaction_no,
                current_user.user_id,
                transaction_type,
                direction,
                abs(amount_difference),
                balance_after + amount_difference,
                balance_after,
                order_id,
                f"订单修改{'补缴' if amount_difference > 0 else '退款'}"
            ])
        
        # 转换响应格式
        formatted_addon_selections = {str(k): v for k, v in addon_selections.items()}
        
        response_data = {
            "order_id": order_id,
            "meal_id": meal_id,
            "old_amount_yuan": old_amount_cents / 100.0,
            "new_amount_yuan": new_amount_cents / 100.0,
            "amount_difference_yuan": amount_difference / 100.0,
            "addon_selections": formatted_addon_selections,
            "transaction_no": transaction_no if amount_difference != 0 else None,
            "remaining_balance_yuan": (balance_after if amount_difference != 0 else None),
            "updated_at": "now"
        }
        
        message = f"订单修改成功"
        if amount_difference > 0:
            message += f"，补缴金额 {amount_difference / 100.0:.2f} 元"
        elif amount_difference < 0:
            message += f"，退款金额 {abs(amount_difference) / 100.0:.2f} 元"
        
        return create_success_response(
            data=response_data,
            message=message
        )
        
    except Exception as e:
        logger.error(f"修改订单失败: {str(e)}")
        return create_error_response(f"修改订单失败: {str(e)}")


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


@router.get("", response_model=Dict[str, Any])
async def get_orders_list(
    meal_id: Optional[int] = Query(None, description="餐次ID过滤"),
    user_id: Optional[int] = Query(None, description="用户ID过滤（管理员可用）"),
    status: Optional[str] = Query(None, description="订单状态过滤"),
    date_start: Optional[str] = Query(None, description="开始日期"),
    date_end: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取完整订单列表（带过滤）
    
    需求: 订单列表页面需要支持多维度过滤和管理员查看所有订单
    """
    try:
        from api.auth.routes import get_admin_user
        
        # 检查是否为管理员
        is_admin = False
        try:
            admin_user = await get_admin_user(current_user, db)
            is_admin = True
        except:
            is_admin = False
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        # 如果不是管理员，只能查看自己的订单
        if not is_admin:
            where_conditions.append("o.user_id = ?")
            params.append(current_user.user_id)
        elif user_id:  # 管理员可以按用户过滤
            where_conditions.append("o.user_id = ?")
            params.append(user_id)
        
        if meal_id:
            where_conditions.append("o.meal_id = ?")
            params.append(meal_id)
        
        if status:
            where_conditions.append("o.status = ?")
            params.append(status)
        
        if date_start:
            where_conditions.append("m.date >= ?")
            params.append(date_start)
        
        if date_end:
            where_conditions.append("m.date <= ?")
            params.append(date_end)
        
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        
        # 计算分页
        offset = (page - 1) * size
        
        # 查询总数
        count_query = f"""
            SELECT COUNT(*)
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            JOIN users u ON o.user_id = u.user_id
            {where_clause}
        """
        total_count = db.conn.execute(count_query, params).fetchone()[0]
        
        # 查询订单列表
        orders_query = f"""
            SELECT 
                o.order_id,
                o.user_id,
                u.wechat_name as user_name,
                o.meal_id,
                m.date as meal_date,
                m.slot as meal_slot,
                m.description as meal_description,
                o.amount_cents,
                o.addon_selections,
                o.status,
                o.created_at,
                o.updated_at
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            JOIN users u ON o.user_id = u.user_id
            {where_clause}
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([size, offset])
        
        orders_result = db.conn.execute(orders_query, params).fetchall()
        
        # 获取附加项详情
        addons_query = "SELECT addon_id, name, price_cents FROM addons WHERE status = 'active'"
        addons_result = db.conn.execute(addons_query).fetchall()
        addons_dict = {addon[0]: {"name": addon[1], "price_cents": addon[2]} for addon in addons_result}
        
        # 格式化订单数据
        formatted_orders = []
        for order in orders_result:
            # 解析附加项选择
            addon_details = []
            if order[8]:  # addon_selections
                import json
                try:
                    addon_selections = json.loads(order[8])
                    for addon_id_str, quantity in addon_selections.items():
                        addon_id = int(addon_id_str)
                        if addon_id in addons_dict and quantity > 0:
                            addon_info = addons_dict[addon_id]
                            addon_details.append({
                                "addon_id": addon_id,
                                "name": addon_info["name"],
                                "price_yuan": addon_info["price_cents"] / 100.0,
                                "quantity": quantity,
                                "total_yuan": (addon_info["price_cents"] * quantity) / 100.0
                            })
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            
            # 状态文本映射
            status_text_map = {
                "active": "有效",
                "completed": "已完成", 
                "canceled": "已取消"
            }
            
            # 餐次时段文本映射
            slot_text_map = {
                "lunch": "午餐",
                "dinner": "晚餐"
            }
            
            formatted_order = {
                "order_id": order[0],
                "user_id": order[1],
                "user_name": order[2],
                "meal_id": order[3],
                "meal_date": order[4],
                "meal_slot": order[5],
                "meal_slot_text": slot_text_map.get(order[5], order[5]),
                "meal_description": order[6],
                "amount_yuan": order[7] / 100.0,
                "addon_selections": json.loads(order[8]) if order[8] else {},
                "addon_details": addon_details,
                "status": order[9],
                "status_text": status_text_map.get(order[9], order[9]),
                "created_at": order[10],
                "updated_at": order[11]
            }
            formatted_orders.append(formatted_order)
        
        # 构建统计信息
        stats_query = f"""
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN o.status = 'active' THEN 1 END) as active_orders,
                COUNT(CASE WHEN o.status = 'canceled' THEN 1 END) as canceled_orders,
                COALESCE(SUM(o.amount_cents), 0) as total_amount_cents,
                COALESCE(SUM(CASE WHEN o.status = 'active' THEN o.amount_cents ELSE 0 END), 0) as active_amount_cents
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            JOIN users u ON o.user_id = u.user_id
            {where_clause.replace('LIMIT ? OFFSET ?', '') if 'LIMIT' not in where_clause else where_clause}
        """
        stats_params = params[:-2] if len(params) >= 2 else params  # 移除LIMIT和OFFSET参数
        stats_result = db.conn.execute(stats_query, stats_params).fetchone()
        
        statistics = {
            "total_orders": stats_result[0] if stats_result else 0,
            "active_orders": stats_result[1] if stats_result else 0,
            "canceled_orders": stats_result[2] if stats_result else 0,
            "total_amount_yuan": (stats_result[3] if stats_result else 0) / 100.0,
            "active_amount_yuan": (stats_result[4] if stats_result else 0) / 100.0
        }
        
        # 构建分页信息
        total_pages = (total_count + size - 1) // size
        pagination = {
            "total_count": total_count,
            "current_page": page,
            "per_page": size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        response_data = {
            "orders": formatted_orders,
            "pagination": pagination,
            "statistics": statistics
        }
        
        return create_success_response(
            data=response_data,
            message="订单列表查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取订单列表失败: {str(e)}")
        return create_error_response(f"获取订单列表失败: {str(e)}")