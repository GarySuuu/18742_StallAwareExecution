# Baseline Definition for This Project

## What this baseline is

- This project baseline is a `gem5` static configuration using `ARM` ISA and `DerivO3CPU`.
- This baseline is **not** intended to model a specific commercial ARM core.
- This baseline is the **reference baseline** for evaluating future adaptive/new-architecture mechanisms in this project.

## Standard static baseline (recommended)

- ISA: `ARM`
- CPU type: `DerivO3CPU`
- Core count: single-core (`-n 1`)
- Simulation mode: `SE` mode (via `configs/deprecated/example/se.py`)
- Cache hierarchy: `--caches --l2cache` enabled
- Memory size: `--mem-size=2GB`
- Workload policy: deterministic ARM test binary (current default: `tests/test-progs/hello/bin/arm/linux/hello`)
- Max instructions policy: fixed per experiment campaign (default in script: `50000000`)
- Output naming:
  - active output dir: user argument (default `runs/baseline/hello_o3_static`)
  - archived run: `runs/baseline/archive/<timestamp>/`
  - latest link: `runs/baseline/latest`

## Must stay fixed for fair baseline comparison

- ISA (`ARM`)
- CPU model (`DerivO3CPU`)
- number of cores (`1`)
- simulation mode (`SE`)
- cache hierarchy enablement (`--caches --l2cache`)
- memory size (`2GB`)
- baseline pipeline/queue/register configuration from `config.ini`
- adaptation behavior disabled for baseline (no runtime adaptation policy active)
- workload input and instruction budget (`maxinsts`) within one comparison batch

## Allowed adjustable knobs for new mechanism experiments

- fetch/decode/rename throttling
- dispatch/issue/commit throttling
- effective in-flight cap
- ROB/IQ/LSQ related dynamic caps
- branch-predictor interaction policies
- mode-switch thresholds/hysteresis/sampling window parameters
- any adaptive controller policy parameters

## Generated artifacts

After running `scripts/run_baseline.sh`, the run produces:

- `stats.txt`, `config.ini`, `config.json`, `run.log`
- `baseline_config_summary.md` (auto-generated from `config.ini`)
- `run_meta.txt` (command, timestamp, output location)

Use `runs/baseline/latest/` as the stable pointer to the latest baseline run outputs.
