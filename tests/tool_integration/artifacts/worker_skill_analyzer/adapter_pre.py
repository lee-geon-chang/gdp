import json
import math


def convert_bop_to_input(bop_json, params):
    """Converts BOP JSON to the input format required by the worker_skill_analyzer tool."""

    data = {}
    data['project_title'] = bop_json.get('project_title', '')
    data['target_uph'] = bop_json.get('target_uph', 0.0)
    data['processes'] = []
    data['equipments'] = []
    data['workers'] = []
    data['materials'] = []
    data['obstacles'] = []

    for process in bop_json.get('processes', []):
        new_process = {
            'process_id': process.get('process_id', ''),
            'parallel_count': process.get('parallel_count', 1),
            'predecessor_ids': process.get('predecessor_ids', []),
            'successor_ids': process.get('successor_ids', []),
            'parallel_lines': [],
            'resources': []
        }

        for line in process.get('parallel_lines', []):
            new_line = {
                'parallel_index': line.get('parallel_index', 1),
                'name': line.get('name', ''),
                'description': line.get('description', ''),
                'cycle_time_sec': line.get('cycle_time_sec', 0.0),
                'location': line.get('location', {'x': 0.0, 'y': 0.0, 'z': 0.0}),
                'rotation_y': line.get('rotation_y', 0.0)
            }
            new_process['parallel_lines'].append(new_line)

        for resource in process.get('resources', []):
            new_resource = {
                'resource_type': resource.get('resource_type', ''),
                'resource_id': resource.get('resource_id', ''),
                'quantity': resource.get('quantity', 1),
                'role': resource.get('role', ''),
                'relative_location': resource.get('relative_location', {'x': 0.0, 'y': 0.0, 'z': 0.0}),
                'rotation_y': resource.get('rotation_y', 0.0),
                'scale': resource.get('scale', {'x': 1.0, 'y': 1.0, 'z': 1.0}),
                'parallel_line_index': resource.get('parallel_line_index', 1)
            }
            new_process['resources'].append(new_resource)

        data['processes'].append(new_process)

    for equipment in bop_json.get('equipments', []):
        data['equipments'].append({
            'equipment_id': equipment.get('equipment_id', ''),
            'name': equipment.get('name', ''),
            'type': equipment.get('type', '')
        })

    for worker in bop_json.get('workers', []):
        data['workers'].append({
            'worker_id': worker.get('worker_id', ''),
            'name': worker.get('name', ''),
            'skill_level': worker.get('skill_level', 'Junior')
        })

    for material in bop_json.get('materials', []):
        data['materials'].append({
            'material_id': material.get('material_id', ''),
            'name': material.get('name', ''),
            'unit': material.get('unit', '')
        })

    for obstacle in bop_json.get('obstacles', []):
        data['obstacles'].append({
            'obstacle_id': obstacle.get('obstacle_id', ''),
            'name': obstacle.get('name', ''),
            'type': obstacle.get('type', ''),
            'position': obstacle.get('position', {'x': 0.0, 'y': 0.0, 'z': 0.0}),
            'size': obstacle.get('size', {'width': 1.0, 'height': 1.0, 'depth': 1.0}),
            'rotation_y': obstacle.get('rotation_y', 0.0)
        })

    return json.dumps(data, indent=2)
