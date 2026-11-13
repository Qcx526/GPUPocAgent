"""M3 GPU CVE Research Framework"""

from .cve_runner import CVEResearchRunner, EvidenceLevel, CVEResearchTask
from .intelligence import search_cve_intelligence, extract_nvidia_advisory_info, assess_reproducibility
from .cuda_tools import (
    detect_cuda_environments,
    validate_cubin,
    execute_nvdisasm,
    get_environment_report,
    CUDAEnvironment
)

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
    "CUDAEnvironment"
]
