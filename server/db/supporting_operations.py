# -*- coding: utf-8 -*-
# 参考文档: doc/db/supporting_operations.md
# 周边支持业务操作Python+DuckDB实现，包括用户注册、登录、权限管理等辅助功能

import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from .manager import DatabaseManager

class SupportingOperations:
    """
    周边支持业务操作类
    参考文档: doc/db/supporting_operations.md
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def _validate_wechat_info(self, open_id: str, wechat_name: str = None):
        """验证微信信息格式"""
        if not open_id or len(open_id.strip()) == 0:
            raise ValueError("微信OpenID不能为空")
        
        if len(open_id) > 128:
            raise ValueError("微信OpenID长度不能超过128字符")
        
        if wechat_name and len(wechat_name) > 100:
            raise ValueError("微信昵称长度不能超过100字符")
    
    def _check_user_exists(self, open_id: str) -> Optional[Dict[str, Any]]:
        """检查用户是否已存在"""
        user_query = """
            SELECT user_id, wechat_name, avatar_url, balance_cents, 
                   is_admin, status, created_at, last_login_at
            FROM users 
            WHERE open_id = ?
        """
        
        result = self.db.conn.execute(user_query, [open_id]).fetchone()
        
        if result:
            return {
                'user_id': result[0],
                'wechat_name': result[1],
                'avatar_url': result[2],
                'balance_cents': result[3],
                'is_admin': result[4],
                'status': result[5],
                'created_at': result[6],
                'last_login_at': result[7]
            }
        return None

    def _check_admin_whitelist(self, open_id: str) -> bool:
        """
        检查OpenID是否在管理员白名单中
        
        Args:
            open_id: 微信OpenID
            
        Returns:
            是否为管理员
        """
        try:
            # 导入配置
            from utils.config import Config
            config = Config()
            
            # 获取管理员白名单
            whitelist = config.get('admin.whitelist_open_ids', [])
            
            # 如果白名单包含 "__any__"，则所有用户都是管理员（仅开发环境使用）
            if "__any__" in whitelist:
                self.db.logger.debug(f"开发模式: __any__ 存在于白名单，{open_id} 设为管理员")
                return True
            
            # 检查是否在白名单中
            is_admin = open_id in whitelist
            if is_admin:
                self.db.logger.info(f"用户 {open_id} 在管理员白名单中")
            
            return is_admin
            
        except Exception as e:
            self.db.logger.error(f"检查管理员白名单失败: {str(e)}")
            return False

    def register_user(self, open_id: str, wechat_name: str = None, avatar_url: str = None) -> Dict[str, Any]:
        """
        注册新用户
        
        Args:
            open_id: 微信OpenID
            wechat_name: 微信昵称
            avatar_url: 头像URL
        
        Returns:
            注册结果
        """
        def register_user_operation():
            # 验证微信信息格式
            self._validate_wechat_info(open_id, wechat_name)
            
            # 检查用户是否已存在
            existing_user = self._check_user_exists(open_id)
            if existing_user:
                raise ValueError(f"用户OpenID {open_id} 已存在")
            
            # 获取下一个用户ID
            max_id = self.db.conn.execute("SELECT COALESCE(MAX(user_id), 0) + 1 FROM users").fetchone()[0]
            
            # 创建新用户
            insert_result = self.db.conn.execute("""
                INSERT INTO users (user_id, open_id, wechat_name, avatar_url, balance_cents, 
                                 is_admin, status, created_at, updated_at, last_login_at)
                VALUES (?, ?, ?, ?, 0, FALSE, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, [max_id, open_id, wechat_name, avatar_url])
            
            # 使用生成的用户ID
            user_id = max_id
            
            # 获取用户信息用于返回
            user_info = self._check_user_exists(open_id)
            
            return {
                'success': True,
                'user_id': user_id,
                'data': {
                    'user_id': user_id,
                    'open_id': open_id,
                    'wechat_name': wechat_name,
                    'avatar_url': avatar_url,
                    'balance_cents': 0,
                    'balance_yuan': 0.0,
                    'is_admin': False,
                    'is_new_user': True,
                    'status': 'active',
                    'created_at': user_info['created_at']
                },
                'message': '用户注册成功'
            }
        
        return self.db.execute_transaction([register_user_operation])[0]

    def user_login(self, open_id: str, wechat_name: str = None, avatar_url: str = None, 
                   update_profile: bool = True, auto_register: bool = True) -> Dict[str, Any]:
        """
        用户登录（如果不存在则自动注册）
        
        Args:
            open_id: 微信OpenID
            wechat_name: 微信昵称
            avatar_url: 头像URL
            update_profile: 是否更新用户资料
        
        Returns:
            登录结果
        """
        def login_operation():
            # 验证微信信息格式
            self._validate_wechat_info(open_id, wechat_name)
            
            # 检查用户是否存在
            existing_user = self._check_user_exists(open_id)
            is_new_user = False
            
            if not existing_user:
                # 用户不存在
                if not auto_register:
                    # 不自动注册，返回失败
                    return {
                        'success': False,
                        'error': '用户不存在',
                        'message': '用户不存在'
                    }
                
                # 自动注册
                # 获取下一个用户ID
                max_id = self.db.conn.execute("SELECT COALESCE(MAX(user_id), 0) + 1 FROM users").fetchone()[0]
                
                self.db.conn.execute("""
                    INSERT INTO users (user_id, open_id, wechat_name, avatar_url, balance_cents, 
                                     is_admin, status, created_at, updated_at, last_login_at)
                    VALUES (?, ?, ?, ?, 0, FALSE, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, [max_id, open_id, wechat_name, avatar_url])
                is_new_user = True
                
                # 获取新创建的用户信息
                existing_user = self._check_user_exists(open_id)
            else:
                # 用户存在，检查账户状态
                if existing_user['status'] != 'active':
                    raise ValueError("用户账户已停用")
                
                # 更新最后登录时间和用户资料
                update_fields = ["last_login_at = CURRENT_TIMESTAMP", "updated_at = CURRENT_TIMESTAMP"]
                update_params = []
                
                if update_profile:
                    if wechat_name:
                        update_fields.append("wechat_name = ?")
                        update_params.append(wechat_name)
                    if avatar_url:
                        update_fields.append("avatar_url = ?")
                        update_params.append(avatar_url)
                
                update_params.append(open_id)
                
                self.db.conn.execute(f"""
                    UPDATE users 
                    SET {', '.join(update_fields)}
                    WHERE open_id = ?
                """, update_params)
                
                # 重新获取更新后的用户信息
                existing_user = self._check_user_exists(open_id)
            
            # 获取用户统计信息
            order_stats = self.db.conn.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_orders,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders,
                    COUNT(CASE WHEN status = 'canceled' THEN 1 END) as canceled_orders,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN amount_cents ELSE 0 END), 0) as total_spent_cents
                FROM orders 
                WHERE user_id = ?
            """, [existing_user['user_id']]).fetchone()
            
            transaction_stats = self.db.conn.execute("""
                SELECT 
                    COUNT(*) as total_transactions,
                    COUNT(CASE WHEN type = 'recharge' THEN 1 END) as recharge_count,
                    COALESCE(SUM(CASE WHEN type = 'recharge' THEN amount_cents ELSE 0 END), 0) as total_recharged_cents
                FROM ledger 
                WHERE user_id = ?
            """, [existing_user['user_id']]).fetchone()
            
            return {
                'success': True,
                'data': {
                    'user_id': existing_user['user_id'],
                    'open_id': open_id,
                    'wechat_name': existing_user['wechat_name'],
                    'avatar_url': existing_user['avatar_url'],
                    'balance_cents': existing_user['balance_cents'],
                    'balance_yuan': existing_user['balance_cents'] / 100,
                    'is_admin': existing_user['is_admin'],
                    'is_new_user': is_new_user,
                    'status': existing_user['status'],
                    'created_at': existing_user['created_at'],
                    'last_login_at': existing_user['last_login_at'],
                    'order_statistics': {
                        'total_orders': order_stats[0] if order_stats else 0,
                        'active_orders': order_stats[1] if order_stats else 0,
                        'completed_orders': order_stats[2] if order_stats else 0,
                        'canceled_orders': order_stats[3] if order_stats else 0,
                        'total_spent_yuan': (order_stats[4] if order_stats else 0) / 100
                    },
                    'transaction_statistics': {
                        'total_transactions': transaction_stats[0] if transaction_stats else 0,
                        'recharge_count': transaction_stats[1] if transaction_stats else 0,
                        'total_recharged_yuan': (transaction_stats[2] if transaction_stats else 0) / 100
                    }
                },
                'message': '用户注册成功' if is_new_user else '登录成功'
            }
        
        return self.db.execute_transaction([login_operation])[0]

    def admin_set_user_admin(self, admin_user_id: int, target_user_id: int, is_admin: bool) -> Dict[str, Any]:
        """
        管理员设置用户管理员权限
        
        Args:
            admin_user_id: 操作的管理员用户ID
            target_user_id: 目标用户ID
            is_admin: 是否设为管理员
        
        Returns:
            操作结果
        """
        def set_admin_operation():
            # 验证操作员管理员权限
            admin_check = self.db.conn.execute(
                "SELECT is_admin FROM users WHERE user_id = ? AND status = 'active'",
                [admin_user_id]
            ).fetchone()
            
            if not admin_check or not admin_check[0]:
                raise PermissionError("操作用户不是管理员或账户已停用")
            
            # 获取目标用户信息
            target_user = self.db.conn.execute("""
                SELECT wechat_name, is_admin, status FROM users WHERE user_id = ?
            """, [target_user_id]).fetchone()
            
            if not target_user:
                raise ValueError(f"目标用户ID {target_user_id} 不存在")
            
            if target_user[2] != 'active':
                raise ValueError("目标用户账户已停用")
            
            current_is_admin = target_user[1]
            if current_is_admin == is_admin:
                return {
                    'target_user_id': target_user_id,
                    'target_user_name': target_user[0],
                    'is_admin': is_admin,
                    'changed': False,
                    'message': f'用户权限无变化，当前为{"管理员" if is_admin else "普通用户"}'
                }
            
            # 更新用户管理员权限
            self.db.conn.execute("""
                UPDATE users 
                SET is_admin = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, [is_admin, target_user_id])
            
            return {
                'target_user_id': target_user_id,
                'target_user_name': target_user[0],
                'is_admin': is_admin,
                'changed': True,
                'message': f'用户权限已更新为{"管理员" if is_admin else "普通用户"}'
            }
        
        return self.db.execute_transaction([set_admin_operation])[0]

    def admin_set_user_status(self, admin_user_id: int, target_user_id: int, 
                             status: str, reason: str = None) -> Dict[str, Any]:
        """
        管理员设置用户账户状态
        
        Args:
            admin_user_id: 操作的管理员用户ID
            target_user_id: 目标用户ID
            status: 新状态 (active/suspended)
            reason: 操作原因
        
        Returns:
            操作结果
        """
        def set_status_operation():
            # 验证操作员管理员权限
            admin_check = self.db.conn.execute(
                "SELECT is_admin FROM users WHERE user_id = ? AND status = 'active'",
                [admin_user_id]
            ).fetchone()
            
            if not admin_check or not admin_check[0]:
                raise PermissionError("操作用户不是管理员或账户已停用")
            
            # 验证状态值
            if status not in ['unregistered', 'active', 'suspended']:
                raise ValueError("状态值必须为 unregistered, active 或 suspended")
            
            # 获取目标用户信息
            target_user = self.db.conn.execute("""
                SELECT wechat_name, status, is_admin FROM users WHERE user_id = ?
            """, [target_user_id]).fetchone()
            
            if not target_user:
                raise ValueError(f"目标用户ID {target_user_id} 不存在")
            
            # 防止管理员停用自己
            if admin_user_id == target_user_id and status == 'suspended':
                raise ValueError("管理员不能停用自己的账户")
            
            current_status = target_user[1]
            if current_status == status:
                return {
                    'target_user_id': target_user_id,
                    'target_user_name': target_user[0],
                    'status': status,
                    'changed': False,
                    'reason': reason,
                    'message': f'用户账户状态无变化，当前为{"正常" if status == "active" else "停用"}'
                }
            
            # 更新用户状态
            self.db.conn.execute("""
                UPDATE users 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, [status, target_user_id])
            
            status_text = "已激活" if status == "active" else "已停用"
            message = f'用户账户{status_text}'
            if reason:
                message += f"，原因：{reason}"
            
            return {
                'target_user_id': target_user_id,
                'target_user_name': target_user[0],
                'status': status,
                'changed': True,
                'reason': reason,
                'message': message
            }
        
        return self.db.execute_transaction([set_status_operation])[0]

    def query_users_list(self, status: str = None, is_admin: bool = None, 
                         offset: int = 0, limit: int = 100) -> Dict[str, Any]:
        """
        查询用户列表（管理员功能）
        
        Args:
            status: 用户状态过滤 (active/suspended)
            is_admin: 管理员权限过滤
            offset: 偏移量
            limit: 每页条数，最大100
        
        Returns:
            用户列表
        """
        # 参数验证
        if limit <= 0 or limit > 100:
            raise ValueError("每页条数必须在1-100之间")
        if offset < 0:
            raise ValueError("偏移量不能为负数")
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("status = ?")
            params.append(status)
        
        if is_admin is not None:
            where_conditions.append("is_admin = ?")
            params.append(is_admin)
        
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        
        # 查询用户列表
        users_query = f"""
            SELECT 
                user_id, open_id, wechat_name, avatar_url, balance_cents,
                is_admin, status, created_at, updated_at, last_login_at
            FROM users
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        
        query_params = params + [limit, offset]
        users_result = self.db.conn.execute(users_query, query_params).fetchall()
        
        # 获取总数
        count_query = f"SELECT COUNT(*) FROM users {where_clause}"
        total_count = self.db.conn.execute(count_query, params).fetchone()[0]
        
        # 格式化用户列表
        users_list = []
        for user in users_result:
            users_list.append({
                'user_id': user[0],
                'open_id': user[1],
                'wechat_name': user[2],
                'avatar_url': user[3],
                'balance_cents': user[4],
                'balance_yuan': user[4] / 100,
                'is_admin': user[5],
                'is_admin_text': "是" if user[5] else "否",
                'status': user[6],
                'status_text': "正常" if user[6] == 'active' else "停用",
                'created_at': user[7],
                'updated_at': user[8],
                'last_login_at': user[9]
            })
        
        return {
            "success": True,
            "data": {
                "users": users_list,
                "pagination": {
                    "total_count": total_count,
                    "current_page": offset // limit + 1,
                    "per_page": limit,
                    "total_pages": (total_count + limit - 1) // limit,
                    "has_next": offset + limit < total_count,
                    "has_prev": offset > 0
                }
            },
            "message": f"用户列表查询成功，共 {len(users_list)} 条记录"
        }

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据用户ID获取用户信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户信息字典或None
        """
        try:
            user_query = """
                SELECT user_id, open_id, wechat_name, avatar_url, balance_cents,
                       is_admin, status, created_at, updated_at, last_login_at
                FROM users 
                WHERE user_id = ?
            """
            
            result = self.db.conn.execute(user_query, [user_id]).fetchone()
            
            if result:
                return {
                    'user_id': result[0],
                    'open_id': result[1],
                    'wechat_name': result[2],
                    'avatar_url': result[3],
                    'balance_cents': result[4],
                    'is_admin': result[5],
                    'status': result[6],
                    'created_at': result[7],
                    'updated_at': result[8],
                    'last_login_at': result[9]
                }
            return None
            
        except Exception as e:
            self.db.logger.error(f"获取用户ID {user_id} 信息失败: {str(e)}")
            return None

    # ===== 新增：三状态用户管理方法 =====
    
    def wechat_silent_login(self, open_id: str) -> Dict[str, Any]:
        """
        微信静默登录 - 获取或创建用户
        
        逻辑：
        - 如果用户不存在，创建未注册用户
        - 如果用户存在，返回用户信息和注册状态
        
        Args:
            open_id: 微信OpenID
            
        Returns:
            包含用户信息和注册状态的字典
        """
        try:
            # 验证OpenID格式
            self._validate_wechat_info(open_id)
            
            # 检查用户是否存在
            existing_user = self._check_user_exists(open_id)
            
            if existing_user:
                # 用户存在，判断注册状态（基于status字段）
                is_registered = existing_user.get('status') == 'active'
                
                # 更新最后登录时间
                self.db.conn.execute("""
                    UPDATE users 
                    SET last_login_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE open_id = ?
                """, [open_id])
                
                return {
                    'success': True,
                    'data': {
                        'user_id': existing_user['user_id'],
                        'open_id': open_id,
                        'wechat_name': existing_user.get('wechat_name'),
                        'avatar_url': existing_user.get('avatar_url'),
                        'balance_cents': existing_user.get('balance_cents', 0),
                        'balance_yuan': existing_user.get('balance_cents', 0) / 100.0,
                        'is_admin': existing_user.get('is_admin', False),
                        'status': existing_user.get('status', 'active'),
                        'is_registered': is_registered,
                        'created_at': existing_user.get('created_at'),
                        'last_login_at': existing_user.get('last_login_at')
                    },
                    'message': "登录成功" if is_registered else "登录成功，请完善个人信息"
                }
            else:
                # 用户不存在，创建未注册用户
                return self._create_unregistered_user(open_id)
                
        except Exception as e:
            self.db.logger.error(f"微信静默登录失败 - OpenID: {open_id}, 错误: {str(e)}")
            return {
                'success': False,
                'error': f"登录失败: {str(e)}",
                'data': None
            }

    def _create_unregistered_user(self, open_id: str) -> Dict[str, Any]:
        """
        创建未注册用户
        
        Args:
            open_id: 微信OpenID
            
        Returns:
            创建的用户信息
        """
        def create_user_operation():
            # 获取下一个用户ID
            max_id = self.db.conn.execute("SELECT COALESCE(MAX(user_id), 0) + 1 FROM users").fetchone()[0]
            
            # 检查是否在管理员白名单中
            is_admin = self._check_admin_whitelist(open_id)
            
            # 创建未注册用户（status为'unregistered'）
            self.db.conn.execute("""
                INSERT INTO users (user_id, open_id, wechat_name, avatar_url, balance_cents, 
                                 is_admin, status, created_at, updated_at, last_login_at)
                VALUES (?, ?, NULL, NULL, 0, ?, 'unregistered', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, [max_id, open_id, is_admin])
            
            return {
                'success': True,
                'data': {
                    'user_id': max_id,
                    'open_id': open_id,
                    'wechat_name': None,
                    'avatar_url': None,
                    'balance_cents': 0,
                    'balance_yuan': 0.0,
                    'is_admin': is_admin,
                    'status': 'unregistered',
                    'is_registered': False,
                    'created_at': datetime.now(),
                    'last_login_at': datetime.now()
                },
                'message': "登录成功，请完善个人信息"
            }
        
        return self.db.execute_transaction([create_user_operation])[0]

    def complete_user_registration(self, open_id: str, wechat_name: str, avatar_url: str = None) -> Dict[str, Any]:
        """
        完成用户注册 - 更新用户信息
        
        将未注册用户转换为已注册用户
        
        Args:
            open_id: 用户OpenID
            wechat_name: 用户昵称（必填）
            avatar_url: 用户头像URL（可选）
            
        Returns:
            更新后的用户信息
        """
        try:
            # 验证输入参数
            self._validate_wechat_info(open_id, wechat_name)
            
            if not wechat_name or not wechat_name.strip():
                raise ValueError("用户昵称不能为空")
            
            # 检查用户是否存在
            existing_user = self._check_user_exists(open_id)
            if not existing_user:
                raise ValueError(f"用户OpenID {open_id} 不存在")
            
            # 检查用户状态
            if existing_user.get('status') == 'suspended':
                raise ValueError("用户账户已停用")
            
            # 如果用户已经是active状态但缺少基本信息，允许更新
            is_info_complete = (existing_user.get('wechat_name') and 
                              existing_user.get('wechat_name').strip())
            
            if existing_user.get('status') == 'active' and is_info_complete:
                # 用户信息完整，只允许更新头像
                if avatar_url:
                    self.db.conn.execute("""
                        UPDATE users 
                        SET avatar_url = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE open_id = ?
                    """, [avatar_url, open_id])
                
                updated_user = self._check_user_exists(open_id)
                return {
                    'success': True,
                    'data': {
                        'user_id': updated_user['user_id'],
                        'open_id': open_id,
                        'wechat_name': updated_user['wechat_name'],
                        'avatar_url': updated_user['avatar_url'],
                        'balance_cents': updated_user['balance_cents'],
                        'balance_yuan': updated_user['balance_cents'] / 100.0,
                        'is_admin': updated_user['is_admin'],
                        'status': updated_user['status']
                    },
                    'message': '头像更新成功'
                }
                
            def update_user_operation():
                # 更新用户信息，并将状态改为active
                self.db.conn.execute("""
                    UPDATE users 
                    SET wechat_name = ?, avatar_url = ?, status = 'active', updated_at = CURRENT_TIMESTAMP
                    WHERE open_id = ?
                """, [wechat_name.strip(), avatar_url, open_id])
                
                # 获取更新后的用户信息
                updated_user = self._check_user_exists(open_id)
                
                return {
                    'success': True,
                    'data': {
                        'user_id': updated_user['user_id'],
                        'open_id': open_id,
                        'wechat_name': updated_user['wechat_name'],
                        'avatar_url': updated_user['avatar_url'],
                        'balance_cents': updated_user['balance_cents'],
                        'balance_yuan': updated_user['balance_cents'] / 100.0,
                        'is_admin': updated_user['is_admin'],
                        'status': updated_user['status'],
                        'is_registered': True,
                        'created_at': updated_user['created_at'],
                        'last_login_at': updated_user['last_login_at']
                    },
                    'message': "注册完成"
                }
            
            return self.db.execute_transaction([update_user_operation])[0]
            
        except Exception as e:
            self.db.logger.error(f"完成用户注册失败 - OpenID: {open_id}, 错误: {str(e)}")
            return {
                'success': False,
                'error': f"注册失败: {str(e)}",
                'data': None
            }

    def get_user_registration_status(self, open_id: str) -> Dict[str, Any]:
        """
        获取用户注册状态
        
        Args:
            open_id: 用户OpenID
            
        Returns:
            用户注册状态信息
        """
        try:
            # 验证OpenID格式
            self._validate_wechat_info(open_id)
            
            # 检查用户是否存在
            existing_user = self._check_user_exists(open_id)
            
            if not existing_user:
                return {
                    'success': True,
                    'data': {
                        'exists': False,
                        'is_registered': False
                    },
                    'message': "用户不存在"
                }
            
            # 判断注册状态（基于status字段）
            is_registered = existing_user.get('status') == 'active'
            
            result = {
                'success': True,
                'data': {
                    'exists': True,
                    'is_registered': is_registered
                },
                'message': "用户已注册" if is_registered else "用户未注册"
            }
            
            if is_registered:
                result['data']['user_info'] = {
                    'user_id': existing_user['user_id'],
                    'open_id': open_id,
                    'wechat_name': existing_user['wechat_name'],
                    'avatar_url': existing_user['avatar_url'],
                    'balance_cents': existing_user['balance_cents'],
                    'balance_yuan': existing_user['balance_cents'] / 100.0,
                    'is_admin': existing_user['is_admin']
                }
            
            return result
            
        except Exception as e:
            self.db.logger.error(f"获取用户注册状态失败 - OpenID: {open_id}, 错误: {str(e)}")
            return {
                'success': False,
                'error': f"获取状态失败: {str(e)}",
                'data': None
            }