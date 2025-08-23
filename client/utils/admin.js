const request = require('./request.js')

/**
 * 管理员工具函数模块
 */
const AdminUtils = {
  /**
   * 获取当前管理员和管理模式状态
   * @returns {Object} { isAdmin: boolean, adminMode: boolean }
   */
  getAdminModeStatus() {
    try {
      // 从本地存储获取用户信息
      const userInfo = wx.getStorageSync('user_info')
      const isAdmin = userInfo ? userInfo.is_admin : false
      
      // 获取管理模式状态
      let adminMode = wx.getStorageSync('admin_mode')
      
      // 如果是管理员且首次使用，默认开启管理模式
      if (isAdmin && adminMode === '') {
        adminMode = true
        wx.setStorageSync('admin_mode', adminMode)
      }
      
      // 非管理员强制关闭管理模式
      if (!isAdmin) {
        adminMode = false
        wx.setStorageSync('admin_mode', adminMode)
      }
      
      return {
        isAdmin: isAdmin,
        adminMode: !!adminMode
      }
    } catch (error) {
      console.error('获取管理员状态失败:', error)
      return {
        isAdmin: false,
        adminMode: false
      }
    }
  },

  /**
   * 设置管理模式状态
   * @param {boolean} adminMode 管理模式状态
   * @returns {boolean} 是否设置成功
   */
  setAdminModeStatus(adminMode) {
    try {
      const { isAdmin } = this.getAdminModeStatus()
      
      // 只有管理员可以设置管理模式
      if (!isAdmin) {
        console.warn('非管理员无法设置管理模式')
        return false
      }
      
      wx.setStorageSync('admin_mode', !!adminMode)
      return true
    } catch (error) {
      console.error('设置管理模式失败:', error)
      return false
    }
  },

  /**
   * 检查是否为管理员且开启了管理模式
   * @returns {boolean}
   */
  isAdminModeEnabled() {
    const { isAdmin, adminMode } = this.getAdminModeStatus()
    return isAdmin && adminMode
  },

  /**
   * 异步刷新管理员状态
   * 从服务器获取最新用户信息
   * @returns {Promise<Object>} 更新后的状态
   */
  async refreshAdminStatus() {
    try {
      const response = await request.get('/users/profile')
      
      if (response.success) {
        // 更新本地用户信息
        wx.setStorageSync('user_info', response.data)
        
        // 重新获取管理员状态
        return this.getAdminModeStatus()
      } else {
        throw new Error(response.error || '获取用户信息失败')
      }
    } catch (error) {
      console.error('刷新管理员状态失败:', error)
      throw error
    }
  }
}

// 导出模块
module.exports = AdminUtils