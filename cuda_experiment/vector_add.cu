// Vector addition: C[i] = A[i] + B[i]
// Includes device info query and CPU-side result verification.
// Notes: CUDA 13 removed several deprecated cudaDeviceProp fields
//        (memoryClockRate, memoryBusWidth, clockRate ...), so only
//        portable fields are printed here.

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <vector>

__global__ void vecAdd(const float* __restrict__ A,
                       const float* __restrict__ B,
                       float* __restrict__ C,
                       int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        C[i] = A[i] + B[i];
    }
}

#define CUDA_CHECK(call)                                                      \
    do {                                                                      \
        cudaError_t err = (call);                                             \
        if (err != cudaSuccess) {                                             \
            fprintf(stderr, "CUDA error at %s:%d -> %s\n", __FILE__,          \
                    __LINE__, cudaGetErrorString(err));                       \
            exit(EXIT_FAILURE);                                               \
        }                                                                     \
    } while (0)

int main()
{
    // ---- Report device details -------------------------------------------
    int deviceCount = 0;
    CUDA_CHECK(cudaGetDeviceCount(&deviceCount));
    printf("CUDA devices found: %d\n", deviceCount);
    if (deviceCount == 0) {
        fprintf(stderr, "No CUDA devices available.\n");
        return EXIT_FAILURE;
    }

    cudaDeviceProp prop{};
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    printf("Device 0: %s\n", prop.name);
    printf("  Compute capability : %d.%d\n", prop.major, prop.minor);
    printf("  Multiprocessors    : %d\n", prop.multiProcessorCount);
    printf("  Global memory      : %.2f GiB\n",
           prop.totalGlobalMem / (1024.0 * 1024.0 * 1024.0));
    printf("  Max threads/block  : %d\n", prop.maxThreadsPerBlock);
    printf("  Max threads/SM     : %d\n", prop.maxThreadsPerMultiProcessor);
    printf("  Shared mem/block   : %.1f KiB\n", prop.sharedMemPerBlock / 1024.0);
    printf("  L2 cache size      : %.1f MiB\n",
           prop.l2CacheSize / (1024.0 * 1024.0));
    printf("  Runtime version    : %d.%d\n", CUDART_VERSION / 1000,
           (CUDART_VERSION % 1000) / 10);

    // ---- Problem setup ---------------------------------------------------
    const int n = 1 << 20;               // 1,048,576 elements
    const size_t bytes = n * sizeof(float);

    printf("\nVector length n = %d elements (%zu bytes per array)\n", n, bytes);

    std::vector<float> h_A(n), h_B(n), h_C(n), h_ref(n);
    for (int i = 0; i < n; ++i) {
        h_A[i] = static_cast<float>(i) * 0.5f;
        h_B[i] = static_cast<float>(i) * 0.25f;
        h_ref[i] = h_A[i] + h_B[i];
    }

    float *d_A = nullptr, *d_B = nullptr, *d_C = nullptr;
    CUDA_CHECK(cudaMalloc(&d_A, bytes));
    CUDA_CHECK(cudaMalloc(&d_B, bytes));
    CUDA_CHECK(cudaMalloc(&d_C, bytes));

    CUDA_CHECK(cudaMemcpy(d_A, h_A.data(), bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, h_B.data(), bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemset(d_C, 0, bytes));

    // ---- Launch ----------------------------------------------------------
    const int threadsPerBlock = 256;
    const int blocks = (n + threadsPerBlock - 1) / threadsPerBlock;
    printf("Launch config: %d blocks x %d threads = %d threads\n", blocks,
           threadsPerBlock, blocks * threadsPerBlock);

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    vecAdd<<<blocks, threadsPerBlock>>>(d_A, d_B, d_C, n);  // warm-up
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    const int iterations = 100;
    CUDA_CHECK(cudaEventRecord(start));
    for (int it = 0; it < iterations; ++it) {
        vecAdd<<<blocks, threadsPerBlock>>>(d_A, d_B, d_C, n);
    }
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));
    CUDA_CHECK(cudaGetLastError());

    float ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));
    double avg_ms = ms / iterations;
    double gbytes = 3.0 * bytes / (1024.0 * 1024.0 * 1024.0);  // 2 reads + 1 write
    printf("Average kernel time : %.4f ms  (achieved %.2f GB/s)\n", avg_ms,
           gbytes / (avg_ms * 1e-3));

    CUDA_CHECK(cudaMemcpy(h_C.data(), d_C, bytes, cudaMemcpyDeviceToHost));

    // ---- Verification ----------------------------------------------------
    int mismatches = 0;
    int first_bad = -1;
    float max_abs_err = 0.0f;
    for (int i = 0; i < n; ++i) {
        float err = std::fabs(h_C[i] - h_ref[i]);
        if (err > max_abs_err) max_abs_err = err;
        if (err > 1e-5f) {
            if (mismatches == 0) first_bad = i;
            ++mismatches;
        }
    }

    printf("\n--- Verification ---\n");
    printf("Elements compared   : %d\n", n);
    printf("Mismatches          : %d\n", mismatches);
    printf("Max absolute error  : %g\n", max_abs_err);
    if (mismatches == 0) {
        printf("Sample: C[0]=%.2f C[1]=%.2f C[%d]=%.2f  (all match reference)\n",
               h_C[0], h_C[1], n - 1, h_C[n - 1]);
        printf("RESULT: PASS\n");
    } else {
        printf("First mismatch at index %d: got %f expected %f\n", first_bad,
               h_C[first_bad], h_ref[first_bad]);
        printf("RESULT: FAIL\n");
    }

    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));

    return (mismatches == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}