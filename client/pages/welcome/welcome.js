// welcome.js
const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

Page({
  data: {
    userInfo: {
      avatarUrl: defaultAvatarUrl,
      nickName: '',
    },
    openid: ''
  },
  onLoad() {
    this.getUserInfo()
    this.getOpenId()
  },
  getUserInfo() {
    // 获取用户信息，可以从缓存或其他方式获取
    const userInfo = wx.getStorageSync('userInfo') || {
      avatarUrl: defaultAvatarUrl,
      nickName: '用户'
    }
    this.setData({
      userInfo: userInfo
    })
  },
  getOpenId() {
    // 获取openid，这里先用模拟数据
    // 实际项目中需要通过wx.login获取code然后调用后台接口换取openid
    const openid = wx.getStorageSync('openid') || 'ox1234567890abcdef'
    this.setData({
      openid: openid
    })
  },
  onStartTap() {
    // 跳转到点餐页面
    wx.navigateTo({
      url: '../meals/meals' // 后续创建点餐页面时的路径
    })
  }
})