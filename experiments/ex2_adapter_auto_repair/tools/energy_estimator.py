"""
Energy Estimator - Estimate energy consumption per process based on equipment type.

Input JSON format:
{
    "processes": [
        {
            "process_id": "P1",
            "name": "Welding",
            "cycle_time_sec": 60.0,
            "parallel_count": 2
        }
    ],
    "equipment_assignments": [
        {
            "process_id": "P1",
            "equipment_id": "EQ001",
            "equipment_name": "Welding Robot",
            "equipment_type": "robot"
        }
    ],
    "energy_rates": {
        "robot": 5.0,
        "machine": 8.0,
        "conveyor": 2.0,
        "manual_station": 0.5,
        "agv": 1.5
    },
    "production_volume": 1000,
    "cost_per_kwh": 0.12
}

Output JSON format:
{
    "process_energy": [
        {
            "process_id": "P1",
            "name": "Welding",
            "equipment_type": "robot",
            "energy_per_unit_kwh": 0.0833,
            "energy_total_kwh": 83.33,
            "cost_estimate": 10.0
        }
    ],
    "total_energy_kwh": 150.5,
    "total_cost": 18.06,
    "energy_by_type": {
        "robot": 83.33,
        "machine": 67.17
    }
}

Logic:
  - For each process: energy_per_cycle = (equipment_power_kw * cycle_time_sec / 3600)
  - energy_per_unit = energy_per_cycle (since each unit goes through the process once)
  - energy_total = energy_per_cycle * production_volume / parallel_count
    (parallel stations share the production volume)
  - cost = energy_total * cost_per_kwh
"""

import argparse
import json
import os
import sys


# Default energy rates (kW) by equipment type if not provided
DEFAULT_ENERGY_RATES = {
    "robot": 5.0,
    "machine": 8.0,
    "conveyor": 2.0,
    "manual_station": 0.5,
    "agv": 1.5,
    "oven": 15.0,
    "press": 12.0,
    "default": 3.0,
}


def estimate_energy(data):
    """Estimate energy consumption per process based on equipment type."""
    processes = data.get("processes", [])
    equipment_assignments = data.get("equipment_assignments", [])
    energy_rates = data.get("energy_rates", {})
    production_volume = data.get("production_volume", 1000)
    cost_per_kwh = data.get("cost_per_kwh", 0.12)

    if not processes:
        return {
            "error": "No processes provided.",
            "process_energy": [],
            "total_energy_kwh": 0,
            "total_cost": 0,
            "energy_by_type": {},
        }

    # Merge default rates with provided rates (provided takes priority)
    effective_rates = dict(DEFAULT_ENERGY_RATES)
    effective_rates.update(energy_rates)

    # Build equipment assignment lookup: process_id -> equipment info
    equipment_by_process = {}
    for ea in equipment_assignments:
        pid = ea["process_id"]
        if pid not in equipment_by_process:
            equipment_by_process[pid] = []
        equipment_by_process[pid].append(ea)

    process_energy = []
    total_energy_kwh = 0.0
    energy_by_type = {}

    for proc in processes:
        pid = proc["process_id"]
        name = proc.get("name", pid)
        cycle_time_sec = proc.get("cycle_time_sec", 0)
        parallel_count = proc.get("parallel_count", 1)
        if parallel_count <= 0:
            parallel_count = 1

        # Get equipment for this process
        equip_list = equipment_by_process.get(pid, [])
        if not equip_list:
            # No equipment assigned, use default
            equip_type = "default"
            equip_power_kw = effective_rates.get("default", 3.0)
        else:
            # If multiple equipment, sum their power
            equip_type_parts = []
            equip_power_kw = 0.0
            for eq in equip_list:
                et = eq.get("equipment_type", "default")
                equip_type_parts.append(et)
                equip_power_kw += effective_rates.get(et, effective_rates.get("default", 3.0))
            equip_type = "+".join(sorted(set(equip_type_parts)))

        # Energy per cycle (kWh) = power_kW * time_hours
        energy_per_cycle_kwh = equip_power_kw * cycle_time_sec / 3600.0

        # Energy per unit = energy per cycle (each unit passes through once)
        energy_per_unit_kwh = energy_per_cycle_kwh

        # Total energy = energy per cycle * (production_volume / parallel_count)
        # Because parallel stations share the total volume
        units_per_station = production_volume / parallel_count
        energy_total_kwh = energy_per_cycle_kwh * units_per_station

        # Cost
        cost_estimate = energy_total_kwh * cost_per_kwh

        process_energy.append({
            "process_id": pid,
            "name": name,
            "equipment_type": equip_type,
            "power_kw": round(equip_power_kw, 4),
            "cycle_time_sec": cycle_time_sec,
            "parallel_count": parallel_count,
            "energy_per_unit_kwh": round(energy_per_unit_kwh, 4),
            "energy_total_kwh": round(energy_total_kwh, 4),
            "cost_estimate": round(cost_estimate, 4),
        })

        total_energy_kwh += energy_total_kwh

        # Aggregate by type
        for et_part in equip_type.split("+"):
            energy_by_type[et_part] = round(
                energy_by_type.get(et_part, 0.0) + energy_total_kwh, 4
            )

    total_cost = total_energy_kwh * cost_per_kwh

    return {
        "process_energy": process_energy,
        "total_energy_kwh": round(total_energy_kwh, 4),
        "total_cost": round(total_cost, 4),
        "energy_by_type": energy_by_type,
        "production_volume": production_volume,
        "cost_per_kwh": cost_per_kwh,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Energy Estimator - Estimate energy consumption per process"
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
        result = estimate_energy(data)
    except Exception as e:
        result = {"error": str(e), "process_energy": [], "total_energy_kwh": 0, "total_cost": 0, "energy_by_type": {}}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Estimation complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
