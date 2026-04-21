"""
TASK 11: Data Ingestion — Batch CSV → Database Pipeline
Chunked ingestion with validation, checkpointing, and error handling.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / "09_data_warehousing"))
from dw_etl_ingestion import BatchIngestionPipeline, generate_ingestion_data
import json, os
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT  = BASE / "output"
OUT.mkdir(exist_ok=True)

def run():
    print("="*60)
    print("  TASK 11: Batch Data Ingestion — CSV → SQLite")
    print("="*60)
    csv_path = generate_ingestion_data(500)
    db_path  = str(OUT / "ingested_payroll.db")
    if os.path.exists(db_path): os.remove(db_path)

    print("\n  Pipeline config:")
    print("    Source   : CSV (500 employee records)")
    print("    Target   : SQLite (ingested_payroll.db)")
    print("    Chunk    : 100 rows per batch")
    print("    Validate : emp_code required, salary >= 0")
    print("    Errors   : Written to ingestion_errors table\n")

    pipeline = BatchIngestionPipeline(csv_path, db_path)
    stats    = pipeline.run()

    print(f"\n  Final Stats:")
    for k,v in stats.items():
        print(f"    {k}: {v}")

    (OUT/"ingestion_stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(f"\n✓ Stats saved: {OUT}/ingestion_stats.json")
    return stats

if __name__ == "__main__":
    run()
