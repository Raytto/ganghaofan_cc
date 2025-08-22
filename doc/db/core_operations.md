# 核心业务操作伪代码

基于database_structure.md设计的核心业务操作Python+DuckDB伪代码，用于指导正式的数据库操作代码实现。

## 设计原则

1. **串行化操作**：所有数据库读写操作串行执行，确保数据一致性
2. **不可变数据**：遵循附加项、餐次、订单的不可变原则
3. **复合操作**：复杂操作通过基础操作组合实现
4. **事务完整性**：关键操作使用事务保证原子性
5. **审计追踪**：记录所有变更的时间和操作者

## 基础操作

### 1. 导入和初始化

```python
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from db_manager import DatabaseManager

class CoreOperations:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    # 公共验证函数
    def _verify_admin_permission(self, admin_user_id: int):
        """验证管理员权限"""
        admin_check = self.db.conn.execute(
            "SELECT is_admin FROM users WHERE user_id = ? AND status = 'active'",
            [admin_user_id]
        ).fetchone()
        
        if not admin_check or not admin_check[0]:
            raise PermissionError("用户不是管理员或账户已停用")
    
    def _verify_user_status(self, user_id: int):
        """验证用户状态，返回用户信息"""
        user_info = self.db.conn.execute(
            "SELECT balance_cents, status, is_admin FROM users WHERE user_id = ?",
            [user_id]
        ).fetchone()
        
        if not user_info:
            raise ValueError(f"用户ID {user_id} 不存在")
        
        if user_info[1] != 'active':
            raise ValueError("用户账户已停用")
            
        return {
            'balance_cents': user_info[0],
            'status': user_info[1],
            'is_admin': user_info[2]
        }
    
    def _verify_addon_exists_and_active(self, addon_id: int):
        """验证附加项存在且为活跃状态，返回附加项信息"""
        addon_info = self.db.conn.execute(
            "SELECT name, status FROM addons WHERE addon_id = ?",
            [addon_id]
        ).fetchone()
        
        if not addon_info:
            raise ValueError(f"附加项ID {addon_id} 不存在")
        
        if addon_info[1] != 'active':
            raise ValueError(f"附加项 '{addon_info[0]}' 已处于非活跃状态")
            
        return {
            'name': addon_info[0],
            'status': addon_info[1]
        }
    
    def _verify_meal_exists(self, meal_id: int):
        """验证餐次存在，返回餐次信息"""
        meal_info = self.db.conn.execute(
            "SELECT date, slot, status, base_price_cents, addon_config, max_orders, current_orders FROM meals WHERE meal_id = ?",
            [meal_id]
        ).fetchone()
        
        if not meal_info:
            raise ValueError(f"餐次ID {meal_id} 不存在")
            
        return {
            'date': meal_info[0],
            'slot': meal_info[1], 
            'status': meal_info[2],
            'base_price_cents': meal_info[3],
            'addon_config': meal_info[4],
            'max_orders': meal_info[5],
            'current_orders': meal_info[6]
        }
    
    def _verify_order_exists_and_active(self, order_id: int):
        """验证订单存在且为活跃状态，返回订单信息"""
        order_info = self.db.conn.execute(
            "SELECT user_id, meal_id, amount_cents, status FROM orders WHERE order_id = ?",
            [order_id]
        ).fetchone()
        
        if not order_info:
            raise ValueError(f"订单ID {order_id} 不存在")
        
        if order_info[3] != 'active':
            raise ValueError("订单已取消或已完成，无法操作")
            
        return {
            'user_id': order_info[0],
            'meal_id': order_info[1],
            'amount_cents': order_info[2],
            'status': order_info[3]
        }
    
    def _verify_addon_ids_active(self, addon_ids: List[int]):
        """验证附加项ID列表都是活跃状态"""
        if not addon_ids:
            return
            
        valid_addons = self.db.conn.execute("""
            SELECT addon_id FROM addons 
            WHERE addon_id = ANY(?) AND status = 'active'
        """, [addon_ids]).fetchall()
        
        valid_addon_ids = [row[0] for row in valid_addons]
        invalid_addon_ids = set(addon_ids) - set(valid_addon_ids)
        
        if invalid_addon_ids:
            raise ValueError(f"无效或非活跃的附加项ID: {list(invalid_addon_ids)}")
    
    def _check_meal_slot_available(self, date: str, slot: str):
        """检查餐次时段是否可用"""
        existing_meal = self.db.conn.execute("""
            SELECT meal_id FROM meals 
            WHERE date = ? AND slot = ? AND status != 'canceled'
        """, [date, slot]).fetchone()
        
        if existing_meal:
            raise ValueError(f"{date} {slot} 时段已存在有效餐次")
    
    def _check_addon_used_by_active_meals(self, addon_id: int):
        """检查附加项是否被活跃餐次使用"""
        active_meals_using_addon = self.db.conn.execute("""
            SELECT meal_id, date, slot FROM meals 
            WHERE status IN ('published', 'locked') 
            AND addon_config IS NOT NULL 
            AND JSON_EXTRACT_STRING(addon_config, CAST(? AS VARCHAR)) IS NOT NULL
        """, [addon_id]).fetchall()
        
        if active_meals_using_addon:
            meal_details = [f"{row[1]} {row[2]}(ID:{row[0]})" for row in active_meals_using_addon]
            return meal_details
        return None
```

### 2. 管理员新增附加项操作

```python
def admin_create_addon(self, admin_user_id: int, name: str, price_cents: int, 
                      display_order: int = 0, is_default: bool = False) -> Dict[str, Any]:
    """
    管理员创建新附加项
    
    Args:
        admin_user_id: 管理员用户ID
        name: 附加项名称
        price_cents: 价格（分）
        display_order: 显示顺序
        is_default: 是否默认选中
    
    Returns:
        Dict包含新创建的addon_id和操作结果
    """
    
    def create_addon_operation():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 检查附加项名称是否已存在（active状态）
        existing_addon = self.db.conn.execute(
            "SELECT addon_id FROM addons WHERE name = ? AND status = 'active'",
            [name]
        ).fetchone()
        
        if existing_addon:
            raise ValueError(f"附加项名称 '{name}' 已存在")
        
        # 创建新附加项
        result = self.db.conn.execute("""
            INSERT INTO addons (name, price_cents, display_order, is_default, status, created_at)
            VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            RETURNING addon_id, created_at
        """, [name, price_cents, display_order, is_default])
        
        addon_data = result.fetchone()
        
        return {
            'addon_id': addon_data[0],
            'created_at': addon_data[1],
            'message': f'附加项 "{name}" 创建成功'
        }
    
    return self.db.execute_transaction([create_addon_operation])[0]
```

### 3. 管理员停用附加项操作

```python
def admin_deactivate_addon(self, admin_user_id: int, addon_id: int) -> Dict[str, Any]:
    """
    管理员停用活跃的附加项
    
    Args:
        admin_user_id: 管理员用户ID
        addon_id: 附加项ID
    
    Returns:
        操作结果
    """
    
    def deactivate_addon_operation():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 检查附加项是否存在且为active状态
        addon_info = self._verify_addon_exists_and_active(addon_id)
        
        # 检查是否有活跃状态的餐次正在使用该附加项
        meal_details = self._check_addon_used_by_active_meals(addon_id)
        if meal_details:
            raise ValueError(f"附加项 '{addon_info['name']}' 正被以下活跃餐次使用，无法停用: {', '.join(meal_details)}")
        
        # 停用附加项
        self.db.conn.execute("""
            UPDATE addons 
            SET status = 'inactive', updated_at = CURRENT_TIMESTAMP
            WHERE addon_id = ?
        """, [addon_id])
        
        return {
            'addon_id': addon_id,
            'addon_name': addon_info['name'],
            'message': f'附加项 "{addon_info["name"]}" 已停用'
        }
    
    return self.db.execute_transaction([deactivate_addon_operation])[0]
```

### 4. 管理员发布餐次操作

```python
def admin_publish_meal(self, admin_user_id: int, date: str, slot: str, 
                      description: str, base_price_cents: int, 
                      addon_config: Dict[int, int], max_orders: int = 50) -> Dict[str, Any]:
    """
    管理员发布餐次
    
    Args:
        admin_user_id: 管理员用户ID
        date: 餐次日期 (YYYY-MM-DD)
        slot: 时段 (lunch/dinner)
        description: 餐次描述
        base_price_cents: 基础价格（分）
        addon_config: 附加项配置字典 {addon_id: max_quantity}
        max_orders: 最大订餐数量
    
    Returns:
        包含新创建meal_id的操作结果
    """
    
    def publish_meal_operation():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 检查该日期时段是否已有非取消状态的餐次
        self._check_meal_slot_available(date, slot)
        
        # 验证所有addon_ids都是活跃状态
        if addon_config:
            addon_ids = list(addon_config.keys())
            self._verify_addon_ids_active(addon_ids)
        
        # 将addon_config转换为JSON字符串
        import json
        addon_config_json = json.dumps({str(k): v for k, v in addon_config.items()}) if addon_config else None
        
        # 创建餐次
        result = self.db.conn.execute("""
            INSERT INTO meals (date, slot, description, base_price_cents, addon_config, 
                             max_orders, current_orders, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'published', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING meal_id, created_at
        """, [date, slot, description, base_price_cents, addon_config_json, max_orders])
        
        meal_data = result.fetchone()
        
        return {
            'meal_id': meal_data[0],
            'date': date,
            'slot': slot,
            'created_at': meal_data[1],
            'message': f'{date} {slot} 餐次发布成功'
        }
    
    return self.db.execute_transaction([publish_meal_operation])[0]
```

### 5. 管理员锁定餐次操作

```python
def admin_lock_meal(self, admin_user_id: int, meal_id: int) -> Dict[str, Any]:
    """
    管理员锁定餐次
    
    Args:
        admin_user_id: 管理员用户ID
        meal_id: 餐次ID
    
    Returns:
        操作结果
    """
    
    def lock_meal_operation():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 获取餐次信息
        meal_info = self._verify_meal_exists(meal_id)
        
        if meal_info['status'] != 'published':
            raise ValueError(f"只能锁定已发布的餐次，当前状态: {meal_info['status']}")
        
        # 锁定餐次
        self.db.conn.execute("""
            UPDATE meals 
            SET status = 'locked', 
                updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ?
        """, [meal_id])
        
        return {
            'meal_id': meal_id,
            'meal_date': meal_info['date'],
            'meal_slot': meal_info['slot'],
            'current_orders': meal_info['current_orders'],
            'message': f'餐次 {meal_info["date"]} {meal_info["slot"]} 已锁定，当前订单数: {meal_info["current_orders"]}'
        }
    
    return self.db.execute_transaction([lock_meal_operation])[0]
```

### 6. 管理员完成餐次操作

```python
def admin_complete_meal(self, admin_user_id: int, meal_id: int) -> Dict[str, Any]:
    """
    管理员完成餐次
    
    Args:
        admin_user_id: 管理员用户ID
        meal_id: 餐次ID
    
    Returns:
        操作结果
    """
    
    def complete_meal_operation():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 获取餐次信息
        meal_info = self._verify_meal_exists(meal_id)
        
        if meal_info['status'] not in ['published', 'locked']:
            raise ValueError(f"只能完成已发布或已锁定的餐次，当前状态: {meal_info['status']}")
        
        # 完成餐次
        self.db.conn.execute("""
            UPDATE meals 
            SET status = 'completed', 
                updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ?
        """, [meal_id])
        
        # 将所有active订单状态改为completed
        completed_orders = self.db.conn.execute("""
            UPDATE orders 
            SET status = 'completed',
                updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ? AND status = 'active'
            RETURNING order_id, user_id
        """, [meal_id]).fetchall()
        
        return {
            'meal_id': meal_id,
            'meal_date': meal_info['date'],
            'meal_slot': meal_info['slot'],
            'completed_orders_count': len(completed_orders),
            'completed_orders': [{'order_id': row[0], 'user_id': row[1]} for row in completed_orders],
            'message': f'餐次 {meal_info["date"]} {meal_info["slot"]} 已完成，共完成 {len(completed_orders)} 个订单'
        }
    
    return self.db.execute_transaction([complete_meal_operation])[0]
```

### 7. 管理员取消餐次操作

```python
def admin_cancel_meal(self, admin_user_id: int, meal_id: int) -> Dict[str, Any]:
    """
    管理员取消餐次（复合操作：取消餐次 + 取消所有相关订单）
    
    Args:
        admin_user_id: 管理员用户ID
        meal_id: 餐次ID
    
    Returns:
        操作结果，包含取消的餐次和订单信息
    """
    
    def cancel_meal_and_orders():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 获取餐次信息
        meal_info = self._verify_meal_exists(meal_id)
        
        if meal_info['status'] == 'canceled':
            raise ValueError(f"餐次 {meal_info['date']} {meal_info['slot']} 已被取消")
        
        # 获取所有相关的active订单
        active_orders = self.db.conn.execute("""
            SELECT order_id, user_id, amount_cents FROM orders 
            WHERE meal_id = ? AND status = 'active'
        """, [meal_id]).fetchall()
        
        # 1. 取消餐次
        self.db.conn.execute("""
            UPDATE meals 
            SET status = 'canceled', 
                canceled_at = CURRENT_TIMESTAMP,
                canceled_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ?
        """, [admin_user_id, meal_id])
        
        # 2. 取消所有相关订单并退款
        canceled_orders = []
        for order_id, user_id, amount_cents in active_orders:
            # 取消订单
            self.db.conn.execute("""
                UPDATE orders 
                SET status = 'canceled',
                    canceled_at = CURRENT_TIMESTAMP,
                    canceled_reason = '餐次被管理员取消',
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, [order_id])
            
            # 退款处理
            refund_result = self._process_refund(user_id, amount_cents, order_id, 
                                               f"餐次取消退款-订单{order_id}")
            
            canceled_orders.append({
                'order_id': order_id,
                'user_id': user_id,
                'refund_amount': amount_cents,
                'refund_transaction': refund_result['transaction_no']
            })
        
        # 更新餐次的当前订单数
        self.db.conn.execute("""
            UPDATE meals SET current_orders = 0 WHERE meal_id = ?
        """, [meal_id])
        
        return {
            'meal_id': meal_id,
            'meal_date': meal_info['date'],
            'meal_slot': meal_info['slot'],
            'canceled_orders_count': len(canceled_orders),
            'canceled_orders': canceled_orders,
            'message': f'餐次 {meal_info["date"]} {meal_info["slot"]} 及其 {len(canceled_orders)} 个订单已取消'
        }
    
    return self.db.execute_transaction([cancel_meal_and_orders])
```

### 6. 用户/管理员下单操作

```python
def create_order(self, user_id: int, meal_id: int, addon_selections: Dict[int, int]) -> Dict[str, Any]:
    """
    用户/管理员对某餐次下单
    
    Args:
        user_id: 用户ID
        meal_id: 餐次ID
        addon_selections: 附加项选择字典 {addon_id: quantity}
    
    Returns:
        订单创建结果
    """
    
    def create_order_operation():
        # 验证用户状态
        user_info = self._verify_user_status(user_id)
        
        # 验证餐次状态和信息
        meal_info = self._verify_meal_exists(meal_id)
        
        if meal_info['status'] != 'published':
            raise ValueError(f"餐次状态为{meal_info['status']}，无法订餐")
        
        # 检查是否已有active订单
        existing_order = self.db.conn.execute("""
            SELECT order_id FROM orders 
            WHERE user_id = ? AND meal_id = ? AND status = 'active'
        """, [user_id, meal_id]).fetchone()
        
        if existing_order:
            raise ValueError(f"用户已有该餐次的有效订单 {existing_order[0]}")
        
        # 检查餐次容量
        if meal_info['current_orders'] >= meal_info['max_orders']:
            raise ValueError("餐次已满，无法下单")
        
        # 解析餐次附加项配置
        import json
        allowed_addon_config = json.loads(meal_info['addon_config']) if meal_info['addon_config'] else {}
        allowed_addon_ids = [int(k) for k in allowed_addon_config.keys()]
        
        # 验证选择的附加项和数量
        base_price = meal_info['base_price_cents']
        total_amount = base_price
        
        if addon_selections:
            # 验证附加项ID是否允许
            invalid_addons = set(addon_selections.keys()) - set(allowed_addon_ids)
            if invalid_addons:
                raise ValueError(f"选择了不允许的附加项: {list(invalid_addons)}")
            
            # 验证数量不超过限制
            for addon_id, quantity in addon_selections.items():
                max_quantity = allowed_addon_config.get(str(addon_id), 0)
                if quantity > max_quantity:
                    raise ValueError(f"附加项{addon_id}最多只能选择{max_quantity}个，当前选择{quantity}个")
                
                if quantity <= 0:
                    raise ValueError(f"附加项{addon_id}数量必须大于0")
            
            # 计算附加项总价格
            for addon_id, quantity in addon_selections.items():
                addon_price = self.db.conn.execute("""
                    SELECT price_cents FROM addons 
                    WHERE addon_id = ? AND status = 'active'
                """, [addon_id]).fetchone()
                
                if not addon_price:
                    raise ValueError(f"附加项{addon_id}不存在或已停用")
                
                total_amount += addon_price[0] * quantity
        
        # 验证用户余额
        if user_info['balance_cents'] < total_amount:
            raise ValueError(f"余额不足，需要 {total_amount/100:.2f} 元，当前余额 {user_info['balance_cents']/100:.2f} 元")
        
        # 将addon_selections转换为JSON字符串
        addon_selections_json = json.dumps({str(k): v for k, v in addon_selections.items()}) if addon_selections else None
        
        # 创建订单
        order_result = self.db.conn.execute("""
            INSERT INTO orders (user_id, meal_id, amount_cents, addon_selections, status, 
                              created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING order_id, created_at
        """, [user_id, meal_id, total_amount, addon_selections_json])
        
        order_data = order_result.fetchone()
        order_id = order_data[0]
        
        # 扣款处理
        deduction_result = self._process_payment(user_id, total_amount, order_id,
                                               f"订餐付款-订单{order_id}")
        
        # 更新餐次当前订单数
        self.db.conn.execute("""
            UPDATE meals 
            SET current_orders = current_orders + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ?
        """, [meal_id])
        
        return {
            'order_id': order_id,
            'meal_id': meal_id,
            'amount_cents': total_amount,
            'addon_selections': addon_selections,
            'created_at': order_data[1],
            'transaction_no': deduction_result['transaction_no'],
            'remaining_balance': deduction_result['balance_after'],
            'message': f'订单创建成功，金额 {total_amount/100:.2f} 元'
        }
    
    return self.db.execute_transaction([create_order_operation])[0]
```

### 7. 用户/管理员取消订单操作

```python
def cancel_order(self, user_id: int, order_id: int, cancel_reason: str = "用户主动取消") -> Dict[str, Any]:
    """
    用户/管理员取消某订单
    
    Args:
        user_id: 用户ID
        order_id: 订单ID
        cancel_reason: 取消原因
    
    Returns:
        取消结果
    """
    
    def cancel_order_operation():
        # 验证订单信息
        order_info = self._verify_order_exists_and_active(order_id)
        
        # 验证用户权限（用户只能取消自己的订单，管理员可以取消任何订单）
        user_check = self._verify_user_status(user_id)
        
        is_admin = user_check['is_admin']
        order_owner_id = order_info['user_id']
        
        if not is_admin and user_id != order_owner_id:
            raise PermissionError("用户只能取消自己的订单")
        
        # 检查餐次状态和用户权限
        meal_info = self._verify_meal_exists(order_info['meal_id'])
        
        # 普通用户不能取消锁定或完成状态的餐次订单
        if not is_admin and meal_info['status'] in ['locked', 'completed']:
            raise ValueError(f"餐次状态为{meal_info['status']}，普通用户无法取消订单")
        
        # 管理员不能取消已完成餐次的订单
        if is_admin and meal_info['status'] == 'completed':
            raise ValueError("餐次已完成，无法取消订单")
        
        # 取消订单
        self.db.conn.execute("""
            UPDATE orders 
            SET status = 'canceled',
                canceled_at = CURRENT_TIMESTAMP,
                canceled_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ?
        """, [cancel_reason, order_id])
        
        # 退款处理
        refund_result = self._process_refund(order_owner_id, order_info['amount_cents'], order_id,
                                           f"订单取消退款-{cancel_reason}")
        
        # 更新餐次当前订单数
        self.db.conn.execute("""
            UPDATE meals 
            SET current_orders = current_orders - 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ?
        """, [order_info['meal_id']])
        
        return {
            'order_id': order_id,
            'meal_id': order_info['meal_id'],
            'refund_amount': order_info['amount_cents'],
            'transaction_no': refund_result['transaction_no'],
            'cancel_reason': cancel_reason,
            'message': f'订单已取消，退款 {order_info["amount_cents"]/100:.2f} 元'
        }
    
    return self.db.execute_transaction([cancel_order_operation])[0]
```

## 辅助方法

### 余额操作辅助方法

```python
def _generate_transaction_no(self) -> str:
    """生成交易号"""
    from datetime import datetime
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    
    # 获取当日最大序号
    date_prefix = f"TXN{now.strftime('%Y%m%d')}"
    max_seq = self.db.conn.execute("""
        SELECT MAX(CAST(SUBSTRING(transaction_no, 12, 6) AS INTEGER))
        FROM ledger 
        WHERE transaction_no LIKE ?
    """, [f"{date_prefix}%"]).fetchone()[0]
    
    seq = (max_seq or 0) + 1
    return f"{date_prefix}{seq:06d}"

def _process_payment(self, user_id: int, amount_cents: int, order_id: int, 
                    description: str) -> Dict[str, Any]:
    """处理付款（扣款）"""
    
    # 获取当前余额
    current_balance = self.db.conn.execute("""
        SELECT balance_cents FROM users WHERE user_id = ?
    """, [user_id]).fetchone()[0]
    
    new_balance = current_balance - amount_cents
    transaction_no = self._generate_transaction_no()
    
    # 更新用户余额
    self.db.conn.execute("""
        UPDATE users 
        SET balance_cents = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, [new_balance, user_id])
    
    # 记录账本
    self.db.conn.execute("""
        INSERT INTO ledger (transaction_no, user_id, type, direction, amount_cents,
                          balance_before_cents, balance_after_cents, order_id, 
                          description, created_at)
        VALUES (?, ?, 'order', 'out', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [transaction_no, user_id, amount_cents, current_balance, new_balance, 
          order_id, description])
    
    return {
        'transaction_no': transaction_no,
        'balance_before': current_balance,
        'balance_after': new_balance
    }

def _process_refund(self, user_id: int, amount_cents: int, order_id: int, 
                   description: str) -> Dict[str, Any]:
    """处理退款"""
    
    # 获取当前余额
    current_balance = self.db.conn.execute("""
        SELECT balance_cents FROM users WHERE user_id = ?
    """, [user_id]).fetchone()[0]
    
    new_balance = current_balance + amount_cents
    transaction_no = self._generate_transaction_no()
    
    # 更新用户余额
    self.db.conn.execute("""
        UPDATE users 
        SET balance_cents = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, [new_balance, user_id])
    
    # 记录账本
    self.db.conn.execute("""
        INSERT INTO ledger (transaction_no, user_id, type, direction, amount_cents,
                          balance_before_cents, balance_after_cents, order_id, 
                          description, created_at)
        VALUES (?, ?, 'refund', 'in', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [transaction_no, user_id, amount_cents, current_balance, new_balance, 
          order_id, description])
    
    return {
        'transaction_no': transaction_no,
        'balance_before': current_balance,
        'balance_after': new_balance
    }
```

## 使用示例

```python
# 初始化
from db_manager import DatabaseManager

db_manager = DatabaseManager("gang_hao_fan.db", auto_connect=True)
core_ops = CoreOperations(db_manager)

try:
    # 1. 管理员创建附加项
    result = core_ops.admin_create_addon(
        admin_user_id=1,
        name="加鸡腿",
        price_cents=300,
        display_order=1
    )
    print(f"创建附加项: {result}")
    
    # 2. 管理员发布餐次
    meal_result = core_ops.admin_publish_meal(
        admin_user_id=1,
        date="2024-11-27",
        slot="lunch",
        description="红烧肉套餐",
        base_price_cents=1500,
        addon_config={result['addon_id']: 3},  # 加鸡腿最多3个
        max_orders=30
    )
    print(f"发布餐次: {meal_result}")
    
    # 3. 用户下单，选择2个加鸡腿
    order_result = core_ops.create_order(
        user_id=2,
        meal_id=meal_result['meal_id'],
        addon_selections={result['addon_id']: 2}  # 选择2个加鸡腿
    )
    print(f"用户下单: {order_result}")
    
finally:
    db_manager.close()
```

## 代码重构优化

### 公共函数优势

通过抽取重复逻辑为公共函数，获得以下优势：

1. **代码复用**：减少重复代码，提高维护性
2. **统一验证**：确保所有操作的验证逻辑一致
3. **易于测试**：公共函数可以独立测试
4. **错误一致性**：统一的错误信息和异常处理
5. **易于修改**：修改验证逻辑只需要改一处

### 重构前后对比

**重构前**（每个函数都有重复的验证代码）：
```python
# 管理员权限验证重复出现在多个函数中
admin_check = self.db.conn.execute(
    "SELECT is_admin FROM users WHERE user_id = ? AND status = 'active'",
    [admin_user_id]
).fetchone()

if not admin_check or not admin_check[0]:
    raise PermissionError("用户不是管理员或账户已停用")
```

**重构后**（统一调用公共函数）：
```python
# 一行代码完成管理员权限验证
self._verify_admin_permission(admin_user_id)
```

### 公共函数清单

- `_verify_admin_permission()` - 管理员权限验证
- `_verify_user_status()` - 用户状态验证
- `_verify_addon_exists_and_active()` - 附加项验证
- `_verify_meal_exists()` - 餐次验证
- `_verify_order_exists_and_active()` - 订单验证
- `_verify_addon_ids_active()` - 批量附加项验证
- `_check_meal_slot_available()` - 餐次时段检查
- `_check_addon_used_by_active_meals()` - 附加项使用检查

## 注意事项

1. **错误处理**：所有操作都包含完整的参数验证和业务规则检查
2. **事务管理**：复合操作使用事务确保数据一致性
3. **串行执行**：所有数据库操作串行执行，避免并发问题
4. **审计追踪**：关键操作记录时间戳和操作者信息
5. **余额安全**：所有涉及余额的操作都有完整的验证和记录
6. **数据不可变**：严格遵循附加项、餐次、订单的不可变原则
7. **代码复用**：通过公共函数减少重复代码，提高可维护性

### 12. 管理员取消餐次操作

```python
def admin_cancel_meal(self, admin_user_id: int, meal_id: int, cancel_reason: str = "管理员取消") -> Dict[str, Any]:
    """
    管理员取消餐次（可以取消已发布和已锁定的餐次）
    
    Args:
        admin_user_id: 管理员用户ID
        meal_id: 餐次ID  
        cancel_reason: 取消原因
    
    Returns:
        取消结果，包含退款统计
    """
    
    def cancel_meal_operation():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 验证餐次状态（不能取消已完成的餐次）
        meal_info = self._verify_meal_exists(meal_id)
        
        if meal_info['status'] not in ['published', 'locked']:
            raise ValueError(f"餐次状态为{meal_info['status']}，无法取消")
        
        # 获取该餐次的所有活跃订单
        active_orders = self.db.conn.execute("""
            SELECT order_id, user_id, amount_cents
            FROM orders 
            WHERE meal_id = ? AND status = 'active'
        """, [meal_id]).fetchall()
        
        total_refund_amount = 0
        refund_count = 0
        
        # 批量取消所有订单并退款
        for order in active_orders:
            order_id, user_id, amount_cents = order
            
            # 取消订单
            self.db.conn.execute("""
                UPDATE orders 
                SET status = 'canceled',
                    canceled_at = CURRENT_TIMESTAMP,
                    canceled_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, [f"餐次取消-{cancel_reason}", order_id])
            
            # 退款处理
            self._process_refund(user_id, amount_cents, order_id,
                               f"餐次取消退款-{cancel_reason}")
            
            total_refund_amount += amount_cents
            refund_count += 1
        
        # 取消餐次
        self.db.conn.execute("""
            UPDATE meals 
            SET status = 'canceled',
                canceled_at = CURRENT_TIMESTAMP,
                canceled_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE meal_id = ?
        """, [cancel_reason, meal_id])
        
        return {
            'meal_id': meal_id,
            'original_status': meal_info['status'],
            'canceled_orders_count': refund_count,
            'total_refund_amount': total_refund_amount,
            'cancel_reason': cancel_reason,
            'message': f'餐次取消成功，共退款 {refund_count} 个订单，总金额 {total_refund_amount/100:.2f} 元'
        }
    
    return self.db.execute_transaction([cancel_meal_operation])[0]
```

### 13. 管理员调整用户余额操作

```python
def admin_adjust_balance(self, admin_user_id: int, target_user_id: int, 
                        amount_cents: int, reason: str = "管理员调整") -> Dict[str, Any]:
    """
    管理员调整用户余额（增加或减少）
    
    Args:
        admin_user_id: 管理员用户ID
        target_user_id: 目标用户ID  
        amount_cents: 调整金额（分），正数为增加，负数为减少
        reason: 调整原因
    
    Returns:
        调整结果，包含调整前后余额
    """
    
    def adjust_balance_operation():
        # 验证管理员权限
        self._verify_admin_permission(admin_user_id)
        
        # 验证目标用户状态
        target_user_info = self._verify_user_status(target_user_id)
        current_balance = target_user_info['balance_cents']
        
        # 计算新余额
        new_balance = current_balance + amount_cents
        
        # 生成交易号
        transaction_no = self._generate_transaction_no()
        
        # 更新用户余额
        self.db.conn.execute("""
            UPDATE users 
            SET balance_cents = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, [new_balance, target_user_id])
        
        # 记录账本
        ledger_type = "recharge" if amount_cents > 0 else "adjustment"
        direction = "in" if amount_cents > 0 else "out"
        ledger_amount = abs(amount_cents)
        
        self.db.conn.execute("""
            INSERT INTO ledger (transaction_no, user_id, type, direction, amount_cents,
                              balance_before_cents, balance_after_cents, 
                              description, operator_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [transaction_no, target_user_id, ledger_type, direction, ledger_amount,
              current_balance, new_balance, f"管理员余额调整-{reason}", admin_user_id])
        
        # 获取目标用户信息用于返回
        target_user = self.db.conn.execute("""
            SELECT wechat_name, open_id FROM users WHERE user_id = ?
        """, [target_user_id]).fetchone()
        
        operation_type = "充值" if amount_cents > 0 else "扣除"
        
        return {
            'target_user_id': target_user_id,
            'target_user_name': target_user[0] if target_user else "未知用户",
            'target_user_open_id': target_user[1] if target_user else "",
            'adjustment_amount': amount_cents,
            'balance_before': current_balance,
            'balance_after': new_balance,
            'transaction_no': transaction_no,
            'operation_type': operation_type,
            'reason': reason,
            'message': f'用户余额{operation_type}成功，{operation_type}金额 {abs(amount_cents)/100:.2f} 元，余额 {current_balance/100:.2f} → {new_balance/100:.2f} 元'
        }
    
    return self.db.execute_transaction([adjust_balance_operation])[0]
```