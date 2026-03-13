import json


def apply_result_to_bop(bop_json, tool_output):
    """Applies the output of the worker_skill_analyzer tool to the BOP JSON."""

    try:
        output_data = json.loads(tool_output)
    except json.JSONDecodeError:
        print("Error: Tool output is not valid JSON.")
        return bop_json

    # Update processes with worker assignments
    process_worker_assignments = output_data.get('process_worker_assignments', {})
    for process in bop_json.get('processes', []):
        process_id = process['process_id']
        assignments = process_worker_assignments.get(process_id, [])

        # Clear existing worker resources for the process
        process['resources'] = [r for r in process['resources'] if r['resource_type'] != 'worker']

        # Add new worker resources based on tool output
        for assignment in assignments:
            worker_id = assignment['worker_id']
            process['resources'].append({
                'resource_type': 'worker',
                'resource_id': worker_id,
                'quantity': 1,
                'role': 'operator',
                'relative_location': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'rotation_y': 0.0,
                'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0},
                'parallel_line_index': 1  # Default value
            })

    # Add mismatch warnings and reassignment suggestions to the BOP (optional)
    bop_json['tool_results'] = {
        'skill_adequacy_scores': output_data.get('skill_adequacy_scores', {}),
        'mismatch_warnings': output_data.get('mismatch_warnings', []),
        'reassignment_suggestions': output_data.get('reassignment_suggestions', [])
    }

    return bop_json
