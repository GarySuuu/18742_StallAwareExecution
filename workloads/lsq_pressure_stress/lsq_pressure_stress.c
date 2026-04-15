#include <stdint.h>

#include "../common/mini_runtime.h"

#define ARRAY_SIZE (16384U)

static uint32_t arr_a[ARRAY_SIZE];
static uint32_t arr_b[ARRAY_SIZE];

/*
 * LSQ-pressure stress:
 * Many independent loads and stores to L1-resident data using a stride
 * pattern. Maximizes load/store queue entries in flight.
 *
 * Intent: isolate the effect of adaptiveConservativeLSQCap. When LSQ cap
 * is active, fetch is throttled because too many loads/stores are queued.
 *
 * Design: interleave loads from arr_a and stores to arr_b, with no
 * serializing dependencies between them. All data fits in L1/L2 cache.
 * The stride pattern avoids triggering prefetcher-dependent behavior.
 *
 * Expected adaptive class: Resource or HighMLP (many independent memory ops)
 */
static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 20000UL) : 20000U;
    uint32_t stride = (argc > 2) ? (uint32_t)parse_u32(argv[2], 3UL) : 3U;
    uint32_t seed = (argc > 3) ? (uint32_t)parse_u32(argv[3], 1UL) : 1U;

    if (stride < 1U) stride = 1U;
    if (stride > 16U) stride = 16U;

    /* Initialize arrays */
    for (uint32_t i = 0; i < ARRAY_SIZE; ++i) {
        uint32_t r = xorshift32(&seed);
        arr_a[i] = r;
        arr_b[i] = r ^ 0xFFFFFFFF;
    }

    uint32_t acc = 0;

    for (uint32_t r = 0; r < rounds; ++r) {
        /* Strided load-store pairs: many independent memory operations */
        for (uint32_t i = 0; i + stride * 7 < ARRAY_SIZE; i += stride * 8) {
            /* 8 independent load-compute-store sequences */
            uint32_t v0 = arr_a[i];
            uint32_t v1 = arr_a[i + stride];
            uint32_t v2 = arr_a[i + stride * 2];
            uint32_t v3 = arr_a[i + stride * 3];
            uint32_t v4 = arr_a[i + stride * 4];
            uint32_t v5 = arr_a[i + stride * 5];
            uint32_t v6 = arr_a[i + stride * 6];
            uint32_t v7 = arr_a[i + stride * 7];

            arr_b[i]              = v0 + r;
            arr_b[i + stride]     = v1 + r;
            arr_b[i + stride * 2] = v2 + r;
            arr_b[i + stride * 3] = v3 + r;
            arr_b[i + stride * 4] = v4 + r;
            arr_b[i + stride * 5] = v5 + r;
            arr_b[i + stride * 6] = v6 + r;
            arr_b[i + stride * 7] = v7 + r;

            acc += v0 ^ v1 ^ v2 ^ v3 ^ v4 ^ v5 ^ v6 ^ v7;
        }
    }

    emit_result("lsq_pressure_stress", rounds, stride,
                seed, (uint64_t)acc ^ (uint64_t)arr_b[0]);
    return (int)(acc & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
