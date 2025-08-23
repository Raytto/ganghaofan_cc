Component({
  options: {
    addGlobalClass: true
  },
  
  methods: {
    goToCalendar() {
      wx.switchTab({
        url: '/pages/calendar/calendar'
      })
    },
    
    goToProfile() {
      wx.switchTab({
        url: '/pages/profile/profile'
      })
    }
  }
})