// 注册页面逻辑
const request = require('../../utils/request.js')

const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

Page({
  data: {
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: ''
    },
    canIUseGetUserProfile: wx.canIUse('getUserProfile'),
    canIUseNicknameComp: wx.canIUse('input.type.nickname'),
    canRegister: false,
    registering: false
  },

  /**
   * 页面加载
   */
  onLoad() {
    console.log('Register页面加载')
    
    // 认证保护：检查是否有有效Token
    const token = wx.getStorageSync('access_token')
    console.log('Register页面Token检查:', !!token)
    
    if (!token) {
      console.log('Register页面：没有Token，跳转到Welcome页面')
      wx.showToast({
        title: '需要先进行身份验证',
        icon: 'none',
        duration: 1500
      })
      
      // 跳转到Welcome页面进行认证
      setTimeout(() => {
        wx.redirectTo({
          url: '../welcome/welcome'
        })
      }, 1500)
      return
    }
    
    this.checkCanRegister()
  },

  /**
   * 头像选择
   */
  onChooseAvatar(e) {
    const { avatarUrl } = e.detail
    console.log('选择头像:', avatarUrl)
    
    this.setData({
      'userInfo.avatarUrl': avatarUrl
    })
    
    this.checkCanRegister()
  },

  /**
   * 昵称输入
   */
  onInputChange(e) {
    const nickName = e.detail.value
    console.log('输入昵称:', nickName)
    
    this.setData({
      'userInfo.nickName': nickName
    })
    
    this.checkCanRegister()
  },

  /**
   * 昵称输入确认（兼容处理）
   */
  onInputConfirm(e) {
    const nickName = e.detail.value
    this.setData({
      'userInfo.nickName': nickName
    })
    
    this.checkCanRegister()
  },

  /**
   * 获取用户信息（旧版本兼容）
   */
  getUserProfile() {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        console.log('获取用户资料成功:', res.userInfo)
        this.setData({
          userInfo: res.userInfo
        })
        this.checkCanRegister()
      },
      fail: (error) => {
        console.error('获取用户资料失败:', error)
        wx.showToast({
          title: '获取用户信息失败',
          icon: 'none'
        })
      }
    })
  },

  /**
   * 检查是否可以注册
   */
  checkCanRegister() {
    const { nickName, avatarUrl } = this.data.userInfo
    const canRegister = nickName && 
                       nickName.trim() && 
                       avatarUrl && 
                       avatarUrl !== defaultAvatarUrl
    
    this.setData({ canRegister })
    
    console.log('检查注册条件:', { 
      nickName, 
      avatarUrl, 
      canRegister 
    })
  },

  /**
   * 注册按钮点击
   */
  async onRegisterTap() {
    if (!this.data.canRegister) {
      wx.showToast({
        title: '请完善信息',
        icon: 'none'
      })
      return
    }

    if (this.data.registering) {
      return // 防止重复点击
    }

    const { nickName, avatarUrl } = this.data.userInfo

    // 表单验证
    if (!nickName || !nickName.trim()) {
      wx.showToast({
        title: '请输入昵称',
        icon: 'none'
      })
      return
    }

    // 检查Token
    console.log('=== 注册前Token检查 ===')
    const token = wx.getStorageSync('access_token')
    const userInfo = wx.getStorageSync('user_info')
    console.log('当前Storage中的token:', token)
    console.log('当前Storage中的userInfo:', userInfo)
    console.log('token存在:', !!token)
    console.log('token类型:', typeof token)
    console.log('token长度:', token?.length)
    
    if (!token) {
      console.error('Token不存在，无法进行注册')
      wx.showToast({
        title: '登录状态已过期，请重新打开小程序',
        icon: 'none'
      })
      return
    }

    try {
      this.setData({ registering: true })

      console.log('开始注册:', { 
        wechat_name: nickName.trim(), 
        avatar_url: avatarUrl 
      })

      // 调用注册接口
      const response = await request.post('/auth/register', {
        wechat_name: nickName.trim(),
        avatar_url: avatarUrl
      })

      console.log('注册响应:', response)

      if (response && response.success) {
        // 更新本地用户信息
        wx.setStorageSync('user_info', response.data)

        wx.showToast({
          title: '注册成功',
          icon: 'success',
          duration: 1500
        })

        // 注册成功后跳转回欢迎页面
        setTimeout(() => {
          wx.redirectTo({
            url: '../welcome/welcome'
          })
        }, 1500)

      } else {
        throw new Error(response?.message || '注册失败')
      }

    } catch (error) {
      console.error('注册失败:', error)
      
      // 处理认证失败
      if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
        wx.removeStorageSync('access_token')
        wx.removeStorageSync('user_info')
        wx.showToast({
          title: '登录状态已过期，请重新打开小程序',
          icon: 'none'
        })
      } else {
        wx.showToast({
          title: error.message || '注册失败',
          icon: 'none'
        })
      }
    } finally {
      this.setData({ registering: false })
    }
  }
})