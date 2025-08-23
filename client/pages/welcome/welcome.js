// welcome.js
const request = require('../../utils/request.js')

const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

Page({
  data: {
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: '',
    },
    openid: '',
    isRegistered: true,
    isAdmin: false,
    loading: true
  },
  onLoad() {
    this.getOpenIdAndFetchUserInfo()
  },
  async getOpenIdAndFetchUserInfo() {
    try {
      // 1. 检查是否已有有效Token
      const token = wx.getStorageSync('access_token')
      if (token) {
        // 有Token，获取当前用户状态
        await this.fetchCurrentUserStatus()
        return
      }
      
      // 2. 没有Token，进行微信静默登录
      console.log('开始微信静默登录流程')
      const loginResult = await this.wechatSilentLogin()
      
      // 3. 根据登录结果处理
      if (loginResult.is_registered) {
        // 已注册用户，显示欢迎页面
        this.setData({
          userInfo: {
            avatarUrl: loginResult.avatar_url || defaultAvatarUrl,
            nickName: loginResult.wechat_name || '用户'
          },
          openid: loginResult.open_id,
          isRegistered: true,
          isAdmin: loginResult.is_admin || false,
          loading: false
        })
      } else {
        // 未注册用户，跳转到注册页面
        console.log('用户未注册，跳转到注册页面')
        wx.redirectTo({
          url: '../register/register'
        })
      }
      
    } catch (error) {
      console.error('初始化失败:', error)
      
      // 显示错误提示并跳转到注册页面
      wx.showToast({
        title: '初始化失败',
        icon: 'none',
        duration: 2000
      })
      
      setTimeout(() => {
        wx.redirectTo({
          url: '../register/register'
        })
      }, 2000)
    }
  },
  async wechatSilentLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: async (res) => {
          if (res.code) {
            try {
              console.log('获取到微信code:', res.code)
              // 调用微信静默登录接口
              const response = await request.post('/auth/wechat/login', {
                code: res.code
              })
              console.log('微信静默登录响应:', response)
              
              if (response.success) {
                // 保存登录信息
                const { access_token, user_info } = response.data
                wx.setStorageSync('access_token', access_token)
                wx.setStorageSync('user_info', user_info)
                
                resolve(user_info)
              } else {
                reject(new Error(response.error || '登录失败'))
              }
            } catch (error) {
              reject(error)
            }
          } else {
            reject(new Error('获取微信code失败'))
          }
        },
        fail: (error) => {
          reject(error)
        }
      })
    })
  },
  async fetchCurrentUserStatus() {
    try {
      // 检查是否有Token
      const token = wx.getStorageSync('access_token')
      if (!token) {
        throw new Error('未找到访问令牌')
      }
      
      // 调用获取用户信息API
      const response = await request.get('/users/profile')
      
      if (response.success) {
        const userData = response.data
        
        // 检查用户是否已注册
        if (userData.wechat_name && userData.wechat_name.trim()) {
          // 已注册用户，显示欢迎页面
          this.setData({
            userInfo: {
              avatarUrl: userData.avatar_url || defaultAvatarUrl,
              nickName: userData.wechat_name
            },
            openid: userData.open_id,
            isRegistered: true,
            isAdmin: userData.is_admin || false,
            loading: false
          })
          
          // 缓存用户信息
          wx.setStorageSync('userInfo', this.data.userInfo)
        } else {
          // 未注册用户，跳转到注册页面
          console.log('用户未注册，跳转到注册页面')
          wx.redirectTo({
            url: '../register/register'
          })
        }
        
      } else {
        // API调用失败
        throw new Error(response.error || '获取用户状态失败')
      }
      
    } catch (error) {
      console.error('获取用户状态失败:', error)
      
      // Token无效或其他错误，清除本地数据并跳转到注册页面
      if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
        console.log('Token已失效，清除本地数据')
        wx.removeStorageSync('access_token')
        wx.removeStorageSync('user_info')
      }
      
      // 跳转到注册页面
      console.log('获取用户状态失败，跳转到注册页面')
      wx.redirectTo({
        url: '../register/register'
      })
    }
  },
  onStartTap() {
    if (!this.data.isRegistered) {
      wx.showToast({
        title: '请先完成注册',
        icon: 'none'
      })
      return
    }
    
    // 跳转到主应用（日历页面）
    wx.switchTab({
      url: '../calendar/calendar'
    })
  }
})