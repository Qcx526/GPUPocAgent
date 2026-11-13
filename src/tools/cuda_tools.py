"""GPU and CUDA environment detection tools"""

import subprocess
import shutil
from typing import Optional, Dict, Any
from pathlib import Path

from langchain_core.tools import tool

# Import workspace configuration
try:
    from src.config import workspace_root
except ImportError:
    from config import workspace_root


@tool
def detect_cuda_environment() -> Dict[str, Any]:
    """Detect CUDA toolkit and GPU availability.

    Returns:
        Dictionary with CUDA environment information including:
        - nvcc_available: bool
        - nvcc_version: str or None
        - nvcc_path: str or None
        - gpu_available: bool
        - gpu_info: dict or None
    """
    result = {
        "nvcc_available": False,
        "nvcc_version": None,
        "nvcc_path": None,
        "gpu_available": False,
        "gpu_info": None,
    }

    # Check nvcc
    nvcc_path = shutil.which("nvcc")
    if nvcc_path:
        result["nvcc_available"] = True
        result["nvcc_path"] = nvcc_path

        try:
            # Get nvcc version
            proc = subprocess.run(
                ["nvcc", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0:
                # Parse version from output
                output = proc.stdout
                for line in output.split('\n'):
                    if 'release' in line.lower():
                        result["nvcc_version"] = line.strip()
                        break
        except Exception as e:
            result["nvcc_version"] = f"Error getting version: {e}"

    # Check GPU via nvidia-smi
    nvidia_smi_path = shutil.which("nvidia-smi")
    if nvidia_smi_path:
        try:
            proc = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,compute_cap,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0 and proc.stdout.strip():
                result["gpu_available"] = True
                # Parse GPU info
                lines = proc.stdout.strip().split('\n')
                if lines:
                    parts = lines[0].split(',')
                    if len(parts) >= 3:
                        result["gpu_info"] = {
                            "name": parts[0].strip(),
                            "compute_capability": parts[1].strip(),
                            "memory_mb": parts[2].strip(),
                        }
        except Exception as e:
            result["gpu_info"] = f"Error querying GPU: {e}"

    return result


@tool
def write_cuda_source(code: str, filename: str, output_dir: str = None, task_id: str = "default_task", run_id: str = "auto") -> Dict[str, Any]:
    """Write CUDA source code to a file.

    Args:
        code: CUDA C/C++ source code
        filename: Output filename (should end with .cu or .cpp)
        output_dir: Directory to write file (default: workspace source dir for this task)
        task_id: Research task identifier (used for workspace organization)
        run_id: Run identifier (auto-generated if "auto")

    Returns:
        Dictionary with:
        - success: bool
        - file_path: str (absolute path)
        - message: str
    """
    try:
        if output_dir is None or output_dir == ".":
            # Use workspace structure
            if run_id == "auto":
                import uuid
                run_id = str(uuid.uuid4())[:8]
            ws_root = workspace_root()
            output_path = ws_root / "runs" / task_id / run_id / "source" / filename
        else:
            output_path = Path(output_dir) / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code, encoding='utf-8')

        return {
            "success": True,
            "file_path": str(output_path.absolute()),
            "message": f"Successfully wrote {len(code)} bytes to {filename}"
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": None,
            "message": f"Error writing file: {e}"
        }


@tool
def compile_cuda_code(
    source_file: str,
    output_file: str = "output",
    compute_capability: str = "75",
    extra_flags: Optional[str] = None
) -> Dict[str, Any]:
    """Compile CUDA source code with nvcc.

    Args:
        source_file: Path to .cu source file
        output_file: Output executable name (without extension)
        compute_capability: GPU compute capability (default: 75 for GTX 1660)
        extra_flags: Additional compiler flags (optional)

    Returns:
        Dictionary with:
        - success: bool
        - output_path: str or None
        - stdout: str
        - stderr: str
        - return_code: int
    """
    try:
        # Build nvcc command
        cmd = [
            "nvcc",
            f"-arch=sm_{compute_capability}",
            source_file,
            "-o", output_file
        ]

        if extra_flags:
            cmd.extend(extra_flags.split())

        # Run compilation
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )

        success = proc.returncode == 0
        output_path = str(Path(output_file).absolute()) if success else None

        return {
            "success": success,
            "output_path": output_path,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "return_code": proc.returncode,
            "command": " ".join(cmd)
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output_path": None,
            "stdout": "",
            "stderr": "Compilation timeout (60 seconds)",
            "return_code": -1,
            "command": " ".join(cmd)
        }
    except Exception as e:
        return {
            "success": False,
            "output_path": None,
            "stdout": "",
            "stderr": f"Error during compilation: {e}",
            "return_code": -1,
            "command": "nvcc (failed to execute)"
        }


@tool
def execute_cuda_program(
    executable_path: str,
    timeout_seconds: int = 10,
    working_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a compiled CUDA program.

    Args:
        executable_path: Path to executable
        timeout_seconds: Execution timeout (default: 10)
        working_dir: Working directory (default: current directory)

    Returns:
        Dictionary with:
        - success: bool (True if exit code 0)
        - stdout: str
        - stderr: str
        - return_code: int
        - timed_out: bool
    """
    try:
        proc = subprocess.run(
            [executable_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=working_dir
        )

        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "return_code": proc.returncode,
            "timed_out": False
        }

    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "stdout": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else "",
            "return_code": -1,
            "timed_out": True
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Error executing program: {e}",
            "return_code": -1,
            "timed_out": False
        }


# Export all tools
CUDA_TOOLS = [
    detect_cuda_environment,
    write_cuda_source,
    compile_cuda_code,
    execute_cuda_program,
]
