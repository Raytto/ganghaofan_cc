// profile.js
const request = require('../../utils/request.js')

Page({
  data: {
    userInfo: null,
    isAdmin: false,
    adminMode: false,
    loading: true
  },

  onLoad() {
    console.log('Profile page loaded')
    this.loadUserInfo()
  },

  onShow() {
    console.log('Profile page shown')
    this.loadUserInfo()
  },

  async loadUserInfo() {
    try {
      const token = wx.getStorageSync('access_token')
      if (!token) {
        wx.reLaunch({
          url: '../welcome/welcome'
        })
        return
      }

      const response = await request.get('/users/profile')
      
      if (response.success) {
        const userInfo = response.data
        const isAdmin = userInfo.is_admin || false
        
        // 获取管理模式状态
        let adminMode = wx.getStorageSync('admin_mode')
        // 注意：wx.getStorageSync 返回空字符串表示没有存储，而不是null
        const finalAdminMode = isAdmin ? (adminMode !== '' ? adminMode : true) : false
        
        this.setData({
          userInfo: userInfo,
          isAdmin: isAdmin,
          adminMode: finalAdminMode,
          loading: false
        })
        
        // 保存管理模式状态
        wx.setStorageSync('admin_mode', finalAdminMode)
        
      } else {
        throw new Error(response.error)
      }
      
    } catch (error) {
      console.error('获取用户信息失败:', error)
      
      if (error.message && (error.message.includes('HTTP 401') || error.message.includes('HTTP 403'))) {
        wx.removeStorageSync('access_token')
        wx.removeStorageSync('user_info')
        wx.reLaunch({
          url: '../welcome/welcome'
        })
      } else {
        this.setData({ loading: false })
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    }
  },

  onAdminModeChange(e) {
    const adminMode = e.detail.value
    this.setData({ adminMode })
    wx.setStorageSync('admin_mode', adminMode)
    
    wx.showToast({
      title: adminMode ? '管理模式已开启' : '管理模式已关闭',
      icon: 'success'
    })
  }
})