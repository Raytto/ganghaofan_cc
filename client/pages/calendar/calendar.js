const request = require('../../utils/request.js')

Page({
  data: {
    currentDate: '',
    weeks: [],
    today: null
  },

  onLoad() {
    this.initCalendar()
    this.loadMealData()
  },

  onShow() {
    // 检查登录状态
    const token = wx.getStorageSync('access_token')
    if (!token) {
      wx.reLaunch({ url: '../welcome/welcome' })
      return
    }
    
    // 刷新餐次数据
    this.loadMealData()
  },

  /**
   * 初始化日历结构
   */
  initCalendar() {
    const today = new Date()
    this.setData({ today })
    
    // 设置当前日期显示
    const year = today.getFullYear()
    const month = today.getMonth() + 1
    const date = today.getDate()
    const currentDate = `${year}年${month}月${date}日`
    this.setData({ currentDate })

    // 生成三周日历结构
    const weeks = this.generateThreeWeeks(today)
    this.setData({ weeks })
  },

  /**
   * 生成三周日历结构
   */
  generateThreeWeeks(today) {
    const weeks = []
    
    // 计算本周的周日
    const currentWeekStart = new Date(today)
    const dayOfWeek = currentWeekStart.getDay()
    currentWeekStart.setDate(currentWeekStart.getDate() - dayOfWeek)

    // 生成三周：上周(-1)、本周(0)、下周(1)
    for (let weekIndex = -1; weekIndex <= 1; weekIndex++) {
      const weekStart = new Date(currentWeekStart)
      weekStart.setDate(weekStart.getDate() + (weekIndex * 7))
      
      const week = {
        weekIndex,
        days: []
      }

      // 生成一周7天
      for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
        const dayDate = new Date(weekStart)
        dayDate.setDate(dayDate.getDate() + dayIndex)
        
        const isToday = this.isSameDay(dayDate, today)
        
        week.days.push({
          dayIndex,
          date: dayDate.getDate(),
          fullDate: dayDate,
          isToday,
          lunch: {
            meal_status: 'unpublished',
            max_orders: 0,
            left_orders: 0,
            myorder_status: 'unordered'
          },
          dinner: {
            meal_status: 'unpublished', 
            max_orders: 0,
            left_orders: 0,
            myorder_status: 'unordered'
          }
        })
      }
      
      weeks.push(week)
    }

    return weeks
  },

  /**
   * 判断是否为同一天
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
      // 计算日期范围
      const { startDate, endDate } = this.getDateRange()
      
      // 调用API获取餐次数据
      const response = await request.get('/meals', {
        start_date: startDate,
        end_date: endDate
      })

      if (response.success) {
        this.syncMealData(response.data.meals)
      } else {
        console.error('获取餐次数据失败:', response.error)
        wx.showToast({
          title: '加载餐次数据失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('加载餐次数据异常:', error)
      if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
        // 登录失效，跳转到欢迎页
        wx.reLaunch({ url: '../welcome/welcome' })
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
    if (weeks.length === 0) return { startDate: '', endDate: '' }

    const firstDay = weeks[0].days[0].fullDate
    const lastDay = weeks[weeks.length - 1].days[6].fullDate

    const startDate = this.formatDate(firstDay)
    const endDate = this.formatDate(lastDay)

    return { startDate, endDate }
  },

  /**
   * 格式化日期为 YYYY-MM-DD
   */
  formatDate(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  },

  /**
   * 同步餐次数据到日历结构
   */
  syncMealData(meals) {
    // 直接使用原始数据，不进行深拷贝以保持Date对象
    const weeks = this.data.weeks
    
    // 创建日期到餐次的映射
    const mealMap = {}
    meals.forEach(meal => {
      const dateKey = meal.date
      if (!mealMap[dateKey]) {
        mealMap[dateKey] = {}
      }
      mealMap[dateKey][meal.slot] = {
        meal_status: meal.status,
        max_orders: meal.max_orders,
        left_orders: meal.available_slots,
        myorder_status: meal.user_ordered ? 'ordered' : 'unordered'
      }
    })

    // 更新日历结构中的餐次数据
    weeks.forEach(week => {
      week.days.forEach(day => {
        const dateKey = this.formatDate(day.fullDate)
        if (mealMap[dateKey]) {
          if (mealMap[dateKey].lunch) {
            day.lunch = mealMap[dateKey].lunch
          }
          if (mealMap[dateKey].dinner) {
            day.dinner = mealMap[dateKey].dinner
          }
        }
      })
    })

    this.setData({ weeks })
  },

  /**
   * 日期点击事件（预留扩展）
   */
  onDayTap(e) {
    const date = e.currentTarget.dataset.date
    console.log('点击日期:', date)
    // 可扩展：跳转到具体日期的订餐页面
  }
})