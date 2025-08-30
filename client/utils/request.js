// 网络请求封装工具
const config = require('../config/index.js')

class Request {
  constructor() {
    this.baseURL = config.baseURL
    this.apiPrefix = config.apiPrefix
    this.timeout = config.timeout
    this.debug = config.debug
  }

  /**
   * 发送HTTP请求
   * @param {Object} options 请求配置
   * @param {string} options.url 请求路径
   * @param {string} options.method 请求方法
   * @param {Object} options.data 请求数据
   * @param {Object} options.header 请求头
   */
  request(options) {
    return new Promise((resolve, reject) => {
      // 构造完整URL
      let url = options.url
      if (!url.startsWith('http')) {
        url = this.baseURL + this.apiPrefix + url
      }

      // 默认请求头
      let header = {
        'Content-Type': 'application/json',
        ...options.header
      }

      // 自动添加Token
      const token = wx.getStorageSync('access_token')
      console.log('=== Request Token处理 ===')
      console.log('从Storage读取的token:', token)
      console.log('token存在:', !!token)
      
      if (token) {
        header.Authorization = `Bearer ${token}`
        console.log('设置的Authorization头:', header.Authorization)
      } else {
        console.log('没有Token，跳过Authorization头设置')
      }

      // 调试日志
      if (this.debug) {
        console.log(`[Request] ${options.method} ${url}`)
        console.log('[Request] Header:', header)
        console.log('[Request] Data:', options.data)
      }

      wx.request({
        url: url,
        method: options.method || 'GET',
        data: options.data,
        header: header,
        timeout: this.timeout,
        success: (res) => {
          if (this.debug) {
            console.log(`[Response] ${options.method} ${url}:`, res)
          }

          // 检查HTTP状态码
          if (res.statusCode >= 200 && res.statusCode < 300) {
            // 检查业务状态码
            if (res.data && res.data.success === false) {
              console.log('[Request] 业务失败响应:', res.data)
              reject(new Error(res.data.message || '请求失败'))
            } else {
              resolve(res.data)
            }
          } else if (res.statusCode === 401 || res.statusCode === 403) {
            // Token失效处理
            this.handleAuthError()
            reject(new Error(`HTTP ${res.statusCode}: 认证失败`))
          } else {
            reject(new Error(`HTTP ${res.statusCode}: ${res.data?.message || '网络错误'}`))
          }
        },
        fail: (error) => {
          if (this.debug) {
            console.error(`[Request Error] ${options.method} ${url}:`, error)
          }
          reject(new Error(`网络请求失败: ${error.errMsg || error.message}`))
        }
      })
    })
  }

  /**
   * 处理认证错误
   */
  handleAuthError() {
    // 清除本地Token和用户信息
    wx.removeStorageSync('access_token')
    wx.removeStorageSync('user_info')
    wx.removeStorageSync('userInfo')
    
    // 提示用户重新登录
    wx.showToast({
      title: '登录状态已过期',
      icon: 'none',
      duration: 2000
    })
  }

  /**
   * GET请求
   * @param {string} url 请求路径
   * @param {Object} data 查询参数
   * @param {Object} header 请求头
   */
  get(url, data = {}, header = {}) {
    // 将data转换为查询参数
    const params = Object.keys(data)
      .filter(key => data[key] !== undefined && data[key] !== null)
      .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(data[key])}`)
      .join('&')
    
    if (params) {
      url += (url.includes('?') ? '&' : '?') + params
    }

    return this.request({
      url: url,
      method: 'GET',
      header: header
    })
  }

  /**
   * POST请求
   * @param {string} url 请求路径
   * @param {Object} data 请求数据
   * @param {Object} header 请求头
   */
  post(url, data = {}, header = {}) {
    return this.request({
      url: url,
      method: 'POST',
      data: data,
      header: header
    })
  }

  /**
   * PUT请求
   * @param {string} url 请求路径
   * @param {Object} data 请求数据
   * @param {Object} header 请求头
   */
  put(url, data = {}, header = {}) {
    return this.request({
      url: url,
      method: 'PUT',
      data: data,
      header: header
    })
  }

  /**
   * DELETE请求
   * @param {string} url 请求路径
   * @param {Object} data 请求数据
   * @param {Object} header 请求头
   */
  delete(url, data = {}, header = {}) {
    return this.request({
      url: url,
      method: 'DELETE',
      data: data,
      header: header
    })
  }
}

// 导出单例实例
module.exports = new Request()