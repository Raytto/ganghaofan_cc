// 罡好饭小程序主入口
App({
  onLaunch() {
    console.log('罡好饭小程序启动')
  },

  onShow() {
    console.log('罡好饭小程序显示')
  },

  onHide() {
    console.log('罡好饭小程序隐藏')
  },

  onError(error) {
    console.error('罡好饭小程序错误:', error)
  },

  globalData: {
    userInfo: null,
    defaultAvatarUrl: 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'
  }
})
