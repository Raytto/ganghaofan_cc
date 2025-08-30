// 用户账单历史页面
// 参考文档: doc/client/page_billing_history.md

const request = require('../../../utils/request')
const adminUtils = require('../../../utils/admin')

Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 用户信息
    userInfo: null,
    balance: 0,
    
    // 交易记录列表
    transactions: [],
    
    // 分页信息
    pagination: {
      page: 1,
      page_size: 20,
      total: 0,
      has_more: true
    },
    
    // 筛选条件
    filters: {
      transaction_type: '',
      date_from: '',
      date_to: ''
    },
    
    // 页面状态
    loading: false,
    refreshing: false,
    loadingMore: false,
    
    // 交易类型选项
    transactionTypes: [
      { value: '', label: '全部类型' },
      { value: 'recharge', label: '充值' },
      { value: 'order_payment', label: '下单支付' },
      { value: 'order_refund', label: '订单退款' },
      { value: 'admin_deduction', label: '管理员扣费' },
      { value: 'admin_recharge', label: '管理员充值' }
    ],
    
    // 计算的索引值（用于picker组件）
    transactionTypeIndex: 0,
    
    // 显示筛选面板
    showFilters: false,
    
    // 显示充值面板
    showRecharge: false,
    rechargeAmount: '',
    submittingRecharge: false,
    
    // 快捷充值金额
    quickRechargeAmounts: [50, 100, 200, 500],
    
    // 权限
    isAdmin: false
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    console.log('[billing_history] onLoad:', options)
    
    // 检查用户权限
    this.checkUserPermission()
    
    // 处理页面参数
    this.processPageOptions(options)
    
    // 加载页面数据
    this.loadPageData()
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
    const { show_recharge } = options
    
    if (show_recharge === 'true') {
      this.setData({ showRecharge: true })
    }
  },

  /**
   * 加载页面数据
   */
  async loadPageData() {
    await Promise.all([
      this.loadUserInfo(),
      this.loadTransactionHistory()
    ])
  },

  /**
   * 加载用户信息
   */
  async loadUserInfo() {
    try {
      const response = await request.get('/users/me')
      if (response.success && response.data) {
        this.setData({
          userInfo: response.data,
          balance: response.data.balance_yuan
        })
      }
    } catch (error) {
      console.error('[billing_history] loadUserInfo error:', error)
    }
  },

  /**
   * 加载交易历史
   */
  async loadTransactionHistory(refresh = false) {
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
      
      const response = await request.get('/users/me/transactions', params)
      
      if (response.success && response.data) {
        const { transactions, total, page, page_size } = response.data
        const has_more = transactions.length === page_size && (page * page_size) < total
        
        this.setData({
          transactions: refresh ? transactions : [...this.data.transactions, ...transactions],
          'pagination.total': total,
          'pagination.page': page,
          'pagination.has_more': has_more
        })
      }
      
    } catch (error) {
      console.error('[billing_history] loadTransactionHistory error:', error)
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
    Promise.all([
      this.loadUserInfo(),
      this.loadTransactionHistory(true)
    ]).finally(() => {
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
    
    this.loadTransactionHistory()
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
    
    if (field === 'transaction_type') {
      this.setData({
        'filters.transaction_type': this.data.transactionTypes[value].value,
        transactionTypeIndex: value
      })
    } else {
      this.setData({
        [`filters.${field}`]: value
      })
    }
  },

  /**
   * 应用筛选条件
   */
  onApplyFilters() {
    this.setData({
      showFilters: false,
      transactions: [],
      'pagination.page': 1,
      'pagination.has_more': true
    })
    
    this.loadTransactionHistory()
  },

  /**
   * 重置筛选条件
   */
  onResetFilters() {
    this.setData({
      filters: {
        transaction_type: '',
        date_from: '',
        date_to: ''
      },
      transactionTypeIndex: 0
    })
  },

  /**
   * 显示充值面板
   */
  onShowRecharge() {
    this.setData({
      showRecharge: true,
      rechargeAmount: ''
    })
  },

  /**
   * 隐藏充值面板
   */
  onHideRecharge() {
    this.setData({
      showRecharge: false,
      rechargeAmount: ''
    })
  },

  /**
   * 充值金额输入
   */
  onRechargeAmountInput(e) {
    const value = parseFloat(e.detail.value) || ''
    this.setData({
      rechargeAmount: value
    })
  },

  /**
   * 快捷金额选择
   */
  onQuickAmountSelect(e) {
    const amount = e.currentTarget.dataset.amount
    this.setData({
      rechargeAmount: amount
    })
  },

  /**
   * 提交充值
   */
  async onSubmitRecharge() {
    const { rechargeAmount } = this.data
    
    if (!rechargeAmount || rechargeAmount <= 0) {
      wx.showToast({
        title: '请输入有效金额',
        icon: 'none'
      })
      return
    }
    
    if (rechargeAmount > 1000) {
      wx.showToast({
        title: '单次充值不能超过1000元',
        icon: 'none'
      })
      return
    }
    
    try {
      this.setData({ submittingRecharge: true })
      
      const response = await request.post('/users/me/recharge', {
        amount_yuan: rechargeAmount,
        payment_method: 'manual' // 手动充值
      })
      
      if (response.success) {
        wx.showToast({
          title: '充值成功',
          icon: 'success'
        })
        
        this.setData({
          showRecharge: false,
          rechargeAmount: ''
        })
        
        // 刷新数据
        setTimeout(() => {
          this.loadPageData()
        }, 1500)
      }
      
    } catch (error) {
      console.error('[billing_history] submitRecharge error:', error)
      wx.showToast({
        title: error.message || '充值失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submittingRecharge: false })
    }
  },

  /**
   * 格式化交易类型
   */
  formatTransactionType(type) {
    const typeMap = {
      'recharge': '💰 充值',
      'order_payment': '🍽️ 下单支付',
      'order_refund': '↩️ 订单退款',
      'admin_deduction': '⚠️ 管理员扣费',
      'admin_recharge': '🎁 管理员充值'
    }
    return typeMap[type] || '❓ 未知类型'
  },

  /**
   * 格式化交易金额
   */
  formatTransactionAmount(amount, type) {
    const isPositive = ['recharge', 'order_refund', 'admin_recharge'].includes(type)
    const sign = isPositive ? '+' : '-'
    const color = isPositive ? 'positive' : 'negative'
    
    return {
      text: `${sign}¥${Math.abs(amount)}`,
      color: color
    }
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
   * 交易记录点击
   */
  onTransactionTap(e) {
    const { transactionId } = e.currentTarget.dataset
    // 可以显示交易详情或导航到相关订单
    console.log('Transaction tapped:', transactionId)
  },

  /**
   * 导出交易记录
   */
  async onExportTransactions() {
    try {
      wx.showLoading({
        title: '导出中...'
      })
      
      const response = await request.get('/users/me/transactions/export', this.data.filters)
      
      if (response.success && response.data) {
        wx.showToast({
          title: '导出成功',
          icon: 'success'
        })
      }
      
    } catch (error) {
      console.error('[billing_history] exportTransactions error:', error)
      wx.showToast({
        title: '导出失败',
        icon: 'error'
      })
    } finally {
      wx.hideLoading()
    }
  },

  /**
   * 页面分享
   */
  onShareAppMessage() {
    return {
      title: '账单历史 - 罡好饭',
      path: '/pages/user/billing_history/billing_history'
    }
  }
})