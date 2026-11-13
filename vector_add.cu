#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cuda_runtime.h>

#define CUDA_CHECK(call)                                                        \
    do {                                                                        \
        cudaError_t err = (call);                                               \
        if (err != cudaSuccess) {                                               \
            fprintf(stderr, "CUDA error at %s:%d -> %s\n", __FILE__, __LINE__,  \
                    cudaGetErrorString(err));                                   \
            exit(EXIT_FAILURE);                                                 \
        }                                                                       \
    } while (0)

__global__ void vecAdd(const float *a, const float *b, float *c, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

int main() {
    const int n = 1 << 20;                 // 1,048,576 elements
    const size_t bytes = n * sizeof(float);

    // Report device info
    int dev = 0;
    CUDA_CHECK(cudaGetDevice(&dev));
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, dev));
    printf("Device: %s\n", prop.name);
    printf("Compute capability: %d.%d\n", prop.major, prop.minor);
    printf("Multiprocessors: %d\n", prop.multiProcessorCount);
    printf("N = %d elements (%.2f MiB per array)\n\n", n, bytes / (1024.0 * 1024.0));

    // Host allocation (pageable)
    float *h_a = (float *)malloc(bytes);
    float *h_b = (float *)malloc(bytes);
    float *h_c = (float *)malloc(bytes);
    float *h_ref = (float *)malloc(bytes);
    if (!h_a || !h_b || !h_c || !h_ref) {
        fprintf(stderr, "Host malloc failed\n");
        return EXIT_FAILURE;
    }

    for (int i = 0; i < n; ++i) {
        h_a[i] = 1.0f * (i % 1024);
        h_b[i] = 2.0f * (i % 512);
        h_ref[i] = h_a[i] + h_b[i];
    }

    // Device allocation
    float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc(&d_a, bytes));
    CUDA_CHECK(cudaMalloc(&d_b, bytes));
    CUDA_CHECK(cudaMalloc(&d_c, bytes));

    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemset(d_c, 0, bytes));

    const int threadsPerBlock = 256;
    const int blocks = (n + threadsPerBlock - 1) / threadsPerBlock;
    printf("Launch config: %d blocks x %d threads = %d threads\n",
           blocks, threadsPerBlock, blocks * threadsPerBlock);

    // Warm-up + timing
    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    vecAdd<<<blocks, threadsPerBlock>>>(d_a, d_b, d_c, n);
    CUDA_CHECK(cudaGetLastError());

    const int iters = 100;
    CUDA_CHECK(cudaEventRecord(start));
    for (int i = 0; i < iters; ++i) {
        vecAdd<<<blocks, threadsPerBlock>>>(d_a, d_b, d_c, n);
    }
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));
    double avg_ms = ms / iters;
    double gbps = (3.0 * bytes) / (avg_ms * 1e-3) / 1e9;
    printf("Avg kernel time: %.4f ms  (~%.1f GB/s effective)\n", avg_ms, gbps);

    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

    // Verify
    int mismatches = 0;
    float max_abs_err = 0.0f;
    for (int i = 0; i < n; ++i) {
        float err = fabsf(h_c[i] - h_ref[i]);
        if (err > max_abs_err) max_abs_err = err;
        if (err > 1e-5f) {
            if (mismatches < 5) {
                printf("MISMATCH at %d: got %f expected %f\n", i, h_c[i], h_ref[i]);
            }
            ++mismatches;
        }
    }

    printf("\nVerification: %d / %d mismatches, max abs error = %g\n",
           mismatches, n, max_abs_err);
    printf("Sample: c[0]=%f (exp %f), c[12345]=%f (exp %f), c[%d]=%f (exp %f)\n",
           h_c[0], h_ref[0], h_c[12345], h_ref[12345], n - 1, h_c[n - 1], h_ref[n - 1]);

    // Cleanup
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    free(h_a); free(h_b); free(h_c); free(h_ref);

    if (mismatches == 0) {
        printf("RESULT: PASS\n");
        return EXIT_SUCCESS;
    }
    printf("RESULT: FAIL\n");
    return EXIT_FAILURE;
}