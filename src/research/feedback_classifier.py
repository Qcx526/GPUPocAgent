"""
执行反馈分类与统计

区分正常拒绝、超时、异常候选
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class ExecutionFeedback:
    """执行反馈分类"""
    input_sha256: str
    return_code: int
    exit_type: str  # "success", "non-zero", "timeout", "error"
    stdout_length: int
    stderr_length: int
    classification: str  # "normal_success", "normal_rejection", "timeout", "anomaly"
    reason: str


class FeedbackClassifier:
    """
    执行反馈分类器

    将执行结果映射到有意义的类别
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
        return_code = execution_record.get("return_code")
        stderr = execution_record.get("stderr", "")

        input_sha = execution_record.get("input_sha256", "unknown")

        # 基本分类逻辑
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

        if status == "ERROR":
            return ExecutionFeedback(
                input_sha256=input_sha,
                return_code=None,
                exit_type="error",
                stdout_length=0,
                stderr_length=len(stderr),
                classification="anomaly",
                reason=f"Execution error: {stderr[:100]}"
            )

        if status == "EXECUTED":
            if return_code == 0:
                return ExecutionFeedback(
                    input_sha256=input_sha,
                    return_code=return_code,
                    exit_type="success",
                    stdout_length=execution_record.get("stdout_length", 0),
                    stderr_length=execution_record.get("stderr_length", 0),
                    classification="normal_success",
                    reason="Tool executed successfully"
                )
            else:
                # 非零退出可能是正常拒绝或异常
                # 简单启发：有大量 stderr 和非零 exit 可能是异常
                if len(stderr) > 100:
                    return ExecutionFeedback(
                        input_sha256=input_sha,
                        return_code=return_code,
                        exit_type="non-zero",
                        stdout_length=execution_record.get("stdout_length", 0),
                        stderr_length=execution_record.get("stderr_length", 0),
                        classification="anomaly",
                        reason=f"Non-zero exit ({return_code}) with stderr output"
                    )
                else:
                    return ExecutionFeedback(
                        input_sha256=input_sha,
                        return_code=return_code,
                        exit_type="non-zero",
                        stdout_length=execution_record.get("stdout_length", 0),
                        stderr_length=execution_record.get("stderr_length", 0),
                        classification="normal_rejection",
                        reason=f"Normal tool rejection (return code {return_code})"
                    )

        return ExecutionFeedback(
            input_sha256=input_sha,
            return_code=None,
            exit_type="unknown",
            stdout_length=0,
            stderr_length=0,
            classification="unknown",
            reason="Unknown execution status"
        )


class FeedbackStatistics:
    """反馈统计"""

    def __init__(self):
        self.feedbacks: List[ExecutionFeedback] = []

    def add_feedback(self, feedback: ExecutionFeedback):
        """添加反馈"""
        self.feedbacks.append(feedback)

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总统计"""
        summary = {
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

        # Count
        summary["count"] = {
            cls: len(items)
            for cls, items in summary["classifications"].items()
        }

        return summary

    def get_anomalies(self) -> List[ExecutionFeedback]:
        """获取异常候选"""
        return [f for f in self.feedbacks if f.classification == "anomaly"]

    def get_json_report(self) -> str:
        """获取 JSON 报告"""
        return json.dumps(self.get_summary(), indent=2, ensure_ascii=False)
