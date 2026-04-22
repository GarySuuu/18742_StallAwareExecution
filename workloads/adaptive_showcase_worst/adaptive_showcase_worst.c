#include <stdint.h>

#include "../common/mini_runtime.h"

/*
 * Adaptive Showcase - Slight Negative Case
 *
 * Goal: a workload V4 slightly HURTS (EDP ~ -2% to -8%).
 *
 * Required classifier behavior to see a throttle:
 *   mem_block_ratio >= 0.12  AND  avg_outstanding_misses_proxy < 12
 *   -> Serialized-memory dominated -> Conservative (fw=5)
 *
 * Required workload behavior for the throttle to be HARMFUL:
 *   - low squash_ratio (no speculation to recover from)
 *   - reasonable baseline IPC (throttle directly cuts throughput)
 *
 * Strategy:
 *   - Serial pointer chase through an L2-resident (not L1-resident) array
 *     -> each load misses L1 but usually hits L2 (~10-15 cycle latency)
 *     -> head of ROB waits for the load -> commit_blocked_mem_cycles grows
 *     -> mem_block_ratio just above 0.12
 *   - A long, branchless, fully-dependent compute chain between loads
 *     -> each iteration is ~30 insts of which only 1 is a load
 *     -> the long dependency chain means IQ/ROB get full on compute, not LSQ
 *     -> avg LSQ occupancy stays below 12
 *   - No data-dependent branches -> squash_ratio ~0
 *     -> NOT classified as Control / NOT Deep Conservative
 *   - Throttle (fw=5) reduces front-end bandwidth without
 *     eliminating any wasted speculation -> IPC drops slightly,
 *     energy saves slightly, EDP slightly negative.
 */

#define CHASE_SIZE (1U << 16)   /* 64K nodes * 4B = 256KB, misses L1 but L2-resident */
static uint32_t chase[CHASE_SIZE];

static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 1500000UL)
                                 : 1500000U;
    uint32_t seed = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1UL) : 1U;

    /* Initialise chase[] to a random permutation so it forms one big cycle. */
    for (uint32_t i = 0; i < CHASE_SIZE; ++i) {
        chase[i] = (i + 1U) & (CHASE_SIZE - 1U);
    }
    for (uint32_t i = CHASE_SIZE - 1U; i > 0U; --i) {
        uint32_t j = xorshift32(&seed) % (i + 1U);
        uint32_t tmp = chase[i];
        chase[i] = chase[j];
        chase[j] = tmp;
    }

    uint32_t idx = 0;
    uint32_t acc = seed;
    uint64_t total = 0;

    for (uint32_t r = 0; r < rounds; ++r) {
        /* Serial chase load. Next iteration's address depends on what
         * comes back in v, so the CPU cannot prefetch ahead: at most a
         * few iterations worth of LSQ entries are ever outstanding. */
        idx = chase[idx];
        uint32_t v = idx;

        /* Long branchless dependent compute chain (~28 ops).
         * Each step depends on the previous -> no ILP to exploit ->
         * issue rate in compute is bounded by the chain length, not by
         * fetch width. But fetching narrower (fw=5) still delays the
         * point at which the *next* chase load enters rename and
         * therefore the point at which it can begin executing.
         * So throttling fw hurts throughput on this chain. */
        v ^= v >> 16; v *= 0x7feb352dU;
        v ^= v >> 15; v *= 0x846ca68bU;
        v ^= v >> 16; v *= 0xcaffe171U;
        v ^= v >> 13; v *= 0x85ebca6bU;
        v ^= v >> 16; v *= 0xc2b2ae35U;
        v ^= v >> 13; v *= 0x1b873593U;
        v ^= v >> 16; v *= 0x21f0aaadU;
        v ^= v >> 15; v *= 0x735a2d97U;
        v ^= v >> 13; v *= 0xc5a308d3U;
        v ^= v >> 15; v *= 0x9e3779b1U;
        v ^= v >> 16; v *= 0x6eed0e9dU;
        v ^= v >> 13; v *= 0xa9c59d11U;
        v ^= v >> 17; v *= 0x94d049bbU;
        v ^= v >> 13;

        acc ^= v;
        total += acc;
    }

    uint64_t checksum = total ^ ((uint64_t)acc << 32) ^ idx;
    emit_result("adaptive_showcase_worst", rounds, seed, 0, checksum);
    return (int)(checksum & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
