const config = require('../config/index.js')

class Request {
  constructor() {
    this.baseURL = config.baseURL + config.apiPrefix
    this.timeout = config.timeout
  }

  request(options) {
    return new Promise((resolve, reject) => {
      const {
        url,
        method = 'GET',
        data = {},
        header = {}
      } = options

      const token = wx.getStorageSync('access_token')
      if (token) {
        header.Authorization = `Bearer ${token}`
      }

      wx.request({
        url: this.baseURL + url,
        method,
        data,
        header: {
          'Content-Type': 'application/json',
          ...header
        },
        timeout: this.timeout,
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(res.data)
          } else {
            reject(new Error(`HTTP ${res.statusCode}`))
          }
        },
        fail: (error) => {
          reject(error)
        }
      })
    })
  }

  get(url, data = {}) {
    return this.request({
      url,
      method: 'GET',
      data
    })
  }

  post(url, data = {}) {
    return this.request({
      url,
      method: 'POST',
      data
    })
  }

  put(url, data = {}) {
    return this.request({
      url,
      method: 'PUT',
      data
    })
  }

  delete(url, data = {}) {
    return this.request({
      url,
      method: 'DELETE',
      data
    })
  }
}

const request = new Request()

module.exports = request