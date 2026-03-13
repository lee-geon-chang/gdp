"""
Material Flow Analyzer - Analyze material flow through the manufacturing line.

Input JSON format:
{
    "processes": [
        {
            "process_id": "P1",
            "name": "Assembly",
            "predecessor_ids": [],
            "successor_ids": ["P2"]
        },
        {
            "process_id": "P2",
            "name": "Welding",
            "predecessor_ids": ["P1"],
            "successor_ids": ["P3"]
        }
    ],
    "material_assignments": [
        {
            "process_id": "P1",
            "material_id": "MAT001",
            "material_name": "Steel Plate",
            "quantity": 2.0,
            "unit": "kg"
        }
    ]
}

Output JSON format:
{
    "material_flows": [
        {
            "material_id": "MAT001",
            "name": "Steel Plate",
            "unit": "kg",
            "used_in_processes": ["P1", "P2"],
            "total_quantity": 5.0
        }
    ],
    "flow_paths": [
        {
            "from_process": "P1",
            "to_process": "P2",
            "materials_transferred": ["MAT001"]
        }
    ],
    "summary": {
        "total_materials": 3,
        "total_quantity_by_unit": {"kg": 10.0, "pcs": 5}
    }
}

Logic:
  - For each material, find which processes use it.
  - For each process->successor edge, identify materials that flow between them
    (materials used in both the source and any downstream process).
  - Aggregate total quantities by material and by unit.
"""

import argparse
import json
import os
import sys


def analyze_material_flow(data):
    """Analyze material flow through the manufacturing line."""
    processes = data.get("processes", [])
    material_assignments = data.get("material_assignments", [])

    if not processes:
        return {
            "error": "No processes provided.",
            "material_flows": [],
            "flow_paths": [],
            "summary": {"total_materials": 0, "total_quantity_by_unit": {}},
        }

    if not material_assignments:
        return {
            "material_flows": [],
            "flow_paths": [],
            "summary": {"total_materials": 0, "total_quantity_by_unit": {}},
        }

    # Build process lookup
    process_map = {}
    for proc in processes:
        pid = proc["process_id"]
        process_map[pid] = proc

    # Group material assignments by material_id
    material_info = {}
    for ma in material_assignments:
        mid = ma["material_id"]
        if mid not in material_info:
            material_info[mid] = {
                "material_id": mid,
                "name": ma.get("material_name", mid),
                "unit": ma.get("unit", "unknown"),
                "used_in_processes": [],
                "total_quantity": 0.0,
            }
        pid = ma["process_id"]
        if pid not in material_info[mid]["used_in_processes"]:
            material_info[mid]["used_in_processes"].append(pid)
        material_info[mid]["total_quantity"] += ma.get("quantity", 0.0)

    # Build set of materials per process
    process_materials = {}
    for ma in material_assignments:
        pid = ma["process_id"]
        mid = ma["material_id"]
        if pid not in process_materials:
            process_materials[pid] = set()
        process_materials[pid].add(mid)

    # Build set of all materials used downstream from each process
    # For flow path detection: materials that are used in both source process
    # and any process reachable from the successor
    def get_all_downstream_materials(pid, visited=None):
        """Get all materials used in pid and all downstream processes."""
        if visited is None:
            visited = set()
        if pid in visited:
            return set()
        visited.add(pid)
        result = set(process_materials.get(pid, set()))
        proc = process_map.get(pid, {})
        for succ_id in proc.get("successor_ids", []):
            result |= get_all_downstream_materials(succ_id, visited)
        return result

    # For each process->successor edge, find materials that flow
    flow_paths = []
    for proc in processes:
        pid = proc["process_id"]
        source_materials = process_materials.get(pid, set())
        for succ_id in proc.get("successor_ids", []):
            # Materials transferred: materials used in source that are also
            # used in the successor or any of its downstream processes
            downstream_mats = get_all_downstream_materials(succ_id)
            transferred = sorted(source_materials & downstream_mats)
            flow_paths.append({
                "from_process": pid,
                "to_process": succ_id,
                "materials_transferred": transferred,
            })

    # Build material_flows list
    material_flows = []
    for mid, info in sorted(material_info.items(), key=lambda x: x[0]):
        material_flows.append({
            "material_id": info["material_id"],
            "name": info["name"],
            "unit": info["unit"],
            "used_in_processes": sorted(info["used_in_processes"]),
            "total_quantity": round(info["total_quantity"], 4),
        })

    # Summary
    total_quantity_by_unit = {}
    for info in material_info.values():
        unit = info["unit"]
        total_quantity_by_unit[unit] = round(
            total_quantity_by_unit.get(unit, 0.0) + info["total_quantity"], 4
        )

    return {
        "material_flows": material_flows,
        "flow_paths": flow_paths,
        "summary": {
            "total_materials": len(material_info),
            "total_quantity_by_unit": total_quantity_by_unit,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Material Flow Analyzer - Analyze material flow through the manufacturing line"
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
        result = analyze_material_flow(data)
    except Exception as e:
        result = {"error": str(e), "material_flows": [], "flow_paths": [], "summary": {}}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
