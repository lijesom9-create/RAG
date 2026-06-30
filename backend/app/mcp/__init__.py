"""
MCP (Model Context Protocol) 模块

标准化工具调用协议，支持：
- 连接 MCP 服务器
- 调用 MCP 工具
- 获取 MCP 资源
"""

from .client import MCPClient
from .server import MCPServer
from .types import MCPTool, MCPResource, MCPResult

__all__ = [
    "MCPClient",
    "MCPServer",
    "MCPTool",
    "MCPResource",
    "MCPResult",
]
