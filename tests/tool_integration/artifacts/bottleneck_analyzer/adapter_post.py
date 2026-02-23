import json


def apply_result_to_bop(bop_json, tool_output):
    try:
        output_data = json.loads(tool_output)
    except json.JSONDecodeError:
        return bop_json

    cycle_times = output_data.get('cycle_times', {})
    bottleneck_process = output_data.get('bottleneck_process', {})
    improvement_suggestion = output_data.get('improvement_suggestion', {})

    # Update process cycle times in BOP
    for process in bop_json.get('processes', []):
        process_id = process.get('process_id')
        if process_id in cycle_times:
            for line in process.get('parallel_lines', []):
                line['cycle_time_sec'] = cycle_times[process_id]

    # Add bottleneck info to BOP (example: add to project_title)
    if bottleneck_process:
        bottleneck_id = bottleneck_process.get('process_id')
        bop_json['project_title'] = bop_json.get('project_title', '') + ' - Bottleneck: ' + str(bottleneck_id)

    # Apply improvement suggestion (example: update parallel count)
    if improvement_suggestion:
        process_id = improvement_suggestion.get('process_id')
        required_parallel_lines = improvement_suggestion.get('required_parallel_lines')

        for process in bop_json.get('processes', []):
            if process.get('process_id') == process_id:
                process['parallel_count'] = required_parallel_lines

    return bop_json