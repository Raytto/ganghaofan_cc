# 参考文档: doc/server_structure.md
# 数据验证器

import re
from datetime import datetime
from typing import Any, Optional

def validate_date(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """
    验证日期格式
    
    Args:
        date_str: 日期字符串
        format_str: 日期格式
    
    Returns:
        验证结果
    """
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False

def validate_wechat_open_id(open_id: str) -> bool:
    """
    验证微信OpenID格式
    
    Args:
        open_id: 微信OpenID
    
    Returns:
        验证结果
    """
    if not open_id or not isinstance(open_id, str):
        return False
    
    # 微信OpenID通常是28位字符，由字母和数字组成
    if len(open_id) < 10 or len(open_id) > 128:
        return False
    
    # 基本字符检查
    if not re.match(r'^[a-zA-Z0-9_-]+$', open_id):
        return False
    
    return True

def validate_meal_slot(slot: str) -> bool:
    """
    验证餐次时段
    
    Args:
        slot: 时段字符串
    
    Returns:
        验证结果
    """
    return slot in ['lunch', 'dinner']

def validate_price_cents(price_cents: Any) -> bool:
    """
    验证价格（分）
    
    Args:
        price_cents: 价格（分）
    
    Returns:
        验证结果
    """
    try:
        price = int(price_cents)
        return price >= 0  # 价格不能为负数（附加项可以为0表示免费）
    except (ValueError, TypeError):
        return False

def validate_positive_integer(value: Any) -> bool:
    """
    验证正整数
    
    Args:
        value: 要验证的值
    
    Returns:
        验证结果
    """
    try:
        int_value = int(value)
        return int_value > 0
    except (ValueError, TypeError):
        return False

def validate_non_negative_integer(value: Any) -> bool:
    """
    验证非负整数
    
    Args:
        value: 要验证的值
    
    Returns:
        验证结果
    """
    try:
        int_value = int(value)
        return int_value >= 0
    except (ValueError, TypeError):
        return False

def validate_string_length(value: str, min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """
    验证字符串长度
    
    Args:
        value: 字符串值
        min_length: 最小长度
        max_length: 最大长度
    
    Returns:
        验证结果
    """
    if not isinstance(value, str):
        return False
    
    if len(value) < min_length:
        return False
    
    if max_length is not None and len(value) > max_length:
        return False
    
    return True

def validate_order_status(status: str) -> bool:
    """
    验证订单状态
    
    Args:
        status: 状态字符串
    
    Returns:
        验证结果
    """
    return status in ['active', 'canceled', 'completed']

def validate_meal_status(status: str) -> bool:
    """
    验证餐次状态
    
    Args:
        status: 状态字符串
    
    Returns:
        验证结果
    """
    return status in ['published', 'locked', 'completed', 'canceled']

def validate_user_status(status: str) -> bool:
    """
    验证用户状态
    
    Args:
        status: 状态字符串
    
    Returns:
        验证结果
    """
    return status in ['active', 'suspended']