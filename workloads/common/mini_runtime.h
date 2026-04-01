#ifndef MINI_RUNTIME_H
#define MINI_RUNTIME_H

#include <stdint.h>

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

int raise(int sig)
{
    (void)sig;
    return 0;
}

static inline uint32_t xorshift32(uint32_t *state)
{
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

static inline uint64_t xorshift64(uint64_t *state)
{
    uint64_t x = *state;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    *state = x;
    return x;
}

static inline unsigned long parse_u32(const char *s, unsigned long def)
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

static inline int append_str(char *buf, int pos, const char *s)
{
    while (*s) {
        buf[pos++] = *s++;
    }
    return pos;
}

static inline int append_u64(char *buf, int pos, uint64_t v)
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

static inline int append_u32(char *buf, int pos, uint32_t v)
{
    return append_u64(buf, pos, (uint64_t)v);
}

static inline uint64_t rotl64(uint64_t value, unsigned shift)
{
    shift &= 63U;
    return (value << shift) | (value >> ((64U - shift) & 63U));
}

static inline void emit_result(const char *name,
                               uint64_t arg0,
                               uint64_t arg1,
                               uint64_t arg2,
                               uint64_t checksum)
{
    char out[192];
    int pos = 0;
    pos = append_str(out, pos, name);
    pos = append_str(out, pos, " done: a0=");
    pos = append_u64(out, pos, arg0);
    pos = append_str(out, pos, " a1=");
    pos = append_u64(out, pos, arg1);
    pos = append_str(out, pos, " a2=");
    pos = append_u64(out, pos, arg2);
    pos = append_str(out, pos, " checksum=");
    pos = append_u64(out, pos, checksum);
    out[pos++] = '\n';
    sys_write(1, out, (unsigned long)pos);
}

#define DEFINE_WORKLOAD_ENTRY(run_fn)              \
    void _start(void)                              \
    {                                              \
        register unsigned long *sp __asm__("sp"); \
        int argc = (int)sp[0];                     \
        char **argv = (char **)&sp[1];             \
        sys_exit(run_fn(argc, argv));              \
    }

#endif
