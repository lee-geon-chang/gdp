"""
Takt Time Optimizer - Optimize parallel counts to meet target UPH.

Input JSON format:
{
    "process_graph": {
        "nodes": [
            {
                "process_id": "P1",
                "name": "Assembly",
                "cycle_time_sec": 120.0,
                "current_parallel_count": 1
            }
        ],
        "edges": [
            {"from_id": "P1", "to_id": "P2"}
        ]
    },
    "target_uph": 60,
    "max_parallel_per_process": 4,
    "optimization_mode": "minimize_total"
}

Output JSON format:
{
    "optimized_processes": [
        {
            "process_id": "P1",
            "name": "Assembly",
            "original_parallel": 1,
            "recommended_parallel": 2,
            "original_effective_time": 120.0,
            "new_effective_time": 60.0
        }
    ],
    "achieved_uph": 60.0,
    "target_uph": 60,
    "improvement_pct": 100.0,
    "total_parallel_added": 3,
    "bottleneck_after": "P2"
}

Logic:
  - takt_time = 3600 / target_uph
  - For each process: needed_parallel = ceil(cycle_time / takt_time)
  - In "minimize_total" mode: use minimum needed parallels
  - In "balance" mode: try to equalize utilization across processes
  - Cap at max_parallel_per_process
"""

import argparse
import json
import math
import os
import sys


def optimize_takt_time(data):
    """Optimize parallel counts to meet target UPH."""
    process_graph = data.get("process_graph", {})
    nodes = process_graph.get("nodes", [])
    edges = process_graph.get("edges", [])
    target_uph = data.get("target_uph", 60)
    max_parallel = data.get("max_parallel_per_process", 4)
    mode = data.get("optimization_mode", "minimize_total")

    if not nodes:
        return {
            "error": "No process nodes provided.",
            "optimized_processes": [],
            "achieved_uph": 0,
            "target_uph": target_uph,
            "improvement_pct": 0,
            "total_parallel_added": 0,
        }

    if target_uph <= 0:
        return {
            "error": "target_uph must be positive.",
            "optimized_processes": [],
            "achieved_uph": 0,
            "target_uph": target_uph,
            "improvement_pct": 0,
            "total_parallel_added": 0,
        }

    takt_time = 3600.0 / target_uph

    # Calculate original max UPH (before optimization)
    original_effective_times = []
    for node in nodes:
        ct = node.get("cycle_time_sec", 0)
        pc = node.get("current_parallel_count", 1)
        if pc <= 0:
            pc = 1
        eff = ct / pc
        original_effective_times.append(eff)

    original_bottleneck_eff = max(original_effective_times) if original_effective_times else 0
    original_uph = 3600.0 / original_bottleneck_eff if original_bottleneck_eff > 0 else float("inf")

    optimized_processes = []
    total_parallel_added = 0

    if mode == "minimize_total":
        # For each process, compute minimum parallels needed to meet takt time
        for node in nodes:
            ct = node.get("cycle_time_sec", 0)
            current_pc = node.get("current_parallel_count", 1)
            if current_pc <= 0:
                current_pc = 1

            if ct <= 0:
                needed = current_pc
            else:
                needed = math.ceil(ct / takt_time)

            # Don't reduce below current count, and cap at max
            recommended = max(needed, 1)
            recommended = min(recommended, max_parallel)

            original_eff = ct / current_pc if current_pc > 0 else ct
            new_eff = ct / recommended if recommended > 0 else ct

            added = max(0, recommended - current_pc)
            total_parallel_added += added

            optimized_processes.append({
                "process_id": node["process_id"],
                "name": node.get("name", node["process_id"]),
                "original_parallel": current_pc,
                "recommended_parallel": recommended,
                "original_effective_time": round(original_eff, 4),
                "new_effective_time": round(new_eff, 4),
            })

    elif mode == "balance":
        # Balance mode: try to equalize utilization
        # First, compute minimum needed for each
        process_info = []
        for node in nodes:
            ct = node.get("cycle_time_sec", 0)
            current_pc = node.get("current_parallel_count", 1)
            if current_pc <= 0:
                current_pc = 1

            if ct <= 0:
                needed = 1
            else:
                needed = math.ceil(ct / takt_time)
            needed = min(needed, max_parallel)
            process_info.append({
                "node": node,
                "cycle_time": ct,
                "current_pc": current_pc,
                "needed": max(needed, 1),
            })

        # Calculate total "budget" of extra parallels we could add
        # In balance mode: after meeting minimum, distribute extra parallels
        # to balance utilization (effective_time / takt_time ratio)
        for info in process_info:
            info["recommended"] = info["needed"]

        # Iteratively add parallels to the most utilized process
        max_iterations = len(process_info) * max_parallel
        for _ in range(max_iterations):
            # Find the process with highest utilization
            utilizations = []
            for info in process_info:
                eff_time = info["cycle_time"] / info["recommended"] if info["recommended"] > 0 else info["cycle_time"]
                util = eff_time / takt_time if takt_time > 0 else 0
                utilizations.append((util, info))

            utilizations.sort(key=lambda x: x[0], reverse=True)
            highest_util, highest_info = utilizations[0]

            # If highest utilization is already <= 1.0 and all are close, stop
            if highest_util <= 1.0:
                # Check if we can balance further
                if len(utilizations) > 1:
                    lowest_util = utilizations[-1][0]
                    if highest_util - lowest_util < 0.05:
                        break
                else:
                    break

            # Try to add a parallel to the highest utilization process
            if highest_info["recommended"] < max_parallel:
                highest_info["recommended"] += 1
            else:
                # Can't add more, check if all are at limit or feasible
                break

        for info in process_info:
            node = info["node"]
            ct = info["cycle_time"]
            current_pc = info["current_pc"]
            recommended = info["recommended"]

            original_eff = ct / current_pc if current_pc > 0 else ct
            new_eff = ct / recommended if recommended > 0 else ct

            added = max(0, recommended - current_pc)
            total_parallel_added += added

            optimized_processes.append({
                "process_id": node["process_id"],
                "name": node.get("name", node["process_id"]),
                "original_parallel": current_pc,
                "recommended_parallel": recommended,
                "original_effective_time": round(original_eff, 4),
                "new_effective_time": round(new_eff, 4),
            })
    else:
        return {
            "error": f"Unknown optimization_mode: {mode}. Use 'minimize_total' or 'balance'.",
            "optimized_processes": [],
            "achieved_uph": 0,
            "target_uph": target_uph,
            "improvement_pct": 0,
            "total_parallel_added": 0,
        }

    # Calculate achieved UPH after optimization
    new_effective_times = [p["new_effective_time"] for p in optimized_processes]
    new_bottleneck_eff = max(new_effective_times) if new_effective_times else 0
    achieved_uph = 3600.0 / new_bottleneck_eff if new_bottleneck_eff > 0 else float("inf")

    # Find the new bottleneck process
    bottleneck_after = None
    for p in optimized_processes:
        if p["new_effective_time"] == new_bottleneck_eff:
            bottleneck_after = p["process_id"]
            break

    # Improvement percentage
    if original_uph > 0 and original_uph != float("inf"):
        improvement_pct = ((achieved_uph - original_uph) / original_uph) * 100.0
    else:
        improvement_pct = 0.0

    return {
        "optimized_processes": optimized_processes,
        "achieved_uph": round(achieved_uph, 2),
        "target_uph": target_uph,
        "improvement_pct": round(improvement_pct, 2),
        "total_parallel_added": total_parallel_added,
        "bottleneck_after": bottleneck_after,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Takt Time Optimizer - Optimize parallel counts to meet target UPH"
    )
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = optimize_takt_time(data)
    except Exception as e:
        result = {"error": str(e), "optimized_processes": [], "achieved_uph": 0, "total_parallel_added": 0}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Optimization complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
