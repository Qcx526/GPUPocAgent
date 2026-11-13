#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cuda_runtime.h>

// One-thread-per-element vector addition kernel
__global__ void vectorAdd(const float *a, const float *b, float *c, int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

// Alternative: grid-stride loop version, for comparison
__global__ void vectorAddGridStride(const float *a, const float *b, float *c, int n)
{
    for (int idx = blockIdx.x * blockDim.x + threadIdx.x; idx < n;
         idx += blockDim.x * gridDim.x) {
        c[idx] = a[idx] + b[idx];
    }
}

#define CUDA_CHECK(call)                                                       \
    do {                                                                       \
        cudaError_t err = (call);                                              \
        if (err != cudaSuccess) {                                              \
            fprintf(stderr, "CUDA error at %s:%d -> %s\n", __FILE__, __LINE__,  \
                    cudaGetErrorString(err));                                  \
            exit(EXIT_FAILURE);                                                \
        }                                                                      \
    } while (0)

// Run one kernel variant, return elapsed ms, and verify results
static float runAndVerify(const char *label, bool useGridStride,
                          float *d_a, float *d_b, float *d_c,
                          const float *h_a, const float *h_b, float *h_c,
                          int N, size_t bytes, int &mismatchesOut)
{
    const int threadsPerBlock = 256;
    const int blocksPerGrid = (N + threadsPerBlock - 1) / threadsPerBlock;

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    CUDA_CHECK(cudaEventRecord(start));
    if (useGridStride) {
        vectorAddGridStride<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, N);
    } else {
        vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, N);
    }
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));

    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

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
    mismatchesOut = mismatches;

    printf("%-22s %10.4f ms   max_abs_err=%.3e   %s (%d/%d bad)\n",
           label, ms, maxAbsErr, (mismatches == 0) ? "PASS" : "FAIL", mismatches, N);

    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    return ms;
}

int main()
{
    const int N = 1 << 20;                 // 1,048,576 elements
    const size_t bytes = N * sizeof(float);

    printf("=== CUDA Vector Addition ===\n");
    printf("N = %d elements (%.2f MiB per array)\n\n", N, bytes / (1024.0 * 1024.0));

    // ---- Host allocation (pinned) ----
    float *h_a = nullptr, *h_b = nullptr, *h_c = nullptr;
    CUDA_CHECK(cudaMallocHost((void **)&h_a, bytes));
    CUDA_CHECK(cudaMallocHost((void **)&h_b, bytes));
    CUDA_CHECK(cudaMallocHost((void **)&h_c, bytes));

    // a[i] = i, b[i] = 2i  ->  c[i] = 3i.
    // Using integer-valued floats keeps the reference exact, so we can demand
    // bit-exact agreement from the kernel.
    for (int i = 0; i < N; ++i) {
        h_a[i] = static_cast<float>(i);
        h_b[i] = static_cast<float>(i) * 2.0f;
    }

    // ---- Device allocation ----
    float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc((void **)&d_a, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_b, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_c, bytes));

    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    // ---- Timing / verification for both variants ----
    printf("Kernel timings and verification:\n");
    int mm1 = 0, mm2 = 0;
    runAndVerify("vectorAdd", false, d_a, d_b, d_c, h_a, h_b, h_c, N, bytes, mm1);
    runAndVerify("grid-stride", true, d_a, d_b, d_c, h_a, h_b, h_c, N, bytes, mm2);
    printf("\n");

    // ---- Concrete spot checks (h_c holds the last run's results) ----
    const int probes[] = {0, 1, 255, 1023, N / 2, N - 1};
    printf("Spot checks (a=i, b=2i, so c must equal 3i):\n");
    printf("  %10s %12s %12s %12s %12s %6s\n",
           "index", "a[i]", "b[i]", "c[i]", "3*i", "status");
    for (int p = 0; p < 6; ++p) {
        int i = probes[p];
        float expected = 3.0f * static_cast<float>(i);
        printf("  %10d %12.1f %12.1f %12.1f %12.1f %6s\n", i, h_a[i], h_b[i], h_c[i],
               expected, (h_c[i] == expected) ? "OK" : "BAD");
    }

    // ---- Final verdict ----
    printf("\n");
    if (mm1 == 0 && mm2 == 0) {
        printf("RESULT: PASS - both kernels produced correct results for all %d elements.\n", N);
    } else {
        printf("RESULT: FAIL - mismatches (vectorAdd=%d, grid-stride=%d).\n", mm1, mm2);
    }

    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    CUDA_CHECK(cudaFreeHost(h_a));
    CUDA_CHECK(cudaFreeHost(h_b));
    CUDA_CHECK(cudaFreeHost(h_c));

    return (mm1 == 0 && mm2 == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}