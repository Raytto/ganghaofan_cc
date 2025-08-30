// 管理员发布餐页面
// 参考文档: doc/client/page_meal_publish.md

const request = require('../../../utils/request')
const adminUtils = require('../../../utils/admin')

Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 餐次信息
    meal: null,
    date: '',
    slot: '',
    
    // 附加项列表
    addons: [],
    
    // 页面状态
    loading: false,
    editing: false,
    submitting: false,
    
    // 餐次表单数据
    mealForm: {
      description: '',
      base_price_yuan: 18,
      max_orders: 50,
      addon_config: {}
    },
    
    // 订单统计
    orderStats: {
      total_orders: 0,
      total_amount: 0,
      active_orders: 0
    },
    
    // 快捷价格选项
    quickPrices: [15, 18, 20, 25],
    
    // 页面模式：publish（发布）、view（查看）、edit（编辑）
    pageMode: 'publish'
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    console.log('[meal_publish] onLoad:', options)
    
    // 检查管理员权限
    if (!this.checkAdminPermission()) {
      wx.showToast({
        title: '权限不足',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
      return
    }
    
    // 获取页面参数
    const { date, slot, meal_id } = options
    if (!date || !slot) {
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
      slot
    })
    
    // 设置页面标题
    const slotText = slot === 'lunch' ? '午餐' : '晚餐'
    wx.setNavigationBarTitle({
      title: `${date} ${slotText}`
    })
    
    // 加载页面数据
    this.loadPageData(meal_id)
  },

  /**
   * 检查管理员权限
   */
  checkAdminPermission() {
    return adminUtils.isAdminModeEnabled()
  },

  /**
   * 加载页面数据
   */
  async loadPageData(meal_id) {
    try {
      this.setData({ loading: true })
      
      // 并行加载数据
      const promises = [
        this.loadAddonsList(),
      ]
      
      if (meal_id) {
        promises.push(this.loadMealData(meal_id))
        promises.push(this.loadMealStatistics(meal_id))
      }
      
      await Promise.all(promises)
      
      // 设置页面模式
      this.updatePageMode()
      
    } catch (error) {
      console.error('[meal_publish] loadPageData error:', error)
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 加载附加项列表
   */
  async loadAddonsList() {
    try {
      const response = await request.get('/admin/addons', { status: 'active' })
      if (response.success && response.data && response.data.addons) {
        this.setData({
          addons: response.data.addons
        })
      }
    } catch (error) {
      console.error('[meal_publish] loadAddonsList error:', error)
    }
  },

  /**
   * 加载餐次数据
   */
  async loadMealData(meal_id) {
    try {
      const response = await request.get(`/meals/${meal_id}`)
      if (response.success && response.data) {
        const meal = response.data
        
        // 预填充表单数据
        const mealForm = {
          description: meal.description || '',
          base_price_yuan: meal.base_price_yuan || 18,
          max_orders: meal.max_orders || 50,
          addon_config: meal.addon_config || {}
        }
        
        this.setData({
          meal,
          mealForm
        })
      }
    } catch (error) {
      console.error('[meal_publish] loadMealData error:', error)
    }
  },

  /**
   * 加载餐次统计
   */
  async loadMealStatistics(meal_id) {
    try {
      const response = await request.get(`/admin/meals/${meal_id}/statistics`)
      if (response.success && response.data) {
        this.setData({
          orderStats: response.data.order_statistics || {}
        })
      }
    } catch (error) {
      console.error('[meal_publish] loadMealStatistics error:', error)
    }
  },

  /**
   * 更新页面模式
   */
  updatePageMode() {
    const { meal } = this.data
    let pageMode = 'publish'
    
    if (meal) {
      if (meal.status === 'published') {
        pageMode = 'view'
      } else if (['locked', 'completed', 'canceled'].includes(meal.status)) {
        pageMode = 'readonly'
      }
    }
    
    this.setData({ pageMode })
  },

  /**
   * 表单输入处理
   */
  onDescriptionInput(e) {
    this.setData({
      'mealForm.description': e.detail.value
    })
  },

  onPriceInput(e) {
    const value = parseFloat(e.detail.value) || 0
    this.setData({
      'mealForm.base_price_yuan': value
    })
    this.calculatePriceRange()
  },

  onMaxOrdersInput(e) {
    const value = parseInt(e.detail.value) || 50
    this.setData({
      'mealForm.max_orders': value
    })
  },

  /**
   * 快捷价格选择
   */
  onQuickPriceSelect(e) {
    const price = e.currentTarget.dataset.price
    this.setData({
      'mealForm.base_price_yuan': price
    })
    this.calculatePriceRange()
  },

  /**
   * 附加项配置变更
   */
  onAddonToggle(e) {
    const addonId = e.currentTarget.dataset.addonId
    const { addon_config } = this.data.mealForm
    
    if (addon_config[addonId]) {
      // 取消选择
      delete addon_config[addonId]
    } else {
      // 选择，默认最大数量为1
      addon_config[addonId] = 1
    }
    
    this.setData({
      'mealForm.addon_config': addon_config
    })
    this.calculatePriceRange()
  },

  onAddonQuantityChange(e) {
    const addonId = e.currentTarget.dataset.addonId
    const type = e.currentTarget.dataset.type
    const { addon_config } = this.data.mealForm
    
    let quantity = addon_config[addonId] || 0
    
    if (type === 'increase') {
      quantity = Math.min(quantity + 1, 10) // 最大10个
    } else if (type === 'decrease') {
      quantity = Math.max(quantity - 1, 0)
    }
    
    if (quantity === 0) {
      delete addon_config[addonId]
    } else {
      addon_config[addonId] = quantity
    }
    
    this.setData({
      'mealForm.addon_config': addon_config
    })
    this.calculatePriceRange()
  },

  /**
   * 计算价格范围
   */
  calculatePriceRange() {
    const { base_price_yuan, addon_config } = this.data.mealForm
    const { addons } = this.data
    
    let minPrice = base_price_yuan
    let maxPrice = base_price_yuan
    
    // 计算附加项价格范围
    addons.forEach(addon => {
      const maxQuantity = addon_config[addon.addon_id]
      if (maxQuantity && maxQuantity > 0) {
        const addonPrice = addon.price_yuan * maxQuantity
        if (addonPrice > 0) {
          maxPrice += addonPrice
        } else {
          minPrice += addonPrice // 负价格附加项
        }
      }
    })
    
    this.setData({
      priceRange: {
        min: Math.max(minPrice, 0),
        max: maxPrice
      }
    })
  },

  /**
   * 表单验证
   */
  validateForm() {
    const { description, base_price_yuan, max_orders } = this.data.mealForm
    
    if (!description || description.trim() === '') {
      wx.showToast({
        title: '请输入餐次描述',
        icon: 'none'
      })
      return false
    }
    
    if (!base_price_yuan || base_price_yuan <= 0) {
      wx.showToast({
        title: '请输入有效价格',
        icon: 'none'
      })
      return false
    }
    
    if (!max_orders || max_orders <= 0) {
      wx.showToast({
        title: '请输入有效订餐上限',
        icon: 'none'
      })
      return false
    }
    
    return true
  },

  /**
   * 发布餐次
   */
  async onPublishMeal() {
    if (!this.validateForm()) {
      return
    }
    
    try {
      this.setData({ submitting: true })
      
      const { date, slot, mealForm } = this.data
      const requestData = {
        date,
        slot,
        description: mealForm.description.trim(),
        base_price_cents: Math.round(mealForm.base_price_yuan * 100),
        addon_config: mealForm.addon_config,
        max_orders: mealForm.max_orders
      }
      
      const response = await request.post('/admin/meals', requestData)
      
      if (response.success) {
        wx.showToast({
          title: '发布成功',
          icon: 'success'
        })
        
        // 发布成功后返回日历页面，触发数据刷新
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      }
      
    } catch (error) {
      console.error('[meal_publish] publishMeal error:', error)
      wx.showToast({
        title: error.message || '发布失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /**
   * 编辑餐次
   */
  onEditMeal() {
    this.setData({ editing: true })
  },

  /**
   * 保存餐次修改
   */
  async onSaveMeal() {
    if (!this.validateForm()) {
      return
    }
    
    try {
      this.setData({ submitting: true })
      
      const { meal, mealForm } = this.data
      const requestData = {
        description: mealForm.description.trim(),
        base_price_cents: Math.round(mealForm.base_price_yuan * 100),
        addon_config: mealForm.addon_config,
        max_orders: mealForm.max_orders
      }
      
      const response = await request.put(`/admin/meals/${meal.meal_id}`, requestData)
      
      if (response.success) {
        wx.showToast({
          title: '保存成功',
          icon: 'success'
        })
        
        this.setData({ editing: false })
        
        // 刷新页面数据
        setTimeout(() => {
          this.loadPageData(meal.meal_id)
        }, 1500)
      }
      
    } catch (error) {
      console.error('[meal_publish] saveMeal error:', error)
      wx.showToast({
        title: error.message || '保存失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /**
   * 取消编辑
   */
  onCancelEdit() {
    // 恢复原始数据
    this.loadMealData(this.data.meal.meal_id)
    this.setData({ editing: false })
  },

  /**
   * 餐次状态操作
   */
  async onMealStatusAction(e) {
    const action = e.currentTarget.dataset.action
    const { meal } = this.data
    
    if (!meal || !meal.meal_id) {
      return
    }
    
    // 确认操作
    const confirmMessages = {
      lock: '确认锁定餐次？锁定后用户无法下单或修改订单',
      unlock: '确认取消锁定？取消后用户可以继续下单',
      complete: '确认完成餐次？完成后无法再修改',
      cancel: '确认取消餐次？将自动退款所有订单'
    }
    
    const confirmMessage = confirmMessages[action]
    if (!confirmMessage) {
      return
    }
    
    try {
      const confirmResult = await this.showConfirm(confirmMessage)
      if (!confirmResult) {
        return
      }
      
      this.setData({ submitting: true })
      
      let url = ''
      let method = 'PUT'
      let data = {}
      
      switch (action) {
        case 'lock':
          url = `/admin/meals/${meal.meal_id}/lock`
          break
        case 'unlock':
          url = `/admin/meals/${meal.meal_id}/unlock`
          break
        case 'complete':
          url = `/admin/meals/${meal.meal_id}/complete`
          break
        case 'cancel':
          url = `/admin/meals/${meal.meal_id}`
          method = 'DELETE'
          data = { cancel_reason: '管理员取消' }
          break
      }
      
      const response = await request[method.toLowerCase()](url, data)
      
      if (response.success) {
        wx.showToast({
          title: '操作成功',
          icon: 'success'
        })
        
        // 刷新页面数据
        setTimeout(() => {
          this.loadPageData(meal.meal_id)
        }, 1500)
      }
      
    } catch (error) {
      console.error(`[meal_publish] ${action} error:`, error)
      wx.showToast({
        title: error.message || '操作失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /**
   * 查看下单详情
   */
  onViewOrderDetails() {
    const { meal } = this.data
    if (!meal) return
    
    wx.navigateTo({
      url: `/pages/common/order_list/order_list?meal_id=${meal.meal_id}`
    })
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
   * 页面分享
   */
  onShareAppMessage() {
    const { date, slot } = this.data
    const slotText = slot === 'lunch' ? '午餐' : '晚餐'
    
    return {
      title: `${date} ${slotText} - 罡好饭`,
      path: `/pages/admin/meal_publish/meal_publish?date=${date}&slot=${slot}`
    }
  }
})