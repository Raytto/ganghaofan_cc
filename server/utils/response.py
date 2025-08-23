# 参考文档: doc/api.md 统一响应格式
# 统一API响应格式工具

from datetime import datetime
from typing import Any, Dict, Optional


def create_success_response(
    data: Any = None, 
    message: str = "操作成功"
) -> Dict[str, Any]:
    """
    创建成功响应
    
    Args:
        data: 响应数据
        message: 成功消息
        
    Returns:
        标准格式的成功响应
    """
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def create_error_response(
    error: str,
    data: Any = None
) -> Dict[str, Any]:
    """
    创建错误响应
    
    Args:
        error: 错误描述信息
        data: 可选的错误数据
        
    Returns:
        标准格式的错误响应
    """
    return {
        "success": False,
        "error": error,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def create_pagination_response(
    items: list,
    total_count: int,
    current_page: int,
    per_page: int,
    message: str = "查询成功"
) -> Dict[str, Any]:
    """
    创建分页响应
    
    Args:
        items: 数据项列表
        total_count: 总记录数
        current_page: 当前页码
        per_page: 每页数量
        message: 成功消息
        
    Returns:
        标准格式的分页响应
    """
    total_pages = (total_count + per_page - 1) // per_page  # 向上取整
    has_next = current_page < total_pages
    has_prev = current_page > 1
    
    return {
        "success": True,
        "data": {
            "items": items,
            "pagination": {
                "total_count": total_count,
                "current_page": current_page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        },
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }