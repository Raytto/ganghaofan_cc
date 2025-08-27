# 附加项相关API路由

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query

from api.auth.routes import get_current_user, get_database
from api.auth.models import TokenData
from db.manager import DatabaseManager
from utils.response import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/addons", tags=["附加项"])


@router.get("", response_model=Dict[str, Any])
async def get_addons_list(
    status: Optional[str] = Query("active", description="状态筛选，默认active"),
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_database)
):
    """
    获取可用附加项接口（普通用户）
    
    需求: 用户订餐页面需要获取可用的附加项列表
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
            SELECT addon_id, name, price_cents, display_order, is_default
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
                "is_default": addon[4]
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