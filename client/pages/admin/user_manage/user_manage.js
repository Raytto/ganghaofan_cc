// 管理员用户管理页面
// 参考文档: doc/client/page_user_manage.md

const request = require('../../../utils/request')
const adminUtils = require('../../../utils/admin')

Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 用户列表
    users: [],
    
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
      role: '',
      search: ''
    },
    
    // 页面状态
    loading: false,
    refreshing: false,
    loadingMore: false,
    
    // 筛选选项
    statusOptions: [
      { value: '', label: '全部状态' },
      { value: 'active', label: '活跃' },
      { value: 'inactive', label: '非活跃' },
      { value: 'suspended', label: '已暂停' }
    ],
    
    roleOptions: [
      { value: '', label: '全部角色' },
      { value: 'user', label: '普通用户' },
      { value: 'admin', label: '管理员' }
    ],
    
    // 计算的索引值（用于picker组件）
    statusIndex: 0,
    roleIndex: 0,
    
    // 显示筛选面板
    showFilters: false,
    
    // 选中的用户（用于批量操作）
    selectedUsers: [],
    showBatchActions: false,
    
    // 用户操作弹窗
    showUserModal: false,
    currentUser: null,
    userOperationForm: {
      balance_change: 0,
      operation_type: 'recharge', // recharge, deduct
      reason: ''
    },
    submittingOperation: false,
    
    // 快捷金额
    quickAmounts: [50, 100, 200, 500]
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    console.log('[user_manage] onLoad:', options)
    
    // 检查管理员权限
    if (!this.checkAdminPermission()) {
      wx.showToast({
        title: '权限不足',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
      return
    }
    
    // 加载用户列表
    this.loadUserList()
  },

  /**
   * 检查管理员权限
   */
  checkAdminPermission() {
    return adminUtils.isAdminModeEnabled()
  },

  /**
   * 加载用户列表
   */
  async loadUserList(refresh = false) {
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
      
      const response = await request.get('/admin/users', params)
      
      if (response.success && response.data) {
        const { users, total, page, page_size } = response.data
        const has_more = users.length === page_size && (page * page_size) < total
        
        this.setData({
          users: refresh ? users : [...this.data.users, ...users],
          'pagination.total': total,
          'pagination.page': page,
          'pagination.has_more': has_more
        })
      }
      
    } catch (error) {
      console.error('[user_manage] loadUserList error:', error)
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
    this.loadUserList(true).finally(() => {
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
    
    this.loadUserList()
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
    
    if (field === 'status') {
      this.setData({
        'filters.status': this.data.statusOptions[value].value,
        statusIndex: value
      })
    } else if (field === 'role') {
      this.setData({
        'filters.role': this.data.roleOptions[value].value,
        roleIndex: value
      })
    } else {
      this.setData({
        [`filters.${field}`]: value
      })
    }
  },

  /**
   * 搜索输入
   */
  onSearchInput(e) {
    const value = e.detail.value
    this.setData({
      'filters.search': value
    })
  },

  /**
   * 应用筛选条件
   */
  onApplyFilters() {
    this.setData({
      showFilters: false,
      users: [],
      'pagination.page': 1,
      'pagination.has_more': true
    })
    
    this.loadUserList()
  },

  /**
   * 重置筛选条件
   */
  onResetFilters() {
    this.setData({
      filters: {
        status: '',
        role: '',
        search: ''
      },
      statusIndex: 0,
      roleIndex: 0
    })
  },

  /**
   * 用户项点击
   */
  onUserItemTap(e) {
    const { userId } = e.currentTarget.dataset
    const user = this.data.users.find(u => u.user_id === userId)
    
    if (user) {
      this.showUserDetails(user)
    }
  },

  /**
   * 显示用户详情/操作面板
   */
  showUserDetails(user) {
    this.setData({
      currentUser: user,
      showUserModal: true,
      userOperationForm: {
        balance_change: 0,
        operation_type: 'recharge',
        reason: ''
      }
    })
  },

  /**
   * 隐藏用户操作面板
   */
  onHideUserModal() {
    this.setData({
      showUserModal: false,
      currentUser: null
    })
  },

  /**
   * 切换用户选择（批量操作）
   */
  onToggleUserSelection(e) {
    const { userId } = e.currentTarget.dataset
    let { selectedUsers } = this.data
    
    const index = selectedUsers.indexOf(userId)
    if (index > -1) {
      selectedUsers.splice(index, 1)
    } else {
      selectedUsers.push(userId)
    }
    
    this.setData({
      selectedUsers,
      showBatchActions: selectedUsers.length > 0
    })
  },

  /**
   * 全选/取消全选
   */
  onToggleSelectAll() {
    const { users, selectedUsers } = this.data
    const allSelected = selectedUsers.length === users.length
    
    this.setData({
      selectedUsers: allSelected ? [] : users.map(u => u.user_id),
      showBatchActions: !allSelected
    })
  },

  /**
   * 余额操作表单变更
   */
  onOperationFormChange(e) {
    const { field } = e.currentTarget.dataset
    const value = e.detail.value
    
    this.setData({
      [`userOperationForm.${field}`]: value
    })
  },

  /**
   * 快捷金额选择
   */
  onQuickAmountSelect(e) {
    const amount = e.currentTarget.dataset.amount
    this.setData({
      'userOperationForm.balance_change': amount
    })
  },

  /**
   * 提交用户操作
   */
  async onSubmitUserOperation() {
    const { currentUser, userOperationForm } = this.data
    const { balance_change, operation_type, reason } = userOperationForm
    
    if (!balance_change || balance_change <= 0) {
      wx.showToast({
        title: '请输入有效金额',
        icon: 'none'
      })
      return
    }
    
    if (!reason || reason.trim() === '') {
      wx.showToast({
        title: '请输入操作原因',
        icon: 'none'
      })
      return
    }
    
    try {
      this.setData({ submittingOperation: true })
      
      const endpoint = operation_type === 'recharge' 
        ? `/admin/users/${currentUser.user_id}/recharge`
        : `/admin/users/${currentUser.user_id}/deduct`
      
      const response = await request.post(endpoint, {
        amount_yuan: balance_change,
        reason: reason.trim()
      })
      
      if (response.success) {
        wx.showToast({
          title: '操作成功',
          icon: 'success'
        })
        
        this.setData({
          showUserModal: false,
          currentUser: null
        })
        
        // 刷新用户列表
        setTimeout(() => {
          this.loadUserList(true)
        }, 1500)
      }
      
    } catch (error) {
      console.error('[user_manage] submitUserOperation error:', error)
      wx.showToast({
        title: error.message || '操作失败',
        icon: 'error'
      })
    } finally {
      this.setData({ submittingOperation: false })
    }
  },

  /**
   * 用户状态操作
   */
  async onUserStatusAction(e) {
    const { userId, action } = e.currentTarget.dataset
    const user = this.data.users.find(u => u.user_id === userId)
    
    if (!user) return
    
    const actionMap = {
      'activate': '激活用户',
      'suspend': '暂停用户',
      'reset_password': '重置密码'
    }
    
    const actionText = actionMap[action]
    if (!actionText) return
    
    try {
      const confirmResult = await this.showConfirm(`确认${actionText}：${user.name}？`)
      if (!confirmResult) return
      
      let endpoint = ''
      let method = 'PUT'
      
      switch (action) {
        case 'activate':
          endpoint = `/admin/users/${userId}/activate`
          break
        case 'suspend':
          endpoint = `/admin/users/${userId}/suspend`
          break
        case 'reset_password':
          endpoint = `/admin/users/${userId}/reset-password`
          method = 'POST'
          break
      }
      
      const response = await request[method.toLowerCase()](endpoint)
      
      if (response.success) {
        wx.showToast({
          title: '操作成功',
          icon: 'success'
        })
        
        // 刷新列表
        setTimeout(() => {
          this.loadUserList(true)
        }, 1500)
      }
      
    } catch (error) {
      console.error(`[user_manage] ${action} error:`, error)
      wx.showToast({
        title: error.message || '操作失败',
        icon: 'error'
      })
    }
  },

  /**
   * 批量操作
   */
  async onBatchAction(e) {
    const { action } = e.currentTarget.dataset
    const { selectedUsers } = this.data
    
    if (selectedUsers.length === 0) {
      wx.showToast({
        title: '请选择用户',
        icon: 'none'
      })
      return
    }
    
    const actionMap = {
      'activate': '批量激活',
      'suspend': '批量暂停'
    }
    
    const actionText = actionMap[action]
    if (!actionText) return
    
    try {
      const confirmResult = await this.showConfirm(`确认${actionText} ${selectedUsers.length} 个用户？`)
      if (!confirmResult) return
      
      const endpoint = action === 'activate' 
        ? '/admin/users/batch-activate'
        : '/admin/users/batch-suspend'
      
      const response = await request.put(endpoint, {
        user_ids: selectedUsers
      })
      
      if (response.success) {
        wx.showToast({
          title: '批量操作成功',
          icon: 'success'
        })
        
        // 清除选择并刷新列表
        this.setData({
          selectedUsers: [],
          showBatchActions: false
        })
        
        setTimeout(() => {
          this.loadUserList(true)
        }, 1500)
      }
      
    } catch (error) {
      console.error(`[user_manage] batch ${action} error:`, error)
      wx.showToast({
        title: error.message || '批量操作失败',
        icon: 'error'
      })
    }
  },

  /**
   * 查看用户订单
   */
  onViewUserOrders(e) {
    const { userId } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/common/order_list/order_list?user_id=${userId}`
    })
  },

  /**
   * 查看用户账单
   */
  onViewUserBilling(e) {
    const { userId } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/admin/user_billing/user_billing?user_id=${userId}`
    })
  },

  /**
   * 导出用户数据
   */
  async onExportUsers() {
    try {
      wx.showLoading({
        title: '导出中...'
      })
      
      const response = await request.get('/admin/users/export', this.data.filters)
      
      if (response.success && response.data) {
        wx.showToast({
          title: '导出成功',
          icon: 'success'
        })
      }
      
    } catch (error) {
      console.error('[user_manage] exportUsers error:', error)
      wx.showToast({
        title: '导出失败',
        icon: 'error'
      })
    } finally {
      wx.hideLoading()
    }
  },

  /**
   * 格式化用户状态
   */
  formatUserStatus(status) {
    const statusMap = {
      'active': '🟢 活跃',
      'inactive': '🟡 非活跃',
      'suspended': '🔴 已暂停'
    }
    return statusMap[status] || '❓ 未知'
  },

  /**
   * 格式化用户角色
   */
  formatUserRole(role) {
    const roleMap = {
      'user': '👤 普通用户',
      'admin': '👑 管理员'
    }
    return roleMap[role] || '❓ 未知'
  },

  /**
   * 格式化最后登录时间
   */
  formatLastLogin(dateTimeStr) {
    if (!dateTimeStr) return '从未登录'
    
    const date = new Date(dateTimeStr)
    const now = new Date()
    const diff = now - date
    const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) {
      return '今天'
    } else if (diffDays === 1) {
      return '昨天'
    } else if (diffDays < 7) {
      return `${diffDays}天前`
    } else {
      return date.toLocaleDateString('zh-CN')
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
      title: '用户管理 - 罡好饭',
      path: '/pages/admin/user_manage/user_manage'
    }
  }
})