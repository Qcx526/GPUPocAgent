"""
执行反馈分类与独立统计

准确区分：启动错误、正常拒绝、异常终止、超时
轮次独立统计
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class ExecutionFeedback:
    """执行反馈分类"""
    input_sha256: str
    return_code: int
    exit_type: str  # "success", "rejection", "abnormal", "timeout", "startup_error", "error", "unknown"
    stdout_length: int
    stderr_length: int
    classification: str  # "success", "normal_rejection", "abnormal_termination", "timeout", "startup_error", "unknown"
    reason: str


class FeedbackClassifier:
    """
    执行反馈分类器

    准确区分执行状态，基于真实进程信息而非启发式规则
    """

    @staticmethod
    def classify(execution_record: Dict[str, Any]) -> ExecutionFeedback:
        """
        分类单个执行结果

        Args:
            execution_record: 执行记录字典

        Returns:
            分类结果
        """
        status = execution_record.get("status")
        exit_type = execution_record.get("exit_type")
        return_code = execution_record.get("return_code")
        stderr = execution_record.get("stderr", "")

        input_sha = execution_record.get("input_sha256", "unknown")

        # 1. 启动错误
        if status == "STARTUP_FAILED":
            return ExecutionFeedback(
                input_sha256=input_sha,
                return_code=None,
                exit_type="startup_error",
                stdout_length=0,
                stderr_length=len(stderr),
                classification="startup_error",
                reason=f"Tool startup failed: {stderr[:100]}"
            )

        # 2. 超时
        if status == "TIMEOUT":
            return ExecutionFeedback(
                input_sha256=input_sha,
                return_code=None,
                exit_type="timeout",
                stdout_length=0,
                stderr_length=len(stderr),
                classification="timeout",
                reason="Execution exceeded timeout limit"
            )

        # 3. 其他框架错误
        if status == "ERROR" and status != "EXECUTED":
            return ExecutionFeedback(
                input_sha256=input_sha,
                return_code=None,
                exit_type="error",
                stdout_length=0,
                stderr_length=len(stderr),
                classification="unknown",
                reason=f"Execution error: {stderr[:100]}"
            )

        # 4. 成功执行的工具行为分类
        if status == "EXECUTED":
            if exit_type == "success" or return_code == 0:
                return ExecutionFeedback(
                    input_sha256=input_sha,
                    return_code=return_code,
                    exit_type="success",
                    stdout_length=execution_record.get("stdout_length", 0),
                    stderr_length=execution_record.get("stderr_length", 0),
                    classification="success",
                    reason="Tool executed successfully (return code 0)"
                )

            elif exit_type == "rejection" or (return_code != 0 and return_code is not None):
                # 工具返回非零 = 工具拒绝输入（正常行为）
                return ExecutionFeedback(
                    input_sha256=input_sha,
                    return_code=return_code,
                    exit_type="rejection",
                    stdout_length=execution_record.get("stdout_length", 0),
                    stderr_length=execution_record.get("stderr_length", 0),
                    classification="normal_rejection",
                    reason=f"Tool rejected input (return code {return_code})"
                )

            elif exit_type == "abnormal":
                # 信号或进程异常终止
                return ExecutionFeedback(
                    input_sha256=input_sha,
                    return_code=return_code,
                    exit_type="abnormal",
                    stdout_length=execution_record.get("stdout_length", 0),
                    stderr_length=execution_record.get("stderr_length", 0),
                    classification="abnormal_termination",
                    reason=f"Process abnormal termination (signal {return_code})"
                )

        return ExecutionFeedback(
            input_sha256=input_sha,
            return_code=return_code,
            exit_type="unknown",
            stdout_length=0,
            stderr_length=0,
            classification="unknown",
            reason="Unknown execution status"
        )


class RoundStatistics:
    """单轮统计（独立，不累计）"""

    def __init__(self, round_num: int):
        self.round_num = round_num
        self.feedbacks: List[ExecutionFeedback] = []

    def add_feedback(self, feedback: ExecutionFeedback):
        """添加反馈"""
        self.feedbacks.append(feedback)

    def get_summary(self) -> Dict[str, Any]:
        """获取该轮独立统计"""
        summary = {
            "round": self.round_num,
            "total_executions": len(self.feedbacks),
            "classifications": {}
        }

        for feedback in self.feedbacks:
            cls = feedback.classification
            if cls not in summary["classifications"]:
                summary["classifications"][cls] = []
            summary["classifications"][cls].append({
                "input_sha256": feedback.input_sha256,
                "return_code": feedback.return_code,
                "reason": feedback.reason
            })

        # 计数
        summary["count"] = {
            cls: len(items)
            for cls, items in summary["classifications"].items()
        }

        return summary

    def get_anomalies(self) -> List[ExecutionFeedback]:
        """获取该轮异常候选"""
        return [f for f in self.feedbacks if f.classification == "abnormal_termination"]

    def get_json_report(self) -> str:
        """获取该轮 JSON 报告"""
        return json.dumps(self.get_summary(), indent=2, ensure_ascii=False)


class FeedbackStatistics:
    """全轮次累计统计（明确区分轮次）"""

    def __init__(self):
        self.round_stats: Dict[int, RoundStatistics] = {}
        self.current_round = None

    def start_round(self, round_num: int):
        """开始新一轮"""
        self.current_round = round_num
        if round_num not in self.round_stats:
            self.round_stats[round_num] = RoundStatistics(round_num)

    def add_feedback(self, feedback: ExecutionFeedback):
        """添加反馈到当前轮"""
        if self.current_round is None:
            raise ValueError("No round started. Call start_round() first.")
        self.round_stats[self.current_round].add_feedback(feedback)

    def get_round_summary(self, round_num: int) -> Dict[str, Any]:
        """获取特定轮的统计"""
        if round_num not in self.round_stats:
            return {"error": f"Round {round_num} not found"}
        return self.round_stats[round_num].get_summary()

    def get_cumulative_summary(self) -> Dict[str, Any]:
        """获取全轮累计统计"""
        cumulative = {
            "total_rounds": len(self.round_stats),
            "total_executions": 0,
            "cumulative_classifications": {}
        }

        for round_num in sorted(self.round_stats.keys()):
            round_summary = self.round_stats[round_num].get_summary()
            cumulative["total_executions"] += round_summary["total_executions"]

            for cls, items in round_summary["classifications"].items():
                if cls not in cumulative["cumulative_classifications"]:
                    cumulative["cumulative_classifications"][cls] = []
                cumulative["cumulative_classifications"][cls].extend(items)

        cumulative["cumulative_count"] = {
            cls: len(items)
            for cls, items in cumulative["cumulative_classifications"].items()
        }

        return cumulative

    def get_all_anomalies(self) -> Dict[int, List[ExecutionFeedback]]:
        """获取所有轮次的异常候选"""
        anomalies_by_round = {}
        for round_num, stats in self.round_stats.items():
            anomalies = stats.get_anomalies()
            if anomalies:
                anomalies_by_round[round_num] = anomalies
        return anomalies_by_round

    def get_json_report(self, round_num: int = None) -> str:
        """获取 JSON 报告"""
        if round_num is not None:
            return self.round_stats[round_num].get_json_report()
        else:
            return json.dumps(self.get_cumulative_summary(), indent=2, ensure_ascii=False)
