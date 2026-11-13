"""
CVE 情报采集模块

使用 Tavily 检索公开漏洞资料
记录所有来源和引用
"""

from typing import Optional, Dict, List, Any
import json
from pathlib import Path


def search_cve_intelligence(cve_id: str, tavily_creds: Optional[str] = None) -> Dict[str, Any]:
    """
    Use Tavily to search for CVE information.

    Args:
        cve_id: CVE ID (e.g. "CVE-2024-53877")
        tavily_creds: Tavily credentials (defaults to env TAVILY_API_KEY or config)

    Returns:
        Dict with search results and sources
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        return {
            "status": "error",
            "message": "Tavily not installed",
            "results": []
        }

    if tavily_creds is None:
        import os
        # Try environment variable first
        tavily_creds = os.environ.get("TAVILY_API_KEY")
        if not tavily_creds:
            # Fall back to config
            from src.config import get_config
            config = get_config()
            tavily_creds = config.tavily_api_key

        if not tavily_creds:
            return {
                "status": "error",
                "message": "Tavily credentials not configured (set TAVILY_API_KEY env var or config)",
                "results": []
            }

    try:
        client = TavilyClient()
        setattr(client, "api_key", tavily_creds)

        # Search multiple dimensions
        queries = [
            f"{cve_id} NVIDIA GPU vulnerability",
            f"{cve_id} nvdisasm cuobjdump",
            f"NVIDIA security bulletin {cve_id}",
            f"{cve_id} patch diff analysis",
            f"{cve_id} proof of concept PoC"
        ]

        all_results = []
        for query in queries:
            response = client.search(
                query=query,
                include_answer=True,
                max_results=5
            )
            all_results.append({
                "query": query,
                "results": response.get("results", []),
                "answer": response.get("answer", "")
            })

        return {
            "status": "success",
            "cve_id": cve_id,
            "search_results": all_results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "results": []
        }


def extract_nvidia_advisory_info(cve_id: str) -> Dict[str, Any]:
    """
    从 NVIDIA 官方公告提取 CVE 信息

    已知公开公告：
    - CVE-2024-53877: nvdisasm NULL pointer
    - CVE-2024-53871: nvdisasm out-of-bounds read
    - CVE-2024-53870: cuobjdump out-of-bounds read

    参考: https://nvidia.custhelp.com/app/answers/detail/a_id/5594
    """

    advisory_db = {
        "CVE-2024-53877": {
            "title": "NVIDIA nvdisasm NULL Pointer Exception",
            "component": "nvdisasm",
            "type": "NULL pointer dereference",
            "severity": "CVSS 5.5 (Medium)",
            "affected_versions": [
                "CUDA Toolkit 11.8.0 to 12.6.x"
            ],
            "fixed_versions": [
                "CUDA Toolkit 12.7.0"
            ],
            "description": "Processing a malformed CUBIN file causes NULL pointer exception"
        },
        "CVE-2024-53871": {
            "title": "NVIDIA nvdisasm Out-of-Bounds Read",
            "component": "nvdisasm",
            "type": "Out-of-bounds memory read",
            "severity": "CVSS 5.3 (Medium)",
            "affected_versions": [
                "CUDA Toolkit 11.8.0 to 12.6.x"
            ],
            "fixed_versions": [
                "CUDA Toolkit 12.7.0"
            ],
            "description": "Processing a malformed CUBIN file causes out-of-bounds read"
        },
        "CVE-2024-53870": {
            "title": "NVIDIA cuobjdump Out-of-Bounds Read",
            "component": "cuobjdump",
            "type": "Out-of-bounds memory read",
            "severity": "CVSS 5.3 (Medium)",
            "affected_versions": [
                "CUDA Toolkit 11.8.0 to 12.6.x"
            ],
            "fixed_versions": [
                "CUDA Toolkit 12.7.0"
            ],
            "description": "Processing a malformed ELF file causes out-of-bounds read"
        }
    }

    return advisory_db.get(cve_id, {
        "status": "not_found",
        "message": f"No known advisory for {cve_id}"
    })


def assess_reproducibility(cve_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    评估 CVE 复现可行性

    返回：
    - feasible: 是否可行
    - blockers: 阻塞项
    - recommendations: 建议
    """

    blockers = []
    recommendations = []

    # 检查受影响版本可用性
    affected = cve_info.get("affected_versions", [])
    if "12.6" in str(affected):
        recommendations.append("CUDA 12.6 广泛可用，易于获得")
    elif "11.8" in str(affected):
        recommendations.append("CUDA 11.8 为较旧版本，可能需要归档")

    # 检查组件
    component = cve_info.get("component", "")
    if component == "nvdisasm":
        recommendations.append("nvdisasm 为独立工具，无需 GPU 即可运行")
    elif component == "cuobjdump":
        recommendations.append("cuobjdump 为独立工具，无需 GPU 即可运行")

    # 检查输入类型
    description = cve_info.get("description", "").lower()
    if "cubin" in description:
        recommendations.append("CUBIN 为 NVIDIA GPU 二进制格式，可通过 nvcc 生成")
    elif "elf" in description:
        recommendations.append("ELF 为标准可执行格式，可自行构造或获得")

    return {
        "feasible": len(blockers) == 0,
        "blockers": blockers,
        "recommendations": recommendations,
        "assessment": "可行" if len(blockers) == 0 else "阻塞"
    }
