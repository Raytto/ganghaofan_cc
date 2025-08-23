const request = require('../../utils/request.js')
const adminUtils = require('../../utils/admin.js')

Page({
  data: {
    userInfo: {},
    isAdmin: false,
    adminMode: false,
    loading: true
  },

  onLoad() {
    this.loadUserInfo()
  },

  onShow() {
    // 检查登录状态
    const token = wx.getStorageSync('access_token')
    if (!token) {
      wx.reLaunch({ url: '../welcome/welcome' })
      return
    }
    
    // 刷新用户信息和管理员状态
    this.loadUserInfo()
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      this.setData({ loading: true })

      // 调用API获取用户信息
      const response = await request.get('/users/profile')

      if (response.success) {
        const userInfo = response.data
        
        // 保存用户信息到本地存储
        wx.setStorageSync('user_info', userInfo)
        
        // 获取管理员状态
        const { isAdmin, adminMode } = adminUtils.getAdminModeStatus()
        
        this.setData({
          userInfo: userInfo,
          isAdmin: isAdmin,
          adminMode: adminMode,
          loading: false
        })
      } else {
        throw new Error(response.error || '获取用户信息失败')
      }
    } catch (error) {
      console.error('加载用户信息异常:', error)
      this.setData({ loading: false })
      
      if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
        // Token失效，清除本地数据并跳转到欢迎页
        wx.removeStorageSync('access_token')
        wx.removeStorageSync('user_info')
        wx.reLaunch({ url: '../welcome/welcome' })
      } else {
        wx.showToast({
          title: '加载用户信息失败',
          icon: 'none'
        })
      }
    }
  },

  /**
   * 管理模式开关变化
   */
  onAdminModeChange(e) {
    const newAdminMode = e.detail.value
    
    // 设置管理模式状态
    const success = adminUtils.setAdminModeStatus(newAdminMode)
    
    if (success) {
      this.setData({ adminMode: newAdminMode })
      
      wx.showToast({
        title: newAdminMode ? '管理模式已开启' : '管理模式已关闭',
        icon: 'success'
      })
    } else {
      wx.showToast({
        title: '设置失败',
        icon: 'none'
      })
    }
  },

  /**
   * 跳转到附加项管理
   */
  goToAddonManage() {
    if (!adminUtils.isAdminModeEnabled()) {
      wx.showToast({
        title: '请先开启管理模式',
        icon: 'none'
      })
      return
    }
    
    // 跳转到附加项管理页面
    wx.navigateTo({
      url: '../admin/addon_manage/addon_manage'
    })
  },

  /**
   * 跳转到用户管理
   */
  goToUserManage() {
    if (!adminUtils.isAdminModeEnabled()) {
      wx.showToast({
        title: '请先开启管理模式',
        icon: 'none'
      })
      return
    }
    
    // TODO: 跳转到用户管理页面
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  /**
   * 跳转到餐次管理
   */
  goToMealManage() {
    if (!adminUtils.isAdminModeEnabled()) {
      wx.showToast({
        title: '请先开启管理模式',
        icon: 'none'
      })
      return
    }
    
    // TODO: 跳转到餐次管理页面
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  /**
   * 跳转到我的订单
   */
  goToMyOrders() {
    // TODO: 跳转到订单列表页面
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  /**
   * 跳转到账单明细
   */
  goToLedger() {
    // TODO: 跳转到账单明细页面
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  },

  /**
   * 跳转到设置
   */
  goToSettings() {
    // TODO: 跳转到设置页面
    wx.showToast({
      title: '功能开发中',
      icon: 'none'
    })
  }
})