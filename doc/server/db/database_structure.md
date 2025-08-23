# 罡好饭 - 数据库结构设计文档

## 一、概述

本文档定义了罡好饭餐饮预订系统的数据库结构设计。系统使用DuckDB作为嵌入式数据库，所有金额字段使用分（cents）为单位以避免浮点数精度问题。

## 二、数据表结构

### 2.1 用户表（users）

存储用户基本信息和账户余额。

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    open_id VARCHAR(128) UNIQUE NOT NULL,      -- 微信OpenID，唯一标识
    wechat_name VARCHAR(100),                  -- 用户微信名
    avatar_url VARCHAR(500),                   -- 头像URL
    balance_cents INTEGER DEFAULT 0,           -- 账户余额（单位：分）
    is_admin BOOLEAN DEFAULT FALSE,            -- 是否管理员
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,                   -- 最后登录时间
    status VARCHAR(20) DEFAULT 'active'        -- 账户状态: unregisted/active/suspended
);

-- 索引
CREATE INDEX idx_users_open_id ON users(open_id);
```

### 2.2 餐次表（meals）

存储每日餐次信息。

```sql
CREATE TABLE meals (
    meal_id INTEGER PRIMARY KEY,
    date DATE NOT NULL,                        -- 餐次日期
    slot VARCHAR(20) NOT NULL,                 -- 时段: lunch/dinner
    description TEXT,                          -- 餐次描述（菜品信息等）
    base_price_cents INTEGER NOT NULL,         -- 不含附加项的基础价格（单位：分）
    addon_config JSON,                         -- 附加项配置：{"addon_id": max_quantity, "addon_id2": max_quantity}
    max_orders INTEGER DEFAULT 50,             -- 最大订餐数量
    current_orders INTEGER DEFAULT 0,          -- 当前已订数量
    status VARCHAR(20) DEFAULT 'published',  -- 状态: published/locked/completed/canceled
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, slot)                         -- 每天每个时段只能有一个餐次
);

-- 索引
CREATE INDEX idx_meals_date_slot ON meals(date, slot);
```

### 2.3 附加项表（addons）

存储所有可用的附加项。

```sql
CREATE TABLE addons (
    addon_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,                -- 附加项名称（如"加鸡腿"、"不要鸡腿"、"加饮料"）
    price_cents INTEGER NOT NULL,              -- 附加项价格（单位：分，可以为负数）
    display_order INTEGER DEFAULT 0,           -- 显示顺序
    is_default BOOLEAN DEFAULT FALSE           -- 是否默认选中
    status VARCHAR(20) DEFAULT 'active',       -- 状态: active/inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 记录创建时间，方便审计
);
```

### 2.4 订单表（orders）

存储用户订餐记录。

```sql
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,                  -- 用户ID
    meal_id INTEGER NOT NULL,                  -- 餐次ID
    amount_cents INTEGER NOT NULL,             -- 订单金额（单位：分，包含基础价格和选中附加项的价格）
    addon_selections JSON,                     -- 附加项选择：{"addon_id": quantity, "addon_id2": quantity}
    status VARCHAR(20) DEFAULT 'active',       -- 状态: active/canceled/completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (meal_id) REFERENCES meals(meal_id),
    UNIQUE(user_id, meal_id)                    -- 每人每餐次只能订一份
);

-- 索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_meal_id ON orders(meal_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
```

### 2.6 账本表（ledger）

记录所有余额变动明细，用于财务对账。

```sql
CREATE TABLE ledger (
    ledger_id INTEGER PRIMARY KEY,
    transaction_no VARCHAR(32) UNIQUE NOT NULL, -- 交易号（格式：TXN20241125120001）
    user_id INTEGER NOT NULL,                   -- 用户ID
    type VARCHAR(20) NOT NULL,                  -- 类型: recharge/order/refund
    direction VARCHAR(10) NOT NULL,             -- 方向: in/out
    amount_cents INTEGER NOT NULL,              -- 金额（单位：分，正数）
    balance_before_cents INTEGER NOT NULL,      -- 变动前余额
    balance_after_cents INTEGER NOT NULL,       -- 变动后余额
    order_id INTEGER,                           -- 关联订单ID（如果是订单相关）
    description VARCHAR(200),                   -- 交易描述
    operator_id INTEGER,                        -- 操作员ID（充值、调整时）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (operator_id) REFERENCES users(user_id)
);

-- 索引
CREATE INDEX idx_ledger_user_id ON ledger(user_id);
CREATE INDEX idx_ledger_type ON ledger(type);
CREATE INDEX idx_ledger_created_at ON ledger(created_at);
CREATE INDEX idx_ledger_transaction_no ON ledger(transaction_no);
```


## 三、数据库设计说明

### 3.1 设计原则

1. **金额处理**：所有金额字段使用整数分（cents）存储，避免浮点数精度问题
2. **唯一性约束**：确保数据完整性（如每人每餐限订一份）
3. **软删除**：使用状态字段而非物理删除，保留历史记录
4. **时间戳**：记录创建和更新时间，便于审计追踪
5. **事务一致性**：余额变动必须同时更新users表和ledger表

### 3.2 关键业务规则实现

1. **每人每餐限订一份**
   - 通过`orders`表的`UNIQUE(user_id, meal_id)`约束实现

2. **先扣款后订餐**
   - 在事务中同时更新余额和创建订单记录
   - 在`ledger`表中记录每笔交易

3. **餐次锁定**
   - 通过`meals.status`字段控制
   - `locked`状态的餐次不允许新增或修改订单

4. **余额追踪**
   - `ledger`表记录每笔资金变动
   - 包含变动前后余额，便于对账和回溯

5. **附加项数量控制**
   - 餐次的`addon_config`字段定义每个附加项的最大可选数量
   - 订单的`addon_selections`字段记录用户选择的各附加项数量
   - 业务逻辑需验证用户选择数量不超过餐次设定的最大值

### 3.3 索引策略

- **主键索引**：所有表都有自增主键
- **唯一索引**：业务唯一性字段（如open_id、order_no）
- **查询索引**：高频查询字段（如date、status、user_id）
- **组合索引**：常用组合查询（如date+slot）

### 3.4 扩展性考虑

1. **配菜功能**：可新增`meal_options`和`order_items`表
2. **评价功能**：可新增`reviews`表
3. **统计报表**：基于现有表结构可生成各类报表
4. **批量操作**：支持批量发布餐次、批量充值等

## 四、使用示例

### 4.1 附加项数量选择示例

```sql
-- 管理员发布餐次，设置"加鸡腿"最多3个，"加饮料"最多1个
INSERT INTO meals (date, slot, description, base_price_cents, addon_config, max_orders)
VALUES (
    '2024-11-27', 
    'lunch', 
    '红烧肉套餐', 
    1500,
    '{"1": 3, "2": 1}',  -- addon_id:1最多3个，addon_id:2最多1个
    50
);

-- 用户下单，选择2个"加鸡腿"和1个"加饮料"
INSERT INTO orders (user_id, meal_id, amount_cents, addon_selections)
VALUES (
    1, 
    1, 
    2100,  -- 1500基础 + 300*2加鸡腿 + 300*1加饮料
    '{"1": 2, "2": 1}'  -- 选择2个addon_id:1和1个addon_id:2
);

-- 查询用户订单详情
SELECT 
    o.order_id,
    o.amount_cents,
    o.addon_selections,
    m.description as meal_description,
    m.addon_config as meal_addon_limits
FROM orders o
JOIN meals m ON o.meal_id = m.meal_id
WHERE o.user_id = 1 AND o.status = 'active';
```

## 五、初始化脚本

```sql
-- 创建数据库（DuckDB）
-- 注：DuckDB会自动创建文件，无需显式创建数据库

-- 执行建表语句（按上述顺序）

-- 创建默认管理员账户
INSERT INTO users (open_id, nickname, is_admin, balance_cents) 
VALUES ('admin_openid_mock', '系统管理员', TRUE, 0);

-- 插入系统配置
-- （见system_config表的预设配置）
```

## 五、数据维护建议

1. **定期备份**：每日备份DuckDB数据文件
2. **数据清理**：定期归档历史订单数据（如保留最近3个月）
3. **性能优化**：定期执行`ANALYZE`更新统计信息
4. **监控告警**：监控数据库文件大小和查询性能

## 六、版本记录

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2024-11-25 | 初始版本，包含核心5张表 | System |
| v1.1 | 2024-11-26 | 新增meal_addons和order_addons表，支持餐次附加项功能 | System |
| v1.2 | 2024-11-26 | 修改为支持附加项数量选择，使用JSON格式存储配置和选择 | System |