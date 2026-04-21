"""
TASK 20: Kafka partitioning, offset management, consumer lag, replay
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "18_streaming_concepts"))
from streaming_kafka_tasks import run as streaming_run
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT  = BASE / "output"; OUT.mkdir(exist_ok=True)

def run():
    print("="*65)
    print(f"  TASK 20: Kafka partitioning, offset management, consumer lag, replay")
    print("="*65)
    results = streaming_run()
    (OUT/"task_20_results.json").write_text(
        json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results: {OUT}/task_20_results.json")
    return results

if __name__ == "__main__":
    run()
