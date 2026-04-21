"""
TASK 10: ETL vs ELT — Dedicated file
See also: 09_data_warehousing/dw_etl_ingestion.py (full implementation)
This file focuses on the comparison and runs both pipelines.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "09_data_warehousing"))
from dw_etl_ingestion import etl_pipeline, elt_pipeline, generate_ingestion_data
import os, json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT  = BASE / "output"
OUT.mkdir(exist_ok=True)

def run():
    print("="*60)
    print("  TASK 10: ETL vs ELT Pipeline Comparison")
    print("="*60)

    # Generate source data
    from dw_etl_ingestion import generate_ingestion_data
    csv_path = OUT / "etl_source.csv"
    csv_path.write_text(
        "emp_id,emp_code,first_name,last_name,dept,designation,basic_salary,gender,dob,email,date_joined,status\n"
        + "\n".join(
            f"{i},EMP{i:04d},Employee{i},Surname{i},IT,Engineer,{50000+i*1000},Male,1990-01-01,emp{i}@pw.in,2020-01-01,Active"
            for i in range(1, 51)
        )
    )

    etl_db = str(OUT / "etl_result.db")
    elt_db = str(OUT / "elt_result.db")
    for db in [etl_db, elt_db]:
        if os.path.exists(db): os.remove(db)

    print("\n[ETL] Extract → Transform (in Python) → Load")
    etl = etl_pipeline(str(csv_path), etl_db)

    print("\n[ELT] Extract → Load raw → Transform (SQL in DB)")
    elt = elt_pipeline(str(csv_path), elt_db)

    print("\n  Comparison Summary:")
    print(f"  {'Metric':<30} {'ETL':>15} {'ELT':>15}")
    print("  " + "─"*63)
    metrics = [
        ("Extract rows",         etl['steps']['extract']['rows'],       elt['steps']['extract']['rows']),
        ("Extract time (ms)",    etl['steps']['extract']['ms'],         elt['steps']['extract']['ms']),
        ("Transform time (ms)",  etl['steps']['transform']['ms'],       elt['steps']['transform_sql']['ms']),
        ("Load time (ms)",       etl['steps']['load']['ms'],            0),
        ("Total time (ms)",      etl['total_ms'],                       elt['total_ms']),
        ("Records loaded",       etl['steps']['load']['loaded'],        elt['steps']['transform_sql']['rows']),
    ]
    for label, ev, lv in metrics:
        print(f"  {label:<30} {str(ev):>15} {str(lv):>15}")

    print("\n  When to use ETL:")
    print("    • Data needs heavy transformation BEFORE landing in target")
    print("    • Target system has limited compute (small DB)")
    print("    • Privacy/security: scrub PII before loading")
    print("    • On-premise legacy pipelines")
    print("\n  When to use ELT:")
    print("    • Cloud DW with massive compute (BigQuery, Snowflake)")
    print("    • Raw data lake approach (load everything, transform later)")
    print("    • Fast ingestion needed (transform can wait)")
    print("    • Exploratory analytics (schema not yet fixed)")

    results = {"etl": etl, "elt": elt, "timestamp": datetime.now().isoformat()}
    (OUT/"etl_elt_comparison.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results: {OUT}/etl_elt_comparison.json")
    return results

if __name__ == "__main__":
    run()
