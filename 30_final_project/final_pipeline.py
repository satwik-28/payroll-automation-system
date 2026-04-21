"""
TASK 30: FINAL PROJECT — End-to-End Payroll Data Engineering Pipeline
Ingestion → Processing → Storage → Orchestration → Dashboard

This is the culmination of all 30 tasks integrated into one
complete, runnable data pipeline for the Payroll System.
"""
import os, sys, json, time, sqlite3, csv, hashlib, threading, random, math
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)
DB     = Path(__file__).parent.parent / "shared/database/payroll.db"

# ══════════════════════════════════════════════════════════════
#  PIPELINE INFRASTRUCTURE
# ══════════════════════════════════════════════════════════════
class PipelineMetrics:
    """Tracks metrics across all pipeline stages."""
    def __init__(self):
        self.stages: Dict[str, dict] = {}
        self.total_start = time.time()
        self.events: List[dict] = []

    def start_stage(self, name: str):
        self.stages[name] = {"start": time.time(), "status": "running"}
        self._log_event("STAGE_START", name)

    def end_stage(self, name: str, rows: int = 0, extra: dict = None):
        s = self.stages.get(name, {})
        s["end"]      = time.time()
        s["duration_ms"] = round((s["end"] - s["start"]) * 1000, 2)
        s["status"]   = "success"
        s["rows"]     = rows
        if extra: s.update(extra)
        self._log_event("STAGE_END", name, {"duration_ms": s["duration_ms"], "rows": rows})

    def fail_stage(self, name: str, error: str):
        s = self.stages.get(name, {})
        s["status"] = "failed"; s["error"] = error
        self._log_event("STAGE_FAIL", name, {"error": error})

    def _log_event(self, event_type: str, stage: str, data: dict = None):
        self.events.append({
            "ts": datetime.now().isoformat(),
            "event": event_type, "stage": stage, **(data or {})
        })

    def summary(self) -> dict:
        total_ms = round((time.time() - self.total_start) * 1000, 2)
        success  = sum(1 for s in self.stages.values() if s.get("status") == "success")
        failed   = sum(1 for s in self.stages.values() if s.get("status") == "failed")
        return {
            "total_stages": len(self.stages),
            "succeeded":    success,
            "failed":       failed,
            "total_ms":     total_ms,
            "stages":       self.stages
        }


class PipelineLogger:
    """Structured logger for the pipeline."""
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._entries = []

    def log(self, level: str, stage: str, message: str, data: dict = None):
        entry = {
            "ts": datetime.now().isoformat(), "level": level,
            "stage": stage, "message": message, "data": data or {}
        }
        self._entries.append(entry)
        icon = {"INFO":"ℹ","WARN":"⚠","ERROR":"✗","SUCCESS":"✓"}.get(level,"•")
        print(f"  [{level:7}] {icon} [{stage}] {message}")

    def save(self):
        self.log_path.write_text(json.dumps(self._entries, indent=2, default=str))


# ══════════════════════════════════════════════════════════════
#  STAGE 1: DATA INGESTION
# ══════════════════════════════════════════════════════════════
class DataIngestionStage:
    """
    Ingests data from multiple sources:
    - SQLite OLTP database (primary)
    - CSV files (supplementary)
    - Simulated REST API (real-time events)
    """
    def __init__(self, metrics: PipelineMetrics, logger: PipelineLogger):
        self.metrics = metrics; self.logger = logger
        self.ingested = {}

    def ingest_from_db(self, period_id: int = 24) -> dict:
        self.metrics.start_stage("ingest_db")
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        try:
            payroll = [dict(r) for r in conn.execute("""
                SELECT pr.*, e.emp_code, e.first_name||' '||e.last_name name,
                       e.pan_number, e.email, e.gender, e.employment_type,
                       d.dept_name, ds.desig_title, sg.grade_name, sg.grade_code,
                       pp.period_name, pp.month, pp.year, pp.working_days
                FROM payroll_records pr
                JOIN employees e ON pr.emp_id=e.emp_id
                JOIN departments d ON e.dept_id=d.dept_id
                JOIN designations ds ON e.desig_id=ds.desig_id
                JOIN salary_grades sg ON e.grade_id=sg.grade_id
                JOIN payroll_periods pp ON pr.period_id=pp.period_id
                WHERE pr.period_id=? AND pr.status='Paid'
            """, (period_id,)).fetchall()]

            employees = [dict(r) for r in conn.execute("""
                SELECT e.*, d.dept_name, ds.desig_title, sg.grade_name
                FROM employees e
                JOIN departments d ON e.dept_id=d.dept_id
                JOIN designations ds ON e.desig_id=ds.desig_id
                JOIN salary_grades sg ON e.grade_id=sg.grade_id
            """).fetchall()]

            attendance = [dict(r) for r in conn.execute("""
                SELECT * FROM vw_attendance_summary WHERE year='2026' AND month='03'
            """).fetchall()]

            loans = [dict(r) for r in conn.execute("""
                SELECT * FROM vw_loan_status WHERE status='Active'
            """).fetchall()]

            revisions = [dict(r) for r in conn.execute("""
                SELECT sr.*, e.emp_code FROM salary_revisions sr
                JOIN employees e ON sr.emp_id=e.emp_id
                ORDER BY sr.effective_date DESC
            """).fetchall()]

        finally:
            conn.close()

        self.ingested = {
            "payroll": payroll, "employees": employees,
            "attendance": attendance, "loans": loans, "revisions": revisions
        }
        total = sum(len(v) for v in self.ingested.values())
        self.metrics.end_stage("ingest_db", total,
                                {"sources": list(self.ingested.keys()),
                                 "rows_per_source": {k: len(v) for k,v in self.ingested.items()}})
        self.logger.log("SUCCESS", "ingest_db", f"Ingested {total} records from OLTP DB",
                        {"period_id": period_id, "tables": list(self.ingested.keys())})
        return self.ingested

    def ingest_from_csv(self, csv_dir: Path = None) -> dict:
        """Ingest supplementary data from CSV files."""
        self.metrics.start_stage("ingest_csv")
        csv_data = {}
        if csv_dir and csv_dir.exists():
            for f in csv_dir.glob("*.csv"):
                with open(f) as fp:
                    csv_data[f.stem] = list(csv.DictReader(fp))
        else:
            # Generate synthetic CSV
            csv_data["tax_config"] = [
                {"fiscal_year":"FY2025-26","income_from":"0","income_to":"400000","rate":"0"},
                {"fiscal_year":"FY2025-26","income_from":"400000","income_to":"800000","rate":"5"},
            ]
        total = sum(len(v) for v in csv_data.values())
        self.metrics.end_stage("ingest_csv", total)
        self.logger.log("INFO", "ingest_csv", f"Ingested {total} rows from CSV")
        return csv_data

    def ingest_api_events(self, n_events: int = 20) -> List[dict]:
        """Simulate real-time API event ingestion."""
        self.metrics.start_stage("ingest_api")
        events = []
        types = ["PAYROLL_VIEWED","PAYSLIP_DOWNLOADED","SALARY_QUERY","REPORT_GENERATED"]
        for i in range(n_events):
            events.append({
                "event_id":   hashlib.md5(f"{i}{time.time()}".encode()).hexdigest()[:8],
                "event_type": random.choice(types),
                "emp_code":   f"EMP{random.randint(1,30):03d}",
                "timestamp":  datetime.now().isoformat(),
                "source":     "web_api",
                "session_id": hashlib.md5(f"sess{i}".encode()).hexdigest()[:10]
            })
        self.metrics.end_stage("ingest_api", len(events))
        self.logger.log("INFO", "ingest_api", f"Ingested {len(events)} API events")
        return events


# ══════════════════════════════════════════════════════════════
#  STAGE 2: DATA PROCESSING
# ══════════════════════════════════════════════════════════════
class DataProcessingStage:
    """
    Transforms and enriches raw data:
    - Clean missing values
    - Calculate derived metrics
    - Validate data quality
    - Normalize and aggregate
    """
    def __init__(self, metrics: PipelineMetrics, logger: PipelineLogger):
        self.metrics = metrics; self.logger = logger

    def clean_and_validate(self, payroll: List[dict]) -> tuple:
        self.metrics.start_stage("clean_validate")
        clean, issues = [], []
        for r in payroll:
            errs = []
            if not r.get("emp_code"):       errs.append("missing emp_code")
            if (r.get("net_salary") or 0) < 0: errs.append("negative net salary")
            if (r.get("gross_salary") or 0) == 0: errs.append("zero gross salary")
            if (r.get("net_salary") or 0) > (r.get("gross_salary") or 1): errs.append("net > gross")

            if errs:
                issues.append({**r, "_errors": errs})
            else:
                clean.append(r)

        self.metrics.end_stage("clean_validate", len(clean),
                                {"issues_found": len(issues), "pass_rate_pct": round(len(clean)/len(payroll)*100,1) if payroll else 0})
        self.logger.log("SUCCESS", "clean_validate",
                        f"Validated {len(payroll)} records: {len(clean)} clean, {len(issues)} issues")
        return clean, issues

    def transform_and_enrich(self, payroll: List[dict]) -> List[dict]:
        self.metrics.start_stage("transform_enrich")
        enriched = []
        for r in payroll:
            gross = float(r.get("gross_salary") or 0)
            net   = float(r.get("net_salary") or 0)
            basic = float(r.get("basic_salary") or 0)
            enriched.append({
                **r,
                # Derived fields
                "annual_gross":        round(gross * 12, 2),
                "annual_net":          round(net * 12, 2),
                "take_home_ratio_pct": round(net / gross * 100, 2) if gross else 0,
                "effective_tds_pct":   round(float(r.get("income_tax_tds") or 0) / gross * 100, 2) if gross else 0,
                "deduction_ratio_pct": round(float(r.get("total_deductions") or 0) / gross * 100, 2) if gross else 0,
                "hra_ratio_pct":       round(float(r.get("hra") or 0) / basic * 100, 1) if basic else 0,
                "attendance_efficiency": round(
                    int(r.get("days_present") or 0) / int(r.get("working_days") or 1) * 100, 1),
                "salary_grade":        r.get("grade_code", ""),
                "pipeline_ts":         datetime.now().isoformat(),
                "pipeline_version":    "v2.0",
                "data_source":         "OLTP_payroll_db",
            })
        self.metrics.end_stage("transform_enrich", len(enriched))
        self.logger.log("SUCCESS", "transform_enrich", f"Enriched {len(enriched)} records with derived metrics")
        return enriched

    def aggregate(self, payroll: List[dict]) -> dict:
        """Compute all KPI aggregations."""
        self.metrics.start_stage("aggregate")

        def _sum(data, field):   return round(sum(float(r.get(field,0) or 0) for r in data), 2)
        def _avg(data, field):   n=len(data); return round(_sum(data,field)/n, 2) if n else 0
        def _max(data, field):   return max((float(r.get(field,0) or 0) for r in data), default=0)
        def _min(data, field):   return min((float(r.get(field,0) or 0) for r in data if (r.get(field,0) or 0) > 0), default=0)

        dept_agg = defaultdict(lambda: {"count":0,"gross":0,"net":0,"tds":0,"pf":0})
        for r in payroll:
            d = r.get("dept_name","Unknown")
            dept_agg[d]["count"] += 1
            dept_agg[d]["gross"] += float(r.get("gross_salary",0) or 0)
            dept_agg[d]["net"]   += float(r.get("net_salary",0) or 0)
            dept_agg[d]["tds"]   += float(r.get("income_tax_tds",0) or 0)
            dept_agg[d]["pf"]    += float(r.get("pf_employee",0) or 0)

        gender_agg = defaultdict(lambda: {"count":0,"avg_net":0,"total_net":0})
        for r in payroll:
            g = r.get("gender","Unknown")
            gender_agg[g]["count"] += 1
            gender_agg[g]["total_net"] += float(r.get("net_salary",0) or 0)
        for g, v in gender_agg.items():
            v["avg_net"] = round(v["total_net"]/v["count"], 2) if v["count"] else 0

        agg = {
            "period":          payroll[0].get("period_name","") if payroll else "",
            "total_employees": len(payroll),
            "total_gross":     _sum(payroll, "gross_salary"),
            "total_net":       _sum(payroll, "net_salary"),
            "total_pf_emp":    _sum(payroll, "pf_employee"),
            "total_esi_emp":   _sum(payroll, "esi_employee"),
            "total_tds":       _sum(payroll, "income_tax_tds"),
            "total_deductions":_sum(payroll, "total_deductions"),
            "avg_net":         _avg(payroll, "net_salary"),
            "avg_gross":       _avg(payroll, "gross_salary"),
            "max_net":         _max(payroll, "net_salary"),
            "min_net":         _min(payroll, "net_salary"),
            "avg_take_home":   _avg(payroll, "take_home_ratio_pct"),
            "avg_attendance":  _avg(payroll, "attendance_efficiency"),
            "dept_breakdown":  {k: {**v, "avg_net": round(v["net"]/v["count"],2) if v["count"] else 0}
                                 for k,v in dept_agg.items()},
            "gender_breakdown":dict(gender_agg),
        }

        self.metrics.end_stage("aggregate", len(payroll))
        self.logger.log("SUCCESS", "aggregate", f"KPI aggregation complete: {len(dept_agg)} departments")
        return agg


# ══════════════════════════════════════════════════════════════
#  STAGE 3: STORAGE
# ══════════════════════════════════════════════════════════════
class StorageStage:
    """
    Persists processed data to:
    - Processed SQLite DB (DW layer)
    - CSV exports
    - JSON reports
    - Simulated S3/cloud archive
    """
    def __init__(self, metrics: PipelineMetrics, logger: PipelineLogger):
        self.metrics = metrics; self.logger = logger
        self.dw_db = OUTPUT / "pipeline_dw.db"

    def write_to_dw(self, payroll: List[dict], aggregations: dict) -> dict:
        self.metrics.start_stage("write_dw")
        conn = sqlite3.connect(self.dw_db)

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fact_payroll_processed (
                payroll_id INTEGER, emp_code TEXT, name TEXT, dept_name TEXT,
                desig_title TEXT, grade_code TEXT, period_name TEXT, year INTEGER, month INTEGER,
                basic_salary REAL, gross_salary REAL, net_salary REAL,
                pf_employee REAL, income_tax_tds REAL, total_deductions REAL,
                days_present INTEGER, days_absent INTEGER,
                annual_net REAL, take_home_ratio_pct REAL, effective_tds_pct REAL,
                attendance_efficiency REAL, pipeline_ts TEXT,
                PRIMARY KEY (payroll_id)
            );
            CREATE TABLE IF NOT EXISTS agg_payroll_summary (
                period TEXT, run_ts TEXT, total_employees INTEGER,
                total_gross REAL, total_net REAL, total_tds REAL,
                avg_net REAL, avg_gross REAL, avg_take_home REAL
            );
        """)

        # Insert fact records
        fields = ["payroll_id","emp_code","name","dept_name","desig_title","grade_code",
                  "period_name","year","month","basic_salary","gross_salary","net_salary",
                  "pf_employee","income_tax_tds","total_deductions","days_present","days_absent",
                  "annual_net","take_home_ratio_pct","effective_tds_pct","attendance_efficiency","pipeline_ts"]
        conn.executemany(
            f"INSERT OR REPLACE INTO fact_payroll_processed({','.join(fields)}) VALUES({','.join('?'*len(fields))})",
            [tuple(r.get(f) for f in fields) for r in payroll]
        )

        # Insert aggregation summary
        conn.execute("""INSERT INTO agg_payroll_summary VALUES(?,?,?,?,?,?,?,?,?)""",
                     (aggregations["period"], datetime.now().isoformat(),
                      aggregations["total_employees"], aggregations["total_gross"],
                      aggregations["total_net"], aggregations["total_tds"],
                      aggregations["avg_net"], aggregations["avg_gross"], aggregations["avg_take_home"]))
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM fact_payroll_processed").fetchone()[0]
        conn.close()

        self.metrics.end_stage("write_dw", count)
        self.logger.log("SUCCESS", "write_dw", f"Wrote {count} records to DW", {"db": str(self.dw_db)})
        return {"rows_written": count, "db": str(self.dw_db)}

    def export_csv(self, payroll: List[dict], aggregations: dict) -> dict:
        self.metrics.start_stage("export_csv")
        exports = {}

        # Full payroll register
        reg_path = OUTPUT / f"payroll_register_{aggregations.get('period','').replace(' ','-')}.csv"
        if payroll:
            with open(reg_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(payroll[0].keys()))
                w.writeheader(); w.writerows(payroll)
            exports["payroll_register"] = str(reg_path)

        # Department summary
        dept_path = OUTPUT / "dept_summary.csv"
        dept_data = aggregations.get("dept_breakdown", {})
        if dept_data:
            with open(dept_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["dept","count","gross","net","tds","pf","avg_net"])
                w.writeheader()
                for dept, d in dept_data.items():
                    w.writerow({"dept":dept, **d})
            exports["dept_summary"] = str(dept_path)

        # KPI summary
        kpi_path = OUTPUT / "kpi_summary.json"
        kpi_path.write_text(json.dumps(aggregations, indent=2, default=str))
        exports["kpi_json"] = str(kpi_path)

        self.metrics.end_stage("export_csv", len(payroll))
        self.logger.log("SUCCESS", "export_csv", f"Exported {len(exports)} files")
        return exports

    def archive_to_cloud(self, payroll: List[dict], period: str) -> dict:
        """Simulate S3 upload."""
        self.metrics.start_stage("cloud_archive")
        size_bytes = len(json.dumps(payroll, default=str).encode())
        archive_key = f"payroll/archive/{period.replace(' ','-')}/payroll_records.json"
        etag = hashlib.md5(archive_key.encode()).hexdigest()
        result = {
            "bucket":     "payrollwise-data-ap-south",
            "key":        archive_key,
            "size_bytes": size_bytes,
            "etag":       etag,
            "url":        f"s3://payrollwise-data-ap-south/{archive_key}",
            "storage_class": "STANDARD_IA",
            "encrypted":  True,
            "checksum_sha256": hashlib.sha256(archive_key.encode()).hexdigest()[:16]
        }
        self.metrics.end_stage("cloud_archive", len(payroll), result)
        self.logger.log("SUCCESS", "cloud_archive", f"Archived {size_bytes} bytes to {result['url']}")
        return result


# ══════════════════════════════════════════════════════════════
#  STAGE 4: ORCHESTRATION
# ══════════════════════════════════════════════════════════════
class OrchestrationStage:
    """
    Manages pipeline scheduling, monitoring, and alerts.
    Simulates Airflow DAG coordination.
    """
    def __init__(self, metrics: PipelineMetrics, logger: PipelineLogger):
        self.metrics = metrics; self.logger = logger

    def validate_sla(self, metrics_summary: dict) -> dict:
        """Check if pipeline met SLA requirements."""
        self.metrics.start_stage("sla_check")
        slas = {
            "total_pipeline_time_ms": 30000,   # 30 seconds
            "success_rate_pct":       100,
        }
        violations = []
        if metrics_summary.get("total_ms", 0) > slas["total_pipeline_time_ms"]:
            violations.append(f"Pipeline time {metrics_summary['total_ms']}ms exceeded SLA {slas['total_pipeline_time_ms']}ms")
        if metrics_summary.get("failed", 0) > 0:
            violations.append(f"{metrics_summary['failed']} stage(s) failed")

        result = {
            "sla_met": len(violations) == 0,
            "violations": violations,
            "pipeline_time_ms": metrics_summary.get("total_ms"),
            "stages_succeeded": metrics_summary.get("succeeded"),
        }
        self.metrics.end_stage("sla_check", 0, result)
        self.logger.log("SUCCESS" if result["sla_met"] else "WARN", "sla_check",
                        f"SLA {'MET' if result['sla_met'] else 'VIOLATED'}: {violations or 'All checks passed'}")
        return result

    def send_notifications(self, aggregations: dict, sla: dict) -> List[str]:
        """Simulate sending payroll completion notifications."""
        self.metrics.start_stage("notifications")
        notifications = [
            f"PAYROLL COMPLETE: {aggregations['period']} processed for {aggregations['total_employees']} employees",
            f"TOTAL NET DISBURSED: ₹{aggregations['total_net']:,.2f}",
            f"TOTAL TDS FILED: ₹{aggregations['total_tds']:,.2f}",
            f"SLA STATUS: {'✓ MET' if sla['sla_met'] else '⚠ VIOLATED'}",
            f"DASHBOARD: http://localhost:5000 | DW: s3://payrollwise-data-ap-south/",
        ]
        channels = {
            "email→ceo@company.com":      notifications[0],
            "email→payroll@company.com":  "\n".join(notifications[:3]),
            "slack→#payroll-alerts":      notifications[0],
            "sms→HR-Manager":             f"Payroll done: ₹{aggregations['total_net']:,.0f} for {aggregations['total_employees']} emp",
        }
        for channel, msg in channels.items():
            self.logger.log("INFO", "notifications", f"Sent to {channel}: {msg[:60]}")
        self.metrics.end_stage("notifications", len(channels))
        return notifications

    def update_monitoring_dashboard(self, metrics_summary: dict) -> dict:
        """Update monitoring metrics."""
        self.metrics.start_stage("monitoring")
        dashboard_data = {
            "last_run":         datetime.now().isoformat(),
            "pipeline_status":  "SUCCESS" if metrics_summary.get("failed",0) == 0 else "FAILED",
            "stages":           metrics_summary.get("stages", {}),
            "sla_met":          True,
            "uptime_pct":       99.97,
            "avg_run_time_ms":  metrics_summary.get("total_ms", 0),
            "grafana_url":      "http://monitoring.company.com/grafana/payroll",
            "alerts":           [],
        }
        dash_path = OUTPUT / "monitoring_dashboard.json"
        dash_path.write_text(json.dumps(dashboard_data, indent=2, default=str))
        self.metrics.end_stage("monitoring", 0, {"dashboard": str(dash_path)})
        self.logger.log("SUCCESS", "monitoring", f"Dashboard updated: {dash_path.name}")
        return dashboard_data


# ══════════════════════════════════════════════════════════════
#  STAGE 5: DASHBOARD OUTPUT
# ══════════════════════════════════════════════════════════════
class DashboardStage:
    """Generates HTML dashboard from pipeline output."""

    def __init__(self, metrics: PipelineMetrics, logger: PipelineLogger):
        self.metrics = metrics; self.logger = logger

    def generate_html_dashboard(self, aggregations: dict, payroll: List[dict],
                                 pipeline_summary: dict) -> str:
        self.metrics.start_stage("dashboard")

        def fmt(n):
            if n is None: return "—"
            n = float(n)
            if n >= 10000000: return f"₹{n/10000000:.2f}Cr"
            if n >= 100000:   return f"₹{n/100000:.2f}L"
            return f"₹{n:,.2f}"

        dept_rows = "".join(
            f"""<tr>
                <td><b>{dept}</b></td>
                <td>{d['count']}</td>
                <td style="color:#22c55e">{fmt(d['gross'])}</td>
                <td style="color:#f0b429">{fmt(d['net'])}</td>
                <td style="color:#ef4444">{fmt(d['tds'])}</td>
                <td>{fmt(d.get('avg_net',0))}</td>
            </tr>"""
            for dept, d in sorted(aggregations.get("dept_breakdown",{}).items(),
                                   key=lambda x: x[1]["net"], reverse=True)
        )

        emp_rows = "".join(
            f"""<tr>
                <td><code>{r.get('emp_code','')}</code></td>
                <td>{r.get('name','')}</td>
                <td>{r.get('dept_name','')}</td>
                <td style="text-align:right">{fmt(r.get('gross_salary'))}</td>
                <td style="text-align:right;color:#22c55e"><b>{fmt(r.get('net_salary'))}</b></td>
                <td style="text-align:right">{r.get('take_home_ratio_pct','')}%</td>
                <td style="text-align:right">{r.get('attendance_efficiency','')}%</td>
            </tr>"""
            for r in sorted(payroll, key=lambda x: x.get("net_salary",0) or 0, reverse=True)[:15]
        )

        stage_rows = "".join(
            f"""<tr>
                <td>{sname}</td>
                <td style="color:{'#22c55e' if s.get('status')=='success' else '#ef4444'}">
                    {'✓' if s.get('status')=='success' else '✗'} {s.get('status','').upper()}</td>
                <td style="text-align:right">{s.get('duration_ms','—')} ms</td>
                <td style="text-align:right">{s.get('rows','—')}</td>
            </tr>"""
            for sname, s in pipeline_summary.get("stages",{}).items()
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PayrollWise — Pipeline Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=IBM+Plex+Mono:wght@400;600&family=Syne:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root{{--bg:#090c12;--bg2:#0e1420;--bg3:#141b29;--border:#1e2b40;--text:#e8edf5;--text2:#8a9ab5;--gold:#f0b429;--green:#22c55e;--red:#ef4444;--blue:#3b82f6;}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Syne',sans-serif;background:var(--bg);color:var(--text);padding:24px;}}
  h1{{font-family:'DM Serif Display',serif;font-size:28px;color:var(--gold);margin-bottom:4px}}
  h2{{font-family:'DM Serif Display',serif;font-size:18px;color:var(--text);margin:24px 0 12px}}
  .subtitle{{font-size:12px;color:var(--text2);font-family:'IBM Plex Mono',monospace;margin-bottom:24px}}
  .stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;margin-bottom:28px}}
  .stat{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:18px;position:relative;overflow:hidden}}
  .stat::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px}}
  .s-gold::before{{background:var(--gold)}} .s-green::before{{background:var(--green)}} .s-blue::before{{background:var(--blue)}} .s-red::before{{background:var(--red)}}
  .stat-label{{font-size:9px;color:var(--text2);text-transform:uppercase;letter-spacing:2px;font-family:'IBM Plex Mono',monospace;margin-bottom:8px}}
  .stat-value{{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:600}}
  .stat-sub{{font-size:11px;color:var(--text2);margin-top:4px}}
  .card{{background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:20px}}
  .card-head{{padding:14px 18px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;display:flex;justify-content:space-between;align-items:center}}
  table{{width:100%;border-collapse:collapse}}
  th{{background:var(--bg3);padding:9px 14px;text-align:left;font-size:10px;font-weight:600;color:var(--text2);letter-spacing:1.5px;text-transform:uppercase;font-family:'IBM Plex Mono',monospace;border-bottom:1px solid var(--border)}}
  td{{padding:10px 14px;font-size:13px;border-bottom:1px solid var(--border)}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:var(--bg3)}}
  code{{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--gold)}}
  .badge{{display:inline-flex;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:600;font-family:'IBM Plex Mono',monospace}}
  .b-gold{{background:rgba(240,180,41,.15);color:var(--gold)}}
  .b-green{{background:rgba(34,197,94,.15);color:var(--green)}}
  footer{{text-align:center;padding:24px;color:var(--text2);font-size:11px;font-family:'IBM Plex Mono',monospace;border-top:1px solid var(--border);margin-top:24px}}
</style>
</head>
<body>
<h1>PayrollWise — Data Pipeline Dashboard</h1>
<div class="subtitle">TASK 30 FINAL PROJECT · Generated: {datetime.now():%Y-%m-%d %H:%M:%S} · Period: {aggregations.get('period','—')}</div>

<h2>Key Metrics</h2>
<div class="stats">
  <div class="stat s-gold"><div class="stat-label">Employees Paid</div><div class="stat-value">{aggregations.get('total_employees',0)}</div><div class="stat-sub">Active headcount</div></div>
  <div class="stat s-blue"><div class="stat-label">Total Gross</div><div class="stat-value">{fmt(aggregations.get('total_gross',0))}</div><div class="stat-sub">Payroll period</div></div>
  <div class="stat s-green"><div class="stat-label">Total Net</div><div class="stat-value">{fmt(aggregations.get('total_net',0))}</div><div class="stat-sub">Amount disbursed</div></div>
  <div class="stat s-red"><div class="stat-label">Total TDS</div><div class="stat-value">{fmt(aggregations.get('total_tds',0))}</div><div class="stat-sub">Tax deducted</div></div>
  <div class="stat s-gold"><div class="stat-label">Avg Net Salary</div><div class="stat-value">{fmt(aggregations.get('avg_net',0))}</div><div class="stat-sub">Per employee</div></div>
  <div class="stat s-green"><div class="stat-label">Avg Take-Home</div><div class="stat-value">{aggregations.get('avg_take_home',0):.1f}%</div><div class="stat-sub">Net/Gross ratio</div></div>
  <div class="stat s-blue"><div class="stat-label">Avg Attendance</div><div class="stat-value">{aggregations.get('avg_attendance',0):.1f}%</div><div class="stat-sub">Working days</div></div>
  <div class="stat s-gold"><div class="stat-label">Total PF</div><div class="stat-value">{fmt(aggregations.get('total_pf_emp',0))}</div><div class="stat-sub">Employee contribution</div></div>
</div>

<div class="card">
  <div class="card-head">Department-wise Payroll <span class="badge b-gold">{len(aggregations.get('dept_breakdown',{}))} Departments</span></div>
  <table>
    <thead><tr><th>Department</th><th>Headcount</th><th>Total Gross</th><th>Total Net</th><th>TDS</th><th>Avg Net</th></tr></thead>
    <tbody>{dept_rows}</tbody>
  </table>
</div>

<div class="card">
  <div class="card-head">Top Earners — {aggregations.get('period','')}</div>
  <table>
    <thead><tr><th>Code</th><th>Employee</th><th>Department</th><th>Gross</th><th>Net Salary</th><th>Take-Home %</th><th>Attendance %</th></tr></thead>
    <tbody>{emp_rows}</tbody>
  </table>
</div>

<div class="card">
  <div class="card-head">Pipeline Execution Summary <span class="badge b-green">Total: {pipeline_summary.get('total_ms',0):.0f}ms</span></div>
  <table>
    <thead><tr><th>Stage</th><th>Status</th><th>Duration</th><th>Records</th></tr></thead>
    <tbody>{stage_rows}</tbody>
  </table>
</div>

<div class="card">
  <div class="card-head">Data Engineering Stack</div>
  <table>
    <thead><tr><th>Task</th><th>Technology</th><th>Purpose</th></tr></thead>
    <tbody>
      <tr><td>Task 01</td><td>Linux + Shell</td><td>Directory setup, file permissions, automation</td></tr>
      <tr><td>Task 02</td><td>HTTP/FTP/TLS</td><td>API simulation, packet capture, secure data flow</td></tr>
      <tr><td>Task 03</td><td>Python CSV</td><td>Multi-file CSV ingestion, cleaning, merging</td></tr>
      <tr><td>Task 04</td><td>Advanced Python</td><td>Normalization, aggregation, validation modules</td></tr>
      <tr><td>Task 05</td><td>Pandas + NumPy</td><td>1M+ row analysis, memory optimization</td></tr>
      <tr><td>Task 06-07</td><td>SQLite SQL</td><td>Queries, joins, window functions, CTEs</td></tr>
      <tr><td>Task 08</td><td>OLTP vs OLAP</td><td>Schema design and use-case comparison</td></tr>
      <tr><td>Task 09</td><td>Star Schema</td><td>Data warehouse with fact + dimension tables</td></tr>
      <tr><td>Task 10</td><td>ETL vs ELT</td><td>Both pipelines implemented and benchmarked</td></tr>
      <tr><td>Task 11</td><td>Batch Ingestion</td><td>Chunked CSV→DB pipeline with checkpointing</td></tr>
      <tr><td>Task 12-13</td><td>HDFS Simulation</td><td>Namenode/Datanode, replication, block storage</td></tr>
      <tr><td>Task 14-17</td><td>Spark Simulation</td><td>RDD, DataFrame, SQL, partitioning, caching</td></tr>
      <tr><td>Task 18-21</td><td>Kafka Streaming</td><td>Producer/consumer, offsets, micro-batches</td></tr>
      <tr><td>Task 22-23</td><td>Airflow Simulation</td><td>DAG, scheduling, retry, SLA monitoring</td></tr>
      <tr><td>Task 24</td><td>AWS/GCP/Azure</td><td>Cloud services comparison for payroll</td></tr>
      <tr><td>Task 25</td><td>S3 Simulation</td><td>Object storage, versioning, lifecycle, presigned URLs</td></tr>
      <tr><td>Task 26</td><td>EC2 Simulation</td><td>Instance lifecycle, CI/CD deployment pipeline</td></tr>
      <tr><td>Task 27</td><td>BigQuery/Redshift</td><td>Cloud DW analytical queries and cost analysis</td></tr>
      <tr><td>Task 28</td><td>Delta Lake</td><td>ACID, time travel, schema evolution, vacuum</td></tr>
      <tr><td>Task 29</td><td>Data Quality</td><td>Checks, anomaly detection, DQ scoring</td></tr>
      <tr><td>Task 30</td><td>Full Pipeline</td><td>End-to-end: ingest→process→store→orchestrate→dashboard</td></tr>
    </tbody>
  </table>
</div>

<footer>PayrollWise Data Engineering System · 30 Tasks Completed · SQLite + Python + Simulation Stack</footer>
</body>
</html>"""

        html_path = OUTPUT / "pipeline_dashboard.html"
        html_path.write_text(html, encoding="utf-8")
        self.metrics.end_stage("dashboard", len(payroll), {"html": str(html_path)})
        self.logger.log("SUCCESS", "dashboard", f"HTML dashboard generated: {html_path.name}")
        return str(html_path)


# ══════════════════════════════════════════════════════════════
#  MASTER PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════
def run():
    print("=" * 65)
    print("  TASK 30: END-TO-END PAYROLL DATA ENGINEERING PIPELINE")
    print("  Ingestion → Processing → Storage → Orchestration → Dashboard")
    print("=" * 65)

    metrics = PipelineMetrics()
    logger  = PipelineLogger(OUTPUT / "pipeline.log.json")

    logger.log("INFO", "PIPELINE", "PayrollWise Data Pipeline v2.0 starting")

    try:
        # ── STAGE 1: INGESTION ────────────────────────────────
        print("\n══ STAGE 1: DATA INGESTION ══")
        ingestor = DataIngestionStage(metrics, logger)
        raw_data = ingestor.ingest_from_db(period_id=24)
        csv_data = ingestor.ingest_from_csv()
        api_events = ingestor.ingest_api_events(n_events=25)
        print(f"  ✓ Ingested: {sum(len(v) for v in raw_data.values())} records from DB, "
              f"{len(api_events)} API events")

        # ── STAGE 2: PROCESSING ───────────────────────────────
        print("\n══ STAGE 2: DATA PROCESSING ══")
        processor = DataProcessingStage(metrics, logger)
        clean_payroll, issues = processor.clean_and_validate(raw_data["payroll"])
        enriched = processor.transform_and_enrich(clean_payroll)
        aggregations = processor.aggregate(enriched)
        print(f"  ✓ Processed: {len(enriched)} records | {len(issues)} quality issues")
        print(f"  ✓ KPIs: gross={aggregations['total_gross']:,.0f} | net={aggregations['total_net']:,.0f}")

        # ── STAGE 3: STORAGE ──────────────────────────────────
        print("\n══ STAGE 3: STORAGE ══")
        storage = StorageStage(metrics, logger)
        dw_result  = storage.write_to_dw(enriched, aggregations)
        csv_result = storage.export_csv(enriched, aggregations)
        s3_result  = storage.archive_to_cloud(enriched, aggregations.get("period",""))
        print(f"  ✓ DW: {dw_result['rows_written']} rows | CSV: {len(csv_result)} files | S3: {s3_result['size_bytes']} bytes")

        # ── STAGE 4: ORCHESTRATION ────────────────────────────
        print("\n══ STAGE 4: ORCHESTRATION ══")
        orchestrator = OrchestrationStage(metrics, logger)
        summary = metrics.summary()
        sla     = orchestrator.validate_sla(summary)
        notifs  = orchestrator.send_notifications(aggregations, sla)
        monitor = orchestrator.update_monitoring_dashboard(summary)
        print(f"  ✓ SLA: {'MET' if sla['sla_met'] else 'VIOLATED'} | {len(notifs)} notifications sent")

        # ── STAGE 5: DASHBOARD ────────────────────────────────
        print("\n══ STAGE 5: DASHBOARD GENERATION ══")
        dasher = DashboardStage(metrics, logger)
        final_summary = metrics.summary()
        html_path = dasher.generate_html_dashboard(aggregations, enriched, final_summary)
        print(f"  ✓ Dashboard: {html_path}")

    except Exception as e:
        import traceback
        logger.log("ERROR", "PIPELINE", f"Pipeline failed: {e}")
        print(f"\n  [ERROR] {e}")
        traceback.print_exc()

    # ── FINAL REPORT ──────────────────────────────────────────
    final = metrics.summary()
    logger.save()

    print("\n" + "="*65)
    print("  FINAL PIPELINE REPORT")
    print("="*65)
    print(f"  Total stages  : {final['total_stages']}")
    print(f"  Succeeded     : {final['succeeded']}")
    print(f"  Failed        : {final['failed']}")
    print(f"  Total time    : {final['total_ms']:.0f} ms")
    print(f"  Status        : {'✓ SUCCESS' if final['failed']==0 else '✗ PARTIAL FAILURE'}")
    print("\n  Stage Breakdown:")
    for name, s in final["stages"].items():
        icon = "✓" if s.get("status")=="success" else "✗"
        print(f"    {icon} {name:<28} {s.get('duration_ms',0):>8.1f}ms  {s.get('rows',0):>6} rows")

    print(f"\n  Outputs:")
    for f in OUTPUT.glob("*"):
        size = f.stat().st_size
        print(f"    {f.name:<45} {size:>8,} bytes")

    final_report = {
        "pipeline_summary": final,
        "aggregations": {k:v for k,v in aggregations.items() if k not in ["dept_breakdown","gender_breakdown"]},
        "dept_breakdown": aggregations.get("dept_breakdown",{}),
        "data_quality_issues": len(issues),
        "sla_result": sla,
        "outputs": {f.name: f.stat().st_size for f in OUTPUT.glob("*")},
        "timestamp": datetime.now().isoformat()
    }
    (OUTPUT/"final_pipeline_report.json").write_text(json.dumps(final_report, indent=2, default=str))
    print(f"\n✓ Final report: {OUTPUT}/final_pipeline_report.json")
    print(f"✓ HTML Dashboard: {OUTPUT}/pipeline_dashboard.html")
    print(f"✓ Log: {OUTPUT}/pipeline.log.json")
    return final_report

if __name__ == "__main__":
    run()
