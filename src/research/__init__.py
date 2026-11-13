"""M3+ GPU 漏洞 PoC 通用探索框架"""

# Phase 2-3A: CVE 情报和环境
from .cve_runner import CVEResearchRunner, EvidenceLevel, CVEResearchTask
from .intelligence import search_cve_intelligence, extract_nvidia_advisory_info, assess_reproducibility
from .cuda_tools import (
    detect_cuda_environments,
    validate_cubin,
    execute_nvdisasm,
    get_environment_report,
    CUDAEnvironment
)

# Phase 3B: 泛化 PoC 探索
from .target_adapter import TargetAdapter, TargetConfig
from .input_mutation import InputMutationEngine, MutationRecord
from .feedback_classifier import FeedbackClassifier, FeedbackStatistics, ExecutionFeedback
from .generic_poc_agent import GenericPoCExplorationAgent

__all__ = [
    "CVEResearchRunner",
    "EvidenceLevel",
    "CVEResearchTask",
    "search_cve_intelligence",
    "extract_nvidia_advisory_info",
    "assess_reproducibility",
    "detect_cuda_environments",
    "validate_cubin",
    "execute_nvdisasm",
    "get_environment_report",
    "CUDAEnvironment",
    "TargetAdapter",
    "TargetConfig",
    "InputMutationEngine",
    "MutationRecord",
    "FeedbackClassifier",
    "FeedbackStatistics",
    "ExecutionFeedback",
    "GenericPoCExplorationAgent"
]
