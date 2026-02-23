"""
Bottleneck Analyzer - Identify bottleneck process in a manufacturing line.

Input JSON format:
{
    "process_details": [
        {"process_id": "P1", "parallel_index": 0, "cycle_time_sec": 45.0, "name": "Assembly Step 1"},
        {"process_id": "P1", "parallel_index": 1, "cycle_time_sec": 46.0, "name": "Assembly Step 1"},
        {"process_id": "P2", "parallel_index": 0, "cycle_time_sec": 60.0, "name": "Welding"}
    ],
    "target_uph": 50
}

Output JSON format:
{
    "bottleneck_process_id": "P2",
    "bottleneck_process_name": "Welding",
    "bottleneck_cycle_time": 60.0,
    "effective_cycle_time": 60.0,
    "current_max_uph": 60.0,
    "target_uph": 50,
    "gap_uph": 10.0,
    "is_target_achievable": true,
    "process_summary": [...],
    "suggestions": [...]
}

Logic:
  - Group process_details by process_id.
  - For each process_id, parallel_count = number of entries.
  - effective_cycle_time = max(cycle_time_sec across parallels) / parallel_count.
  - Bottleneck = process with the highest effective_cycle_time.
  - current_max_uph = 3600 / bottleneck_effective_cycle_time.
"""

import argparse
import json
import os
import sys


def analyze_bottleneck(data):
    """Identify the bottleneck process in a manufacturing line."""
    process_details = data.get("process_details", [])
    target_uph = data.get("target_uph", 60)

    if not process_details:
        return {
            "error": "No process_details provided.",
            "bottleneck_process_id": None,
            "suggestions": ["Provide process_details array with at least one process."],
        }

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

    # Calculate effective cycle time for each process
    process_summary = []
    for pid, info in process_groups.items():
        parallel_count = len(info["cycle_times"])
        max_cycle_time = max(info["cycle_times"])
        effective_cycle_time = max_cycle_time / parallel_count
        process_summary.append(
            {
                "process_id": pid,
                "name": info["name"],
                "parallel_count": parallel_count,
                "max_cycle_time_sec": round(max_cycle_time, 4),
                "effective_cycle_time_sec": round(effective_cycle_time, 4),
            }
        )

    # Sort by effective_cycle_time descending to find bottleneck
    process_summary.sort(key=lambda x: x["effective_cycle_time_sec"], reverse=True)
    bottleneck = process_summary[0]

    current_max_uph = 3600.0 / bottleneck["effective_cycle_time_sec"] if bottleneck["effective_cycle_time_sec"] > 0 else float("inf")
    gap_uph = current_max_uph - target_uph
    is_target_achievable = current_max_uph >= target_uph

    # Generate suggestions
    suggestions = []
    if not is_target_achievable:
        required_cycle = 3600.0 / target_uph
        suggestions.append(
            f"Bottleneck process '{bottleneck['name']}' (effective {bottleneck['effective_cycle_time_sec']}s) "
            f"exceeds required takt time ({round(required_cycle, 2)}s). "
            f"Consider adding parallel stations or reducing cycle time."
        )
        # How many parallels needed
        needed_parallel = -(-int(bottleneck["max_cycle_time_sec"] / required_cycle))  # ceil division
        if needed_parallel > bottleneck["parallel_count"]:
            suggestions.append(
                f"Increasing parallel count of '{bottleneck['name']}' from "
                f"{bottleneck['parallel_count']} to {needed_parallel} would resolve the bottleneck."
            )
    else:
        suggestions.append(
            f"Target UPH ({target_uph}) is achievable. Current max UPH is {round(current_max_uph, 2)}."
        )
        # Check if there are processes close to bottleneck
        if len(process_summary) > 1:
            second = process_summary[1]
            ratio = second["effective_cycle_time_sec"] / bottleneck["effective_cycle_time_sec"]
            if ratio > 0.9:
                suggestions.append(
                    f"Process '{second['name']}' is close to bottleneck "
                    f"({round(ratio * 100, 1)}% of bottleneck cycle time). Monitor closely."
                )

    return {
        "bottleneck_process_id": bottleneck["process_id"],
        "bottleneck_process_name": bottleneck["name"],
        "bottleneck_cycle_time_sec": bottleneck["max_cycle_time_sec"],
        "effective_cycle_time_sec": bottleneck["effective_cycle_time_sec"],
        "current_max_uph": round(current_max_uph, 2),
        "target_uph": target_uph,
        "gap_uph": round(gap_uph, 2),
        "is_target_achievable": is_target_achievable,
        "process_summary": process_summary,
        "suggestions": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="Bottleneck Analyzer - Identify bottleneck process in a manufacturing line")
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
        result = analyze_bottleneck(data)
    except Exception as e:
        result = {"error": str(e), "suggestions": ["Check input data format."]}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
