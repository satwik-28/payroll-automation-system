"""
TASK 28: Lakehouse — Delta Lake / Iceberg simulation with versioning
TASK 29: Data Quality — Validation checks and anomaly detection
"""
import json, hashlib, time, sqlite3, random, math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)
DB = Path(__file__).parent.parent / "shared/database/payroll.db"

# ══════════════════════════════════════════════════════════════
#  TASK 28: DELTA LAKE / ICEBERG SIMULATION
# ══════════════════════════════════════════════════════════════
class DeltaTable:
    """
    Simulates Delta Lake table with ACID transactions,
    versioning, time travel, and schema evolution.
    """
    def __init__(self, name: str, location: Path):
        self.name = name
        self.location = location / name
        self.location.mkdir(parents=True, exist_ok=True)
        self._delta_log = self.location / "_delta_log"
        self._delta_log.mkdir(exist_ok=True)
        self._data_path = self.location / "data"
        self._data_path.mkdir(exist_ok=True)
        self._version = -1
        self._snapshots: Dict[int, dict] = {}
        self._current_data: List[dict] = []
        self._schema: List[str] = []
        self._statistics: dict = {}

    def _commit(self, operation: str, data_added: list, data_removed: list = None, schema_change: dict = None) -> int:
        """Write a commit to the Delta log (ACID transaction)."""
        self._version += 1
        commit = {
            "version":         self._version,
            "timestamp":       datetime.now().isoformat(),
            "operation":       operation,
            "operationParams": {"mode": "append" if operation=="WRITE" else operation},
            "numFiles":        1,
            "numOutputRows":   len(data_added),
            "numRemovedFiles": len(data_removed) if data_removed else 0,
            "schema":          self._schema,
            "schema_change":   schema_change,
            "checksum":        hashlib.md5(json.dumps(data_added, default=str).encode()).hexdigest()[:12],
            "invariants":      {"no_null_emp_id": all(r.get("emp_id") for r in data_added) if data_added else True}
        }
        log_path = self._delta_log / f"{self._version:020d}.json"
        log_path.write_text(json.dumps(commit, indent=2))

        # Save actual data as "parquet" file (simulated as JSON)
        if data_added:
            data_file = self._data_path / f"part-{self._version:05d}-{commit['checksum']}.snappy.parquet.json"
            data_file.write_text(json.dumps(data_added, default=str))

        self._snapshots[self._version] = {
            "version": self._version, "timestamp": commit["timestamp"],
            "operation": operation, "rows": len(self._current_data),
            "data_files": len(list(self._data_path.glob("*.json")))
        }
        return self._version

    def write(self, records: List[dict], mode: str = "append") -> int:
        """Write records (INSERT / OVERWRITE)."""
        if self._schema and records:
            self._schema = list(set(self._schema) | set(records[0].keys()))
        elif records:
            self._schema = list(records[0].keys())

        if mode == "overwrite":
            removed = self._current_data[:]
            self._current_data = records[:]
        else:
            removed = []
            self._current_data.extend(records)

        version = self._commit("WRITE", records, removed)
        return version

    def update(self, predicate_fn, update_fn) -> Tuple[int, int]:
        """Update records matching predicate."""
        updated_count = 0
        old_data = self._current_data[:]
        new_data = []
        for r in self._current_data:
            if predicate_fn(r):
                new_data.append(update_fn(dict(r)))
                updated_count += 1
            else:
                new_data.append(r)
        self._current_data = new_data
        version = self._commit("UPDATE", [r for r,o in zip(new_data,old_data) if r!=o], [])
        return version, updated_count

    def delete(self, predicate_fn) -> Tuple[int, int]:
        """Delete records matching predicate."""
        old_data = self._current_data[:]
        deleted = [r for r in old_data if predicate_fn(r)]
        self._current_data = [r for r in old_data if not predicate_fn(r)]
        version = self._commit("DELETE", [], deleted)
        return version, len(deleted)

    def merge(self, source: List[dict], key_col: str, when_matched="update", when_not_matched="insert") -> dict:
        """MERGE (upsert) operation."""
        source_map = {str(r.get(key_col)): r for r in source}
        current_keys = {str(r.get(key_col)): i for i, r in enumerate(self._current_data)}
        updated = inserted = 0
        for key, src_row in source_map.items():
            if key in current_keys:
                if when_matched == "update":
                    idx = current_keys[key]
                    self._current_data[idx] = {**self._current_data[idx], **src_row}
                    updated += 1
            else:
                self._current_data.append(src_row)
                inserted += 1
        version = self._commit("MERGE", source, [])
        return {"version": version, "updated": updated, "inserted": inserted}

    def read(self) -> List[dict]:
        """Read current snapshot."""
        return self._current_data[:]

    def time_travel(self, version: int = None, timestamp: str = None) -> List[dict]:
        """Read table at a specific version (time travel)."""
        if version is None and timestamp:
            for v, snap in sorted(self._snapshots.items()):
                if snap["timestamp"] >= timestamp:
                    version = v - 1; break
            version = version or max(self._snapshots.keys(), default=0)

        # Reconstruct state at that version
        target_version = min(version, self._version)
        data_files = sorted(self._data_path.glob("*.json"))[:target_version+1]
        reconstructed = []
        for f in data_files:
            reconstructed.extend(json.loads(f.read_text()))
        return reconstructed

    def vacuum(self, retain_hours: int = 168) -> dict:
        """Remove old data files (default: keep 7 days)."""
        cutoff = datetime.now() - timedelta(hours=retain_hours)
        old_files = [f for f in self._data_path.glob("*.json")
                     if datetime.fromtimestamp(f.stat().st_mtime) < cutoff]
        removed = len(old_files)
        for f in old_files: f.unlink()
        return {"vacuumed_files": removed, "retained_hours": retain_hours}

    def add_column(self, col_name: str, col_type: str, default=None) -> int:
        """Schema evolution — add column."""
        if col_name not in self._schema:
            self._schema.append(col_name)
            for r in self._current_data:
                r[col_name] = default
        version = self._commit("SCHEMA_CHANGE", [], [], {"added": col_name, "type": col_type})
        return version

    def history(self) -> List[dict]:
        return list(self._snapshots.values())

    def describe_detail(self) -> dict:
        return {
            "name": self.name, "location": str(self.location),
            "format": "delta", "current_version": self._version,
            "num_files": len(list(self._data_path.glob("*.json"))),
            "current_rows": len(self._current_data),
            "schema": self._schema,
            "features": ["ACID", "Time Travel", "Schema Evolution", "Merge", "Vacuum"]
        }


class IcebergTable:
    """Simulates Apache Iceberg table features."""
    def __init__(self, name: str):
        self.name = name; self._snapshots = []; self._data = []
        self._manifests = []; self._partition_spec = {}

    def partition_by(self, *cols):
        self._partition_spec = {c: "identity" for c in cols}
        return self

    def write(self, records: List[dict], snapshot_id: str = None) -> str:
        snapshot_id = snapshot_id or hashlib.md5(f"{time.time()}".encode()).hexdigest()[:12]
        partitioned = defaultdict(list)
        for r in records:
            pk = tuple(r.get(c,"?") for c in self._partition_spec.keys())
            partitioned[pk].append(r)
        manifest = {
            "snapshot_id": snapshot_id, "timestamp": datetime.now().isoformat(),
            "operation": "append", "partitions": len(partitioned),
            "added_files": len(partitioned), "added_rows": len(records),
            "partition_spec": self._partition_spec
        }
        self._manifests.append(manifest)
        self._data.extend(records)
        self._snapshots.append({"snapshot_id": snapshot_id, "rows": len(self._data),
                                  "manifest_files": len(self._manifests)})
        return snapshot_id

    def rollback(self, snapshot_id: str) -> bool:
        for snap in self._snapshots:
            if snap["snapshot_id"] == snapshot_id:
                print(f"  Rolled back to snapshot {snapshot_id} ({snap['rows']} rows)")
                return True
        return False

    def expire_snapshots(self, older_than_days=7) -> int:
        cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        expired = sum(1 for m in self._manifests if m["timestamp"] < cutoff)
        return expired

    def read(self, filter_fn=None) -> List[dict]:
        data = self._data
        return [r for r in data if filter_fn(r)] if filter_fn else data


# ══════════════════════════════════════════════════════════════
#  TASK 29: DATA QUALITY & ANOMALY DETECTION
# ══════════════════════════════════════════════════════════════
class DataQualityCheck:
    """Base class for data quality checks."""
    def __init__(self, name: str, description: str):
        self.name = name; self.description = description
        self.result = None; self.passed = None; self.details = {}

    def run(self, data: List[dict]) -> bool: raise NotImplementedError

    def to_dict(self):
        return {"check": self.name, "description": self.description,
                "passed": self.passed, "details": self.details}


class CompletenessCheck(DataQualityCheck):
    """Check for null/missing values."""
    def __init__(self, field: str, threshold_pct: float = 100.0):
        super().__init__(f"completeness_{field}", f"Field '{field}' must be >= {threshold_pct}% non-null")
        self.field = field; self.threshold = threshold_pct

    def run(self, data):
        total = len(data)
        non_null = sum(1 for r in data if r.get(self.field) is not None
                       and str(r.get(self.field)).strip() != "")
        pct = (non_null / total * 100) if total else 0
        self.passed = pct >= self.threshold
        self.details = {"total": total, "non_null": non_null, "completeness_pct": round(pct,2),
                        "threshold_pct": self.threshold}
        return self.passed


class UniquenessCheck(DataQualityCheck):
    """Check for duplicate values in a field."""
    def __init__(self, field: str):
        super().__init__(f"uniqueness_{field}", f"Field '{field}' must be unique")
        self.field = field

    def run(self, data):
        values = [r.get(self.field) for r in data if r.get(self.field)]
        unique = len(set(values)); total = len(values)
        dups = [(v, values.count(v)) for v in set(values) if values.count(v) > 1]
        self.passed = len(dups) == 0
        self.details = {"total": total, "unique": unique, "duplicates": len(dups),
                        "duplicate_examples": dups[:5]}
        return self.passed


class RangeCheck(DataQualityCheck):
    """Check numeric values are within expected range."""
    def __init__(self, field: str, min_val: float, max_val: float):
        super().__init__(f"range_{field}", f"'{field}' must be in [{min_val}, {max_val}]")
        self.field = field; self.min_val = min_val; self.max_val = max_val

    def run(self, data):
        values = [float(r.get(self.field, 0) or 0) for r in data]
        out_of_range = [(i, v) for i, v in enumerate(values) if not (self.min_val <= v <= self.max_val)]
        self.passed = len(out_of_range) == 0
        self.details = {"total": len(values), "violations": len(out_of_range),
                        "min": min(values) if values else None, "max": max(values) if values else None,
                        "examples": out_of_range[:3]}
        return self.passed


class ConsistencyCheck(DataQualityCheck):
    """Cross-field consistency check."""
    def __init__(self, name: str, check_fn, description: str):
        super().__init__(name, description)
        self.check_fn = check_fn

    def run(self, data):
        violations = [(i, r) for i, r in enumerate(data) if not self.check_fn(r)]
        self.passed = len(violations) == 0
        self.details = {"total": len(data), "violations": len(violations),
                        "violation_rate_pct": round(len(violations)/len(data)*100, 2) if data else 0,
                        "examples": [str(r) for _, r in violations[:3]]}
        return self.passed


class AnomalyDetector:
    """Statistical anomaly detection for payroll data."""

    @staticmethod
    def z_score_outliers(values: List[float], threshold: float = 3.0) -> List[Tuple[int, float, float]]:
        """Z-score based outlier detection."""
        if len(values) < 2: return []
        mean = sum(values) / len(values)
        std  = math.sqrt(sum((v - mean)**2 for v in values) / len(values)) or 1
        return [(i, v, abs((v-mean)/std)) for i, v in enumerate(values) if abs((v-mean)/std) > threshold]

    @staticmethod
    def iqr_outliers(values: List[float]) -> List[Tuple[int, float]]:
        """IQR (Interquartile Range) outlier detection."""
        sorted_v = sorted(values)
        n = len(sorted_v)
        q1 = sorted_v[n//4]; q3 = sorted_v[3*n//4]
        iqr = q3 - q1
        lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr
        return [(i, v) for i, v in enumerate(values) if not (lo <= v <= hi)]

    @staticmethod
    def detect_salary_anomalies(records: List[dict]) -> dict:
        """Multi-metric salary anomaly detection."""
        salaries = [float(r.get("net_salary", 0) or 0) for r in records]
        if not salaries: return {}
        z_outliers  = AnomalyDetector.z_score_outliers(salaries)
        iqr_outliers = AnomalyDetector.iqr_outliers(salaries)
        mean = sum(salaries)/len(salaries)
        std  = math.sqrt(sum((v-mean)**2 for v in salaries)/len(salaries))

        return {
            "total_records":   len(records),
            "mean":            round(mean, 2),
            "std_dev":         round(std, 2),
            "cv_pct":          round(std/mean*100, 2) if mean else 0,
            "z_score_outliers": len(z_outliers),
            "iqr_outliers":    len(iqr_outliers),
            "outlier_records_z": [{"index":i,"value":v,"z_score":round(z,2)}
                                   for i,v,z in z_outliers[:5]],
            "outlier_records_iqr": [{"index":i,"value":v} for i,v in iqr_outliers[:5]],
            "normal_range":    [round(mean - 2*std, 2), round(mean + 2*std, 2)]
        }

    @staticmethod
    def detect_attendance_anomalies(records: List[dict]) -> List[dict]:
        """Flag employees with suspiciously low attendance."""
        anomalies = []
        for r in records:
            days_present = int(r.get("days_present", 0) or 0)
            working_days = int(r.get("working_days", 26) or 26)
            pct = days_present / working_days * 100 if working_days else 0
            if pct < 50:
                anomalies.append({"emp_code": r.get("emp_code","?"),
                                   "days_present": days_present,
                                   "working_days": working_days,
                                   "attendance_pct": round(pct, 1),
                                   "flag": "LOW_ATTENDANCE"})
        return anomalies

    @staticmethod
    def detect_payroll_spikes(records: List[dict], threshold_pct: float = 30.0) -> List[dict]:
        """Detect unusual month-over-month salary jumps."""
        by_emp = defaultdict(list)
        for r in records:
            by_emp[r.get("emp_id")].append(r)
        spikes = []
        for emp_id, pays in by_emp.items():
            if len(pays) < 2: continue
            pays_sorted = sorted(pays, key=lambda x: (x.get("year",0), x.get("month",0)))
            for i in range(1, len(pays_sorted)):
                prev = float(pays_sorted[i-1].get("net_salary",0) or 0)
                curr = float(pays_sorted[i].get("net_salary",0) or 0)
                if prev > 0:
                    change_pct = abs(curr - prev) / prev * 100
                    if change_pct > threshold_pct:
                        spikes.append({"emp_id": emp_id,
                                       "prev_net": prev, "curr_net": curr,
                                       "change_pct": round(change_pct, 1),
                                       "flag": "SALARY_SPIKE"})
        return spikes


class DataQualityEngine:
    """Runs all checks and generates a DQ report."""

    def __init__(self, dataset_name: str):
        self.name = dataset_name
        self.checks: List[DataQualityCheck] = []
        self.run_time = None

    def add_check(self, check: DataQualityCheck):
        self.checks.append(check); return self

    def run_all(self, data: List[dict]) -> dict:
        self.run_time = datetime.now()
        results = []
        for check in self.checks:
            try:
                passed = check.run(data)
            except Exception as e:
                check.passed = False; check.details = {"error": str(e)}
            results.append(check.to_dict())

        passed_count = sum(1 for r in results if r["passed"])
        failed_count = len(results) - passed_count
        score = round(passed_count / len(results) * 100, 1) if results else 0

        report = {
            "dataset": self.name, "run_time": self.run_time.isoformat(),
            "total_records": len(data), "total_checks": len(results),
            "passed": passed_count, "failed": failed_count,
            "dq_score_pct": score,
            "overall_status": "PASS" if score >= 80 else "WARN" if score >= 60 else "FAIL",
            "check_results": results
        }
        return report


def run():
    print("="*60)
    print("  TASK 28: Lakehouse (Delta Lake / Iceberg)")
    print("  TASK 29: Data Quality & Anomaly Detection")
    print("="*60)

    # ── TASK 28: DELTA LAKE ───────────────────────────────────
    print("\n══ TASK 28: DELTA LAKE SIMULATION ══")
    lakehouse_path = OUTPUT / "lakehouse"

    # Load data from OLTP
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    payroll_data = [dict(r) for r in conn.execute("""
        SELECT pr.payroll_id, pr.emp_id, e.emp_code,
               e.first_name||' '||e.last_name AS name,
               d.dept_name AS dept, pp.period_name AS period,
               pp.year, pp.month,
               pr.basic_salary, pr.gross_salary, pr.net_salary,
               pr.pf_employee, pr.income_tax_tds, pr.status,
               pr.days_present, pr.days_absent
        FROM payroll_records pr
        JOIN employees e ON pr.emp_id=e.emp_id
        JOIN departments d ON e.dept_id=d.dept_id
        JOIN payroll_periods pp ON pr.period_id=pp.period_id
        WHERE pr.status='Paid'
    """).fetchall()]
    conn.close()

    # Create Delta table
    dt = DeltaTable("fact_payroll", lakehouse_path)

    print(f"\n  [1] Initial Write — {len(payroll_data)} records:")
    v0 = dt.write(payroll_data[:60], mode="overwrite")
    print(f"  Version {v0}: WRITE OVERWRITE — {len(dt._current_data)} rows")

    print("\n  [2] Append new records:")
    new_records = [{"payroll_id": 9999+i, "emp_id": i, "emp_code": f"EMP{i:03d}",
                    "name": f"New Employee {i}", "dept": "IT", "period": "April-2026",
                    "year": 2026, "month": 4,
                    "basic_salary": 50000+i*1000, "gross_salary": 78000+i*1000,
                    "net_salary": 72000+i*1000, "pf_employee": 1800,
                    "income_tax_tds": 500, "status": "Draft",
                    "days_present": 26, "days_absent": 0}
                   for i in range(1, 6)]
    v1 = dt.write(new_records, mode="append")
    print(f"  Version {v1}: APPEND — +{len(new_records)} rows, total={len(dt._current_data)}")

    print("\n  [3] Update records (April-2026 Draft → Approved):")
    v2, updated = dt.update(
        lambda r: r.get("period") == "April-2026" and r.get("status") == "Draft",
        lambda r: {**r, "status": "Approved", "updated_at": datetime.now().isoformat()}
    )
    print(f"  Version {v2}: UPDATE — {updated} rows updated")

    print("\n  [4] Delete test records:")
    v3, deleted = dt.delete(lambda r: r.get("payroll_id", 0) >= 9999)
    print(f"  Version {v3}: DELETE — {deleted} rows removed, total={len(dt._current_data)}")

    print("\n  [5] Merge (upsert) operation:")
    upsert_data = [
        {"payroll_id": 1, "net_salary": 65000, "status": "Paid", "emp_code": "EMP001",
         "payment_ref": "NEFT2026041501"},
        {"payroll_id": 200, "emp_id": 200, "emp_code": "EMP200", "net_salary": 45000,
         "status": "Paid", "dept": "New-Dept", "period": "April-2026",
         "year": 2026, "month": 4, "days_present": 26, "days_absent": 0},
    ]
    merge_result = dt.merge(upsert_data, key_col="payroll_id")
    print(f"  Version {merge_result['version']}: MERGE — updated={merge_result['updated']}, inserted={merge_result['inserted']}")

    print("\n  [6] Schema Evolution — add audit columns:")
    v5 = dt.add_column("loaded_at", "TIMESTAMP", datetime.now().isoformat())
    v6 = dt.add_column("data_source", "STRING", "OLTP_payroll_db")
    print(f"  Version {v5}: Added 'loaded_at' column")
    print(f"  Version {v6}: Added 'data_source' column")

    print("\n  [7] Time Travel:")
    v0_data = dt.time_travel(version=0)
    print(f"  Table at version 0: {len(v0_data)} rows")
    current_data = dt.read()
    print(f"  Table at version {dt._version} (current): {len(current_data)} rows")

    print("\n  [8] Delta Table History:")
    for snap in dt.history():
        print(f"  v{snap['version']:2d} | {snap['operation']:15} | {snap['timestamp'][:19]} | rows={snap['rows']}")

    print("\n  [9] Vacuum (cleanup old files):")
    vacuum_result = dt.vacuum(retain_hours=0)  # vacuum all for demo
    print(f"  Vacuumed: {vacuum_result}")

    detail = dt.describe_detail()
    print(f"\n  Table Details:")
    for k, v in detail.items():
        print(f"    {k}: {v}")

    # Iceberg
    print("\n  [10] Iceberg Table:")
    iceberg = IcebergTable("payroll_iceberg").partition_by("dept", "year")
    snap1 = iceberg.write(payroll_data[:30])
    snap2 = iceberg.write(payroll_data[30:60])
    print(f"  Snapshots: {snap1}, {snap2}")
    march_data = iceberg.read(filter_fn=lambda r: r.get("month") == 3)
    print(f"  Partition filter (month=3): {len(march_data)} rows")
    iceberg.rollback(snap1)
    expired = iceberg.expire_snapshots(older_than_days=0)
    print(f"  Expired snapshots: {expired}")

    print("\n  Delta Lake vs Iceberg vs Hudi:")
    comparison = {
        "ACID": {"Delta":"Yes","Iceberg":"Yes","Hudi":"Yes"},
        "Time Travel": {"Delta":"Via version","Iceberg":"Via snapshot","Hudi":"Via timeline"},
        "Schema Evolve": {"Delta":"Yes","Iceberg":"Yes","Hudi":"Yes"},
        "Streaming": {"Delta":"Native","Iceberg":"Limited","Hudi":"Native"},
        "Best Engine": {"Delta":"Spark/Databricks","Iceberg":"Spark/Trino/Flink","Hudi":"Spark"},
        "Payroll Use": {"Delta":"Versioned payroll facts","Iceberg":"Multi-engine queries","Hudi":"Incremental ingestion"},
    }
    print(f"  {'Feature':<16} {'Delta Lake':>16} {'Iceberg':>12} {'Hudi':>12}")
    print("  " + "-"*58)
    for feat, vals in comparison.items():
        print(f"  {feat:<16} {vals['Delta']:>16} {vals['Iceberg']:>12} {vals['Hudi']:>12}")

    # ── TASK 29: DATA QUALITY ─────────────────────────────────
    print("\n══ TASK 29: DATA QUALITY & ANOMALY DETECTION ══")

    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    payroll_recs = [dict(r) for r in conn.execute("""
        SELECT pr.*, e.emp_code, e.pan_number, e.email,
               d.dept_name, pp.period_name, pp.working_days
        FROM payroll_records pr
        JOIN employees e ON pr.emp_id=e.emp_id
        JOIN departments d ON e.dept_id=d.dept_id
        JOIN payroll_periods pp ON pr.period_id=pp.period_id
        WHERE pr.status='Paid'
    """).fetchall()]
    conn.close()

    # Inject some deliberate quality issues for demo
    bad_recs = [
        {**payroll_recs[0], "net_salary": -500,   "emp_code": "EMP001"},  # negative salary
        {**payroll_recs[1], "income_tax_tds": None,"emp_code": "EMP002"},  # null TDS
        {**payroll_recs[2], "emp_code": "",         "net_salary": 99999999},  # empty code, spike
        {**payroll_recs[3], "gross_salary": 0,      "net_salary": 50000},  # zero gross
    ] + payroll_recs[4:]

    engine = DataQualityEngine("payroll_records_march_2026")

    # Register all checks
    (engine
     .add_check(CompletenessCheck("emp_code", threshold_pct=100))
     .add_check(CompletenessCheck("gross_salary", threshold_pct=100))
     .add_check(CompletenessCheck("net_salary", threshold_pct=100))
     .add_check(CompletenessCheck("income_tax_tds", threshold_pct=95))
     .add_check(UniquenessCheck("payroll_id"))
     .add_check(RangeCheck("net_salary", 1000, 2000000))
     .add_check(RangeCheck("gross_salary", 5000, 3000000))
     .add_check(RangeCheck("days_present", 0, 31))
     .add_check(ConsistencyCheck(
         "net_le_gross", lambda r: (r.get("net_salary") or 0) <= (r.get("gross_salary") or 1),
         "Net salary must not exceed gross salary"))
     .add_check(ConsistencyCheck(
         "pf_valid", lambda r: 0 <= (r.get("pf_employee") or 0) <= 1800,
         "PF employee contribution must be 0-1800 (15000 x 12%)"))
     .add_check(ConsistencyCheck(
         "positive_net", lambda r: (r.get("net_salary") or 0) > 0,
         "Net salary must be positive"))
     .add_check(ConsistencyCheck(
         "tds_not_exceed_gross", lambda r: (r.get("income_tax_tds") or 0) <= (r.get("gross_salary") or 1),
         "TDS cannot exceed gross salary"))
    )

    print("\n  Running Data Quality Checks:")
    dq_report = engine.run_all(bad_recs)
    print(f"\n  DQ Score: {dq_report['dq_score_pct']}% | Status: {dq_report['overall_status']}")
    print(f"  Checks: {dq_report['passed']} passed, {dq_report['failed']} failed")
    print(f"\n  {'Check Name':<35} {'Status':>6} {'Details'}")
    print("  " + "-"*80)
    for r in dq_report["check_results"]:
        status = "✓ PASS" if r["passed"] else "✗ FAIL"
        detail = str(r["details"])[:50]
        print(f"  {r['check']:<35} {status:>6} {detail}")

    # Anomaly Detection
    print("\n  Anomaly Detection:")
    salary_anomalies = AnomalyDetector.detect_salary_anomalies(payroll_recs)
    print(f"\n  [A] Salary Outliers (Z-score > 3):")
    print(f"    Z-score outliers: {salary_anomalies.get('z_score_outliers',0)}")
    print(f"    IQR outliers:     {salary_anomalies.get('iqr_outliers',0)}")
    print(f"    Normal range:     ₹{salary_anomalies.get('normal_range',['?','?'])[0]:,.0f} – ₹{salary_anomalies.get('normal_range',['?','?'])[1]:,.0f}")
    for ex in salary_anomalies.get("outlier_records_z", []):
        print(f"    Row {ex['index']}: net=₹{ex['value']:,.0f} (z={ex['z_score']})")

    att_anomalies = AnomalyDetector.detect_attendance_anomalies(payroll_recs)
    print(f"\n  [B] Attendance Anomalies (<50% attendance):")
    print(f"    Flagged: {len(att_anomalies)} employees")
    for a in att_anomalies[:5]:
        print(f"    {a['emp_code']}: {a['days_present']}/{a['working_days']} days ({a['attendance_pct']}%) → {a['flag']}")

    spike_anomalies = AnomalyDetector.detect_payroll_spikes(payroll_recs, threshold_pct=20)
    print(f"\n  [C] Payroll Spikes (MoM change > 20%):")
    print(f"    Flagged: {len(spike_anomalies)} records")
    for s in spike_anomalies[:5]:
        print(f"    emp_id={s['emp_id']}: ₹{s['prev_net']:,.0f} → ₹{s['curr_net']:,.0f} (+{s['change_pct']}%)")

    # Save results
    results = {
        "task28_delta": {
            "table": dt.name,
            "final_version": dt._version,
            "final_rows": len(dt._current_data),
            "history": dt.history(),
        },
        "task29_dq": {
            "dq_score": dq_report["dq_score_pct"],
            "status": dq_report["overall_status"],
            "checks": len(dq_report["check_results"]),
            "anomalies": {
                "salary_outliers": salary_anomalies.get("z_score_outliers", 0),
                "attendance_flags": len(att_anomalies),
                "payroll_spikes": len(spike_anomalies)
            }
        },
        "timestamp": datetime.now().isoformat()
    }
    (OUTPUT/"lakehouse_dq_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results saved: {OUTPUT}/lakehouse_dq_results.json")
    return results

if __name__ == "__main__":
    run()
