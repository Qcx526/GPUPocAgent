"""
M3: GPU CVE 自主研究框架

核心职责：
1. CVE 情报采集 (Tavily + 公开资料)
2. 环境和版本可用性验证
3. 漏洞机制假设建立
4. 候选输入生成
5. 受控工具实验
6. 证据收集与差分分析
7. 客观结论输出
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

from src.config import get_config


@dataclass
class EvidenceLevel:
    """研究证据等级"""
    INFORMATION_COLLECTED = "INFORMATION_COLLECTED"
    CANDIDATE_GENERATED = "CANDIDATE_GENERATED"
    EXECUTED = "EXECUTED"
    ANOMALY_OBSERVED = "ANOMALY_OBSERVED"
    DIFFERENTIAL_SUPPORTED = "DIFFERENTIAL_SUPPORTED"
    MECHANISM_SUPPORTED = "MECHANISM_SUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"


@dataclass
class CVEResearchTask:
    """CVE 研究任务"""
    cve_id: str
    task_id: str
    run_id: str
    created_at: str
    evidence_level: str = EvidenceLevel.INFORMATION_COLLECTED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CVEResearchRunner:
    """CVE 自主研究执行器"""

    def __init__(self, cve_id: str):
        self.cve_id = cve_id
        self.config = get_config()
        self.task_id = f"cve_research_{cve_id.lower()}"

        # 生成 run_id 并初始化研究目录
        from src.config import generate_run_id
        self.run_id = generate_run_id()
        self.run_dir = self.config.get_run_directory(self.task_id, self.run_id)

        # 创建子目录
        self.evidence_dir = self.run_dir / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir = self.run_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 研究任务元数据
        self.task = CVEResearchTask(
            cve_id=cve_id,
            task_id=self.task_id,
            run_id=self.run_id,
            created_at=datetime.now().isoformat()
        )

        # 保存元数据
        self._save_metadata()

    def _save_metadata(self):
        """保存任务元数据"""
        metadata_file = self.run_dir / "metadata.json"
        metadata_file.write_text(
            json.dumps(self.task.to_dict(), indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def log_evidence(self, evidence_type: str, content: str, source: Optional[str] = None):
        """记录证据"""
        timestamp = datetime.now().isoformat().replace(':', '-')
        filename = f"{evidence_type}_{timestamp}.txt"
        filepath = self.evidence_dir / filename

        output = f"=== {evidence_type} ===\n"
        if source:
            output += f"Source: {source}\n"
        output += f"Timestamp: {timestamp}\n"
        output += f"\n{content}\n"

        filepath.write_text(output, encoding='utf-8')
        return filepath

    def log_execution(self, command: str, return_code: int, stdout: str, stderr: str, tool: str = "unknown"):
        """记录工具执行结果"""
        timestamp = datetime.now().isoformat().replace(':', '-')
        filename = f"execution_{tool}_{timestamp}.json"
        filepath = self.run_dir / "logs" / filename

        record = {
            "tool": tool,
            "command": command,
            "return_code": return_code,
            "stdout": stdout[:2000],  # 截断长输出
            "stderr": stderr[:2000],
            "timestamp": timestamp
        }

        filepath.write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        return filepath

    def save_test_input(self, input_data: bytes, description: str = ""):
        """保存测试输入并计算哈希"""
        sha256 = hashlib.sha256(input_data).hexdigest()
        filename = f"input_{sha256[:8]}.bin"
        filepath = self.evidence_dir / filename

        filepath.write_bytes(input_data)

        # 记录哈希清单
        checksum_file = self.evidence_dir / "checksums.txt"
        line = f"{sha256}  {filename}"
        if description:
            line += f"  ({description})"

        if checksum_file.exists():
            content = checksum_file.read_text() + "\n" + line
        else:
            content = line

        checksum_file.write_text(content)
        return filepath, sha256

    def update_evidence_level(self, level: str):
        """更新证据等级"""
        self.task.evidence_level = level
        self._save_metadata()

    def get_research_dir(self) -> Path:
        """获取研究产物根目录"""
        return self.run_dir

    def generate_report(self, findings: Dict[str, Any]) -> str:
        """生成研究报告"""
        report = f"""# {self.cve_id} 研究报告

## 任务信息
- CVE ID: {self.cve_id}
- Task ID: {self.task_id}
- Run ID: {self.run_id}
- 创建时间: {self.task.created_at}
- 证据等级: {self.task.evidence_level}

## 研究发现
{json.dumps(findings, indent=2, ensure_ascii=False)}

## 产物位置
{self.run_dir}

---
生成于 {datetime.now().isoformat()}
"""
        report_file = self.run_dir / "REPORT.md"
        report_file.write_text(report, encoding='utf-8')
        return report
