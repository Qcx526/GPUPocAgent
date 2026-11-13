```cuda
/*
 * vector_add.cu
 * Simple CUDA vector addition test with host verification.
 *
 * Target GPU: NVIDIA GeForce GTX 1660
 * Compute capability: 7.5 (sm_75)
 *
 * Build:
 *   nvcc -arch=sm_75 -O2 -o vector_add vector_add.cu
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <cuda_runtime.h>

#define N (1 << 20)
#define THREADS_PER_BLOCK 256

__global__ void vector_add(const float * __restrict__ a,
                           const float * __restrict__ b,
                           float * __restrict__ c,
                           int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

static void cuda_check(cudaError_t err, const char *what)
{
    if (err != cudaSuccess) {
        fprintf(stderr, "CUDA error during %s: %s\n", what, cudaGetErrorString(err));
        exit(EXIT_FAILURE);
    }
}

int main(void)
{
    int device = 0;
    cudaDeviceProp prop;

    cuda_check(cudaGetDeviceProperties(&prop, device), "cudaGetDeviceProperties");
    cuda_check(cudaSetDevice(device), "cudaSetDevice");

    printf("Device: %s\n", prop.name);
    printf("Compute capability: %d.%d\n", prop.major, prop.minor);

    if (prop.major != 7 || prop.minor != 5) {
        printf("Warning: expected compute capability 7.5 (GTX 1660), got %d.%d\n",
               prop.major, prop.minor);
    }

    const size_t bytes = (size_t)N * sizeof(float);

    float *h_a = (float *)malloc(bytes);
    float *h_b = (float *)malloc(bytes);
    float *h_c = (float *)malloc(bytes);
    float *h_ref = (float *)malloc(bytes);
    if (!h_a || !h_b || !h_c || !h_ref) {
        fprintf(stderr, "Host allocation failed\n");
        return EXIT_FAILURE;
    }

    srand(12345);
    for (int i = 0; i < N; ++i) {
        h_a[i] = (float)(rand() % 1000) / 10.0f;
        h_b[i] = (float)(rand() % 1000) / 10.0f;
    }

    float *d_a = NULL;
    float *d_b = NULL;
    float *d_c = NULL;

    cuda_check(cudaMalloc((void **)&d_a, bytes), "cudaMalloc(d_a)");
    cuda_check(cudaMalloc((void **)&d_b, bytes), "cudaMalloc(d_b)");
    cuda_check(cudaMalloc((void **)&d_c, bytes), "cudaMalloc(d_c)");

    cuda_check(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice), "cudaMemcpy(d_a)");
    cuda_check(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice), "cudaMemcpy(d_b)");

    int blocks = (N + THREADS_PER_BLOCK - 1) / THREADS_PER_BLOCK;
    vector_add<<<blocks, THREADS_PER_BLOCK>>>(d_a, d_b, d_c, N);

    cuda_check(cudaGetLastError(), "kernel launch");
    cuda_check(cudaDeviceSynchronize(), "kernel execution");

    cuda_check(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost), "cudaMemcpy(h_c)");

    for (int i = 0; i < N; ++i) {
        h_ref[i] = h_a[i] + h_b[i];
    }

    int mismatches = 0;
    const float tolerance = 1e-5f;
    for (int i = 0; i < N; ++i) {
        if (fabsf(h_c[i] - h_ref[i]) > tolerance) {
            if (mismatches < 5) {
                fprintf(stderr, "Mismatch at index %d: got %f, expected %f\n",
                        i, h_c[i], h_ref[i]);
            }
            ++mismatches;
        }
    }

    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_c);

    free(h_a);
    free(h_b);
    free(h_c);
    free(h_ref);

    if (mismatches == 0) {
        printf("SUCCESS: CUDA vector addition verified for %d elements\n", N);
        return EXIT_SUCCESS;
    } else {
        printf("FAILURE: %d mismatches detected out of %d elements\n", mismatches, N);
        return EXIT_FAILURE;
    }
}
```