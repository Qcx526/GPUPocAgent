"""
通用 GPU PoC 自动探索 Agent

支持反馈驱动的输入变异和策略调整
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.research.target_adapter import TargetAdapter, TargetConfig
from src.research.input_mutation import InputMutationEngine
from src.research.feedback_classifier import FeedbackClassifier, FeedbackStatistics


class GenericPoCExplorationAgent:
    """
    通用 PoC 探索 Agent

    不需要预知具体 CVE 触发条件
    支持反馈驱动的变异和策略调整
    """

    def __init__(
        self,
        target_config: TargetConfig,
        seed_file: Path,
        workspace: Path,
        research_task: str = "gpu_poc_exploration"
    ):
        """
        初始化探索 Agent

        Args:
            target_config: 目标工具配置
            seed_file: 初始种子文件
            workspace: 工作空间
            research_task: 研究任务描述
        """
        self.target_config = target_config
        self.seed_file = seed_file
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.research_task = research_task

        self.adapter = TargetAdapter(target_config)
        self.mutation_engine = InputMutationEngine(seed_file, self.workspace / "inputs")
        self.feedback_stats = FeedbackStatistics()

        self.rounds_completed = 0
        self.total_executions = 0

    def run_exploration_round(
        self,
        round_num: int,
        num_candidates: int = 20,
        mutation_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        执行一轮探索

        Args:
            round_num: 轮次号
            num_candidates: 本轮生成候选数
            mutation_types: 使用的变异类型

        Returns:
            本轮结果摘要
        """
        if mutation_types is None:
            mutation_types = ["bit_flip", "byte_flip", "truncate", "boundary"]

        print(f"\n[Round {round_num}] Starting exploration round")
        print(f"  Mutations: {mutation_types}")
        print(f"  Candidates to generate: {num_candidates}")

        candidates = []
        round_id = f"round_{round_num}"

        # 生成候选
        candidates_per_type = num_candidates // len(mutation_types)
        for mutation_type in mutation_types:
            if mutation_type == "bit_flip":
                candidates.extend(self.mutation_engine.bit_flip(count=candidates_per_type))
            elif mutation_type == "byte_flip":
                candidates.extend(self.mutation_engine.byte_flip(count=candidates_per_type))
            elif mutation_type == "truncate":
                candidates.extend(self.mutation_engine.truncate(count=candidates_per_type))
            elif mutation_type == "extend":
                candidates.extend(self.mutation_engine.extend(count=candidates_per_type))
            elif mutation_type == "boundary":
                candidates.extend(self.mutation_engine.boundary(count=candidates_per_type))

        print(f"  Generated {len(candidates)} candidates")

        # 执行
        round_results = {
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "mutations_generated": len(candidates),
            "executions": []
        }

        for i, (candidate_file, mutation_record) in enumerate(candidates):
            exec_record = self.adapter.execute(
                candidate_file,
                task_id=self.research_task,
                run_id=round_id
            )

            # 分类反馈
            feedback = FeedbackClassifier.classify(exec_record)
            self.feedback_stats.add_feedback(feedback)

            round_results["executions"].append({
                "candidate_index": i,
                "input_sha256": feedback.input_sha256,
                "classification": feedback.classification,
                "return_code": feedback.return_code,
                "reason": feedback.reason
            })

            self.total_executions += 1

        # 汇总本轮
        round_summary = self.feedback_stats.get_summary()
        round_results["summary"] = round_summary

        print(f"  Completed {len(candidates)} executions")
        print(f"  Classifications:")
        for cls, count in round_summary.get("count", {}).items():
            print(f"    - {cls}: {count}")

        # 保存本轮结果
        round_report_file = self.workspace / f"round_{round_num}_results.json"
        round_report_file.write_text(
            json.dumps(round_results, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

        self.rounds_completed = round_num

        return round_results

    def analyze_round_results(self, round_num: int) -> Dict[str, Any]:
        """分析某一轮的结果，建议下一步策略"""
        summary = self.feedback_stats.get_summary()
        anomalies = self.feedback_stats.get_anomalies()

        analysis = {
            "round": round_num,
            "total_anomalies": len(anomalies),
            "normal_successes": summary.get("count", {}).get("normal_success", 0),
            "normal_rejections": summary.get("count", {}).get("normal_rejection", 0),
            "timeouts": summary.get("count", {}).get("timeout", 0)
        }

        # 策略建议
        recommendations = []

        if len(anomalies) > 0:
            recommendations.append(
                "Anomalies detected - preserve these candidates for detailed analysis"
            )
            analysis["anomalies"] = [
                {
                    "input_sha256": a.input_sha256,
                    "return_code": a.return_code,
                    "reason": a.reason
                }
                for a in anomalies
            ]
        else:
            recommendations.append(
                "No anomalies in this round - increase mutation intensity or expand mutation types"
            )

        if analysis["normal_successes"] > analysis["normal_rejections"]:
            recommendations.append(
                "Many inputs accepted by tool - focus on format-aware mutations"
            )
        else:
            recommendations.append(
                "Many inputs rejected - explore boundary conditions and truncation"
            )

        analysis["recommendations"] = recommendations

        return analysis

    def generate_exploration_report(self) -> Dict[str, Any]:
        """生成完整探索报告"""
        report = {
            "research_task": self.research_task,
            "timestamp": datetime.now().isoformat(),
            "exploration_summary": {
                "rounds_completed": self.rounds_completed,
                "total_executions": self.total_executions,
                "target_tool": self.target_config.tool_name,
                "target_version": self.target_config.tool_version,
                "seed_file": str(self.seed_file)
            },
            "feedback_statistics": self.feedback_stats.get_summary(),
            "candidates_workspace": str(self.workspace / "inputs" / "candidates"),
            "execution_logs": self.adapter.get_log()[-min(10, len(self.adapter.get_log())):]  # 最后 10 个
        }

        return report

    def save_report(self, report: Dict[str, Any], filename: str = "exploration_report.json"):
        """保存报告"""
        report_file = self.workspace / filename
        report_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"\n[OK] Report saved to {report_file}")
        return report_file
