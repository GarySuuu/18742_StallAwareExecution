#!/usr/bin/env python3
"""Parse adaptive_window_log.csv and print classification/mode distribution."""
import csv
import sys
from collections import Counter

if len(sys.argv) < 2:
    print("Usage: parse_window_dist.py <csv_file>")
    sys.exit(1)

fname = sys.argv[1]
class_count = Counter()
mode_count = Counter()
total = 0

with open(fname) as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        class_count[row['class']] += 1
        mode_count[row['applied_mode']] += 1

print(f"Total windows: {total}")
print("--- Classification ---")
for k, v in sorted(class_count.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} ({100*v/total:.1f}%)")
print("--- Applied Mode ---")
for k, v in sorted(mode_count.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} ({100*v/total:.1f}%)")
