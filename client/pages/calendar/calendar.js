// calendar.js
const request = require('../../utils/request.js')

Page({
  data: {
    currentMonth: '',
    weeks: [],
    today: null
  },

  onLoad() {
    this.initializeCalendar()
    this.loadMealData()
  },

  onShow() {
    // 页面显示时刷新数据
    this.loadMealData()
  },

  /**
   * 初始化日历结构
   */
  initializeCalendar() {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    
    // 设置当前月份显示
    const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', 
                       '7月', '8月', '9月', '10月', '11月', '12月']
    this.setData({
      currentMonth: `${now.getFullYear()}年${monthNames[now.getMonth()]}`,
      today: today
    })

    // 生成三周的日期结构
    const weeks = this.generateThreeWeeks(today)
    this.setData({ weeks })
  },

  /**
   * 生成三周的日期结构（上周、本周、下周）
   */
  generateThreeWeeks(today) {
    const weeks = []
    
    // 获取本周的开始日期（周日）
    const currentWeekStart = new Date(today)
    const dayOfWeek = today.getDay() // 0=周日, 1=周一...
    currentWeekStart.setDate(today.getDate() - dayOfWeek)
    
    // 生成三周数据：上周、本周、下周
    for (let weekOffset = -1; weekOffset <= 1; weekOffset++) {
      const weekStart = new Date(currentWeekStart)
      weekStart.setDate(currentWeekStart.getDate() + (weekOffset * 7))
      
      const week = {
        weekIndex: weekOffset + 1,
        days: []
      }
      
      // 生成一周的7天
      for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
        const date = new Date(weekStart)
        date.setDate(weekStart.getDate() + dayOffset)
        
        const dayData = {
          dayIndex: dayOffset,
          date: date.getDate(),
          fullDate: date,
          isToday: this.isSameDay(date, today),
          isCurrentMonth: date.getMonth() === today.getMonth(),
          // 初始化餐次数据
          lunch: {
            status: 'unpublished', // available, ordered, locked, unpublished
            price: 0
          },
          dinner: {
            status: 'unpublished',
            price: 0
          }
        }
        
        week.days.push(dayData)
      }
      
      weeks.push(week)
    }
    
    return weeks
  },

  /**
   * 判断两个日期是否是同一天
   */
  isSameDay(date1, date2) {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate()
  },

  /**
   * 加载餐次数据
   */
  async loadMealData() {
    try {
      // 检查登录状态
      const token = wx.getStorageSync('access_token')
      if (!token) {
        console.log('未登录，跳转到欢迎页面')
        wx.reLaunch({
          url: '../welcome/welcome'
        })
        return
      }

      // 计算日期范围
      const dateRange = this.getDateRange()
      
      // 调用API获取餐次数据
      const response = await request.get('/meals', {
        start_date: dateRange.startDate,
        end_date: dateRange.endDate
      })

      if (response.success) {
        this.updateMealData(response.data.meals)
      } else {
        console.error('获取餐次数据失败:', response.error)
        wx.showToast({
          title: '获取数据失败',
          icon: 'none'
        })
      }
      
    } catch (error) {
      console.error('加载餐次数据失败:', error)
      
      // 如果是认证错误，跳转到欢迎页面重新登录
      if (error.message && (error.message.includes('HTTP 401') || error.message.includes('HTTP 403'))) {
        wx.removeStorageSync('access_token')
        wx.removeStorageSync('user_info')
        wx.reLaunch({
          url: '../welcome/welcome'
        })
      } else {
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        })
      }
    }
  },

  /**
   * 获取三周的日期范围
   */
  getDateRange() {
    const weeks = this.data.weeks
    if (weeks.length === 0) return { startDate: null, endDate: null }
    
    const firstDay = weeks[0].days[0].fullDate
    const lastDay = weeks[weeks.length - 1].days[6].fullDate
    
    return {
      startDate: this.formatDate(firstDay),
      endDate: this.formatDate(lastDay)
    }
  },

  /**
   * 格式化日期为 YYYY-MM-DD 格式
   */
  formatDate(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  },

  /**
   * 更新餐次数据到日历中
   */
  updateMealData(mealsData) {
    const weeks = this.data.weeks.map(week => {
      const updatedDays = week.days.map(day => {
        const dateStr = this.formatDate(day.fullDate)
        const dayMeals = mealsData.filter(meal => meal.date === dateStr)
        
        // 更新午餐数据
        const lunch = dayMeals.find(meal => meal.slot === 'lunch')
        if (lunch) {
          day.lunch = this.getMealStatus(lunch)
        }
        
        // 更新晚餐数据
        const dinner = dayMeals.find(meal => meal.slot === 'dinner')
        if (dinner) {
          day.dinner = this.getMealStatus(dinner)
        }
        
        return day
      })
      
      return { ...week, days: updatedDays }
    })
    
    this.setData({ weeks })
  },

  /**
   * 根据餐次信息确定状态
   */
  getMealStatus(meal) {
    // 根据后端返回的餐次状态确定前端显示状态
    // TODO: 需要后端提供用户订单状态信息
    // 暂时根据餐次状态判断
    if (meal.status === 'locked' || meal.status === 'completed') {
      return { status: 'locked', price: meal.base_price_yuan }
    } else if (meal.status === 'published') {
      return { status: 'available', price: meal.base_price_yuan }
    } else {
      return { status: 'unpublished', price: 0 }
    }
  },

  /**
   * 点击日期格子的处理
   */
  onDayTap(e) {
    const { weekIndex, dayIndex } = e.currentTarget.dataset
    const day = this.data.weeks[weekIndex].days[dayIndex]
    
    if (!day.isCurrentMonth) {
      return // 不是当前月份的日期不响应点击
    }
    
    // TODO: 跳转到具体日期的餐次详情页面
    console.log('点击日期:', this.formatDate(day.fullDate))
  }
})