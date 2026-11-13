#include <cstdio>
#include <cstdlib>
#include <cmath>

// Verification harness: same kernel logic, swept across edge-case sizes.
// Exercises: N not divisible by blockDim, N smaller than one block,
// grid-stride loop wrap-around, and the 65535-block cap.

#define CUDA_CHECK(call)                                                      \
    do {                                                                      \
        cudaError_t err__ = (call);                                           \
        if (err__ != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA error at %s:%d -> %s\n", __FILE__,         \
                    __LINE__, cudaGetErrorString(err__));                     \
            exit(EXIT_FAILURE);                                               \
        }                                                                     \
    } while (0)

__global__ void vectorAdd(const float * __restrict__ A,
                          const float * __restrict__ B,
                          float * __restrict__ C,
                          int n)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int stride = blockDim.x * gridDim.x;
    for (int i = idx; i < n; i += stride) {
        C[i] = A[i] + B[i];
    }
}

static int runCase(int n, int threadsPerBlock)
{
    const size_t bytes = (size_t)n * sizeof(float);

    float *d_A, *d_B, *d_C;
    CUDA_CHECK(cudaMalloc((void **)&d_A, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_B, bytes));
    CUDA_CHECK(cudaMalloc((void **)&d_C, bytes));

    // Build host data on the fly to keep memory flat for large N
    float *h_A = (float *)malloc(bytes);
    float *h_B = (float *)malloc(bytes);
    float *h_C = (float *)malloc(bytes);
    for (int i = 0; i < n; ++i) { h_A[i] = 1.0f * i; h_B[i] = 2.0f * i; }

    CUDA_CHECK(cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_B, h_B, bytes, cudaMemcpyHostToDevice));

    int blocks = (n + threadsPerBlock - 1) / threadsPerBlock;
    int uncapped = blocks;
    if (blocks > 65535) blocks = 65535;

    vectorAdd<<<blocks, threadsPerBlock>>>(d_A, d_B, d_C, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    CUDA_CHECK(cudaMemcpy(h_C, d_C, bytes, cudaMemcpyDeviceToHost));

    int errors = 0;
    for (int i = 0; i < n; ++i) {
        float expected = h_A[i] + h_B[i];
        if (h_C[i] != expected) ++errors;   // exact: values are small integers
    }

    printf("  N=%-9d blocks=%-6d (raw %-6d) tpb=%-4d %s  mismatches=%d\n",
           n, blocks, uncapped, threadsPerBlock,
           errors == 0 ? "PASS" : "FAIL", errors);

    free(h_A); free(h_B); free(h_C);
    CUDA_CHECK(cudaFree(d_A));
    CUDA_CHECK(cudaFree(d_B));
    CUDA_CHECK(cudaFree(d_C));
    return errors;
}

int main()
{
    printf("Edge-case sweep for vectorAdd\n");
    int total = 0;
    total += runCase(1,          256);  // single element, one block
    total += runCase(255,        256);  // partial block
    total += runCase(256,        256);  // exactly one full block
    total += runCase(257,        256);  // one block + 1
    total += runCase(1023,       256);  // tail handling
    total += runCase(1024,       256);  // power of two
    total += runCase(1000003,    256);  // prime, not block-divisible
    total += runCase(1048576,    256);  // original default
    total += runCase(1048576,     32);  // small block size
    total += runCase(1048576,    512);  // larger block size
    total += runCase(20000000,   256);  // exceeds 65535 blocks -> grid-stride wrap

    printf("\nOVERALL: %s (total mismatches = %d)\n",
           total == 0 ? "ALL PASS" : "FAILURES", total);
    return total == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
