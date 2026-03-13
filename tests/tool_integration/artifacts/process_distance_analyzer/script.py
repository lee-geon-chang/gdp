import json
import argparse
import sys
import os
import math


def calculate_distance(loc1, loc2):
    """Calculates Euclidean distance between two 3D points."""
    return math.sqrt((loc1['x'] - loc2['x'])**2 + (loc1['y'] - loc2['y'])**2 + (loc1['z'] - loc2['z'])**2)


def process_data(data):
    """Calculates process distances, total distance, and identifies the longest segment.

    Input JSON format:
    {
        "project_title": "string",
        "target_uph": float,
        "processes": [
            {
                "process_id": "string",
                "parallel_count": int,
                "predecessor_ids": ["string"],
                "successor_ids": ["string"],
                "parallel_lines": [
                    {
                        "parallel_index": int,
                        "name": "string",
                        "description": "string",
                        "cycle_time_sec": float,
                        "location": {"x": float, "y": float, "z": float},
                        "rotation_y": float
                    }
                ],
                "resources": []
            }
        ],
        "equipments": [],
        "workers": [],
        "materials": [],
        "obstacles": []
    }

    Output JSON format:
    {
        "process_distances": {
            "process_id1 -> process_id2": float,
            "process_id3 -> process_id4": float,
            ...
        },
        "total_distance": float,
        "max_distance_segment": {
            "process_id1": "string",
            "process_id2": "string",
            "distance": float
        }
    }
    """

    process_distances = {}
    total_distance = 0.0
    max_distance = 0.0
    max_distance_segment = {"process_id1": None, "process_id2": None, "distance": 0.0}

    process_map = {process['process_id']: process for process in data['processes']}

    for process in data['processes']:
        process_id = process['process_id']
        for successor_id in process['successor_ids']:
            if successor_id in process_map:
                successor = process_map[successor_id]

                # Assuming first parallel line for distance calculation
                if process['parallel_lines'] and successor['parallel_lines']:
                    location1 = process['parallel_lines'][0]['location']
                    location2 = successor['parallel_lines'][0]['location']

                    distance = calculate_distance(location1, location2)
                    process_distances[f'{process_id} -> {successor_id}'] = distance
                    total_distance += distance

                    if distance > max_distance:
                        max_distance = distance
                        max_distance_segment = {"process_id1": process_id, "process_id2": successor_id, "distance": distance}
                else:
                    print(f"[Warning] No parallel lines found for process {process_id} or {successor_id}")

            else:
                print(f"[Warning] Successor process {successor_id} not found.")

    result = {
        "process_distances": process_distances,
        "total_distance": total_distance,
        "max_distance_segment": max_distance_segment
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Analyzes process distances in a manufacturing layout.")
    parser.add_argument('--input', '-i', type=str, required=True, help='Input JSON file path')
    parser.add_argument('--output', '-o', type=str, required=True, help='Output JSON file path')
    args = parser.parse_args()

    # Read input
    if not os.path.exists(args.input):
        print(f"[Error] Input file not found: {args.input}")
        sys.exit(1)

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[Error] Invalid JSON format in {args.input}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[Error] Could not read input file {args.input}: {e}")
        sys.exit(1)

    # Process
    try:
        result = process_data(input_data)
    except Exception as e:
        print(f"[Error] Processing failed: {e}")
        sys.exit(1)

    # Write output
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Error] Could not write to output file {args.output}: {e}")
        sys.exit(1)

    print(f"[Success] Results saved to {args.output}")


if __name__ == "__main__":
    main()
