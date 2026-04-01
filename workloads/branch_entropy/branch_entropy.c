#include <stdint.h>

#include "../common/mini_runtime.h"

#define MAX_STATE 65536U

static uint32_t state_table[MAX_STATE];

/*
 * Control-dominated branch cascade:
 * pseudo-random branches keep speculation noisy while the working set stays
 * small, approximating branch-heavy request handling or rule evaluation.
 */
static int run_main(int argc, char **argv)
{
    uint32_t state_size = (argc > 1) ? (uint32_t)parse_u32(argv[1], 32768UL)
                                     : 32768U;
    uint32_t iters = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1024UL) : 1024U;
    uint32_t seed = (argc > 3) ? (uint32_t)parse_u32(argv[3], 1UL) : 1U;
    uint32_t idx = 0;
    uint64_t acc = 0x84222325cbf29ce4ULL;
    uint64_t total_steps;

    if (state_size < 64U) {
        state_size = 64U;
    }
    if (state_size > MAX_STATE) {
        state_size = MAX_STATE;
    }
    if (iters < 1U) {
        iters = 1U;
    }

    for (uint32_t i = 0; i < state_size; ++i) {
        uint32_t x = (uint32_t)xorshift64((uint64_t *)&acc);
        state_table[i] = x ^ (i * 0x9e3779b9U);
    }

    total_steps = (uint64_t)state_size * (uint64_t)iters;
    for (uint64_t step = 0; step < total_steps; ++step) {
        uint32_t r = xorshift32(&seed) ^ state_table[idx];

        if (r & 1U) {
            acc += ((uint64_t)r << 3) ^ (acc >> 7);
        } else {
            acc ^= ((uint64_t)r << 11) + 0x9e3779b97f4a7c15ULL;
        }

        if (r & 2U) {
            acc = rotl64(acc, 9U) + state_table[(idx + 17U) % state_size];
        } else {
            acc = rotl64(acc ^ r, 21U) - state_table[(idx + 3U) % state_size];
        }

        if ((r ^ (uint32_t)acc) & 4U) {
            idx = (idx + r + 7U) % state_size;
        } else if (r & 8U) {
            idx = (idx + state_table[(idx + 11U) % state_size] + 1U) % state_size;
        } else {
            idx = (idx ^ r ^ state_table[(idx + 5U) % state_size]) % state_size;
        }

        state_table[idx] ^= r + (uint32_t)step;
    }

    emit_result("branch_entropy", state_size, iters, seed, acc ^ idx);
    return (int)(acc & 0xffU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
