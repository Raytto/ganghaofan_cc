# 参考文档: doc/api.md 餐次模块
# 餐次相关API路由

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path

from .models import MealBasic, MealDetail, AvailableAddon, OrderedUser
from api.auth.routes import get_current_user, get_database
from api.auth.models import TokenData
from db.manager import DatabaseManager
from db.query_operations import QueryOperations
from utils.response import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/meals", tags=["餐次"])


@router.get("", response_model=Dict[str, Any])
async def get_meals_list(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=60, description="每页条数"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取餐次列表
    
    参考文档: doc/api.md - 3.1 获取餐次列表
    """
    try:
        # 设置默认日期范围
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        query_ops = QueryOperations(db)
        
        # 查询餐次列表
        meals_result = query_ops.query_meals_by_date_range(
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )
        
        if not meals_result["success"]:
            return create_error_response(meals_result["message"])
        
        meals_data = meals_result["data"]
        
        # 格式化餐次数据
        formatted_meals = []
        for meal in meals_data["meals"]:
            # 时段文本
            slot_text = "午餐" if meal["slot"] == "lunch" else "晚餐" if meal["slot"] == "dinner" else meal["slot"]
            
            # 状态文本
            status_text_map = {
                "published": "已发布",
                "locked": "已锁定",
                "completed": "已完成",
                "canceled": "已取消"
            }
            
            # 日历页面状态映射：将canceled映射为unpublished
            calendar_status = "unpublished" if meal["status"] == "canceled" else meal["status"]
            
            formatted_meal = {
                "meal_id": meal["meal_id"],
                "date": meal["date"],
                "slot": meal["slot"],
                "slot_text": slot_text,
                "description": meal["description"],
                "base_price_cents": meal["base_price_cents"],
                "base_price_yuan": meal["base_price_cents"] / 100.0,
                "addon_config": meal.get("addon_config"),
                "max_orders": meal["max_orders"],
                "current_orders": meal["current_orders"],
                "available_slots": meal["max_orders"] - meal["current_orders"],
                "status": meal["status"],
                "status_text": status_text_map.get(meal["status"], meal["status"]),
                "calendar_status": calendar_status,  # 日历页面专用状态
                "created_at": meal["created_at"]
            }
            formatted_meals.append(formatted_meal)
        
        response_data = {
            "meals": formatted_meals,
            "pagination": meals_data["pagination"]
        }
        
        return create_success_response(
            data=response_data,
            message="餐次列表查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取餐次列表失败: {str(e)}")
        return create_error_response(f"获取餐次列表失败: {str(e)}")


@router.get("/{meal_id}", response_model=Dict[str, Any])
async def get_meal_detail(
    meal_id: int = Path(..., description="餐次ID"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取餐次详情
    
    参考文档: doc/api.md - 3.2 获取餐次详情
    """
    try:
        query_ops = QueryOperations(db)
        
        # 查询餐次详情
        meal_result = query_ops.query_meal_detail(meal_id)
        
        if not meal_result["success"]:
            return create_error_response(meal_result["error"])
        
        meal_data = meal_result["data"]
        
        # 时段文本
        slot_text = "午餐" if meal_data["slot"] == "lunch" else "晚餐" if meal_data["slot"] == "dinner" else meal_data["slot"]
        
        # 状态文本
        status_text_map = {
            "published": "已发布",
            "locked": "已锁定", 
            "completed": "已完成",
            "canceled": "已取消"
        }
        
        # 格式化可选附加项
        available_addons = []
        for addon in meal_data.get("available_addons", []):
            formatted_addon = {
                "addon_id": addon["addon_id"],
                "name": addon["name"],
                "price_cents": addon["price_cents"],
                "price_yuan": addon["price_cents"] / 100.0,
                "max_quantity": addon["max_quantity"],
                "status": addon["status"],
                "is_active": addon["status"] == "active"
            }
            available_addons.append(formatted_addon)
        
        # 格式化已订餐用户
        ordered_users = []
        for user in meal_data.get("ordered_users", []):
            formatted_user = {
                "order_id": user["order_id"],
                "user_id": user["user_id"],
                "wechat_name": user["wechat_name"],
                "amount_yuan": user["amount_cents"] / 100.0,
                "addon_selections": user.get("addon_selections", {}),
                "created_at": user["created_at"]
            }
            ordered_users.append(formatted_user)
        
        # 日历页面状态映射：将canceled映射为unpublished  
        calendar_status = "unpublished" if meal_data["status"] == "canceled" else meal_data["status"]
        
        # 构建详情响应
        detail_data = {
            "meal_id": meal_data["meal_id"],
            "date": meal_data["date"],
            "slot": meal_data["slot"],
            "slot_text": slot_text,
            "description": meal_data["description"],
            "base_price_cents": meal_data["base_price_cents"],
            "base_price_yuan": meal_data["base_price_cents"] / 100.0,
            "addon_config": meal_data.get("addon_config", {}),
            "max_orders": meal_data["max_orders"],
            "current_orders": meal_data["current_orders"],
            "available_slots": meal_data["max_orders"] - meal_data["current_orders"],
            "status": meal_data["status"],
            "status_text": status_text_map.get(meal_data["status"], meal_data["status"]),
            "calendar_status": calendar_status,  # 日历页面专用状态
            "available_addons": available_addons,
            "ordered_users": ordered_users
        }
        
        return create_success_response(
            data=detail_data,
            message="餐次详情查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取餐次详情失败: {str(e)}")
        return create_error_response(f"获取餐次详情失败: {str(e)}")


@router.get("/{meal_id}/my-order", response_model=Dict[str, Any])
async def get_my_meal_order(
    meal_id: int = Path(..., description="餐次ID"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取当前用户在指定餐次的订单信息
    """
    try:
        query_ops = QueryOperations(db)
        
        # 查询用户餐次订单
        order_result = query_ops.query_user_meal_order(current_user.user_id, meal_id)
        
        if not order_result["success"]:
            return create_error_response(order_result["message"])
        
        order_data = order_result["data"]
        
        # 格式化订单信息
        if order_data.get("has_order"):
            response_data = {
                "meal_id": meal_id,
                "has_order": True,
                "order_id": order_data["order_id"],
                "order_status": order_data["order_status"],
                "amount_yuan": order_data["amount_cents"] / 100.0,
                "addon_selections": order_data.get("addon_selections", {}),
                "ordered_at": order_data["created_at"]
            }
        else:
            response_data = {
                "meal_id": meal_id,
                "has_order": False,
                "order_id": None,
                "order_status": None,
                "amount_yuan": None,
                "addon_selections": None,
                "ordered_at": None
            }
        
        return create_success_response(
            data=response_data,
            message="用户餐次订单查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取用户餐次订单失败: {str(e)}")
        return create_error_response(f"获取用户餐次订单失败: {str(e)}")


@router.get("/calendar", response_model=Dict[str, Any])
async def get_calendar_meals(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(60, ge=1, le=60, description="每页条数"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取日历页面的餐次列表
    
    专门为日历页面优化的API端点，将canceled状态映射为unpublished
    """
    try:
        # 设置默认日期范围（三周：上周、本周、下周）
        if not start_date:
            # 获取上周周日
            today = datetime.now()
            days_since_sunday = (today.weekday() + 1) % 7  # 周日=0，周一=1...
            last_sunday = today - timedelta(days=days_since_sunday + 7)
            start_date = last_sunday.strftime("%Y-%m-%d")
            
        if not end_date:
            # 获取下周周六  
            today = datetime.now()
            days_since_sunday = (today.weekday() + 1) % 7
            next_saturday = today + timedelta(days=13 - days_since_sunday)
            end_date = next_saturday.strftime("%Y-%m-%d")
        
        query_ops = QueryOperations(db)
        
        # 查询餐次列表
        meals_result = query_ops.query_meals_by_date_range(
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )
        
        if not meals_result["success"]:
            return create_error_response(meals_result["message"])
        
        meals_data = meals_result["data"]
        
        # 格式化餐次数据（专门为日历页面优化）
        formatted_meals = []
        for meal in meals_data["meals"]:
            # 时段文本
            slot_text = "午餐" if meal["slot"] == "lunch" else "晚餐" if meal["slot"] == "dinner" else meal["slot"]
            
            # 日历页面状态映射：canceled -> unpublished
            calendar_status = "unpublished" if meal["status"] == "canceled" else meal["status"]
            
            # 状态文本映射（日历页面专用）
            calendar_status_text_map = {
                "published": "已发布",
                "locked": "已锁定", 
                "completed": "已完成",
                "unpublished": "未发布"  # canceled状态映射后的显示文本
            }
            
            formatted_meal = {
                "meal_id": meal["meal_id"],
                "date": meal["date"],
                "slot": meal["slot"],
                "slot_text": slot_text,
                "description": meal["description"],
                "base_price_cents": meal["base_price_cents"],
                "base_price_yuan": meal["base_price_cents"] / 100.0,
                "addon_config": meal.get("addon_config"),
                "max_orders": meal["max_orders"],
                "current_orders": meal["current_orders"],
                "available_slots": meal["max_orders"] - meal["current_orders"],
                "status": calendar_status,  # 日历页面使用映射后的状态
                "status_text": calendar_status_text_map.get(calendar_status, calendar_status),
                "original_status": meal["status"],  # 保留原始状态用于调试
                "created_at": meal["created_at"]
            }
            formatted_meals.append(formatted_meal)
        
        response_data = {
            "meals": formatted_meals,
            "pagination": meals_data["pagination"],
            "calendar_info": {
                "start_date": start_date,
                "end_date": end_date,
                "status_mapping": "canceled -> unpublished"
            }
        }
        
        return create_success_response(
            data=response_data,
            message="日历餐次列表查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取日历餐次列表失败: {str(e)}")
        return create_error_response(f"获取日历餐次列表失败: {str(e)}")