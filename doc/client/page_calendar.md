# 健康日历页面 (calendar.js)

## 页面概述

健康日历页面是用户查看餐次信息的核心页面，以三周日历视图的形式展示餐次的预订状态、价格和时间安排。用户可以直观地查看上周、本周、下周的所有餐次信息。

## 页面路径
- 文件位置：`client/pages/calendar/calendar.js`
- 页面路径：`pages/calendar/calendar`
- Tab页面：是（底部导航栏第一个）

## 页面功能

### 主要职责
1. **日历展示**：以三周视图显示日期和餐次信息
2. **餐次状态**：显示每日午餐和晚餐的预订状态和价格
3. **实时更新**：页面显示时自动刷新最新数据
4. **状态区分**：通过颜色和文字区分不同的餐次状态

### 核心功能模块

#### 1. 日历结构生成
- **三周范围**：上周、本周、下周（共21天）
- **周结构**：每周从周日开始到周六结束
- **今日标识**：高亮显示当前日期

#### 2. 餐次信息展示
- **午餐信息**：价格、预订状态
- **晚餐信息**：价格、预订状态
- **状态类型**：可预订、已预订、已截止、未发布

#### 3. 数据加载机制
- **登录检查**：验证用户登录状态
- **API调用**：获取指定日期范围的餐次数据
- **数据同步**：将后端数据映射到前端日历结构

## 页面数据结构

### data 字段
```javascript
{
  currentDate: String,     // 当前月份显示文本 (如: "2024年8月23日")
  weeks: Array,            // 三周的数据结构
  today: Date              // 今天的日期对象
}
```

### weeks 数组结构
```javascript
[
  {
    weekIndex: Number,       // 周索引 (-1=上周, 0=本周, 1=下周)
    days: [
      {
        dayIndex: Number,       // 日索引 (0-6, 0=周日)
        date: Number,           // 日期数字 (1-31)
        fullDate: Date,         // 完整日期对象
        isToday: Boolean,       // 是否为今天
        lunch: {                // 午餐信息
          meal_status: String,  // 餐的状态: published/locked/unpublished/completed
          max_orders: Number,   // 最大可订数量
          left_orders: Number,   // 剩余可订数量
          myorder_status: String,// 我对此餐的状态: unordered/orderd
        },
        dinner: {               // 晚餐信息
          meal_status: String,  // 餐的状态: published/locked/unpublished/completed
          max_orders: Number,   // 最大可订数量
          left_orders: Number,   // 剩余可订数量
          myorder_status: String,// 我对此餐的状态: unordered/orderd
        }
      }
      // ... 7天
    ]
  }
  // ... 3周
]
```

## 餐次状态系统

### 每餐状态
每餐显示三行文字来对应状态：
1. 第一行，餐的状态 published/locked/unpublished/completed
2. 第二行，剩余可订数量 current_orders/max_orders
2. 第三行，我我对此餐的状态: unordered/orderd

### 状态映射逻辑
```javascript
// 后端数据 -> 前端状态
待补充
```

## API 调用
参考文档 doc/api.md

### 获取日历餐次数据
- **接口**：`GET /meals/calendar`
- **参数**：
  ```javascript
  {
    start_date: "YYYY-MM-DD",  // 开始日期
    end_date: "YYYY-MM-DD"     // 结束日期
  }
  ```
- **返回**：餐次列表包含状态和价格信息

## 页面布局结构

### 1. 日历头部
- **今天日子**：当前年月日

### 2. 三周日历网格
- **7列布局**：对应一周七天
- **1行星期**：对应周日到周六的列标题
- **3行布局**：对应三周
- **日期格子**：包含日期数字和两个餐次信息


## 交互功能

### 1. 页面加载 (onLoad)
```
页面加载 → 初始化日历结构 → 加载餐次数据 → 渲染页面
```

### 2. 页面显示 (onShow)
```
页面显示 → 刷新餐次数据 → 更新页面状态
```

### 3. 餐次点击 (onDayTap) [预留]
- **功能**：点击日期格子跳转到餐次详情页
- **扩展**：可跳转到具体日期的订餐页面

## 错误处理

### 1. 登录状态检查
```javascript
const token = wx.getStorageSync('access_token')
if (!token) {
  wx.reLaunch({ url: '../welcome/welcome' })
  return
}
```
