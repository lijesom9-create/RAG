"""
MCP 服务器

实现 MCP 协议的服务端，用于：
- 提供工具
- 提供资源
- 处理请求
"""

import asyncio
import json
from typing import Dict, List, Any, Callable
from loguru import logger

from .types import MCPTool, MCPResource, MCPResult


class MCPServer:
    """
    MCP 服务器

    提供工具和资源，处理客户端请求。
    """

    def __init__(self, server_id: str, name: str):
        self.server_id = server_id
        self.name = name
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.tool_handlers: Dict[str, Callable] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
    ):
        """
        注册工具

        Args:
            name: 工具名称
            description: 工具描述
            input_schema: 输入 Schema
            handler: 处理函数
        """
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            server_id=self.server_id,
        )
        self.tools[name] = tool
        self.tool_handlers[name] = handler
        logger.info(f"注册工具: {name}")

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "",
    ):
        """
        注册资源

        Args:
            uri: 资源 URI
            name: 资源名称
            description: 资源描述
            mime_type: MIME 类型
        """
        resource = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
        )
        self.resources[uri] = resource
        logger.info(f"注册资源: {uri}")

    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPResult:
        """
        处理工具调用

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

        # 查找处理函数
        handler = self.tool_handlers.get(tool_name)
        if not handler:
            return MCPResult(
                success=False,
                error=f"处理函数不存在: {tool_name}",
            )

        try:
            # 调用处理函数
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            return MCPResult(
                success=True,
                data=result,
            )

        except Exception as e:
            logger.error(f"处理工具调用失败: {e}")
            return MCPResult(
                success=False,
                error=str(e),
            )

    async def handle_resource_request(
        self,
        uri: str,
    ) -> MCPResult:
        """
        处理资源请求

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

        # TODO: 实现资源获取
        return MCPResult(
            success=True,
            data={"content": f"资源 {uri} 内容（模拟）"},
        )

    def get_tools_list(self) -> List[Dict]:
        """获取工具列表"""
        return [tool.to_dict() for tool in self.tools.values()]

    def get_resources_list(self) -> List[Dict]:
        """获取资源列表"""
        return [resource.to_dict() for resource in self.resources.values()]


# ========== 预定义 MCP 服务器 ==========

def create_example_server() -> MCPServer:
    """创建示例 MCP 服务器"""
    server = MCPServer(
        server_id="example",
        name="示例服务器",
    )

    # 注册工具
    server.register_tool(
        name="get_weather",
        description="获取天气信息",
        input_schema={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称",
                },
            },
            "required": ["city"],
        },
        handler=lambda city: {"weather": "晴天", "temperature": 25},
    )

    server.register_tool(
        name="search_web",
        description="搜索网页",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
            },
            "required": ["query"],
        },
        handler=lambda query: {"results": [f"搜索结果: {query}"]},
    )

    # 注册资源
    server.register_resource(
        uri="example://docs/readme",
        name="README",
        description="示例文档",
        mime_type="text/markdown",
    )

    return server
