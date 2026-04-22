#include <stdint.h>

#include "../common/mini_runtime.h"

/*
 * Adaptive Showcase - Neutral Case
 *
 * Designed to show the mechanism is safe: almost no benefit but also
 * almost no harm. This demonstrates the mechanism's ability to
 * correctly identify workloads that don't need throttling.
 *
 * Characteristics:
 *   - Pure integer compute, no memory access beyond registers
 *   - Very high IPC (~2.4) but commit_activity ~1.0 (almost no squash)
 *   - No phase changes, completely steady state
 *   - Classified as Resource -> Aggressive (no throttle)
 *   - Resource congestion does NOT trigger (commit_activity ~1.0 > 0.95)
 *
 * Expected result: EDP ~0% (no change from baseline)
 */

static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 2000000UL)
                                 : 2000000U;
    uint32_t seed = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1UL) : 1U;

    /* Multiple independent dependency chains to keep execution units busy
     * but with NO speculation waste (no branches, no memory) */
    uint32_t a = seed;
    uint32_t b = seed ^ 0xDEADBEEF;
    uint32_t c = seed ^ 0xCAFEBABE;
    uint32_t d = seed ^ 0x12345678;
    uint32_t e = seed ^ 0xABCDEF01;
    uint32_t f = seed ^ 0x87654321;

    for (uint32_t r = 0; r < rounds; ++r) {
        /* Chain 1: multiply-add */
        a = a * 0x01000193 + b;
        b = b * 0x811C9DC5 + c;

        /* Chain 2: shift-xor */
        c ^= (c << 13);
        c ^= (c >> 17);
        c ^= (c << 5);

        /* Chain 3: rotate-add */
        d = ((d << 7) | (d >> 25)) + e;
        e = ((e << 13) | (e >> 19)) + f;

        /* Chain 4: mix */
        f = f ^ a ^ d;
        a += f >> 3;
    }

    uint64_t checksum = (uint64_t)a ^ ((uint64_t)b << 7) ^
                        (uint64_t)c ^ ((uint64_t)d << 13) ^
                        (uint64_t)e ^ ((uint64_t)f << 19);

    emit_result("adaptive_showcase_neutral", rounds, seed, 0, checksum);
    return (int)(checksum & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
