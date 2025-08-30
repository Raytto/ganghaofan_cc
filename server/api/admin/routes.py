# 参考文档: doc/api.md 管理员模块
# 管理员相关API路由

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path

from .models import (
    CreateAddonRequest, AddonInfo, CreateMealRequest, MealInfo,
    AdjustBalanceRequest, SetUserAdminRequest, SetUserStatusRequest,
    CancelMealRequest, UserListItem
)
from api.auth.routes import get_admin_user, get_database
from api.auth.models import TokenData
from db.manager import DatabaseManager
from db.core_operations import CoreOperations
from db.query_operations import QueryOperations
from db.supporting_operations import SupportingOperations
from utils.response import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["管理员"])


# ===== 附加项管理 =====

@router.post("/addons", response_model=Dict[str, Any])
async def create_addon(
    addon_request: CreateAddonRequest,
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    创建附加项
    
    参考文档: doc/api.md - 5.1.1 创建附加项
    """
    try:
        core_ops = CoreOperations(db)
        
        # 创建附加项
        addon_result = core_ops.admin_create_addon(
            admin_user_id=current_admin.user_id,
            name=addon_request.name,
            price_cents=addon_request.price_cents,
            display_order=addon_request.display_order,
            is_default=addon_request.is_default
        )
        
        if not addon_result.get("success", True):
            return create_error_response(addon_result.get("message", "附加项创建失败"))
        
        response_data = {
            "addon_id": addon_result["addon_id"],
            "name": addon_request.name,
            "price_cents": addon_request.price_cents,
            "price_yuan": addon_request.price_cents / 100.0,
            "display_order": addon_request.display_order,
            "is_default": addon_request.is_default,
            "status": "active",
            "created_at": addon_result["created_at"]
        }
        
        return create_success_response(
            data=response_data,
            message=addon_result.get("message", f"附加项 \"{addon_request.name}\" 创建成功")
        )
        
    except Exception as e:
        logger.error(f"创建附加项失败: {str(e)}")
        return create_error_response(f"创建附加项失败: {str(e)}")


@router.delete("/addons/{addon_id}", response_model=Dict[str, Any])
async def deactivate_addon(
    addon_id: int = Path(..., description="附加项ID"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    停用附加项
    
    参考文档: doc/api.md - 5.1.2 停用附加项
    """
    try:
        # 使用修复后的core_operations方法
        core_ops = CoreOperations(db)
        
        deactivate_result = core_ops.admin_deactivate_addon(
            admin_user_id=current_admin.user_id,
            addon_id=addon_id
        )
        
        response_data = {
            "addon_id": deactivate_result["addon_id"],
            "addon_name": deactivate_result["addon_name"]
        }
        
        return create_success_response(
            data=response_data,
            message=deactivate_result.get("message", f"附加项 \"{deactivate_result['addon_name']}\" 已停用")
        )
        
    except Exception as e:
        logger.error(f"停用附加项失败: {str(e)}")
        return create_error_response(f"停用附加项失败: {str(e)}")


@router.get("/addons", response_model=Dict[str, Any])
async def get_addons_list(
    status: Optional[str] = Query(None, description="状态筛选 (active/inactive)"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取附加项列表
    
    参考文档: doc/api.md - 5.1.3 获取附加项列表
    """
    try:
        # 构建查询条件
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        
        # 查询附加项列表
        addons_query = f"""
            SELECT addon_id, name, price_cents, display_order, is_default, status, created_at
            FROM addons
            {where_clause}
            ORDER BY display_order, created_at
        """
        
        addons_result = db.conn.execute(addons_query, params).fetchall()
        
        # 格式化附加项数据
        addons_list = []
        for addon in addons_result:
            addon_info = {
                "addon_id": addon[0],
                "name": addon[1],
                "price_cents": addon[2],
                "price_yuan": addon[2] / 100.0,
                "display_order": addon[3],
                "is_default": addon[4],
                "status": addon[5],
                "created_at": addon[6]
            }
            addons_list.append(addon_info)
        
        response_data = {
            "addons": addons_list
        }
        
        return create_success_response(
            data=response_data,
            message="附加项列表查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取附加项列表失败: {str(e)}")
        return create_error_response(f"获取附加项列表失败: {str(e)}")


# ===== 餐次管理 =====

@router.post("/meals", response_model=Dict[str, Any])
async def publish_meal(
    meal_request: CreateMealRequest,
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    发布餐次
    
    参考文档: doc/api.md - 5.2.1 发布餐次
    """
    try:
        core_ops = CoreOperations(db)
        
        # 转换附加项配置格式（字符串键转整数键）
        addon_config = {}
        if meal_request.addon_config:
            for addon_id_str, max_quantity in meal_request.addon_config.items():
                try:
                    addon_id = int(addon_id_str)
                    addon_config[addon_id] = max_quantity
                except ValueError:
                    return create_error_response(f"无效的附加项ID: {addon_id_str}")
        
        # 发布餐次
        meal_result = core_ops.admin_publish_meal(
            admin_user_id=current_admin.user_id,
            date=meal_request.date,
            slot=meal_request.slot,
            description=meal_request.description,
            base_price_cents=meal_request.base_price_cents,
            addon_config=addon_config,
            max_orders=meal_request.max_orders
        )
        
        if not meal_result.get("success", True):
            return create_error_response(meal_result.get("message", "餐次发布失败"))
        
        # 转换附加项配置格式（整数键转字符串键）
        formatted_addon_config = {}
        if addon_config:
            formatted_addon_config = {str(k): v for k, v in addon_config.items()}
        
        response_data = {
            "meal_id": meal_result["meal_id"],
            "date": meal_result["date"],
            "slot": meal_result["slot"],
            "description": meal_request.description,
            "base_price_yuan": meal_request.base_price_cents / 100.0,
            "addon_config": formatted_addon_config,
            "max_orders": meal_request.max_orders,
            "status": "published",
            "created_at": meal_result["created_at"]
        }
        
        return create_success_response(
            data=response_data,
            message=meal_result.get("message", f"{meal_result['date']} {meal_result['slot']} 餐次发布成功")
        )
        
    except Exception as e:
        logger.error(f"发布餐次失败: {str(e)}")
        return create_error_response(f"发布餐次失败: {str(e)}")


@router.put("/meals/{meal_id}", response_model=Dict[str, Any])
async def update_meal(
    meal_request: CreateMealRequest,
    meal_id: int = Path(..., description="餐次ID"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    修改餐次信息
    
    需求: 管理员发布餐页面需要能够修改已发布餐次的配置
    """
    try:
        # 转换附加项配置格式（字符串键转整数键）
        addon_config = {}
        if meal_request.addon_config:
            for addon_id_str, max_quantity in meal_request.addon_config.items():
                try:
                    addon_id = int(addon_id_str)
                    addon_config[addon_id] = max_quantity
                except ValueError:
                    return create_error_response(f"无效的附加项ID: {addon_id_str}")

        # 构建更新数据
        update_data = {
            "description": meal_request.description,
            "base_price_cents": meal_request.base_price_cents,
            "max_orders": meal_request.max_orders
        }
        
        if addon_config:
            import json
            update_data["addon_config"] = json.dumps(addon_config)
        
        # 执行更新
        set_clauses = []
        params = []
        for key, value in update_data.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        params.append("now")  # updated_at
        params.append(meal_id)
        
        update_query = f"""
            UPDATE meals 
            SET {', '.join(set_clauses)}, updated_at = ?
            WHERE meal_id = ? AND status = 'published'
        """
        
        cursor = db.conn.execute(update_query, params)
        if cursor.rowcount == 0:
            return create_error_response("餐次不存在或状态不允许修改")
        
        # 获取更新后的餐次信息
        meal_query = """
            SELECT meal_id, date, slot, description, base_price_cents, addon_config, max_orders, updated_at
            FROM meals WHERE meal_id = ?
        """
        meal_result = db.conn.execute(meal_query, [meal_id]).fetchone()
        
        if not meal_result:
            return create_error_response("餐次信息获取失败")
        
        # 格式化响应数据
        formatted_addon_config = {}
        if meal_result[5]:  # addon_config
            import json
            try:
                addon_config_dict = json.loads(meal_result[5])
                formatted_addon_config = {str(k): v for k, v in addon_config_dict.items()}
            except (json.JSONDecodeError, TypeError):
                pass

        response_data = {
            "meal_id": meal_result[0],
            "date": meal_result[1],
            "slot": meal_result[2], 
            "description": meal_result[3],
            "base_price_yuan": meal_result[4] / 100.0,
            "addon_config": formatted_addon_config,
            "max_orders": meal_result[6],
            "status": "published",
            "updated_at": meal_result[7]
        }
        
        return create_success_response(
            data=response_data,
            message="餐次信息更新成功"
        )
        
    except Exception as e:
        logger.error(f"修改餐次失败: {str(e)}")
        return create_error_response(f"修改餐次失败: {str(e)}")


@router.put("/meals/{meal_id}/lock", response_model=Dict[str, Any])
async def lock_meal(
    meal_id: int = Path(..., description="餐次ID"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    锁定餐次
    
    参考文档: doc/api.md - 5.2.2 锁定餐次
    """
    try:
        core_ops = CoreOperations(db)
        
        # 锁定餐次
        lock_result = core_ops.admin_lock_meal(
            admin_user_id=current_admin.user_id,
            meal_id=meal_id
        )
        
        if not lock_result.get("success", True):
            return create_error_response(lock_result.get("message", "餐次锁定失败"))
        
        response_data = {
            "meal_id": lock_result["meal_id"],
            "meal_date": lock_result["meal_date"],
            "meal_slot": lock_result["meal_slot"],
            "current_orders": lock_result["current_orders"]
        }
        
        return create_success_response(
            data=response_data,
            message=lock_result.get("message", f"餐次 {lock_result['meal_date']} {lock_result['meal_slot']} 已锁定")
        )
        
    except Exception as e:
        logger.error(f"锁定餐次失败: {str(e)}")
        return create_error_response(f"锁定餐次失败: {str(e)}")


@router.put("/meals/{meal_id}/unlock", response_model=Dict[str, Any])
async def unlock_meal(
    meal_id: int = Path(..., description="餐次ID"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    取消餐次锁定
    
    需求: 管理员需要能够将锁定状态的餐次恢复为发布状态
    """
    try:
        # 检查餐次状态并更新
        update_query = """
            UPDATE meals 
            SET status = 'published', updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ? AND status = 'locked'
        """
        
        cursor = db.conn.execute(update_query, [meal_id])
        if cursor.rowcount == 0:
            return create_error_response("餐次不存在或状态不允许取消锁定")
        
        # 获取更新后的餐次信息
        meal_query = """
            SELECT meal_id, date, slot
            FROM meals WHERE meal_id = ?
        """
        meal_result = db.conn.execute(meal_query, [meal_id]).fetchone()
        
        if not meal_result:
            return create_error_response("餐次信息获取失败")
        
        response_data = {
            "meal_id": meal_result[0],
            "meal_date": meal_result[1],
            "meal_slot": meal_result[2],
            "status": "published"
        }
        
        return create_success_response(
            data=response_data,
            message="餐次锁定已取消，恢复为已发布状态"
        )
        
    except Exception as e:
        logger.error(f"取消餐次锁定失败: {str(e)}")
        return create_error_response(f"取消餐次锁定失败: {str(e)}")


@router.put("/meals/{meal_id}/complete", response_model=Dict[str, Any])
async def complete_meal(
    meal_id: int = Path(..., description="餐次ID"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    完成餐次
    
    参考文档: doc/api.md - 5.2.3 完成餐次
    """
    try:
        core_ops = CoreOperations(db)
        
        # 完成餐次
        complete_result = core_ops.admin_complete_meal(
            admin_user_id=current_admin.user_id,
            meal_id=meal_id
        )
        
        if not complete_result.get("success", True):
            return create_error_response(complete_result.get("message", "餐次完成失败"))
        
        response_data = {
            "meal_id": complete_result["meal_id"],
            "meal_date": complete_result["meal_date"],
            "meal_slot": complete_result["meal_slot"],
            "completed_orders_count": complete_result["completed_orders_count"],
            "completed_orders": complete_result.get("completed_orders", [])
        }
        
        return create_success_response(
            data=response_data,
            message=complete_result.get("message", f"餐次已完成，共完成 {complete_result['completed_orders_count']} 个订单")
        )
        
    except Exception as e:
        logger.error(f"完成餐次失败: {str(e)}")
        return create_error_response(f"完成餐次失败: {str(e)}")


@router.delete("/meals/{meal_id}", response_model=Dict[str, Any])
async def cancel_meal(
    meal_id: int = Path(..., description="餐次ID"),
    cancel_request: CancelMealRequest = CancelMealRequest(),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    取消餐次
    
    参考文档: doc/api.md - 5.2.4 取消餐次
    """
    try:
        core_ops = CoreOperations(db)
        
        # 取消餐次
        cancel_result = core_ops.admin_cancel_meal(
            admin_user_id=current_admin.user_id,
            meal_id=meal_id,
            cancel_reason=cancel_request.cancel_reason
        )
        
        if not cancel_result.get("success", True):
            return create_error_response(cancel_result.get("message", "餐次取消失败"))
        
        response_data = {
            "meal_id": cancel_result["meal_id"],
            "original_status": cancel_result.get("original_status"),
            "canceled_orders_count": cancel_result["canceled_orders_count"],
            "total_refund_amount_yuan": cancel_result["total_refund_amount"] / 100.0,
            "cancel_reason": cancel_result.get("cancel_reason")
        }
        
        return create_success_response(
            data=response_data,
            message=cancel_result.get("message", f"餐次取消成功，共退款 {cancel_result['canceled_orders_count']} 个订单")
        )
        
    except Exception as e:
        logger.error(f"取消餐次失败: {str(e)}")
        return create_error_response(f"取消餐次失败: {str(e)}")


@router.get("/meals/{meal_id}/statistics", response_model=Dict[str, Any])
async def get_meal_statistics(
    meal_id: int = Path(..., description="餐次ID"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取餐次订单统计信息
    
    需求: 管理员需要查看特定餐次的订单统计信息
    """
    try:
        # 获取餐次基本信息
        meal_query = """
            SELECT meal_id, date, slot, description
            FROM meals WHERE meal_id = ?
        """
        meal_result = db.conn.execute(meal_query, [meal_id]).fetchone()
        
        if not meal_result:
            return create_error_response("餐次不存在")
        
        # 获取订单统计
        order_stats_query = """
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_orders,
                COUNT(CASE WHEN status = 'canceled' THEN 1 END) as canceled_orders,
                COALESCE(SUM(amount_cents), 0) as total_amount_cents,
                COALESCE(SUM(CASE WHEN status = 'active' THEN amount_cents ELSE 0 END), 0) as active_amount_cents
            FROM orders WHERE meal_id = ?
        """
        order_stats = db.conn.execute(order_stats_query, [meal_id]).fetchone()
        
        # 获取附加项统计
        addon_stats_query = """
            SELECT 
                a.addon_id,
                a.name as addon_name,
                COALESCE(SUM(CAST(json_extract(o.addon_selections, '$.' || a.addon_id) AS INTEGER)), 0) as total_quantity,
                COALESCE(SUM(CAST(json_extract(o.addon_selections, '$.' || a.addon_id) AS INTEGER) * a.price_cents), 0) as total_amount_cents
            FROM addons a
            LEFT JOIN orders o ON o.meal_id = ? AND o.status = 'active'
                AND json_extract(o.addon_selections, '$.' || a.addon_id) IS NOT NULL
            WHERE a.status = 'active'
            GROUP BY a.addon_id, a.name
            HAVING total_quantity > 0
            ORDER BY total_quantity DESC
        """
        addon_stats = db.conn.execute(addon_stats_query, [meal_id]).fetchall()
        
        # 构建响应数据
        addon_statistics = []
        for addon in addon_stats:
            addon_statistics.append({
                "addon_id": addon[0],
                "addon_name": addon[1],
                "total_quantity": addon[2],
                "total_amount_yuan": addon[3] / 100.0
            })
        
        response_data = {
            "meal_info": {
                "meal_id": meal_result[0],
                "date": meal_result[1],
                "slot": meal_result[2],
                "description": meal_result[3]
            },
            "order_statistics": {
                "total_orders": order_stats[0] if order_stats else 0,
                "active_orders": order_stats[1] if order_stats else 0,
                "canceled_orders": order_stats[2] if order_stats else 0,
                "total_amount_yuan": (order_stats[3] if order_stats else 0) / 100.0,
                "active_amount_yuan": (order_stats[4] if order_stats else 0) / 100.0
            },
            "addon_statistics": addon_statistics
        }
        
        return create_success_response(
            data=response_data,
            message="餐次统计查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取餐次统计失败: {str(e)}")
        return create_error_response(f"获取餐次统计失败: {str(e)}")


# ===== 用户管理 =====

@router.get("/users", response_model=Dict[str, Any])
async def get_users_list(
    status: Optional[str] = Query(None, description="用户状态 (active/suspended)"),
    is_admin: Optional[bool] = Query(None, description="管理员筛选"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取用户列表
    
    参考文档: doc/api.md - 5.3.1 获取用户列表
    """
    try:
        support_ops = SupportingOperations(db)
        
        # 查询用户列表
        users_result = support_ops.query_users_list(
            status=status,
            is_admin=is_admin,
            offset=offset,
            limit=limit
        )
        
        if not users_result["success"]:
            return create_error_response(users_result["message"])
        
        return create_success_response(
            data=users_result["data"],
            message=users_result["message"]
        )
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        return create_error_response(f"获取用户列表失败: {str(e)}")


@router.put("/users/{user_id}/balance", response_model=Dict[str, Any])
async def adjust_user_balance(
    user_id: int = Path(..., description="用户ID"),
    balance_request: AdjustBalanceRequest = None,
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    调整用户余额
    
    参考文档: doc/api.md - 5.3.2 调整用户余额
    """
    try:
        core_ops = CoreOperations(db)
        
        # 调整用户余额
        adjust_result = core_ops.admin_adjust_balance(
            admin_user_id=current_admin.user_id,
            target_user_id=user_id,
            amount_cents=balance_request.amount_cents,
            reason=balance_request.reason
        )
        
        if not adjust_result.get("success", True):
            return create_error_response(adjust_result.get("message", "余额调整失败"))
        
        response_data = {
            "target_user_id": adjust_result["target_user_id"],
            "target_user_name": adjust_result["target_user_name"],
            "adjustment_amount_yuan": adjust_result["adjustment_amount"] / 100.0,
            "balance_before_yuan": adjust_result["balance_before"] / 100.0,
            "balance_after_yuan": adjust_result["balance_after"] / 100.0,
            "transaction_no": adjust_result["transaction_no"],
            "operation_type": adjust_result["operation_type"],
            "reason": adjust_result["reason"]
        }
        
        return create_success_response(
            data=response_data,
            message=adjust_result.get("message", "用户余额调整成功")
        )
        
    except Exception as e:
        logger.error(f"调整用户余额失败: {str(e)}")
        return create_error_response(f"调整用户余额失败: {str(e)}")


@router.post("/users/{user_id}/recharge", response_model=Dict[str, Any])
async def recharge_user(
    user_id: int = Path(..., description="用户ID"),
    recharge_request: AdjustBalanceRequest = None,
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    用户充值接口
    
    需求: 管理员用户管理页面需要独立的充值接口
    """
    try:
        if recharge_request.amount_cents <= 0:
            return create_error_response("充值金额必须大于0")
            
        core_ops = CoreOperations(db)
        
        # 执行充值操作（使用正数金额）
        recharge_result = core_ops.admin_adjust_balance(
            admin_user_id=current_admin.user_id,
            target_user_id=user_id,
            amount_cents=abs(recharge_request.amount_cents),  # 确保为正数
            reason=recharge_request.reason or "管理员充值"
        )
        
        if not recharge_result.get("success", True):
            return create_error_response(recharge_result.get("message", "充值失败"))
        
        response_data = {
            "user_id": recharge_result["target_user_id"],
            "user_name": recharge_result["target_user_name"],
            "recharge_amount_yuan": recharge_result["adjustment_amount"] / 100.0,
            "balance_before_yuan": recharge_result["balance_before"] / 100.0,
            "balance_after_yuan": recharge_result["balance_after"] / 100.0,
            "transaction_no": recharge_result["transaction_no"],
            "reason": recharge_result["reason"],
            "operator_id": current_admin.user_id,
            "operator_name": recharge_result.get("operator_name", "管理员")
        }
        
        return create_success_response(
            data=response_data,
            message=f"用户充值成功，充值金额 {recharge_result['adjustment_amount'] / 100.0:.2f} 元"
        )
        
    except Exception as e:
        logger.error(f"用户充值失败: {str(e)}")
        return create_error_response(f"用户充值失败: {str(e)}")


@router.post("/users/{user_id}/deduct", response_model=Dict[str, Any])
async def deduct_user(
    user_id: int = Path(..., description="用户ID"),
    deduct_request: AdjustBalanceRequest = None,
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    用户扣款接口
    
    需求: 管理员需要能够扣减用户余额
    """
    try:
        if deduct_request.amount_cents <= 0:
            return create_error_response("扣款金额必须大于0")
            
        core_ops = CoreOperations(db)
        
        # 执行扣款操作（使用负数金额）
        deduct_result = core_ops.admin_adjust_balance(
            admin_user_id=current_admin.user_id,
            target_user_id=user_id,
            amount_cents=-abs(deduct_request.amount_cents),  # 确保为负数
            reason=deduct_request.reason or "管理员扣款"
        )
        
        if not deduct_result.get("success", True):
            return create_error_response(deduct_result.get("message", "扣款失败"))
        
        response_data = {
            "user_id": deduct_result["target_user_id"],
            "user_name": deduct_result["target_user_name"],
            "deduct_amount_yuan": abs(deduct_result["adjustment_amount"]) / 100.0,
            "balance_before_yuan": deduct_result["balance_before"] / 100.0,
            "balance_after_yuan": deduct_result["balance_after"] / 100.0,
            "transaction_no": deduct_result["transaction_no"],
            "reason": deduct_result["reason"],
            "operator_id": current_admin.user_id,
            "operator_name": deduct_result.get("operator_name", "管理员")
        }
        
        return create_success_response(
            data=response_data,
            message=f"用户扣款成功，扣款金额 {abs(deduct_result['adjustment_amount']) / 100.0:.2f} 元"
        )
        
    except Exception as e:
        logger.error(f"用户扣款失败: {str(e)}")
        return create_error_response(f"用户扣款失败: {str(e)}")


@router.put("/users/{user_id}/admin", response_model=Dict[str, Any])
async def set_user_admin(
    user_id: int = Path(..., description="用户ID"),
    admin_request: SetUserAdminRequest = None,
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    设置用户管理员权限
    """
    try:
        support_ops = SupportingOperations(db)
        
        # 设置用户管理员权限
        admin_result = support_ops.admin_set_user_admin(
            admin_user_id=current_admin.user_id,
            target_user_id=user_id,
            is_admin=admin_request.is_admin
        )
        
        if not admin_result.get("success", True):
            return create_error_response(admin_result.get("message", "设置管理员权限失败"))
        
        return create_success_response(
            data=admin_result,
            message=admin_result.get("message", "用户权限设置成功")
        )
        
    except Exception as e:
        logger.error(f"设置用户管理员权限失败: {str(e)}")
        return create_error_response(f"设置用户管理员权限失败: {str(e)}")


@router.put("/users/{user_id}/status", response_model=Dict[str, Any])
async def set_user_status(
    user_id: int = Path(..., description="用户ID"),
    status_request: SetUserStatusRequest = None,
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    设置用户状态
    """
    try:
        support_ops = SupportingOperations(db)
        
        # 设置用户状态
        status_result = support_ops.admin_set_user_status(
            admin_user_id=current_admin.user_id,
            target_user_id=user_id,
            status=status_request.status,
            reason=status_request.reason
        )
        
        if not status_result.get("success", True):
            return create_error_response(status_result.get("message", "设置用户状态失败"))
        
        return create_success_response(
            data=status_result,
            message=status_result.get("message", "用户状态设置成功")
        )
        
    except Exception as e:
        logger.error(f"设置用户状态失败: {str(e)}")
        return create_error_response(f"设置用户状态失败: {str(e)}")


# ===== 统计信息 =====

@router.get("/statistics", response_model=Dict[str, Any])
async def get_admin_statistics(
    current_admin: TokenData = Depends(get_admin_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取管理员统计信息
    """
    try:
        # 查询统计数据
        stats_queries = [
            ("total_users", "SELECT COUNT(*) FROM users"),
            ("active_users", "SELECT COUNT(*) FROM users WHERE status = 'active'"),
            ("total_meals", "SELECT COUNT(*) FROM meals"),
            ("total_orders", "SELECT COUNT(*) FROM orders"),
            ("total_revenue", "SELECT SUM(amount_cents) FROM orders WHERE status IN ('active', 'completed')")
        ]
        
        stats_data = {}
        for stat_name, query in stats_queries:
            result = db.conn.execute(query).fetchone()
            stats_data[stat_name] = result[0] if result and result[0] is not None else 0
        
        response_data = {
            "total_users": stats_data["total_users"],
            "active_users": stats_data["active_users"],
            "total_meals": stats_data["total_meals"],
            "total_orders": stats_data["total_orders"],
            "total_revenue_yuan": stats_data["total_revenue"] / 100.0
        }
        
        return create_success_response(
            data=response_data,
            message="统计信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return create_error_response(f"获取统计信息失败: {str(e)}")