#include <stdint.h>

#include "../common/mini_runtime.h"

#define MAX_ELEMS 1048576U

static uint32_t flags[MAX_ELEMS];
static uint32_t data_a[MAX_ELEMS];
static uint32_t data_b[MAX_ELEMS];

/*
 * Mixed-phase analytics kernel:
 * phase 1 filters branchy metadata, phase 2 performs a long streaming reduce.
 * It is intended to exercise class changes rather than a single fixed mode.
 */
static int run_main(int argc, char **argv)
{
    uint32_t elems = (argc > 1) ? (uint32_t)parse_u32(argv[1], 524288UL)
                                : 524288U;
    uint32_t phases = (argc > 2) ? (uint32_t)parse_u32(argv[2], 24UL) : 24U;
    uint32_t seed = (argc > 3) ? (uint32_t)parse_u32(argv[3], 1UL) : 1U;
    uint64_t score0 = 0x243f6a8885a308d3ULL;
    uint64_t score1 = 0x13198a2e03707344ULL;

    if (elems < 1024U) {
        elems = 1024U;
    }
    if (elems > MAX_ELEMS) {
        elems = MAX_ELEMS;
    }
    if (phases < 1U) {
        phases = 1U;
    }

    for (uint32_t i = 0; i < elems; ++i) {
        uint32_t r = xorshift32(&seed);
        flags[i] = r;
        data_a[i] = r ^ (i * 17U);
        data_b[i] = (r << 3) ^ (i * 29U);
    }

    for (uint32_t p = 0; p < phases; ++p) {
        for (uint32_t i = 0; i < elems; ++i) {
            uint32_t f = flags[i] ^ (p * 0x9e3779b9U);
            if (f & 1U) {
                score0 += data_a[i] + (score1 >> 3);
            } else if (f & 2U) {
                score0 ^= ((uint64_t)data_b[i] << 5) + score1;
            } else {
                score1 += (uint64_t)data_a[i] ^ (score0 << 1);
            }
            if (f & 8U) {
                flags[i] = f ^ (uint32_t)score0;
            }
        }

        for (uint32_t i = 0; i < elems; ++i) {
            uint64_t a = data_a[i];
            uint64_t b = data_b[i];
            score0 += a * 3ULL + b * 5ULL + (score1 >> 7);
            score1 ^= (a << 9) + (b << 1) + score0;
            data_a[i] = (uint32_t)(score0 ^ a);
            data_b[i] = (uint32_t)(score1 + b);
        }
    }

    emit_result("phase_scan_mix", elems, phases, seed, score0 ^ score1);
    return (int)((score0 ^ score1) & 0xffU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
