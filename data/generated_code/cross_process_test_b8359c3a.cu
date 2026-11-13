#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <cuda_runtime.h>

#define N (1 << 20)
#define THREADS_PER_BLOCK 256
#define TOLERANCE 1e-5f

#define CUDA_CHECK(call)                                                     \
    do {                                                                     \
        cudaError_t err_ = (call);                                           \
        if (err_ != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA error at %s:%d: %s\n",                     \
                    __FILE__, __LINE__, cudaGetErrorString(err_));           \
            exit(EXIT_FAILURE);                                              \
        }                                                                    \
    } while (0)

__global__ void vectorAdd(const float *a, const float *b, float *c, int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

int main(void)
{
    int device = 0;
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDevice(&device));
    CUDA_CHECK(cudaGetDeviceProperties(&prop, device));

    printf("Using GPU: %s (compute capability %d.%d)\n",
           prop.name, prop.major, prop.minor);

    if (prop.major != 7 || prop.minor != 5) {
        printf("WARNING: Expected compute capability 7.5 (GTX 1660), found %d.%d\n",
               prop.major, prop.minor);
    }

    size_t bytes = (size_t)N * sizeof(float);

    float *h_a = (float *)malloc(bytes);
    float *h_b = (float *)malloc(bytes);
    float *h_c = (float *)malloc(bytes);
    float *h_ref = (float *)malloc(bytes);

    if (h_a == NULL || h_b == NULL || h_c == NULL || h_ref == NULL) {
        fprintf(stderr, "FAILURE: Host memory allocation failed\n");
        return EXIT_FAILURE;
    }

    for (int i = 0; i < N; ++i) {
        h_a[i] = (float)(i % 1000) * 0.5f;
        h_b[i] = (float)((i * 3) % 1000) * 0.25f;
        h_ref[i] = h_a[i] + h_b[i];
    }

    float *d_a = NULL;
    float *d_b = NULL;
    float *d_c = NULL;

    CUDA_CHECK(cudaMalloc((void **)&d_a, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_b, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_c, bytes));

    CUDA_CHECK(cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice));

    int blocks = (N + THREADS_PER_BLOCK - 1) / THREADS_PER_BLOCK;
    vectorAdd<<<blocks, THREADS_PER_BLOCK>>>(d_a, d_b, d_c, N);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost));

    int mismatches = 0;
    for (int i = 0; i < N; ++i) {
        float diff = fabsf(h_c[i] - h_ref[i]);
        if (diff > TOLERANCE) {
            if (mismatches < 5) {
                fprintf(stderr,
                        "Mismatch at index %d: got %f, expected %f, diff %f\n",
                        i, h_c[i], h_ref[i], diff);
            }
            ++mismatches;
        }
    }

    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));

    free(h_a);
    free(h_b);
    free(h_c);
    free(h_ref);

    if (mismatches == 0) {
        printf("SUCCESS: Vector addition verified for %d elements.\n", N);
        return EXIT_SUCCESS;
    } else {
        printf("FAILURE: Vector addition verification failed with %d mismatches.\n",
               mismatches);
        return EXIT_FAILURE;
    }
}