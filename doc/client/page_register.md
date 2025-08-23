# 注册页面 (register.js)

## 页面概述

注册页面用于未注册用户完成个人信息设置，将用户从"未注册"状态转换为"已注册"状态。用户在此页面设置昵称和头像后，即可正常使用小程序的完整功能。

## 页面路径
- 文件位置：`client/pages/register/register.js`
- 页面路径：`../register/register`

## 页面功能

### 主要职责
1. **信息收集**：收集用户昵称和头像信息
2. **完成注册**：调用后端API完成用户注册流程
3. **状态转换**：将未注册用户转换为已注册用户

### 访问前提条件
- 用户必须已经通过微信静默登录获得了访问Token
- 用户在数据库中已存在记录，但 `wechat_name` 字段为空
- 通常由欢迎页面在检测到未注册状态时跳转而来

## 页面数据结构

### data 字段
```javascript
{
  userInfo: {
    avatarUrl: String,      // 用户选择的头像URL
    nickName: String        // 用户输入的昵称
  },
  canIUseGetUserProfile: Boolean,    // 是否支持getUserProfile API
  canIUseNicknameComp: Boolean,      // 是否支持昵称输入组件
  canRegister: Boolean,              // 是否可以进行注册
  registering: Boolean               // 是否正在注册中
}
```

## 核心功能逻辑

### 1. 页面加载 (onLoad)
```
页面加载 → 调用checkCanRegister() → 检查注册条件
```

### 2. 头像选择 (onChooseAvatar)
```
用户点击头像 → 调用头像选择组件 → 更新avatarUrl → 检查注册条件
```

### 3. 昵称输入 (onInputChange)
```
用户输入昵称 → 实时更新nickName → 检查注册条件
```

### 4. 注册条件检查 (checkCanRegister)
```javascript
// 检查逻辑
const canRegister = 
  nickName && 
  nickName.trim() && 
  avatarUrl && 
  avatarUrl !== defaultAvatarUrl
```

### 5. 完成注册流程 (onRegisterTap)
```
验证注册条件
│
├─ 检查Token存在性
│
├─ 调用 POST /auth/register
│  ├─ 成功 → 更新本地用户信息 → 显示成功提示 → 跳转欢迎页
│  └─ 失败 → 显示错误提示
│
└─ 异常处理 → Token失效处理 + 错误提示
```

## 用户交互界面

### 1. 头像设置区域
- **默认状态**：显示默认头像
- **选择方式**：点击头像区域调用微信头像选择组件
- **兼容性**：支持新版本的button.open-type="chooseAvatar"
- **显示效果**：圆形头像展示

### 2. 昵称输入区域
- **输入组件**：支持nickname类型的input组件
- **实时验证**：输入时实时检查并更新注册按钮状态
- **字符限制**：最大长度由后端API限制（通常100字符）
- **必填验证**：昵称不能为空或只包含空格

### 3. 注册按钮
- **动态状态**：根据`canRegister`状态变化
  - 可注册：绿色激活状态
  - 不可注册：灰色禁用状态
- **加载状态**：注册中显示loading效果
- **点击保护**：注册过程中禁止重复点击

### 4. 用户资料获取方式（兼容性支持）
- **新版本**：使用头像选择组件和昵称输入组件
- **旧版本**：提供getUserProfile按钮获取微信资料

## API调用

### 完成注册接口
- **接口**：`POST /auth/register`
- **请求头**：自动携带Token (Authorization: Bearer {token})
- **参数**：
  ```javascript
  {
    wechat_name: String,  // 用户输入的昵称
    avatar_url: String    // 用户选择的头像URL
  }
  ```
- **响应**：更新后的用户信息

## 页面状态流转

### 1. 初始状态
- `canRegister: false` - 注册按钮禁用
- `registering: false` - 未在注册过程中
- 显示默认头像和空昵称

### 2. 信息填写过程
- 用户选择头像或输入昵称时实时更新`canRegister`状态
- 只有当头像不为默认头像且昵称不为空时，`canRegister`才为true

### 3. 注册进行中
- `registering: true` - 按钮显示loading状态
- 禁止用户重复操作

### 4. 注册完成
- 显示"注册成功"提示
- 1.5秒后自动跳转到欢迎页面
- 跳转方式：`wx.redirectTo` (不可返回)

## 错误处理

### 1. 表单验证错误
```javascript
// 昵称为空的处理
if (!nickName || !nickName.trim()) {
  wx.showToast({
    title: '请输入昵称',
    icon: 'none'
  })
  return
}
```

### 2. Token验证错误
```javascript
// Token不存在或失效
if (!token) {
  wx.showToast({
    title: '登录状态已过期，请重新打开小程序',
    icon: 'none'
  })
  return
}
```

### 3. 认证失败处理
- **401/403错误**：Token失效
  - 清除本地Token和用户信息
  - 提示用户重新打开小程序
- **其他错误**：显示具体错误信息

### 4. 网络请求失败
- 显示具体错误信息
- 不自动跳转，允许用户重试

## 本地存储管理

### 更新的数据
- `user_info`: 注册成功后更新为最新的用户信息

### 异常清理
- Token失效时清除 `access_token` 和 `user_info`

## 页面设计特点

1. **简洁直观**：只收集必要的信息（昵称+头像）
2. **实时反馈**：输入时实时检查并更新按钮状态
3. **防误操作**：注册中禁止重复点击
4. **错误友好**：详细的错误提示和处理
5. **跳转流畅**：成功后自动跳转，提升用户体验

## 兼容性考虑

### 微信版本兼容
- **新版本**：使用 `button.open-type="chooseAvatar"` 和 `input.type="nickname"`
- **旧版本**：提供 `getUserProfile` 备选方案
- **检查方式**：通过 `wx.canIUse()` 检查API可用性

### 组件降级方案
```javascript
canIUseGetUserProfile: wx.canIUse('getUserProfile'),
canIUseNicknameComp: wx.canIUse('input.type.nickname')
```

## 业务规则

1. **必填信息**：昵称为必填项，头像可选但建议设置
2. **数据验证**：昵称不能为空或只包含空格
3. **头像处理**：未选择头像时使用默认头像
4. **注册唯一性**：基于已存在的OpenID完成注册，不创建新用户
5. **状态转换**：注册成功后用户状态从"未注册"变为"已注册"