"""
TASK 03: Python Basics — CSV Read, Clean & Merge
Reads multiple payroll-related CSV files, cleans missing
values, and merges into a unified dataset.
"""
import csv, os, json, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)

# ── Generate Sample Multi-CSV Payroll Dataset ─────────────────
def create_sample_csvs():
    csvs = {
        "employees.csv": [
            ["emp_id","emp_code","first_name","last_name","dept","designation","basic_salary","gender","dob","email","date_joined","status"],
            [1,"EMP001","Rajesh","Kumar","HR","HR Executive",45000,"Male","1985-03-15","rajesh.kumar@pw.in","2018-06-01","Active"],
            [2,"EMP002","Priya","Sharma","HR","HR Manager",125000,"Female","1990-07-22","priya.sharma@pw.in","2016-03-15","Active"],
            [3,"EMP003","Amit","Patel","IT","Software Engineer",65000,"Male","1988-11-08","amit.patel@pw.in","2019-09-01","Active"],
            [4,"EMP004","Sneha","Reddy","Support","HR Executive",30000,"Female","","sneha.reddy@pw.in","2021-01-10","Active"],
            [5,"EMP005","Vikram","Singh","Sales","Sales Executive","","Male","1983-12-19","","2017-08-20","Active"],
            [6,"EMP006","Ananya","Iyer","Finance","Accounts Executive",28000,"Female","1994-06-14","ananya.iyer@pw.in","2022-03-01",""],
            [7,"EMP007","Rohit","Gupta","IT","Senior SWE",88000,"Male","1987-09-25","rohit.gupta@pw.in","2015-05-12","Active"],
            [8,"","Kavitha","Menon","Analytics","Data Scientist",72000,"Female","1991-02-18","kavitha.menon@pw.in","2020-07-01","Active"],
            [9,"EMP009","Sanjay","Nair","Ops","Ops Analyst",44000,"Male","","sanjay.nair@pw.in","2018-11-15","Inactive"],
            [10,"EMP010","Deepa","Joshi","R&D","Research Scientist",95000,"Female","1993-05-28","","2019-02-01","Active"],
        ],
        "payroll_jan2026.csv": [
            ["payroll_id","emp_id","period","working_days","days_present","basic","hra","da","gross","pf","tds","net","status"],
            [1,1,"Jan-2026",27,25,45000,13500,7650,67650,1800,"",65850,"Paid"],
            [2,2,"Jan-2026",27,27,125000,50000,22500,202500,1800,25500,"","Paid"],
            [3,3,"Jan-2026",27,26,65000,19500,11050,96850,1800,5600,89450,"Paid"],
            [4,4,"Jan-2026",27,27,30000,3000,4500,37500,1800,"",35700,"Paid"],
            [5,5,"Jan-2026",27,25,38000,7600,6460,53460,1800,"",51660,"Paid"],
            [6,6,"Jan-2026",27,24,28000,2800,4200,34200,1800,"",32400,"Paid"],
            [7,7,"Jan-2026",27,"",88000,33440,15840,"",1800,5200,"","Draft"],
            [8,8,"Jan-2026",27,26,72000,21600,12240,107640,1800,3500,102340,"Paid"],
            [9,9,"Jan-2026",27,20,44000,13200,7480,65000,1800,"",63200,"Paid"],
            [10,10,"Jan-2026",27,27,95000,38000,17100,151300,1800,14400,135100,"Paid"],
        ],
        "attendance_jan2026.csv": [
            ["att_id","emp_id","month","year","days_present","days_absent","leave_days","overtime_hrs","late_arrivals"],
            [1,1,"January",2026,25,2,0,4,2],
            [2,2,"January",2026,27,0,0,0,""],
            [3,3,"January",2026,26,1,0,6,1],
            [4,4,"January",2026,27,0,0,0,0],
            [5,5,"January",2026,25,2,0,0,3],
            [6,6,"January",2026,24,3,0,"",2],
            [7,7,"January",2026,"",0,0,0,0],
            [8,8,"January",2026,26,1,0,8,0],
            [9,9,"January",2026,20,7,0,0,5],
            [10,10,"January",2026,27,0,0,12,0],
        ],
        "departments.csv": [
            ["dept_code","dept_name","location","budget","manager"],
            ["HR","Human Resources","Mumbai",4500000,"Priya Sharma"],
            ["IT","Information Technology","Bengaluru",8500000,""],
            ["Sales","Sales & Marketing","Delhi",6200000,"Vikram Singh"],
            ["Finance","Finance & Accounts","Mumbai",3800000,"Ananya Iyer"],
            ["Support","Customer Support","Hyderabad",3200000,""],
            ["Ops","Operations","Pune",5100000,"Sanjay Nair"],
            ["R&D","Research & Development","Bengaluru",9200000,"Deepa Joshi"],
            ["Analytics","Data Science","Bengaluru","","Kavitha Menon"],
        ]
    }
    for fname, rows in csvs.items():
        fp = OUTPUT / fname
        with open(fp, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        print(f"  Created: {fname} ({len(rows)-1} records)")
    return list(csvs.keys())

# ── Read CSV ──────────────────────────────────────────────────
def read_csv(filepath):
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

# ── Cleaning Functions ─────────────────────────────────────────
def clean_employees(rows):
    cleaned, issues = [], []
    for i, row in enumerate(rows, 1):
        orig = dict(row)
        # Fix missing emp_code
        if not row["emp_code"].strip():
            row["emp_code"] = f"EMP{int(row['emp_id']):03d}"
            issues.append(f"Row {i}: Generated emp_code={row['emp_code']}")
        # Fix missing basic_salary
        if not row["basic_salary"].strip():
            row["basic_salary"] = "0"
            issues.append(f"Row {i}: Set basic_salary=0 (was missing)")
        # Fix missing status
        if not row["status"].strip():
            row["status"] = "Unknown"
            issues.append(f"Row {i}: Set status=Unknown")
        # Fix missing dob
        if not row["dob"].strip():
            row["dob"] = "1990-01-01"
            issues.append(f"Row {i}: Set dob=1990-01-01 (placeholder)")
        # Fix missing email
        if not row["email"].strip():
            fn = row["first_name"].lower(); ln = row["last_name"].lower()
            row["email"] = f"{fn}.{ln}@payrollwise.in"
            issues.append(f"Row {i}: Generated email={row['email']}")
        # Type conversion
        row["emp_id"] = int(row["emp_id"])
        row["basic_salary"] = float(row["basic_salary"])
        cleaned.append(row)
    return cleaned, issues

def clean_payroll(rows):
    cleaned, issues = [], []
    dept_avg_gross = 96000  # fallback average
    for i, row in enumerate(rows, 1):
        # Fill missing days_present
        if not row["days_present"].strip():
            row["days_present"] = row["working_days"]
            issues.append(f"Row {i}: days_present assumed=working_days")
        # Fill missing gross
        if not row["gross"].strip():
            basic = float(row["basic"] or 0)
            row["gross"] = str(round(basic * 1.55, 2))
            issues.append(f"Row {i}: Computed gross from basic")
        # Fill missing net
        if not row["net"].strip():
            gross = float(row["gross"])
            pf    = float(row["pf"] or 0)
            tds   = float(row["tds"] or 0)
            row["net"] = str(round(gross - pf - tds, 2))
            issues.append(f"Row {i}: Computed net=gross-pf-tds")
        # Fill missing tds → 0
        if not row["tds"].strip():
            row["tds"] = "0"
        # Type conversion
        for f in ["emp_id","working_days","days_present"]:
            try: row[f] = int(float(row[f]))
            except: row[f] = 0
        for f in ["basic","hra","da","gross","pf","tds","net"]:
            try: row[f] = float(row[f])
            except: row[f] = 0.0
        cleaned.append(row)
    return cleaned, issues

def clean_attendance(rows):
    cleaned, issues = [], []
    for i, row in enumerate(rows, 1):
        if not row["days_present"].strip():
            row["days_present"] = "0"
            issues.append(f"Row {i}: Set days_present=0")
        if not row["overtime_hrs"].strip():
            row["overtime_hrs"] = "0"
        if not row["late_arrivals"].strip():
            row["late_arrivals"] = "0"
        for f in ["emp_id","days_present","days_absent","leave_days"]:
            try: row[f] = int(float(row[f]))
            except: row[f] = 0
        for f in ["overtime_hrs","late_arrivals"]:
            try: row[f] = float(row[f])
            except: row[f] = 0.0
        cleaned.append(row)
    return cleaned, issues

# ── Merge Datasets ────────────────────────────────────────────
def merge_datasets(employees, payroll, attendance, departments):
    # Build lookup maps
    emp_map  = {e["emp_id"]: e for e in employees}
    att_map  = {a["emp_id"]: a for a in attendance}
    dept_map = {d["dept_code"]: d for d in departments}

    merged = []
    for pay in payroll:
        eid = pay["emp_id"]
        emp = emp_map.get(eid, {})
        att = att_map.get(eid, {})
        dept_code = emp.get("dept", "")
        dept = dept_map.get(dept_code, {})

        record = {
            # Employee info
            "emp_id":       eid,
            "emp_code":     emp.get("emp_code", ""),
            "full_name":    f"{emp.get('first_name','')} {emp.get('last_name','')}".strip(),
            "gender":       emp.get("gender", ""),
            "dept_name":    dept.get("dept_name", dept_code),
            "dept_location":dept.get("location", ""),
            "designation":  emp.get("designation", ""),
            "emp_status":   emp.get("status", ""),
            # Payroll
            "period":       pay["period"],
            "working_days": pay["working_days"],
            "days_present": pay["days_present"],
            "basic":        pay["basic"],
            "hra":          pay["hra"],
            "da":           pay["da"],
            "gross":        pay["gross"],
            "pf":           pay["pf"],
            "tds":          pay["tds"],
            "net":          pay["net"],
            "pay_status":   pay["status"],
            # Attendance
            "days_absent":  att.get("days_absent", 0),
            "overtime_hrs": att.get("overtime_hrs", 0),
            "late_arrivals":att.get("late_arrivals", 0),
            # Derived
            "take_home_pct":round(pay["net"] / pay["gross"] * 100, 1) if pay["gross"] else 0,
            "attendance_pct":round(pay["days_present"] / pay["working_days"] * 100, 1) if pay["working_days"] else 0,
        }
        merged.append(record)
    return merged

# ── Save Merged CSV ───────────────────────────────────────────
def save_merged(merged, filename="merged_payroll_data.csv"):
    if not merged: return
    fp = OUTPUT / filename
    with open(fp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=merged[0].keys())
        w.writeheader(); w.writerows(merged)
    print(f"  Merged file: {fp.name} ({len(merged)} records)")
    return fp

# ── Summary Stats ─────────────────────────────────────────────
def summary_stats(merged):
    gross_values = [r["gross"] for r in merged if r["gross"] > 0]
    net_values   = [r["net"]   for r in merged if r["net"]   > 0]
    return {
        "total_employees":   len(merged),
        "total_gross":       round(sum(gross_values), 2),
        "total_net":         round(sum(net_values), 2),
        "avg_gross":         round(sum(gross_values)/len(gross_values), 2) if gross_values else 0,
        "avg_net":           round(sum(net_values)  /len(net_values),   2) if net_values   else 0,
        "avg_attendance_pct":round(sum(r["attendance_pct"] for r in merged)/len(merged), 1),
        "dept_breakdown":    _dept_breakdown(merged),
    }

def _dept_breakdown(merged):
    dept = defaultdict(lambda: {"count":0,"total_net":0})
    for r in merged:
        d = r["dept_name"]
        dept[d]["count"] += 1
        dept[d]["total_net"] += r["net"]
    return {k: {"count":v["count"],"avg_net":round(v["total_net"]/v["count"],2)} for k,v in dept.items()}

def run():
    print("="*60)
    print("  TASK 03: Python Basics — CSV Clean & Merge")
    print("="*60)

    print("\n[1] Creating sample CSV files...")
    create_sample_csvs()

    print("\n[2] Reading CSV files...")
    emp_raw  = read_csv(OUTPUT/"employees.csv")
    pay_raw  = read_csv(OUTPUT/"payroll_jan2026.csv")
    att_raw  = read_csv(OUTPUT/"attendance_jan2026.csv")
    dept_raw = read_csv(OUTPUT/"departments.csv")
    print(f"  employees: {len(emp_raw)} rows, payroll: {len(pay_raw)} rows, attendance: {len(att_raw)} rows, depts: {len(dept_raw)} rows")

    print("\n[3] Cleaning datasets...")
    employees, emp_issues = clean_employees(emp_raw)
    print(f"  Employees — {len(emp_issues)} issues fixed:")
    for iss in emp_issues: print(f"    • {iss}")

    payroll, pay_issues = clean_payroll(pay_raw)
    print(f"  Payroll — {len(pay_issues)} issues fixed:")
    for iss in pay_issues: print(f"    • {iss}")

    attendance, att_issues = clean_attendance(att_raw)
    print(f"  Attendance — {len(att_issues)} issues fixed")

    print("\n[4] Merging datasets...")
    merged = merge_datasets(employees, payroll, attendance, dept_raw)
    print(f"  Merged {len(merged)} records (10 employees × 3 datasets)")

    print("\n[5] Saving merged output...")
    save_merged(merged)

    print("\n[6] Summary Statistics:")
    stats = summary_stats(merged)
    print(f"  Total Employees : {stats['total_employees']}")
    print(f"  Total Gross     : ₹{stats['total_gross']:,.2f}")
    print(f"  Total Net       : ₹{stats['total_net']:,.2f}")
    print(f"  Avg Gross       : ₹{stats['avg_gross']:,.2f}")
    print(f"  Avg Net         : ₹{stats['avg_net']:,.2f}")
    print(f"  Avg Attendance  : {stats['avg_attendance_pct']}%")
    print(f"\n  Dept Breakdown:")
    for dept, info in stats["dept_breakdown"].items():
        print(f"    {dept:25} count={info['count']} avg_net=₹{info['avg_net']:,.2f}")

    (OUTPUT/"summary_stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(f"\n✓ Summary saved: {OUTPUT}/summary_stats.json")
    return merged, stats

if __name__ == "__main__":
    run()
