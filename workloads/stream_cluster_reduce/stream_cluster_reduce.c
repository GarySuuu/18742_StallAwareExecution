#include <stdint.h>

#include "../common/mini_runtime.h"

#define MAX_ELEMS 1048576U

static uint32_t in_a[MAX_ELEMS];
static uint32_t in_b[MAX_ELEMS];
static uint32_t in_c[MAX_ELEMS];
static uint32_t out_d[MAX_ELEMS];

/*
 * Streaming reduction kernel:
 * long sequential passes over multiple arrays approximate analytics or image
 * pipelines with higher memory concurrency and sustained backend activity.
 */
static int run_main(int argc, char **argv)
{
    uint32_t elems = (argc > 1) ? (uint32_t)parse_u32(argv[1], 1048576UL)
                                : 1048576U;
    uint32_t passes = (argc > 2) ? (uint32_t)parse_u32(argv[2], 16UL) : 16U;
    uint32_t seed = (argc > 3) ? (uint32_t)parse_u32(argv[3], 1UL) : 1U;
    uint64_t checksum = 0x3c6ef372fe94f82bULL;

    if (elems < 1024U) {
        elems = 1024U;
    }
    if (elems > MAX_ELEMS) {
        elems = MAX_ELEMS;
    }
    if (passes < 1U) {
        passes = 1U;
    }

    for (uint32_t i = 0; i < elems; ++i) {
        uint32_t r = xorshift32(&seed);
        in_a[i] = r;
        in_b[i] = r ^ 0x9e3779b9U;
        in_c[i] = (r << 7) ^ (i * 13U);
        out_d[i] = 0U;
    }

    for (uint32_t p = 0; p < passes; ++p) {
        for (uint32_t i = 0; i < elems; ++i) {
            uint64_t a = in_a[i];
            uint64_t b = in_b[i];
            uint64_t c = in_c[i];
            uint64_t v = (a * 3ULL) + (b * 5ULL) + (c * 7ULL) + (checksum >> 11);
            out_d[i] = (uint32_t)(v ^ (v >> 17));
            checksum += v + out_d[i];
        }
        for (uint32_t i = 0; i < elems; ++i) {
            in_a[i] ^= out_d[i] + p;
            in_b[i] += out_d[i] ^ (p * 17U);
            in_c[i] = (in_c[i] << 1) ^ out_d[i];
            checksum ^= ((uint64_t)out_d[i] << (i & 7U));
        }
    }

    emit_result("stream_cluster_reduce", elems, passes, seed, checksum);
    return (int)(checksum & 0xffU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
