# 罡好饭 API 接口文档

基于 doc/db 下的数据库操作逻辑设计的 RESTful API 接口，为微信小程序提供完整的餐饮预订服务。

## 基础信息

- **Base URL**: `https://pangruitao.com` (生产环境)
- **Base URL**: `http://localhost:8000` (开发环境1 - 本地)
- **Base URL**: `http://us.pangruitao.com:8000` (开发环境2 - 远程)
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

## 统一响应格式

### 成功响应
```json
{
    "success": true,
    "data": {},
    "message": "操作成功描述",
    "timestamp": "2024-12-01T10:30:00Z"
}
```

### 失败响应
```json
{
    "success": false,
    "error": "错误描述信息",
    "data": null,
    "timestamp": "2024-12-01T10:30:00Z"
}
```

### 分页响应
```json
{
    "success": true,
    "data": {
        "items": [],
        "pagination": {
            "total_count": 100,
            "current_page": 1,
            "per_page": 20,
            "total_pages": 5,
            "has_next": true,
            "has_prev": false
        }
    },
    "message": "查询成功"
}
```

## 认证机制

### JWT Token 认证
需要认证的接口在 Header 中携带 JWT Token：

```
Authorization: Bearer <jwt_token>
```

### 权限级别
- **用户**: JWT 认证，个人功能
- **管理员**: JWT 认证 + 管理员权限

## API 接口

### 1. 认证模块 `/api/auth`

#### 1.1 微信静默登录
```
POST /api/auth/wechat/login
```

**说明**: 微信小程序静默登录，获取或创建用户

**请求参数**:
```json
{
    "code": "微信授权码"
}
```

**响应数据**:

**已注册用户**:
```json
{
    "success": true,
    "data": {
        "access_token": "jwt_token_string",
        "token_type": "Bearer", 
        "expires_in": 86400,
        "user_info": {
            "user_id": 1,
            "open_id": "wx_openid_123",
            "wechat_name": "张三",
            "avatar_url": "https://wx.avatar.com/123.jpg",
            "balance_cents": 5000,
            "balance_yuan": 50.0,
            "is_admin": false,
            "status": "active",
            "is_registered": true
        }
    },
    "message": "登录成功"
}
```

**未注册用户**:
```json
{
    "success": true,
    "data": {
        "access_token": "jwt_token_string",
        "token_type": "Bearer", 
        "expires_in": 86400,
        "user_info": {
            "user_id": 1,
            "open_id": "wx_openid_123",
            "wechat_name": null,
            "avatar_url": null,
            "balance_cents": 0,
            "balance_yuan": 0.0,
            "is_admin": false,
            "status": "unregistered",
            "is_registered": false
        }
    },
    "message": "登录成功，请完善个人信息"
}
```

#### 1.2 完成用户注册
```
POST /api/auth/register
```

**权限**: 用户（未注册用户，status='unregistered'）

**说明**: 完善用户个人信息，将status从'unregistered'改为'active'

**请求参数**:
```json
{
    "wechat_name": "用户昵称",
    "avatar_url": "头像URL（可选）"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_id": 1,
        "open_id": "wx_openid_123",
        "wechat_name": "用户昵称",
        "avatar_url": "https://wx.avatar.com/123.jpg",
        "balance_cents": 0,
        "balance_yuan": 0.0,
        "is_admin": false,
        "is_registered": true
    },
    "message": "注册完成"
}
```

#### 1.3 刷新 Token
```
POST /api/auth/refresh
```

**权限**: 用户

**响应数据**:
```json
{
    "success": true,
    "data": {
        "access_token": "new_jwt_token_string",
        "expires_in": 86400
    },
    "message": "Token刷新成功"
}
```

### 2. 用户模块 `/api/users`

#### 2.1 获取用户信息
```
GET /api/users/profile
```

**权限**: 用户

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_id": 1,
        "open_id": "wx_openid_123",
        "wechat_name": "张三",
        "avatar_url": "https://wx.avatar.com/123.jpg",
        "balance_cents": 5000,
        "balance_yuan": 50.0,
        "is_admin": false,
        "created_at": "2024-01-01T00:00:00Z",
        "last_login_at": "2024-12-01T10:30:00Z",
        "order_statistics": {
            "total_orders": 25,
            "active_orders": 2,
            "completed_orders": 20,
            "canceled_orders": 3,
            "total_spent_yuan": 500.0
        },
        "transaction_statistics": {
            "total_transactions": 30,
            "recharge_count": 5,
            "total_recharged_yuan": 600.0
        }
    },
    "message": "用户信息查询成功"
}
```

#### 2.2 获取账单历史
```
GET /api/users/ledger
```

**权限**: 用户

**查询参数**:
- `offset`: 偏移量，默认0
- `limit`: 每页条数，最大200，默认50

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_info": {
            "user_id": 1,
            "wechat_name": "张三",
            "current_balance_yuan": 50.0
        },
        "ledger_records": [
            {
                "ledger_id": 1,
                "transaction_no": "TXN20241201000001",
                "type": "recharge",
                "type_text": "充值",
                "direction": "in",
                "direction_text": "收入",
                "amount_yuan": 100.0,
                "balance_before_yuan": 0.0,
                "balance_after_yuan": 100.0,
                "balance_change": "+100.00",
                "description": "微信充值",
                "created_at": "2024-12-01T10:30:00Z",
                "related_order": null
            }
        ],
        "pagination": {}
    },
    "message": "账单历史查询成功"
}
```

### 3. 餐次模块 `/api/meals`

#### 3.1 获取餐次列表
```
GET /api/meals
```

**权限**: 用户

**查询参数**:
- `start_date`: 开始日期 (YYYY-MM-DD)，默认今天
- `end_date`: 结束日期 (YYYY-MM-DD)，默认今天+7天
- `offset`: 偏移量，默认0
- `limit`: 每页条数，最大60，默认20

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meals": [
            {
                "meal_id": 1,
                "date": "2024-12-01",
                "slot": "lunch",
                "slot_text": "午餐",
                "description": "红烧肉套餐",
                "base_price_cents": 1500,
                "base_price_yuan": 15.0,
                "addon_config": {"1": 3, "2": 1},
                "max_orders": 50,
                "current_orders": 15,
                "available_slots": 35,
                "status": "published",
                "status_text": "已发布",
                "created_at": "2024-11-30T18:00:00Z"
            }
        ],
        "pagination": {}
    },
    "message": "餐次列表查询成功"
}
```

#### 3.2 获取餐次详情
```
GET /api/meals/{meal_id}
```

**权限**: 用户

**路径参数**:
- `meal_id`: 餐次ID

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meal_id": 1,
        "date": "2024-12-01",
        "slot": "lunch",
        "slot_text": "午餐",
        "description": "红烧肉套餐",
        "base_price_cents": 1500,
        "base_price_yuan": 15.0,
        "max_orders": 50,
        "current_orders": 15,
        "available_slots": 35,
        "status": "published",
        "status_text": "已发布",
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
                "wechat_name": "李四",
                "amount_yuan": 21.0,
                "addon_selections": {"1": 2},
                "created_at": "2024-12-01T08:30:00Z"
            }
        ]
    },
    "message": "餐次详情查询成功"
}
```

### 4. 订单模块 `/api/orders`

#### 4.1 创建订单
```
POST /api/orders
```

**权限**: 用户

**请求参数**:
```json
{
    "meal_id": 1,
    "addon_selections": {
        "1": 2,
        "2": 1
    }
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "order_id": 1,
        "meal_id": 1,
        "amount_cents": 2100,
        "amount_yuan": 21.0,
        "addon_selections": {"1": 2, "2": 1},
        "transaction_no": "TXN20241201000002",
        "remaining_balance_yuan": 29.0,
        "created_at": "2024-12-01T10:30:00Z"
    },
    "message": "订单创建成功，金额 21.00 元"
}
```

#### 4.2 取消订单
```
DELETE /api/orders/{order_id}
```

**权限**: 用户

**路径参数**:
- `order_id`: 订单ID

**请求参数**:
```json
{
    "cancel_reason": "用户主动取消"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "order_id": 1,
        "meal_id": 1,
        "refund_amount_yuan": 21.0,
        "transaction_no": "TXN20241201000003",
        "cancel_reason": "用户主动取消"
    },
    "message": "订单已取消，退款 21.00 元"
}
```

#### 4.3 获取用户订单列表
```
GET /api/orders/my
```

**权限**: 用户

**查询参数**:
- `status`: 订单状态 (active/canceled/completed)，可选
- `offset`: 偏移量，默认0
- `limit`: 每页条数，最大100，默认20

**响应数据**:
```json
{
    "success": true,
    "data": {
        "orders": [
            {
                "order_id": 1,
                "meal_info": {
                    "meal_id": 1,
                    "date": "2024-12-01",
                    "slot": "lunch",
                    "slot_text": "午餐",
                    "description": "红烧肉套餐"
                },
                "amount_yuan": 21.0,
                "addon_selections": {"1": 2, "2": 1},
                "status": "active",
                "status_text": "已下单",
                "created_at": "2024-12-01T10:30:00Z"
            }
        ],
        "pagination": {}
    },
    "message": "订单列表查询成功"
}
```

#### 4.4 获取餐次订单详情
```
GET /api/orders/meal/{meal_id}
```

**权限**: 用户

**路径参数**:
- `meal_id`: 餐次ID

**响应数据**:
```json
{
    "success": true,
    "data": {
        "order_id": 1,
        "user_info": {
            "user_id": 1,
            "wechat_name": "张三"
        },
        "meal_info": {
            "meal_id": 1,
            "date": "2024-12-01",
            "slot": "lunch",
            "slot_text": "午餐",
            "description": "红烧肉套餐",
            "meal_status": "published"
        },
        "order_details": {
            "total_amount_yuan": 21.0,
            "base_price_yuan": 15.0,
            "addons_price_yuan": 6.0,
            "selected_addons": [
                {
                    "addon_id": 1,
                    "name": "加鸡腿",
                    "unit_price_yuan": 3.0,
                    "quantity": 2,
                    "total_price_yuan": 6.0
                }
            ],
            "status": "active",
            "created_at": "2024-12-01T10:30:00Z"
        }
    },
    "message": "订单查询成功"
}
```

### 5. 管理员模块 `/api/admin`

#### 5.1 附加项管理

##### 5.1.1 创建附加项
```
POST /api/admin/addons
```

**权限**: 管理员

**请求参数**:
```json
{
    "name": "加鸡腿",
    "price_cents": 300,
    "display_order": 1,
    "is_default": false
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "addon_id": 1,
        "name": "加鸡腿",
        "price_cents": 300,
        "price_yuan": 3.0,
        "display_order": 1,
        "is_default": false,
        "status": "active",
        "created_at": "2024-12-01T10:30:00Z"
    },
    "message": "附加项 \"加鸡腿\" 创建成功"
}
```

##### 5.1.2 停用附加项
```
DELETE /api/admin/addons/{addon_id}
```

**权限**: 管理员

**路径参数**:
- `addon_id`: 附加项ID

**响应数据**:
```json
{
    "success": true,
    "data": {
        "addon_id": 1,
        "addon_name": "加鸡腿"
    },
    "message": "附加项 \"加鸡腿\" 已停用"
}
```

##### 5.1.3 获取附加项列表
```
GET /api/admin/addons
```

**权限**: 管理员

**查询参数**:
- `status`: 状态筛选 (active/inactive)，可选

**响应数据**:
```json
{
    "success": true,
    "data": {
        "addons": [
            {
                "addon_id": 1,
                "name": "加鸡腿",
                "price_cents": 300,
                "price_yuan": 3.0,
                "display_order": 1,
                "is_default": false,
                "status": "active",
                "created_at": "2024-12-01T10:30:00Z"
            }
        ]
    },
    "message": "附加项列表查询成功"
}
```

#### 5.2 餐次管理

##### 5.2.1 发布餐次
```
POST /api/admin/meals
```

**权限**: 管理员

**请求参数**:
```json
{
    "date": "2024-12-01",
    "slot": "lunch",
    "description": "红烧肉套餐",
    "base_price_cents": 1500,
    "addon_config": {
        "1": 3,
        "2": 1
    },
    "max_orders": 50
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meal_id": 1,
        "date": "2024-12-01",
        "slot": "lunch",
        "description": "红烧肉套餐",
        "base_price_yuan": 15.0,
        "addon_config": {"1": 3, "2": 1},
        "max_orders": 50,
        "status": "published",
        "created_at": "2024-11-30T18:00:00Z"
    },
    "message": "2024-12-01 午餐 餐次发布成功"
}
```

##### 5.2.2 锁定餐次
```
PUT /api/admin/meals/{meal_id}/lock
```

**权限**: 管理员

**路径参数**:
- `meal_id`: 餐次ID

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meal_id": 1,
        "meal_date": "2024-12-01",
        "meal_slot": "lunch",
        "current_orders": 15
    },
    "message": "餐次 2024-12-01 午餐 已锁定，当前订单数: 15"
}
```

##### 5.2.3 完成餐次
```
PUT /api/admin/meals/{meal_id}/complete
```

**权限**: 管理员

**路径参数**:
- `meal_id`: 餐次ID

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meal_id": 1,
        "meal_date": "2024-12-01",
        "meal_slot": "lunch",
        "completed_orders_count": 15,
        "completed_orders": [
            {"order_id": 1, "user_id": 2},
            {"order_id": 2, "user_id": 3}
        ]
    },
    "message": "餐次 2024-12-01 午餐 已完成，共完成 15 个订单"
}
```

##### 5.2.4 取消餐次
```
DELETE /api/admin/meals/{meal_id}
```

**权限**: 管理员

**路径参数**:
- `meal_id`: 餐次ID

**请求参数**:
```json
{
    "cancel_reason": "食材临时短缺"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meal_id": 1,
        "original_status": "published",
        "canceled_orders_count": 15,
        "total_refund_amount_yuan": 315.0,
        "cancel_reason": "食材临时短缺"
    },
    "message": "餐次取消成功，共退款 15 个订单，总金额 315.00 元"
}
```

#### 5.3 用户管理

##### 5.3.1 获取用户列表
```
GET /api/admin/users
```

**权限**: 管理员

**查询参数**:
- `status`: 用户状态 (active/suspended)，可选
- `is_admin`: 管理员筛选 (true/false)，可选
- `offset`: 偏移量，默认0
- `limit`: 每页条数，最大100，默认20

**响应数据**:
```json
{
    "success": true,
    "data": {
        "users": [
            {
                "user_id": 1,
                "open_id": "wx_openid_123",
                "wechat_name": "张三",
                "balance_yuan": 50.0,
                "is_admin": false,
                "is_admin_text": "否",
                "status": "active",
                "status_text": "正常",
                "created_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-12-01T10:30:00Z"
            }
        ],
        "pagination": {}
    },
    "message": "用户列表查询成功"
}
```

##### 5.3.2 调整用户余额
```
PUT /api/admin/users/{user_id}/balance
```

**权限**: 管理员

**路径参数**:
- `user_id`: 用户ID

**请求参数**:
```json
{
    "amount_cents": 5000,
    "reason": "用户充值"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "target_user_id": 2,
        "target_user_name": "张三",
        "adjustment_amount_yuan": 50.0,
        "balance_before_yuan": 20.0,
        "balance_after_yuan": 70.0,
        "transaction_no": "TXN20241201000004",
        "operation_type": "充值",
        "reason": "用户充值"
    },
    "message": "用户余额充值成功，充值金额 50.00 元，余额 20.00 → 70.00 元"
}
```

##### 5.3.3 设置管理员权限
```
PUT /api/admin/users/{user_id}/admin
```

**权限**: 管理员

**路径参数**:
- `user_id`: 用户ID

**请求参数**:
```json
{
    "is_admin": true
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "target_user_id": 2,
        "target_user_name": "张三",
        "is_admin": true,
        "changed": true
    },
    "message": "用户权限已更新为管理员"
}
```

##### 5.3.4 设置用户状态
```
PUT /api/admin/users/{user_id}/status
```

**权限**: 管理员

**路径参数**:
- `user_id`: 用户ID

**请求参数**:
```json
{
    "status": "suspended",
    "reason": "违规操作"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "target_user_id": 2,
        "target_user_name": "张三",
        "status": "suspended",
        "changed": true,
        "reason": "违规操作"
    },
    "message": "用户账户已停用，原因：违规操作"
}
```

##### 5.3.5 管理员取消订单
```
DELETE /api/admin/orders/{order_id}
```

**权限**: 管理员

**路径参数**:
- `order_id`: 订单ID

**请求参数**:
```json
{
    "cancel_reason": "管理员取消"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "order_id": 1,
        "meal_id": 1,
        "refund_amount_yuan": 21.0,
        "transaction_no": "TXN20241201000005",
        "cancel_reason": "管理员取消"
    },
    "message": "订单已取消，退款 21.00 元"
}
```

## 常见错误信息

### 通用错误
- `请求参数错误`
- `请求体格式错误`
- `必填参数缺失`
- `参数值无效`

### 认证错误
- `未授权访问`
- `Token无效或已过期`
- `Token格式错误`
- `权限不足`
- `微信授权失败`
- `用户账户已停用`

### 业务错误
- `用户不存在`
- `餐次不存在`
- `订单不存在`
- `附加项不存在`
- `餐次已满`
- `餐次状态不允许操作`
- `重复下单`
- `订单状态不允许操作`
- `附加项数量超限`
- `用户只能取消自己的订单`

### 系统错误
- `内部服务器错误`
- `数据库连接失败`
- `数据库操作失败`
- `外部服务调用失败`

## 使用示例

### 微信小程序登录
```javascript
// 1. 获取微信授权码
wx.login({
    success: res => {
        const code = res.code;
        
        // 2. 调用登录接口
        wx.request({
            url: 'https://api.ganghaofan.com/api/auth/wechat/login',
            method: 'POST',
            data: {
                code: code,
                wechat_name: '张三',
                avatar_url: 'https://wx.avatar.com/123.jpg'
            },
            success: res => {
                if (res.data.success) {
                    // 3. 保存Token
                    wx.setStorageSync('access_token', res.data.data.access_token);
                    wx.setStorageSync('user_info', res.data.data.user_info);
                }
            }
        });
    }
});
```

### API调用示例
```javascript
// 获取餐次列表
wx.request({
    url: 'https://api.ganghaofan.com/api/meals',
    method: 'GET',
    header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('access_token')
    },
    data: {
        start_date: '2024-12-01',
        end_date: '2024-12-07'
    },
    success: res => {
        if (res.data.success) {
            console.log('餐次列表:', res.data.data.meals);
        }
    }
});
```

### 下单流程
```javascript
// 创建订单
wx.request({
    url: 'https://api.ganghaofan.com/api/orders',
    method: 'POST',
    header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('access_token'),
        'Content-Type': 'application/json'
    },
    data: {
        meal_id: 1,
        addon_selections: {
            "1": 2,  // 加鸡腿 x2
            "2": 1   // 加饮料 x1
        }
    },
    success: res => {
        if (res.data.success) {
            wx.showToast({
                title: '下单成功',
                icon: 'success'
            });
        } else {
            wx.showToast({
                title: res.data.error,
                icon: 'none'
            });
        }
    }
});
```

## 开发说明

### 服务端开发
1. **严格按照此API文档实现**: 确保请求/响应格式完全一致
2. **数据验证**: 使用Pydantic进行完整的数据验证
3. **错误处理**: 统一错误信息格式
4. **日志记录**: 记录所有API调用和关键业务操作

### 客户端开发  
1. **统一请求封装**: 封装HTTP请求方法，处理Token和错误
2. **错误处理**: 根据错误信息进行相应的用户提示
3. **数据缓存**: 合理缓存用户信息和餐次数据
4. **加载状态**: 显示加载状态，提升用户体验

这套API设计基于doc/db下的数据库操作逻辑，确保了前后端的一致性和完整性。