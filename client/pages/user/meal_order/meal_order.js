// 用户下单页面
// 参考文档: doc/client/page_meal_order.md

const request = require('../../../utils/request')

Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 餐次信息
    meal: null,
    date: '',
    slot: '',
    
    // 用户信息
    userInfo: null,
    balance: 0,
    
    // 附加项列表
    addons: [],
    
    // 页面状态
    loading: false,
    submitting: false,
    
    // 用户已有订单
    existingOrder: null,
    
    // 下单表单数据
    orderForm: {
      addon_selections: {}
    },
    
    // 价格计算结果
    priceCalculation: {
      base_price_yuan: 0,
      addon_price_yuan: 0,
      total_price_yuan: 0,
      is_affordable: true
    },
    
    // 页面模式：order（下单）、view（查看订单）、modify（修改订单）
    pageMode: 'order'
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    console.log('[meal_order] onLoad:', options)
    
    // 获取页面参数
    const { date, slot, meal_id } = options
    if (!date || !slot || !meal_id) {
      wx.showToast({
        title: '参数错误',
        icon: 'error'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
      return
    }
    
    this.setData({
      date,
      slot,
      meal_id: meal_id
    })
    
    // 设置页面标题
    const slotText = slot === 'lunch' ? '午餐' : '晚餐'
    wx.setNavigationBarTitle({
      title: `${date} ${slotText}`
    })
    
    // 加载页面数据
    this.loadPageData()
  },

  /**
   * 加载页面数据
   */
  async loadPageData() {
    try {
      this.setData({ loading: true })
      
      // 并行加载数据
      await Promise.all([
        this.loadUserInfo(),
        this.loadMealData(),
        this.loadExistingOrder()
      ])
      
      // 更新页面模式
      this.updatePageMode()
      
      // 初始化表单和计算价格
      this.initializeOrderForm()
      this.calculatePrice()
      
    } catch (error) {
      console.error('[meal_order] loadPageData error:', error)
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      const userInfo = wx.getStorageSync('userInfo')
      if (!userInfo) {
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        })
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
        return
      }
      
      // 获取最新余额
      const response = await request.get('/users/me')
      if (response.success && response.data) {
        this.setData({
          userInfo: response.data,
          balance: response.data.balance_yuan
        })
      }
    } catch (error) {
      console.error('[meal_order] loadUserInfo error:', error)
    }
  },

  /**
   * 加载餐次数据
   */
  async loadMealData() {
    try {
      const { meal_id } = this.data
      const response = await request.get(`/meals/${meal_id}`)
      if (response.success && response.data) {
        const meal = response.data
        
        // 检查餐次状态
        if (meal.status !== 'published') {
          wx.showToast({
            title: '餐次不可下单',
            icon: 'none'
          })
          setTimeout(() => {
            wx.navigateBack()
          }, 1500)
          return
        }
        
        // 加载可用附加项
        await this.loadAvailableAddons(meal.addon_config)
        
        this.setData({ meal })
      }
    } catch (error) {
      console.error('[meal_order] loadMealData error:', error)
    }
  },

  /**
   * 加载可用附加项
   */
  async loadAvailableAddons(addonConfig) {
    try {
      if (!addonConfig || Object.keys(addonConfig).length === 0) {
        this.setData({ addons: [] })
        return
      }
      
      const addonIds = Object.keys(addonConfig).join(',')
      const response = await request.get('/addons', { addon_ids: addonIds })
      if (response.success && response.data && response.data.addons) {
        // 为每个附加项添加配置信息
        const addons = response.data.addons.map(addon => ({
          ...addon,
          max_quantity: addonConfig[addon.addon_id] || 0
        }))
        this.setData({ addons })
      }
    } catch (error) {
      console.error('[meal_order] loadAvailableAddons error:', error)
    }
  },

  /**
   * 加载已有订单
   */
  async loadExistingOrder() {
    try {
      const { meal_id } = this.data
      const response = await request.get(`/orders/my-order/${meal_id}`)
      if (response.success && response.data) {
        this.setData({
          existingOrder: response.data
        })
      }
    } catch (error) {
      // 没有订单是正常情况，不需要报错
      console.log('[meal_order] No existing order found')
    }
  },

  /**
   * 更新页面模式
   */
  updatePageMode() {
    const { existingOrder } = this.data
    let pageMode = 'order'
    
    if (existingOrder) {
      if (['placed', 'confirmed'].includes(existingOrder.status)) {
        pageMode = 'view'
      }
    }
    
    this.setData({ pageMode })
  },

  /**
   * 初始化下单表单
   */
  initializeOrderForm() {
    const { existingOrder, addons } = this.data
    let addon_selections = {}
    
    if (existingOrder && existingOrder.addon_selections) {
      // 如果有已有订单，预填充附加项选择
      addon_selections = { ...existingOrder.addon_selections }
    } else {
      // 初始化所有附加项为0
      addons.forEach(addon => {
        addon_selections[addon.addon_id] = 0
      })
    }
    
    this.setData({
      'orderForm.addon_selections': addon_selections
    })
  },

  /**
   * 附加项数量变更
   */
  onAddonQuantityChange(e) {
    const addonId = e.currentTarget.dataset.addonId
    const type = e.currentTarget.dataset.type
    const { addon_selections } = this.data.orderForm
    const { addons } = this.data
    
    const addon = addons.find(a => a.addon_id == addonId)
    if (!addon) return
    
    let quantity = addon_selections[addonId] || 0
    
    if (type === 'increase') {
      quantity = Math.min(quantity + 1, addon.max_quantity)
    } else if (type === 'decrease') {
      quantity = Math.max(quantity - 1, 0)
    }
    
    addon_selections[addonId] = quantity
    
    this.setData({
      'orderForm.addon_selections': addon_selections
    })
    
    this.calculatePrice()
  },

  /**
   * 计算价格
   */
  calculatePrice() {
    const { meal, addons, orderForm, balance } = this.data
    if (!meal) return
    
    let base_price_yuan = meal.base_price_yuan
    let addon_price_yuan = 0
    
    // 计算附加项价格
    addons.forEach(addon => {
      const quantity = orderForm.addon_selections[addon.addon_id] || 0
      if (quantity > 0) {
        addon_price_yuan += addon.price_yuan * quantity
      }
    })
    
    const total_price_yuan = base_price_yuan + addon_price_yuan
    const is_affordable = balance >= total_price_yuan
    
    this.setData({
      priceCalculation: {
        base_price_yuan,
        addon_price_yuan,
        total_price_yuan,
        is_affordable
      }
    })
  },

  /**
   * 下单
   */
  async onPlaceOrder() {
    if (!this.validateOrder()) {
      return
    }
    
    try {
      this.setData({ submitting: true })
      
      const { meal_id, orderForm } = this.data
      const requestData = {
        meal_id: parseInt(meal_id),
        addon_selections: orderForm.addon_selections
      }
      
      const response = await request.post('/orders', requestData)
      
      if (response.success) {
        wx.showToast({
          title: '下单成功',
          icon: 'success'
        })
        
        // 重新加载页面数据
        setTimeout(() => {
          this.loadPageData()
        }, 1500)
      }
      
    } catch (error) {
      console.error('[meal_order] placeOrder error:', error)
      wx.showToast({
        title: error.message || '下单失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /**
   * 修改订单
   */
  async onModifyOrder() {
    if (!this.validateOrder()) {
      return
    }
    
    try {
      this.setData({ submitting: true })
      
      const { existingOrder, orderForm } = this.data
      const requestData = {
        addon_selections: orderForm.addon_selections
      }
      
      const response = await request.put(`/orders/${existingOrder.order_id}`, requestData)
      
      if (response.success) {
        wx.showToast({
          title: '修改成功',
          icon: 'success'
        })
        
        // 重新加载页面数据
        setTimeout(() => {
          this.loadPageData()
        }, 1500)
      }
      
    } catch (error) {
      console.error('[meal_order] modifyOrder error:', error)
      wx.showToast({
        title: error.message || '修改失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /**
   * 取消订单
   */
  async onCancelOrder() {
    try {
      const confirmResult = await this.showConfirm('确认取消订单？取消后将自动退款到账户余额')
      if (!confirmResult) {
        return
      }
      
      this.setData({ submitting: true })
      
      const { existingOrder } = this.data
      const response = await request.delete(`/orders/${existingOrder.order_id}`)
      
      if (response.success) {
        wx.showToast({
          title: '取消成功',
          icon: 'success'
        })
        
        // 重新加载页面数据
        setTimeout(() => {
          this.loadPageData()
        }, 1500)
      }
      
    } catch (error) {
      console.error('[meal_order] cancelOrder error:', error)
      wx.showToast({
        title: error.message || '取消失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /**
   * 开始修改订单
   */
  onStartModifyOrder() {
    this.setData({ pageMode: 'modify' })
    this.initializeOrderForm()
  },

  /**
   * 取消修改
   */
  onCancelModify() {
    this.setData({ pageMode: 'view' })
    this.initializeOrderForm()
    this.calculatePrice()
  },

  /**
   * 验证订单
   */
  validateOrder() {
    const { priceCalculation } = this.data
    
    if (!priceCalculation.is_affordable) {
      wx.showToast({
        title: '余额不足，请先充值',
        icon: 'none'
      })
      return false
    }
    
    return true
  },

  /**
   * 显示确认对话框
   */
  showConfirm(content) {
    return new Promise((resolve) => {
      wx.showModal({
        title: '确认操作',
        content,
        success: (res) => {
          resolve(res.confirm)
        },
        fail: () => {
          resolve(false)
        }
      })
    })
  },

  /**
   * 查看订单详情
   */
  onViewOrderDetails() {
    const { existingOrder } = this.data
    if (!existingOrder) return
    
    wx.navigateTo({
      url: `/pages/common/order_list/order_list?order_id=${existingOrder.order_id}`
    })
  },

  /**
   * 前往充值页面
   */
  onGoToRecharge() {
    wx.navigateTo({
      url: '/pages/user/billing_history/billing_history?show_recharge=true'
    })
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    this.loadPageData().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  /**
   * 页面分享
   */
  onShareAppMessage() {
    const { date, slot, meal } = this.data
    const slotText = slot === 'lunch' ? '午餐' : '晚餐'
    
    return {
      title: `${date} ${slotText} - ${meal?.description || '罡好饭'}`,
      path: `/pages/user/meal_order/meal_order?date=${date}&slot=${slot}&meal_id=${meal?.meal_id}`
    }
  }
})