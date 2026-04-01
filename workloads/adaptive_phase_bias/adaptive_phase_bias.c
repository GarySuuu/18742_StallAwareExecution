#include <stdint.h>

static inline uint32_t xorshift32(uint32_t *state)
{
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

static inline long sys_write(int fd, const void *buf, unsigned long len)
{
    register long r0 __asm__("r0") = fd;
    register const void *r1 __asm__("r1") = buf;
    register unsigned long r2 __asm__("r2") = len;
    register long r7 __asm__("r7") = 4;
    __asm__ volatile("svc 0"
                     : "+r"(r0)
                     : "r"(r1), "r"(r2), "r"(r7)
                     : "memory");
    return r0;
}

static inline void sys_exit(int code)
{
    register long r0 __asm__("r0") = code;
    register long r7 __asm__("r7") = 1;
    __asm__ volatile("svc 0" : : "r"(r0), "r"(r7) : "memory");
    __builtin_unreachable();
}

static unsigned long parse_u32(const char *s, unsigned long def)
{
    unsigned long v = 0;
    int seen = 0;
    if (!s) {
        return def;
    }
    while (*s) {
        if (*s < '0' || *s > '9') {
            return seen ? v : def;
        }
        v = v * 10 + (unsigned long)(*s - '0');
        seen = 1;
        ++s;
    }
    return seen ? v : def;
}

static int append_str(char *buf, int pos, const char *s)
{
    while (*s) {
        buf[pos++] = *s++;
    }
    return pos;
}

static int append_u64(char *buf, int pos, uint64_t v)
{
    char tmp[32];
    int n = 0;
    if (v == 0) {
        buf[pos++] = '0';
        return pos;
    }
    while (v > 0) {
        tmp[n++] = (char)('0' + (v % 10));
        v /= 10;
    }
    while (n > 0) {
        buf[pos++] = tmp[--n];
    }
    return pos;
}

/*
 * This microbenchmark is intentionally phase-structured to favor adaptive v1:
 * - control phase: pseudo-random, hard-to-predict branches -> likely control pressure
 * - compute phase: stable arithmetic loop -> likely aggressive-friendly phase
 * A static always-aggressive baseline does not adapt between these phases.
 */
static int run_main(int argc, char **argv)
{
    unsigned long outer_loops = (argc > 1) ? parse_u32(argv[1], 2000UL) : 2000UL;
    unsigned long control_iters = (argc > 2) ? parse_u32(argv[2], 12000UL) : 12000UL;
    unsigned long compute_iters = (argc > 3) ? parse_u32(argv[3], 24000UL) : 24000UL;
    uint32_t seed = (argc > 4) ? (uint32_t)parse_u32(argv[4], 1UL) : 1U;

    uint64_t acc0 = 0x12345678ULL;
    uint64_t acc1 = 0x9abcdef0ULL;

    for (unsigned long phase = 0; phase < outer_loops; ++phase) {
        for (unsigned long i = 0; i < control_iters; ++i) {
            uint32_t r = xorshift32(&seed);
            if (r & 1U) {
                acc0 += (uint64_t)(r * 3U) ^ (acc1 >> 2);
                acc1 ^= (acc0 << 5) + 0x9e3779b9U;
            } else {
                acc1 += (uint64_t)(r * 7U) ^ (acc0 >> 3);
                acc0 ^= (acc1 << 3) + 0x85ebca6bU;
            }

            if (r & 8U) {
                acc0 += (uint64_t)(seed ^ (uint32_t)i);
            } else {
                acc1 += (uint64_t)(seed + (uint32_t)phase);
            }
        }

        for (unsigned long i = 0; i < compute_iters; ++i) {
            acc0 = acc0 * 1664525ULL + 1013904223ULL + (acc1 >> 7);
            acc1 = acc1 * 22695477ULL + 1ULL + (acc0 >> 11);
            acc0 ^= acc1 << 9;
            acc1 ^= acc0 >> 13;
        }
    }

    {
        char out[160];
        int pos = 0;
        pos = append_str(out, pos, "adaptive_phase_bias done: outer=");
        pos = append_u64(out, pos, outer_loops);
        pos = append_str(out, pos, " control=");
        pos = append_u64(out, pos, control_iters);
        pos = append_str(out, pos, " compute=");
        pos = append_u64(out, pos, compute_iters);
        pos = append_str(out, pos, " seed=");
        pos = append_u64(out, pos, seed);
        pos = append_str(out, pos, " checksum=");
        pos = append_u64(out, pos, acc0 ^ acc1);
        out[pos++] = '\n';
        sys_write(1, out, (unsigned long)pos);
    }

    return (int)((acc0 ^ acc1) & 0xffU);
}

void _start(void)
{
    register unsigned long *sp __asm__("sp");
    int argc = (int)sp[0];
    char **argv = (char **)&sp[1];
    sys_exit(run_main(argc, argv));
}
