"""
TASK 17: 17 Pyspark Advanced
Delegates to the comprehensive hadoop_spark_tasks.py implementation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "12_hadoop"))
from hadoop_spark_tasks import run as hadoop_run
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT  = BASE / "output"; OUT.mkdir(exist_ok=True)

TASK_FOCUS = {
    "14": "Spark Basics: SparkContext, parallelize, map/filter/reduce, stats",
    "15": "Spark DataFrames: withColumn, filter, groupBy, join, dropDuplicates",
    "16": "Spark SQL: GroupBy queries, top-earner per dept, YTD net by employee",
    "17": "PySpark Advanced: Partitioning by dept, caching, broadcast join",
}

def run():
    print("="*65)
    print(f"  TASK 17: {TASK_FOCUS.get('17','Spark Task')}")
    print("="*65)
    print("\n  Running comprehensive Spark simulation (tasks 12-17 combined)...")
    results = hadoop_run()
    (OUT/"spark_task_17_results.json").write_text(
        json.dumps(results, indent=2, default=str))
    print(f"\n  Focus areas covered in this task:")
    print(f"    {TASK_FOCUS.get('17','')}")
    print(f"\n✓ Results: {OUT}/spark_task_17_results.json")
    return results

if __name__ == "__main__":
    run()
