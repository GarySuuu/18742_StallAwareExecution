#include <stdint.h>

#include "../common/mini_runtime.h"

/*
 * Adaptive Showcase - Best Case
 *
 * Designed to maximally benefit from Deep Conservative (fw=3).
 * Steady-state behavior (no phases):
 *   - Random memory accesses that create cache misses -> mem_block_ratio > 0.12
 *   - Data-dependent branches after each load -> high branch misprediction
 *   - High squash_ratio (>0.25) -> Deep Conservative activates
 *   - Under fw=3, speculation waste is eliminated -> IPC maintained, energy saved
 *
 * This mimics real workloads like hash table lookups, tree traversals,
 * and rule-matching engines where each memory access determines the
 * next branch direction.
 */

#define TABLE_SIZE (1U << 16)  /* 64K entries = 256KB, exceeds L1D */
static uint32_t table[TABLE_SIZE];

static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 2000000UL)
                                 : 2000000U;
    uint32_t seed = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1UL) : 1U;

    /* Initialize table with pseudo-random values */
    for (uint32_t i = 0; i < TABLE_SIZE; ++i) {
        table[i] = xorshift32(&seed);
    }

    uint32_t acc = seed;
    uint32_t idx = 0;
    uint64_t total = 0;

    for (uint32_t r = 0; r < rounds; ++r) {
        /* Load from table - likely L1D miss (256KB > 64KB L1D) */
        uint32_t val = table[idx];

        /* Data-dependent branch - unpredictable direction based on loaded value */
        if (val & 0x01) {
            acc += val;
        } else {
            acc ^= val;
        }

        if (val & 0x04) {
            acc += (val >> 8);
        } else {
            acc ^= (val << 3);
        }

        if (val & 0x10) {
            total += acc;
        } else {
            total ^= acc;
        }

        /* Next index depends on loaded value - pointer-chase-like pattern */
        idx = (val ^ acc) & (TABLE_SIZE - 1);

        /* Store back (creates memory traffic) */
        table[(idx + 1) & (TABLE_SIZE - 1)] = acc;
    }

    uint64_t checksum = total ^ ((uint64_t)acc << 32) ^ idx;
    emit_result("adaptive_showcase_best", rounds, seed, 0, checksum);
    return (int)(checksum & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
