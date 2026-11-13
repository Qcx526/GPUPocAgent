```cuda
#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define CUDA_CHECK(call)                                                     \
    do {                                                                     \
        cudaError_t err__ = (call);                                          \
        if (err__ != cudaSuccess) {                                          \
            fprintf(stderr, "CUDA error at %s:%d: %s\n",                    \
                    __FILE__, __LINE__, cudaGetErrorString(err__));          \
            exit(EXIT_FAILURE);                                              \
        }                                                                    \
    } while (0)

__global__ void vectorAdd(const float* __restrict__ A,
                          const float* __restrict__ B,
                          float* __restrict__ C,
                          int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        C[idx] = A[idx] + B[idx];
    }
}

int main(void) {
    const int n = 1 << 20;
    const size_t bytes = (size_t)n * sizeof(float);

    float* h_A = (float*)malloc(bytes);
    float* h_B = (float*)malloc(bytes);
    float* h_C = (float*)malloc(bytes);
    float* h_ref = (float*)malloc(bytes);

    if (h_A == NULL || h_B == NULL || h_C == NULL || h_ref == NULL) {
        fprintf(stderr, "FAILURE: Host memory allocation failed.\n");
        free(h_A);
        free(h_B);
        free(h_C);
        free(h_ref);
        return EXIT_FAILURE;
    }

    for (int i = 0; i < n; ++i) {
        h_A[i] = (float)((i % 1000) - 500) / 10.0f;
        h_B[i] = (float)((i % 777) - 300) / 7.0f;
        h_ref[i] = h_A[i] + h_B[i];
    }

    float* d_A = NULL;
    float* d_B = NULL;
    float* d_C = NULL;

    CUDA_CHECK(cudaMalloc((void**)&d_A, bytes));
    CUDA_CHECK(cudaMalloc((void**)&d_B, bytes));
    CUDA_CHECK(cudaMalloc((void**)&d_C, bytes));

    CUDA_CHECK(cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, h_B, bytes, cudaMemcpyHostToDevice));

    const int threadsPerBlock = 256;
    const int blocksPerGrid = (n + threadsPerBlock - 1) / threadsPerBlock;

    vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_A, d_B, d_C, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(h_C, d_C, bytes, cudaMemcpyDeviceToHost));

    bool success = true;
    int firstMismatch = -1;
    float maxError = 0.0f;
    const float tolerance = 1e-5f;

    for (int i = 0; i < n; ++i) {
        float diff = fabsf(h_C[i] - h_ref[i]);
        if (diff > maxError) {
            maxError = diff;
        }
        if (diff > tolerance) {
            success = false;
            if (firstMismatch < 0) {
                firstMismatch = i;
            }
        }
    }

    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));

    free(h_A);
    free(h_B);
    free(h_C);
    free(h_ref);

    if (success) {
        printf("SUCCESS: CUDA vector addition verified for %d elements. Max error = %e\n",
               n, maxError);
        return EXIT_SUCCESS;
    } else {
        printf("FAILURE: CUDA vector addition verification failed. First mismatch at index %d, max error = %e\n",
               firstMismatch, maxError);
        return EXIT_FAILURE;
    }
}
```