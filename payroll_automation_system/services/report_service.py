"""
Report Service - Generate various payroll and HR reports
"""
import os
import sys
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from utils.db_connection import get_connection, execute_query

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _header(title: str, width: int = 80) -> str:
    bar = "=" * width
    return f"\n{bar}\n  {title}\n{bar}\n"


def report_payroll_register(period_id: int) -> str:
    """Full payroll register for a period."""
    rows = execute_query("""
        SELECT ps.*, pp.period_id
        FROM vw_payroll_summary ps
        JOIN payroll_records pr ON ps.payroll_id = pr.payroll_id
        JOIN payroll_periods pp ON pr.period_id = pp.period_id
        WHERE pp.period_id=? ORDER BY ps.dept_name, ps.employee_name
    """, (period_id,))

    if not rows:
        return f"No payroll data for period_id={period_id}"

    period_name = rows[0]["period_name"] if rows else f"Period {period_id}"
    lines = [_header(f"PAYROLL REGISTER - {period_name}")]
    lines.append(f"{'#':<4} {'EMP CODE':<9} {'EMPLOYEE NAME':<22} {'DEPT':<20} "
                 f"{'GROSS':>12} {'DEDUCT':>10} {'NET':>12} {'STATUS':<10}")
    lines.append("-" * 100)

    totals = {"gross": 0, "ded": 0, "net": 0}
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i:<4} {r['emp_code']:<9} {r['employee_name']:<22} {r['dept_name'][:19]:<20} "
            f"{r['gross_salary']:>12,.2f} {r['total_deductions']:>10,.2f} "
            f"{r['net_salary']:>12,.2f} {r['status']:<10}"
        )
        totals["gross"] += r["gross_salary"]
        totals["ded"]   += r["total_deductions"]
        totals["net"]   += r["net_salary"]

    lines.append("-" * 100)
    lines.append(f"{'TOTAL':<37} {totals['gross']:>12,.2f} {totals['ded']:>10,.2f} {totals['net']:>12,.2f}")
    lines.append(f"\n  Total Employees: {len(rows)}  |  Generated: {datetime.now():%Y-%m-%d %H:%M:%S}")
    return "\n".join(lines)


def report_payslip(emp_id: int, period_id: int) -> str:
    """Individual payslip."""
    rows = execute_query("""
        SELECT ps.*, e.emp_code, e.first_name||' '||e.last_name AS name,
               e.pan_number, e.bank_name, e.bank_account, e.phone, e.email,
               d.dept_name, ds.desig_title, sg.grade_name,
               pp.period_name, pp.month, pp.year
        FROM   payroll_records ps
        JOIN   employees       e  ON ps.emp_id    = e.emp_id
        JOIN   departments     d  ON e.dept_id    = d.dept_id
        JOIN   designations    ds ON e.desig_id   = ds.desig_id
        JOIN   salary_grades   sg ON e.grade_id   = sg.grade_id
        JOIN   payroll_periods pp ON ps.period_id = pp.period_id
        WHERE  ps.emp_id=? AND ps.period_id=?
    """, (emp_id, period_id))

    if not rows:
        return f"Payslip not found for emp_id={emp_id}, period_id={period_id}"

    r = dict(rows[0])
    w = 60
    lines = ["=" * w,
             f"  {'PAYROLL WISE LTD':^{w-4}}",
             f"  {'SALARY SLIP':^{w-4}}",
             "=" * w,
             f"  Employee Code : {r['emp_code']:<20} Period : {r['period_name']}",
             f"  Name          : {r['name']:<20} Dept   : {r['dept_name']}",
             f"  Designation   : {r['desig_title']:<20} Grade  : {r['grade_name']}",
             f"  PAN           : {r['pan_number']:<20} Bank   : {r['bank_name']}",
             f"  Bank A/C      : {r['bank_account']}",
             "-" * w,
             f"  {'EARNINGS':<28} {'DEDUCTIONS':<28}",
             "-" * w,
             f"  {'Basic Salary':<24} {r['basic_salary']:>8,.2f}   {'PF (Employee)':<20} {r['pf_employee']:>8,.2f}",
             f"  {'HRA':<24} {r['hra']:>8,.2f}   {'ESI (Employee)':<20} {r['esi_employee']:>8,.2f}",
             f"  {'Dearness Allowance':<24} {r['da']:>8,.2f}   {'Professional Tax':<20} {r['professional_tax']:>8,.2f}",
             f"  {'Transport Allow.':<24} {r['transport_allow']:>8,.2f}   {'Income Tax (TDS)':<20} {r['income_tax_tds']:>8,.2f}",
             f"  {'Other Allowances':<24} {r['other_allowances']:>8,.2f}   {'Loan EMI':<20} {r['loan_deduction']:>8,.2f}",
             f"  {'':<24} {'':>8}    {'Other Deductions':<20} {r['other_deductions']:>8,.2f}",
             "-" * w,
             f"  {'Gross Salary':<24} {r['gross_salary']:>8,.2f}   {'Total Deductions':<20} {r['total_deductions']:>8,.2f}",
             "=" * w,
             f"  {'NET SALARY (Take Home)':<24} {'':>8}   {r['net_salary']:>8,.2f}",
             "=" * w,
             f"  Days Present: {r['days_present']}  |  Days Absent: {r['days_absent']}  |  Leave: {r['days_leave']}",
             f"  Payment Status: {r['status']}  |  Payment Date: {r.get('payment_date','--')}",
             "=" * w]
    return "\n".join(lines)


def report_department_summary(period_id: int) -> str:
    """Department-wise payroll cost summary."""
    rows = execute_query("""
        SELECT d.dept_name,
               COUNT(pr.payroll_id)              AS headcount,
               ROUND(SUM(pr.gross_salary),2)     AS total_gross,
               ROUND(SUM(pr.pf_employee),2)      AS pf_emp,
               ROUND(SUM(pr.pf_employer),2)      AS pf_er,
               ROUND(SUM(pr.income_tax_tds),2)   AS tds,
               ROUND(SUM(pr.net_salary),2)        AS total_net,
               ROUND(AVG(pr.net_salary),2)        AS avg_net
        FROM payroll_records pr
        JOIN employees e ON pr.emp_id = e.emp_id
        JOIN departments d ON e.dept_id = d.dept_id
        WHERE pr.period_id = ?
        GROUP BY d.dept_id ORDER BY total_gross DESC
    """, (period_id,))

    lines = [_header("DEPARTMENT-WISE PAYROLL SUMMARY")]
    lines.append(f"{'DEPARTMENT':<25} {'HC':>4} {'GROSS':>14} {'NET':>14} {'AVG NET':>12} {'TDS':>10}")
    lines.append("-" * 85)

    tg = tn = 0
    for r in rows:
        lines.append(
            f"{r['dept_name'][:24]:<25} {r['headcount']:>4} "
            f"{r['total_gross']:>14,.2f} {r['total_net']:>14,.2f} "
            f"{r['avg_net']:>12,.2f} {r['tds']:>10,.2f}"
        )
        tg += r["total_gross"]; tn += r["total_net"]

    lines.append("-" * 85)
    lines.append(f"{'TOTAL':<25} {sum(r['headcount'] for r in rows):>4} {tg:>14,.2f} {tn:>14,.2f}")
    return "\n".join(lines)


def report_ytd_salary(year: int) -> str:
    """Year-to-date salary summary."""
    rows = execute_query("""
        SELECT * FROM vw_ytd_salary WHERE year=? ORDER BY ytd_gross DESC
    """, (year,))

    lines = [_header(f"YEAR-TO-DATE SALARY SUMMARY - FY {year}")]
    lines.append(f"{'EMP CODE':<10} {'NAME':<24} {'MONTHS':>6} {'YTD GROSS':>14} {'YTD TDS':>10} {'YTD NET':>14}")
    lines.append("-" * 82)

    for r in rows:
        lines.append(
            f"{r['emp_code']:<10} {r['employee_name'][:23]:<24} {r['months_processed']:>6} "
            f"{r['ytd_gross']:>14,.2f} {r['ytd_tds']:>10,.2f} {r['ytd_net']:>14,.2f}"
        )
    return "\n".join(lines)


def report_attendance_summary(year: int, month: int) -> str:
    """Attendance summary for a month."""
    rows = execute_query("""
        SELECT * FROM vw_attendance_summary WHERE year=? AND month=?
        ORDER BY days_absent DESC, employee_name
    """, (str(year), f"{month:02d}"))

    lines = [_header(f"ATTENDANCE SUMMARY - {year}/{month:02d}")]
    lines.append(f"{'EMP CODE':<10} {'NAME':<24} {'PRESENT':>8} {'ABSENT':>7} {'LEAVE':>6} {'HOURS':>8}")
    lines.append("-" * 70)

    for r in rows:
        lines.append(
            f"{r['emp_code']:<10} {r['employee_name'][:23]:<24} "
            f"{r['days_present']:>8} {r['days_absent']:>7} {r['leave_days']:>6} {r['total_hours']:>8.1f}"
        )
    return "\n".join(lines)


def report_loan_outstanding() -> str:
    """Loan outstanding report."""
    rows = execute_query("SELECT * FROM vw_loan_status WHERE status='Active' ORDER BY outstanding_balance DESC")

    lines = [_header("EMPLOYEE LOAN OUTSTANDING REPORT")]
    lines.append(f"{'EMP':<8} {'NAME':<24} {'DEPT':<18} {'LOAN AMT':>12} {'EMI':>8} {'PAID':>5} {'REM':>4} {'OUTSTANDING':>13}")
    lines.append("-" * 100)

    total = 0
    for r in rows:
        lines.append(
            f"{r['emp_code']:<8} {r['employee_name'][:23]:<24} {r['dept_name'][:17]:<18} "
            f"{r['loan_amount']:>12,.2f} {r['emi_amount']:>8,.2f} {r['emis_paid']:>5} "
            f"{r['emis_remaining']:>4} {r['outstanding_balance']:>13,.2f}"
        )
        total += r["outstanding_balance"]

    lines.append("-" * 100)
    lines.append(f"{'TOTAL OUTSTANDING':>90} {total:>13,.2f}")
    return "\n".join(lines)


def export_payroll_csv(period_id: int) -> str:
    """Export payroll register to CSV."""
    rows = execute_query("""
        SELECT ps.*
        FROM vw_payroll_summary ps
        JOIN payroll_records pr ON ps.payroll_id = pr.payroll_id
        WHERE pr.period_id=? ORDER BY ps.dept_name
    """, (period_id,))

    if not rows:
        return "No data to export"

    fname = os.path.join(REPORTS_DIR, f"payroll_period_{period_id}.csv")
    with open(fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dict(rows[0]).keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])

    return f"CSV exported to: {fname}  ({len(rows)} records)"


def report_audit_trail(table_name: str = None, limit: int = 50) -> str:
    """Show audit trail."""
    if table_name:
        rows = execute_query("""
            SELECT * FROM audit_logs WHERE table_name=?
            ORDER BY performed_at DESC LIMIT ?
        """, (table_name, limit))
    else:
        rows = execute_query("""
            SELECT * FROM audit_logs ORDER BY performed_at DESC LIMIT ?
        """, (limit,))

    lines = [_header(f"AUDIT TRAIL {'- ' + table_name if table_name else '(ALL TABLES)'}")]
    lines.append(f"{'#':<4} {'TABLE':<20} {'REC ID':>8} {'ACTION':<8} {'WHEN':<22} {'BY'}")
    lines.append("-" * 80)

    for i, r in enumerate(rows, 1):
        lines.append(f"{i:<4} {r['table_name']:<20} {r['record_id']:>8} {r['action']:<8} "
                     f"{r['performed_at']:<22} {r['performed_by']}")
    return "\n".join(lines)


def report_salary_revisions() -> str:
    """Show all salary revisions."""
    rows = execute_query("""
        SELECT sr.revision_id, e.emp_code,
               e.first_name||' '||e.last_name AS emp_name,
               d.dept_name,
               sr.old_basic, sr.new_basic,
               ROUND((sr.new_basic - sr.old_basic)*100.0/sr.old_basic, 2) AS pct_hike,
               sr.effective_date, sr.reason
        FROM   salary_revisions sr
        JOIN   employees e ON sr.emp_id = e.emp_id
        JOIN   departments d ON e.dept_id = d.dept_id
        ORDER  BY sr.effective_date DESC, pct_hike DESC
    """)

    lines = [_header("SALARY REVISION HISTORY")]
    lines.append(f"{'EMP':<8} {'NAME':<22} {'OLD BASIC':>11} {'NEW BASIC':>11} {'% HIKE':>7} {'EFFECTIVE':<12} REASON")
    lines.append("-" * 100)

    for r in rows:
        lines.append(
            f"{r['emp_code']:<8} {r['emp_name'][:21]:<22} {r['old_basic']:>11,.2f} "
            f"{r['new_basic']:>11,.2f} {r['pct_hike']:>6.1f}% {r['effective_date']:<12} {r['reason']}"
        )
    return "\n".join(lines)
