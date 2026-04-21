"""
Payroll Service - Core Business Logic
Handles payroll calculation, generation, and processing
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from utils.db_connection import get_connection, execute_query


def calc_tds_annual(annual_income: float, fiscal_year: str = "FY2025-26") -> float:
    """Calculate annual TDS using tax slabs from DB."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT income_from, income_to, tax_rate_pct
        FROM   tax_slabs
        WHERE  fiscal_year = ?
        ORDER  BY income_from
    """, (fiscal_year,))
    slabs = cur.fetchall()
    conn.close()

    tax = 0.0
    prev = 0.0
    for slab in slabs:
        income_from, income_to, rate = slab[0], slab[1], slab[2]
        if income_to is None:
            income_to = float('inf')
        if annual_income <= income_from:
            break
        taxable = min(annual_income, income_to) - prev
        tax    += taxable * rate / 100
        prev    = min(annual_income, income_to)
        if annual_income <= income_to:
            break

    # Rebate u/s 87A (Rs 60,000 for FY2025-26)
    if annual_income <= 1200000:
        tax = max(tax - 60000, 0)

    # Cess 4%
    tax = round(tax * 1.04, 2)
    return max(tax, 0)


def calculate_payroll_for_employee(emp_id: int, period_id: int) -> dict:
    """Calculate full payroll for one employee for a given period."""
    conn = get_connection()
    cur  = conn.cursor()

    # Get employee + grade info
    cur.execute("""
        SELECT e.emp_id, e.emp_code, e.first_name||' '||e.last_name AS name,
               e.basic_salary, e.grade_id, sg.hra_pct, sg.da_pct, sg.ta_flat,
               e.dept_id, e.desig_id, e.status
        FROM   employees e
        JOIN   salary_grades sg ON e.grade_id = sg.grade_id
        WHERE  e.emp_id = ?
    """, (emp_id,))
    emp = cur.fetchone()

    if not emp or emp["status"] == "Terminated":
        conn.close()
        return {"error": f"Employee {emp_id} not found or terminated"}

    # Get period info
    cur.execute("SELECT * FROM payroll_periods WHERE period_id = ?", (period_id,))
    period = cur.fetchone()
    if not period:
        conn.close()
        return {"error": f"Period {period_id} not found"}

    working_days = period["working_days"]
    total_days   = period["total_days"]

    # Get attendance for period
    cur.execute("""
        SELECT
            SUM(CASE WHEN status='Present'  THEN 1   ELSE 0   END) AS days_present,
            SUM(CASE WHEN status='Absent'   THEN 1   ELSE 0   END) AS days_absent,
            SUM(CASE WHEN status='Half-Day' THEN 0.5 ELSE 0   END) AS half_days,
            SUM(CASE WHEN status='On-Leave' THEN 1   ELSE 0   END) AS leave_days
        FROM attendance
        WHERE emp_id = ? AND att_date BETWEEN ? AND ?
    """, (emp_id, period["start_date"], period["end_date"]))
    att = cur.fetchone()

    days_present = int(att["days_present"] or 0) + int(att["half_days"] or 0)
    days_absent  = int(att["days_absent"] or 0)
    days_leave   = int(att["leave_days"] or 0)

    # If no attendance data, assume fully present
    if days_present == 0 and days_absent == 0 and days_leave == 0:
        days_present = working_days

    basic = emp["basic_salary"]
    per_day = basic / working_days
    effective_basic = round(basic - (days_absent * per_day), 2)

    hra   = round(effective_basic * emp["hra_pct"] / 100, 2)
    da    = round(effective_basic * emp["da_pct"]  / 100, 2)
    ta    = emp["ta_flat"] if days_absent < working_days * 0.5 else 0
    gross = round(effective_basic + hra + da + ta, 2)

    # Statutory deductions
    pf_base  = min(effective_basic, 15000)
    pf_emp   = round(pf_base * 0.12, 2)
    pf_er    = round(pf_base * 0.12, 2)
    esi_emp  = round(gross * 0.0075, 2) if gross <= 21000 else 0
    esi_er   = round(gross * 0.0325, 2) if gross <= 21000 else 0
    pt       = 200 if gross > 10000 else 0

    # TDS monthly
    tds = round(calc_tds_annual(gross * 12) / 12, 2)

    # Loan EMI
    cur.execute("""
        SELECT loan_id, emi_amount
        FROM   employee_loans
        WHERE  emp_id = ? AND status = 'Active'
        LIMIT  1
    """, (emp_id,))
    loan = cur.fetchone()
    loan_ded = float(loan["emi_amount"]) if loan else 0

    total_ded = round(pf_emp + esi_emp + pt + tds + loan_ded, 2)
    net       = round(gross - total_ded, 2)

    conn.close()

    return {
        "emp_id": emp_id, "emp_code": emp["emp_code"], "name": emp["name"],
        "period_id": period_id, "period_name": period["period_name"],
        "total_days": total_days, "working_days": working_days,
        "days_present": days_present, "days_absent": days_absent, "days_leave": days_leave,
        "basic_salary": effective_basic, "hra": hra, "da": da, "transport_allow": ta,
        "other_allowances": 0, "gross_salary": gross,
        "pf_employee": pf_emp, "pf_employer": pf_er,
        "esi_employee": esi_emp, "esi_employer": esi_er,
        "professional_tax": pt, "income_tax_tds": tds,
        "loan_deduction": loan_ded, "other_deductions": 0,
        "total_deductions": total_ded, "net_salary": net
    }


def generate_payroll(period_id: int, emp_ids: list = None) -> dict:
    """Generate payroll for all or specific employees for a period."""
    conn = get_connection()
    cur  = conn.cursor()

    # Validate period
    cur.execute("SELECT * FROM payroll_periods WHERE period_id=?", (period_id,))
    period = cur.fetchone()
    if not period:
        conn.close()
        return {"error": "Period not found"}
    if period["status"] == "Paid":
        conn.close()
        return {"error": "Period already paid"}

    # Get employees
    if emp_ids:
        placeholders = ",".join("?" * len(emp_ids))
        cur.execute(f"SELECT emp_id FROM employees WHERE status='Active' AND emp_id IN ({placeholders})", emp_ids)
    else:
        cur.execute("SELECT emp_id FROM employees WHERE status='Active'")

    employees = [r["emp_id"] for r in cur.fetchall()]
    conn.close()

    results = {"success": [], "failed": [], "total": len(employees)}

    for emp_id in employees:
        try:
            p = calculate_payroll_for_employee(emp_id, period_id)
            if "error" in p:
                results["failed"].append({"emp_id": emp_id, "error": p["error"]})
                continue

            conn2 = get_connection()
            cur2  = conn2.cursor()
            cur2.execute("""
                INSERT OR REPLACE INTO payroll_records(
                    emp_id, period_id, total_days, working_days, days_present, days_absent, days_leave,
                    basic_salary, hra, da, transport_allow, other_allowances, gross_salary,
                    pf_employee, pf_employer, esi_employee, esi_employer,
                    professional_tax, income_tax_tds, loan_deduction, other_deductions,
                    total_deductions, net_salary, status
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p["emp_id"], p["period_id"], p["total_days"], p["working_days"],
                p["days_present"], p["days_absent"], p["days_leave"],
                p["basic_salary"], p["hra"], p["da"], p["transport_allow"],
                p["other_allowances"], p["gross_salary"],
                p["pf_employee"], p["pf_employer"], p["esi_employee"], p["esi_employer"],
                p["professional_tax"], p["income_tax_tds"], p["loan_deduction"],
                p["other_deductions"], p["total_deductions"], p["net_salary"], "Draft"
            ))
            conn2.commit()
            conn2.close()
            results["success"].append(emp_id)

        except Exception as e:
            results["failed"].append({"emp_id": emp_id, "error": str(e)})

    return results


def approve_payroll(period_id: int) -> dict:
    """Approve all Draft payroll records for a period."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE payroll_records SET status='Approved', updated_at=datetime('now')
        WHERE  period_id=? AND status='Draft'
    """, (period_id,))
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return {"approved_count": updated, "period_id": period_id}


def mark_paid(period_id: int, payment_date: str) -> dict:
    """Mark all Approved payroll records as Paid."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE payroll_records
        SET    status='Paid', payment_date=?, updated_at=datetime('now')
        WHERE  period_id=? AND status='Approved'
    """, (payment_date, period_id))
    updated = cur.rowcount

    cur.execute("""
        UPDATE payroll_periods SET status='Paid', processed_at=datetime('now')
        WHERE  period_id=?
    """, (period_id,))
    conn.commit()
    conn.close()
    return {"paid_count": updated, "period_id": period_id, "payment_date": payment_date}


def get_payslip(emp_id: int, period_id: int) -> dict:
    """Fetch complete payslip for an employee."""
    rows = execute_query("""
        SELECT ps.*, e.emp_code, e.first_name||' '||e.last_name AS name,
               e.pan_number, e.bank_name, e.ifsc_code, e.bank_account,
               d.dept_name, ds.desig_title, sg.grade_name,
               pp.period_name, pp.month, pp.year
        FROM   payroll_records ps
        JOIN   employees       e  ON ps.emp_id    = e.emp_id
        JOIN   departments     d  ON e.dept_id    = d.dept_id
        JOIN   designations    ds ON e.desig_id   = ds.desig_id
        JOIN   salary_grades   sg ON e.grade_id   = sg.grade_id
        JOIN   payroll_periods pp ON ps.period_id = pp.period_id
        WHERE  ps.emp_id = ? AND ps.period_id = ?
    """, (emp_id, period_id))

    if not rows:
        return {"error": "Payslip not found"}
    return dict(rows[0])


def get_department_summary(period_id: int) -> list:
    """Get department-wise payroll summary for a period."""
    rows = execute_query("""
        SELECT * FROM vw_dept_payroll_cost WHERE period_id = ?
        ORDER BY total_gross DESC
    """, (period_id,))

    # Fallback if view period doesn't match
    if not rows:
        rows = execute_query("""
            SELECT d.dept_name,
                   COUNT(pr.payroll_id)          AS headcount,
                   ROUND(SUM(pr.gross_salary),2) AS total_gross,
                   ROUND(SUM(pr.net_salary),2)   AS total_net,
                   ROUND(AVG(pr.net_salary),2)   AS avg_net_salary
            FROM payroll_records pr
            JOIN employees e ON pr.emp_id = e.emp_id
            JOIN departments d ON e.dept_id = d.dept_id
            WHERE pr.period_id = ?
            GROUP BY d.dept_id
            ORDER BY total_gross DESC
        """, (period_id,))
    return [dict(r) for r in rows]
