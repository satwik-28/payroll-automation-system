"""
RUN_ALL.py — Master Runner for All 30 Data Engineering Tasks
Payroll Automation System — Complete Implementation

Usage:
    python run_all.py              # Run all 30 tasks
    python run_all.py --task 5    # Run only task 5
    python run_all.py --task 1-10 # Run tasks 1 through 10
    python run_all.py --list      # Show all tasks
"""
import sys, os, time, json, importlib.util, traceback
from pathlib import Path
from datetime import datetime

BASE        = Path(__file__).parent
RESULTS_DIR = BASE / "shared" / "output"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TASKS = {
    1:  ("01_linux_filesystem/filesystem_task.py",          "Linux + File System Setup"),
    2:  ("02_networking/networking_task.py",                 "Networking & API Simulation"),
    3:  ("03_python_basics/python_basics_task.py",           "Python Basics — CSV Merge"),
    4:  ("04_advanced_python/advanced_python_task.py",       "Advanced Python Modules"),
    5:  ("05_pandas_numpy/pandas_numpy_task.py",             "Pandas + NumPy (1.2M rows)"),
    6:  ("06_sql_basics/sql_tasks_06_07_08.py",              "SQL Basics — SELECT/WHERE/GROUP BY"),
    7:  ("07_advanced_sql/advanced_sql_task.py",             "Advanced SQL — Joins/Windows/CTEs"),
    8:  ("08_database_concepts/db_concepts_task.py",         "DB Concepts — OLTP vs OLAP"),
    9:  ("09_data_warehousing/dw_etl_ingestion.py",          "Data Warehousing — Star Schema"),
    10: ("10_etl_elt/etl_elt_task.py",                       "ETL vs ELT Pipelines"),
    11: ("11_data_ingestion/ingestion_task.py",              "Batch Data Ingestion"),
    12: ("12_hadoop/hadoop_spark_tasks.py",                  "Hadoop HDFS Simulation"),
    13: ("13_hdfs_architecture/hdfs_arch_task.py",           "HDFS Architecture Deep Dive"),
    14: ("14_spark_basics/task_14.py",                       "Spark Basics — RDD Operations"),
    15: ("15_spark_dataframes/task_15.py",                   "Spark DataFrames"),
    16: ("16_spark_sql/task_16.py",                          "Spark SQL Queries"),
    17: ("17_pyspark_advanced/task_17.py",                   "PySpark Advanced — Partitioning"),
    18: ("18_streaming_concepts/streaming_kafka_tasks.py",   "Streaming Concepts"),
    19: ("19_kafka_basics/task_19.py",                       "Kafka Producer-Consumer"),
    20: ("20_kafka_advanced/task_20.py",                     "Kafka Advanced — Offsets"),
    21: ("21_structured_streaming/task_21.py",               "Spark Structured Streaming"),
    22: ("22_airflow_basics/airflow_tasks.py",               "Airflow DAG"),
    23: ("23_airflow_advanced/task_23.py",                   "Airflow Advanced — SLA+Monitoring"),
    24: ("24_cloud_basics/cloud_tasks.py",                   "Cloud AWS/GCP/Azure Comparison"),
    25: ("25_cloud_storage/task_25.py",                      "Cloud Storage — S3 Simulation"),
    26: ("26_cloud_compute/task_26.py",                      "Cloud Compute — EC2 Deploy"),
    27: ("27_data_warehouse_cloud/task_27.py",               "Cloud DW — BigQuery/Redshift"),
    28: ("28_lakehouse/lakehouse_dq_tasks.py",               "Delta Lake / Iceberg Lakehouse"),
    29: ("29_data_quality/data_quality_task.py",             "Data Quality & Anomaly Detection"),
    30: ("30_final_project/final_pipeline.py",               "Final E2E Pipeline + Dashboard"),
}

def banner():
    print("=" * 70)
    print("  PAYROLL AUTOMATION SYSTEM")
    print("  30 Data Engineering Tasks — Complete Implementation")
    print("  Python + SQLite | No External Cluster Required")
    print("=" * 70)
    print(f"  Started : {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Base    : {BASE}")
    print()

def list_tasks():
    categories = {
        "Infrastructure":    [1, 2],
        "Python":            [3, 4, 5],
        "SQL":               [6, 7, 8],
        "Data Engineering":  [9, 10, 11],
        "Hadoop & Spark":    [12, 13, 14, 15, 16, 17],
        "Streaming & Kafka": [18, 19, 20, 21],
        "Orchestration":     [22, 23],
        "Cloud":             [24, 25, 26, 27],
        "Modern DE":         [28, 29],
        "Final Project":     [30],
    }
    print("\n  ALL 30 TASKS:\n")
    for cat, nums in categories.items():
        print(f"  -- {cat} --")
        for n in nums:
            title = TASKS[n][1]
            fpath = BASE / TASKS[n][0]
            exists = "[OK]" if fpath.exists() else "[MISSING]"
            print(f"    {exists} Task {n:02d}: {title}")
        print()

def run_task(task_num: int) -> dict:
    info = TASKS.get(task_num)
    if not info:
        return {"status": "not_found", "task": task_num}

    rel_path, title = info
    script_path = BASE / rel_path

    print(f"\n{'─'*70}")
    print(f"  TASK {task_num:02d}: {title}")
    print(f"  File: {rel_path}")
    print(f"{'─'*70}")

    if not script_path.exists():
        print(f"  [MISSING] File not found: {rel_path}")
        return {"status": "missing", "task": task_num, "title": title}

    t0 = time.time()
    try:
        spec   = importlib.util.spec_from_file_location(f"task_{task_num}", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.run() if hasattr(module, "run") else None
        elapsed = round(time.time() - t0, 2)
        print(f"\n  [SUCCESS] Task {task_num:02d} completed in {elapsed}s")
        return {"status": "success", "task": task_num, "title": title,
                "elapsed_s": elapsed, "file": rel_path}
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"\n  [FAILED] Task {task_num:02d} — {e}")
        traceback.print_exc()
        return {"status": "failed", "task": task_num, "title": title,
                "elapsed_s": elapsed, "error": str(e)}

def parse_args():
    args = sys.argv[1:]
    if "--list" in args:
        return "list"
    if "--task" in args:
        idx = args.index("--task")
        val = args[idx + 1] if idx + 1 < len(args) else ""
        if "-" in val:
            lo, hi = val.split("-")
            return list(range(int(lo), int(hi) + 1))
        elif val.isdigit():
            return [int(val)]
    return list(range(1, 31))

def main():
    banner()
    cmd = parse_args()

    if cmd == "list":
        list_tasks()
        return

    task_nums = cmd
    print(f"  Running {len(task_nums)} tasks...")

    results  = []
    t_start  = time.time()

    for n in task_nums:
        results.append(run_task(n))

    total_s = round(time.time() - t_start, 1)
    success = [r for r in results if r["status"] == "success"]
    failed  = [r for r in results if r["status"] == "failed"]

    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    print(f"  Tasks run   : {len(results)}")
    print(f"  Succeeded   : {len(success)}")
    print(f"  Failed      : {len(failed)}")
    print(f"  Total time  : {total_s}s")
    print()
    print(f"  {'#':<5} {'Title':<48} {'Status':<9} {'Time':>7}")
    print("  " + "─" * 72)
    for r in results:
        icon   = "[OK]" if r["status"] == "success" else "[FAIL]"
        status = r["status"].upper()[:6]
        secs   = f"{r.get('elapsed_s', 0):.2f}s"
        title  = r.get("title", "")[:47]
        print(f"  {icon} {r['task']:02d}  {title:<48} {status:<9} {secs:>7}")

    score = round(len(success) / max(len(results), 1) * 100, 1)
    print(f"\n  Pipeline score: {score}% ({len(success)}/{len(results)} tasks passed)")

    report = {
        "run_time":     datetime.now().isoformat(),
        "tasks_run":    len(results),
        "succeeded":    len(success),
        "failed":       len(failed),
        "score_pct":    score,
        "total_time_s": total_s,
        "results":      results,
    }
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"run_{ts}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\n  Report: {path}")
    return report

if __name__ == "__main__":
    main()
