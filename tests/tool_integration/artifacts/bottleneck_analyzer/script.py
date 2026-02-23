"""
Bottleneck Analyzer

Description: Analyzes a manufacturing line to identify bottleneck processes and suggests improvements.

Usage:
    python bottleneck_analyzer.py --input input.json --output output.json

Input JSON format:
    {
        "project_title": "Project Title",
        "target_uph": 60.0,
        "processes": [
            {
                "process_id": "process1",
                "parallel_count": 1,
                "predecessor_ids": [],
                "successor_ids": ["process2"],
                "parallel_lines": [
                    {
                        "parallel_index": 0,
                        "name": "Line 1",
                        "description": "",
                        "cycle_time_sec": 60.0,
                        "location": {"x": 0, "y": 0, "z": 0},
                        "rotation_y": 0.0
                    }
                ],
                "resources": []
            },
            {
                "process_id": "process2",
                "parallel_count": 1,
                "predecessor_ids": ["process1"],
                "successor_ids": [],
                "parallel_lines": [
                    {
                        "parallel_index": 0,
                        "name": "Line 2",
                        "description": "",
                        "cycle_time_sec": 30.0,
                        "location": {"x": 0, "y": 0, "z": 0},
                        "rotation_y": 0.0
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
        "cycle_times": {
            "process1": 60.0,
            "process2": 30.0
        },
        "target_takt_time": 60.0,
        "bottleneck_process": {
            "process_id": "process1",
            "cycle_time": 60.0
        },
        "improvement_suggestion": {
            "process_id": "process1",
            "required_parallel_lines": 1
        }
    }
"""

import json
import argparse
import sys
import os
import math

def process_data(data):
    """Main processing logic."""
    target_uph = data['target_uph']
    processes = data['processes']

    # Calculate target takt time
    target_takt_time = 3600.0 / target_uph  # seconds per unit

    # Calculate cycle times for each process
    cycle_times = {}
    for process in processes:
        process_id = process['process_id']
        cycle_time = 0.0
        for line in process['parallel_lines']:
            cycle_time = max(cycle_time, line['cycle_time_sec'])
        cycle_times[process_id] = cycle_time

    # Identify bottleneck process
    bottleneck_process_id = None
    max_cycle_time = 0.0
    for process_id, cycle_time in cycle_times.items():
        if cycle_time > max_cycle_time:
            max_cycle_time = cycle_time
            bottleneck_process_id = process_id

    bottleneck_process = {
        "process_id": bottleneck_process_id,
        "cycle_time": max_cycle_time
    }

    # Suggest improvement (calculate required parallel lines)
    bottleneck_process_data = next((p for p in processes if p['process_id'] == bottleneck_process_id), None)
    if bottleneck_process_data:
        required_parallel_lines = math.ceil(max_cycle_time / target_takt_time)
    else:
        required_parallel_lines = 1

    improvement_suggestion = {
        "process_id": bottleneck_process_id,
        "required_parallel_lines": int(required_parallel_lines)
    }

    result = {
        "cycle_times": cycle_times,
        "target_takt_time": target_takt_time,
        "bottleneck_process": bottleneck_process,
        "improvement_suggestion": improvement_suggestion
    }
    return result

def main():
    parser = argparse.ArgumentParser(description="Analyzes manufacturing line bottlenecks.")
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
        print(f"[Error] Invalid JSON format in input file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[Error] Failed to read input file: {e}")
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
        print(f"[Error] Failed to write output file: {e}")
        sys.exit(1)

    print(f"[Success] Results saved to {args.output}")

if __name__ == "__main__":
    main()
