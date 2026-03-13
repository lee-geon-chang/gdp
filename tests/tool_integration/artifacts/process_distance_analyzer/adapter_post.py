import json


def apply_result_to_bop(bop_json: dict, tool_output: str) -> dict:
    """Parse tool output, update BOP, return complete updated BOP."""
    try:
        output_data = json.loads(tool_output)
    except json.JSONDecodeError:
        print("[Error] Invalid JSON format in tool output.")
        return bop_json  # Return original BOP if parsing fails

    process_distances = output_data.get('process_distances', {})
    total_distance = output_data.get('total_distance', 0.0)
    max_distance_segment = output_data.get('max_distance_segment', {})

    # Add tool output to BOP (example: add to a new 'analysis' field)
    bop_json['analysis'] = {
        'process_distances': process_distances,
        'total_distance': total_distance,
        'max_distance_segment': max_distance_segment
    }

    return bop_json
