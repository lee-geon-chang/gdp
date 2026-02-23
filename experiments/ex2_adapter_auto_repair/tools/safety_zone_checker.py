"""
Safety Zone Checker - Check if processes maintain safe distance from obstacles/zones.

Input JSON format:
{
    "processes": [
        {
            "process_id": "P1",
            "name": "Assembly Station 1",
            "x": 0.0, "y": 0.0, "z": 0.0,
            "width": 2.0, "height": 3.0, "depth": 2.0
        }
    ],
    "obstacles": [
        {
            "obstacle_id": "OBS1",
            "name": "Support Pillar",
            "type": "structural",
            "x": 5.0, "y": 0.0, "z": 0.0,
            "width": 0.5, "height": 4.0, "depth": 0.5
        }
    ],
    "min_safety_distance": 1.0
}

Output JSON format:
{
    "violations": [
        {
            "process_id": "P1",
            "process_name": "Assembly Station 1",
            "obstacle_id": "OBS1",
            "obstacle_name": "Support Pillar",
            "distance": 0.5,
            "required_distance": 1.0,
            "is_violation": true
        }
    ],
    "safe_processes": ["P2", "P3"],
    "violation_count": 1,
    "all_safe": false
}

Logic:
  - For each process-obstacle pair, calculate minimum distance between
    axis-aligned bounding boxes in 3D.
  - If distance < min_safety_distance, it's a violation.
  - Report all violations and list safe processes.
"""

import argparse
import json
import math
import os
import sys


def bounding_box_distance(box_a, box_b):
    """
    Calculate the minimum distance between two axis-aligned bounding boxes.
    Each box is defined by (x, y, z, width, height, depth) where x,y,z is the
    corner with minimum coordinates.

    Returns 0.0 if boxes overlap.
    """
    # Box A extents
    a_min_x = box_a["x"]
    a_max_x = box_a["x"] + box_a["width"]
    a_min_y = box_a["y"]
    a_max_y = box_a["y"] + box_a["height"]
    a_min_z = box_a["z"]
    a_max_z = box_a["z"] + box_a["depth"]

    # Box B extents
    b_min_x = box_b["x"]
    b_max_x = box_b["x"] + box_b["width"]
    b_min_y = box_b["y"]
    b_max_y = box_b["y"] + box_b["height"]
    b_min_z = box_b["z"]
    b_max_z = box_b["z"] + box_b["depth"]

    # Gap along each axis (negative means overlap on that axis)
    gap_x = max(0.0, max(a_min_x - b_max_x, b_min_x - a_max_x))
    gap_y = max(0.0, max(a_min_y - b_max_y, b_min_y - a_max_y))
    gap_z = max(0.0, max(a_min_z - b_max_z, b_min_z - a_max_z))

    # Euclidean distance between nearest points
    return math.sqrt(gap_x ** 2 + gap_y ** 2 + gap_z ** 2)


def check_safety_zones(data):
    """Check if processes maintain safe distance from obstacles."""
    processes = data.get("processes", [])
    obstacles = data.get("obstacles", [])
    min_safety_distance = data.get("min_safety_distance", 1.0)

    if not processes:
        return {
            "violations": [],
            "safe_processes": [],
            "violation_count": 0,
            "all_safe": True,
            "warning": "No processes provided.",
        }

    if not obstacles:
        return {
            "violations": [],
            "safe_processes": [p["process_id"] for p in processes],
            "violation_count": 0,
            "all_safe": True,
            "info": "No obstacles defined. All processes are safe by default.",
        }

    violations = []
    violating_process_ids = set()

    for proc in processes:
        proc_box = {
            "x": proc.get("x", 0.0),
            "y": proc.get("y", 0.0),
            "z": proc.get("z", 0.0),
            "width": proc.get("width", 1.0),
            "height": proc.get("height", 1.0),
            "depth": proc.get("depth", 1.0),
        }

        for obs in obstacles:
            obs_box = {
                "x": obs.get("x", 0.0),
                "y": obs.get("y", 0.0),
                "z": obs.get("z", 0.0),
                "width": obs.get("width", 0.5),
                "height": obs.get("height", 0.5),
                "depth": obs.get("depth", 0.5),
            }

            distance = bounding_box_distance(proc_box, obs_box)
            is_violation = distance < min_safety_distance

            if is_violation:
                violating_process_ids.add(proc["process_id"])

            violations.append({
                "process_id": proc["process_id"],
                "process_name": proc.get("name", proc["process_id"]),
                "obstacle_id": obs["obstacle_id"],
                "obstacle_name": obs.get("name", obs["obstacle_id"]),
                "distance": round(distance, 4),
                "required_distance": min_safety_distance,
                "is_violation": is_violation,
            })

    # Only include actual violations in the violations list for clarity
    actual_violations = [v for v in violations if v["is_violation"]]
    safe_processes = sorted([
        p["process_id"] for p in processes
        if p["process_id"] not in violating_process_ids
    ])

    return {
        "violations": actual_violations,
        "safe_processes": safe_processes,
        "violation_count": len(actual_violations),
        "all_safe": len(actual_violations) == 0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Safety Zone Checker - Check if processes maintain safe distance from obstacles"
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
        result = check_safety_zones(data)
    except Exception as e:
        result = {"error": str(e), "violations": [], "safe_processes": [], "violation_count": 0, "all_safe": False}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
