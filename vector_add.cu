#include <cstdio>
#include <cstdlib>
#include <cmath>

// ---------------------------------------------------------------------------
// Vector addition: C[i] = A[i] + B[i]
//   - Each thread computes one element
//   - Grid-stride loop so the code works for any N
//   - CUDA error checking on every API call
// ---------------------------------------------------------------------------

#define CUDA_CHECK(call)                                                      \
    do {                                                                      \
        cudaError_t err__ = (call);                                           \
        if (err__ != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA error at %s:%d -> %s\n", __FILE__,         \
                    __LINE__, cudaGetErrorString(err__));                     \
            exit(EXIT_FAILURE);                                               \
        }                                                                     \
    } while (0)

__global__ void vectorAdd(const float * __restrict__ A,
                          const float * __restrict__ B,
                          float * __restrict__ C,
                          int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int stride = blockDim.x * gridDim.x;

    for (int i = idx; i < n; i += stride) {
        C[i] = A[i] + B[i];
    }
}

int main(int argc, char **argv)
{
    // Problem size (overridable from the command line)
    int n = (argc > 1) ? atoi(argv[1]) : (1 << 20);
    if (n <= 0) {
        fprintf(stderr, "Vector size must be positive.\n");
        return EXIT_FAILURE;
    }

    const size_t bytes = (size_t)n * sizeof(float);

    printf("Vector addition: N = %d  (%.2f MiB per array)\n", n,
           (double)bytes / (1024.0 * 1024.0));

    // ---- Host allocations (pinned memory for faster transfers) -------------
    float *h_A = nullptr, *h_B = nullptr, *h_C = nullptr;
    CUDA_CHECK(cudaHostAlloc((void **)&h_A, bytes, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void **)&h_B, bytes, cudaHostAllocDefault));
    CUDA_CHECK(cudaHostAlloc((void **)&h_C, bytes, cudaHostAllocDefault));

    for (int i = 0; i < n; ++i) {
        h_A[i] = 1.0f * i;
        h_B[i] = 2.0f * i;
    }

    // ---- Device allocations ------------------------------------------------
    float *d_A = nullptr, *d_B = nullptr, *d_C = nullptr;
    CUDA_CHECK(cudaMalloc((void **)&d_A, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_B, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_C, bytes));

    // ---- Events for timing host->device / kernel / device->host ------------
    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    CUDA_CHECK(cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, h_B, bytes, cudaMemcpyHostToDevice));

    // ---- Launch configuration ---------------------------------------------
    const int threadsPerBlock = 256;
    int blocksPerGrid = (n + threadsPerBlock - 1) / threadsPerBlock;
    const int maxBlocks = 65535;  // conservative limit for grid dimension
    if (blocksPerGrid > maxBlocks) blocksPerGrid = maxBlocks;

    printf("Launch: %d blocks x %d threads\n", blocksPerGrid, threadsPerBlock);

    CUDA_CHECK(cudaEventRecord(start));
    vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float kernelMs = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&kernelMs, start, stop));

    CUDA_CHECK(cudaMemcpy(h_C, d_C, bytes, cudaMemcpyDeviceToHost));

    // ---- Verify ------------------------------------------------------------
    int errors = 0;
    for (int i = 0; i < n; ++i) {
        float expected = h_A[i] + h_B[i];
        if (fabsf(h_C[i] - expected) > 1e-5f * fmaxf(1.0f, fabsf(expected))) {
            if (errors < 5) {
                fprintf(stderr, "Mismatch at %d: got %f, expected %f\n",
                        i, h_C[i], expected);
            }
            ++errors;
        }
    }

    printf("Kernel time: %.3f ms\n", kernelMs);
    printf("Result: %s (%d mismatches out of %d elements)\n",
           (errors == 0) ? "PASS" : "FAIL", errors, n);
    printf("Sample: C[0]=%.1f  C[%d]=%.1f  C[%d]=%.1f\n",
           h_C[0], n / 2, h_C[n / 2], n - 1, h_C[n - 1]);

    // ---- Cleanup -----------------------------------------------------------
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));
    CUDA_CHECK(cudaFreeHost(h_A));
    CUDA_CHECK(cudaFreeHost(h_B));
    CUDA_CHECK(cudaFreeHost(h_C));

    return (errors == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
