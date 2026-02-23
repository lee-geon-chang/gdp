"""
Layout Compactor - Compact process layout to minimize total footprint while maintaining minimum gaps.

Input JSON format:
{
    "layout_nodes": [
        {
            "node_id": "P1",
            "name": "Assembly Station 1",
            "x": 0.0, "y": 0.0, "z": 0.0,
            "width": 3.0, "depth": 2.0,
            "predecessors": [],
            "successors": ["P2"]
        },
        {
            "node_id": "P2",
            "name": "Welding Station",
            "x": 10.0, "y": 0.0, "z": 0.0,
            "width": 4.0, "depth": 3.0,
            "predecessors": ["P1"],
            "successors": ["P3"]
        }
    ],
    "min_gap": 1.5,
    "flow_direction": "x"
}

Output JSON format:
{
    "compacted_nodes": [
        {
            "node_id": "P1",
            "name": "Assembly Station 1",
            "original_x": 0.0,
            "original_z": 0.0,
            "new_x": 0.0,
            "new_z": 0.0,
            "shifted": false
        },
        {
            "node_id": "P2",
            "name": "Welding Station",
            "original_x": 10.0,
            "original_z": 0.0,
            "new_x": 4.5,
            "new_z": 0.0,
            "shifted": true
        }
    ],
    "total_original_span": 14.0,
    "total_compacted_span": 9.5,
    "reduction_pct": 32.14
}

Logic:
  - Sort nodes in topological order along flow_direction.
  - Place each node as close as possible to its predecessors while maintaining min_gap.
  - For nodes without predecessors (roots), place them starting from 0 in order.
  - Calculate total span reduction.
"""

import argparse
import json
import os
import sys
from collections import deque


def topological_sort(nodes_map, node_ids):
    """
    Perform topological sort on the DAG defined by nodes_map.
    Returns a list of node_ids in topological order.
    Falls back to original order if cycle detected.
    """
    in_degree = {nid: 0 for nid in node_ids}
    adj = {nid: [] for nid in node_ids}

    for nid in node_ids:
        node = nodes_map[nid]
        for succ_id in node.get("successors", []):
            if succ_id in adj:
                adj[nid].append(succ_id)
                in_degree[succ_id] = in_degree.get(succ_id, 0) + 1

    # Kahn's algorithm
    queue = deque()
    for nid in node_ids:
        if in_degree[nid] == 0:
            queue.append(nid)

    result = []
    while queue:
        # Among ready nodes, prefer those with smaller original position
        # (to maintain stable ordering)
        nid = queue.popleft()
        result.append(nid)
        for succ_id in adj.get(nid, []):
            in_degree[succ_id] -= 1
            if in_degree[succ_id] == 0:
                queue.append(succ_id)

    if len(result) != len(node_ids):
        # Cycle detected, fall back to original order
        return node_ids

    return result


def compact_layout(data):
    """Compact process layout to minimize total footprint."""
    layout_nodes = data.get("layout_nodes", [])
    min_gap = data.get("min_gap", 1.5)
    flow_direction = data.get("flow_direction", "x")

    if not layout_nodes:
        return {
            "compacted_nodes": [],
            "total_original_span": 0,
            "total_compacted_span": 0,
            "reduction_pct": 0,
            "warning": "No layout nodes provided.",
        }

    # Validate flow_direction
    if flow_direction not in ("x", "z"):
        flow_direction = "x"

    # Build node map
    nodes_map = {}
    for node in layout_nodes:
        nid = node["node_id"]
        nodes_map[nid] = node

    node_ids = [n["node_id"] for n in layout_nodes]

    # Topological sort
    sorted_ids = topological_sort(nodes_map, node_ids)

    # Determine primary and secondary axes
    primary_axis = flow_direction  # "x" or "z"
    size_key = "width" if primary_axis == "x" else "depth"
    secondary_axis = "z" if primary_axis == "x" else "x"

    # Calculate original span
    original_positions = []
    for nid in node_ids:
        node = nodes_map[nid]
        pos = node.get(primary_axis, 0.0)
        size = node.get(size_key, 1.0)
        original_positions.append((pos, pos + size))

    if original_positions:
        orig_min = min(p[0] for p in original_positions)
        orig_max = max(p[1] for p in original_positions)
        total_original_span = orig_max - orig_min
    else:
        total_original_span = 0

    # Place nodes in topological order
    new_positions = {}  # node_id -> new primary axis position

    for nid in sorted_ids:
        node = nodes_map[nid]
        predecessors = node.get("predecessors", [])
        node_size = node.get(size_key, 1.0)

        if not predecessors or all(p not in new_positions for p in predecessors):
            # Root node or predecessors not in graph: place at earliest available
            # Find the first available position that doesn't overlap with already-placed nodes
            candidate_pos = 0.0

            # Check for overlap with all previously placed nodes
            for placed_id, placed_pos in new_positions.items():
                placed_node = nodes_map[placed_id]
                placed_size = placed_node.get(size_key, 1.0)
                placed_end = placed_pos + placed_size

                # Check if this node and the placed node share the same secondary axis zone
                # (i.e., they could collide)
                node_sec = node.get(secondary_axis, 0.0)
                node_sec_size = node.get("depth" if primary_axis == "x" else "width", 1.0)
                placed_sec = placed_node.get(secondary_axis, 0.0)
                placed_sec_size = placed_node.get("depth" if primary_axis == "x" else "width", 1.0)

                # Check secondary axis overlap
                sec_overlap = not (
                    node_sec + node_sec_size <= placed_sec or
                    placed_sec + placed_sec_size <= node_sec
                )

                if sec_overlap:
                    # Must not overlap on primary axis
                    min_start = placed_end + min_gap
                    if candidate_pos < min_start:
                        candidate_pos = min_start

            new_positions[nid] = candidate_pos
        else:
            # Has predecessors: place right after the latest predecessor
            latest_pred_end = 0.0
            for pred_id in predecessors:
                if pred_id in new_positions:
                    pred_node = nodes_map.get(pred_id, {})
                    pred_size = pred_node.get(size_key, 1.0)
                    pred_end = new_positions[pred_id] + pred_size
                    if pred_end > latest_pred_end:
                        latest_pred_end = pred_end

            candidate_pos = latest_pred_end + min_gap

            # Also check for overlap with non-predecessor placed nodes
            for placed_id, placed_pos in new_positions.items():
                if placed_id in predecessors:
                    continue
                placed_node = nodes_map[placed_id]
                placed_size = placed_node.get(size_key, 1.0)
                placed_end = placed_pos + placed_size

                # Check secondary axis overlap
                node_sec = node.get(secondary_axis, 0.0)
                node_sec_size = node.get("depth" if primary_axis == "x" else "width", 1.0)
                placed_sec = placed_node.get(secondary_axis, 0.0)
                placed_sec_size = placed_node.get("depth" if primary_axis == "x" else "width", 1.0)

                sec_overlap = not (
                    node_sec + node_sec_size <= placed_sec or
                    placed_sec + placed_sec_size <= node_sec
                )

                if sec_overlap:
                    min_start = placed_end + min_gap
                    if candidate_pos < min_start:
                        candidate_pos = min_start

            new_positions[nid] = candidate_pos

    # Build output
    compacted_nodes = []
    for nid in node_ids:
        node = nodes_map[nid]
        orig_x = node.get("x", 0.0)
        orig_z = node.get("z", 0.0)

        new_primary = new_positions.get(nid, node.get(primary_axis, 0.0))

        if primary_axis == "x":
            new_x = round(new_primary, 4)
            new_z = round(orig_z, 4)
        else:
            new_x = round(orig_x, 4)
            new_z = round(new_primary, 4)

        shifted = (abs(new_x - orig_x) > 0.001) or (abs(new_z - orig_z) > 0.001)

        compacted_nodes.append({
            "node_id": nid,
            "name": node.get("name", nid),
            "original_x": round(orig_x, 4),
            "original_z": round(orig_z, 4),
            "new_x": new_x,
            "new_z": new_z,
            "shifted": shifted,
        })

    # Calculate compacted span
    if new_positions:
        compacted_positions = []
        for nid, pos in new_positions.items():
            node = nodes_map[nid]
            size = node.get(size_key, 1.0)
            compacted_positions.append((pos, pos + size))

        comp_min = min(p[0] for p in compacted_positions)
        comp_max = max(p[1] for p in compacted_positions)
        total_compacted_span = comp_max - comp_min
    else:
        total_compacted_span = 0

    reduction_pct = 0.0
    if total_original_span > 0:
        reduction_pct = ((total_original_span - total_compacted_span) / total_original_span) * 100.0

    return {
        "compacted_nodes": compacted_nodes,
        "total_original_span": round(total_original_span, 4),
        "total_compacted_span": round(total_compacted_span, 4),
        "reduction_pct": round(reduction_pct, 2),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Layout Compactor - Compact process layout to minimize total footprint"
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
        result = compact_layout(data)
    except Exception as e:
        result = {"error": str(e), "compacted_nodes": [], "total_original_span": 0, "total_compacted_span": 0, "reduction_pct": 0}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Compaction complete. Results written to {args.output}")


if __name__ == "__main__":
    main()
