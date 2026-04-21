"""
TASK 01: Linux + File System — Python Implementation
Payroll Data Pipeline Directory Setup, Permissions & Logging
"""
import os, shutil, stat, logging, json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
PROJECT = BASE / "payroll_pipeline"
LOG_FILE = BASE / "pipeline_operations.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

DIRS = [
    "raw/employees", "raw/payroll", "raw/attendance", "raw/loans",
    "processed/cleaned", "processed/transformed", "processed/aggregated",
    f"archive/{datetime.now().year}/{datetime.now().month:02d}",
    "output/reports", "output/exports",
    "logs/pipeline", "logs/errors",
    "config", "scripts", "temp", "quarantine", "backup"
]

PERMISSIONS = {
    "raw":        0o755,
    "processed":  0o755,
    "output":     0o755,
    "config":     0o700,
    "scripts":    0o755,
    "logs":       0o755,
    "quarantine": 0o750,
    "backup":     0o700,
    "temp":       0o777,
}

SAMPLE_DATA = {
    "raw/employees/employees.csv": (
        "emp_id,emp_code,first_name,last_name,department,basic_salary,status\n"
        "1,EMP001,Rajesh,Kumar,HR,45000,Active\n"
        "2,EMP002,Priya,Sharma,HR,125000,Active\n"
        "3,EMP003,Amit,Patel,IT,65000,Active\n"
        "4,EMP004,Sneha,Reddy,Support,30000,Active\n"
        "5,EMP005,Vikram,Singh,Sales,38000,Active\n"
    ),
    "raw/payroll/payroll_202603.csv": (
        "payroll_id,emp_id,period,gross_salary,net_salary,status\n"
        "1,1,March-2026,64900,62363.33,Paid\n"
        "2,2,March-2026,197500,172166.67,Paid\n"
        "3,3,March-2026,97266.67,91581.67,Paid\n"
    ),
    "raw/attendance/attendance_202603.csv": (
        "emp_id,att_date,status,hours_worked\n"
        "1,2026-03-01,Present,9.5\n"
        "1,2026-03-02,Present,9.0\n"
        "2,2026-03-01,Present,10.0\n"
    ),
    "config/pipeline.json": json.dumps({
        "version": "1.0",
        "batch_size": 1000,
        "log_level": "INFO",
        "archive_days": 30,
        "quarantine_threshold_bytes": 10
    }, indent=2)
}

def setup_directories():
    log.info("Creating directory structure...")
    for d in DIRS:
        path = PROJECT / d
        path.mkdir(parents=True, exist_ok=True)
        log.info(f"  Created: {path.relative_to(BASE)}")

def set_permissions():
    log.info("Setting file permissions...")
    for folder, perm in PERMISSIONS.items():
        path = PROJECT / folder
        if path.exists():
            os.chmod(path, perm)
            log.info(f"  {folder}/ → {oct(perm)}")

def create_sample_files():
    log.info("Creating sample data files...")
    for rel_path, content in SAMPLE_DATA.items():
        fp = PROJECT / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        log.info(f"  Created: {rel_path} ({fp.stat().st_size} bytes)")

def automate_file_movement():
    log.info("Automating file movement (raw → processed)...")
    moved, quarantined = 0, 0
    for raw_file in (PROJECT / "raw").rglob("*.csv"):
        size = raw_file.stat().st_size
        dest_dir = PROJECT / "processed" / "cleaned"
        dest = dest_dir / raw_file.name
        if size > 0:
            shutil.copy2(raw_file, dest)
            log.info(f"  Moved: {raw_file.name} → processed/cleaned/ ({size}B)")
            moved += 1
        else:
            shutil.copy2(raw_file, PROJECT / "quarantine" / raw_file.name)
            log.warning(f"  Quarantined (empty): {raw_file.name}")
            quarantined += 1
    log.info(f"Movement complete. Moved={moved}, Quarantined={quarantined}")
    return moved, quarantined

def archive_old_files():
    log.info("Archiving processed files...")
    archive_dir = PROJECT / f"archive/{datetime.now().year}/{datetime.now().month:02d}"
    count = 0
    for f in (PROJECT / "processed" / "cleaned").glob("*.csv"):
        shutil.copy2(f, archive_dir / f.name)
        log.info(f"  Archived: {f.name}")
        count += 1
    log.info(f"Archived {count} files.")

def generate_report():
    report = {
        "timestamp": datetime.now().isoformat(),
        "project_dir": str(PROJECT),
        "files": {
            "raw":       sum(1 for _ in (PROJECT/"raw").rglob("*") if _.is_file()),
            "processed": sum(1 for _ in (PROJECT/"processed").rglob("*") if _.is_file()),
            "archived":  sum(1 for _ in (PROJECT/"archive").rglob("*") if _.is_file()),
            "quarantine":sum(1 for _ in (PROJECT/"quarantine").rglob("*") if _.is_file()),
        },
        "disk_usage_bytes": sum(f.stat().st_size for f in PROJECT.rglob("*") if f.is_file()),
        "status": "SUCCESS"
    }
    rpt_path = PROJECT / f"logs/pipeline/report_{datetime.now():%Y%m%d_%H%M%S}.json"
    rpt_path.write_text(json.dumps(report, indent=2))
    log.info(f"Report saved: {rpt_path.relative_to(BASE)}")

    print("\n" + "="*55)
    print("  PIPELINE REPORT")
    print("="*55)
    for k, v in report.items():
        print(f"  {k:20}: {v}")
    return report

def run():
    print("="*55)
    print("  TASK 01: Linux + File System")
    print("="*55)
    setup_directories()
    set_permissions()
    create_sample_files()
    m, q = automate_file_movement()
    archive_old_files()
    report = generate_report()
    print(f"\n✓ Pipeline complete | Log: {LOG_FILE}")
    return report

if __name__ == "__main__":
    run()
