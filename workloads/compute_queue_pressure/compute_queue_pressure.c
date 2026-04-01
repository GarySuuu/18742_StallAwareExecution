#include <stdint.h>

#include "../common/mini_runtime.h"

#define MAX_BLOCK 8192U

static uint32_t coeffs[MAX_BLOCK];
static uint32_t data[MAX_BLOCK];

/*
 * Backend-pressure integer kernel:
 * several accumulators stay active at once, stressing issue/execute resources
 * more than memory latency. This is intended to look compute/resource-heavy.
 */
static int run_main(int argc, char **argv)
{
    uint32_t block = (argc > 1) ? (uint32_t)parse_u32(argv[1], 4096UL) : 4096U;
    uint32_t rounds = (argc > 2) ? (uint32_t)parse_u32(argv[2], 8192UL) : 8192U;
    uint32_t seed = (argc > 3) ? (uint32_t)parse_u32(argv[3], 1UL) : 1U;
    uint64_t a0 = 0x123456789abcdef0ULL;
    uint64_t a1 = 0x0fedcba987654321ULL;
    uint64_t a2 = 0x9e3779b97f4a7c15ULL;
    uint64_t a3 = 0xbf58476d1ce4e5b9ULL;

    if (block < 256U) {
        block = 256U;
    }
    if (block > MAX_BLOCK) {
        block = MAX_BLOCK;
    }
    if (rounds < 1U) {
        rounds = 1U;
    }

    for (uint32_t i = 0; i < block; ++i) {
        uint32_t r = xorshift32(&seed);
        coeffs[i] = r | 1U;
        data[i] = (r << 5) ^ (i * 33U);
    }

    for (uint32_t r = 0; r < rounds; ++r) {
        for (uint32_t i = 0; i < block; ++i) {
            uint64_t x = data[i];
            uint64_t c = coeffs[(i + r) % block];
            a0 = a0 * 1664525ULL + x + (a3 >> 3);
            a1 = a1 * 22695477ULL + c + (a0 >> 7);
            a2 ^= (a0 << 11) + (a1 >> 5) + x * c;
            a3 += rotl64(a2 ^ a1, (unsigned)(i & 31U)) + (a0 ^ c);
            data[i] = (uint32_t)(a0 ^ a1 ^ a2 ^ a3);
        }
    }

    emit_result("compute_queue_pressure", block, rounds, seed, a0 ^ a1 ^ a2 ^ a3);
    return (int)((a0 ^ a1 ^ a2 ^ a3) & 0xffU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
