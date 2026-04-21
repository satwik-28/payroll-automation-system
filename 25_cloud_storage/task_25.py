"""
TASK 25: Cloud Storage — S3 bucket, versioning, presigned URLs, lifecycle
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "24_cloud_basics"))
from cloud_tasks import run as cloud_run
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT  = BASE / "output"; OUT.mkdir(exist_ok=True)

def run():
    print("="*65)
    print(f"  TASK 25: Cloud Storage — S3 bucket, versioning, presigned URLs, lifecycle")
    print("="*65)
    results = cloud_run()
    (OUT/"task_25_results.json").write_text(
        json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results: {OUT}/task_25_results.json")
    return results

if __name__ == "__main__":
    run()
