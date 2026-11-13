// Vector addition on GPU - CUDA experiment
// Target: NVIDIA GeForce GTX 1660 (compute capability 7.5)
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cuda_runtime.h>

#define N (1 << 20)          // 1,048,576 elements
#define THREADS 256

// GPU kernel: one thread per element
__global__ void vectorAdd(const float *a, const float *b, float *c, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

#define CUDA_CHECK(call)                                                       \
    do {                                                                       \
        cudaError_t err = (call);                                              \
        if (err != cudaSuccess) {                                              \
            fprintf(stderr, "CUDA error at %s:%d -> %s\n", __FILE__, __LINE__, \
                    cudaGetErrorString(err));                                  \
            exit(EXIT_FAILURE);                                                \
        }                                                                      \
    } while (0)

int main() {
    const size_t bytes = N * sizeof(float);

    // Print device info
    int dev = 0;
    CUDA_CHECK(cudaGetDevice(&dev));
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, dev));
    printf("Device %d: %s\n", dev, prop.name);
    printf("Compute capability: %d.%d\n", prop.major, prop.minor);
    printf("Total global memory: %.1f MiB\n", prop.totalGlobalMem / (1024.0 * 1024.0));
    printf("Vector size N = %d floats (%.2f MiB each array)\n",
           N, bytes / (1024.0 * 1024.0));

    // Allocate host memory
    float *h_a = (float *)malloc(bytes);
    float *h_b = (float *)malloc(bytes);
    float *h_c = (float *)malloc(bytes);
    if (!h_a || !h_b || !h_c) {
        fprintf(stderr, "Host allocation failed\n");
        return EXIT_FAILURE;
    }

    // Initialize host data
    for (int i = 0; i < N; i++) {
        h_a[i] = static_cast<float>(i) * 0.5f;
        h_b[i] = static_cast<float>(i) * 0.25f;
    }

    // Allocate device memory
    float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc(&d_a, bytes));
    CUDA_CHECK(cudaMalloc(&d_b, bytes));
    CUDA_CHECK(cudaMalloc(&d_c, bytes));

    // Copy inputs to device
    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    // Launch kernel
    int blocks = (N + THREADS - 1) / THREADS;
    printf("Launching kernel: %d blocks x %d threads\n", blocks, THREADS);

    // Timing with events
    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));

    vectorAdd<<<blocks, THREADS>>>(d_a, d_b, d_c, N);
    CUDA_CHECK(cudaGetLastError());

    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));
    float ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));
    printf("Kernel execution time: %.4f ms\n", ms);

    // Copy result back
    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

    // Verify results on CPU
    int mismatches = 0;
    for (int i = 0; i < N; i++) {
        float expected = h_a[i] + h_b[i];
        if (fabsf(h_c[i] - expected) > 1e-5f) {
            if (mismatches < 5) {
                printf("MISMATCH at index %d: got %f, expected %f\n",
                       i, h_c[i], expected);
            }
            mismatches++;
        }
    }

    printf("Verification: %d mismatches out of %d elements\n", mismatches, N);
    printf("Sample results: c[0]=%f, c[1]=%f, c[1000]=%f, c[N-1]=%f\n",
           h_c[0], h_c[1], h_c[1000], h_c[N - 1]);

    // Cleanup
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    free(h_a);
    free(h_b);
    free(h_c);

    if (mismatches == 0) {
        printf("RESULT: SUCCESS - vector addition verified correct.\n");
        return EXIT_SUCCESS;
    } else {
        printf("RESULT: FAILURE - incorrect results.\n");
        return EXIT_FAILURE;
    }
}