#include <stdint.h>

#include "../common/mini_runtime.h"

/*
 * Rename/dispatch width stress:
 * Many short 1-cycle ALU instructions that resolve quickly, with high
 * register pressure requiring many renames per cycle.
 *
 * Intent: isolate the effect of adaptiveConservativeRenameWidth and
 * adaptiveConservativeDispatchWidth. When these are limited, the pipeline
 * throughput drops because fewer instructions can be renamed/dispatched
 * per cycle, even though IQ and execution are not bottlenecked.
 *
 * Design: 16 accumulator variables that are all touched each iteration.
 * Instructions complete in 1 cycle, so they retire fast. The rename and
 * dispatch stages become the critical throughput limiter.
 *
 * Expected adaptive class: Resource (high commit activity)
 */
static int run_main(int argc, char **argv)
{
    uint32_t rounds = (argc > 1) ? (uint32_t)parse_u32(argv[1], 200000UL) : 200000U;
    uint32_t seed = (argc > 2) ? (uint32_t)parse_u32(argv[2], 1UL) : 1U;

    /* 16 accumulators to maximize register rename pressure */
    uint32_t r0  = seed;
    uint32_t r1  = seed ^ 0x11111111;
    uint32_t r2  = seed ^ 0x22222222;
    uint32_t r3  = seed ^ 0x33333333;
    uint32_t r4  = seed ^ 0x44444444;
    uint32_t r5  = seed ^ 0x55555555;
    uint32_t r6  = seed ^ 0x66666666;
    uint32_t r7  = seed ^ 0x77777777;
    uint32_t r8  = seed ^ 0x88888888;
    uint32_t r9  = seed ^ 0x99999999;
    uint32_t r10 = seed ^ 0xAAAAAAAA;
    uint32_t r11 = seed ^ 0xBBBBBBBB;
    uint32_t r12 = seed ^ 0xCCCCCCCC;
    uint32_t r13 = seed ^ 0xDDDDDDDD;
    uint32_t r14 = seed ^ 0xEEEEEEEE;
    uint32_t r15 = seed ^ 0xFFFFFFFF;

    for (uint32_t i = 0; i < rounds; ++i) {
        /* 32 simple add/xor ops touching all 16 registers.
           Each is a 1-cycle instruction. All independent within
           the group of 2 (each register read-then-written). */
        r0  += r1;    r1  ^= r2;
        r2  += r3;    r3  ^= r4;
        r4  += r5;    r5  ^= r6;
        r6  += r7;    r7  ^= r8;
        r8  += r9;    r9  ^= r10;
        r10 += r11;   r11 ^= r12;
        r12 += r13;   r13 ^= r14;
        r14 += r15;   r15 ^= r0;

        /* Another 16 ops with reversed dependency direction */
        r15 += r14;   r14 ^= r13;
        r13 += r12;   r12 ^= r11;
        r11 += r10;   r10 ^= r9;
        r9  += r8;    r8  ^= r7;
        r7  += r6;    r6  ^= r5;
        r5  += r4;    r4  ^= r3;
        r3  += r2;    r2  ^= r1;
        r1  += r0;    r0  ^= r15;
    }

    uint64_t checksum = (uint64_t)r0  ^ ((uint64_t)r1  << 3) ^
                        (uint64_t)r2  ^ ((uint64_t)r3  << 5) ^
                        (uint64_t)r4  ^ ((uint64_t)r5  << 7) ^
                        (uint64_t)r6  ^ ((uint64_t)r7  << 11) ^
                        (uint64_t)r8  ^ ((uint64_t)r9  << 13) ^
                        (uint64_t)r10 ^ ((uint64_t)r11 << 17) ^
                        (uint64_t)r12 ^ ((uint64_t)r13 << 19) ^
                        (uint64_t)r14 ^ ((uint64_t)r15 << 23);

    emit_result("rename_dispatch_stress", rounds, seed, 0, checksum);
    return (int)(checksum & 0xFFU);
}

DEFINE_WORKLOAD_ENTRY(run_main)
