"""Total Cycle Calculator - HAS BUG"""
import json
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o', required=True)
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 버그: total에 누적하지 않고 덮어씀
    total = 0
    for proc in data.get("processes", []):
        for line in proc.get("parallel_lines", []):
            total = line.get("cycle_time_sec", 0)  # 버그! += 이어야 함

    result = {
        "total_cycle_time": total,
        "process_count": len(data.get("processes", []))
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"[Success] Total: {total}")

if __name__ == "__main__":
    main()
