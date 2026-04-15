#include <stdint.h>

#include "../common/mini_runtime.h"

#define BLOCK_SIZE 1024U

static uint32_t data[BLOCK_SIZE];

/*
 * IQ-pressure stress:
 * Many independent multiply operations that have multi-cycle latency,
 * filling the issue queue. Working set fits in L1 cache.
 *
 * Intent: when IQ cap is enabled in conservative mode, the pipeline stalls
 * because instructions cannot be issued fast enough. This isolates the
 * effect of adaptiveConservativeIQCap.
 *
 * Design: 8 independent accumulator chains, each using multiplication
 * (multi-cycle on ARM). All data fits in L1 (4KB), so memory is not
 * the bottleneck -- IQ capacity is.
 *
 * Expected adaptive class: Resource (high IQ saturation, high commit activity)
 */
static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 50000UL) : 50000U;
    uint32_t seed = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1UL) : 1U;

    /* Initialize data array (fits in L1) */
    for (uint32_t i = 0; i < BLOCK_SIZE; ++i) {
        uint32_t r = xorshift32(&seed);
        data[i] = r | 1U;
    }

    /* 8 independent accumulators using multiply */
    uint32_t m0 = seed | 1U;
    uint32_t m1 = (seed ^ 0xFF) | 1U;
    uint32_t m2 = (seed ^ 0xAA) | 1U;
    uint32_t m3 = (seed ^ 0x55) | 1U;
    uint32_t m4 = (seed ^ 0xCC) | 1U;
    uint32_t m5 = (seed ^ 0x33) | 1U;
    uint32_t m6 = (seed ^ 0x77) | 1U;
    uint32_t m7 = (seed ^ 0xBB) | 1U;

    for (uint32_t r = 0; r < rounds; ++r) {
        for (uint32_t i = 0; i < BLOCK_SIZE; i += 8) {
            /* 8 independent multiplies -- each takes multiple cycles,
               filling the IQ with waiting instructions */
            m0 = m0 * data[i]     + data[i + 1];
            m1 = m1 * data[i + 1] + data[i + 2];
            m2 = m2 * data[i + 2] + data[i + 3];
            m3 = m3 * data[i + 3] + data[i + 4];
            m4 = m4 * data[i + 4] + data[i + 5];
            m5 = m5 * data[i + 5] + data[i + 6];
            m6 = m6 * data[i + 6] + data[i + 7];
            m7 = m7 * data[i + 7] + data[i];
        }
    }

    uint64_t checksum = (uint64_t)m0 ^ ((uint64_t)m1 << 5) ^
                        (uint64_t)m2 ^ ((uint64_t)m3 << 11) ^
                        (uint64_t)m4 ^ ((uint64_t)m5 << 17) ^
                        (uint64_t)m6 ^ ((uint64_t)m7 << 23);

    emit_result("iq_pressure_stress", rounds, seed, 0, checksum);
    return (int)(checksum & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
