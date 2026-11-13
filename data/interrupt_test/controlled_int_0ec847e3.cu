```cuda
#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define CUDA_CHECK(expr)                                                     \
    do {                                                                     \
        cudaError_t err__ = (expr);                                          \
        if (err__ != cudaSuccess) {                                          \
            fprintf(stderr, "CUDA error %s at %s:%d: %s\n",                  \
                    cudaGetErrorName(err__), __FILE__, __LINE__,             \
                    cudaGetErrorString(err__));                              \
            exit(EXIT_FAILURE);                                              \
        }                                                                    \
    } while (0)

/* Vector addition kernel: c = a + b */
__global__ void vectorAdd(const float* __restrict__ a,
                          const float* __restrict__ b,
                          float* __restrict__ c,
                          int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

int main(void)
{
    /* Problem size: 1M elements (~4 MB per array). */
    const int    n     = 1 << 20;
    const size_t bytes = (size_t)n * sizeof(float);

    /* Report the target device information. */
    int device = 0;
    CUDA_CHECK(cudaGetDevice(&device));
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, device));
    printf("Device: %s (compute capability %d.%d)\n",
           prop.name, prop.major, prop.minor);

    /* Allocate host memory. */
    float* h_a = (float*)malloc(bytes);
    float* h_b = (float*)malloc(bytes);
    float* h_c = (float*)malloc(bytes);
    if (!h_a || !h_b || !h_c) {
        fprintf(stderr, "Host allocation failed\n");
        return EXIT_FAILURE;
    }

    /* Initialize input data. */
    for (int i = 0; i < n; ++i) {
        h_a[i] = 1.0f * (float)i;
        h_b[i] = 2.0f * (float)i;
    }

    /* Allocate device memory. */
    float *d_a = NULL, *d_b = NULL, *d_c = NULL;
    CUDA_CHECK(cudaMalloc((void**)&d_a, bytes));
    CUDA_CHECK(cudaMalloc((void**)&d_b, bytes));
    CUDA_CHECK(cudaMalloc((void**)&d_c, bytes));

    /* Copy inputs to device. */
    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    /* Launch kernel. */
    const int threadsPerBlock = 256;
    const int blocksPerGrid   = (n + threadsPerBlock - 1) / threadsPerBlock;
    printf("Launching vectorAdd<<<%d blocks, %d threads>>>\n",
           blocksPerGrid, threadsPerBlock);

    vectorAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    /* Copy result back to host. */
    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

    /* Verify. */
    int errors = 0;
    for (int i = 0; i < n; ++i) {
        float expected = h_a[i] + h_b[i];
        if (fabsf(h_c[i] - expected) > 1e-5f) {
            if (errors < 5) {
                fprintf(stderr, "Mismatch at index %d: got %f, expected %f\n",
                        i, h_c[i], expected);
            }
            ++errors;
        }
    }

    if (errors == 0) {
        printf("Vector addition of %d elements: SUCCESS\n", n);
    } else {
        printf("Vector addition FAILED with %d errors\n", errors);
    }

    /* Clean up. */
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    free(h_a);
    free(h_b);
    free(h_c);

    return (errors == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
```