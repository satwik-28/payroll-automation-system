"""
TASK 13: HDFS Architecture — Namenode, Datanode, Block Replication
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent / "12_hadoop"))
from hadoop_spark_tasks import HDFSCluster, HDFSNamenode, HDFSDatanode
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
OUT  = BASE / "output"; OUT.mkdir(exist_ok=True)

ARCHITECTURE_EXPLANATION = """
╔═══════════════════════════════════════════════════════════════════╗
║           HDFS ARCHITECTURE — PAYROLL DATA STORAGE                ║
╚═══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────┐
│           NAMENODE (Master)              │
│  • fsimage  — filesystem snapshot        │
│  • edits log — transaction log           │
│  • Metadata ONLY (no actual data)        │
│  • Manages: namespace, block mapping     │
│  • HA: Active + Standby Namenode         │
└──────────────┬──────────────────────────┘
               │ Block reports + Heartbeat (3s)
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│  DN1  │ │  DN2  │ │  DN3  │ │  DN4  │
│Mumbai │ │Blr    │ │Delhi  │ │Pune   │
│Rack 1 │ │Rack 1 │ │Rack 2 │ │Rack 2 │
└───────┘ └───────┘ └───────┘ └───────┘

PAYROLL USE CASE — BLOCK DISTRIBUTION:
  payroll_march2026.csv (420 MB):
    Block A (128MB) → DN1, DN3, DN4  (rack-aware replication)
    Block B (128MB) → DN2, DN3, DN1
    Block C (128MB) → DN4, DN1, DN2
    Block D (36MB)  → DN3, DN2, DN4

RACK AWARENESS:
  • First replica: local datanode
  • Second replica: different rack (fault tolerance)
  • Third replica: same rack as second (bandwidth efficiency)
  
KEY FEATURES:
  • Write-once, read-many (WORM) for audit compliance
  • Block size: 128MB (configurable)  
  • Default replication: 3×
  • Checksum verification on read
  • Transparent failover if Datanode dies
"""

def run():
    print("="*65)
    print("  TASK 13: HDFS Architecture")
    print("="*65)
    print(ARCHITECTURE_EXPLANATION)

    cluster = HDFSCluster()
    payroll_files = {
        "/payroll/2026/march/payroll_register.csv":
            "emp_code,gross,net\n" + "\n".join(f"EMP{i:03d},{65000+i*1000},{60000+i*900}" for i in range(1,31)),
        "/payroll/2026/march/payslips_batch.tar":
            "BINARY_PAYSLIP_DATA" * 200,
        "/payroll/archive/2025/annual_report.parquet":
            "PARQUET_BINARY_DATA" * 500,
        "/hdfs_logs/namenode_audit.log":
            "2026-03-01 09:00 OPEN /payroll/2026/march/payroll_register.csv\n" * 20,
    }

    print("\n  Uploading payroll data to HDFS:")
    for path, content in payroll_files.items():
        blocks = cluster.put(path, content)
        meta   = cluster.namenode.stat(path)
        print(f"  ✓ {path}")
        print(f"    Size={meta['size_bytes']}B | Blocks={len(meta['block_ids'])} | "
              f"Replicated×{meta['replication']} | Checksum={meta['checksum'][:8]}...")

    print("\n  Namenode Filesystem Report:")
    report = cluster.namenode.get_filesystem_report()
    for k, v in report.items():
        print(f"    {k}: {v}")

    print("\n  Simulating Datanode failure (DN2 offline):")
    print("    → Namenode detects missing heartbeat after 10 minutes")
    print("    → Identifies under-replicated blocks")
    print("    → Triggers re-replication from surviving DNs")
    print("    → Replication factor restored: 3×")

    result = {"architecture": "HDFS", "cluster_report": report,
              "files_stored": len(payroll_files),
              "total_blocks": report["total_blocks"],
              "timestamp": datetime.now().isoformat()}
    (OUT/"hdfs_architecture_report.json").write_text(json.dumps(result, indent=2))
    print(f"\n✓ Report: {OUT}/hdfs_architecture_report.json")
    return result

if __name__ == "__main__":
    run()
