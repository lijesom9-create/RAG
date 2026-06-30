"""
MCP 客户端

实现 MCP 协议，支持：
- 连接 MCP 服务器
- 调用 MCP 工具
- 获取 MCP 资源
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger

from .types import MCPTool, MCPResource, MCPResult, MCPServerConfig


class MCPClient:
    """
    MCP 客户端

    支持连接多个 MCP 服务器，统一管理工具和资源。
    """

    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.connections: Dict[str, Any] = {}

    async def add_server(self, config: MCPServerConfig) -> bool:
        """
        添加 MCP 服务器

        Args:
            config: 服务器配置

        Returns:
            bool: 是否成功
        """
        try:
            self.servers[config.id] = config

            # 连接服务器
            if config.transport == "stdio":
                await self._connect_stdio(config)
            elif config.transport == "sse":
                await self._connect_sse(config)
            elif config.transport == "http":
                await self._connect_http(config)
            else:
                logger.warning(f"不支持的传输方式: {config.transport}")
                return False

            # 获取工具列表
            await self._discover_tools(config.id)

            logger.info(f"添加 MCP 服务器: {config.name} ({config.id})")
            return True

        except Exception as e:
            logger.error(f"添加 MCP 服务器失败: {e}")
            return False

    async def remove_server(self, server_id: str) -> bool:
        """
        移除 MCP 服务器

        Args:
            server_id: 服务器 ID

        Returns:
            bool: 是否成功
        """
        try:
            # 断开连接
            if server_id in self.connections:
                await self._disconnect(server_id)

            # 移除工具
            self.tools = {
                k: v for k, v in self.tools.items()
                if v.server_id != server_id
            }

            # 移除服务器
            del self.servers[server_id]

            logger.info(f"移除 MCP 服务器: {server_id}")
            return True

        except Exception as e:
            logger.error(f"移除 MCP 服务器失败: {e}")
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
        # 查找工具
        tool = self.tools.get(tool_name)
        if not tool:
            return MCPResult(
                success=False,
                error=f"工具不存在: {tool_name}",
            )

        # 检查服务器连接
        if tool.server_id not in self.connections:
            return MCPResult(
                success=False,
                error=f"服务器未连接: {tool.server_id}",
            )

        try:
            # 调用工具
            result = await self._call_tool_on_server(
                server_id=tool.server_id,
                tool_name=tool_name,
                arguments=arguments,
            )

            logger.info(f"调用 MCP 工具: {tool_name}")
            return result

        except Exception as e:
            logger.error(f"调用 MCP 工具失败: {e}")
            return MCPResult(
                success=False,
                error=str(e),
            )

    async def get_resource(
        self,
        uri: str,
    ) -> MCPResult:
        """
        获取 MCP 资源

        Args:
            uri: 资源 URI

        Returns:
            MCPResult: 资源内容
        """
        # 查找资源
        resource = self.resources.get(uri)
        if not resource:
            return MCPResult(
                success=False,
                error=f"资源不存在: {uri}",
            )

        try:
            # 获取资源
            result = await self._get_resource_from_server(
                server_id=resource.server_id if hasattr(resource, 'server_id') else "",
                uri=uri,
            )

            logger.info(f"获取 MCP 资源: {uri}")
            return result

        except Exception as e:
            logger.error(f"获取 MCP 资源失败: {e}")
            return MCPResult(
                success=False,
                error=str(e),
            )

    def get_all_tools(self) -> List[MCPTool]:
        """获取所有工具"""
        return list(self.tools.values())

    def get_tools_schema(self) -> List[Dict]:
        """获取所有工具的 Schema（用于 Function Calling）"""
        schemas = []
        for tool in self.tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            schemas.append(schema)
        return schemas

    def get_server_status(self) -> Dict[str, Dict]:
        """获取服务器状态"""
        status = {}
        for server_id, config in self.servers.items():
            status[server_id] = {
                "name": config.name,
                "transport": config.transport,
                "connected": server_id in self.connections,
                "tools_count": sum(
                    1 for t in self.tools.values()
                    if t.server_id == server_id
                ),
            }
        return status

    # ========== 内部方法 ==========

    async def _connect_stdio(self, config: MCPServerConfig):
        """连接 stdio 服务器"""
        # TODO: 实现 stdio 连接
        logger.info(f"连接 stdio 服务器: {config.name}")
        self.connections[config.id] = {"type": "stdio"}

    async def _connect_sse(self, config: MCPServerConfig):
        """连接 SSE 服务器"""
        # TODO: 实现 SSE 连接
        logger.info(f"连接 SSE 服务器: {config.name}")
        self.connections[config.id] = {"type": "sse"}

    async def _connect_http(self, config: MCPServerConfig):
        """连接 HTTP 服务器"""
        # TODO: 实现 HTTP 连接
        logger.info(f"连接 HTTP 服务器: {config.name}")
        self.connections[config.id] = {"type": "http"}

    async def _disconnect(self, server_id: str):
        """断开连接"""
        if server_id in self.connections:
            del self.connections[server_id]
            logger.info(f"断开连接: {server_id}")

    async def _discover_tools(self, server_id: str):
        """发现服务器工具"""
        # TODO: 从服务器获取工具列表
        logger.info(f"发现工具: {server_id}")

    async def _call_tool_on_server(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPResult:
        """在服务器上调用工具"""
        # TODO: 实现实际的工具调用
        return MCPResult(
            success=True,
            data={"message": f"工具 {tool_name} 调用成功（模拟）"},
        )

    async def _get_resource_from_server(
        self,
        server_id: str,
        uri: str,
    ) -> MCPResult:
        """从服务器获取资源"""
        # TODO: 实现实际的资源获取
        return MCPResult(
            success=True,
            data={"content": f"资源 {uri} 内容（模拟）"},
        )
