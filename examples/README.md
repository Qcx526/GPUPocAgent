# CUDA Examples

Reference implementations and reproducible test cases for GPU research.

## vector_add.cu

A well-tested vector addition kernel with:
- Device capability detection
- Comprehensive error checking
- Performance measurement (GB/s)
- Full result verification

**Usage:**
```bash
nvcc -arch=sm_75 vector_add.cu -o vector_add
./vector_add
```

**Output:**
Reports GPU device info, kernel performance, and verification status.

**Historical note:**
Originally in `cuda_experiment/vector_add.cu`, preserved as a reproducible reference.
