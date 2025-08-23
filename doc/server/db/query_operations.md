# 查询业务操作伪代码

基于database_structure.md设计的查询业务操作Python+DuckDB伪代码，统一使用JSON格式返回数据。

## 设计原则

1. **统一格式**：所有查询结果使用统一的JSON格式返回
2. **分页支持**：长列表查询支持偏移量和限制条数  
3. **完整信息**：查询结果包含业务所需的完整信息
4. **性能优化**：使用索引优化常用查询
5. **错误处理**：包含完整的参数验证和异常处理

## 基础查询类

```python
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from db_manager import DatabaseManager

class QueryOperations:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def _validate_date_range(self, start_date: str, end_date: str):
        """验证日期范围格式"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("开始日期不能晚于结束日期")
        except ValueError as e:
            raise ValueError(f"日期格式错误或无效: {str(e)}")
    
    def _validate_pagination(self, offset: int, limit: int, max_limit: int):
        """验证分页参数"""
        if offset < 0:
            raise ValueError("偏移量不能为负数")
        if limit <= 0 or limit > max_limit:
            raise ValueError(f"每页条数必须在1-{max_limit}之间")
```

## 1. 查询日期范围内的餐次信息

```python
def query_meals_by_date_range(self, start_date: str, end_date: str, 
                             offset: int = 0, limit: int = 60) -> Dict[str, Any]:
    """
    查询指定日期范围内的非取消状态餐次信息
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        offset: 偏移量，默认0
        limit: 每页条数，最大60
    
    Returns:
        统一JSON格式的餐次列表和分页信息
    """
    
    # 参数验证
    self._validate_date_range(start_date, end_date)
    self._validate_pagination(offset, limit, 60)
    
    # 查询餐次信息
    meals_query = """
        SELECT 
            meal_id,
            date,
            slot,
            description,
            base_price_cents,
            addon_config,
            max_orders,
            current_orders,
            status,
            created_at,
            updated_at
        FROM meals
        WHERE date BETWEEN ? AND ? 
        AND status != 'canceled'
        ORDER BY date ASC, slot ASC
        LIMIT ? OFFSET ?
    """
    
    meals_result = self.db.conn.execute(meals_query, [start_date, end_date, limit, offset]).fetchall()
    
    # 获取总数用于分页
    count_query = """
        SELECT COUNT(*) FROM meals
        WHERE date BETWEEN ? AND ? 
        AND status != 'canceled'
    """
    total_count = self.db.conn.execute(count_query, [start_date, end_date]).fetchone()[0]
    
    # 格式化结果
    meals_list = []
    for meal in meals_result:
        # 解析addon_config
        addon_config = json.loads(meal[5]) if meal[5] else {}
        
        meals_list.append({
            "meal_id": meal[0],
            "date": meal[1],
            "slot": meal[2],
            "description": meal[3],
            "base_price_cents": meal[4],
            "base_price_yuan": meal[4] / 100,
            "addon_config": addon_config,
            "max_orders": meal[6],
            "current_orders": meal[7],
            "available_slots": meal[6] - meal[7],
            "status": meal[8],
            "status_text": {
                "published": "已发布",
                "locked": "已锁定", 
                "completed": "已完成"
            }.get(meal[8], meal[8]),
            "created_at": meal[9],
            "updated_at": meal[10]
        })
    
    return {
        "success": True,
        "data": {
            "meals": meals_list,
            "pagination": {
                "total_count": total_count,
                "current_page": offset // limit + 1,
                "per_page": limit,
                "total_pages": (total_count + limit - 1) // limit,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            }
        },
        "message": f"查询成功，共找到 {len(meals_list)} 条餐次记录"
    }
```

## 2. 查询餐次详细信息

```python
def query_meal_detail(self, meal_id: int) -> Dict[str, Any]:
    """
    查询餐次详细信息，包括附加项和已订用户列表
    
    Args:
        meal_id: 餐次ID
    
    Returns:
        餐次详细信息的JSON格式数据
    """
    
    # 查询餐次基本信息
    meal_query = """
        SELECT 
            meal_id, date, slot, description, base_price_cents,
            addon_config, max_orders, current_orders, status,
            created_at, updated_at
        FROM meals
        WHERE meal_id = ?
    """
    
    meal_result = self.db.conn.execute(meal_query, [meal_id]).fetchone()
    
    if not meal_result:
        return {
            "success": False,
            "error": "餐次不存在",
            "data": None
        }
    
    # 解析addon_config并获取附加项详细信息
    addon_config = json.loads(meal_result[5]) if meal_result[5] else {}
    addons_detail = []
    
    if addon_config:
        addon_ids = [int(k) for k in addon_config.keys()]
        addon_query = """
            SELECT addon_id, name, price_cents, status
            FROM addons
            WHERE addon_id = ANY(?)
        """
        
        addon_results = self.db.conn.execute(addon_query, [addon_ids]).fetchall()
        
        for addon in addon_results:
            addon_id_str = str(addon[0])
            max_quantity = addon_config.get(addon_id_str, 0)
            
            addons_detail.append({
                "addon_id": addon[0],
                "name": addon[1],
                "price_cents": addon[2],
                "price_yuan": addon[2] / 100,
                "max_quantity": max_quantity,
                "status": addon[3],
                "is_active": addon[3] == 'active'
            })
    
    # 查询已订用户列表（包含openid和用户名）
    orders_query = """
        SELECT 
            o.order_id,
            o.user_id,
            u.open_id,
            u.wechat_name,
            o.amount_cents,
            o.addon_selections,
            o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.meal_id = ? AND o.status = 'active'
        ORDER BY o.created_at ASC
    """
    
    orders_result = self.db.conn.execute(orders_query, [meal_id]).fetchall()
    
    orders_list = []
    for order in orders_result:
        addon_selections = json.loads(order[5]) if order[5] else {}
        
        orders_list.append({
            "order_id": order[0],
            "user_id": order[1],
            "open_id": order[2],
            "wechat_name": order[3],
            "amount_cents": order[4],
            "amount_yuan": order[4] / 100,
            "addon_selections": addon_selections,
            "created_at": order[6]
        })
    
    # 构建返回数据
    meal_data = {
        "meal_id": meal_result[0],
        "date": meal_result[1],
        "slot": meal_result[2],
        "slot_text": "午餐" if meal_result[2] == "lunch" else "晚餐",
        "description": meal_result[3],
        "base_price_cents": meal_result[4],
        "base_price_yuan": meal_result[4] / 100,
        "max_orders": meal_result[6],
        "current_orders": meal_result[7],
        "available_slots": meal_result[6] - meal_result[7],
        "status": meal_result[8],
        "status_text": {
            "published": "已发布",
            "locked": "已锁定", 
            "completed": "已完成",
            "canceled": "已取消"
        }.get(meal_result[8], meal_result[8]),
        "created_at": meal_result[9],
        "updated_at": meal_result[10],
        "available_addons": addons_detail,
        "ordered_users": orders_list
    }
    
    return {
        "success": True,
        "data": meal_data,
        "message": f"餐次详情查询成功，已有 {len(orders_list)} 个订单"
    }
```

## 3. 查询用户在特定餐次的订单信息

```python
def query_user_meal_order(self, meal_id: int, user_id: int) -> Dict[str, Any]:
    """
    查询某用户在指定餐次下的活跃订单信息
    
    Args:
        meal_id: 餐次ID
        user_id: 用户ID
    
    Returns:
        用户订单信息的JSON格式数据
    """
    
    # 查询订单信息，包含餐次和用户基本信息
    order_query = """
        SELECT 
            o.order_id,
            o.user_id,
            o.meal_id,
            o.amount_cents,
            o.addon_selections,
            o.status,
            o.created_at,
            o.updated_at,
            u.wechat_name,
            u.open_id,
            m.date,
            m.slot,
            m.description,
            m.base_price_cents,
            m.status as meal_status
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        JOIN meals m ON o.meal_id = m.meal_id
        WHERE o.meal_id = ? AND o.user_id = ? AND o.status = 'active'
    """
    
    order_result = self.db.conn.execute(order_query, [meal_id, user_id]).fetchone()
    
    if not order_result:
        # 检查餐次是否存在
        meal_exists = self.db.conn.execute(
            "SELECT meal_id FROM meals WHERE meal_id = ?", [meal_id]
        ).fetchone()
        
        # 检查用户是否存在
        user_exists = self.db.conn.execute(
            "SELECT user_id FROM users WHERE user_id = ?", [user_id]
        ).fetchone()
        
        if not meal_exists:
            error_msg = "餐次不存在"
        elif not user_exists:
            error_msg = "用户不存在"
        else:
            error_msg = "该用户在此餐次没有活跃订单"
        
        return {
            "success": False,
            "error": error_msg,
            "data": None
        }
    
    # 解析附加项选择并获取附加项详细信息
    addon_selections = json.loads(order_result[4]) if order_result[4] else {}
    selected_addons = []
    
    if addon_selections:
        addon_ids = [int(k) for k in addon_selections.keys()]
        addon_query = """
            SELECT addon_id, name, price_cents
            FROM addons
            WHERE addon_id = ANY(?)
        """
        
        addon_results = self.db.conn.execute(addon_query, [addon_ids]).fetchall()
        
        for addon in addon_results:
            addon_id_str = str(addon[0])
            quantity = addon_selections.get(addon_id_str, 0)
            total_price = addon[2] * quantity
            
            selected_addons.append({
                "addon_id": addon[0],
                "name": addon[1],
                "unit_price_cents": addon[2],
                "unit_price_yuan": addon[2] / 100,
                "quantity": quantity,
                "total_price_cents": total_price,
                "total_price_yuan": total_price / 100
            })
    
    # 构建订单详情
    order_data = {
        "order_id": order_result[0],
        "user_info": {
            "user_id": order_result[1],
            "wechat_name": order_result[8],
            "open_id": order_result[9]
        },
        "meal_info": {
            "meal_id": order_result[2],
            "date": order_result[10],
            "slot": order_result[11],
            "slot_text": "午餐" if order_result[11] == "lunch" else "晚餐",
            "description": order_result[12],
            "base_price_cents": order_result[13],
            "base_price_yuan": order_result[13] / 100,
            "meal_status": order_result[14]
        },
        "order_details": {
            "total_amount_cents": order_result[3],
            "total_amount_yuan": order_result[3] / 100,
            "base_price_cents": order_result[13],
            "base_price_yuan": order_result[13] / 100,
            "addons_price_cents": order_result[3] - order_result[13],
            "addons_price_yuan": (order_result[3] - order_result[13]) / 100,
            "selected_addons": selected_addons,
            "status": order_result[5],
            "created_at": order_result[6],
            "updated_at": order_result[7]
        }
    }
    
    return {
        "success": True,
        "data": order_data,
        "message": "订单查询成功"
    }
```

## 4. 查询用户历史账单变更信息

```python
def query_user_ledger_history(self, user_id: int, offset: int = 0, limit: int = 200) -> Dict[str, Any]:
    """
    查询用户的历史账单变更信息
    
    Args:
        user_id: 用户ID
        offset: 偏移量，默认0
        limit: 每页条数，最大200
    
    Returns:
        用户账单历史的JSON格式数据
    """
    
    # 参数验证
    self._validate_pagination(offset, limit, 200)
    
    # 检查用户是否存在
    user_info = self.db.conn.execute("""
        SELECT wechat_name, open_id, balance_cents, status
        FROM users WHERE user_id = ?
    """, [user_id]).fetchone()
    
    if not user_info:
        return {
            "success": False,
            "error": "用户不存在",
            "data": None
        }
    
    if user_info[3] != 'active':
        return {
            "success": False,
            "error": "用户账户已停用",
            "data": None
        }
    
    # 查询账单历史，包含关联的订单和餐次信息
    ledger_query = """
        SELECT 
            l.ledger_id,
            l.transaction_no,
            l.type,
            l.direction,
            l.amount_cents,
            l.balance_before_cents,
            l.balance_after_cents,
            l.order_id,
            l.description,
            l.operator_id,
            l.created_at,
            o.meal_id,
            m.date,
            m.slot,
            m.description as meal_description,
            op.wechat_name as operator_name
        FROM ledger l
        LEFT JOIN orders o ON l.order_id = o.order_id
        LEFT JOIN meals m ON o.meal_id = m.meal_id
        LEFT JOIN users op ON l.operator_id = op.user_id
        WHERE l.user_id = ?
        ORDER BY l.created_at DESC
        LIMIT ? OFFSET ?
    """
    
    ledger_result = self.db.conn.execute(ledger_query, [user_id, limit, offset]).fetchall()
    
    # 获取总数
    count_query = "SELECT COUNT(*) FROM ledger WHERE user_id = ?"
    total_count = self.db.conn.execute(count_query, [user_id]).fetchone()[0]
    
    # 格式化账单记录
    ledger_list = []
    for record in ledger_result:
        # 判断交易类型和方向
        type_text = {
            "recharge": "充值",
            "order": "订餐",
            "refund": "退款",
            "adjustment": "余额调整"
        }.get(record[2], record[2])
        
        direction_text = "收入" if record[3] == "in" else "支出"
        
        # 构建关联信息
        related_info = None
        if record[7]:  # 有关联订单
            related_info = {
                "order_id": record[7],
                "meal_info": {
                    "meal_id": record[11],
                    "date": record[12],
                    "slot": record[13],
                    "slot_text": "午餐" if record[13] == "lunch" else "晚餐" if record[13] else None,
                    "description": record[14]
                } if record[11] else None
            }
        
        ledger_list.append({
            "ledger_id": record[0],
            "transaction_no": record[1],
            "type": record[2],
            "type_text": type_text,
            "direction": record[3],
            "direction_text": direction_text,
            "amount_cents": record[4],
            "amount_yuan": record[4] / 100,
            "balance_before_cents": record[5],
            "balance_before_yuan": record[5] / 100,
            "balance_after_cents": record[6],
            "balance_after_yuan": record[6] / 100,
            "balance_change": f"+{record[4]/100:.2f}" if record[3] == "in" else f"-{record[4]/100:.2f}",
            "description": record[8],
            "operator_info": {
                "operator_id": record[9],
                "operator_name": record[15]
            } if record[9] else None,
            "related_order": related_info,
            "created_at": record[10]
        })
    
    return {
        "success": True,
        "data": {
            "user_info": {
                "user_id": user_id,
                "wechat_name": user_info[0],
                "open_id": user_info[1],
                "current_balance_cents": user_info[2],
                "current_balance_yuan": user_info[2] / 100
            },
            "ledger_records": ledger_list,
            "pagination": {
                "total_count": total_count,
                "current_page": offset // limit + 1,
                "per_page": limit,
                "total_pages": (total_count + limit - 1) // limit,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            }
        },
        "message": f"账单历史查询成功，共 {len(ledger_list)} 条记录"
    }
```

## 使用示例

```python
# 初始化
from db_manager import DatabaseManager

db_manager = DatabaseManager("gang_hao_fan.db", auto_connect=True)
query_ops = QueryOperations(db_manager)

try:
    # 1. 查询本周餐次（分页）
    meals_result = query_ops.query_meals_by_date_range(
        start_date="2024-11-25",
        end_date="2024-12-01",
        offset=0,
        limit=20
    )
    print(f"本周餐次: {meals_result}")
    
    # 2. 查询某餐次详情（包含可选附加项和已订用户）
    meal_detail = query_ops.query_meal_detail(meal_id=1)
    print(f"餐次详情: {meal_detail}")
    
    # 3. 查询特定用户的餐次订单
    user_order = query_ops.query_user_meal_order(meal_id=1, user_id=2)
    print(f"用户订单: {user_order}")
    
    # 4. 查询用户账单历史（分页）
    ledger_history = query_ops.query_user_ledger_history(
        user_id=2, 
        offset=0, 
        limit=50
    )
    print(f"账单历史: {ledger_history}")
    
finally:
    db_manager.close()
```

## 统一返回格式说明

### 成功响应格式
```json
{
    "success": true,
    "data": {
        /* 具体业务数据 */
    },
    "message": "操作成功描述"
}
```

### 失败响应格式
```json
{
    "success": false,
    "error": "错误描述信息",
    "data": null
}
```

### 分页信息格式
```json
{
    "pagination": {
        "total_count": 100,
        "current_page": 1,
        "per_page": 20,
        "total_pages": 5,
        "has_next": true,
        "has_prev": false
    }
}
```

## 查询结果示例

### 餐次列表查询结果
```json
{
    "success": true,
    "data": {
        "meals": [
            {
                "meal_id": 1,
                "date": "2024-11-27",
                "slot": "lunch",
                "description": "红烧肉套餐",
                "base_price_cents": 1500,
                "base_price_yuan": 15.0,
                "addon_config": {"1": 3, "2": 1},
                "max_orders": 50,
                "current_orders": 15,
                "available_slots": 35,
                "status": "published",
                "status_text": "已发布"
            }
        ],
        "pagination": {
            "total_count": 25,
            "current_page": 1,
            "per_page": 20,
            "total_pages": 2,
            "has_next": true,
            "has_prev": false
        }
    },
    "message": "查询成功，共找到 20 条餐次记录"
}
```

### 餐次详情查询结果
```json
{
    "success": true,
    "data": {
        "meal_id": 1,
        "date": "2024-11-27",
        "slot": "lunch",
        "slot_text": "午餐",
        "description": "红烧肉套餐",
        "base_price_cents": 1500,
        "base_price_yuan": 15.0,
        "available_addons": [
            {
                "addon_id": 1,
                "name": "加鸡腿",
                "price_cents": 300,
                "price_yuan": 3.0,
                "max_quantity": 3,
                "status": "active",
                "is_active": true
            }
        ],
        "ordered_users": [
            {
                "order_id": 1,
                "user_id": 2,
                "open_id": "wx_user_123",
                "wechat_name": "张三",
                "amount_cents": 2100,
                "amount_yuan": 21.0,
                "addon_selections": {"1": 2}
            }
        ]
    },
    "message": "餐次详情查询成功，已有 15 个订单"
}
```

## 注意事项

1. **性能优化**：所有查询基于已有索引，确保查询效率
2. **数据完整性**：查询结果包含业务所需的完整信息
3. **错误处理**：详细的参数验证和异常处理
4. **金额格式**：同时返回分和元两种格式，便于不同场景使用
5. **状态翻译**：提供中文状态描述，提升用户体验
6. **关联查询**：通过JOIN减少数据库查询次数，提高性能
7. **分页支持**：长列表查询均支持分页，避免一次性加载过多数据