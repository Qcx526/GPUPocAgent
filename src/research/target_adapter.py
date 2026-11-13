"""
通用目标工具 Adapter

受控执行、路径校验、参数安全
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path
import subprocess
import json
import shlex


@dataclass
class TargetConfig:
    """目标工具配置"""
    tool_name: str
    tool_path: Path
    tool_version: str
    input_mode: str  # "file", "stdin"
    command_template: str  # "{tool_path} {input_file}" 等
    timeout_seconds: int = 30
    max_output_bytes: int = 10_000_000
    workspace: Path = None

    def validate(self) -> tuple[bool, str]:
        """验证配置安全性"""
        if not self.tool_path.exists():
            return False, f"Tool not found: {self.tool_path}"
        if not self.tool_path.is_file():
            return False, f"Tool is not a file: {self.tool_path}"
        return True, "OK"


class TargetAdapter:
    """
    通用目标工具执行适配器

    安全参数执行 (shell=False)
    明确区分启动失败 vs 正常拒绝
    """

    def __init__(self, config: TargetConfig):
        self.config = config
        is_valid, msg = config.validate()
        if not is_valid:
            raise ValueError(f"Invalid target config: {msg}")

        self.execution_log = []

    def execute(
        self,
        input_file: Path,
        task_id: str = None,
        run_id: str = None
    ) -> Dict[str, Any]:
        """
        执行目标工具（安全参数列表）

        Args:
            input_file: 输入文件路径
            task_id: 研究任务 ID
            run_id: 本轮执行 ID

        Returns:
            执行记录字典
        """
        import hashlib
        from datetime import datetime

        if not input_file.exists():
            return {
                "status": "INPUT_NOT_FOUND",
                "input_file": str(input_file),
                "task_id": task_id,
                "run_id": run_id,
                "exit_type": "error"
            }

        input_data = input_file.read_bytes()
        input_sha256 = hashlib.sha256(input_data).hexdigest()

        # 安全构建命令参数列表（不使用 shell 格式化）
        cmd_args = self._build_command_args(input_file)

        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "run_id": run_id,
            "tool": self.config.tool_name,
            "tool_version": self.config.tool_version,
            "tool_path": str(self.config.tool_path),
            "command_args": cmd_args,  # 参数列表，非字符串
            "input_file": str(input_file),
            "input_size": len(input_data),
            "input_sha256": input_sha256,
            "timeout_seconds": self.config.timeout_seconds
        }

        try:
            # 安全执行：参数列表 + shell=False
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                shell=False  # 关键：不通过 shell 解析
            )

            # 截断超长输出
            stdout = result.stdout
            stderr = result.stderr
            if len(stdout) > self.config.max_output_bytes:
                stdout = stdout[:self.config.max_output_bytes] + f"\n... [truncated, total {len(result.stdout)} bytes]"
            if len(stderr) > self.config.max_output_bytes:
                stderr = stderr[:self.config.max_output_bytes] + f"\n... [truncated, total {len(result.stderr)} bytes]"

            execution_record.update({
                "status": "EXECUTED",
                "return_code": result.returncode,
                "stdout_length": len(result.stdout),
                "stderr_length": len(result.stderr),
                "stdout": stdout,
                "stderr": stderr,
                "exit_type": self._classify_exit_type(result.returncode, result.stderr)
            })

        except subprocess.TimeoutExpired:
            execution_record.update({
                "status": "TIMEOUT",
                "return_code": None,
                "exit_type": "timeout",
                "stderr": f"Execution exceeded {self.config.timeout_seconds} seconds"
            })

        except FileNotFoundError as e:
            execution_record.update({
                "status": "STARTUP_FAILED",
                "return_code": None,
                "exit_type": "startup_error",
                "error": f"Tool not found or not executable: {e}"
            })

        except Exception as e:
            execution_record.update({
                "status": "ERROR",
                "return_code": None,
                "exit_type": "error",
                "error": str(e)
            })

        self.execution_log.append(execution_record)
        return execution_record

    def _build_command_args(self, input_file: Path) -> List[str]:
        """
        安全构建命令参数列表

        Args:
            input_file: 输入文件路径

        Returns:
            参数列表 (适合 subprocess 的 args 参数)
        """
        # 构建参数列表（避免字符串解析）
        return [
            str(self.config.tool_path),
            str(input_file)
        ]

    def _classify_exit_type(self, return_code: int, stderr: str) -> str:
        """
        分类进程退出类型

        Args:
            return_code: 返回码
            stderr: 标准错误输出

        Returns:
            分类: "success", "rejection", "abnormal", "unknown"
        """
        if return_code == 0:
            return "success"

        # 非零退出
        if return_code > 0:
            # Windows 进程返回码 > 0 通常表示拒绝或错误
            # 需要根据工具类型判断
            if "nvdisasm" in self.config.tool_name.lower():
                # nvdisasm: 非零通常是输入格式拒绝
                return "rejection"
            return "rejection"

        # 负数返回码或信号 (Unix-like)
        if return_code < 0:
            return "abnormal"

        return "unknown"

    def get_log(self) -> List[Dict[str, Any]]:
        """获取完整执行日志"""
        return self.execution_log
