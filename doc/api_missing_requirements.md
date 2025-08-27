# 需要补充的API接口需求文档

基于新编写的页面需求文档，与现有的 `api.md` 对比分析，发现以下接口需要补充或调整。

## 重要说明：多附加项支持

**附加项多选机制**：
- **管理员发布餐次**：可以选择多个不同附加项（如加鸡腿、不要米饭、少盐等），并为每个附加项设置最大可选数量
- **用户下单时**：可以同时选择多个附加项，每个附加项可选择 0 到最大数量范围内的任意数量
- **支持负价格**：附加项可以是负价格（如“不要米饭”-¥1.00）
- **数据结构**：JSON 格式 `{"addon_id": quantity}` 支持多附加项选择

## 接口分析总结

### 已存在的接口（无需补充）
- ✅ 用户认证相关接口
- ✅ 基础用户信息查询
- ✅ 餐次CRUD操作
- ✅ 订单CRUD操作
- ✅ 附加项管理
- ✅ 基础管理员功能

### 需要补充的接口

## 1. 餐次管理相关接口

### 1.1 修改餐次接口
**现状**: 缺少餐次更新接口
**需求**: 管理员发布餐页面需要能够修改已发布餐次的配置

```
PUT /api/admin/meals/{meal_id}
```

**权限**: 管理员

**请求参数**:
```json
{
    "description": "更新后的餐次描述",
    "base_price_cents": 1800,
    "addon_config": {
        "1": 3,     // 加鸡腿最多3个
        "2": 1,     // 加饮料最多1个  
        "3": 1,     // 不要米饭最多1个
        "4": 1      // 少盐最多1个
    },
    "max_orders": 60
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
        "description": "更新后的餐次描述",
        "base_price_yuan": 18.0,
        "addon_config": {"1": 3, "2": 1, "3": 1, "4": 1},
        "max_orders": 60,
        "status": "published",
        "updated_at": "2024-12-01T15:30:00Z"
    },
    "message": "餐次信息更新成功"
}
```

### 1.2 取消餐次锁定接口
**现状**: 缺少取消锁定接口
**需求**: 管理员需要能够将锁定状态的餐次恢复为发布状态

```
PUT /api/admin/meals/{meal_id}/unlock
```

**权限**: 管理员

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meal_id": 1,
        "meal_date": "2024-12-01",
        "meal_slot": "lunch",
        "status": "published"
    },
    "message": "餐次锁定已取消，恢复为已发布状态"
}
```

### 1.3 获取餐次订单统计接口
**现状**: 缺少餐次统计接口
**需求**: 管理员需要查看特定餐次的订单统计信息

```
GET /api/admin/meals/{meal_id}/statistics
```

**权限**: 管理员

**响应数据**:
```json
{
    "success": true,
    "data": {
        "meal_info": {
            "meal_id": 1,
            "date": "2024-12-01",
            "slot": "lunch",
            "description": "红烧肉套餐"
        },
        "order_statistics": {
            "total_orders": 25,
            "active_orders": 23,
            "canceled_orders": 2,
            "total_amount_yuan": 487.50,
            "active_amount_yuan": 456.00
        },
        "addon_statistics": [
            {
                "addon_id": 1,
                "addon_name": "加鸡腿",
                "total_quantity": 35,
                "total_amount_yuan": 105.00
            }
        ]
    },
    "message": "餐次统计查询成功"
}
```

## 2. 订单管理相关接口

### 2.1 修改订单接口
**现状**: 缺少订单修改接口
**需求**: 用户在餐次未锁定时应该能够修改自己的订单

```
PUT /api/orders/{order_id}
```

**权限**: 用户（订单所有者）

**请求参数**:
```json
{
    "addon_selections": {
        "1": 2,     // 选择加鸡腿 2个
        "2": 1,     // 选择加饮料 1个
        "3": 1,     // 选择不要米饭 1个
        "4": 0      // 不选择少盐
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
        "old_amount_yuan": 21.0,
        "new_amount_yuan": 23.0,
        "amount_difference_yuan": 2.0,
        "addon_selections": {"1": 2, "2": 1, "3": 1, "4": 0},
        "transaction_no": "TXN20241201000006",
        "remaining_balance_yuan": 27.0,
        "updated_at": "2024-12-01T16:30:00Z"
    },
    "message": "订单修改成功，补缴金额 2.00 元"
}
```

### 2.2 获取完整订单列表接口（带过滤）
**现状**: 现有接口功能不够完整
**需求**: 订单列表页面需要支持多维度过滤和管理员查看所有订单

```
GET /api/orders
```

**权限**: 用户（仅返回自己的订单）/ 管理员（返回所有订单）

**查询参数**:
```
meal_id: 餐次ID过滤（可选）
user_id: 用户ID过滤（管理员可用）
status: 订单状态过滤（active/canceled/completed）
date_start: 开始日期（YYYY-MM-DD）
date_end: 结束日期（YYYY-MM-DD）
page: 页码，默认1
size: 每页大小，默认20
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "orders": [
            {
                "order_id": 1,
                "user_id": 2,
                "user_name": "张三",
                "meal_id": 1,
                "meal_date": "2024-12-01",
                "meal_slot": "lunch",
                "meal_slot_text": "午餐",
                "meal_description": "红烧肉套餐",
                "amount_yuan": 21.0,
                "addon_selections": {"1": 2, "2": 1, "3": 1, "4": 0},
                "addon_details": [
                    {
                        "addon_id": 1,
                        "name": "加鸡腿",
                        "price_yuan": 3.0,
                        "quantity": 2,
                        "total_yuan": 6.0
                    },
                    {
                        "addon_id": 2,
                        "name": "加饮料",
                        "price_yuan": 2.0,
                        "quantity": 1,
                        "total_yuan": 2.0
                    },
                    {
                        "addon_id": 3,
                        "name": "不要米饭",
                        "price_yuan": -1.0,
                        "quantity": 1,
                        "total_yuan": -1.0
                    }
                ],
                "status": "active",
                "status_text": "有效",
                "created_at": "2024-12-01T10:30:00Z",
                "updated_at": "2024-12-01T10:30:00Z"
            }
        ],
        "pagination": {
            "total_count": 100,
            "current_page": 1,
            "per_page": 20,
            "total_pages": 5,
            "has_next": true,
            "has_prev": false
        },
        "statistics": {
            "total_orders": 100,
            "active_orders": 85,
            "canceled_orders": 15,
            "total_amount_yuan": 2350.0,
            "active_amount_yuan": 2100.0
        }
    },
    "message": "订单列表查询成功"
}
```

## 3. 用户账单相关接口

### 3.1 增强账单历史接口
**现状**: 现有接口功能不够完整
**需求**: 需要支持更多筛选条件和管理员查看任意用户账单

```
GET /api/users/{user_id}/ledger
```

**权限**: 用户（仅查看自己的，user_id必须是自己）/ 管理员（可查看任意用户）

**查询参数**:
```
type: 交易类型（recharge/order/refund/all）
direction: 交易方向（in/out/all）
date_start: 开始日期（YYYY-MM-DD）
date_end: 结束日期（YYYY-MM-DD）
amount_min: 最小金额（分）
amount_max: 最大金额（分）
page: 页码，默认1
size: 每页大小，默认20
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_info": {
            "user_id": 1,
            "wechat_name": "张三",
            "current_balance_yuan": 88.50
        },
        "ledger_records": [
            {
                "ledger_id": 1,
                "transaction_no": "TXN20241201000001",
                "type": "recharge",
                "type_display": "充值",
                "direction": "in",
                "direction_display": "收入",
                "amount_yuan": 100.0,
                "amount_display": "+100.00",
                "balance_before_yuan": 0.0,
                "balance_after_yuan": 100.0,
                "order_id": null,
                "order_info": null,
                "description": "管理员充值",
                "operator_id": 2,
                "operator_name": "管理员",
                "created_at": "2024-12-01T10:30:00Z"
            },
            {
                "ledger_id": 2,
                "transaction_no": "TXN20241201000002",
                "type": "order",
                "type_display": "订餐消费",
                "direction": "out",
                "direction_display": "支出",
                "amount_yuan": 21.0,
                "amount_display": "-21.00",
                "balance_before_yuan": 100.0,
                "balance_after_yuan": 79.0,
                "order_id": 1,
                "order_info": {
                    "meal_date": "2024-12-01",
                    "meal_slot": "lunch",
                    "meal_description": "红烧肉套餐",
                    "addon_summary": "加鸡腿×2,加饮料×1,不要米饭×1"
                },
                "description": "订餐扣费",
                "operator_id": null,
                "operator_name": null,
                "created_at": "2024-12-01T11:30:00Z"
            }
        ],
        "pagination": {
            "total_count": 50,
            "current_page": 1,
            "per_page": 20,
            "total_pages": 3,
            "has_next": true,
            "has_prev": false
        },
        "statistics": {
            "total_in": 500.0,
            "total_out": 420.0,
            "net_amount": 80.0,
            "recharge_amount": 500.0,
            "order_amount": 400.0,
            "refund_amount": 20.0,
            "transaction_count": 50
        }
    },
    "message": "账单历史查询成功"
}
```

### 3.2 账单统计接口
**现状**: 缺少单独的统计接口
**需求**: 用户账单页面需要显示统计信息

```
GET /api/users/{user_id}/ledger/statistics
```

**权限**: 用户（仅查看自己的）/ 管理员（可查看任意用户）

**查询参数**: 同账单历史接口的筛选参数

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_info": {
            "user_id": 1,
            "wechat_name": "张三",
            "current_balance_yuan": 88.50
        },
        "statistics": {
            "total_in": 500.0,
            "total_out": 420.0,
            "net_amount": 80.0,
            "recharge_amount": 500.0,
            "order_amount": 400.0,
            "refund_amount": 20.0,
            "transaction_count": 50,
            "recharge_count": 5,
            "order_count": 18,
            "refund_count": 2
        },
        "monthly_statistics": [
            {
                "month": "2024-12",
                "total_in": 200.0,
                "total_out": 150.0,
                "net_amount": 50.0
            }
        ]
    },
    "message": "账单统计查询成功"
}
```

## 4. 用户管理相关接口

### 4.1 增强用户列表接口
**现状**: 现有接口功能不够完整
**需求**: 用户管理页面需要支持搜索、筛选和详细统计

```
GET /api/admin/users
```

**权限**: 管理员

**查询参数**:
```
keyword: 搜索关键词（昵称、OpenID）
status: 用户状态（active/suspended/all）
balance_min: 最小余额（分）
balance_max: 最大余额（分）
has_orders: 是否有订单记录（true/false）
sort: 排序字段（created_at/balance/last_login/order_count）
order: 排序方向（asc/desc）
page: 页码，默认1
size: 每页大小，默认20
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "users": [
            {
                "user_id": 1,
                "open_id": "oAB***EF",
                "wechat_name": "张三",
                "avatar_url": "https://wx.avatar.com/123.jpg",
                "balance_cents": 8850,
                "balance_yuan": 88.50,
                "is_admin": false,
                "status": "active",
                "status_display": "正常",
                "created_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-12-01T10:30:00Z",
                "order_count": 15,
                "total_consumed_yuan": 320.0,
                "last_order_date": "2024-11-30"
            }
        ],
        "pagination": {
            "total_count": 52,
            "current_page": 1,
            "per_page": 20,
            "total_pages": 3,
            "has_next": true,
            "has_prev": false
        },
        "statistics": {
            "total_users": 52,
            "active_users": 48,
            "suspended_users": 4,
            "total_balance_yuan": 4387.50,
            "users_with_orders": 45,
            "users_without_orders": 7
        }
    },
    "message": "用户列表查询成功"
}
```

### 4.2 用户充值接口
**现状**: 现有接口名称不够明确
**需求**: 管理员用户管理页面需要独立的充值接口

```
POST /api/admin/users/{user_id}/recharge
```

**权限**: 管理员

**请求参数**:
```json
{
    "amount_cents": 5000,
    "reason": "用户申请充值"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_id": 1,
        "user_name": "张三",
        "recharge_amount_yuan": 50.0,
        "balance_before_yuan": 88.50,
        "balance_after_yuan": 138.50,
        "transaction_no": "TXN20241201000007",
        "reason": "用户申请充值",
        "operator_id": 2,
        "operator_name": "管理员"
    },
    "message": "用户充值成功，充值金额 50.00 元"
}
```

### 4.3 用户扣款接口
**现状**: 缺少扣款接口
**需求**: 管理员需要能够扣减用户余额

```
POST /api/admin/users/{user_id}/deduct
```

**权限**: 管理员

**请求参数**:
```json
{
    "amount_cents": 2000,
    "reason": "补扣费用"
}
```

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_id": 1,
        "user_name": "张三",
        "deduct_amount_yuan": 20.0,
        "balance_before_yuan": 138.50,
        "balance_after_yuan": 118.50,
        "transaction_no": "TXN20241201000008",
        "reason": "补扣费用",
        "operator_id": 2,
        "operator_name": "管理员"
    },
    "message": "用户扣款成功，扣款金额 20.00 元"
}
```

### 4.4 用户详情接口
**现状**: 缺少用户详细信息查询接口
**需求**: 管理员需要查看用户的详细统计信息

```
GET /api/admin/users/{user_id}/detail
```

**权限**: 管理员

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_info": {
            "user_id": 1,
            "open_id": "oABC***DEF",
            "wechat_name": "张三",
            "avatar_url": "https://wx.avatar.com/123.jpg",
            "balance_yuan": 118.50,
            "is_admin": false,
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "last_login_at": "2024-12-01T10:30:00Z"
        },
        "order_statistics": {
            "total_orders": 15,
            "active_orders": 2,
            "completed_orders": 10,
            "canceled_orders": 3,
            "total_amount_yuan": 320.0,
            "avg_order_amount_yuan": 21.33,
            "first_order_date": "2024-01-15",
            "last_order_date": "2024-11-30"
        },
        "financial_statistics": {
            "total_recharged_yuan": 500.0,
            "total_consumed_yuan": 320.0,
            "total_refunded_yuan": 61.50,
            "net_consumption_yuan": 258.50,
            "recharge_count": 5,
            "last_recharge_date": "2024-11-20"
        },
        "recent_activities": [
            {
                "type": "order",
                "description": "订餐消费 21.00 元",
                "date": "2024-11-30T12:00:00Z"
            },
            {
                "type": "recharge",
                "description": "充值 100.00 元",
                "date": "2024-11-20T09:30:00Z"
            }
        ]
    },
    "message": "用户详情查询成功"
}
```

### 4.5 用户统计总览接口
**现状**: 缺少用户总体统计接口
**需求**: 用户管理页面需要显示系统用户统计信息

```
GET /api/admin/users/statistics
```

**权限**: 管理员

**响应数据**:
```json
{
    "success": true,
    "data": {
        "user_statistics": {
            "total_users": 52,
            "active_users": 48,
            "suspended_users": 4,
            "admin_users": 2,
            "registered_today": 3,
            "registered_this_week": 8,
            "registered_this_month": 15
        },
        "financial_statistics": {
            "total_balance_yuan": 4387.50,
            "avg_balance_yuan": 84.37,
            "users_with_positive_balance": 45,
            "users_with_zero_balance": 7,
            "total_recharged_this_month_yuan": 2500.0,
            "total_consumed_this_month_yuan": 1800.0
        },
        "activity_statistics": {
            "users_with_orders": 45,
            "users_without_orders": 7,
            "users_ordered_today": 12,
            "users_ordered_this_week": 35,
            "avg_orders_per_user": 8.5
        }
    },
    "message": "用户统计查询成功"
}
```

## 5. 其他支持接口

### 5.1 获取可用附加项接口（普通用户）
**现状**: 缺少用户端获取附加项接口
**需求**: 用户订餐页面需要获取可用的附加项列表

```
GET /api/addons
```

**权限**: 用户

**查询参数**:
```
status: 状态筛选，默认active
```

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
                "is_default": false
            },
            {
                "addon_id": 2,
                "name": "加饮料",
                "price_cents": 200,
                "price_yuan": 2.0,
                "display_order": 2,
                "is_default": false
            },
            {
                "addon_id": 3,
                "name": "不要米饭",
                "price_cents": -100,
                "price_yuan": -1.0,
                "display_order": 3,
                "is_default": false
            },
            {
                "addon_id": 4,
                "name": "少盐",
                "price_cents": 0,
                "price_yuan": 0.0,
                "display_order": 4,
                "is_default": false
            }
        ]
    },
    "message": "附加项列表查询成功"
}
```

### 5.2 获取用户基本信息接口优化
**现状**: 现有接口路径为 `/api/users/profile`
**需求**: 建议增加更简洁的路径支持

```
GET /api/users/me
```

**权限**: 用户

**响应数据**: 与现有 `/api/users/profile` 相同

## 6. 需要调整的现有接口

### 6.1 餐次详情接口增强
**建议**: 现有的 `GET /api/meals/{meal_id}` 接口增加更多信息

增加字段：
- `meal_base_price_yuan`: 基础价格（元）
- `can_order`: 用户是否可以下单（布尔值）
- `user_order`: 当前用户的订单信息（如果已订餐）

### 6.2 用户订单列表接口路径调整
**建议**: 将 `GET /api/orders/my` 调整为 `GET /api/orders?user_id=me` 的形式，与统一的订单接口合并

## 实现优先级

### 高优先级（核心功能必需）
1. ✅ 餐次修改接口 (`PUT /api/admin/meals/{meal_id}`)
2. ✅ 订单修改接口 (`PUT /api/orders/{order_id}`)
3. ✅ 完整订单列表接口 (`GET /api/orders`)
4. ✅ 用户充值/扣款接口
5. ✅ 增强用户列表接口

### 中优先级（体验优化）
1. 🟡 餐次统计接口
2. 🟡 取消餐次锁定接口
3. 🟡 账单历史接口增强
4. 🟡 用户详情接口

### 低优先级（功能完善）
1. 🟠 各类统计接口
2. 🟠 用户端附加项接口
3. 🟠 接口路径调整

## 数据模型注意事项

1. **金额字段**: 所有涉及金额的接口都应该同时返回 `*_cents`（分）和 `*_yuan`（元）两个字段
2. **时间格式**: 统一使用 ISO 8601 格式 (`2024-12-01T10:30:00Z`)
3. **状态字段**: 除了状态码，还应返回 `*_text` 或 `*_display` 字段用于显示
4. **分页**: 统一使用 `pagination` 对象包含分页信息
5. **权限**: 每个接口都需要明确权限要求和权限验证逻辑

这些接口的实现将完善整个系统的功能闭环，为前端页面提供完整的数据支持。