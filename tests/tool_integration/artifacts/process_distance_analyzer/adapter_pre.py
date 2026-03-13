import json
import math


def convert_bop_to_input(bop_json: dict, params: dict) -> str:
    """Extract data from BOP, apply field mappings, return as JSON string."""
    data = {
        'project_title': bop_json.get('project_title', ''),
        'target_uph': bop_json.get('target_uph', 0.0),
        'processes': []
    }

    for process in bop_json.get('processes', []):
        process_data = {
            'process_id': process.get('process_id', ''),
            'parallel_count': process.get('parallel_count', 0),
            'predecessor_ids': process.get('predecessor_ids', []),
            'successor_ids': process.get('successor_ids', []),
            'parallel_lines': [],
            'resources': []
        }

        for line in process.get('parallel_lines', []):
            line_data = {
                'parallel_index': line.get('parallel_index', 0),
                'name': line.get('name', ''),
                'description': line.get('description', ''),
                'cycle_time_sec': line.get('cycle_time_sec', 0.0),
                'location': line.get('location', {'x': 0.0, 'y': 0.0, 'z': 0.0}),
                'rotation_y': line.get('rotation_y', 0.0)
            }
            process_data['parallel_lines'].append(line_data)

        data['processes'].append(process_data)

    data['equipments'] = bop_json.get('equipments', [])
    data['workers'] = bop_json.get('workers', [])
    data['materials'] = bop_json.get('materials', [])
    data['obstacles'] = bop_json.get('obstacles', [])

    return json.dumps(data, indent=2)
