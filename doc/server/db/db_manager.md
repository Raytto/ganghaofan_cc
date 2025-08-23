# 数据库管理器

数据库连接和事务管理的核心组件，为所有业务操作提供统一的数据库访问接口。

## 设计原则

1. **连接管理**：统一管理DuckDB数据库连接的生命周期
2. **事务安全**：提供事务操作的原子性保障
3. **错误处理**：完整的异常处理和回滚机制
4. **资源管理**：确保数据库连接的正确释放
5. **简单易用**：为业务层提供简洁的操作接口

## DatabaseManager类定义

```python
import duckdb
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from contextlib import contextmanager

class DatabaseManager:
    """
    数据库管理器
    
    负责DuckDB数据库连接管理、事务处理和基础操作
    """
    
    def __init__(self, db_path: str, auto_connect: bool = False):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
            auto_connect: 是否自动连接数据库
        """
        self.db_path = db_path
        self.conn = None
        self._is_connected = False
        
        # 配置日志
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if auto_connect:
            self.connect()
    
    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        建立数据库连接
        
        Returns:
            DuckDB连接对象
        
        Raises:
            ConnectionError: 连接失败时抛出异常
        """
        try:
            if self.conn is not None:
                self.logger.warning("数据库连接已存在，先关闭现有连接")
                self.close()
            
            self.conn = duckdb.connect(self.db_path)
            self._is_connected = True
            self.logger.info(f"成功连接到数据库: {self.db_path}")
            
            # 设置DuckDB优化参数
            self._configure_database()
            
            return self.conn
            
        except Exception as e:
            self.logger.error(f"连接数据库失败: {str(e)}")
            raise ConnectionError(f"无法连接到数据库 {self.db_path}: {str(e)}")
    
    def close(self):
        """
        关闭数据库连接
        """
        if self.conn is not None:
            try:
                self.conn.close()
                self.logger.info("数据库连接已关闭")
            except Exception as e:
                self.logger.error(f"关闭数据库连接时发生错误: {str(e)}")
            finally:
                self.conn = None
                self._is_connected = False
    
    def _configure_database(self):
        """
        配置DuckDB优化参数
        """
        try:
            # 设置内存限制和并发参数
            optimizations = [
                "PRAGMA memory_limit='1GB'",
                "PRAGMA threads=4", 
                "PRAGMA enable_progress_bar=false",
                "PRAGMA enable_profiling=false"
            ]
            
            for opt in optimizations:
                self.conn.execute(opt)
                
            self.logger.debug("数据库优化参数配置完成")
            
        except Exception as e:
            self.logger.warning(f"配置数据库参数时出现警告: {str(e)}")
    
    def is_connected(self) -> bool:
        """
        检查数据库连接状态
        
        Returns:
            连接状态布尔值
        """
        return self._is_connected and self.conn is not None
    
    def ensure_connected(self):
        """
        确保数据库连接可用
        
        Raises:
            ConnectionError: 连接不可用时抛出异常
        """
        if not self.is_connected():
            raise ConnectionError("数据库未连接，请先调用connect()方法")
    
    def execute_transaction(self, operations: List[Callable]) -> List[Any]:
        """
        串行执行事务操作
        
        Args:
            operations: 操作函数列表，每个函数返回操作结果
        
        Returns:
            所有操作结果的列表
            
        Raises:
            ConnectionError: 数据库未连接
            Exception: 事务执行失败时抛出原始异常
        """
        self.ensure_connected()
        
        if not operations:
            self.logger.warning("事务操作列表为空")
            return []
        
        results = []
        transaction_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        try:
            self.logger.debug(f"开始事务 {transaction_id}，包含 {len(operations)} 个操作")
            self.conn.begin()
            
            for i, operation in enumerate(operations):
                self.logger.debug(f"执行事务 {transaction_id} 中的操作 {i+1}/{len(operations)}")
                result = operation()
                results.append(result)
            
            self.conn.commit()
            self.logger.info(f"事务 {transaction_id} 提交成功")
            
            return results
            
        except Exception as e:
            self.logger.error(f"事务 {transaction_id} 执行失败: {str(e)}")
            try:
                self.conn.rollback()
                self.logger.info(f"事务 {transaction_id} 已回滚")
            except Exception as rollback_error:
                self.logger.error(f"事务回滚失败: {str(rollback_error)}")
            
            raise e
    
    def execute_single(self, query: str, params: List = None) -> Any:
        """
        执行单个SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
        
        Returns:
            查询结果
        """
        self.ensure_connected()
        
        try:
            if params:
                return self.conn.execute(query, params)
            else:
                return self.conn.execute(query)
                
        except Exception as e:
            self.logger.error(f"执行SQL查询失败: {query[:100]}..., 错误: {str(e)}")
            raise e
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        Usage:
            with db_manager.transaction():
                # 执行数据库操作
                db_manager.conn.execute("INSERT ...")
                db_manager.conn.execute("UPDATE ...")
        """
        self.ensure_connected()
        
        try:
            self.conn.begin()
            self.logger.debug("手动事务开始")
            yield self.conn
            self.conn.commit()
            self.logger.debug("手动事务提交成功")
        except Exception as e:
            self.logger.error(f"手动事务执行失败: {str(e)}")
            try:
                self.conn.rollback()
                self.logger.debug("手动事务已回滚")
            except Exception as rollback_error:
                self.logger.error(f"手动事务回滚失败: {str(rollback_error)}")
            raise e
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取数据表信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        self.ensure_connected()
        
        try:
            # 获取表结构
            columns_result = self.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            
            if not columns_result:
                raise ValueError(f"表 {table_name} 不存在")
            
            columns = []
            for col in columns_result:
                columns.append({
                    'name': col[1],
                    'type': col[2], 
                    'not_null': bool(col[3]),
                    'default_value': col[4],
                    'primary_key': bool(col[5])
                })
            
            # 获取记录数
            count_result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            record_count = count_result[0] if count_result else 0
            
            return {
                'table_name': table_name,
                'columns': columns,
                'record_count': record_count
            }
            
        except Exception as e:
            self.logger.error(f"获取表 {table_name} 信息失败: {str(e)}")
            raise e
    
    def vacuum(self):
        """
        清理和优化数据库
        """
        self.ensure_connected()
        
        try:
            self.logger.info("开始数据库清理优化")
            self.conn.execute("VACUUM")
            self.logger.info("数据库清理优化完成")
        except Exception as e:
            self.logger.error(f"数据库清理优化失败: {str(e)}")
            raise e
    
    def backup(self, backup_path: str):
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径
        """
        self.ensure_connected()
        
        try:
            self.logger.info(f"开始备份数据库到: {backup_path}")
            self.conn.execute(f"EXPORT DATABASE '{backup_path}'")
            self.logger.info("数据库备份完成")
        except Exception as e:
            self.logger.error(f"数据库备份失败: {str(e)}")
            raise e
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        if not self.is_connected():
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.close()
    
    def __del__(self):
        """
        析构函数，确保连接被正确关闭
        """
        if self.is_connected():
            self.close()
```

## 使用示例

### 基础使用

```python
# 1. 基本连接管理
db_manager = DatabaseManager("gang_hao_fan.db")
db_manager.connect()

try:
    # 执行查询
    result = db_manager.execute_single(
        "SELECT * FROM users WHERE user_id = ?", 
        [1]
    )
    
finally:
    db_manager.close()
```

### 上下文管理器使用

```python
# 2. 使用上下文管理器（推荐）
with DatabaseManager("gang_hao_fan.db") as db:
    result = db.execute_single(
        "SELECT COUNT(*) FROM meals WHERE status = ?", 
        ['published']
    )
    print(f"已发布餐次数量: {result.fetchone()[0]}")
```

### 事务操作

```python
# 3. 使用事务操作列表
def create_user_operation():
    return db.execute_single("""
        INSERT INTO users (open_id, wechat_name, balance_cents) 
        VALUES (?, ?, ?)
        RETURNING user_id
    """, ["wx123", "测试用户", 0])

def create_ledger_operation():
    return db.execute_single("""
        INSERT INTO ledger (transaction_no, user_id, type, direction, amount_cents)
        VALUES (?, ?, ?, ?, ?)
    """, ["TXN20241201000001", 1, "recharge", "in", 1000])

with DatabaseManager("gang_hao_fan.db") as db:
    results = db.execute_transaction([
        create_user_operation,
        create_ledger_operation
    ])
```

### 手动事务控制

```python
# 4. 使用手动事务上下文管理器
with DatabaseManager("gang_hao_fan.db") as db:
    with db.transaction():
        # 在事务中执行多个操作
        user_result = db.conn.execute("""
            INSERT INTO users (open_id, wechat_name) 
            VALUES (?, ?) RETURNING user_id
        """, ["wx456", "另一个用户"])
        
        user_id = user_result.fetchone()[0]
        
        db.conn.execute("""
            INSERT INTO ledger (user_id, type, amount_cents) 
            VALUES (?, ?, ?)
        """, [user_id, "recharge", 2000])
```

### 数据库管理功能

```python
# 5. 数据库管理和维护
with DatabaseManager("gang_hao_fan.db") as db:
    # 获取表信息
    table_info = db.get_table_info("users")
    print(f"用户表结构: {table_info}")
    
    # 数据库优化
    db.vacuum()
    
    # 数据库备份
    db.backup("/backup/gang_hao_fan_backup.sql")
```

## 集成示例

### 与业务操作类集成

```python
from db_manager import DatabaseManager
from core_operations import CoreOperations
from query_operations import QueryOperations
from supporting_operations import SupportingOperations

# 统一初始化
db_manager = DatabaseManager("gang_hao_fan.db", auto_connect=True)

# 初始化各业务操作类
core_ops = CoreOperations(db_manager)
query_ops = QueryOperations(db_manager)
support_ops = SupportingOperations(db_manager)

try:
    # 使用各种业务操作
    user_result = support_ops.register_user("wx789", "新用户")
    meal_result = core_ops.admin_publish_meal(1, "2024-12-01", "lunch", "今日特餐", 1500, {}, 50)
    meals_list = query_ops.query_meals_by_date_range("2024-12-01", "2024-12-07")
    
finally:
    db_manager.close()
```

## 配置选项

### 数据库优化参数

```python
# 自定义优化配置
class CustomDatabaseManager(DatabaseManager):
    def _configure_database(self):
        """自定义数据库配置"""
        optimizations = [
            "PRAGMA memory_limit='2GB'",      # 更大内存限制
            "PRAGMA threads=8",               # 更多线程
            "PRAGMA checkpoint_threshold='1GB'",  # 检查点阈值
            "PRAGMA wal_autocheckpoint=1000"   # WAL自动检查点
        ]
        
        for opt in optimizations:
            self.conn.execute(opt)
```

### 日志配置

```python
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 使用时自动显示详细日志
db_manager = DatabaseManager("gang_hao_fan.db")
```

## 错误处理

### 常见异常处理

```python
from db_manager import DatabaseManager

try:
    with DatabaseManager("gang_hao_fan.db") as db:
        result = db.execute_single("SELECT * FROM non_existent_table")
        
except ConnectionError as e:
    print(f"数据库连接错误: {e}")
    
except Exception as e:
    print(f"数据库操作错误: {e}")
```

## 注意事项

1. **连接管理**：使用上下文管理器确保连接正确释放
2. **事务安全**：复杂操作使用事务保证数据一致性  
3. **错误处理**：捕获并处理数据库相关异常
4. **性能优化**：合理配置DuckDB参数和使用批量操作
5. **日志记录**：启用日志记录便于问题诊断
6. **备份策略**：定期备份重要数据
7. **资源管理**：避免长时间持有数据库连接