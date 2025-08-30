# 参考文档: doc/db/query_operations.md
# 查询业务操作Python+DuckDB实现，统一使用JSON格式返回数据

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from .manager import DatabaseManager

class QueryOperations:
    """
    查询业务操作类
    参考文档: doc/db/query_operations.md
    """
    def __init__(self, db_manager: DatabaseManager):
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

    # 1. 查询日期范围内的餐次信息
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

    # 2. 查询餐次详细信息
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
            placeholders = ','.join(['?' for _ in addon_ids])
            addon_query = f"""
                SELECT addon_id, name, price_cents, status
                FROM addons
                WHERE addon_id IN ({placeholders})
            """
            
            addon_results = self.db.conn.execute(addon_query, addon_ids).fetchall()
            
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
            "addon_config": addon_config,
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

    # 3. 查询用户在特定餐次的订单信息
    def query_user_meal_order(self, user_id: int, meal_id: int) -> Dict[str, Any]:
        """
        查询某用户在指定餐次下的活跃订单信息
        
        Args:
            user_id: 用户ID
            meal_id: 餐次ID
        
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
                return {
                    "success": False,
                    "error": "餐次不存在",
                    "data": None
                }
            elif not user_exists:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "data": None
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "has_order": False
                    }
                }
        
        # 返回简化的订单信息
        return {
            "success": True,
            "data": {
                "has_order": True,
                "order_id": order_result[0],
                "order_status": order_result[5],
                "amount_cents": order_result[3]
            }
        }

    # 4. 查询用户历史账单变更信息
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

    def query_user_order_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        查询用户订单统计信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            订单统计数据
        """
        try:
            # 检查用户是否存在
            user_check = self.db.conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?", [user_id]
            ).fetchone()
            
            if not user_check:
                return {
                    "total_orders": 0,
                    "active_orders": 0,
                    "completed_orders": 0,
                    "canceled_orders": 0,
                    "total_spent_yuan": 0.0
                }
            
            # 查询订单统计
            stats_query = """
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_orders,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                    SUM(CASE WHEN status = 'canceled' THEN 1 ELSE 0 END) as canceled_orders,
                    SUM(CASE WHEN status IN ('active', 'completed') THEN amount_cents ELSE 0 END) as total_spent_cents
                FROM orders 
                WHERE user_id = ?
            """
            
            result = self.db.conn.execute(stats_query, [user_id]).fetchone()
            
            return {
                "total_orders": result[0] if result else 0,
                "active_orders": result[1] if result else 0,
                "completed_orders": result[2] if result else 0,
                "canceled_orders": result[3] if result else 0,
                "total_spent_yuan": (result[4] if result else 0) / 100.0
            }
            
        except Exception as e:
            self.db.logger.error(f"查询用户订单统计失败: {str(e)}")
            return {
                "total_orders": 0,
                "active_orders": 0,
                "completed_orders": 0,
                "canceled_orders": 0,
                "total_spent_yuan": 0.0
            }

    def query_user_transaction_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        查询用户交易统计信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            交易统计数据
        """
        try:
            # 检查用户是否存在
            user_check = self.db.conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?", [user_id]
            ).fetchone()
            
            if not user_check:
                return {
                    "total_transactions": 0,
                    "recharge_count": 0,
                    "total_recharged_yuan": 0.0
                }
            
            # 查询交易统计
            stats_query = """
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN type = 'recharge' THEN 1 ELSE 0 END) as recharge_count,
                    SUM(CASE WHEN type = 'recharge' THEN amount_cents ELSE 0 END) as total_recharged_cents
                FROM ledger 
                WHERE user_id = ?
            """
            
            result = self.db.conn.execute(stats_query, [user_id]).fetchone()
            
            return {
                "total_transactions": result[0] if result else 0,
                "recharge_count": result[1] if result else 0,
                "total_recharged_yuan": (result[2] if result else 0) / 100.0
            }
            
        except Exception as e:
            self.db.logger.error(f"查询用户交易统计失败: {str(e)}")
            return {
                "total_transactions": 0,
                "recharge_count": 0,
                "total_recharged_yuan": 0.0
            }

    def query_user_orders(self, user_id: int, status: str = None, 
                         offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        """
        查询用户订单列表
        
        Args:
            user_id: 用户ID
            status: 订单状态过滤
            offset: 偏移量
            limit: 每页条数
        
        Returns:
            用户订单列表
        """
        try:
            # 参数验证
            self._validate_pagination(offset, limit, 100)
            
            # 检查用户是否存在
            user_info = self.db.conn.execute(
                "SELECT wechat_name FROM users WHERE user_id = ?", [user_id]
            ).fetchone()
            
            if not user_info:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "data": None
                }
            
            # 构建查询条件
            where_conditions = ["o.user_id = ?"]
            params = [user_id]
            
            if status:
                where_conditions.append("o.status = ?")
                params.append(status)
            
            where_clause = " AND ".join(where_conditions)
            
            # 查询订单列表
            orders_query = f"""
                SELECT 
                    o.order_id,
                    o.meal_id,
                    o.amount_cents,
                    o.addon_selections,
                    o.status,
                    o.created_at,
                    o.updated_at,
                    o.canceled_at,
                    o.canceled_reason,
                    m.date,
                    m.slot,
                    m.description as meal_description,
                    m.base_price_cents,
                    m.status as meal_status
                FROM orders o
                LEFT JOIN meals m ON o.meal_id = m.meal_id
                WHERE {where_clause}
                ORDER BY o.created_at DESC
                LIMIT ? OFFSET ?
            """
            
            query_params = params + [limit, offset]
            orders_result = self.db.conn.execute(orders_query, query_params).fetchall()
            
            # 获取总数
            count_query = f"SELECT COUNT(*) FROM orders o WHERE {where_clause}"
            total_count = self.db.conn.execute(count_query, params).fetchone()[0]
            
            # 格式化订单列表
            orders_list = []
            for order in orders_result:
                # 解析附加项选择
                addon_selections = {}
                if order[3]:
                    try:
                        addon_selections = json.loads(order[3])
                    except:
                        pass
                
                # 状态文本
                status_text_map = {
                    "active": "有效",
                    "completed": "已完成", 
                    "canceled": "已取消"
                }
                
                orders_list.append({
                    "order_id": order[0],
                    "meal_id": order[1],
                    "amount_cents": order[2],
                    "amount_yuan": order[2] / 100.0,
                    "addon_selections": addon_selections,
                    "status": order[4],
                    "status_text": status_text_map.get(order[4], order[4]),
                    "created_at": order[5],
                    "updated_at": order[6],
                    "canceled_at": order[7],
                    "canceled_reason": order[8],
                    "meal_info": {
                        "meal_id": order[1],
                        "date": order[9],
                        "slot": order[10],
                        "slot_text": "午餐" if order[10] == "lunch" else "晚餐" if order[10] == "dinner" else order[10],
                        "description": order[11],
                        "base_price_cents": order[12],
                        "base_price_yuan": order[12] / 100.0 if order[12] else 0.0,
                        "meal_status": order[13]
                    } if order[1] else None
                })
            
            return {
                "success": True,
                "data": {
                    "user_info": {
                        "user_id": user_id,
                        "wechat_name": user_info[0]
                    },
                    "orders": orders_list,
                    "pagination": {
                        "total_count": total_count,
                        "current_page": offset // limit + 1,
                        "per_page": limit,
                        "total_pages": (total_count + limit - 1) // limit,
                        "has_next": offset + limit < total_count,
                        "has_prev": offset > 0
                    }
                },
                "message": f"订单列表查询成功，共 {len(orders_list)} 条记录"
            }
            
        except Exception as e:
            self.db.logger.error(f"查询用户订单列表失败: {str(e)}")
            return {
                "success": False,
                "error": f"查询失败: {str(e)}",
                "data": None
            }