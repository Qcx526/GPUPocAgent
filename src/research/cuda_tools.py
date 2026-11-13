"""
CUDA 环境工具

包括工具版本检测、CUBIN 完整性检查、受控执行
"""

import subprocess
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CUDAEnvironment:
    """CUDA 工具链环境"""
    cuda_version: str
    nvcc_path: Path
    nvdisasm_path: Path
    cuobjdump_path: Path
    gpu_compute_capability: Optional[str] = None
    driver_version: Optional[str] = None

    def is_complete(self) -> bool:
        """检查所有必要工具是否可用"""
        return all(p.exists() for p in [self.nvcc_path, self.nvdisasm_path, self.cuobjdump_path])


def detect_cuda_environments() -> Dict[str, CUDAEnvironment]:
    """
    检测系统中所有可用的 CUDA 工具链

    Returns:
        Dict mapping CUDA version string to CUDAEnvironment
    """
    base_path = Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA")
    environments = {}

    if not base_path.exists():
        return environments

    for version_dir in base_path.iterdir():
        if not version_dir.is_dir():
            continue

        version = version_dir.name.replace("v", "")

        nvcc = version_dir / "bin" / "nvcc.exe"
        nvdisasm = version_dir / "bin" / "nvdisasm.exe"
        cuobjdump = version_dir / "bin" / "cuobjdump.exe"

        if nvcc.exists() and nvdisasm.exists() and cuobjdump.exists():
            env = CUDAEnvironment(
                cuda_version=version,
                nvcc_path=nvcc,
                nvdisasm_path=nvdisasm,
                cuobjdump_path=cuobjdump
            )

            # Try to get GPU info
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=compute_cap,driver_version",
                     "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(", ")
                    env.gpu_compute_capability = parts[0]
                    env.driver_version = parts[1]
            except:
                pass

            environments[version] = env

    return environments


def validate_cubin(cubin_path: Path) -> Tuple[bool, str]:
    """
    基础 CUBIN 文件格式检查（初步识别，不代表有效 CUDA 二进制）

    警告：此检查仅验证魔数，不保证文件完全有效。
    完整验证需由 nvdisasm 或其他 CUDA 工具执行。

    Args:
        cubin_path: Path to .cubin file

    Returns:
        Tuple of (looks_like_cuda_format, message)
    """
    if not cubin_path.exists():
        return False, f"File not found: {cubin_path}"

    data = cubin_path.read_bytes()

    # CUBIN/FATBIN magic check
    if len(data) < 4:
        return False, f"File too small ({len(data)} bytes) - not CUDA binary format"

    # CUDA ELF magic: 7f 45 4c 46 (ELF header)
    if data[:4] == b'\x7fELF':
        return True, f"ELF format detected ({len(data)} bytes) - PRELIMINARY, requires tool validation"

    # FATBIN magic: 0xba55ed50 (little-endian)
    if len(data) >= 4 and int.from_bytes(data[:4], 'little') == 0xba55ed50:
        return True, f"FATBIN format detected ({len(data)} bytes) - PRELIMINARY, requires tool validation"

    return False, f"Unrecognized format (first 4 bytes: {data[:4].hex()}) - not recognized as CUDA binary"


def execute_nvdisasm(
    env: CUDAEnvironment,
    input_file: Path,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    以受控方式执行 nvdisasm，完整保存所有证据

    Args:
        env: CUDA environment to use
        input_file: Path to .cubin or .o file
        timeout: Execution timeout in seconds

    Returns:
        Execution record dict with complete evidence
    """
    is_valid, validation_msg = validate_cubin(input_file)

    if not is_valid:
        return {
            "status": "FORMAT_CHECK_FAILED",
            "validation_message": validation_msg,
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "input_file": str(input_file),
            "input_size": input_file.stat().st_size if input_file.exists() else None
        }

    # Calculate input hash
    input_sha256 = hashlib.sha256(input_file.read_bytes()).hexdigest()

    # Get tool binary hash
    tool_sha256 = hashlib.sha256(env.nvdisasm_path.read_bytes()).hexdigest()

    try:
        result = subprocess.run(
            [str(env.nvdisasm_path), str(input_file)],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "status": "EXECUTED",
            "cuda_version": env.cuda_version,
            "tool_path": str(env.nvdisasm_path),
            "tool_binary_sha256": tool_sha256,
            "input_file": str(input_file),
            "input_size": input_file.stat().st_size,
            "input_sha256": input_sha256,
            "return_code": result.returncode,
            "stdout_length": len(result.stdout),
            "stderr_length": len(result.stderr),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": f'"{env.nvdisasm_path}" "{input_file}"',
            "exit_status": "success" if result.returncode == 0 else f"non-zero ({result.returncode})"
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "cuda_version": env.cuda_version,
            "tool_path": str(env.nvdisasm_path),
            "timeout_seconds": timeout,
            "input_file": str(input_file),
            "return_code": None,
            "stdout": "",
            "stderr": f"Execution exceeded {timeout} seconds",
            "exit_status": "timeout"
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "cuda_version": env.cuda_version,
            "tool_path": str(env.nvdisasm_path),
            "error": str(e),
            "input_file": str(input_file),
            "return_code": None,
            "stdout": "",
            "stderr": str(e),
            "exit_status": "error"
        }


def get_environment_report() -> Dict[str, Any]:
    """Generate complete environment capability report"""
    environments = detect_cuda_environments()

    return {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "available_versions": list(environments.keys()),
        "environments": {
            ver: {
                "cuda_version": env.cuda_version,
                "complete": env.is_complete(),
                "gpu_compute_capability": env.gpu_compute_capability,
                "driver_version": env.driver_version
            }
            for ver, env in environments.items()
        },
        "capable_of": {
            "baseline_cubin_generation": len(environments) > 0,
            "cubin_disassembly": len(environments) > 0,
            "multi_version_comparison": len(environments) >= 2
        }
    }
