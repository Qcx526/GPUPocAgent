```cuda
// vector_add.cu
// Simple CUDA vector addition for cross-process test
// Target: NVIDIA GeForce GTX 1660 (compute capability 7.5, sm_75)
// Build:  nvcc -arch=sm_75 -O2 -o vector_add vector_add.cu

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cuda_runtime.h>

#define CUDA_CHECK(call)                                                      \
    do {                                                                      \
        cudaError_t err__ = (call);                                           \
        if (err__ != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA error at %s:%d: %s\n",                     \
                    __FILE__, __LINE__, cudaGetErrorString(err__));           \
            std::exit(EXIT_FAILURE);                                          \
        }                                                                     \
    } while (0)

__global__ void vectorAdd(const float* __restrict__ a,
                          const float* __restrict__ b,
                          float* __restrict__ c,
                          int n) {
    int idx    = blockIdx.x * blockDim.x + threadIdx.x;
    int stride = gridDim.x * blockDim.x;
    for (int i = idx; i < n; i += stride) {
        c[i] = a[i] + b[i];
    }
}

int main() {
    const int    N     = 1 << 20;               // 1,048,576 elements
    const size_t bytes = (size_t)N * sizeof(float);

    // ---------------------------------------------------------------
    // Device info
    // ---------------------------------------------------------------
    int dev = 0;
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, dev));
    printf("Device: %s\n", prop.name);
    printf("Compute capability: %d.%d\n", prop.major, prop.minor);

    // ---------------------------------------------------------------
    // Host allocation & initialization
    // ---------------------------------------------------------------
    float* h_a   = (float*)std::malloc(bytes);
    float* h_b   = (float*)std::malloc(bytes);
    float* h_c   = (float*)std::malloc(bytes);
    float* h_ref = (float*)std::malloc(bytes);
    if (!h_a || !h_b || !h_c || !h_ref) {
        fprintf(stderr, "Host allocation failed\n");
        return EXIT_FAILURE;
    }

    for (int i = 0; i < N; ++i) {
        h_a[i]   = (float)(i % 1000) * 0.5f;
        h_b[i]   = (float)(i % 500)  * 0.25f;
        h_ref[i] = h_a[i] + h_b[i];
        h_c[i]   = 0.0f;
    }

    // ---------------------------------------------------------------
    // Device allocation & host->device transfer
    // ---------------------------------------------------------------
    float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc((void**)&d_a, bytes));
    CUDA_CHECK(cudaMalloc((void**)&d_b, bytes));
    CUDA_CHECK(cudaMalloc((void**)&d_c, bytes));

    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    // ---------------------------------------------------------------
    // Kernel launch
    // ---------------------------------------------------------------
    const int threads = 256;
    int       blocks  = (N + threads - 1) / threads;
    if (blocks > 65535) blocks = 65535;

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    CUDA_CHECK(cudaEventRecord(start));
    vectorAdd<<<blocks, threads>>>(d_a, d_b, d_c, N);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&ms, start, stop));
    printf("Kernel time: %.3f ms\n", ms);

    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));

    // ---------------------------------------------------------------
    // Device->host transfer & verification
    // ---------------------------------------------------------------
    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

    int mismatches = 0;
    const float tol = 1e-5f;
    for (int i = 0; i < N; ++i) {
        if (std::fabs(h_c[i] - h_ref[i]) > tol) {
            if (mismatches < 5) {
                fprintf(stderr, "Mismatch at index %d: got %f, expected %f\n",
                        i, h_c[i], h_ref[i]);
            }
            ++mismatches;
        }
    }

    // ---------------------------------------------------------------
    // Report
    // ---------------------------------------------------------------
    if (mismatches == 0) {
        printf("SUCCESS: Vector addition verified for %d elements.\n", N);
    } else {
        printf("FAILURE: %d mismatches found out of %d elements.\n",
               mismatches, N);
    }

    // ---------------------------------------------------------------
    // Cleanup
    // ---------------------------------------------------------------
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    std::free(h_a);
    std::free(h_b);
    std::free(h_c);
    std::free(h_ref);

    return (mismatches == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
```