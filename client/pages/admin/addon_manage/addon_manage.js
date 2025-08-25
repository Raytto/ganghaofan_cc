const request = require('../../../utils/request.js')
const adminUtils = require('../../../utils/admin.js')

Page({
  data: {
    activeAddons: [],        // 生效中的附加项列表
    loading: true,           // 页面加载状态
    newAddon: {             // 新增附加项表单
      name: '',
      price_yuan: 0
    },
    submitting: false       // 提交状态
  },

  onLoad() {
    // 检查管理员权限
    if (!this.checkAdminPermission()) {
      wx.showToast({
        title: '权限不足',
        icon: 'none',
        duration: 2000
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 2000)
      return
    }

    // 加载附加项列表
    this.loadAddonList()
  },

  onShow() {
    // 页面显示时刷新数据（从其他页面返回时）
    if (!this.data.loading) {
      this.loadAddonList()
    }
  },

  /**
   * 检查管理员权限
   */
  checkAdminPermission() {
    return adminUtils.isAdminModeEnabled()
  },

  /**
   * 加载附加项列表
   */
  async loadAddonList() {
    try {
      console.log('=== 开始加载附加项列表 ===')
      this.setData({ loading: true })

      const response = await request.get('/admin/addons', {
        status: 'active'
      })

      console.log('=== 附加项列表响应 ===')
      console.log('响应数据:', response)

      if (response && response.success) {
        console.log('附加项数量:', response.data?.addons?.length || 0)
        this.setData({
          activeAddons: response.data.addons || [],
          loading: false
        })
      } else {
        const serverError = response?.error || response?.message || '获取附加项列表失败'
        throw new Error(serverError)
      }
    } catch (error) {
      console.error('=== 加载附加项列表失败 ===')
      console.error('错误对象:', error)
      console.error('错误消息:', error.message)
      this.setData({ loading: false })
      
      if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
        wx.showToast({
          title: '权限验证失败',
          icon: 'none'
        })
        setTimeout(() => {
          wx.navigateBack()
        }, 2000)
      } else {
        wx.showToast({
          title: error.message || '加载失败',
          icon: 'none'
        })
      }
    }
  },

  /**
   * 删除附加项
   */
  onDeleteAddon(e) {
    const { addonId, addonName } = e.currentTarget.dataset
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除附加项"${addonName}"吗？删除后将无法恢复。`,
      success: (res) => {
        if (res.confirm) {
          this.deleteAddon(addonId)
        }
      }
    })
  },

  /**
   * 执行删除附加项
   */
  async deleteAddon(addonId) {
    try {
      console.log('=== 开始删除附加项 ===')
      console.log('附加项ID:', addonId)
      
      wx.showLoading({
        title: '删除中...',
        mask: true
      })

      const response = await request.delete(`/admin/addons/${addonId}`)

      console.log('=== 删除响应 ===')
      console.log('响应数据:', response)

      wx.hideLoading()

      if (response && response.success) {
        wx.showToast({
          title: '删除成功',
          icon: 'success'
        })
        
        // 从列表中移除已删除的项目
        const activeAddons = this.data.activeAddons.filter(addon => addon.addon_id !== addonId)
        this.setData({ activeAddons })
      } else {
        // 提取服务器返回的具体错误信息
        const serverError = response?.error || response?.message || '删除失败'
        throw new Error(serverError)
      }
    } catch (error) {
      wx.hideLoading()
      console.error('=== 删除附加项失败 ===')
      console.error('错误对象:', error)
      console.error('错误消息:', error.message)
      console.error('错误堆栈:', error.stack)
      
      // 提取并显示具体的错误信息
      let errorMsg = '删除失败'
      const errorMessage = error.message || ''
      
      if (errorMessage.includes('正在被使用') || errorMessage.includes('被使用')) {
        errorMsg = '该附加项正在被使用，无法删除'
      } else if (errorMessage.includes('HTTP 401') || errorMessage.includes('HTTP 403')) {
        errorMsg = '权限不足'
      } else if (errorMessage.includes('HTTP 404')) {
        errorMsg = '附加项不存在'
      } else if (errorMessage.includes('请求失败')) {
        // 这是从request.js抛出的通用错误，尝试获取更具体的信息
        errorMsg = '服务器处理失败，请稍后重试'
      } else if (errorMessage !== '删除失败') {
        // 使用服务器返回的具体错误信息
        errorMsg = errorMessage
      }
      
      wx.showToast({
        title: errorMsg,
        icon: 'none',
        duration: 3000
      })
    }
  },

  /**
   * 附加项名称输入
   */
  onNameInput(e) {
    this.setData({
      'newAddon.name': e.detail.value.trim()
    })
  },

  /**
   * 价格输入
   */
  onPriceInput(e) {
    let value = parseFloat(e.detail.value) || 0
    // 限制价格范围：-999.99 到 999.99（支持负价格，如"不要鸡腿"）
    if (value < -999.99) value = -999.99
    if (value > 999.99) value = 999.99
    
    this.setData({
      'newAddon.price_yuan': value
    })
  },

  /**
   * 价格-1按钮
   */
  onPriceMinus() {
    let currentPrice = this.data.newAddon.price_yuan || 0
    let newPrice = currentPrice - 1
    
    // 限制最小价格（支持负价格，如"不要鸡腿"可以是负数）
    if (newPrice < -999.99) {
      wx.showToast({
        title: '价格不能低于-999.99元',
        icon: 'none'
      })
      return
    }
    
    this.setData({
      'newAddon.price_yuan': newPrice
    })
  },

  /**
   * 价格+1按钮
   */
  onPricePlus() {
    let currentPrice = this.data.newAddon.price_yuan || 0
    let newPrice = currentPrice + 1
    
    // 限制最大价格
    if (newPrice > 999.99) {
      wx.showToast({
        title: '价格不能超过999.99元',
        icon: 'none'
      })
      return
    }
    
    this.setData({
      'newAddon.price_yuan': newPrice
    })
  },

  /**
   * 添加新附加项
   */
  onAddAddon() {
    const { name, price_yuan } = this.data.newAddon
    
    // 表单验证
    if (!name || name.trim() === '') {
      wx.showToast({
        title: '请输入附加项名称',
        icon: 'none'
      })
      return
    }
    
    // 检查价格范围（支持负价格，如减价附加项）
    if (price_yuan < -999.99 || price_yuan > 999.99) {
      wx.showToast({
        title: '价格范围应在-999.99到999.99元之间',
        icon: 'none'
      })
      return
    }
    
    // 检查名称是否重复
    const existingAddon = this.data.activeAddons.find(addon => 
      addon.name.trim() === name.trim()
    )
    if (existingAddon) {
      wx.showToast({
        title: '附加项名称已存在',
        icon: 'none'
      })
      return
    }

    this.createAddon()
  },

  /**
   * 创建新附加项
   */
  async createAddon() {
    try {
      this.setData({ submitting: true })

      const { name, price_yuan } = this.data.newAddon
      
      const response = await request.post('/admin/addons', {
        name: name.trim(),
        price_cents: Math.round(price_yuan * 100), // 转换为分
        display_order: this.data.activeAddons.length + 1, // 简单的排序逻辑
        is_default: false
      })

      if (response.success) {
        wx.showToast({
          title: '添加成功',
          icon: 'success'
        })
        
        // 添加到列表中
        const newAddon = response.data
        const activeAddons = [...this.data.activeAddons, newAddon]
        
        // 清空表单并更新列表
        this.setData({
          activeAddons: activeAddons,
          newAddon: {
            name: '',
            price_yuan: 0
          },
          submitting: false
        })
      } else {
        throw new Error(response.error || '添加失败')
      }
    } catch (error) {
      console.error('创建附加项失败:', error)
      this.setData({ submitting: false })
      
      let errorMsg = '添加失败'
      if (error.message.includes('名称已存在')) {
        errorMsg = '附加项名称已存在'
      } else if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
        errorMsg = '权限不足'
      }
      
      wx.showToast({
        title: errorMsg,
        icon: 'none'
      })
    }
  }
})