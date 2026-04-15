#include <stdint.h>

#include "../common/mini_runtime.h"

/*
 * Fetch-bandwidth stress:
 * Large basic blocks of independent ALU ops with no memory accesses and
 * minimal branching. The only branch is the outer loop.
 *
 * Intent: throughput is limited by fetch width. If fetch width is reduced
 * from 8 to 2, throughput should drop roughly 4x, making this the workload
 * most sensitive to adaptiveConservativeFetchWidth.
 *
 * Expected adaptive class: Resource (high commit activity, low memory pressure)
 * Expected mode: Aggressive (no throttling needed)
 */
static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 100000UL) : 100000U;
    uint32_t seed = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1UL) : 1U;

    /* Registers that hold independent accumulators -- no data dependencies
       between consecutive instructions within the unrolled block. */
    volatile uint32_t a0 = seed;
    volatile uint32_t a1 = seed ^ 0xDEADBEEF;
    volatile uint32_t a2 = seed ^ 0xCAFEBABE;
    volatile uint32_t a3 = seed ^ 0x12345678;
    volatile uint32_t a4 = seed ^ 0xABCDEF01;
    volatile uint32_t a5 = seed ^ 0x87654321;
    volatile uint32_t a6 = seed ^ 0xFEDCBA98;
    volatile uint32_t a7 = seed ^ 0x13579BDF;

    for (uint32_t r = 0; r < rounds; ++r) {
        /* 32 independent ALU ops per iteration -- all can execute as soon
           as they are fetched; no data hazards between them. */
        a0 += 0x9E3779B9;
        a1 += 0x6A09E667;
        a2 ^= a0;
        a3 ^= a1;
        a4 += 0xBB67AE85;
        a5 += 0x3C6EF372;
        a6 ^= a4;
        a7 ^= a5;

        a0 += 0xA54FF53A;
        a1 += 0x510E527F;
        a2 ^= a0;
        a3 ^= a1;
        a4 += 0x9B05688C;
        a5 += 0x1F83D9AB;
        a6 ^= a4;
        a7 ^= a5;

        a0 += 0x5BE0CD19;
        a1 += 0xCBBB9D5D;
        a2 ^= a0;
        a3 ^= a1;
        a4 += 0x629A292A;
        a5 += 0x9159015A;
        a6 ^= a4;
        a7 ^= a5;

        a0 += 0x152FECD8;
        a1 += 0x67332667;
        a2 ^= a0;
        a3 ^= a1;
        a4 += 0x8EB44A87;
        a5 += 0xDB0C2E0D;
        a6 ^= a4;
        a7 ^= a5;
    }

    uint64_t checksum = (uint64_t)a0 ^ ((uint64_t)a1 << 7) ^
                        (uint64_t)a2 ^ ((uint64_t)a3 << 13) ^
                        (uint64_t)a4 ^ ((uint64_t)a5 << 19) ^
                        (uint64_t)a6 ^ ((uint64_t)a7 << 23);

    emit_result("fetch_bandwidth_stress", rounds, seed, 0, checksum);
    return (int)(checksum & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
