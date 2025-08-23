# 参考文档: doc/db/supporting_operations.md
# 支持业务操作测试

import pytest


class TestUserManagement:
    """用户管理测试"""
    
    def test_register_user_success(self, support_ops):
        """测试用户注册成功"""
        result = support_ops.register_user(
            open_id="test_new_user",
            wechat_name="新测试用户",
            avatar_url="http://test.com/new_user.jpg"
        )
        
        assert result['success'] is True
        assert result['user_id'] is not None
        assert result['data']['wechat_name'] == "新测试用户"
        assert result['data']['balance_cents'] == 0
        assert result['data']['is_admin'] is False
        assert "注册成功" in result['message']
    
    def test_register_user_duplicate_open_id(self, support_ops):
        """测试重复openid注册"""
        # 第一次注册
        support_ops.register_user(
            open_id="duplicate_test",
            wechat_name="用户1",
            avatar_url="http://test.com/user1.jpg"
        )
        
        # 第二次注册应该失败
        with pytest.raises(Exception) as exc_info:
            support_ops.register_user(
                open_id="duplicate_test",  # 重复的openid
                wechat_name="用户2",
                avatar_url="http://test.com/user2.jpg"
            )
        
        assert "已存在" in str(exc_info.value) or "重复" in str(exc_info.value)
    
    def test_user_login_success(self, support_ops):
        """测试用户登录成功"""
        # 先注册用户
        register_result = support_ops.register_user(
            open_id="login_test_user",
            wechat_name="登录测试用户",
            avatar_url="http://test.com/login_user.jpg"
        )
        
        # 登录
        login_result = support_ops.user_login("login_test_user")
        
        assert login_result['success'] is True
        assert login_result['data']['user_id'] == register_result['user_id']
        assert login_result['data']['wechat_name'] == "登录测试用户"
        assert "登录成功" in login_result['message']
    
    def test_user_login_nonexistent_user(self, support_ops):
        """测试不存在用户的登录"""
        result = support_ops.user_login("nonexistent_openid", auto_register=False)
        
        assert result['success'] is False
        assert "不存在" in result.get('error', '') or "未找到" in result.get('message', '')
    
    def test_get_user_by_id(self, support_ops, sample_user):
        """测试根据ID获取用户"""
        user_info = support_ops.get_user_by_id(sample_user)
        
        assert user_info is not None
        assert user_info['user_id'] == sample_user
        assert user_info['wechat_name'] == "测试用户"
        assert user_info['status'] == 'active'
    
    def test_get_user_by_id_nonexistent(self, support_ops):
        """测试获取不存在的用户"""
        user_info = support_ops.get_user_by_id(99999)
        
        assert user_info is None


class TestAdminManagement:
    """管理员管理测试"""
    
    def test_admin_set_user_admin(self, support_ops, sample_admin_user, sample_user):
        """测试设置用户管理员权限"""
        # 设置为管理员
        result = support_ops.admin_set_user_admin(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            is_admin=True
        )
        
        assert result['target_user_id'] == sample_user
        assert result['is_admin'] is True
        assert result['changed'] is True
        assert "管理员" in result['message']
        
        # 验证权限已设置
        user_info = support_ops.get_user_by_id(sample_user)
        assert user_info['is_admin'] is True
        
        # 取消管理员权限
        result2 = support_ops.admin_set_user_admin(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            is_admin=False
        )
        
        assert result2['is_admin'] is False
        assert result2['changed'] is True
        assert "普通用户" in result2['message']
    
    def test_admin_set_user_admin_no_change(self, support_ops, sample_admin_user, sample_user):
        """测试设置相同的管理员权限"""
        # 用户默认不是管理员，再次设置为非管理员应该无变化
        result = support_ops.admin_set_user_admin(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            is_admin=False
        )
        
        assert result['changed'] is False
        assert "无变化" in result['message']
    
    def test_admin_set_user_status(self, support_ops, sample_admin_user, sample_user):
        """测试设置用户账户状态"""
        # 停用用户
        result = support_ops.admin_set_user_status(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            status="suspended",
            reason="测试停用"
        )
        
        assert result['target_user_id'] == sample_user
        assert result['status'] == "suspended"
        assert result['changed'] is True
        assert result['reason'] == "测试停用"
        assert "已停用" in result['message']
        
        # 验证状态已更改
        user_info = support_ops.get_user_by_id(sample_user)
        assert user_info['status'] == "suspended"
        
        # 重新激活用户
        result2 = support_ops.admin_set_user_status(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            status="active",
            reason="测试激活"
        )
        
        assert result2['status'] == "active"
        assert result2['changed'] is True
        assert "已激活" in result2['message']
    
    def test_admin_cannot_suspend_self(self, support_ops, sample_admin_user):
        """测试管理员不能停用自己"""
        with pytest.raises(Exception) as exc_info:
            support_ops.admin_set_user_status(
                admin_user_id=sample_admin_user,
                target_user_id=sample_admin_user,
                status="suspended",
                reason="测试自我停用"
            )
        
        assert "不能停用自己" in str(exc_info.value)
    
    def test_non_admin_cannot_manage_users(self, support_ops, sample_user):
        """测试非管理员不能管理其他用户"""
        # 创建另一个用户
        other_user_result = support_ops.register_user(
            open_id="other_test_user",
            wechat_name="其他用户",
            avatar_url="http://test.com/other.jpg"
        )
        other_user_id = other_user_result['user_id']
        
        # 普通用户尝试设置其他用户权限应该失败
        with pytest.raises(Exception) as exc_info:
            support_ops.admin_set_user_admin(
                admin_user_id=sample_user,  # 普通用户
                target_user_id=other_user_id,
                is_admin=True
            )
        
        assert "不是管理员" in str(exc_info.value) or "权限" in str(exc_info.value)


class TestUsersList:
    """用户列表查询测试"""
    
    def test_query_users_list_all(self, support_ops, sample_admin_user, sample_user):
        """测试查询所有用户列表"""
        result = support_ops.query_users_list()
        
        assert result['success'] is True
        users_data = result['data']
        
        assert len(users_data['users']) >= 2  # 至少有管理员和普通用户
        assert users_data['pagination']['total_count'] >= 2
        
        # 查找测试用户
        test_user = next((u for u in users_data['users'] if u['user_id'] == sample_user), None)
        assert test_user is not None
        assert test_user['wechat_name'] == "测试用户"
        assert test_user['is_admin'] is False
        assert test_user['is_admin_text'] == "否"
        assert test_user['status'] == "active"
        assert test_user['status_text'] == "正常"
    
    def test_query_users_list_filter_by_admin(self, support_ops, sample_admin_user):
        """测试按管理员权限筛选用户"""
        # 查询管理员用户
        result = support_ops.query_users_list(is_admin=True)
        
        assert result['success'] is True
        users_data = result['data']
        
        # 所有返回的用户都应该是管理员
        for user in users_data['users']:
            assert user['is_admin'] is True
            assert user['is_admin_text'] == "是"
    
    def test_query_users_list_filter_by_status(self, support_ops, sample_admin_user, sample_user):
        """测试按状态筛选用户"""
        # 先停用一个用户
        support_ops.admin_set_user_status(
            admin_user_id=sample_admin_user,
            target_user_id=sample_user,
            status="suspended",
            reason="测试筛选"
        )
        
        # 查询活跃用户
        active_result = support_ops.query_users_list(status="active")
        assert active_result['success'] is True
        
        # 查询停用用户
        suspended_result = support_ops.query_users_list(status="suspended")
        assert suspended_result['success'] is True
        
        # 在停用用户列表中应该找到测试用户
        suspended_users = suspended_result['data']['users']
        test_user = next((u for u in suspended_users if u['user_id'] == sample_user), None)
        assert test_user is not None
        assert test_user['status'] == "suspended"
        assert test_user['status_text'] == "停用"
    
    def test_query_users_list_pagination(self, support_ops):
        """测试用户列表分页"""
        # 创建多个测试用户
        for i in range(5):
            support_ops.register_user(
                open_id=f"pagination_test_user_{i}",
                wechat_name=f"分页测试用户{i+1}",
                avatar_url=f"http://test.com/page_user_{i}.jpg"
            )
        
        # 测试第一页（限制2个用户）
        result = support_ops.query_users_list(offset=0, limit=2)
        
        assert result['success'] is True
        users_data = result['data']
        pagination = users_data['pagination']
        
        assert len(users_data['users']) == 2
        assert pagination['per_page'] == 2
        assert pagination['current_page'] == 1
        assert pagination['total_count'] >= 5
        assert pagination['has_next'] is True
        assert pagination['has_prev'] is False


class TestValidations:
    """验证逻辑测试"""
    
    def test_invalid_open_id_registration(self, support_ops):
        """测试无效的openid注册"""
        with pytest.raises(Exception) as exc_info:
            support_ops.register_user(
                open_id="",  # 空字符串
                wechat_name="测试用户",
                avatar_url="http://test.com/test.jpg"
            )
        
        assert "不能为空" in str(exc_info.value)
    
    def test_long_wechat_name_registration(self, support_ops):
        """测试过长微信昵称注册"""
        with pytest.raises(Exception) as exc_info:
            support_ops.register_user(
                open_id="long_name_test",
                wechat_name="a" * 101,  # 超过100字符
                avatar_url="http://test.com/test.jpg"
            )
        
        assert "长度" in str(exc_info.value)
    
    def test_invalid_status_value(self, support_ops, sample_admin_user, sample_user):
        """测试无效的状态值"""
        with pytest.raises(Exception) as exc_info:
            support_ops.admin_set_user_status(
                admin_user_id=sample_admin_user,
                target_user_id=sample_user,
                status="invalid_status",
                reason="测试无效状态"
            )
        
        assert "active" in str(exc_info.value) or "suspended" in str(exc_info.value)
    
    def test_invalid_pagination_params(self, support_ops):
        """测试无效的分页参数"""
        # 负数偏移量
        with pytest.raises(Exception) as exc_info:
            support_ops.query_users_list(offset=-1)
        
        assert "偏移量不能为负数" in str(exc_info.value)
        
        # 超过限制的每页条数
        with pytest.raises(Exception) as exc_info:
            support_ops.query_users_list(limit=101)
        
        assert "每页条数必须在1-100之间" in str(exc_info.value)