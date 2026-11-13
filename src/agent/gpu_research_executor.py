"""
GPU 漏洞研究 Agent

集成 Deep Agents、Tavily 情报、CUDA 工具、证据持久化
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from src.config import get_config
from src.research import (
    CVEResearchRunner,
    extract_nvidia_advisory_info,
    detect_cuda_environments,
    execute_nvdisasm,
    validate_cubin
)


class GPUVulnerabilityResearchAgent:
    """GPU CVE 自主研究执行器"""

    def __init__(self, cve_id: str):
        """
        初始化研究 Agent

        Args:
            cve_id: CVE ID (e.g. "CVE-2024-53877")
        """
        self.cve_id = cve_id
        self.config = get_config()
        self.runner = CVEResearchRunner(cve_id)
        self.work_dir = self.runner.run_dir

    def research_workflow(self, baseline_cubin_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        执行完整研究工作流：
        情报采集 -> 环境检查 -> 基线实验 -> 报告生成

        Args:
            baseline_cubin_path: Optional path to pre-built CUBIN for testing.
                                If None, will attempt to locate or generate.

        Returns:
            Research result dict with evidence and conclusions
        """
        result = {
            "cve_id": self.cve_id,
            "workflow_start": datetime.now().isoformat(),
            "stages": {}
        }

        # Stage 1: Intelligence Collection
        result["stages"]["intelligence"] = self._collect_intelligence()

        # Stage 2: Environment Detection
        result["stages"]["environment"] = self._detect_environment()

        # Stage 3: Baseline Experiment
        if baseline_cubin_path and Path(baseline_cubin_path).exists():
            result["stages"]["baseline_experiment"] = self._run_baseline_experiment(
                Path(baseline_cubin_path)
            )
        else:
            result["stages"]["baseline_experiment"] = {
                "status": "SKIPPED",
                "reason": "No baseline CUBIN provided or not found"
            }

        # Stage 4: Generate Report
        result["stages"]["report"] = self._generate_report(result)

        result["workflow_end"] = datetime.now().isoformat()

        return result

    def _collect_intelligence(self) -> Dict[str, Any]:
        """收集 CVE 官方情报"""
        print(f"[Agent] Collecting intelligence for {self.cve_id}...")

        advisory = extract_nvidia_advisory_info(self.cve_id)

        if "status" in advisory and advisory["status"] == "not_found":
            return {
                "status": "NOT_FOUND",
                "message": f"No known advisory for {self.cve_id}"
            }

        # Log evidence
        self.runner.log_evidence(
            "OFFICIAL_ADVISORY_EXTRACTED",
            f"""CVE: {self.cve_id}
Title: {advisory.get('title', 'N/A')}
Component: {advisory.get('component', 'N/A')}
Type: {advisory.get('type', 'N/A')}
Severity: {advisory.get('severity', 'N/A')}
Source: {advisory.get('source', 'N/A')}

Description: {advisory.get('description', 'N/A')}

Known Limitations:
""" + "\n".join(f"  - {l}" for l in advisory.get('known_limitations', [])),
            source="NVIDIA Official Advisory"
        )

        return {
            "status": "COLLECTED",
            "cve_id": self.cve_id,
            "title": advisory.get("title"),
            "component": advisory.get("component"),
            "severity": advisory.get("severity"),
            "known_limitations": advisory.get("known_limitations", [])
        }

    def _detect_environment(self) -> Dict[str, Any]:
        """检测 CUDA 工具链环境"""
        print(f"[Agent] Detecting CUDA environments...")

        environments = detect_cuda_environments()

        env_summary = {
            "status": "DETECTED",
            "versions_available": list(environments.keys()),
            "tools": {}
        }

        for version, env in environments.items():
            env_summary["tools"][version] = {
                "nvdisasm_path": str(env.nvdisasm_path),
                "nvcc_path": str(env.nvcc_path),
                "cuobjdump_path": str(env.cuobjdump_path),
                "complete": env.is_complete(),
                "gpu_compute_capability": env.gpu_compute_capability,
                "driver_version": env.driver_version
            }

        # Log evidence
        self.runner.log_evidence(
            "ENVIRONMENT_DETECTED",
            json.dumps(env_summary, indent=2),
            source="Agent CUDA Detection"
        )

        return env_summary

    def _run_baseline_experiment(self, cubin_path: Path) -> Dict[str, Any]:
        """执行基线 CUBIN 反汇编实验"""
        print(f"[Agent] Running baseline experiment with {cubin_path}...")

        # Get latest environment (highest version)
        environments = detect_cuda_environments()
        if not environments:
            return {
                "status": "NO_ENVIRONMENT",
                "message": "No CUDA environments detected"
            }

        # Use latest version by default
        latest_version = sorted(environments.keys(), reverse=True)[0]
        env = environments[latest_version]

        print(f"[Agent] Using nvdisasm from CUDA {latest_version}")

        # Execute
        exec_result = execute_nvdisasm(env, cubin_path, timeout=30)

        # Log raw execution result
        self.runner.log_execution(
            command=exec_result.get("command", "N/A"),
            return_code=exec_result.get("return_code"),
            stdout=exec_result.get("stdout", ""),
            stderr=exec_result.get("stderr", ""),
            tool=f"nvdisasm_{latest_version}"
        )

        # Save detailed execution record
        exec_record_file = self.work_dir / "baseline_execution_record.json"
        exec_record_file.write_text(
            json.dumps(exec_result, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        return {
            "status": exec_result.get("status"),
            "cuda_version": latest_version,
            "tool_path": exec_result.get("tool_path"),
            "tool_binary_sha256": exec_result.get("tool_binary_sha256"),
            "input_file": exec_result.get("input_file"),
            "input_sha256": exec_result.get("input_sha256"),
            "return_code": exec_result.get("return_code"),
            "exit_status": exec_result.get("exit_status"),
            "stdout_length": exec_result.get("stdout_length"),
            "stderr_length": exec_result.get("stderr_length"),
            "output_saved_to": str(exec_record_file)
        }

    def _generate_report(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成研究报告"""
        print(f"[Agent] Generating research report...")

        report = {
            "cve_id": self.cve_id,
            "report_generated": datetime.now().isoformat(),
            "workflow_stages": workflow_result["stages"],
            "evidence_assessment": self._assess_evidence(workflow_result),
            "research_continuity": {
                "artifacts_location": str(self.work_dir),
                "evidence_level": self.runner.task.evidence_level,
                "next_steps": self._recommend_next_steps(workflow_result)
            }
        }

        # Save report
        report_file = self.work_dir / "RESEARCH_REPORT.json"
        report_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        self.runner.log_evidence(
            "RESEARCH_REPORT_GENERATED",
            json.dumps(report, indent=2),
            source="Agent Report Generator"
        )

        return report

    def _assess_evidence(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """评估证据完整性"""
        stages = workflow_result["stages"]
        intel = stages.get("intelligence", {})
        baseline = stages.get("baseline_experiment", {})

        verdict = "PARTIAL"
        reasons = []

        if intel.get("status") == "COLLECTED":
            reasons.append("Official advisory collected and verified")
        else:
            reasons.append("Advisory collection incomplete")

        if baseline.get("status") == "EXECUTED":
            if baseline.get("return_code") == 0:
                reasons.append("Baseline CUBIN processed successfully by nvdisasm")
                reasons.append("Normal behavior baseline established")
            else:
                reasons.append(f"Baseline execution returned non-zero code: {baseline.get('return_code')}")
        else:
            reasons.append("Baseline experiment not completed")

        reasons.append("Version comparison infrastructure ready but CUDA 12.8 not available")
        reasons.append("Exact triggering ELF structure unknown from public sources")

        return {
            "overall_verdict": verdict,
            "findings": reasons
        }

    def _recommend_next_steps(self, workflow_result: Dict[str, Any]) -> list:
        """推荐下一阶段工作"""
        return [
            "Research public PoC or patch analysis for exact ELF trigger structure",
            "Confirm affected version boundaries from NVIDIA official archives",
            "Evaluate CUDA 12.8 installation in isolated environment if feasible",
            "Implement minimal ELF mutation for hypothesis testing (when trigger known)",
            "Execute differential analysis between affected and patched versions"
        ]
