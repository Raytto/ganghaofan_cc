# 个人中心页面 (profile.js)

## 页面概述

个人中心页面展示用户信息、管理员状态，并提供管理模式开关功能。管理员可以通过此页面切换管理模式，以访问管理功能。

## 页面路径
- 文件位置：`client/pages/profile/profile.js`
- 页面路径：`pages/profile/profile`
- Tab页面：是（底部导航栏第二个）

## 页面功能

### 主要职责
1. **用户信息展示**：显示头像、昵称、余额等基本信息
2. **管理员标识**：显示管理员身份标识
3. **管理模式切换**：管理员可开启/关闭管理模式
4. **功能入口**：提供其他功能页面的入口（占位）

## 页面数据结构

### data 字段
```javascript
{
  userInfo: Object,      // 用户详细信息
  isAdmin: Boolean,      // 是否为管理员
  adminMode: Boolean,    // 管理模式开关状态
  loading: Boolean       // 页面加载状态
}
```

### userInfo 对象结构
```javascript
{
  user_id: Number,           // 用户ID
  open_id: String,          // 微信OpenID
  wechat_name: String,      // 微信昵称
  avatar_url: String,       // 头像URL
  balance_cents: Number,    // 余额（分）
  balance_yuan: Number,     // 余额（元）
  is_admin: Boolean,        // 管理员标识
  created_at: String,       // 创建时间
  last_login_at: String,    // 最后登录时间
  order_statistics: Object, // 订单统计
  transaction_statistics: Object // 交易统计
}
```

## 管理模式系统

### 核心逻辑
1. **状态初始化**：
   - 管理员用户首次使用时，管理模式默认开启
   - 普通用户无法看到管理模式开关
   - 状态保存在本地存储中

2. **状态管理**：
   ```javascript
   // 管理员首次使用
   if (isAdmin && adminMode === '') {
     adminMode = true  // 默认开启
   }
   
   // 非管理员强制关闭
   if (!isAdmin) {
     adminMode = false
   }
   ```

3. **状态持久化**：
   - 使用 `wx.setStorageSync('admin_mode', boolean)` 保存
   - 页面加载时从本地存储读取状态

### 管理模式开关交互
- **仅管理员可见**：通过 `wx:if="{{isAdmin}}"` 控制显示
- **实时生效**：切换后立即保存到本地存储
- **Toast提示**：切换时显示"管理模式已开启/关闭"

## API 调用

### 获取用户信息
- **接口**：`GET /users/profile`
- **权限**：需要登录Token
- **调用时机**：
  - 页面加载时 (onLoad)
  - 页面显示时 (onShow)
- **返回数据**：包含用户完整信息和统计数据

## 页面布局

### 1. 用户信息卡片
```
┌─────────────────────────────────┐
│  [头像]  昵称                    │
│          用户ID: 123             │
│          余额: ¥50.00            │
│          [管理员标识]             │
└─────────────────────────────────┘
```

### 2. 管理模式开关（仅管理员）
```
┌─────────────────────────────────┐
│  管理模式                        │
│  开启后可使用管理员功能          │
│                        [开关]    │
└─────────────────────────────────┘
```

### 3. 功能菜单
```
┌─────────────────────────────────┐
│  📋 我的订单                  >  │
│  💰 账单明细                  >  │
│  ⚙️ 设置                      >  │
└─────────────────────────────────┘
```

## 错误处理

### 1. Token失效
```javascript
if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
  // 清除本地数据
  wx.removeStorageSync('access_token')
  wx.removeStorageSync('user_info')
  // 跳转到欢迎页重新登录
  wx.reLaunch({ url: '../welcome/welcome' })
}
```

### 2. 网络错误
- 显示"加载失败"Toast提示
- 保持在当前页面，允许用户重试

### 3. 未登录状态
- 检测到无Token时自动跳转到欢迎页面

## 工具函数集成

### admin.js 工具函数
项目提供了 `utils/admin.js` 工具模块，包含以下函数：

1. **getAdminModeStatus()**
   - 获取当前管理员和管理模式状态
   - 返回：`{ isAdmin: boolean, adminMode: boolean }`

2. **setAdminModeStatus(adminMode)**
   - 设置管理模式状态
   - 仅管理员可设置

3. **isAdminModeEnabled()**
   - 检查是否为管理员且开启了管理模式
   - 返回：`boolean`

4. **refreshAdminStatus()**
   - 异步刷新管理员状态
   - 从服务器获取最新信息

### 使用示例
```javascript
const adminUtils = require('../../utils/admin.js')

// 获取管理模式状态
const { isAdmin, adminMode } = adminUtils.getAdminModeStatus()

// 检查是否可以使用管理功能
if (adminUtils.isAdminModeEnabled()) {
  // 显示管理功能
}
```

## 界面布局

### 1. 卡片设计
- 信息卡片布局
- 清晰的信息层次

### 2. 功能区分
- 用户信息突出显示
- 管理员标识醒目
- 功能入口清晰

### 3. 响应式设计
- 适配不同设备屏幕
- 保持布局一致性

## 页面状态流转

### 1. 初始加载
```
onLoad → 
  loadUserInfo() → 
    获取用户信息 → 
      判断管理员身份 → 
        设置管理模式状态 → 
          更新页面显示
```

### 2. 管理模式切换
```
用户切换开关 → 
  onAdminModeChange() → 
    更新本地存储 → 
      更新页面状态 → 
        显示Toast提示
```

## 扩展功能预留

### 1. 功能菜单项
- **我的订单**：跳转到订单列表页面
- **账单明细**：查看充值和消费记录
- **设置**：用户设置页面

### 2. 统计信息展示
- 订单统计数据
- 消费统计图表
- 充值记录

### 3. 管理功能入口
- 当管理模式开启时，可显示管理功能入口
- 如：发布餐次、用户管理等

## 安全考虑

### 1. 权限验证
- 前端通过 `is_admin` 字段控制显示
- 管理模式状态仅在前端记录
- 实际管理操作需要后端API权限验证

### 2. 状态隔离
- 管理模式状态与用户账号绑定
- 切换账号时自动重置状态
- 非管理员无法开启管理模式

### 3. 数据保护
- 敏感信息不在前端存储
- Token失效时自动清理本地数据

## 用户体验优化

### 1. 加载状态
- 显示"加载中..."提示
- 避免页面闪烁

### 2. 实时反馈
- 管理模式切换立即生效
- Toast提示操作结果

### 3. 信息层次
- 用户信息清晰展示
- 管理员功能明确区分
- 操作反馈及时准确