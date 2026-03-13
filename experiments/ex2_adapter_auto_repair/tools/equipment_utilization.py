"""
Equipment Utilization Analyzer - Calculate equipment utilization rates.

Input JSON format:
{
    "equipments": [
        {"equipment_id": "EQ001", "name": "Robot Arm A", "type": "robot"},
        {"equipment_id": "EQ002", "name": "Welding Gun B", "type": "welding_tool"}
    ],
    "assignments": [
        {"process_id": "P001", "parallel_index": 0, "resource_type": "equipment", "resource_id": "EQ001", "role": "main"},
        {"process_id": "P002", "parallel_index": 0, "resource_type": "equipment", "resource_id": "EQ002", "role": "main"}
    ],
    "process_times": [
        {"process_id": "P001", "parallel_index": 0, "cycle_time_sec": 45.0},
        {"process_id": "P002", "parallel_index": 0, "cycle_time_sec": 60.0}
    ],
    "target_uph": 50
}

Output JSON format:
{
    "takt_time_sec": 72.0,
    "equipment_utilization": [...],
    "overall_utilization_pct": 72.9,
    "underutilized": [...],
    "overloaded": [...],
    "unassigned_equipment": [...],
    "suggestions": [...]
}

Logic:
  - takt_time = 3600 / target_uph
  - For each equipment, find its assignment(s), then look up cycle_time from process_times.
  - utilization = cycle_time / takt_time * 100
  - Underutilized: utilization < 50%. Overloaded: utilization > 100%.
"""

import argparse
import json
import os
import sys


def analyze_equipment_utilization(data):
    """Calculate equipment utilization rates."""
    equipments = data.get("equipments", [])
    assignments = data.get("assignments", [])
    process_times = data.get("process_times", [])
    target_uph = data.get("target_uph", 60)

    if not equipments:
        return {
            "error": "No equipments provided.",
            "suggestions": ["Provide equipments array with at least one equipment."],
        }

    if target_uph <= 0:
        return {
            "error": "target_uph must be positive.",
            "suggestions": ["Provide a positive target_uph value."],
        }

    takt_time = 3600.0 / target_uph

    # Build lookup: (process_id, parallel_index) -> cycle_time_sec
    pt_lookup = {}
    for pt in process_times:
        key = (pt["process_id"], pt.get("parallel_index", 0))
        pt_lookup[key] = pt.get("cycle_time_sec", 0.0)

    # Build lookup: resource_id -> list of assignments
    assignment_lookup = {}
    for asgn in assignments:
        rid = asgn.get("resource_id")
        if rid:
            if rid not in assignment_lookup:
                assignment_lookup[rid] = []
            assignment_lookup[rid].append(asgn)

    equipment_utilization = []
    underutilized = []
    overloaded = []
    unassigned = []
    utilization_values = []

    for eq in equipments:
        eid = eq["equipment_id"]
        eq_name = eq.get("name", eid)
        eq_type = eq.get("type", "unknown")

        eq_assignments = assignment_lookup.get(eid, [])

        if not eq_assignments:
            unassigned.append({
                "equipment_id": eid,
                "name": eq_name,
                "type": eq_type,
            })
            equipment_utilization.append({
                "equipment_id": eid,
                "name": eq_name,
                "type": eq_type,
                "assigned_process_id": None,
                "cycle_time_sec": 0.0,
                "utilization_pct": 0.0,
                "status": "unassigned",
            })
            utilization_values.append(0.0)
            continue

        # An equipment could be assigned to multiple processes (shared resource).
        # Sum cycle times across all assignments for total busy time per unit.
        total_cycle_time = 0.0
        assigned_pids = []
        for asgn in eq_assignments:
            pid = asgn["process_id"]
            pidx = asgn.get("parallel_index", 0)
            ct = pt_lookup.get((pid, pidx), 0.0)
            total_cycle_time += ct
            assigned_pids.append(pid)

        utilization_pct = (total_cycle_time / takt_time * 100.0) if takt_time > 0 else 0.0

        if utilization_pct > 100:
            status = "overloaded"
        elif utilization_pct < 50:
            status = "underutilized"
        else:
            status = "normal"

        entry = {
            "equipment_id": eid,
            "name": eq_name,
            "type": eq_type,
            "assigned_process_id": assigned_pids[0] if len(assigned_pids) == 1 else assigned_pids,
            "cycle_time_sec": round(total_cycle_time, 4),
            "utilization_pct": round(utilization_pct, 2),
            "status": status,
        }
        equipment_utilization.append(entry)
        utilization_values.append(utilization_pct)

        if status == "underutilized":
            underutilized.append({
                "equipment_id": eid,
                "name": eq_name,
                "utilization_pct": round(utilization_pct, 2),
            })
        elif status == "overloaded":
            overloaded.append({
                "equipment_id": eid,
                "name": eq_name,
                "utilization_pct": round(utilization_pct, 2),
            })

    overall_utilization = sum(utilization_values) / len(utilization_values) if utilization_values else 0.0

    # Sort by utilization descending
    equipment_utilization.sort(key=lambda x: x["utilization_pct"], reverse=True)

    # Suggestions
    suggestions = []
    if overloaded:
        names = ", ".join(o["name"] for o in overloaded)
        suggestions.append(
            f"Overloaded equipment detected: {names}. "
            f"Consider adding parallel equipment or redistributing work."
        )
    if underutilized:
        names = ", ".join(u["name"] for u in underutilized)
        suggestions.append(
            f"Underutilized equipment: {names}. "
            f"Consider consolidating tasks or sharing equipment between processes."
        )
    if unassigned:
        names = ", ".join(u["name"] for u in unassigned)
        suggestions.append(
            f"Unassigned equipment: {names}. "
            f"These may be spare/backup or should be assigned to processes."
        )
    if overall_utilization < 60:
        suggestions.append(
            f"Overall utilization is low ({round(overall_utilization, 1)}%). "
            f"The line may have excess equipment capacity."
        )
    elif overall_utilization > 90:
        suggestions.append(
            f"Overall utilization is very high ({round(overall_utilization, 1)}%). "
            f"Limited slack for maintenance or unexpected demand spikes."
        )

    return {
        "takt_time_sec": round(takt_time, 4),
        "target_uph": target_uph,
        "equipment_utilization": equipment_utilization,
        "overall_utilization_pct": round(overall_utilization, 2),
        "underutilized": underutilized,
        "overloaded": overloaded,
        "unassigned_equipment": unassigned,
        "suggestions": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="Equipment Utilization Analyzer")
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
        result = analyze_equipment_utilization(data)
    except Exception as e:
        result = {"error": str(e), "suggestions": ["Check input data format."]}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
