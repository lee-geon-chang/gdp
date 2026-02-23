def apply_result_to_bop(bop_json, tool_output):
    import json
    import copy
    result = copy.deepcopy(bop_json)

    output = json.loads(tool_output)
    # output이 배열이므로 배열 순회
    for item in output:
        process_id = item['id']
        count = item['count']
        print(f"Process {process_id}: {count} resources")

    return result