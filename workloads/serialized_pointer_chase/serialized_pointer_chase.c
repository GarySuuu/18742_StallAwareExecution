#include <stdint.h>

#include "../common/mini_runtime.h"

typedef struct {
    uint32_t next;
    uint32_t pad;
    uint64_t payload;
} Node;

#define MAX_NODES 1048576U

static Node nodes[MAX_NODES];
static uint32_t perm[MAX_NODES];

/*
 * Serialized-memory dominated pointer chase:
 * every next access depends on the previous load result, so outstanding misses
 * stay low and memory-level parallelism is intentionally constrained.
 */
static int run_main(int argc, char **argv)
{
    uint32_t num_nodes = (argc > 1) ? (uint32_t)parse_u32(argv[1], 1048576UL)
                                    : 1048576U;
    uint32_t iters = (argc > 2) ? (uint32_t)parse_u32(argv[2], 12UL) : 12U;
    uint64_t seed = (argc > 3) ? (uint64_t)parse_u32(argv[3], 1UL) : 1ULL;
    uint32_t idx;
    uint64_t checksum = 0xD1B54A32D192ED03ULL;
    uint64_t total_steps;

    if (num_nodes < 2U) {
        num_nodes = 2U;
    }
    if (num_nodes > MAX_NODES) {
        num_nodes = MAX_NODES;
    }
    if (iters < 1U) {
        iters = 1U;
    }

    for (uint32_t i = 0; i < num_nodes; ++i) {
        perm[i] = i;
        nodes[i].next = 0;
        nodes[i].pad = i ^ 0x9e3779b9U;
        nodes[i].payload = ((uint64_t)i * 0x9E3779B185EBCA87ULL) ^ 0x94D049BB133111EBULL;
    }

    for (uint32_t i = num_nodes - 1; i > 0; --i) {
        uint32_t j = (uint32_t)(xorshift64(&seed) % (uint64_t)(i + 1U));
        uint32_t tmp = perm[i];
        perm[i] = perm[j];
        perm[j] = tmp;
    }

    for (uint32_t i = 0; i + 1U < num_nodes; ++i) {
        nodes[perm[i]].next = perm[i + 1U];
    }
    nodes[perm[num_nodes - 1U]].next = perm[0];

    idx = perm[0];
    total_steps = (uint64_t)num_nodes * (uint64_t)iters;
    for (uint64_t step = 0; step < total_steps; ++step) {
        idx = nodes[idx].next;
        checksum ^= nodes[idx].payload + ((uint64_t)idx << (step & 15U));
        checksum = rotl64(checksum, 7U);
    }

    emit_result("serialized_pointer_chase", num_nodes, iters, (uint32_t)seed, checksum ^ idx);
    return (int)(checksum & 0xffU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
