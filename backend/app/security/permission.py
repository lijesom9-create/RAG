"""
Permission Manager - 权限管理器

管理工具调用权限，支持：
- 权限级别定义
- 权限检查
- 权限授予/撤销
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger


class PermissionLevel(Enum):
    """权限级别"""
    PUBLIC = "public"      # 公开，无需确认
    CONFIRM = "confirm"    # 需要用户确认
    RESTRICTED = "restricted"  # 受限，需要特殊权限
    DENIED = "denied"      # 禁止


@dataclass
class Permission:
    """权限定义"""
    tool_name: str
    level: PermissionLevel
    description: str = ""
    allowed_roles: List[str] = field(default_factory=list)
    max_calls_per_hour: int = 100
    require_confirmation: bool = False

    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "level": self.level.value,
            "description": self.description,
            "allowed_roles": self.allowed_roles,
            "max_calls_per_hour": self.max_calls_per_hour,
            "require_confirmation": self.require_confirmation,
        }


class PermissionManager:
    """
    权限管理器

    管理工具调用权限，防止危险操作。
    """

    def __init__(self):
        self.permissions: Dict[str, Permission] = {}
        self.call_counts: Dict[str, int] = {}  # 工具调用计数
        self.user_roles: Dict[str, List[str]] = {}  # 用户角色

    def register_permission(self, permission: Permission):
        """注册权限"""
        self.permissions[permission.tool_name] = permission
        logger.info(f"注册权限: {permission.tool_name} ({permission.level.value})")

    def set_user_roles(self, user_id: str, roles: List[str]):
        """设置用户角色"""
        self.user_roles[user_id] = roles

    async def check_permission(
        self,
        user_id: str,
        tool_name: str,
    ) -> Dict[str, Any]:
        """
        检查权限

        Args:
            user_id: 用户 ID
            tool_name: 工具名称

        Returns:
            Dict: 权限检查结果
        """
        # 获取权限配置
        permission = self.permissions.get(tool_name)
        if not permission:
            # 默认允许公开工具
            return {
                "allowed": True,
                "level": "public",
                "reason": "未配置权限，默认允许",
            }

        # 检查权限级别
        if permission.level == PermissionLevel.DENIED:
            return {
                "allowed": False,
                "level": "denied",
                "reason": f"工具 {tool_name} 已被禁止",
            }

        # 检查用户角色
        if permission.allowed_roles:
            user_roles = self.user_roles.get(user_id, [])
            if not any(role in permission.allowed_roles for role in user_roles):
                return {
                    "allowed": False,
                    "level": "restricted",
                    "reason": f"用户无权使用工具 {tool_name}",
                }

        # 检查调用频率
        call_key = f"{user_id}:{tool_name}"
        current_count = self.call_counts.get(call_key, 0)
        if current_count >= permission.max_calls_per_hour:
            return {
                "allowed": False,
                "level": "rate_limited",
                "reason": f"工具 {tool_name} 调用频率超限",
            }

        # 需要确认
        if permission.level == PermissionLevel.CONFIRM:
            return {
                "allowed": True,
                "level": "confirm",
                "reason": f"工具 {tool_name} 需要用户确认",
                "require_confirmation": True,
            }

        # 允许
        return {
            "allowed": True,
            "level": permission.level.value,
            "reason": "允许",
        }

    async def record_call(self, user_id: str, tool_name: str):
        """记录调用"""
        call_key = f"{user_id}:{tool_name}"
        self.call_counts[call_key] = self.call_counts.get(call_key, 0) + 1

    def get_permission(self, tool_name: str) -> Optional[Permission]:
        """获取权限配置"""
        return self.permissions.get(tool_name)

    def get_all_permissions(self) -> List[Dict]:
        """获取所有权限配置"""
        return [p.to_dict() for p in self.permissions.values()]

    def get_user_permissions(self, user_id: str) -> List[Dict]:
        """获取用户可用的权限"""
        user_roles = self.user_roles.get(user_id, [])
        available = []

        for permission in self.permissions.values():
            if permission.level == PermissionLevel.DENIED:
                continue

            if permission.allowed_roles:
                if any(role in permission.allowed_roles for role in user_roles):
                    available.append(permission.to_dict())
            else:
                available.append(permission.to_dict())

        return available


# 预定义权限
def create_default_permissions() -> List[Permission]:
    """创建默认权限"""
    return [
        # 公开工具
        Permission(
            tool_name="web_search",
            level=PermissionLevel.PUBLIC,
            description="搜索网页",
            max_calls_per_hour=100,
        ),
        Permission(
            tool_name="web_crawler",
            level=PermissionLevel.PUBLIC,
            description="爬取网页",
            max_calls_per_hour=50,
        ),
        Permission(
            tool_name="generate_text",
            level=PermissionLevel.PUBLIC,
            description="生成文本",
            max_calls_per_hour=100,
        ),
        Permission(
            tool_name="search_knowledge",
            level=PermissionLevel.PUBLIC,
            description="搜索知识库",
            max_calls_per_hour=100,
        ),

        # 需要确认的工具
        Permission(
            tool_name="file_write",
            level=PermissionLevel.CONFIRM,
            description="写入文件",
            max_calls_per_hour=20,
            require_confirmation=True,
        ),
        Permission(
            tool_name="file_delete",
            level=PermissionLevel.CONFIRM,
            description="删除文件",
            max_calls_per_hour=10,
            require_confirmation=True,
        ),

        # 受限工具
        Permission(
            tool_name="system_command",
            level=PermissionLevel.RESTRICTED,
            description="执行系统命令",
            allowed_roles=["admin"],
            max_calls_per_hour=10,
        ),

        # 禁止的工具
        Permission(
            tool_name="dangerous_operation",
            level=PermissionLevel.DENIED,
            description="危险操作",
        ),
    ]
