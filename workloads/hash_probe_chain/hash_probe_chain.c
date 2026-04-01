#include <stdint.h>

#include "../common/mini_runtime.h"

#define MAX_ENTRIES 262144U
#define MAX_BUCKETS 65536U

static uint32_t bucket_head[MAX_BUCKETS];
static uint32_t next_idx[MAX_ENTRIES];
static uint32_t keys[MAX_ENTRIES];
static uint64_t payloads[MAX_ENTRIES];

/*
 * Hash-table probe microbenchmark:
 * each lookup follows a collision chain, so misses are dependency-ordered and
 * resemble serialized key-value lookups with limited MLP.
 */
static int run_main(int argc, char **argv)
{
    uint32_t entries = (argc > 1) ? (uint32_t)parse_u32(argv[1], 131072UL)
                                  : 131072U;
    uint32_t rounds = (argc > 2) ? (uint32_t)parse_u32(argv[2], 64UL) : 64U;
    uint32_t seed = (argc > 3) ? (uint32_t)parse_u32(argv[3], 1UL) : 1U;
    uint32_t bucket_count;
    uint64_t checksum = 0x6a09e667f3bcc909ULL;

    if (entries < 1024U) {
        entries = 1024U;
    }
    if (entries > MAX_ENTRIES) {
        entries = MAX_ENTRIES;
    }
    if (rounds < 1U) {
        rounds = 1U;
    }

    bucket_count = entries / 4U;
    if (bucket_count < 256U) {
        bucket_count = 256U;
    }
    if (bucket_count > MAX_BUCKETS) {
        bucket_count = MAX_BUCKETS;
    }

    for (uint32_t b = 0; b < bucket_count; ++b) {
        bucket_head[b] = 0xffffffffU;
    }

    for (uint32_t i = 0; i < entries; ++i) {
        uint32_t raw = xorshift32(&seed) ^ (i * 0x9e3779b9U);
        uint32_t bucket = raw % bucket_count;
        keys[i] = raw | 1U;
        payloads[i] = ((uint64_t)raw << 17) ^ (0x94d049bb133111ebULL + i);
        next_idx[i] = bucket_head[bucket];
        bucket_head[bucket] = i;
    }

    for (uint32_t r = 0; r < rounds; ++r) {
        for (uint32_t q = 0; q < entries; ++q) {
            uint32_t query_index = (q * 17U + r * 131U) % entries;
            uint32_t key = keys[query_index];
            uint32_t bucket = key % bucket_count;
            uint32_t cursor = bucket_head[bucket];

            while (cursor != 0xffffffffU) {
                if (keys[cursor] == key) {
                    checksum ^= payloads[cursor] + ((uint64_t)cursor << (r & 15U));
                    checksum = rotl64(checksum, 5U);
                    break;
                }
                checksum ^= ((uint64_t)keys[cursor] << 9) + payloads[cursor];
                checksum = rotl64(checksum, 3U);
                cursor = next_idx[cursor];
            }
        }
    }

    emit_result("hash_probe_chain", entries, rounds, seed, checksum);
    return (int)(checksum & 0xffU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
