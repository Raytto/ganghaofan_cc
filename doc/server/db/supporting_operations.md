# 周边支持业务操作伪代码

基于database_structure.md设计的周边支持业务操作Python+DuckDB伪代码，包括用户注册、登录、权限管理等辅助功能。

## 设计原则

1. **安全性**：用户信息验证和权限控制
2. **完整性**：确保用户数据的一致性和完整性
3. **审计性**：记录关键操作的时间戳和状态变更
4. **扩展性**：支持后续功能扩展
5. **统一格式**：返回统一的JSON格式
6. **状态管理**：使用status字段统一管理用户状态（unregistered/active/suspended）

## 基础支持类

```python
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from db_manager import DatabaseManager

class SupportingOperations:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def _generate_user_id(self) -> int:
        """生成新用户ID"""
        result = self.db.conn.execute("SELECT MAX(user_id) FROM users").fetchone()
        max_id = result[0] if result[0] else 0
        return max_id + 1
    
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
```

## 用户状态管理

### 用户状态定义

基于 `status` 字段的三种用户状态：

1. **未知用户**：OpenID 不存在于数据库中的用户
2. **未注册用户**：OpenID 存在且 `status = 'unregistered'` 的用户
3. **已注册用户**：OpenID 存在且 `status = 'active'` 的用户
4. **已停用用户**：OpenID 存在且 `status = 'suspended'` 的用户

### 核心操作方法

```python
def wechat_silent_login(self, open_id: str) -> Dict[str, Any]:
    """
    微信静默登录 - 获取或创建用户
    
    逻辑：
    - 如果用户不存在，创建未注册用户（status='unregistered'）
    - 如果用户存在，返回用户信息和注册状态（基于status字段判断）
    
    返回格式：
    {
        "success": true,
        "data": {
            "user_id": 123,
            "open_id": "wx_123",
            "wechat_name": null,  // 未注册时为null
            "avatar_url": null,   // 未注册时为null
            "balance_cents": 0,
            "is_admin": false,
            "status": "unregistered",  // 用户状态
            "is_registered": false  // 基于status判断：status=='active'为true
        },
        "message": "登录成功"
    }
    """
    
def complete_user_registration(self, open_id: str, wechat_name: str, avatar_url: str = None) -> Dict[str, Any]:
    """
    完成用户注册 - 更新用户信息
    
    将未注册用户（status='unregistered'）转换为已注册用户（status='active'）
    
    参数：
    - open_id: 用户OpenID
    - wechat_name: 用户昵称（必填）
    - avatar_url: 用户头像URL（可选）
    
    操作：
    - 更新wechat_name和avatar_url字段
    - 将status从'unregistered'改为'active'
    
    返回：用户完整信息
    """

def get_user_registration_status(self, open_id: str) -> Dict[str, Any]:
    """
    获取用户注册状态
    
    返回：
    - 未知用户：{"exists": false}
    - 未注册用户：{"exists": true, "is_registered": false}
    - 已注册用户：{"exists": true, "is_registered": true, "user_info": {...}}
    """
```

## 使用示例

```python
# 初始化
from db_manager import DatabaseManager

db_manager = DatabaseManager("gang_hao_fan.db", auto_connect=True)
support_ops = SupportingOperations(db_manager)

try:
    # 1. 微信静默登录（未知用户）
    login_result = support_ops.wechat_silent_login("wx_new_user_123")
    # 返回：{"success": true, "data": {"is_registered": false, ...}}
    
    # 2. 完成用户注册
    if not login_result["data"]["is_registered"]:
        register_result = support_ops.complete_user_registration(
            open_id="wx_new_user_123",
            wechat_name="用户昵称",
            avatar_url="https://wx.avatar.com/123.jpg"
        )
        print(f"注册完成: {register_result}")
    
    # 3. 已注册用户登录
    login_result = support_ops.wechat_silent_login("wx_registered_user_456")
    # 返回：{"success": true, "data": {"is_registered": true, "wechat_name": "已有昵称", ...}}
    
finally:
    db_manager.close()
```

## 统一返回格式

### 成功响应
```json
{
    "success": true,
    "data": { /* 具体业务数据 */ },
    "message": "操作成功描述"
}
```

### 失败响应
```json
{
    "success": false,
    "error": "错误描述信息",
    "data": null
}
```

## 注意事项

1. **安全性**：所有用户操作都包含权限验证和状态检查
2. **数据一致性**：使用事务确保用户数据的完整性
3. **微信集成**：支持微信OAuth登录和用户信息自动更新
4. **权限控制**：区分普通用户和管理员的操作权限
5. **审计追踪**：记录用户状态变更和关键操作时间
6. **防护机制**：防止管理员误操作（如停用自己）
7. **统计信息**：用户信息包含订单和交易统计数据