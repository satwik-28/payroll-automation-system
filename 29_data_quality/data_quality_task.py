"""
TASK 29: Data Quality — Validation Checks and Anomaly Detection
Dedicated file with extended DQ checks for all payroll tables.
"""
import sys, sqlite3, json, math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / "28_lakehouse"))
from lakehouse_dq_tasks import (
    DataQualityEngine, CompletenessCheck, UniquenessCheck,
    RangeCheck, ConsistencyCheck, AnomalyDetector
)

BASE = Path(__file__).parent
DB   = Path(__file__).parent.parent / "shared/database/payroll.db"
OUT  = BASE / "output"; OUT.mkdir(exist_ok=True)

def run():
    print("="*65)
    print("  TASK 29: Data Quality — Full Validation Suite")
    print("="*65)

    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row

    # ── 1. Employee DQ ────────────────────────────────────────
    print("\n[1] Employee Data Quality")
    employees = [dict(r) for r in conn.execute("""
        SELECT e.*, d.dept_name FROM employees e
        JOIN departments d ON e.dept_id=d.dept_id
    """).fetchall()]

    emp_engine = DataQualityEngine("employees")
    (emp_engine
     .add_check(CompletenessCheck("emp_code",     100))
     .add_check(CompletenessCheck("email",         100))
     .add_check(CompletenessCheck("pan_number",    100))
     .add_check(CompletenessCheck("bank_account",  100))
     .add_check(UniquenessCheck("emp_code"))
     .add_check(UniquenessCheck("email"))
     .add_check(UniquenessCheck("pan_number"))
     .add_check(RangeCheck("basic_salary", 10000, 5000000))
     .add_check(ConsistencyCheck(
         "valid_status", lambda r: r.get("status") in
         ["Active","Inactive","Terminated","On-Leave"], "Status must be valid"))
     .add_check(ConsistencyCheck(
         "valid_gender", lambda r: r.get("gender") in ["Male","Female","Other"],
         "Gender must be Male/Female/Other"))
     .add_check(ConsistencyCheck(
         "emp_code_format", lambda r: (r.get("emp_code","") or "").startswith("EMP"),
         "emp_code must start with EMP"))
    )
    emp_report = emp_engine.run_all(employees)
    print(f"  DQ Score: {emp_report['dq_score_pct']}% | {emp_report['overall_status']}")

    # ── 2. Payroll DQ ─────────────────────────────────────────
    print("\n[2] Payroll Records Data Quality")
    payroll = [dict(r) for r in conn.execute("""
        SELECT pr.*, e.emp_code, pp.period_name
        FROM payroll_records pr
        JOIN employees e ON pr.emp_id=e.emp_id
        JOIN payroll_periods pp ON pr.period_id=pp.period_id
    """).fetchall()]

    pay_engine = DataQualityEngine("payroll_records")
    (pay_engine
     .add_check(CompletenessCheck("emp_id",         100))
     .add_check(CompletenessCheck("period_id",       100))
     .add_check(CompletenessCheck("gross_salary",    100))
     .add_check(CompletenessCheck("net_salary",      100))
     .add_check(UniquenessCheck("payroll_id"))
     .add_check(RangeCheck("gross_salary",     0, 5000000))
     .add_check(RangeCheck("net_salary",       0, 5000000))
     .add_check(RangeCheck("pf_employee",      0,    1800))
     .add_check(RangeCheck("days_present",     0,      31))
     .add_check(ConsistencyCheck(
         "net_le_gross",
         lambda r: (r.get("net_salary") or 0) <= (r.get("gross_salary") or 1),
         "Net must be ≤ Gross"))
     .add_check(ConsistencyCheck(
         "positive_values",
         lambda r: all([(r.get(f) or 0) >= 0 for f in
                        ["gross_salary","net_salary","pf_employee","esi_employee"]]),
         "All salary fields must be non-negative"))
     .add_check(ConsistencyCheck(
         "valid_status",
         lambda r: r.get("status") in ["Draft","Approved","Paid","Cancelled","Revised"],
         "Payroll status must be valid"))
    )
    pay_report = pay_engine.run_all(payroll)
    print(f"  DQ Score: {pay_report['dq_score_pct']}% | {pay_report['overall_status']}")

    # ── 3. Attendance DQ ──────────────────────────────────────
    print("\n[3] Attendance Data Quality")
    attendance = [dict(r) for r in conn.execute("""
        SELECT * FROM attendance
    """).fetchall()]

    att_engine = DataQualityEngine("attendance")
    (att_engine
     .add_check(CompletenessCheck("emp_id",       100))
     .add_check(CompletenessCheck("att_date",      100))
     .add_check(CompletenessCheck("status",        100))
     .add_check(UniquenessCheck("att_id"))
     .add_check(RangeCheck("hours_worked", 0, 16))
     .add_check(ConsistencyCheck(
         "valid_att_status",
         lambda r: r.get("status") in
         ["Present","Absent","Half-Day","Holiday","Weekend","On-Leave"],
         "Attendance status must be valid"))
     .add_check(ConsistencyCheck(
         "hours_when_present",
         lambda r: not (r.get("status")=="Present" and (r.get("hours_worked") or 0) < 4),
         "Present employees must have ≥4 hours worked"))
    )
    att_report = att_engine.run_all(attendance)
    print(f"  DQ Score: {att_report['dq_score_pct']}% | {att_report['overall_status']}")

    # ── 4. Anomaly Detection ──────────────────────────────────
    print("\n[4] Anomaly Detection")
    salary_anoms = AnomalyDetector.detect_salary_anomalies(payroll)
    att_anoms    = AnomalyDetector.detect_attendance_anomalies(payroll)
    spikes       = AnomalyDetector.detect_payroll_spikes(payroll, 25.0)

    print(f"  Salary outliers (Z>3):    {salary_anoms.get('z_score_outliers',0)}")
    print(f"  IQR outliers:             {salary_anoms.get('iqr_outliers',0)}")
    print(f"  Attendance flags (<50%):  {len(att_anoms)}")
    print(f"  Payroll spikes (>25% MoM):{len(spikes)}")
    print(f"  Normal salary range:      ₹{salary_anoms.get('normal_range',['?','?'])[0]:,.0f} – "
          f"₹{salary_anoms.get('normal_range',['?','?'])[1]:,.0f}")

    # ── 5. DQ Score Summary ───────────────────────────────────
    print("\n[5] Overall DQ Dashboard")
    all_reports = [emp_report, pay_report, att_report]
    avg_score = sum(r["dq_score_pct"] for r in all_reports) / len(all_reports)
    print(f"  {'Table':<25} {'Score':>8} {'Status':>8} {'Checks':>7} {'Passed':>7}")
    print("  " + "─"*58)
    for report in all_reports:
        print(f"  {report['dataset']:<25} {report['dq_score_pct']:>7}% "
              f"{report['overall_status']:>8} {report['total_checks']:>7} {report['passed']:>7}")
    print(f"  {'OVERALL AVERAGE':<25} {avg_score:>7.1f}%")

    conn.close()

    results = {
        "employee_dq":   emp_report,
        "payroll_dq":    pay_report,
        "attendance_dq": att_report,
        "anomalies": {
            "salary_z_outliers":  salary_anoms.get("z_score_outliers", 0),
            "iqr_outliers":       salary_anoms.get("iqr_outliers", 0),
            "attendance_flags":   len(att_anoms),
            "payroll_spikes":     len(spikes),
        },
        "overall_avg_dq_score": round(avg_score, 1),
        "timestamp": datetime.now().isoformat()
    }
    (OUT/"data_quality_full_report.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Full DQ report: {OUT}/data_quality_full_report.json")
    return results

if __name__ == "__main__":
    run()
