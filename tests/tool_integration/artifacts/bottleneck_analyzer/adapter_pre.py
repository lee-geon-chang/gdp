import json
import math


def convert_bop_to_input(bop_json, params):
    project_title = params.get('project_title') or bop_json.get('project_title')
    target_uph = params.get('target_uph') or bop_json.get('target_uph')

    process_width = params.get('process_width')
    process_height = params.get('process_height')
    process_depth = params.get('process_depth')

    data = {
        'project_title': project_title,
        'target_uph': target_uph,
        'processes': [],
        'equipments': [],
        'workers': [],
        'materials': [],
        'obstacles': []
    }

    for process in bop_json.get('processes', []):
        process_data = {
            'process_id': process.get('process_id'),
            'parallel_count': process.get('parallel_count', 1),
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

        for resource in process.get('resources', []):
            process_data['resources'].append(resource.get('resource_id'))

        data['processes'].append(process_data)

    for equipment in bop_json.get('equipments', []):
        data['equipments'].append(equipment.get('equipment_id'))

    for worker in bop_json.get('workers', []):
        data['workers'].append(worker.get('worker_id'))

    for material in bop_json.get('materials', []):
        data['materials'].append(material.get('material_id'))

    for obstacle in bop_json.get('obstacles', []):
        data['obstacles'].append(obstacle.get('obstacle_id'))

    return json.dumps(data, indent=2)
