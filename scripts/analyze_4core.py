#!/usr/bin/env python3
import re, os


def get(p, pat):
    if not os.path.exists(p):
        return None
    with open(p) as f:
        for l in f:
            m = re.search(pat, l)
            if m:
                return float(m.group(1))
    return None


def mcpat_energy(p):
    if not os.path.exists(p):
        return None
    s = False
    with open(p) as f:
        for l in f:
            if "System:" in l and "Core" not in l:
                s = True
                continue
            if s:
                m = re.search(r"Total Runtime Energy\s*=\s*([\d.]+)\s*J", l)
                if m:
                    return float(m.group(1))
    return None


g = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("4-Core Same-Workload Results")
print("=" * 90)

for wl in ["branch_entropy", "phase_scan_mix"]:
    print(f"\n  {wl} (4 cores, same workload):")

    results = {}
    for cfg, label in [("baseline", "BL"), ("v4", "V4")]:
        d = os.path.join(g, f"runs/v4_multicore/{wl}_{cfg}/latest")
        ticks = get(os.path.join(d, "stats.txt"), r"simTicks\s+(\d+)")
        en_per_core = mcpat_energy(os.path.join(d, "mcpat.out"))
        en_total = en_per_core * 4 if en_per_core else None
        edp = en_total * (ticks / 1e12) if en_total and ticks else None

        ipcs = []
        for i in range(4):
            ipc = get(
                os.path.join(d, "stats.txt"),
                rf"system\.cpu{i}\.ipc\s+([\d.]+)",
            )
            ipcs.append(ipc or 0)
        avg_ipc = sum(ipcs) / 4

        results[cfg] = {
            "ticks": ticks,
            "en": en_total,
            "edp": edp,
            "ipcs": ipcs,
            "avg_ipc": avg_ipc,
        }

        ipc_str = " ".join(f"{v:.3f}" for v in ipcs)
        print(
            f"    {label}: avg_IPC={avg_ipc:.3f}  Energy={en_total:.3f}J  EDP={edp:.5f}"
        )
        print(f"        per-CPU IPC: [{ipc_str}]")

    bl = results["baseline"]
    v4 = results["v4"]

    dipc = (v4["avg_ipc"] / bl["avg_ipc"] - 1) * 100
    deng = (v4["en"] / bl["en"] - 1) * 100
    dedp = (1 - v4["edp"] / bl["edp"]) * 100
    dticks = (v4["ticks"] / bl["ticks"] - 1) * 100

    print(f"    --- Improvement ---")
    print(
        f"    dIPC(avg): {dipc:+.1f}%  dEnergy: {deng:+.1f}%  dSimTicks: {dticks:+.1f}%  dEDP: {dedp:+.1f}%"
    )

    per_cpu_dipc = [
        (v4["ipcs"][i] / bl["ipcs"][i] - 1) * 100 if bl["ipcs"][i] > 0 else 0
        for i in range(4)
    ]
    dipc_str = " ".join(f"{v:+.1f}%" for v in per_cpu_dipc)
    print(f"    per-CPU dIPC: [{dipc_str}]")
