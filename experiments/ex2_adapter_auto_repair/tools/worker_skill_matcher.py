"""
Worker Skill Matcher - Evaluate worker-process skill matching quality.

Input JSON format:
{
    "workers": [
        {"worker_id": "W001", "name": "Alice Kim", "skill_level": "Senior"},
        {"worker_id": "W002", "name": "Bob Park", "skill_level": "Mid"},
        {"worker_id": "W003", "name": "Charlie Lee", "skill_level": "Junior"}
    ],
    "assignments": [
        {"process_id": "P001", "parallel_index": 0, "resource_id": "W001", "role": "operator"},
        {"process_id": "P002", "parallel_index": 0, "resource_id": "W002", "role": "operator"},
        {"process_id": "P003", "parallel_index": 0, "resource_id": "W003", "role": "operator"}
    ],
    "process_complexity": [
        {"process_id": "P001", "name": "Welding", "cycle_time_sec": 130.0, "complexity_level": "High"},
        {"process_id": "P002", "name": "Assembly", "cycle_time_sec": 80.0, "complexity_level": "Medium"},
        {"process_id": "P003", "name": "Inspection", "cycle_time_sec": 40.0, "complexity_level": "Low"}
    ]
}

Output JSON format:
{
    "matches": [...],
    "overall_match_score": 95.0,
    "mismatches": [...],
    "skill_distribution": {...},
    "suggestions": [...]
}

Logic:
  - complexity_level can be explicitly provided or derived from cycle_time:
    >120s = High, >60s = Medium, else = Low.
  - Match scores: Perfect match (same tier) = 100.
    Senior on Medium = 80, Senior on Low = 60.
    Mid on High = 70, Mid on Low = 80.
    Junior on Medium = 70, Junior on High = 40.
  - Mismatches: match_score < 70.
"""

import argparse
import json
import os
import sys


# Skill levels ordered from lowest to highest
SKILL_LEVELS = {"Junior": 1, "Mid": 2, "Senior": 3}
COMPLEXITY_LEVELS = {"Low": 1, "Medium": 2, "High": 3}

# Match score matrix: (skill_level, complexity_level) -> score
MATCH_SCORES = {
    ("Senior", "High"): 100,
    ("Senior", "Medium"): 80,
    ("Senior", "Low"): 60,
    ("Mid", "High"): 70,
    ("Mid", "Medium"): 100,
    ("Mid", "Low"): 80,
    ("Junior", "High"): 40,
    ("Junior", "Medium"): 70,
    ("Junior", "Low"): 100,
}

RECOMMENDATIONS = {
    ("Senior", "High"): "Excellent match. Senior skill well-suited for high complexity.",
    ("Senior", "Medium"): "Good match but senior skill may be underutilized. Consider for higher complexity work.",
    ("Senior", "Low"): "Overqualified. Reassign to higher complexity process.",
    ("Mid", "High"): "Skill gap risk. Consider additional training or pairing with senior worker.",
    ("Mid", "Medium"): "Excellent match. Mid-level skill well-suited for medium complexity.",
    ("Mid", "Low"): "Good match. Worker has headroom for slightly more complex tasks.",
    ("Junior", "High"): "Critical mismatch. High risk of quality issues. Reassign immediately.",
    ("Junior", "Medium"): "Slight skill gap. Provide supervision and training plan.",
    ("Junior", "Low"): "Excellent match. Good entry-level assignment.",
}


def derive_complexity(cycle_time_sec):
    """Derive complexity level from cycle time."""
    if cycle_time_sec > 120:
        return "High"
    elif cycle_time_sec > 60:
        return "Medium"
    else:
        return "Low"


def evaluate_skill_matching(data):
    """Evaluate worker-process skill matching."""
    workers = data.get("workers", [])
    assignments = data.get("assignments", [])
    process_complexity = data.get("process_complexity", [])

    if not workers:
        return {"error": "No workers provided.", "suggestions": ["Provide workers array."]}
    if not assignments:
        return {"error": "No assignments provided.", "suggestions": ["Provide assignments array."]}
    if not process_complexity:
        return {"error": "No process_complexity provided.", "suggestions": ["Provide process_complexity array."]}

    # Build worker lookup
    worker_lookup = {}
    for w in workers:
        worker_lookup[w["worker_id"]] = {
            "name": w.get("name", w["worker_id"]),
            "skill_level": w.get("skill_level", "Mid"),
        }

    # Build process complexity lookup
    proc_lookup = {}
    for pc in process_complexity:
        pid = pc["process_id"]
        complexity = pc.get("complexity_level")
        if not complexity:
            complexity = derive_complexity(pc.get("cycle_time_sec", 60.0))
        proc_lookup[pid] = {
            "name": pc.get("name", pid),
            "cycle_time_sec": pc.get("cycle_time_sec", 0.0),
            "complexity_level": complexity,
        }

    # Evaluate each assignment
    matches = []
    mismatches = []
    scores = []
    unmatched_workers = set(worker_lookup.keys())

    for asgn in assignments:
        resource_id = asgn.get("resource_id")
        process_id = asgn.get("process_id")

        if resource_id not in worker_lookup:
            continue  # This assignment may be for equipment, skip
        if process_id not in proc_lookup:
            continue

        unmatched_workers.discard(resource_id)

        worker = worker_lookup[resource_id]
        process = proc_lookup[process_id]

        skill_level = worker["skill_level"]
        complexity_level = process["complexity_level"]

        # Normalize skill_level for lookup (handle case variations)
        skill_normalized = skill_level.capitalize()
        if skill_normalized not in SKILL_LEVELS:
            # Try common aliases
            skill_map = {"senior": "Senior", "mid": "Mid", "middle": "Mid", "junior": "Junior",
                         "expert": "Senior", "beginner": "Junior", "intermediate": "Mid"}
            skill_normalized = skill_map.get(skill_level.lower(), "Mid")

        complexity_normalized = complexity_level.capitalize()
        if complexity_normalized not in COMPLEXITY_LEVELS:
            complexity_map = {"high": "High", "medium": "Medium", "low": "Low",
                              "hard": "High", "easy": "Low", "moderate": "Medium"}
            complexity_normalized = complexity_map.get(complexity_level.lower(), "Medium")

        score = MATCH_SCORES.get((skill_normalized, complexity_normalized), 50)
        recommendation = RECOMMENDATIONS.get(
            (skill_normalized, complexity_normalized),
            "Review this assignment."
        )

        match_entry = {
            "worker_id": resource_id,
            "worker_name": worker["name"],
            "skill_level": skill_normalized,
            "process_id": process_id,
            "process_name": process["name"],
            "complexity_level": complexity_normalized,
            "cycle_time_sec": process["cycle_time_sec"],
            "match_score": score,
            "recommendation": recommendation,
        }
        matches.append(match_entry)
        scores.append(score)

        if score < 70:
            mismatches.append(match_entry)

    # Overall score
    overall_match_score = sum(scores) / len(scores) if scores else 0.0

    # Sort matches by score ascending (worst first for visibility)
    matches.sort(key=lambda x: x["match_score"])

    # Skill distribution
    skill_dist = {"Senior": 0, "Mid": 0, "Junior": 0}
    for w in workers:
        sl = w.get("skill_level", "Mid").capitalize()
        if sl in skill_dist:
            skill_dist[sl] += 1

    complexity_dist = {"High": 0, "Medium": 0, "Low": 0}
    for pc in process_complexity:
        cl = pc.get("complexity_level")
        if not cl:
            cl = derive_complexity(pc.get("cycle_time_sec", 60.0))
        cl = cl.capitalize()
        if cl in complexity_dist:
            complexity_dist[cl] += 1

    # Suggestions
    suggestions = []
    if mismatches:
        critical = [m for m in mismatches if m["match_score"] < 50]
        if critical:
            names = ", ".join(f"{m['worker_name']}@{m['process_name']}" for m in critical)
            suggestions.append(
                f"Critical skill mismatches detected: {names}. "
                f"Immediate reassignment recommended."
            )
        moderate = [m for m in mismatches if 50 <= m["match_score"] < 70]
        if moderate:
            names = ", ".join(f"{m['worker_name']}@{m['process_name']}" for m in moderate)
            suggestions.append(
                f"Moderate skill gaps: {names}. "
                f"Consider training programs or gradual transition."
            )
    else:
        suggestions.append("All worker-process assignments are well-matched.")

    if overall_match_score < 70:
        suggestions.append(
            f"Overall match score is low ({round(overall_match_score, 1)}). "
            f"Broad reassignment review recommended."
        )
    elif overall_match_score >= 90:
        suggestions.append(
            f"Overall match score is excellent ({round(overall_match_score, 1)})."
        )

    # Check for unassigned workers
    if unmatched_workers:
        names = ", ".join(worker_lookup[wid]["name"] for wid in unmatched_workers if wid in worker_lookup)
        if names:
            suggestions.append(f"Unassigned workers: {names}.")

    # Check skill-complexity balance
    if skill_dist.get("Senior", 0) > 0 and complexity_dist.get("High", 0) == 0:
        suggestions.append(
            "Senior workers available but no high-complexity processes. "
            "Senior workers may be underutilized."
        )
    if skill_dist.get("Junior", 0) > 0 and complexity_dist.get("Low", 0) == 0:
        suggestions.append(
            "Junior workers present but no low-complexity processes. "
            "Risk of quality issues due to skill gaps."
        )

    return {
        "matches": matches,
        "overall_match_score": round(overall_match_score, 2),
        "mismatches": mismatches,
        "skill_distribution": skill_dist,
        "complexity_distribution": complexity_dist,
        "num_evaluated": len(matches),
        "suggestions": suggestions,
    }


def main():
    parser = argparse.ArgumentParser(description="Worker Skill Matcher - Evaluate worker-process skill matching")
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
        result = evaluate_skill_matching(data)
    except Exception as e:
        result = {"error": str(e), "suggestions": ["Check input data format."]}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
