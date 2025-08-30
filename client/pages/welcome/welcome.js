// 欢迎页面逻辑
const request = require('../../utils/request.js')

const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

Page({
  data: {
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: ''
    },
    openid: '',
    isRegistered: true,
    loading: true
  },

  /**
   * 页面加载
   */
  onLoad() {
    console.log('Welcome页面加载')
    this.getOpenIdAndFetchUserInfo()
  },

  /**
   * 页面显示时刷新数据
   */
  onShow() {
    // 如果不是初始加载，则刷新用户状态
    if (!this.data.loading) {
      this.getOpenIdAndFetchUserInfo()
    }
  },

  /**
   * 获取OpenID并检查用户状态
   */
  async getOpenIdAndFetchUserInfo() {
    try {
      this.setData({ loading: true })
      
      // 1. 检查本地Token
      const token = wx.getStorageSync('access_token')
      
      if (token) {
        // 有Token，验证用户状态
        await this.fetchCurrentUserStatus()
      } else {
        // 无Token，微信静默登录
        await this.wechatSilentLogin()
      }
      
    } catch (error) {
      console.error('获取用户信息失败:', error)
      wx.showToast({
        title: '初始化失败',
        icon: 'none'
      })
      
      // 错误时跳转到注册页面
      setTimeout(() => {
        wx.redirectTo({
          url: '../register/register'
        })
      }, 2000)
    }
  },

  /**
   * 微信静默登录
   */
  async wechatSilentLogin() {
    try {
      // 1. 获取微信授权码
      const loginResult = await new Promise((resolve, reject) => {
        wx.login({
          success: resolve,
          fail: reject
        })
      })

      if (!loginResult.code) {
        throw new Error('获取微信授权码失败')
      }

      console.log('获取到微信code:', loginResult.code)

      // 2. 发送到服务器登录
      const response = await request.post('/auth/wechat/login', {
        code: loginResult.code
      })

      console.log('=== 静默登录响应分析 ===')
      console.log('完整响应对象:', response)
      console.log('response.success:', response?.success)
      console.log('response.data:', response?.data)
      
      if (response?.data) {
        console.log('response.data.access_token:', response.data.access_token)
        console.log('response.data.user_info:', response.data.user_info)
      }

      if (response && response.success && response.data) {
        // 修复：正确提取Token和用户信息
        const access_token = response.data.access_token
        const user_info = response.data.user_info

        console.log('=== Token提取结果 ===')
        console.log('提取的access_token:', access_token)
        console.log('access_token类型:', typeof access_token)
        console.log('access_token长度:', access_token?.length)
        console.log('提取的user_info:', user_info)

        if (!access_token) {
          console.error('错误：access_token为空！')
          throw new Error('服务器返回的Token为空')
        }

        // 3. 保存Token和用户信息
        console.log('=== 开始保存到Storage ===')
        try {
          wx.setStorageSync('access_token', access_token)
          wx.setStorageSync('user_info', user_info)
          console.log('Storage保存操作已执行')
        } catch (storageError) {
          console.error('Storage保存失败:', storageError)
          throw storageError
        }

        // 验证保存是否成功
        console.log('=== 验证Storage保存结果 ===')
        const savedToken = wx.getStorageSync('access_token')
        const savedUserInfo = wx.getStorageSync('user_info')
        console.log('读取的savedToken:', savedToken)
        console.log('读取的savedUserInfo:', savedUserInfo)
        console.log('Token保存验证:', savedToken ? '成功' : '失败')

        // 4. 更新页面数据
        this.updateUserInfo(user_info)
        
        return user_info
      } else {
        console.error('响应验证失败:', {
          hasResponse: !!response,
          success: response?.success,
          hasData: !!response?.data
        })
        throw new Error(response?.message || '登录失败')
      }

    } catch (error) {
      console.error('微信静默登录失败:', error)
      throw error
    }
  },

  /**
   * 获取当前用户状态
   */
  async fetchCurrentUserStatus() {
    try {
      console.log('验证Token状态')
      
      const response = await request.get('/auth/me')
      
      console.log('用户状态响应:', response)

      if (response && response.success && response.data) {
        const userInfo = response.data
        
        // 更新本地存储
        wx.setStorageSync('user_info', userInfo)
        
        // 更新页面数据
        this.updateUserInfo(userInfo)
        
        return userInfo
      } else {
        throw new Error(response?.message || '获取用户状态失败')
      }
      
    } catch (error) {
      console.error('获取用户状态失败:', error)
      
      // Token失效，清除本地数据并重新登录
      if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
        wx.removeStorageSync('access_token')
        wx.removeStorageSync('user_info')
        // 重新进行微信静默登录
        await this.wechatSilentLogin()
      } else {
        throw error
      }
    }
  },

  /**
   * 更新用户信息到页面
   */
  updateUserInfo(userInfo) {
    // 添加详细调试信息
    console.log('用户信息详情:', JSON.stringify(userInfo, null, 2))
    console.log('wechat_name字段:', userInfo.wechat_name)
    console.log('wechat_name类型:', typeof userInfo.wechat_name)
    console.log('用户状态:', userInfo.status)
    console.log('is_registered字段:', userInfo.is_registered)
    
    const isRegistered = userInfo.wechat_name && userInfo.wechat_name.trim() !== ''
    console.log('最终判断isRegistered:', isRegistered)
    
    this.setData({
      userInfo: {
        avatarUrl: userInfo.avatar_url || defaultAvatarUrl,
        nickName: userInfo.wechat_name || ''
      },
      openid: userInfo.open_id || '',
      isRegistered: isRegistered,
      loading: false
    })

    // 保存显示用的用户信息
    wx.setStorageSync('userInfo', this.data.userInfo)

    // 根据注册状态决定页面跳转
    if (!isRegistered) {
      console.log('用户未注册，跳转注册页面')
      wx.redirectTo({
        url: '../register/register'
      })
    } else {
      console.log('用户已注册，显示欢迎页面')
    }
  },

  /**
   * 开始使用按钮点击
   */
  onStartTap() {
    if (!this.data.isRegistered) {
      wx.showToast({
        title: '请先完成注册',
        icon: 'none'
      })
      return
    }

    // 跳转到日历页面
    wx.switchTab({
      url: '../calendar/calendar'
    })
  }
})