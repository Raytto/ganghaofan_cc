# 周边支持业务操作伪代码

基于database_structure.md设计的周边支持业务操作Python+DuckDB伪代码，包括用户注册、登录、权限管理等辅助功能。

## 设计原则

1. **安全性**：用户信息验证和权限控制
2. **完整性**：确保用户数据的一致性和完整性
3. **审计性**：记录关键操作的时间戳和状态变更
4. **扩展性**：支持后续功能扩展
5. **统一格式**：返回统一的JSON格式

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

## 使用示例

```python
# 初始化
from db_manager import DatabaseManager

db_manager = DatabaseManager("gang_hao_fan.db", auto_connect=True)
support_ops = SupportingOperations(db_manager)

try:
    # 1. 新用户注册
    register_result = support_ops.register_user(
        open_id="wx_new_user_123",
        wechat_name="新用户",
        avatar_url="https://wx.avatar.com/123.jpg"
    )
    print(f"用户注册: {register_result}")
    
    # 2. 用户登录
    login_result = support_ops.user_login(
        open_id="wx_existing_user_456",
        wechat_name="更新的昵称",
        avatar_url="https://wx.avatar.com/456.jpg",
        update_profile=True
    )
    print(f"用户登录: {login_result}")
    
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