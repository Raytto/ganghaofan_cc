// 订单列表页面
// 参考文档: doc/client/page_order_list.md

const request = require('../../../utils/request')
const adminUtils = require('../../../utils/admin')

Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 订单列表
    orders: [],
    
    // 分页信息
    pagination: {
      page: 1,
      page_size: 20,
      total: 0,
      has_more: true
    },
    
    // 筛选条件
    filters: {
      status: '',
      date_from: '',
      date_to: '',
      meal_id: null
    },
    
    // 页面状态
    loading: false,
    refreshing: false,
    loadingMore: false,
    
    // 用户信息
    userInfo: null,
    isAdmin: false,
    
    // 筛选选项
    statusOptions: [
      { value: '', label: '全部状态' },
      { value: 'placed', label: '已下单' },
      { value: 'confirmed', label: '已确认' },
      { value: 'completed', label: '已完成' },
      { value: 'canceled', label: '已取消' }
    ],
    
    // 显示筛选面板
    showFilters: false,
    
    // 选中的订单（用于批量操作）
    selectedOrders: [],
    showBatchActions: false
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    console.log('[order_list] onLoad:', options)
    
    // 检查用户信息和权限
    this.checkUserPermission()
    
    // 处理页面参数
    this.processPageOptions(options)
    
    // 加载订单列表
    this.loadOrderList()
  },

  /**
   * 检查用户权限
   */
  checkUserPermission() {
    const userInfo = wx.getStorageSync('userInfo')
    const isAdmin = adminUtils.isAdminModeEnabled()
    
    this.setData({
      userInfo,
      isAdmin
    })
    
    if (!userInfo) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
      return
    }
  },

  /**
   * 处理页面参数
   */
  processPageOptions(options) {
    const { order_id, meal_id, status, user_id } = options
    const filters = { ...this.data.filters }
    
    if (order_id) {
      // 查看特定订单，设置标题
      wx.setNavigationBarTitle({
        title: '订单详情'
      })
    } else if (meal_id) {
      // 查看特定餐次的订单
      filters.meal_id = parseInt(meal_id)
      wx.setNavigationBarTitle({
        title: '餐次订单'
      })
    } else if (user_id && this.data.isAdmin) {
      // 管理员查看特定用户订单
      filters.user_id = parseInt(user_id)
      wx.setNavigationBarTitle({
        title: '用户订单'
      })
    } else {
      // 默认标题
      wx.setNavigationBarTitle({
        title: this.data.isAdmin ? '订单管理' : '我的订单'
      })
    }
    
    if (status) {
      filters.status = status
    }
    
    this.setData({ filters })
  },

  /**
   * 加载订单列表
   */
  async loadOrderList(refresh = false) {
    if (this.data.loading && !refresh) return
    
    try {
      if (refresh) {
        this.setData({ 
          refreshing: true,
          'pagination.page': 1,
          'pagination.has_more': true
        })
      } else {
        this.setData({ loading: true })
      }
      
      const { filters, pagination } = this.data
      const params = {
        ...filters,
        page: refresh ? 1 : pagination.page,
        page_size: pagination.page_size
      }
      
      // 清理空参数
      Object.keys(params).forEach(key => {
        if (params[key] === '' || params[key] === null || params[key] === undefined) {
          delete params[key]
        }
      })
      
      const response = await request.get('/orders', params)
      
      if (response.success && response.data) {
        const { orders, total, page, page_size } = response.data
        const has_more = orders.length === page_size && (page * page_size) < total
        
        this.setData({
          orders: refresh ? orders : [...this.data.orders, ...orders],
          'pagination.total': total,
          'pagination.page': page,
          'pagination.has_more': has_more
        })
      }
      
    } catch (error) {
      console.error('[order_list] loadOrderList error:', error)
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      })
    } finally {
      this.setData({ 
        loading: false, 
        refreshing: false,
        loadingMore: false
      })
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    this.loadOrderList(true).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  /**
   * 上拉加载更多
   */
  onReachBottom() {
    if (!this.data.pagination.has_more || this.data.loadingMore) {
      return
    }
    
    this.setData({ 
      loadingMore: true,
      'pagination.page': this.data.pagination.page + 1 
    })
    
    this.loadOrderList()
  },

  /**
   * 切换筛选面板
   */
  onToggleFilters() {
    this.setData({
      showFilters: !this.data.showFilters
    })
  },

  /**
   * 筛选条件变更
   */
  onFilterChange(e) {
    const { field } = e.currentTarget.dataset
    const value = e.detail.value
    
    this.setData({
      [`filters.${field}`]: value
    })
  },

  /**
   * 应用筛选条件
   */
  onApplyFilters() {
    this.setData({
      showFilters: false,
      orders: [],
      'pagination.page': 1,
      'pagination.has_more': true
    })
    
    this.loadOrderList()
  },

  /**
   * 重置筛选条件
   */
  onResetFilters() {
    this.setData({
      filters: {
        status: '',
        date_from: '',
        date_to: '',
        meal_id: null
      }
    })
  },

  /**
   * 订单项点击
   */
  onOrderItemTap(e) {
    const { orderId } = e.currentTarget.dataset
    // 可以导航到订单详情页面或展开详情
    console.log('Order item tapped:', orderId)
  },

  /**
   * 订单操作
   */
  async onOrderAction(e) {
    const { orderId, action } = e.currentTarget.dataset
    const order = this.data.orders.find(o => o.order_id === orderId)
    
    if (!order) return
    
    try {
      let confirmMessage = ''
      let endpoint = ''
      let method = 'PUT'
      let requestData = {}
      
      switch (action) {
        case 'cancel':
          confirmMessage = '确认取消订单？取消后将自动退款'
          endpoint = `/orders/${orderId}`
          method = 'DELETE'
          break
        case 'confirm':
          confirmMessage = '确认订单？确认后用户无法修改或取消'
          endpoint = `/admin/orders/${orderId}/confirm`
          break
        case 'complete':
          confirmMessage = '标记订单为已完成？'
          endpoint = `/admin/orders/${orderId}/complete`
          break
        default:
          return
      }
      
      if (confirmMessage) {
        const confirmResult = await this.showConfirm(confirmMessage)
        if (!confirmResult) return
      }
      
      const response = await request[method.toLowerCase()](endpoint, requestData)
      
      if (response.success) {
        wx.showToast({
          title: '操作成功',
          icon: 'success'
        })
        
        // 刷新列表
        setTimeout(() => {
          this.loadOrderList(true)
        }, 1000)
      }
      
    } catch (error) {
      console.error(`[order_list] ${action} error:`, error)
      wx.showToast({
        title: error.message || '操作失败',
        icon: 'error'
      })
    }
  },

  /**
   * 切换订单选择（批量操作）
   */
  onToggleOrderSelection(e) {
    const { orderId } = e.currentTarget.dataset
    let { selectedOrders } = this.data
    
    const index = selectedOrders.indexOf(orderId)
    if (index > -1) {
      selectedOrders.splice(index, 1)
    } else {
      selectedOrders.push(orderId)
    }
    
    this.setData({
      selectedOrders,
      showBatchActions: selectedOrders.length > 0
    })
  },

  /**
   * 全选/取消全选
   */
  onToggleSelectAll() {
    const { orders, selectedOrders } = this.data
    const allSelected = selectedOrders.length === orders.length
    
    this.setData({
      selectedOrders: allSelected ? [] : orders.map(o => o.order_id),
      showBatchActions: !allSelected
    })
  },

  /**
   * 批量操作
   */
  async onBatchAction(e) {
    const { action } = e.currentTarget.dataset
    const { selectedOrders } = this.data
    
    if (selectedOrders.length === 0) {
      wx.showToast({
        title: '请选择订单',
        icon: 'none'
      })
      return
    }
    
    try {
      let confirmMessage = ''
      let endpoint = ''
      
      switch (action) {
        case 'confirm':
          confirmMessage = `确认选中的 ${selectedOrders.length} 个订单？`
          endpoint = '/admin/orders/batch-confirm'
          break
        case 'complete':
          confirmMessage = `标记选中的 ${selectedOrders.length} 个订单为已完成？`
          endpoint = '/admin/orders/batch-complete'
          break
        default:
          return
      }
      
      const confirmResult = await this.showConfirm(confirmMessage)
      if (!confirmResult) return
      
      const response = await request.put(endpoint, {
        order_ids: selectedOrders
      })
      
      if (response.success) {
        wx.showToast({
          title: '批量操作成功',
          icon: 'success'
        })
        
        // 清除选择并刷新列表
        this.setData({
          selectedOrders: [],
          showBatchActions: false
        })
        
        setTimeout(() => {
          this.loadOrderList(true)
        }, 1000)
      }
      
    } catch (error) {
      console.error(`[order_list] batch ${action} error:`, error)
      wx.showToast({
        title: error.message || '批量操作失败',
        icon: 'error'
      })
    }
  },

  /**
   * 导出订单数据（仅管理员）
   */
  async onExportOrders() {
    if (!this.data.isAdmin) return
    
    try {
      wx.showLoading({
        title: '导出中...'
      })
      
      const response = await request.get('/admin/orders/export', this.data.filters)
      
      if (response.success && response.data) {
        // 这里可以处理导出的数据，比如生成文件链接或显示数据
        wx.showToast({
          title: '导出成功',
          icon: 'success'
        })
      }
      
    } catch (error) {
      console.error('[order_list] exportOrders error:', error)
      wx.showToast({
        title: '导出失败',
        icon: 'error'
      })
    } finally {
      wx.hideLoading()
    }
  },

  /**
   * 格式化状态文本
   */
  formatStatus(status) {
    const statusMap = {
      'placed': '已下单 🟡',
      'confirmed': '已确认 🟢',
      'completed': '已完成 ✅',
      'canceled': '已取消 ❌'
    }
    return statusMap[status] || '未知状态'
  },

  /**
   * 格式化日期时间
   */
  formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return ''
    
    const date = new Date(dateTimeStr)
    const now = new Date()
    const diff = now - date
    const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) {
      return '今天 ' + date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } else if (diffDays === 1) {
      return '昨天 ' + date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } else {
      return date.toLocaleDateString('zh-CN') + ' ' + 
             date.toLocaleTimeString('zh-CN', { 
               hour: '2-digit', 
               minute: '2-digit' 
             })
    }
  },

  /**
   * 显示确认对话框
   */
  showConfirm(content) {
    return new Promise((resolve) => {
      wx.showModal({
        title: '确认操作',
        content,
        success: (res) => {
          resolve(res.confirm)
        },
        fail: () => {
          resolve(false)
        }
      })
    })
  },

  /**
   * 页面分享
   */
  onShareAppMessage() {
    return {
      title: '订单列表 - 罡好饭',
      path: '/pages/common/order_list/order_list'
    }
  }
})