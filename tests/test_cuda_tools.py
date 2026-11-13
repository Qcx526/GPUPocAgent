"""Test CUDA tools"""

import pytest
from pathlib import Path
import tempfile
import os

from src.tools.cuda_tools import (
    detect_cuda_environment,
    write_cuda_source,
    compile_cuda_code,
    execute_cuda_program,
)


def test_detect_cuda_environment():
    """Test CUDA environment detection"""
    result = detect_cuda_environment.invoke({})

    print(f"\nCUDA Detection Result: {result}")

    # Should detect CUDA on this system
    assert isinstance(result, dict)
    assert "nvcc_available" in result
    assert "gpu_available" in result

    # System should have CUDA
    assert result["nvcc_available"] is True
    assert result["nvcc_path"] is not None
    assert "13.4" in result["nvcc_version"]  # CUDA 13.4

    # Should have GPU
    assert result["gpu_available"] is True
    assert result["gpu_info"] is not None


def test_write_cuda_source():
    """Test writing CUDA source code"""
    with tempfile.TemporaryDirectory() as tmpdir:
        code = """
#include <stdio.h>

int main() {
    printf("Hello from CUDA test\\n");
    return 0;
}
"""
        result = write_cuda_source.invoke({
            "code": code,
            "filename": "test.cu",
            "output_dir": tmpdir
        })

        print(f"\nWrite Result: {result}")

        assert result["success"] is True
        assert Path(result["file_path"]).exists()
        assert Path(result["file_path"]).read_text() == code


@pytest.mark.skipif(
    not Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.4/bin/nvcc.exe").exists(),
    reason="Requires CUDA nvcc compiler"
)
def test_compile_and_execute_simple_cuda():
    """Test compiling and executing a simple CUDA program"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Simple CUDA program
        cuda_code = """
#include <stdio.h>

__global__ void hello_kernel() {
    printf("Hello from GPU thread %d\\n", threadIdx.x);
}

int main() {
    printf("Launching kernel...\\n");
    hello_kernel<<<1, 5>>>();
    cudaDeviceSynchronize();
    printf("Kernel completed\\n");
    return 0;
}
"""

        # Write source
        source_file = tmpdir_path / "hello.cu"
        write_result = write_cuda_source.invoke({
            "code": cuda_code,
            "filename": "hello.cu",
            "output_dir": str(tmpdir_path)
        })

        assert write_result["success"] is True
        print(f"\nSource written to: {write_result['file_path']}")

        # Compile
        output_exe = str(tmpdir_path / "hello")
        compile_result = compile_cuda_code.invoke({
            "source_file": str(source_file),
            "output_file": output_exe,
            "compute_capability": "75"  # GTX 1660
        })

        print(f"\nCompile Result: {compile_result}")
        print(f"STDOUT: {compile_result['stdout']}")
        print(f"STDERR: {compile_result['stderr']}")

        assert compile_result["success"] is True, f"Compilation failed: {compile_result['stderr']}"

        # Execute
        exec_result = execute_cuda_program.invoke({
            "executable_path": output_exe + ".exe",  # Windows adds .exe
            "timeout_seconds": 10
        })

        print(f"\nExecution Result: {exec_result}")
        print(f"STDOUT: {exec_result['stdout']}")
        print(f"STDERR: {exec_result['stderr']}")

        assert exec_result["success"] is True
        assert "Hello from GPU" in exec_result["stdout"]
        assert "Kernel completed" in exec_result["stdout"]


def test_compile_invalid_code():
    """Test that compilation errors are properly captured"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Invalid CUDA code
        invalid_code = """
#include <stdio.h>

int main() {
    this_function_does_not_exist();
    return 0;
}
"""

        source_file = tmpdir_path / "invalid.cu"
        write_cuda_source.invoke({
            "code": invalid_code,
            "filename": "invalid.cu",
            "output_dir": str(tmpdir_path)
        })

        output_exe = str(tmpdir_path / "invalid")
        compile_result = compile_cuda_code.invoke({
            "source_file": str(source_file),
            "output_file": output_exe,
            "compute_capability": "75"
        })

        print(f"\nInvalid Compile Result: {compile_result}")

        assert compile_result["success"] is False
        assert compile_result["return_code"] != 0
        assert len(compile_result["stderr"]) > 0  # Should have error message


if __name__ == "__main__":
    # Run tests manually
    print("Testing CUDA tools...")
    test_detect_cuda_environment()
    test_write_cuda_source()
    test_compile_and_execute_simple_cuda()
    test_compile_invalid_code()
    print("\nAll tests passed!")
