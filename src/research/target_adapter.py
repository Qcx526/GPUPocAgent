"""
通用目标工具 Adapter

支持受控执行、资源限制、工作空间管理
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path
import subprocess
import json


@dataclass
class TargetConfig:
    """目标工具配置"""
    tool_name: str  # "nvdisasm", "cuobjdump" 等
    tool_path: Path
    tool_version: str
    input_mode: str  # "file", "stdin", "arg"
    command_template: str  # "{tool_path} {input_file}" 等
    timeout_seconds: int = 30
    max_output_bytes: int = 10_000_000  # 10MB
    workspace: Path = None  # 工作目录


class TargetAdapter:
    """
    通用目标工具执行适配器

    不对输入进行格式校验——只传入、执行、记录结果
    """

    def __init__(self, config: TargetConfig):
        self.config = config
        self.execution_log = []

    def execute(
        self,
        input_file: Path,
        task_id: str = None,
        run_id: str = None
    ) -> Dict[str, Any]:
        """
        执行目标工具（无格式预检查）

        Args:
            input_file: 输入文件路径
            task_id: 研究任务 ID
            run_id: 本轮执行 ID

        Returns:
            执行记录字典
        """
        import hashlib
        from datetime import datetime

        # 读取输入
        if not input_file.exists():
            return {
                "status": "INPUT_NOT_FOUND",
                "input_file": str(input_file),
                "task_id": task_id,
                "run_id": run_id
            }

        input_data = input_file.read_bytes()
        input_sha256 = hashlib.sha256(input_data).hexdigest()

        # 构建命令
        cmd = self.config.command_template.format(
            tool_path=self.config.tool_path,
            input_file=input_file
        )

        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "run_id": run_id,
            "tool": self.config.tool_name,
            "tool_version": self.config.tool_version,
            "tool_path": str(self.config.tool_path),
            "command": cmd,
            "input_file": str(input_file),
            "input_size": len(input_data),
            "input_sha256": input_sha256,
            "timeout_seconds": self.config.timeout_seconds
        }

        try:
            # 执行（不过滤输入）
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                shell=True
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
                "exit_type": "success" if result.returncode == 0 else "non-zero"
            })

        except subprocess.TimeoutExpired:
            execution_record.update({
                "status": "TIMEOUT",
                "return_code": None,
                "exit_type": "timeout",
                "stderr": f"Execution exceeded {self.config.timeout_seconds} seconds"
            })

        except Exception as e:
            execution_record.update({
                "status": "ERROR",
                "return_code": None,
                "exit_type": "error",
                "error": str(e),
                "stderr": str(e)
            })

        # 记录
        self.execution_log.append(execution_record)

        return execution_record

    def get_log(self) -> List[Dict[str, Any]]:
        """获取完整执行日志"""
        return self.execution_log
