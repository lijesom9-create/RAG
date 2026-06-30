"""
Optimization Layer 测试
"""

import pytest
from app.optimization.versioned_config import VersionedConfig
from app.optimization.change_log import ChangeLog, ChangeLogEntry
from app.optimization.rollback import RollbackManager
from app.models.optimization_change import OptimizationChange


class TestVersionedConfig:
    """版本化配置测试"""

    def test_create_config(self):
        """创建配置"""
        config = VersionedConfig(config_id="test_config")
        assert config.config_id == "test_config"
        assert config.current_version == 0

    def test_update_config(self):
        """更新配置"""
        config = VersionedConfig(config_id="test_config")
        version = config.update("value1", "初始值")
        assert version == 1
        assert config.get_current() == "value1"

    def test_version_history(self):
        """版本历史"""
        config = VersionedConfig(config_id="test_config")
        config.update("v1", "版本1")
        config.update("v2", "版本2")
        config.update("v3", "版本3")
        assert config.current_version == 3
        assert len(config.versions) == 3

    def test_get_version(self):
        """获取指定版本"""
        config = VersionedConfig(config_id="test_config")
        config.update("v1", "版本1")
        config.update("v2", "版本2")
        assert config.get_version(1) == "v1"
        assert config.get_version(2) == "v2"

    def test_rollback(self):
        """回滚"""
        config = VersionedConfig(config_id="test_config")
        config.update("v1", "版本1")
        config.update("v2", "版本2")
        config.update("v3", "版本3")
        success = config.rollback(1)
        assert success
        assert config.get_current() == "v1"
        assert config.current_version == 4  # 回滚创建新版本

    def test_rollback_nonexistent(self):
        """回滚不存在的版本"""
        config = VersionedConfig(config_id="test_config")
        config.update("v1", "版本1")
        success = config.rollback(99)
        assert not success

    def test_serialization(self):
        """序列化/反序列化"""
        config = VersionedConfig(config_id="test_config")
        config.update("v1", "版本1")
        config.update("v2", "版本2")
        data = config.to_dict()
        restored = VersionedConfig.from_dict(data)
        assert restored.config_id == "test_config"
        assert restored.current_version == 2
        assert restored.get_current() == "v2"


class TestChangeLog:
    """变更日志测试"""

    def test_create_log(self):
        """创建日志"""
        log = ChangeLog()
        assert len(log.entries) == 0

    def test_log_change(self):
        """记录变更"""
        log = ChangeLog()
        change = OptimizationChange(
            insight_id="insight_1",
            target_type="prompt",
            target_id="system_prompt",
            old_version=1,
            new_version=2,
            reason="优化提示",
            applied=True,
        )
        entry = log.log_change(change)
        assert entry.change_id == change.id
        assert len(log.entries) == 1

    def test_get_pending_changes(self):
        """获取待审核变更"""
        log = ChangeLog()
        change1 = OptimizationChange(
            target_type="prompt",
            target_id="p1",
            old_version=1,
            new_version=2,
            applied=False,
        )
        change2 = OptimizationChange(
            target_type="prompt",
            target_id="p2",
            old_version=1,
            new_version=2,
            applied=True,
        )
        log.log_change(change1)
        log.log_change(change2)
        pending = log.get_pending_changes()
        assert len(pending) == 1

    def test_mark_applied(self):
        """标记为已应用"""
        log = ChangeLog()
        change = OptimizationChange(
            target_type="prompt",
            target_id="p1",
            old_version=1,
            new_version=2,
            applied=False,
        )
        log.log_change(change)
        assert log.mark_applied(change.id)
        assert len(log.get_applied_changes()) == 1

    def test_serialization(self):
        """序列化/反序列化"""
        log = ChangeLog()
        change = OptimizationChange(
            target_type="prompt",
            target_id="p1",
            old_version=1,
            new_version=2,
        )
        log.log_change(change)
        data = log.to_dict()
        restored = ChangeLog.from_dict(data)
        assert len(restored.entries) == 1


class TestRollbackManager:
    """回滚管理器测试"""

    def test_create_manager(self):
        """创建管理器"""
        log = ChangeLog()
        manager = RollbackManager(log)
        assert len(manager.configs) == 0

    def test_register_config(self):
        """注册配置"""
        log = ChangeLog()
        manager = RollbackManager(log)
        config = VersionedConfig(config_id="test")
        manager.register_config(config)
        assert "test" in manager.configs

    def test_rollback(self):
        """回滚操作"""
        log = ChangeLog()
        manager = RollbackManager(log)
        config = VersionedConfig(config_id="test")
        config.update("v1", "版本1")
        config.update("v2", "版本2")
        manager.register_config(config)

        success = manager.rollback("test", 1, "回滚原因")
        assert success
        assert config.get_current() == "v1"
        assert len(log.entries) == 1

    def test_rollback_nonexistent(self):
        """回滚不存在的配置"""
        log = ChangeLog()
        manager = RollbackManager(log)
        success = manager.rollback("nonexistent", 1)
        assert not success

    def test_get_available_versions(self):
        """获取可用版本"""
        log = ChangeLog()
        manager = RollbackManager(log)
        config = VersionedConfig(config_id="test")
        config.update("v1", "版本1")
        config.update("v2", "版本2")
        manager.register_config(config)
        versions = manager.get_available_versions("test")
        assert versions == [1, 2]
