"""
MCP 管理器

统一管理 MCP 客户端和服务器，提供：
- 服务器管理
- 工具管理
- 统一调用接口
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from .client import MCPClient
from .server import MCPServer
from .types import MCPTool, MCPResource, MCPResult, MCPServerConfig


class MCPManager:
    """
    MCP 管理器

    统一管理 MCP 客户端和服务器。
    """

    def __init__(self):
        self.client = MCPClient()
        self.servers: Dict[str, MCPServer] = {}

    async def add_server_config(self, config: MCPServerConfig) -> bool:
        """
        添加外部 MCP 服务器

        Args:
            config: 服务器配置

        Returns:
            bool: 是否成功
        """
        return await self.client.add_server(config)

    def add_local_server(self, server: MCPServer) -> bool:
        """
        添加本地 MCP 服务器

        Args:
            server: 服务器实例

        Returns:
            bool: 是否成功
        """
        try:
            self.servers[server.server_id] = server

            # 将服务器工具注册到客户端
            for tool in server.tools.values():
                self.client.tools[tool.name] = tool

            logger.info(f"添加本地 MCP 服务器: {server.name}")
            return True

        except Exception as e:
            logger.error(f"添加本地 MCP 服务器失败: {e}")
            return False

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPResult:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            MCPResult: 调用结果
        """
        # 先查找本地服务器
        for server in self.servers.values():
            if tool_name in server.tools:
                return await server.handle_tool_call(tool_name, arguments)

        # 再查找外部服务器
        return await self.client.call_tool(tool_name, arguments)

    def get_all_tools(self) -> List[MCPTool]:
        """获取所有工具"""
        return self.client.get_all_tools()

    def get_tools_schema(self) -> List[Dict]:
        """获取所有工具的 Schema"""
        return self.client.get_tools_schema()

    def get_server_status(self) -> Dict[str, Dict]:
        """获取服务器状态"""
        status = self.client.get_server_status()

        # 添加本地服务器状态
        for server_id, server in self.servers.items():
            status[server_id] = {
                "name": server.name,
                "transport": "local",
                "connected": True,
                "tools_count": len(server.tools),
            }

        return status

    async def start(self):
        """启动管理器"""
        logger.info("MCP 管理器启动")

    async def stop(self):
        """停止管理器"""
        # 断开所有外部连接
        for server_id in list(self.client.servers.keys()):
            await self.client.remove_server(server_id)

        logger.info("MCP 管理器停止")


# 全局 MCP 管理器实例
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """获取全局 MCP 管理器"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
