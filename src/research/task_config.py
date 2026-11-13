"""
研究任务配置

支持通过配置文件切换研究目标，无需修改源码
"""

import json
from pathlib import Path
from typing import Dict, Any


class ResearchTaskConfig:
    """研究任务配置"""

    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict

    @property
    def task_name(self) -> str:
        return self.config.get("task_name", "unknown")

    @property
    def description(self) -> str:
        return self.config.get("description", "")

    @property
    def target_tool(self) -> str:
        return self.config.get("target", {}).get("tool_name", "")

    @property
    def target_version(self) -> str:
        return self.config.get("target", {}).get("tool_version", "")

    @property
    def seed_file(self) -> str:
        return self.config.get("seed_file", "")

    @property
    def workspace(self) -> str:
        return self.config.get("workspace", "")

    @property
    def exploration_rounds(self) -> int:
        return self.config.get("exploration", {}).get("rounds", 1)

    @property
    def candidates_per_round(self) -> int:
        return self.config.get("exploration", {}).get("candidates_per_round", 20)

    @property
    def mutation_types(self) -> list:
        return self.config.get("exploration", {}).get("mutation_types", [])

    @property
    def target_config_dict(self) -> Dict[str, Any]:
        return self.config.get("target", {})

    def to_dict(self) -> Dict[str, Any]:
        return self.config


class ResearchTaskConfigManager:
    """研究任务配置管理器"""

    CONFIG_DIR = Path("F:/qcx/code/GPUPocAgent/configs/research_tasks")

    @staticmethod
    def ensure_config_dir():
        """确保配置目录存在"""
        ResearchTaskConfigManager.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def load_task_config(task_name: str) -> ResearchTaskConfig:
        """
        加载研究任务配置

        Args:
            task_name: 任务名称 (对应 configs/research_tasks/{task_name}.json)

        Returns:
            ResearchTaskConfig
        """
        config_file = ResearchTaskConfigManager.CONFIG_DIR / f"{task_name}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Task config not found: {config_file}")

        config_dict = json.loads(config_file.read_text(encoding='utf-8'))
        return ResearchTaskConfig(config_dict)

    @staticmethod
    def save_task_config(task_name: str, config: Dict[str, Any]):
        """保存研究任务配置"""
        ResearchTaskConfigManager.ensure_config_dir()
        config_file = ResearchTaskConfigManager.CONFIG_DIR / f"{task_name}.json"
        config_file.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        return config_file

    @staticmethod
    def list_available_tasks() -> list:
        """列出可用的任务配置"""
        ResearchTaskConfigManager.ensure_config_dir()
        return [f.stem for f in ResearchTaskConfigManager.CONFIG_DIR.glob("*.json")]
