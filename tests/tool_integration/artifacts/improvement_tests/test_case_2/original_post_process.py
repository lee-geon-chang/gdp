def apply_result_to_bop(bop_json, tool_output):
    import json
    import copy
    result = copy.deepcopy(bop_json)

    output = json.loads(tool_output)
    # 오류: output이 배열인데 객체처럼 접근
    for process_id, count in output["resource_counts"].items():
        print(f"Process {process_id}: {count} resources")

    return result
