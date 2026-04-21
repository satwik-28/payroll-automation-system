"""
Payroll Automation System - Main CLI Application
Author: PayrollWise Team
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from utils.db_connection import get_connection, execute_query
from services.payroll_service import (
    calculate_payroll_for_employee, generate_payroll,
    approve_payroll, mark_paid, get_payslip, get_department_summary
)
from services.report_service import (
    report_payroll_register, report_payslip, report_department_summary,
    report_ytd_salary, report_attendance_summary, report_loan_outstanding,
    export_payroll_csv, report_audit_trail, report_salary_revisions
)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def separator(char="=", width=70):
    return char * width


def banner():
    print(separator())
    print("  ██████╗  █████╗ ██╗   ██╗██████╗  ██████╗ ██╗     ██╗")
    print("  ██╔══██╗██╔══██╗╚██╗ ██╔╝██╔══██╗██╔═══██╗██║     ██║")
    print("  ██████╔╝███████║ ╚████╔╝ ██████╔╝██║   ██║██║     ██║")
    print("  ██╔═══╝ ██╔══██║  ╚██╔╝  ██╔══██╗██║   ██║██║     ██║")
    print("  ██║     ██║  ██║   ██║   ██║  ██║╚██████╔╝███████╗███████╗")
    print("  ╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝")
    print("         W I S E   P A Y R O L L   A U T O M A T I O N")
    print(separator())


def main_menu():
    print("\n" + separator("-"))
    print("  MAIN MENU")
    print(separator("-"))
    print("  1. Employee Management")
    print("  2. Payroll Processing")
    print("  3. Attendance & Leave")
    print("  4. Reports & Analytics")
    print("  5. Database Utilities")
    print("  6. Demo - Run All Reports")
    print("  0. Exit")
    print(separator("-"))
    return input("  Enter choice: ").strip()


def employee_menu():
    print("\n" + separator("-"))
    print("  EMPLOYEE MANAGEMENT")
    print(separator("-"))
    print("  1. List All Employees")
    print("  2. View Employee Profile")
    print("  3. Add New Employee")
    print("  4. Update Employee Status")
    print("  5. Salary Revision History")
    print("  0. Back")
    print(separator("-"))
    return input("  Enter choice: ").strip()


def payroll_menu():
    print("\n" + separator("-"))
    print("  PAYROLL PROCESSING")
    print(separator("-"))
    print("  1. List Payroll Periods")
    print("  2. Generate Payroll (for a period)")
    print("  3. View Employee Payslip")
    print("  4. Approve Payroll")
    print("  5. Mark as Paid")
    print("  6. Department Payroll Summary")
    print("  0. Back")
    print(separator("-"))
    return input("  Enter choice: ").strip()


def reports_menu():
    print("\n" + separator("-"))
    print("  REPORTS & ANALYTICS")
    print(separator("-"))
    print("  1.  Payroll Register (by period)")
    print("  2.  Department Summary")
    print("  3.  Year-to-Date Salary")
    print("  4.  Attendance Summary")
    print("  5.  Loan Outstanding")
    print("  6.  Salary Revision History")
    print("  7.  Audit Trail")
    print("  8.  Export Payroll to CSV")
    print("  9.  Generate ER Diagram")
    print("  0. Back")
    print(separator("-"))
    return input("  Enter choice: ").strip()


# ────────────────────────────────────────────────────────────────
# Employee handlers
# ────────────────────────────────────────────────────────────────
def list_employees():
    rows = execute_query("""
        SELECT emp_id, emp_code, full_name, dept_name, desig_title, basic_salary, status
        FROM vw_employee_profile ORDER BY dept_name, full_name
    """)
    print("\n" + separator())
    print(f"  {'ID':<5} {'CODE':<9} {'NAME':<24} {'DEPT':<20} {'DESIGNATION':<25} {'BASIC':>10} {'STATUS'}")
    print(separator("-"))
    for r in rows:
        print(f"  {r['emp_id']:<5} {r['emp_code']:<9} {r['full_name'][:23]:<24} "
              f"{r['dept_name'][:19]:<20} {r['desig_title'][:24]:<25} "
              f"{r['basic_salary']:>10,.0f} {r['status']}")
    print(f"\n  Total: {len(rows)} employees")


def view_employee_profile():
    emp_id = input("  Enter Employee ID: ").strip()
    rows = execute_query("""
        SELECT * FROM vw_employee_profile WHERE emp_id=?
    """, (emp_id,))
    if not rows:
        print(f"  Employee {emp_id} not found.")
        return
    r = dict(rows[0])
    print("\n" + separator())
    print(f"  EMPLOYEE PROFILE - {r['full_name']}")
    print(separator("-"))
    for k, v in r.items():
        print(f"  {k.replace('_',' ').title():<25}: {v}")


def add_employee():
    print("\n  ADD NEW EMPLOYEE")
    print("  (Enter details or press Enter to skip optional fields)")
    try:
        emp_code   = input("  Employee Code (e.g. EMP031): ").strip()
        first_name = input("  First Name: ").strip()
        last_name  = input("  Last Name: ").strip()
        gender     = input("  Gender [Male/Female/Other]: ").strip()
        dob        = input("  DOB (YYYY-MM-DD): ").strip()
        email      = input("  Email: ").strip()
        phone      = input("  Phone: ").strip()
        address    = input("  Address: ").strip()
        city       = input("  City: ").strip()
        state      = input("  State: ").strip()
        pan        = input("  PAN Number: ").strip()
        aadhaar    = input("  Last 4 digits of Aadhaar: ").strip()
        bank_acc   = input("  Bank Account: ").strip()
        bank_name  = input("  Bank Name: ").strip()
        ifsc       = input("  IFSC Code: ").strip()
        dept_id    = int(input("  Department ID: ").strip())
        desig_id   = int(input("  Designation ID: ").strip())
        grade_id   = int(input("  Grade ID: ").strip())
        basic      = float(input("  Basic Salary: ").strip())
        joined     = input("  Date Joined (YYYY-MM-DD): ").strip()

        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO employees(
                emp_code, first_name, last_name, gender, dob, email, phone, address,
                city, state, pan_number, aadhaar_last4, bank_account, bank_name, ifsc_code,
                dept_id, desig_id, grade_id, basic_salary, date_joined
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (emp_code, first_name, last_name, gender, dob, email, phone, address,
              city, state, pan, aadhaar, bank_acc, bank_name, ifsc,
              dept_id, desig_id, grade_id, basic, joined))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        print(f"\n  [✓] Employee added with ID: {new_id}")
    except Exception as e:
        print(f"\n  [✗] Error: {e}")


# ────────────────────────────────────────────────────────────────
# Payroll handlers
# ────────────────────────────────────────────────────────────────
def list_payroll_periods():
    rows = execute_query("""
        SELECT p.period_id, p.period_name, p.working_days, p.status,
               COUNT(pr.payroll_id) AS records
        FROM payroll_periods p
        LEFT JOIN payroll_records pr ON p.period_id = pr.period_id
        GROUP BY p.period_id ORDER BY p.year DESC, p.month DESC
    """)
    print("\n" + separator())
    print(f"  {'ID':<5} {'PERIOD':<20} {'WORK DAYS':>10} {'PAYROLL RECS':>13} {'STATUS'}")
    print(separator("-"))
    for r in rows:
        print(f"  {r['period_id']:<5} {r['period_name']:<20} {r['working_days']:>10} "
              f"{r['records']:>13} {r['status']}")


def process_payroll():
    list_payroll_periods()
    try:
        period_id = int(input("\n  Enter Period ID to process: ").strip())
        print(f"\n  Generating payroll for period {period_id}...")
        result = generate_payroll(period_id)
        if "error" in result:
            print(f"  [✗] {result['error']}")
        else:
            print(f"  [✓] Processed: {len(result['success'])} employees")
            if result["failed"]:
                print(f"  [!] Failed: {len(result['failed'])}")
                for f in result["failed"]:
                    print(f"      EMP {f['emp_id']}: {f['error']}")
    except Exception as e:
        print(f"  [✗] Error: {e}")


def view_payslip():
    try:
        emp_id    = int(input("  Enter Employee ID: ").strip())
        period_id = int(input("  Enter Period ID: ").strip())
        print("\n" + report_payslip(emp_id, period_id))
    except Exception as e:
        print(f"  [✗] Error: {e}")


# ────────────────────────────────────────────────────────────────
# Demo - Run all key reports
# ────────────────────────────────────────────────────────────────
def run_demo():
    print("\n" + separator())
    print("  DEMO MODE - Running key reports on sample data")
    print(separator())

    # Payroll register for period 24 (March 2026)
    print(report_payroll_register(24))
    input("\n  [Press Enter to continue...]")

    # Payslip for emp 1, period 24
    print(report_payslip(1, 24))
    input("\n  [Press Enter to continue...]")

    # Department summary
    print(report_department_summary(24))
    input("\n  [Press Enter to continue...]")

    # YTD
    print(report_ytd_salary(2026))
    input("\n  [Press Enter to continue...]")

    # Attendance
    print(report_attendance_summary(2026, 3))
    input("\n  [Press Enter to continue...]")

    # Loans
    print(report_loan_outstanding())
    input("\n  [Press Enter to continue...]")

    # Salary revisions
    print(report_salary_revisions())
    input("\n  [Press Enter to continue...]")

    # Audit trail
    print(report_audit_trail(limit=20))
    input("\n  [Press Enter to continue...]")

    # CSV export
    result = export_payroll_csv(24)
    print(f"\n  {result}")


# ────────────────────────────────────────────────────────────────
# Database utilities
# ────────────────────────────────────────────────────────────────
def db_utilities():
    print("\n  DATABASE UTILITIES")
    print(separator("-"))
    print("  1. Show Table Record Counts")
    print("  2. Show DB Schema Objects")
    print("  3. Execute Custom SQL")
    print("  0. Back")
    ch = input("  Choice: ").strip()

    if ch == "1":
        tables = ["departments","designations","salary_grades","employees",
                  "payroll_periods","attendance","leave_types","leave_requests",
                  "deduction_types","tax_slabs","payroll_records","payroll_deductions",
                  "salary_revisions","audit_logs","employee_loans"]
        print("\n  TABLE RECORD COUNTS")
        print(separator("-"))
        conn = get_connection()
        total = 0
        for t in tables:
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"  {t:<30} {cnt:>6} records")
                total += cnt
            except:
                pass
        print(separator("-"))
        print(f"  {'TOTAL':<30} {total:>6} records")
        conn.close()

    elif ch == "2":
        conn = get_connection()
        rows = conn.execute("""
            SELECT type, name FROM sqlite_master
            WHERE type IN ('table','view','index','trigger')
            ORDER BY type, name
        """).fetchall()
        print("\n  DB SCHEMA OBJECTS")
        for r in rows:
            print(f"  {r[0].upper():<10} {r[1]}")
        conn.close()

    elif ch == "3":
        sql = input("  Enter SQL: ").strip()
        try:
            rows = execute_query(sql)
            if rows:
                cols = rows[0].keys()
                print("  " + " | ".join(f"{c}" for c in cols))
                print("  " + "-" * 60)
                for r in rows[:50]:
                    print("  " + " | ".join(str(r[c]) for c in cols))
            else:
                print("  No rows returned.")
        except Exception as e:
            print(f"  Error: {e}")


# ────────────────────────────────────────────────────────────────
# Reports handler
# ────────────────────────────────────────────────────────────────
def handle_reports(ch):
    if ch == "1":
        list_payroll_periods()
        pid = int(input("\n  Enter Period ID: ").strip())
        print(report_payroll_register(pid))
    elif ch == "2":
        list_payroll_periods()
        pid = int(input("\n  Enter Period ID: ").strip())
        print(report_department_summary(pid))
    elif ch == "3":
        yr = int(input("  Enter Year (e.g. 2026): ").strip())
        print(report_ytd_salary(yr))
    elif ch == "4":
        yr = int(input("  Enter Year: ").strip())
        mo = int(input("  Enter Month (1-12): ").strip())
        print(report_attendance_summary(yr, mo))
    elif ch == "5":
        print(report_loan_outstanding())
    elif ch == "6":
        print(report_salary_revisions())
    elif ch == "7":
        tbl = input("  Table name (or Enter for all): ").strip() or None
        print(report_audit_trail(tbl))
    elif ch == "8":
        list_payroll_periods()
        pid = int(input("\n  Enter Period ID to export: ").strip())
        print(export_payroll_csv(pid))
    elif ch == "9":
        try:
            from diagrams.er_diagram import generate_er_diagram
            path = generate_er_diagram()
            print(f"\n  [✓] ER Diagram generated: {path}")
        except Exception as e:
            print(f"  [✗] Could not generate diagram: {e}")
            print("       Run: pip install matplotlib")


# ────────────────────────────────────────────────────────────────
# Main loop
# ────────────────────────────────────────────────────────────────
def run():
    banner()

    # Quick DB check
    try:
        rows = execute_query("SELECT COUNT(*) AS cnt FROM employees")
        emp_count = rows[0]["cnt"] if rows else 0
        print(f"\n  Database: {emp_count} employees loaded")
    except Exception as e:
        print(f"\n  [!] Database error: {e}")
        print("      Run setup first: python database/setup_db.py && python database/sample_data.py")
        return

    while True:
        ch = main_menu()

        if ch == "0":
            print("\n  Goodbye! Thank you for using PayrollWise.\n")
            break

        elif ch == "1":
            while True:
                ec = employee_menu()
                if ec == "0":
                    break
                elif ec == "1":
                    list_employees()
                elif ec == "2":
                    view_employee_profile()
                elif ec == "3":
                    add_employee()
                elif ec == "4":
                    emp_id = input("  Employee ID: ").strip()
                    status = input("  New Status [Active/Inactive/Terminated/On-Leave]: ").strip()
                    conn = get_connection()
                    conn.execute("UPDATE employees SET status=? WHERE emp_id=?", (status, emp_id))
                    conn.commit()
                    conn.close()
                    print("  [✓] Status updated")
                elif ec == "5":
                    print(report_salary_revisions())

        elif ch == "2":
            while True:
                pc = payroll_menu()
                if pc == "0":
                    break
                elif pc == "1":
                    list_payroll_periods()
                elif pc == "2":
                    process_payroll()
                elif pc == "3":
                    view_payslip()
                elif pc == "4":
                    list_payroll_periods()
                    pid = int(input("\n  Period ID to approve: ").strip())
                    r = approve_payroll(pid)
                    print(f"  [✓] Approved {r['approved_count']} payroll records")
                elif pc == "5":
                    list_payroll_periods()
                    pid  = int(input("\n  Period ID: ").strip())
                    pdate = input("  Payment Date (YYYY-MM-DD): ").strip()
                    r = mark_paid(pid, pdate)
                    print(f"  [✓] Marked {r['paid_count']} records as Paid")
                elif pc == "6":
                    list_payroll_periods()
                    pid = int(input("\n  Period ID: ").strip())
                    print(report_department_summary(pid))

        elif ch == "3":
            print("\n  ATTENDANCE & LEAVE")
            yr = int(input("  Year: ").strip() or "2026")
            mo = int(input("  Month (1-12): ").strip() or "3")
            print(report_attendance_summary(yr, mo))
            print(report_loan_outstanding())

        elif ch == "4":
            while True:
                rc = reports_menu()
                if rc == "0":
                    break
                try:
                    handle_reports(rc)
                except Exception as e:
                    print(f"  [✗] Error: {e}")

        elif ch == "5":
            db_utilities()

        elif ch == "6":
            run_demo()

        input("\n  [Press Enter to continue...]")


if __name__ == "__main__":
    run()
