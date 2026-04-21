"""
TASK 23: Airflow Advanced — Scheduling, Monitoring, Retry, SLA
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "22_airflow_basics"))
from airflow_tasks import run as airflow_run
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT  = BASE / "output"; OUT.mkdir(exist_ok=True)

def run():
    print("="*65)
    print("  TASK 23: Airflow Advanced — Scheduling, Monitoring, Retry, SLA")
    print("="*65)
    results = airflow_run()
    (OUT/"task_23_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results: {OUT}/task_23_results.json")
    return results

if __name__ == "__main__":
    run()
