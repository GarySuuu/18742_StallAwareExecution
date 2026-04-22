#!/usr/bin/env python3
import argparse
import json
import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def load_stats(stats_path: Path) -> dict[str, float]:
    stats: dict[str, float] = {}
    with stats_path.open() as fp:
        for raw in fp:
            left = raw.split("#", 1)[0].strip()
            if not left:
                continue
            parts = left.split()
            if len(parts) < 2:
                continue
            try:
                stats[parts[0]] = float(parts[1])
            except ValueError:
                continue
    return stats


def get_stat(stats: dict[str, float], key: str, default: float = 0.0) -> float:
    val = stats.get(key, default)
    if math.isnan(val) or math.isinf(val):
        return default
    return val


def parse_config(config_path: Path) -> tuple[dict, dict]:
    root = json.loads(config_path.read_text())
    system = root["system"]
    cpu = (
        system["cpu"][0] if isinstance(system["cpu"], list) else system["cpu"]
    )
    return system, cpu


def parse_template(template_path: Path) -> ET.ElementTree:
    text = template_path.read_text()
    # The bundled regression XML has a few malformed attribute tokens that McPAT
    # accepts but ElementTree rejects. Normalize them before parsing.
    fixes = {
        'execu_bypass_start_wiring_level"value': 'execu_bypass_start_wiring_level" value',
        'writeback_buff_access_mode"value': 'writeback_buff_access_mode" value',
    }
    for src, dst in fixes.items():
        text = text.replace(src, dst)
    return ET.ElementTree(ET.fromstring(text))


def find_component(root: ET.Element, comp_id: str) -> ET.Element:
    comp = root.find(f".//component[@id='{comp_id}']")
    if comp is None:
        raise KeyError(f"Missing component {comp_id}")
    return comp


def find_first_component(root: ET.Element, *comp_ids: str) -> ET.Element:
    for comp_id in comp_ids:
        comp = root.find(f".//component[@id='{comp_id}']")
        if comp is not None:
            return comp
    raise KeyError(f"Missing components {comp_ids}")


def set_param(comp: ET.Element, name: str, value) -> None:
    elem = comp.find(f"./param[@name='{name}']")
    if elem is None:
        raise KeyError(f"Missing param {name} in {comp.attrib.get('id')}")
    elem.set("value", str(value))


def set_stat(comp: ET.Element, name: str, value) -> None:
    elem = comp.find(f"./stat[@name='{name}']")
    if elem is None:
        raise KeyError(f"Missing stat {name} in {comp.attrib.get('id')}")
    elem.set("value", str(int(value) if float(value).is_integer() else value))


def set_stat_if_present(comp: ET.Element, name: str, value) -> None:
    elem = comp.find(f"./stat[@name='{name}']")
    if elem is not None:
        elem.set(
            "value", str(int(value) if float(value).is_integer() else value)
        )


def set_param_if_present(comp: ET.Element, name: str, value) -> None:
    elem = comp.find(f"./param[@name='{name}']")
    if elem is not None:
        elem.set("value", str(value))


def has_param(comp: ET.Element, name: str) -> bool:
    return comp.find(f"./param[@name='{name}']") is not None


def set_cache_geometry(
    comp: ET.Element,
    *,
    size: int,
    line_size: int,
    assoc: int,
    throughput: int,
    latency: int,
    policy: int,
    config_name: str,
) -> None:
    if has_param(comp, "size"):
        set_param(comp, "size", size)
        set_param(comp, "block_size", line_size)
        set_param(comp, "assoc", assoc)
        set_param(comp, "latency", latency)
        set_param(comp, "throughput", throughput)
        return

    if has_param(comp, config_name):
        block_width = max(line_size // 8, 1)
        config = f"{size},{block_width},{assoc},1,{throughput},{latency},32,{policy}"
        set_param(comp, config_name, config)
        return

    raise KeyError(f"Missing cache geometry params in {comp.attrib.get('id')}")


def set_btb_geometry(
    comp: ET.Element,
    *,
    entries: int,
    assoc: int = 2,
    throughput: int = 1,
    latency: int = 3,
) -> None:
    if has_param(comp, "size"):
        set_param(comp, "size", entries)
        set_param(comp, "block_size", 4)
        set_param(comp, "assoc", assoc)
        return

    if has_param(comp, "BTB_config"):
        config = f"{entries},4,{assoc},1,{throughput},{latency}"
        set_param(comp, "BTB_config", config)
        return

    raise KeyError(f"Missing BTB geometry params in {comp.attrib.get('id')}")


def set_tlb_stats(comp: ET.Element, *, accesses: float, misses: float) -> None:
    if comp.find("./stat[@name='read_accesses']") is not None:
        set_stat(comp, "read_accesses", accesses)
        set_stat(comp, "read_misses", misses)
    else:
        set_stat(comp, "total_accesses", accesses)
        set_stat(comp, "total_misses", misses)
    set_stat(comp, "conflicts", 0)


def parse_clock_mhz(system_cfg: dict) -> int:
    cpu_clk_ticks = system_cfg["cpu_clk_domain"]["clock"][0]
    ticks_per_sec = 1_000_000_000_000
    return int(round((ticks_per_sec / cpu_clk_ticks) / 1_000_000))


def generate_xml(
    template_path: Path,
    config_path: Path,
    stats_path: Path,
    output_path: Path,
    num_cores: int = 1,
) -> None:
    system_cfg, cpu_cfg = parse_config(config_path)
    stats = load_stats(stats_path)
    tree = parse_template(template_path)
    root = tree.getroot()

    system = find_component(root, "system")
    core = find_component(root, "system.core0")
    predictor = find_component(root, "system.core0.predictor")
    itlb = find_component(root, "system.core0.itlb")
    icache = find_component(root, "system.core0.icache")
    dtlb = find_component(root, "system.core0.dtlb")
    dcache = find_component(root, "system.core0.dcache")
    # Some McPAT templates name the BTB component "BTB" instead of
    # "btargetbuf". Accept both to keep the conversion script usable across
    # our bundled templates and older run directories.
    btb = find_first_component(
        root, "system.core0.btargetbuf", "system.core0.BTB"
    )
    l2 = find_component(root, "system.L20")

    # For multicore: use cpu0 stats as representative core
    cpu_prefix = "system.cpu0" if num_cores > 1 else "system.cpu"

    clock_mhz = parse_clock_mhz(system_cfg)
    line_size = int(system_cfg.get("cache_line_size", 64))
    sim_insts = get_stat(stats, "simInsts")
    total_cycles = max(get_stat(stats, f"{cpu_prefix}.numCycles"), 1.0)
    load_insts = get_stat(
        stats, f"{cpu_prefix}.commit.committedInstType_0::MemRead"
    )
    store_insts = get_stat(
        stats, f"{cpu_prefix}.commit.committedInstType_0::MemWrite"
    )
    branch_insts = get_stat(stats, f"{cpu_prefix}.branchPred.lookups")
    int_insts = max(sim_insts - load_insts - store_insts - branch_insts, 0.0)
    pipeline_duty = min(
        get_stat(stats, f"{cpu_prefix}.ipc")
        / max(int(cpu_cfg.get("commitWidth", 1)), 1),
        1.0,
    )

    # For multicore: McPAT runs with single-core template using cpu0 stats.
    # The caller multiplies energy by num_cores for total system energy.

    set_param(system, "target_core_clockrate", clock_mhz)
    set_stat(system, "total_cycles", total_cycles)

    set_param(core, "clock_rate", clock_mhz)
    set_param(core, "fetch_width", int(cpu_cfg.get("fetchWidth", 1)))
    set_param(core, "decode_width", int(cpu_cfg.get("decodeWidth", 1)))
    set_param(core, "issue_width", int(cpu_cfg.get("issueWidth", 1)))
    set_param(core, "peak_issue_width", int(cpu_cfg.get("issueWidth", 1)))
    set_param(core, "commit_width", int(cpu_cfg.get("commitWidth", 1)))
    set_param(
        core, "instruction_window_size", int(cpu_cfg.get("numIQEntries", 16))
    )
    set_param(
        core,
        "fp_instruction_window_size",
        max(int(cpu_cfg.get("numIQEntries", 16)) // 2, 1),
    )
    set_param(core, "ROB_size", int(cpu_cfg.get("numROBEntries", 64)))
    set_param(
        core, "phy_Regs_IRF_size", int(cpu_cfg.get("numPhysIntRegs", 128))
    )
    set_param(
        core, "phy_Regs_FRF_size", int(cpu_cfg.get("numPhysFloatRegs", 128))
    )
    set_param(core, "store_buffer_size", int(cpu_cfg.get("SQEntries", 16)))
    set_param(core, "load_buffer_size", int(cpu_cfg.get("LQEntries", 16)))
    set_param(core, "RAS_size", int(cpu_cfg["branchPred"].get("RASSize", 16)))

    set_stat(core, "total_instructions", sim_insts)
    set_stat(core, "int_instructions", int_insts)
    set_stat(core, "fp_instructions", 0)
    set_stat(core, "branch_instructions", branch_insts)
    set_stat(
        core,
        "branch_mispredictions",
        get_stat(stats, f"{cpu_prefix}.commit.branchMispredicts"),
    )
    set_stat(core, "load_instructions", load_insts)
    set_stat(core, "store_instructions", store_insts)
    set_stat(core, "committed_instructions", sim_insts)
    set_stat(core, "committed_int_instructions", int_insts)
    set_stat(core, "committed_fp_instructions", 0)
    set_stat(core, "pipeline_duty_cycle", round(pipeline_duty, 6))
    set_stat(core, "total_cycles", total_cycles)
    set_stat(
        core,
        "ROB_reads",
        get_stat(stats, f"{cpu_prefix}.rob.reads", sim_insts),
    )
    set_stat(
        core,
        "ROB_writes",
        get_stat(stats, f"{cpu_prefix}.rob.writes", sim_insts),
    )
    set_stat(
        core,
        "rename_reads",
        get_stat(stats, f"{cpu_prefix}.rename.lookups", sim_insts),
    )
    set_stat(
        core,
        "rename_writes",
        get_stat(stats, f"{cpu_prefix}.rename.renamedInsts", sim_insts),
    )
    set_stat(core, "fp_rename_reads", 0)
    set_stat(core, "fp_rename_writes", 0)
    set_stat(
        core,
        "inst_window_reads",
        get_stat(stats, f"{cpu_prefix}.instsIssued", sim_insts),
    )
    set_stat(
        core,
        "inst_window_writes",
        get_stat(stats, f"{cpu_prefix}.instsAdded", sim_insts),
    )
    set_stat(
        core,
        "inst_window_wakeup_accesses",
        get_stat(stats, f"{cpu_prefix}.instsIssued", sim_insts),
    )
    set_stat(core, "fp_inst_window_reads", 0)
    set_stat(core, "fp_inst_window_writes", 0)
    set_stat(core, "fp_inst_window_wakeup_accesses", 0)
    set_stat(
        core,
        "int_regfile_reads",
        get_stat(stats, f"{cpu_prefix}.rename.intLookups", int_insts),
    )
    set_stat(core, "float_regfile_reads", 0)
    set_stat(
        core,
        "int_regfile_writes",
        get_stat(stats, f"{cpu_prefix}.rename.renamedOperands", int_insts),
    )
    set_stat(core, "float_regfile_writes", 0)
    set_stat(
        core,
        "function_calls",
        get_stat(stats, f"{cpu_prefix}.commit.functionCalls"),
    )
    set_stat(core, "context_switches", 0)
    set_stat(
        core,
        "ialu_accesses",
        get_stat(stats, f"{cpu_prefix}.commit.committedInstType_0::IntAlu"),
    )
    set_stat(core, "fpu_accesses", 0)
    set_stat(
        core,
        "mul_accesses",
        get_stat(stats, f"{cpu_prefix}.commit.committedInstType_0::IntMult"),
    )
    set_stat(
        core,
        "cdb_alu_accesses",
        get_stat(stats, f"{cpu_prefix}.commit.committedInstType_0::IntAlu"),
    )
    set_stat(
        core,
        "cdb_mul_accesses",
        get_stat(stats, f"{cpu_prefix}.commit.committedInstType_0::IntMult"),
    )
    set_stat(core, "cdb_fpu_accesses", 0)

    bp_cfg = cpu_cfg["branchPred"]
    set_param(
        predictor,
        "local_predictor_entries",
        int(bp_cfg.get("localPredictorSize", 2048)),
    )
    set_param(
        predictor,
        "global_predictor_entries",
        int(bp_cfg.get("globalPredictorSize", 8192)),
    )
    set_param(
        predictor, "global_predictor_bits", int(bp_cfg.get("globalCtrBits", 2))
    )
    set_param(
        predictor,
        "chooser_predictor_entries",
        int(bp_cfg.get("choicePredictorSize", 8192)),
    )
    set_param(
        predictor,
        "chooser_predictor_bits",
        int(bp_cfg.get("choiceCtrBits", 2)),
    )

    set_stat(
        itlb,
        "total_accesses",
        get_stat(stats, f"{cpu_prefix}.icache.ReadReq.accesses::total"),
    )
    set_stat(itlb, "total_misses", 4)
    set_stat(itlb, "conflicts", 0)

    set_cache_geometry(
        icache,
        size=int(cpu_cfg["icache"]["size"]),
        line_size=line_size,
        assoc=int(cpu_cfg["icache"]["assoc"]),
        throughput=int(cpu_cfg["icache"].get("tag_latency", 2)),
        latency=int(cpu_cfg["icache"].get("response_latency", 2)),
        policy=0,
        config_name="icache_config",
    )
    set_stat(
        icache,
        "read_accesses",
        get_stat(stats, f"{cpu_prefix}.icache.ReadReq.accesses::total"),
    )
    set_stat(
        icache,
        "read_misses",
        get_stat(stats, f"{cpu_prefix}.icache.ReadReq.misses::total"),
    )
    set_stat(icache, "conflicts", 0)
    set_stat_if_present(icache, "duty_cycle", 1)

    set_tlb_stats(
        dtlb,
        accesses=get_stat(stats, f"{cpu_prefix}.dcache.demandAccesses::total"),
        misses=4,
    )

    d_reads = get_stat(
        stats, "system.cpu.dcache.ReadReq.accesses::total"
    ) + get_stat(stats, f"{cpu_prefix}.dcache.LoadLockedReq.accesses::total")
    d_writes = get_stat(
        stats, "system.cpu.dcache.WriteReq.accesses::total"
    ) + get_stat(stats, f"{cpu_prefix}.dcache.StoreCondReq.accesses::total")
    d_read_misses = get_stat(
        stats, "system.cpu.dcache.ReadReq.misses::total"
    ) + get_stat(stats, f"{cpu_prefix}.dcache.LoadLockedReq.misses::total")
    d_write_misses = get_stat(
        stats, "system.cpu.dcache.WriteReq.misses::total"
    )
    set_cache_geometry(
        dcache,
        size=int(cpu_cfg["dcache"]["size"]),
        line_size=line_size,
        assoc=int(cpu_cfg["dcache"]["assoc"]),
        throughput=int(cpu_cfg["dcache"].get("tag_latency", 2)),
        latency=int(cpu_cfg["dcache"].get("response_latency", 2)),
        policy=1,
        config_name="dcache_config",
    )
    set_stat(dcache, "read_accesses", d_reads)
    set_stat(dcache, "write_accesses", d_writes)
    set_stat(dcache, "read_misses", d_read_misses)
    set_stat(dcache, "write_misses", d_write_misses)
    set_stat(dcache, "conflicts", 0)
    set_stat_if_present(dcache, "duty_cycle", 1)

    set_btb_geometry(btb, entries=int(bp_cfg.get("BTBEntries", 4096)))
    set_stat(
        btb,
        "read_accesses",
        get_stat(stats, f"{cpu_prefix}.branchPred.BTBLookups"),
    )
    set_stat(
        btb,
        "write_accesses",
        get_stat(stats, f"{cpu_prefix}.branchPred.BTBUpdates"),
    )

    l2_reads = get_stat(
        stats, "system.l2.ReadCleanReq.accesses::total"
    ) + get_stat(stats, "system.l2.ReadSharedReq.accesses::total")
    l2_writes = get_stat(
        stats, "system.l2.WritebackClean.accesses::total"
    ) + get_stat(stats, "system.l2.ReadExReq.accesses::total")
    l2_read_misses = get_stat(
        stats, "system.l2.ReadCleanReq.misses::total"
    ) + get_stat(stats, "system.l2.ReadSharedReq.misses::total")
    l2_write_misses = get_stat(stats, "system.l2.ReadExReq.misses::total")
    set_cache_geometry(
        l2,
        size=int(system_cfg["l2"]["size"]),
        line_size=line_size,
        assoc=int(system_cfg["l2"]["assoc"]),
        throughput=int(system_cfg["l2"].get("tag_latency", 20)),
        latency=int(system_cfg["l2"].get("response_latency", 20)),
        policy=1,
        config_name="L2_config",
    )
    set_param(l2, "clockrate", clock_mhz)
    set_stat(l2, "read_accesses", l2_reads)
    set_stat(l2, "write_accesses", l2_writes)
    set_stat(l2, "read_misses", l2_read_misses)
    set_stat(l2, "write_misses", l2_write_misses)
    set_stat(l2, "conflicts", 0)
    set_stat_if_present(l2, "duty_cycle", 1)

    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a minimal McPAT XML from gem5 outputs."
    )
    parser.add_argument("--stats", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--template",
        default="ext/mcpat/regression/test-0/power_region0.xml",
        help="McPAT XML template base",
    )
    parser.add_argument(
        "--num-cores",
        type=int,
        default=1,
        help="Number of cores (>1 reads cpu0 stats, sets number_of_cores)",
    )
    parser.add_argument("--run-mcpat", action="store_true")
    parser.add_argument("--mcpat-binary", default="build/mcpat/mcpat")
    parser.add_argument("--mcpat-output", default="")
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_xml(
        Path(args.template),
        Path(args.config),
        Path(args.stats),
        out,
        num_cores=args.num_cores,
    )

    if args.run_mcpat:
        cmd = [args.mcpat_binary, "-infile", str(out), "-print_level", "5"]
        if args.mcpat_output:
            with Path(args.mcpat_output).open("w") as fp:
                subprocess.run(cmd, check=True, stdout=fp)
        else:
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
