#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cuda_runtime.h>

// Simple one-thread-per-element vector addition kernel
__global__ void vectorAdd(const float *a, const float *b, float *c, int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

#define CUDA_CHECK(call)                                                      \
    do {                                                                      \
        cudaError_t err = (call);                                             \
        if (err != cudaSuccess) {                                             \
            fprintf(stderr, "CUDA error at %s:%d -> %s\n", __FILE__, __LINE__, \
                    cudaGetErrorString(err));                                 \
            exit(EXIT_FAILURE);                                               \
        }                                                                     \
    } while (0)

int main()
{
    const int N = 1 << 20;                 // 1,048,576 elements
    const size_t bytes = N * sizeof(float);
    const int threadsPerBlock = 256;
    const int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;

    printf("Vector addition: N = %d elements (%.2f MiB per array)\n",
           N, bytes / (1024.0 * 1024.0));
    printf("Launch config: %d blocks x %d threads\n", blocksPerGrid, threadsPerBlock);

    // ---- Host allocation (pinned for faster transfers) ----
    float *h_a = nullptr, *h_b = nullptr, *h_c = nullptr;
    CUDA_CHECK(cudaMallocHost((void **)&h_a, bytes));
    CUDA_CHECK(cudaMallocHost((void **)&h_b, bytes));
    CUDA_CHECK(cudaMallocHost((void **)&h_c, bytes));

    for (int i = 0; i < N; ++i) {
        h_a[i] = static_cast<float>(i) * 1.0f;
        h_b[i] = static_cast<float>(i) * 2.0f;
    }

    // ---- Device allocation ----
    float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc((void **)&d_a, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_b, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_c, bytes));

    // ---- H2D transfers ----
    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    // ---- Kernel launch (timed) ----
    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));
    vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, N);
    CUDA_CHECK(cudaGetLastError());        // catch launch errors
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));
    printf("Kernel execution time: %.4f ms\n", ms);

    // ---- D2H transfer ----
    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

    // ---- Verification on the host ----
    int mismatches = 0;
    double maxAbsErr = 0.0;
    for (int i = 0; i < N; ++i) {
        float expected = h_a[i] + h_b[i];
        double err = fabs(static_cast<double>(h_c[i] - expected));
        if (err > maxAbsErr) maxAbsErr = err;
        if (err > 1e-5) {
            if (mismatches < 5) {
                printf("  MISMATCH at %d: got %f, expected %f\n", i, h_c[i], expected);
            }
            ++mismatches;
        }
    }

    printf("Max absolute error: %.6e\n", maxAbsErr);
    if (mismatches == 0) {
        printf("RESULT: PASS - all %d elements verified.\n", N);
    } else {
        printf("RESULT: FAIL - %d of %d elements mismatched.\n", mismatches, N);
    }

    // ---- Cleanup ----
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    CUDA_CHECK(cudaFreeHost(h_a));
    CUDA_CHECK(cudaFreeHost(h_b));
    CUDA_CHECK(cudaFreeHost(h_c));

    return (mismatches == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}