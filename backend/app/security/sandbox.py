"""
Sandbox - 沙箱

提供安全的执行环境，支持：
- 代码执行沙箱
- 文件操作沙箱
- 网络访问沙箱
"""

import asyncio
import tempfile
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class SandboxConfig:
    """沙箱配置"""
    max_execution_time: int = 30  # 最大执行时间（秒）
    max_memory_mb: int = 256  # 最大内存（MB）
    allowed_modules: List[str] = field(default_factory=lambda: [
        "math", "json", "re", "datetime", "collections",
    ])
    blocked_modules: List[str] = field(default_factory=lambda: [
        "os", "sys", "subprocess", "shutil", "socket",
    ])
    allow_file_access: bool = False
    allow_network_access: bool = False
    temp_dir: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "max_execution_time": self.max_execution_time,
            "max_memory_mb": self.max_memory_mb,
            "allowed_modules": self.allowed_modules,
            "blocked_modules": self.blocked_modules,
            "allow_file_access": self.allow_file_access,
            "allow_network_access": self.allow_network_access,
        }


class Sandbox:
    """
    沙箱

    提供安全的执行环境。
    """

    def __init__(self, config: SandboxConfig = None):
        self.config = config or SandboxConfig()
        self.temp_dir = self.config.temp_dir or tempfile.mkdtemp()

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = None,
    ) -> Dict[str, Any]:
        """
        执行代码

        Args:
            code: 代码内容
            language: 编程语言
            timeout: 超时时间

        Returns:
            Dict: 执行结果
        """
        timeout = timeout or self.config.max_execution_time

        try:
            if language == "python":
                return await self._execute_python(code, timeout)
            else:
                return {
                    "success": False,
                    "error": f"不支持的语言: {language}",
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"执行超时 ({timeout}秒)",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def _execute_python(self, code: str, timeout: int) -> Dict[str, Any]:
        """执行 Python 代码"""
        # 安全检查
        if not self._check_code_safety(code):
            return {
                "success": False,
                "error": "代码包含不安全的操作",
            }

        # 创建临时文件
        temp_file = os.path.join(self.temp_dir, "script.py")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            # 执行代码
            proc = await asyncio.create_subprocess_exec(
                "python", temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "return_code": proc.returncode,
            }

        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _check_code_safety(self, code: str) -> bool:
        """检查代码安全性"""
        # 检查禁止的模块
        for module in self.config.blocked_modules:
            if f"import {module}" in code or f"from {module}" in code:
                logger.warning(f"代码包含禁止的模块: {module}")
                return False

        # 检查危险操作
        dangerous_patterns = [
            "exec(",
            "eval(",
            "__import__",
            "open(",
            "os.system",
            "subprocess",
            "shutil.rmtree",
        ]

        for pattern in dangerous_patterns:
            if pattern in code:
                logger.warning(f"代码包含危险操作: {pattern}")
                return False

        return True

    async def write_file(
        self,
        filename: str,
        content: str,
    ) -> Dict[str, Any]:
        """写入文件（沙箱内）"""
        if not self.config.allow_file_access:
            return {
                "success": False,
                "error": "沙箱不允许文件访问",
            }

        filepath = os.path.join(self.temp_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "filepath": filepath,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def read_file(
        self,
        filename: str,
    ) -> Dict[str, Any]:
        """读取文件（沙箱内）"""
        if not self.config.allow_file_access:
            return {
                "success": False,
                "error": "沙箱不允许文件访问",
            }

        filepath = os.path.join(self.temp_dir, filename)

        try:
            if not os.path.exists(filepath):
                return {
                    "success": False,
                    "error": f"文件不存在: {filename}",
                }

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            return {
                "success": True,
                "content": content,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def cleanup(self):
        """清理沙箱"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"沙箱已清理: {self.temp_dir}")
