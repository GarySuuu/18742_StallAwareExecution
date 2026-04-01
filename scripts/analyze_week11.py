#!/usr/bin/env python3
import argparse
import csv
import os
import re
from collections import Counter


def parse_stats(stats_path: str) -> dict:
    out: dict = {}
    if not os.path.exists(stats_path):
        return out
    # gem5 stats.txt lines are generally: "key value # comment"
    # We'll parse only what we need.
    wanted = {
        "simTicks": "simTicks",
        "simInsts": "simInsts",
        "simSeconds": "simSeconds",
        "hostSeconds": "hostSeconds",
        "system.cpu.ipc": "ipc",
    }
    with open(stats_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            key, val = parts[0], parts[1]
            if key in wanted:
                out[wanted[key]] = val
    return out


def parse_window_log(csv_path: str) -> dict:
    out: dict = {}
    if not os.path.exists(csv_path):
        return out
    with open(
        csv_path, "r", encoding="utf-8", errors="ignore", newline=""
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    out["windows"] = str(len(rows))
    if not rows:
        return out

    def count_ratio(field: str, prefix: str):
        c = Counter((r.get(field) or "").strip() for r in rows)
        total = sum(c.values()) or 1
        for k, v in c.items():
            if not k:
                continue
            out[f"{prefix}_{k}_ratio"] = f"{v/total:.6f}"
            out[f"{prefix}_{k}_count"] = str(v)

    # switched column may be "0/1" or "true/false"
    switched = 0
    for r in rows:
        v = (r.get("switched") or "").strip().lower()
        if v in ("1", "true", "yes", "y"):
            switched += 1
    out["switch_count"] = str(switched)
    out["switch_ratio"] = f"{switched/len(rows):.6f}"

    count_ratio("class", "class")
    count_ratio("applied_mode", "mode")
    return out


def find_latest_archive(run_root: str) -> str | None:
    """
    run_root is like .../w5000_h2_m2_cap96/serialized_pointer_chase/
    We want the most recent .../archive/<timestamp>/ folder within it.
    """
    archive_dir = os.path.join(run_root, "archive")
    if not os.path.isdir(archive_dir):
        return None
    candidates = []
    for name in os.listdir(archive_dir):
        p = os.path.join(archive_dir, name)
        if os.path.isdir(p):
            candidates.append(p)
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


LABEL_RE = re.compile(
    r"w(?P<window>\d+)_h(?P<hyst>\d+)_m(?P<hold>\d+)_cap(?P<cap>\d+)"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--sweep-base",
        required=True,
        help="Base folder containing per-point folders.",
    )
    ap.add_argument(
        "--out-csv", required=True, help="Path to write merged results CSV."
    )
    args = ap.parse_args()

    rows_out = []
    for entry in sorted(os.listdir(args.sweep_base)):
        point_dir = os.path.join(args.sweep_base, entry)
        if not os.path.isdir(point_dir):
            continue
        m = LABEL_RE.match(entry)
        if not m:
            continue

        # run_adaptive_unique.sh nests as: <point_dir>/<run_tag>/archive/<timestamp>/
        # We'll walk one level down to find <run_tag> directories, then pick latest archive.
        for run_tag_dir in os.listdir(point_dir):
            run_root = os.path.join(point_dir, run_tag_dir)
            if not os.path.isdir(run_root):
                continue
            latest = find_latest_archive(run_root)
            if not latest:
                continue

            stats = parse_stats(os.path.join(latest, "stats.txt"))
            win = parse_window_log(
                os.path.join(latest, "adaptive_window_log.csv")
            )
            row = {
                "label": entry,
                "run_tag": run_tag_dir,
                "outdir": latest,
                **m.groupdict(),
                **stats,
                **win,
            }
            rows_out.append(row)

    # Stable header: union of keys.
    keys = sorted({k for r in rows_out for k in r.keys()})
    os.makedirs(os.path.dirname(os.path.abspath(args.out_csv)), exist_ok=True)
    with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    print(f"Wrote {len(rows_out)} rows to {args.out_csv}")


if __name__ == "__main__":
    main()
