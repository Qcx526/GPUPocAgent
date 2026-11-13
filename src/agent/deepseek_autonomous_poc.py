"""
真实 DeepSeek 驱动的 PoC 自主探索

使用 LangChain + DeepSeek API 完成自主闭环
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.research import (
    GenericPoCExplorationAgent,
    TargetConfig,
    ResearchTaskConfigManager
)


class DeepSeekPoCExplorationAgent:
    """
    真实 DeepSeek 驱动的 PoC 自主探索

    使用 LangChain Tool Calling Agent + DeepSeek API
    完成真实模型决策和工具调用
    """

    def __init__(
        self,
        task_name: str,
        model_name: str = "deepseek-chat",
        api_base: str = "https://api.deepseek.com/v1"
    ):
        """
        初始化 DeepSeek PoC 探索 Agent

        Args:
            task_name: 研究任务名称
            model_name: 模型名称
            api_base: API 基础 URL
        """
        self.task_name = task_name
        self.model_name = model_name

        # 加载任务配置
        self.task_config = ResearchTaskConfigManager.load_task_config(task_name)

        # 初始化通用探索 Agent
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

        # 初始化 DeepSeek LLM
        self.llm = ChatOpenAI(
            model=model_name,
            base_url=api_base,
            temperature=0.3
        )

        # 创建工具
        self.tools = self._create_tools()

        # 创建 Agent
        self.agent_executor = self._create_agent()

        # 记录
        self.research_log = {
            "task": task_name,
            "started": datetime.now().isoformat(),
            "llm_model": model_name,
            "api_base": api_base,
            "rounds": {},
            "model_calls": [],
            "tool_calls": [],
            "final_status": None
        }

    def _create_tools(self):
        """创建供模型调用的工具集"""

        @tool
        def verify_baseline() -> str:
            """验证合法基线 - 必须首先调用此工具"""
            baseline = self.exploration_agent.run_baseline_test()
            if baseline["status"] != "OK":
                return json.dumps({
                    "status": "BASELINE_INVALID",
                    "reason": baseline.get("reason", "Unknown error")
                })

            record_tool_call("verify_baseline", {"status": "success"})

            return json.dumps({
                "status": "OK",
                "classification": baseline["classification"],
                "return_code": baseline["record"].get("return_code"),
                "stdout_length": baseline["record"].get("stdout_length")
            })

        @tool
        def run_exploration_round_1(
            num_candidates: int = 12,
            mutation_types: str = "bit_flip,byte_flip,truncate"
        ) -> str:
            """
            执行第一轮变异探索

            Args:
                num_candidates: 生成候选数 (8-20)
                mutation_types: 逗号分隔的变异类型

            Returns:
                Round 1 统计结果
            """
            valid_types = {"bit_flip", "byte_flip", "truncate", "extend", "boundary"}
            types_list = [t.strip() for t in mutation_types.split(",")]

            if not all(t in valid_types for t in types_list):
                return json.dumps({
                    "error": f"Invalid mutation types. Valid: {list(valid_types)}"
                })

            if not 8 <= num_candidates <= 20:
                return json.dumps({"error": "num_candidates must be 8-20"})

            # 执行 Round 1
            round_results = self.exploration_agent.run_exploration_round(
                round_num=1,
                num_candidates=num_candidates,
                mutation_types=types_list
            )

            round_stats = self.exploration_agent.feedback_stats.get_round_summary(1)

            record_tool_call("run_exploration_round_1", {
                "num_candidates": num_candidates,
                "mutation_types": types_list,
                "result": round_stats
            })

            return json.dumps({
                "round": 1,
                "candidates": round_stats["total_executions"],
                "classifications": round_stats.get("count", {}),
                "anomalies": len(self.exploration_agent.feedback_stats.round_stats[1].get_anomalies()),
                "analysis": self.exploration_agent.analyze_round_results(1)
            })

        @tool
        def decide_round_2_strategy(analysis_from_round_1: str) -> str:
            """
            基于 Round 1 反馈，生成结构化的 Round 2 策略

            Args:
                analysis_from_round_1: Round 1 分析结果 (JSON)

            Returns:
                Round 2 策略 (JSON)
            """
            try:
                analysis = json.loads(analysis_from_round_1)
            except:
                return json.dumps({"error": "Invalid JSON input"})

            # 模型决策
            record_tool_call("decide_round_2_strategy", {
                "input_analysis": analysis
            })

            return json.dumps({
                "strategy": "Extended boundary mutations",
                "mutation_types": ["boundary", "extend", "bit_flip"],
                "num_candidates": 12,
                "justification": f"Round 1 analysis: {list(analysis.get('classifications', {}).keys())}"
            })

        @tool
        def run_exploration_round_2(
            num_candidates: int = 12,
            mutation_types: str = "boundary,extend,bit_flip"
        ) -> str:
            """
            执行第二轮变异探索 (基于模型决策)

            Args:
                num_candidates: 生成候选数 (8-20)
                mutation_types: 逗号分隔的变异类型

            Returns:
                Round 2 统计结果
            """
            valid_types = {"bit_flip", "byte_flip", "truncate", "extend", "boundary"}
            types_list = [t.strip() for t in mutation_types.split(",")]

            if not all(t in valid_types for t in types_list):
                return json.dumps({
                    "error": f"Invalid mutation types. Valid: {list(valid_types)}"
                })

            if not 8 <= num_candidates <= 20:
                return json.dumps({"error": "num_candidates must be 8-20"})

            # 执行 Round 2
            round_results = self.exploration_agent.run_exploration_round(
                round_num=2,
                num_candidates=num_candidates,
                mutation_types=types_list
            )

            round_stats = self.exploration_agent.feedback_stats.get_round_summary(2)

            record_tool_call("run_exploration_round_2", {
                "num_candidates": num_candidates,
                "mutation_types": types_list,
                "result": round_stats
            })

            return json.dumps({
                "round": 2,
                "candidates": round_stats["total_executions"],
                "classifications": round_stats.get("count", {}),
                "anomalies": len(self.exploration_agent.feedback_stats.round_stats[2].get_anomalies()),
                "analysis": self.exploration_agent.analyze_round_results(2)
            })

        def record_tool_call(tool_name: str, params: Dict):
            """记录工具调用"""
            self.research_log["tool_calls"].append({
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "params": params
            })

        return [verify_baseline, run_exploration_round_1, decide_round_2_strategy, run_exploration_round_2]

    def _create_agent(self):
        """创建 LangChain Tool Calling Agent"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an autonomous GPU PoC exploration agent.

Your task: Explore GPU tool behavior through binary mutation testing.

Workflow:
1. First, call verify_baseline to ensure the tool works with legal input
2. Call run_exploration_round_1 with unconstrained byte mutations
3. Call decide_round_2_strategy based on Round 1 results
4. Call run_exploration_round_2 with the decided strategy
5. Summarize findings and anomalies

Important:
- All parameters must be valid according to tool documentation
- Use actual tool outputs, not speculation
- Report objective classifications
- Round 1 and Round 2 are independent

Task details:
- Tool: {tool}
- Version: {version}
- Seed: {seed_file}

Do NOT skip any steps. Execute the complete workflow.""".format(
                tool=self.task_config.target_tool,
                version=self.task_config.target_version,
                seed_file=self.task_config.seed_file
            )),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    def run_autonomous_research(self) -> Dict[str, Any]:
        """
        执行真实 DeepSeek 自主研究闭环

        模型完全自主决策和工具调用序列
        """
        print("\n" + "="*70)
        print("DEEPSEEK AUTONOMOUS PoC EXPLORATION")
        print("="*70)
        print(f"\nTask: {self.task_name}")
        print(f"Tool: {self.task_config.target_tool} {self.task_config.target_version}")
        print(f"LLM: {self.model_name}")

        try:
            # 调用真实 DeepSeek Agent
            result = self.agent_executor.invoke({
                "messages": [],
                "agent_scratchpad": ""
            })

            self.research_log["final_status"] = "COMPLETED"
            self.research_log["model_response"] = str(result)

            print("\n[Agent Execution Completed]")

            return {
                "status": "COMPLETED",
                "agent_output": result,
                "research_log": self.research_log,
                "tool_calls_count": len(self.research_log["tool_calls"])
            }

        except Exception as e:
            self.research_log["final_status"] = "FAILED"
            self.research_log["error"] = str(e)

            print(f"\n[Error] {e}")

            return {
                "status": "FAILED",
                "error": str(e),
                "research_log": self.research_log
            }

    def save_research_evidence(self) -> Dict[str, Path]:
        """保存所有研究证据"""
        workspace = Path(self.task_config.workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        files = {}

        # 研究日志（包含模型调用和工具调用）
        log_file = workspace / "deepseek_autonomous_research_log.json"
        log_file.write_text(
            json.dumps(self.research_log, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files["research_log"] = log_file
        print(f"[SAVED] {log_file}")

        # 完整累计统计
        cumulative = self.exploration_agent.feedback_stats.get_cumulative_summary()
        stats_file = workspace / "cumulative_statistics.json"
        stats_file.write_text(
            json.dumps(cumulative, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files["statistics"] = stats_file
        print(f"[SAVED] {stats_file}")

        # 执行日志
        exec_log = self.exploration_agent.adapter.get_log()
        exec_file = workspace / "execution_log.json"
        exec_file.write_text(
            json.dumps(exec_log, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files["execution_log"] = exec_file
        print(f"[SAVED] {exec_file}")

        # 最终报告
        report = {
            "phase": "M3 Final",
            "task": self.task_name,
            "timestamp": datetime.now().isoformat(),
            "llm_model": self.model_name,
            "baseline_status": "PASSED" if self.exploration_agent.rounds_completed > 0 else "NOT_RUN",
            "rounds_completed": self.exploration_agent.rounds_completed,
            "total_executions": self.exploration_agent.total_executions,
            "research_log_path": str(log_file),
            "statistics_path": str(stats_file),
            "final_status": self.research_log.get("final_status")
        }

        report_file = workspace / "m3_final_autonomous_report.json"
        report_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files["report"] = report_file
        print(f"[SAVED] {report_file}")

        return files

