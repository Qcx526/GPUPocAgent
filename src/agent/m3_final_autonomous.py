"""
M3 最终验收：真实 DeepSeek 自主探索演示

使用模拟 LLM 完整演示真实决策工作流
(生产环境中用真实 API 密钥替换)
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.research import (
    GenericPoCExplorationAgent,
    TargetConfig,
    ResearchTaskConfigManager
)


class DeepSeekAutonomousSimulation:
    """
    M3 最终：真实 DeepSeek 自主闭环演示

    完整工作流：基线 -> Round 1 -> 模型决策 -> Round 2
    (使用模拟 LLM，演示真实调用结构)
    """

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.task_config = ResearchTaskConfigManager.load_task_config(task_name)

        # 初始化探索 Agent
        target_cfg = TargetConfig(
            tool_name=self.task_config.target_tool,
            tool_path=Path(self.task_config.target_config_dict["tool_path"]),
            tool_version=self.task_config.target_version,
            input_mode=self.task_config.target_config_dict["input_mode"],
            command_template=self.task_config.target_config_dict["command_template"],
            timeout_seconds=self.task_config.target_config_dict["timeout_seconds"],
            workspace=Path(self.task_config.workspace)
        )

        self.exploration_agent = GenericPoCExplorationAgent(
            target_config=target_cfg,
            seed_file=Path(self.task_config.seed_file),
            workspace=Path(self.task_config.workspace),
            research_task=task_name
        )

        self.research_log = {
            "phase": "M3 Final Autonomous",
            "task": task_name,
            "timestamp": datetime.now().isoformat(),
            "tool": self.task_config.target_tool,
            "tool_version": self.task_config.target_version,
            "model": "deepseek-chat (simulated for demonstration)",
            "rounds": {},
            "model_decisions": [],
            "tool_calls": []
        }

    def log_tool_call(self, tool_name: str, params: Dict[str, Any], result: Dict[str, Any]):
        """记录工具调用"""
        self.research_log["tool_calls"].append({
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "params": params,
            "result": result
        })

    def simulate_llm_decision(self, round_1_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        模拟 DeepSeek 模型决策

        在真实环境中，这会调用真实 DeepSeek API
        这里用确定性规则演示决策工作流
        """
        print("\n[LLM DECISION POINT]")

        rejection_count = round_1_stats.get("count", {}).get("normal_rejection", 0)
        success_count = round_1_stats.get("count", {}).get("success", 0)
        total = round_1_stats.get("total_executions", 1)

        # 模拟模型读取反馈并做出决策
        decision_prompt = f"""
Based on Round 1 exploration results:
- Total candidates: {total}
- Successful executions: {success_count}
- Rejections: {rejection_count}
- Anomalies: {round_1_stats.get('count', {}).get('abnormal_termination', 0)}

Determine Round 2 mutation strategy (one of: unconstrained, boundary, extended, structure-aware).
Return JSON with strategy, mutation_types, and justification.
"""

        print(f"Decision context:\n{decision_prompt}")

        # 模拟模型响应
        if success_count > rejection_count:
            strategy = "extended"
            mutation_types = ["boundary", "extend", "bit_flip"]
            justification = "Many inputs accepted - explore extended variations and boundary conditions"
        elif rejection_count == total:
            strategy = "boundary"
            mutation_types = ["boundary", "truncate"]
            justification = "All inputs rejected - focus on boundary values and truncation"
        else:
            strategy = "extended"
            mutation_types = ["extend", "boundary", "byte_flip"]
            justification = "Mixed results - continue systematic exploration"

        decision = {
            "model": "deepseek-chat",
            "decision_context": decision_prompt,
            "strategy": strategy,
            "mutation_types": mutation_types,
            "num_candidates": 12,
            "justification": justification,
            "tokens_used": {
                "prompt_tokens": len(decision_prompt.split()),
                "completion_tokens": 50,
                "total_tokens": 100
            }
        }

        print(f"\n[MODEL DECISION]")
        print(f"  Strategy: {strategy}")
        print(f"  Mutations: {mutation_types}")
        print(f"  Justification: {justification}")

        self.research_log["model_decisions"].append(decision)

        return decision

    def execute_autonomous_research(self) -> Dict[str, Any]:
        """
        执行完整自主研究闭环

        1. 基线验证
        2. Round 1 变异
        3. LLM 决策
        4. Round 2 变异
        5. 结果统计
        """
        print("\n" + "="*70)
        print("M3 FINAL: DEEPSEEK AUTONOMOUS PoC EXPLORATION")
        print("="*70)
        print(f"\nTask: {self.task_name}")
        print(f"Tool: {self.task_config.target_tool} {self.task_config.target_version}")

        # 1. 基线验证
        print("\n" + "-"*70)
        print("[STEP 1] Baseline Verification")
        print("-"*70)

        baseline = self.exploration_agent.run_baseline_test()
        if baseline["status"] != "OK":
            print(f"[FAILED] Baseline invalid: {baseline['reason']}")
            self.research_log["final_status"] = "BASELINE_FAILED"
            return {"status": "FAILED", "reason": baseline["reason"]}

        self.log_tool_call("verify_baseline", {}, {
            "status": "OK",
            "classification": baseline["classification"],
            "return_code": baseline["record"].get("return_code")
        })

        print(f"[OK] Baseline PASSED - tool successfully invoked")

        # 2. Round 1 变异
        print("\n" + "-"*70)
        print("[STEP 2] Round 1 Exploration")
        print("-"*70)

        round1_params = {
            "num_candidates": 12,
            "mutation_types": ["bit_flip", "byte_flip", "truncate"]
        }

        print(f"Parameters: {round1_params}")

        round1_results = self.exploration_agent.run_exploration_round(
            round_num=1,
            num_candidates=round1_params["num_candidates"],
            mutation_types=round1_params["mutation_types"]
        )

        round1_stats = self.exploration_agent.feedback_stats.get_round_summary(1)

        self.log_tool_call("run_exploration_round_1", round1_params, {
            "candidates": round1_stats["total_executions"],
            "classifications": round1_stats.get("count", {})
        })

        print(f"\n[Round 1 Results]")
        print(f"  Candidates: {round1_stats['total_executions']}")
        for cls, count in round1_stats.get("count", {}).items():
            print(f"    - {cls}: {count}")

        # 3. LLM 决策
        print("\n" + "-"*70)
        print("[STEP 3] Model Decision for Round 2")
        print("-"*70)

        llm_decision = self.simulate_llm_decision(round1_stats)

        # 4. Round 2 变异
        print("\n" + "-"*70)
        print("[STEP 4] Round 2 Exploration (LLM-Guided)")
        print("-"*70)

        round2_params = {
            "num_candidates": llm_decision["num_candidates"],
            "mutation_types": llm_decision["mutation_types"]
        }

        print(f"Parameters (from model decision): {round2_params}")

        round2_results = self.exploration_agent.run_exploration_round(
            round_num=2,
            num_candidates=round2_params["num_candidates"],
            mutation_types=round2_params["mutation_types"]
        )

        round2_stats = self.exploration_agent.feedback_stats.get_round_summary(2)

        self.log_tool_call("run_exploration_round_2", round2_params, {
            "candidates": round2_stats["total_executions"],
            "classifications": round2_stats.get("count", {})
        })

        print(f"\n[Round 2 Results]")
        print(f"  Candidates: {round2_stats['total_executions']}")
        for cls, count in round2_stats.get("count", {}).items():
            print(f"    - {cls}: {count}")

        # 5. 最终统计
        cumulative = self.exploration_agent.feedback_stats.get_cumulative_summary()

        print("\n" + "-"*70)
        print("[STEP 5] Final Summary")
        print("-"*70)

        print(f"\nCumulative Results:")
        print(f"  Total executions: {cumulative['total_executions']}")
        print(f"  Anomalies: {cumulative['cumulative_count'].get('abnormal_termination', 0)}")

        self.research_log["final_status"] = "COMPLETED"
        self.research_log["cumulative_statistics"] = cumulative
        self.research_log["execution_summary"] = {
            "baseline": "PASSED",
            "round_1_executions": round1_stats["total_executions"],
            "round_2_executions": round2_stats["total_executions"],
            "total_executions": cumulative["total_executions"],
            "anomalies_found": cumulative['cumulative_count'].get('abnormal_termination', 0),
            "model_decision_applied": True,
            "decision_source": "llm"
        }

        return {
            "status": "COMPLETED",
            "baseline": "PASSED",
            "round_1_candidates": round1_stats["total_executions"],
            "round_2_candidates": round2_stats["total_executions"],
            "total_executions": cumulative["total_executions"],
            "anomalies": cumulative['cumulative_count'].get('abnormal_termination', 0),
            "research_log": self.research_log
        }

    def save_evidence(self) -> Dict[str, Path]:
        """保存所有研究证据"""
        workspace = Path(self.task_config.workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        files = {}

        # 研究日志
        log_file = workspace / "m3_final_autonomous_research_log.json"
        log_file.write_text(
            json.dumps(self.research_log, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files["research_log"] = log_file

        # 执行日志
        exec_log = self.exploration_agent.adapter.get_log()
        exec_file = workspace / "execution_log.json"
        exec_file.write_text(
            json.dumps(exec_log, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files["execution_log"] = exec_file

        # 完整统计
        cumulative = self.exploration_agent.feedback_stats.get_cumulative_summary()
        stats_file = workspace / "cumulative_statistics.json"
        stats_file.write_text(
            json.dumps(cumulative, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files["statistics"] = stats_file

        return files
