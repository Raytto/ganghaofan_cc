// register.js
const request = require('../../utils/request.js')
const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

Page({
  data: {
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: '',
    },
    canIUseGetUserProfile: wx.canIUse('getUserProfile'),
    canIUseNicknameComp: wx.canIUse('input.type.nickname'),
    canRegister: false,
    registering: false
  },
  
  onLoad() {
    // 页面加载时检查是否可以注册
    this.checkCanRegister()
  },
  
  onChooseAvatar(e) {
    const { avatarUrl } = e.detail
    this.setData({
      "userInfo.avatarUrl": avatarUrl
    })
    this.checkCanRegister()
  },
  
  onInputChange(e) {
    const nickName = e.detail.value
    this.setData({
      "userInfo.nickName": nickName
    })
    this.checkCanRegister()
  },
  
  getUserProfile(e) {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        console.log(res)
        this.setData({
          userInfo: res.userInfo
        })
        this.checkCanRegister()
      }
    })
  },
  
  checkCanRegister() {
    const { avatarUrl, nickName } = this.data.userInfo
    const canRegister = nickName && nickName.trim() && avatarUrl && avatarUrl !== defaultAvatarUrl
    this.setData({
      canRegister: canRegister
    })
  },
  
  async onRegisterTap() {
    if (!this.data.canRegister || this.data.registering) {
      return
    }
    
    if (!this.data.userInfo.nickName || !this.data.userInfo.nickName.trim()) {
      wx.showToast({
        title: '请输入昵称',
        icon: 'none'
      })
      return
    }
    
    // 检查是否有访问令牌
    const token = wx.getStorageSync('access_token')
    if (!token) {
      wx.showToast({
        title: '登录状态已过期，请重新打开小程序',
        icon: 'none'
      })
      return
    }
    
    try {
      this.setData({ registering: true })
      
      // 调用完成注册接口
      const response = await request.post('/auth/register', {
        wechat_name: this.data.userInfo.nickName.trim(),
        avatar_url: this.data.userInfo.avatarUrl
      })
      
      if (response.success) {
        // 更新本地用户信息
        const updatedUserInfo = response.data
        wx.setStorageSync('user_info', updatedUserInfo)
        
        wx.showToast({
          title: '注册成功',
          icon: 'success'
        })
        
        // 延迟一下再跳转，让用户看到成功提示
        setTimeout(() => {
          wx.switchTab({
            url: '../calendar/calendar'
          })
        }, 1500)
        
      } else {
        throw new Error(response.error || '注册失败')
      }
      
    } catch (error) {
      console.error('注册失败:', error)
      
      // 如果是认证相关错误，清除token并提示重新登录
      if (error.message && (error.message.includes('HTTP 401') || error.message.includes('HTTP 403'))) {
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