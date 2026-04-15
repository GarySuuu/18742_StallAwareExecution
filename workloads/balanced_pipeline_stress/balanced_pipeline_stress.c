#include <stdint.h>

#include "../common/mini_runtime.h"

/*
 * Balanced pipeline stress workload
 *
 * Designed to exercise ALL major pipeline resources simultaneously so that
 * sweeping any single architectural parameter (fetch width, ROB cap, IQ cap,
 * LSQ cap, rename/dispatch width) produces observable signal changes.
 *
 * Structure per iteration:
 *   - 8 independent ALU ops          (stress fetch/rename/dispatch width)
 *   - 4 load + 4 store operations    (stress LSQ, create memory traffic)
 *   - 2 multiply-accumulate chains   (stress IQ occupancy with long latency)
 *   - 1 data-dependent branch        (create squash, moderate branch pressure)
 *   - short dependency chain via acc  (keep ROB occupied waiting for results)
 *
 * Target characteristics:
 *   - IPC ~2-3 (high enough that width limits matter)
 *   - ~25% memory instructions (load+store out of total)
 *   - ~5-10% branch misprediction (pseudo-random branch direction)
 *   - moderate ILP (mix of independent and dependent instructions)
 *   - working set fits in L1D (~16KB used) to isolate pipeline effects
 */

#define ARRAY_SIZE 4096U    /* 4096 * 4 = 16KB, fits in L1D */

static uint32_t arr_a[ARRAY_SIZE];
static uint32_t arr_b[ARRAY_SIZE];

static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 1000000UL)
                                 : 1000000U;
    uint32_t seed = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1UL) : 1U;

    /* Initialize arrays */
    for (uint32_t i = 0; i < ARRAY_SIZE; ++i) {
        arr_a[i] = xorshift32(&seed);
        arr_b[i] = xorshift32(&seed);
    }

    /* Independent accumulators -- no dependency between them */
    uint32_t acc0 = seed ^ 0x9E3779B9;
    uint32_t acc1 = seed ^ 0x6A09E667;
    uint32_t acc2 = seed ^ 0xBB67AE85;
    uint32_t acc3 = seed ^ 0x3C6EF372;

    /* Multiply-accumulate chains (long latency, occupy IQ) */
    uint32_t mac0 = seed ^ 0xA54FF53A;
    uint32_t mac1 = seed ^ 0x510E527F;

    /* Memory index, wraps within L1D-sized array */
    uint32_t idx = 0;

    uint64_t total = 0;

    for (uint32_t r = 0; r < rounds; ++r) {

        /* ---- Block 1: 8 independent ALU ops ---- */
        /* These can all issue in parallel if fetch/rename/dispatch are wide */
        acc0 += 0x9E3779B9;
        acc1 ^= 0x6A09E667;
        acc2 += 0xBB67AE85;
        acc3 ^= 0x3C6EF372;
        acc0 ^= acc2 >> 5;
        acc1 += acc3 << 3;
        acc2 ^= acc0 >> 7;
        acc3 += acc1 << 2;

        /* ---- Block 2: 4 loads + 4 stores (LSQ pressure) ---- */
        uint32_t i0 = idx & (ARRAY_SIZE - 1);
        uint32_t i1 = (idx + 1) & (ARRAY_SIZE - 1);
        uint32_t i2 = (idx + 2) & (ARRAY_SIZE - 1);
        uint32_t i3 = (idx + 3) & (ARRAY_SIZE - 1);

        uint32_t v0 = arr_a[i0];   /* load */
        uint32_t v1 = arr_a[i1];   /* load */
        uint32_t v2 = arr_b[i2];   /* load */
        uint32_t v3 = arr_b[i3];   /* load */

        arr_b[i0] = v0 ^ acc0;     /* store */
        arr_a[i1] = v1 + acc1;     /* store */
        arr_b[i2] = v2 ^ acc2;     /* store */
        arr_a[i3] = v3 + acc3;     /* store */

        /* ---- Block 3: 2 multiply-accumulate chains ---- */
        /* Multiplies have multi-cycle latency, keeping IQ entries occupied */
        mac0 = mac0 * 0x01000193 + v0;
        mac0 = mac0 * 0x811C9DC5 + v1;
        mac1 = mac1 * 0x01000193 + v2;
        mac1 = mac1 * 0x811C9DC5 + v3;

        /* ---- Block 4: data-dependent branch ---- */
        /* Branch direction depends on runtime values, creating ~50% mispredict
           rate for a simple predictor (actual rate depends on pattern) */
        uint32_t branch_val = acc0 ^ mac0;
        if (branch_val & 0x80) {
            acc0 += mac1;
            acc1 ^= v0;
        } else {
            acc2 += mac0;
            acc3 ^= v3;
        }

        /* A second, less predictable branch to add more squash pressure */
        if ((branch_val >> 4) & 0x3) {
            total += (uint64_t)acc0 + acc1;
        } else {
            total += (uint64_t)acc2 ^ acc3;
        }

        /* ---- Advance index (creates cross-iteration dependency) ---- */
        idx = (idx + 4 + (acc0 & 0x3)) & (ARRAY_SIZE - 1);

        /* ---- Block 5: short dependency tail ---- */
        /* Forces some instructions to stay in ROB waiting for the branch
           and multiply results to resolve */
        acc0 ^= mac0 >> 11;
        acc1 += mac1 >> 13;
    }

    uint64_t checksum = total ^ ((uint64_t)acc0 << 32) ^ acc1 ^
                        ((uint64_t)acc2 << 16) ^ acc3 ^
                        ((uint64_t)mac0 << 8) ^ mac1;

    emit_result("balanced_pipeline_stress", rounds, seed, 0, checksum);
    return (int)(checksum & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
