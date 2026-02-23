"""
Process Distance Analyzer - Analyze distances between sequential processes.

Input JSON format:
{
    "processes": [
        {"process_id": "P001", "predecessor_ids": [], "successor_ids": ["P002"]},
        {"process_id": "P002", "predecessor_ids": ["P001"], "successor_ids": ["P003"]},
        {"process_id": "P003", "predecessor_ids": ["P002"], "successor_ids": []}
    ],
    "process_locations": [
        {"process_id": "P001", "x": 0.0, "y": 0.0, "z": 0.0, "name": "Station 1"},
        {"process_id": "P002", "x": 5.0, "y": 3.0, "z": 0.0, "name": "Station 2"},
        {"process_id": "P003", "x": 12.0, "y": 1.0, "z": 0.0, "name": "Station 3"}
    ]
}

Output JSON format:
{
    "distances": [...],
    "total_flow_distance_m": 15.2,
    "avg_distance_m": 7.6,
    "max_distance_pair": {...},
    "min_distance_pair": {...},
    "distance_std_dev": 2.1,
    "suggestions": [...]
}

Logic:
  - For each process, calculate Euclidean distance to each of its successors.
  - Total flow distance = sum of all sequential distances.
  - Identify maximum distance pair as potential optimization target.
"""

import argparse
import json
import math
import os
import sys
import statistics


def analyze_process_distances(data):
    """Analyze distances between sequential processes."""
    processes = data.get("processes", [])
    process_locations = data.get("process_locations", [])

    if not processes:
        return {
            "error": "No processes provided.",
            "suggestions": ["Provide processes array with predecessor/successor info."],
        }
    if not process_locations:
        return {
            "error": "No process_locations provided.",
            "suggestions": ["Provide process_locations array with x, y, z coordinates."],
        }

    # Build location lookup
    loc_lookup = {}
    name_lookup = {}
    for loc in process_locations:
        pid = loc["process_id"]
        loc_lookup[pid] = {
            "x": loc.get("x", 0.0),
            "y": loc.get("y", 0.0),
            "z": loc.get("z", 0.0),
        }
        name_lookup[pid] = loc.get("name", pid)

    # Also get names from processes if not in locations
    for proc in processes:
        pid = proc["process_id"]
        if pid not in name_lookup:
            name_lookup[pid] = proc.get("name", pid)

    # Calculate distances for each predecessor->successor pair
    distances = []
    for proc in processes:
        from_id = proc["process_id"]
        successor_ids = proc.get("successor_ids", [])

        if from_id not in loc_lookup:
            continue

        from_loc = loc_lookup[from_id]
        from_name = name_lookup.get(from_id, from_id)

        for to_id in successor_ids:
            if to_id not in loc_lookup:
                continue

            to_loc = loc_lookup[to_id]
            to_name = name_lookup.get(to_id, to_id)

            dx = to_loc["x"] - from_loc["x"]
            dy = to_loc["y"] - from_loc["y"]
            dz = to_loc["z"] - from_loc["z"]
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)

            distances.append({
                "from_id": from_id,
                "to_id": to_id,
                "from_name": from_name,
                "to_name": to_name,
                "distance_m": round(distance, 4),
                "dx": round(dx, 4),
                "dy": round(dy, 4),
                "dz": round(dz, 4),
            })

    if not distances:
        return {
            "distances": [],
            "total_flow_distance_m": 0.0,
            "avg_distance_m": 0.0,
            "max_distance_pair": None,
            "min_distance_pair": None,
            "suggestions": ["No valid process pairs with locations found."],
        }

    distance_values = [d["distance_m"] for d in distances]
    total_flow_distance = sum(distance_values)
    avg_distance = total_flow_distance / len(distance_values)

    # Sort by distance descending
    distances_sorted = sorted(distances, key=lambda x: x["distance_m"], reverse=True)
    max_pair = distances_sorted[0]
    min_pair = distances_sorted[-1]

    distance_std_dev = 0.0
    if len(distance_values) >= 2:
        distance_std_dev = statistics.stdev(distance_values)

    # Suggestions
    suggestions = []
    if max_pair["distance_m"] > avg_distance * 2.0 and len(distance_values) > 1:
        suggestions.append(
            f"Process pair '{max_pair['from_name']}' -> '{max_pair['to_name']}' "
            f"has the longest distance ({max_pair['distance_m']}m), "
            f"which is significantly above average ({round(avg_distance, 2)}m). "
            f"Consider relocating these stations closer together."
        )

    if distance_std_dev > avg_distance * 0.5 and len(distance_values) > 1:
        suggestions.append(
            f"High variability in distances (std dev: {round(distance_std_dev, 2)}m). "
            f"Consider rearranging the layout for more uniform spacing."
        )

    if total_flow_distance > 50:
        suggestions.append(
            f"Total flow distance is {round(total_flow_distance, 2)}m. "
            f"Consider a U-shaped or cellular layout to reduce material travel distance."
        )

    if not suggestions:
        suggestions.append(
            f"Layout appears reasonable. Total flow distance: {round(total_flow_distance, 2)}m, "
            f"average: {round(avg_distance, 2)}m."
        )

    return {
        "distances": distances_sorted,
        "total_flow_distance_m": round(total_flow_distance, 4),
        "avg_distance_m": round(avg_distance, 4),
        "max_distance_pair": {
            "from_id": max_pair["from_id"],
            "to_id": max_pair["to_id"],
            "from_name": max_pair["from_name"],
            "to_name": max_pair["to_name"],
            "distance_m": max_pair["distance_m"],
        },
        "min_distance_pair": {
            "from_id": min_pair["from_id"],
            "to_id": min_pair["to_id"],
            "from_name": min_pair["from_name"],
            "to_name": min_pair["to_name"],
            "distance_m": min_pair["distance_m"],
        },
        "distance_std_dev_m": round(distance_std_dev, 4),
        "num_pairs": len(distances),
        "suggestions": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="Process Distance Analyzer - Analyze distances between sequential processes")
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
        result = analyze_process_distances(data)
    except Exception as e:
        result = {"error": str(e), "suggestions": ["Check input data format."]}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
