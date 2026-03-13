"""
Line Balance Calculator - Calculate line balance efficiency for a manufacturing line.

Input JSON format:
{
    "process_details": [
        {"process_id": "P1", "parallel_index": 0, "cycle_time_sec": 45.0, "name": "Step 1"},
        {"process_id": "P1", "parallel_index": 1, "cycle_time_sec": 46.0, "name": "Step 1"},
        {"process_id": "P2", "parallel_index": 0, "cycle_time_sec": 60.0, "name": "Step 2"}
    ],
    "target_uph": 50
}

Output JSON format:
{
    "line_balance_rate": 85.5,
    "takt_time_sec": 72.0,
    "process_times": [...],
    "total_idle_time_sec": 30.0,
    "total_effective_time_sec": 120.0,
    "num_processes": 3,
    "suggestions": [...]
}

Logic:
  - takt_time = 3600 / target_uph
  - Group by process_id to find parallel_count per process.
  - effective_time = max(cycle_time) / parallel_count for each process.
  - utilization = effective_time / takt_time * 100
  - line_balance_rate = sum(effective_times) / (num_processes * max(effective_times)) * 100
"""

import argparse
import json
import os
import sys


def calculate_line_balance(data):
    """Calculate line balance efficiency."""
    process_details = data.get("process_details", [])
    target_uph = data.get("target_uph", 60)

    if not process_details:
        return {
            "error": "No process_details provided.",
            "line_balance_rate": 0.0,
            "suggestions": ["Provide process_details with at least one process."],
        }

    if target_uph <= 0:
        return {
            "error": "target_uph must be positive.",
            "line_balance_rate": 0.0,
            "suggestions": ["Provide a positive target_uph value."],
        }

    takt_time = 3600.0 / target_uph

    # Group by process_id
    process_groups = {}
    for pd in process_details:
        pid = pd["process_id"]
        if pid not in process_groups:
            process_groups[pid] = {
                "process_id": pid,
                "name": pd.get("name", pid),
                "cycle_times": [],
            }
        process_groups[pid]["cycle_times"].append(pd.get("cycle_time_sec", 0.0))

    # Calculate effective cycle time and utilization for each process
    process_times = []
    effective_times = []
    for pid, info in process_groups.items():
        parallel_count = len(info["cycle_times"])
        max_cycle_time = max(info["cycle_times"])
        effective_cycle_time = max_cycle_time / parallel_count
        utilization = (effective_cycle_time / takt_time * 100.0) if takt_time > 0 else 0.0
        idle_time = max(0.0, takt_time - effective_cycle_time)

        effective_times.append(effective_cycle_time)
        process_times.append(
            {
                "process_id": pid,
                "name": info["name"],
                "parallel_count": parallel_count,
                "max_cycle_time_sec": round(max_cycle_time, 4),
                "effective_cycle_time_sec": round(effective_cycle_time, 4),
                "utilization_pct": round(utilization, 2),
                "idle_time_sec": round(idle_time, 4),
            }
        )

    # Sort by effective_cycle_time descending
    process_times.sort(key=lambda x: x["effective_cycle_time_sec"], reverse=True)

    num_processes = len(process_groups)
    max_effective_time = max(effective_times) if effective_times else 0
    sum_effective_times = sum(effective_times)
    total_idle_time = sum(pt["idle_time_sec"] for pt in process_times)

    # Line balance rate
    if num_processes > 0 and max_effective_time > 0:
        line_balance_rate = (sum_effective_times / (num_processes * max_effective_time)) * 100.0
    else:
        line_balance_rate = 0.0

    # Suggestions
    suggestions = []
    if line_balance_rate < 70:
        suggestions.append(
            f"Line balance rate is low ({round(line_balance_rate, 1)}%). "
            f"Consider redistributing work between processes."
        )
    elif line_balance_rate < 85:
        suggestions.append(
            f"Line balance rate is moderate ({round(line_balance_rate, 1)}%). "
            f"There is room for improvement."
        )
    else:
        suggestions.append(
            f"Line balance rate is good ({round(line_balance_rate, 1)}%)."
        )

    # Find processes with low utilization
    for pt in process_times:
        if pt["utilization_pct"] < 50:
            suggestions.append(
                f"Process '{pt['name']}' has low utilization ({pt['utilization_pct']}%). "
                f"Consider merging with adjacent process or adding work content."
            )
    # Find processes exceeding takt
    for pt in process_times:
        if pt["utilization_pct"] > 100:
            suggestions.append(
                f"Process '{pt['name']}' exceeds takt time ({pt['utilization_pct']}% utilization). "
                f"This is a bottleneck - consider adding parallel stations."
            )

    return {
        "line_balance_rate": round(line_balance_rate, 2),
        "takt_time_sec": round(takt_time, 4),
        "process_times": process_times,
        "total_effective_time_sec": round(sum_effective_times, 4),
        "total_idle_time_sec": round(total_idle_time, 4),
        "num_processes": num_processes,
        "target_uph": target_uph,
        "suggestions": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="Line Balance Calculator - Calculate line balance efficiency")
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
        result = calculate_line_balance(data)
    except Exception as e:
        result = {"error": str(e), "suggestions": ["Check input data format."]}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
