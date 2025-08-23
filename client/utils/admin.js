// admin.js - 管理员模式工具函数
const request = require('./request.js')

/**
 * 获取管理员模式状态
 * @returns {Object} { isAdmin: boolean, adminMode: boolean }
 */
function getAdminModeStatus() {
  const userInfo = wx.getStorageSync('user_info') || {}
  const isAdmin = userInfo.is_admin || false
  const adminMode = wx.getStorageSync('admin_mode') || false
  
  return {
    isAdmin: isAdmin,
    adminMode: isAdmin ? adminMode : false
  }
}

/**
 * 设置管理员模式状态
 * @param {boolean} adminMode - 管理员模式状态
 */
function setAdminModeStatus(adminMode) {
  const { isAdmin } = getAdminModeStatus()
  if (isAdmin) {
    wx.setStorageSync('admin_mode', adminMode)
    return true
  }
  return false
}

/**
 * 检查是否为管理员且开启了管理模式
 * @returns {boolean}
 */
function isAdminModeEnabled() {
  const { isAdmin, adminMode } = getAdminModeStatus()
  return isAdmin && adminMode
}

/**
 * 异步获取最新用户信息并更新管理员状态
 * @returns {Promise<Object>}
 */
async function refreshAdminStatus() {
  try {
    const token = wx.getStorageSync('access_token')
    if (!token) {
      return { isAdmin: false, adminMode: false }
    }

    const response = await request.get('/users/profile')
    if (response.success) {
      const userInfo = response.data
      const isAdmin = userInfo.is_admin || false
      
      // 更新本地用户信息
      wx.setStorageSync('user_info', userInfo)
      
      // 获取当前管理模式状态
      let adminMode = wx.getStorageSync('admin_mode')
      if (isAdmin && adminMode === '') {
        // 管理员首次使用，默认开启管理模式
        adminMode = true
        wx.setStorageSync('admin_mode', adminMode)
      } else if (!isAdmin) {
        // 非管理员强制关闭管理模式
        adminMode = false
        wx.setStorageSync('admin_mode', adminMode)
      }
      
      return {
        isAdmin: isAdmin,
        adminMode: isAdmin ? adminMode : false,
        userInfo: userInfo
      }
    }
    
    return { isAdmin: false, adminMode: false }
  } catch (error) {
    console.error('刷新管理员状态失败:', error)
    return { isAdmin: false, adminMode: false }
  }
}

module.exports = {
  getAdminModeStatus,
  setAdminModeStatus,
  isAdminModeEnabled,
  refreshAdminStatus
}