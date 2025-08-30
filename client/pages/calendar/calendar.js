const request = require('../../utils/request.js')
const adminUtils = require('../../utils/admin.js')

Page({
  data: {
    currentDate: '',
    weeks: [],
    today: null
  },

  onLoad() {
    console.log('【新版本】Calendar页面 onLoad 开始')
    this.initCalendar()
    this.loadMealData()
    console.log('【新版本】Calendar页面 onLoad 结束')
  },

  onShow() {
    console.log('=== Calendar页面 onShow 开始 ===')
    // 检查登录状态
    const token = wx.getStorageSync('access_token')
    if (!token) {
      console.log('未找到token，跳转到欢迎页面')
      wx.reLaunch({ url: '../welcome/welcome' })
      return
    }
    
    // 刷新餐次数据
    this.loadMealData()
    console.log('=== Calendar页面 onShow 结束 ===')
  },

  /**
   * 初始化日历结构
   */
  initCalendar() {
    console.log('【新版本】initCalendar 开始')
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
    console.log('【新版本】生成的weeks数据长度:', weeks.length)
    if (weeks.length > 0 && weeks[0].days.length > 0) {
      console.log('【新版本】第一天dateString:', weeks[0].days[0].dateString)
    }
    this.setData({ weeks })
    console.log('【新版本】initCalendar 完成')
  },

  /**
   * 生成三周日历结构
   */
  generateThreeWeeks(today) {
    console.log('=== generateThreeWeeks 开始 ===')
    console.log('输入的today参数:', today)
    const weeks = []
    
    // 计算本周的周日
    const currentWeekStart = new Date(today)
    const dayOfWeek = currentWeekStart.getDay()
    console.log('今天是周几:', dayOfWeek)
    currentWeekStart.setDate(currentWeekStart.getDate() - dayOfWeek)
    console.log('本周周日日期:', currentWeekStart)

    // 生成三周：上周(-1)、本周(0)、下周(1)
    for (let weekIndex = -1; weekIndex <= 1; weekIndex++) {
      console.log(`--- 生成第${weekIndex}周 ---`)
      const weekStart = new Date(currentWeekStart)
      weekStart.setDate(weekStart.getDate() + (weekIndex * 7))
      console.log(`第${weekIndex}周开始日期:`, weekStart)
      
      const week = {
        weekIndex,
        days: []
      }

      // 生成一周7天
      for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
        const dayDate = new Date(weekStart)
        dayDate.setDate(dayDate.getDate() + dayIndex)
        
        const isToday = this.isSameDay(dayDate, today)
        
        // 手动格式化日期字符串
        const year = dayDate.getFullYear()
        const month = String(dayDate.getMonth() + 1).padStart(2, '0')
        const day = String(dayDate.getDate()).padStart(2, '0')
        const dateString = `${year}-${month}-${day}`
        
        console.log(`生成日期 ${dayIndex}: ${dateString}, isToday: ${isToday}`)

        const dayData = {
          dayIndex,
          date: dayDate.getDate(),
          fullDate: dayDate,
          dateString: dateString,
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
        }
        
        week.days.push(dayData)
        console.log(`第${weekIndex}周第${dayIndex}天数据:`, dayData)
      }
      
      weeks.push(week)
      console.log(`第${weekIndex}周完成，days数量:`, week.days.length)
    }

    console.log('=== generateThreeWeeks 完成 ===')
    console.log('最终weeks数组:', weeks)
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
    console.log('【新版】onDayTap被触发，数据:', e.currentTarget.dataset)
    // 可扩展：跳转到具体日期的订餐页面
  },

  /**
   * 餐次点击事件
   */
  onMealTap(e) {
    console.log('【新版】onMealTap被触发！数据:', e.currentTarget.dataset)
    const { date, slot, status } = e.currentTarget.dataset
    console.log('解构出的数据 - date:', date, 'slot:', slot, 'status:', status)
    
    // date 现在已经是格式化的字符串了，直接使用
    
    // 检查是否为管理员模式
    const isAdminMode = adminUtils.isAdminModeEnabled()
    console.log('管理员模式状态:', isAdminMode)
    if (isAdminMode) {
      // 管理员模式下，未发布的餐次跳转到发布页面
      if (status === 'unpublished') {
        console.log('跳转到发布页面，URL:', `/pages/admin/meal_publish/meal_publish?date=${date}&slot=${slot}`)
        wx.navigateTo({
          url: `/pages/admin/meal_publish/meal_publish?date=${date}&slot=${slot}`
        })
      } else if (status === 'published' || status === 'locked' || status === 'completed') {
        console.log('跳转到餐次管理页面，需要先获取meal_id')
        // 已发布的餐次跳转到查看/编辑页面
        // 需要先获取meal_id
        this.getMealIdAndNavigate(date, slot)
      } else {
        console.log('管理员模式下，餐次状态不支持操作:', status)
      }
    } else {
      console.log('普通用户模式')
      // 普通用户模式
      if (status === 'published') {
        console.log('跳转到订餐页面，URL:', `/pages/order/order?date=${date}&slot=${slot}`)
        // 跳转到订餐页面
        wx.navigateTo({
          url: `/pages/order/order?date=${date}&slot=${slot}`
        })
      } else {
        console.log('普通用户模式下，餐次状态不可订餐:', status)
      }
    }
  },

  /**
   * 获取餐次ID并跳转
   */
  async getMealIdAndNavigate(date, slot) {
    try {
      const response = await request.get('/meals', {
        date: date,
        slot: slot
      })
      
      if (response.success && response.data.meals && response.data.meals.length > 0) {
        const meal = response.data.meals[0]
        wx.navigateTo({
          url: `/pages/admin/meal_publish/meal_publish?date=${date}&slot=${slot}&meal_id=${meal.meal_id}`
        })
      }
    } catch (error) {
      console.error('获取餐次ID失败:', error)
      wx.showToast({
        title: '获取餐次信息失败',
        icon: 'none'
      })
    }
  }
})