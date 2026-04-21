"""
TASK 06: SQL Basics — Student-style queries on Payroll DB
TASK 07: Advanced SQL — Joins, Subqueries, Window Functions
TASK 08: Database Concepts — OLTP vs OLAP comparison
"""
import sqlite3, json, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
DB   = Path(__file__).parent.parent / "shared/database/payroll.db"
OUT  = BASE / "output"
OUT.mkdir(exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def run_query(conn, title, sql, params=()):
    t0 = time.time()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    elapsed = (time.time()-t0)*1000
    return rows, elapsed

def print_table(rows, title, elapsed=0, limit=10):
    if not rows:
        print(f"  {title}: No results")
        return
    cols = list(rows[0].keys())
    widths = [max(len(str(c)), max(len(str(r[c])) for r in rows[:limit])) for c in cols]
    widths = [min(w, 30) for w in widths]
    header = " | ".join(str(c)[:w].ljust(w) for c, w in zip(cols, widths))
    sep    = "-+-".join("-"*w for w in widths)
    print(f"\n  ── {title} ({len(rows)} rows, {elapsed:.1f}ms) ──")
    print("  " + header)
    print("  " + sep)
    for row in rows[:limit]:
        line = " | ".join(str(row[c])[:w].ljust(w) for c, w in zip(cols, widths))
        print("  " + line)
    if len(rows) > limit:
        print(f"  ... ({len(rows)-limit} more rows)")

# ══════════════════════════════════════════════════════════════
#  TASK 06: SQL BASICS
# ══════════════════════════════════════════════════════════════
BASIC_QUERIES = {
    "Q1 - SELECT: All active employees": """
        SELECT emp_code, first_name||' '||last_name AS full_name,
               email, basic_salary, date_joined, status
        FROM employees
        WHERE status = 'Active'
        ORDER BY emp_code
        LIMIT 10
    """,

    "Q2 - WHERE + AND: High earners in IT": """
        SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
               d.dept_name, e.basic_salary
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        WHERE e.basic_salary > 70000
          AND d.dept_name LIKE '%Technology%'
        ORDER BY e.basic_salary DESC
    """,

    "Q3 - GROUP BY + COUNT: Employees per department": """
        SELECT d.dept_name,
               COUNT(e.emp_id) AS total_employees,
               SUM(CASE WHEN e.status='Active' THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN e.status='Inactive' THEN 1 ELSE 0 END) AS inactive
        FROM departments d
        LEFT JOIN employees e ON d.dept_id = e.dept_id
        GROUP BY d.dept_id
        ORDER BY total_employees DESC
    """,

    "Q4 - GROUP BY + HAVING: Depts with avg salary > 80K": """
        SELECT d.dept_name,
               COUNT(e.emp_id) AS headcount,
               ROUND(AVG(e.basic_salary), 2) AS avg_salary,
               ROUND(MAX(e.basic_salary), 2) AS max_salary,
               ROUND(MIN(e.basic_salary), 2) AS min_salary
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        WHERE e.status = 'Active'
        GROUP BY d.dept_id
        HAVING avg_salary > 80000
        ORDER BY avg_salary DESC
    """,

    "Q5 - ORDER BY + LIMIT: Top 10 earners": """
        SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
               d.dept_name, ds.desig_title,
               e.basic_salary,
               ROUND(e.basic_salary * 12, 2) AS annual_salary
        FROM employees e
        JOIN departments d  ON e.dept_id  = d.dept_id
        JOIN designations ds ON e.desig_id = ds.desig_id
        ORDER BY e.basic_salary DESC
        LIMIT 10
    """,

    "Q6 - BETWEEN + IN: Mid-range IT & Finance staff": """
        SELECT e.emp_code, e.first_name||' '||e.last_name name,
               d.dept_name, e.basic_salary, e.employment_type
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        WHERE e.basic_salary BETWEEN 30000 AND 90000
          AND d.dept_name IN ('Information Technology','Finance & Accounts','Human Resources')
        ORDER BY d.dept_name, e.basic_salary DESC
    """,

    "Q7 - Aggregate: Payroll statistics by gender": """
        SELECT e.gender,
               COUNT(*) AS count,
               ROUND(AVG(e.basic_salary), 2) AS avg_salary,
               ROUND(SUM(e.basic_salary), 2) AS total_salary,
               ROUND(MAX(e.basic_salary), 2) AS max_salary
        FROM employees e
        WHERE e.status = 'Active'
        GROUP BY e.gender
        ORDER BY avg_salary DESC
    """,

    "Q8 - DATE functions: Experience by joining year": """
        SELECT strftime('%Y', date_joined) AS join_year,
               COUNT(*) AS employees,
               ROUND(AVG(basic_salary), 2) AS avg_salary,
               ROUND(AVG((julianday('now')-julianday(date_joined))/365.25), 1) AS avg_exp_years
        FROM employees
        WHERE status = 'Active'
        GROUP BY join_year
        ORDER BY join_year
    """,
}

# ══════════════════════════════════════════════════════════════
#  TASK 07: ADVANCED SQL
# ══════════════════════════════════════════════════════════════
ADVANCED_QUERIES = {
    "Q1 - INNER JOIN (3 tables): Payroll with full context": """
        SELECT pr.payroll_id, pp.period_name,
               e.emp_code, e.first_name||' '||e.last_name AS employee,
               d.dept_name, ds.desig_title,
               pr.gross_salary, pr.net_salary, pr.income_tax_tds,
               pr.pf_employee, pr.status
        FROM payroll_records pr
        JOIN employees e       ON pr.emp_id    = e.emp_id
        JOIN payroll_periods pp ON pr.period_id = pp.period_id
        JOIN departments d      ON e.dept_id    = d.dept_id
        JOIN designations ds    ON e.desig_id   = ds.desig_id
        WHERE pp.period_id = 24
        ORDER BY pr.net_salary DESC
        LIMIT 10
    """,

    "Q2 - LEFT JOIN: Employees without payroll (period 25)": """
        SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
               d.dept_name, e.status,
               pr.payroll_id,
               CASE WHEN pr.payroll_id IS NULL THEN 'NO PAYROLL' ELSE 'Has Payroll' END AS payroll_status
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        LEFT JOIN payroll_records pr ON e.emp_id = pr.emp_id AND pr.period_id = 25
        ORDER BY payroll_status DESC, e.emp_code
    """,

    "Q3 - Subquery: Employees earning above dept average": """
        SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
               d.dept_name, e.basic_salary,
               dept_avg.avg_salary AS dept_avg_salary,
               ROUND((e.basic_salary - dept_avg.avg_salary) / dept_avg.avg_salary * 100, 1) AS pct_above_avg
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        JOIN (
            SELECT dept_id, ROUND(AVG(basic_salary), 2) AS avg_salary
            FROM employees WHERE status='Active'
            GROUP BY dept_id
        ) dept_avg ON e.dept_id = dept_avg.dept_id
        WHERE e.basic_salary > dept_avg.avg_salary
          AND e.status = 'Active'
        ORDER BY pct_above_avg DESC
        LIMIT 10
    """,

    "Q4 - CTE: 3-month payroll trend": """
        WITH monthly_payroll AS (
            SELECT pp.period_name, pp.year, pp.month,
                   COUNT(pr.payroll_id) AS employees_paid,
                   ROUND(SUM(pr.gross_salary), 2) AS total_gross,
                   ROUND(SUM(pr.net_salary), 2) AS total_net,
                   ROUND(SUM(pr.income_tax_tds), 2) AS total_tds,
                   ROUND(AVG(pr.net_salary), 2) AS avg_net
            FROM payroll_records pr
            JOIN payroll_periods pp ON pr.period_id = pp.period_id
            WHERE pr.status = 'Paid'
            GROUP BY pp.period_id
        )
        SELECT period_name, employees_paid, total_gross, total_net,
               total_tds, avg_net
        FROM monthly_payroll
        ORDER BY year DESC, month DESC
        LIMIT 6
    """,

    "Q5 - Window ROW_NUMBER: Salary rank within dept": """
        SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
               d.dept_name, e.basic_salary,
               ROW_NUMBER() OVER (PARTITION BY d.dept_name ORDER BY e.basic_salary DESC) AS rank_in_dept,
               ROUND(SUM(e.basic_salary) OVER (PARTITION BY d.dept_name), 2) AS dept_total_salary,
               ROUND(AVG(e.basic_salary) OVER (PARTITION BY d.dept_name), 2) AS dept_avg_salary
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        WHERE e.status = 'Active'
        ORDER BY d.dept_name, rank_in_dept
        LIMIT 20
    """,

    "Q6 - Window LAG/LEAD: Month-over-month payroll change": """
        WITH monthly AS (
            SELECT pp.period_name, pp.year, pp.month,
                   ROUND(SUM(pr.net_salary), 2) AS total_net
            FROM payroll_records pr
            JOIN payroll_periods pp ON pr.period_id = pp.period_id
            WHERE pr.status='Paid'
            GROUP BY pp.period_id
        )
        SELECT period_name,
               total_net,
               LAG(total_net) OVER (ORDER BY year, month) AS prev_month_net,
               ROUND(total_net - LAG(total_net) OVER (ORDER BY year, month), 2) AS mom_change,
               ROUND((total_net - LAG(total_net) OVER (ORDER BY year, month))
                     / LAG(total_net) OVER (ORDER BY year, month) * 100, 2) AS mom_pct
        FROM monthly
        ORDER BY year DESC, month DESC
        LIMIT 8
    """,

    "Q7 - Window NTILE: Salary quartile analysis": """
        SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
               d.dept_name, e.basic_salary,
               NTILE(4) OVER (ORDER BY e.basic_salary) AS salary_quartile,
               CASE NTILE(4) OVER (ORDER BY e.basic_salary)
                   WHEN 1 THEN 'Q1 (Bottom 25%)'
                   WHEN 2 THEN 'Q2 (25-50%)'
                   WHEN 3 THEN 'Q3 (50-75%)'
                   WHEN 4 THEN 'Q4 (Top 25%)'
               END AS quartile_label,
               ROUND(PERCENT_RANK() OVER (ORDER BY e.basic_salary) * 100, 1) AS percentile
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        WHERE e.status = 'Active'
        ORDER BY e.basic_salary DESC
        LIMIT 15
    """,

    "Q8 - Correlated subquery: Employees with active loans": """
        SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
               d.dept_name, e.basic_salary,
               (SELECT ROUND(SUM(outstanding), 2)
                FROM employee_loans l
                WHERE l.emp_id = e.emp_id AND l.status='Active') AS total_outstanding,
               (SELECT COUNT(*)
                FROM employee_loans l
                WHERE l.emp_id = e.emp_id AND l.status='Active') AS active_loans
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        WHERE EXISTS (
            SELECT 1 FROM employee_loans l
            WHERE l.emp_id = e.emp_id AND l.status='Active'
        )
        ORDER BY total_outstanding DESC
    """,

    "Q9 - ROLLUP-style: Dept+Grade salary summary": """
        SELECT d.dept_name, sg.grade_name,
               COUNT(e.emp_id) AS headcount,
               ROUND(SUM(e.basic_salary), 2) AS total_salary,
               ROUND(AVG(e.basic_salary), 2) AS avg_salary
        FROM employees e
        JOIN departments d ON e.dept_id = d.dept_id
        JOIN salary_grades sg ON e.grade_id = sg.grade_id
        WHERE e.status='Active'
        GROUP BY d.dept_name, sg.grade_name
        ORDER BY d.dept_name, avg_salary DESC
        LIMIT 20
    """,

    "Q10 - Full business report: YTD salary with running total": """
        WITH ytd AS (
            SELECT e.emp_code, e.first_name||' '||e.last_name AS name,
                   d.dept_name,
                   COUNT(pr.payroll_id) AS months,
                   ROUND(SUM(pr.gross_salary), 2) AS ytd_gross,
                   ROUND(SUM(pr.net_salary), 2) AS ytd_net,
                   ROUND(SUM(pr.income_tax_tds), 2) AS ytd_tds
            FROM payroll_records pr
            JOIN employees e ON pr.emp_id = e.emp_id
            JOIN payroll_periods pp ON pr.period_id = pp.period_id
            JOIN departments d ON e.dept_id = d.dept_id
            WHERE pp.year = 2026 AND pr.status = 'Paid'
            GROUP BY e.emp_id
        )
        SELECT name, dept_name, months, ytd_gross, ytd_net, ytd_tds,
               ROUND(SUM(ytd_net) OVER (ORDER BY ytd_net DESC
                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total_net,
               ROUND(ytd_tds / ytd_gross * 100, 2) AS effective_tax_pct
        FROM ytd
        ORDER BY ytd_net DESC
    """,
}

# ══════════════════════════════════════════════════════════════
#  TASK 08: OLTP vs OLAP
# ══════════════════════════════════════════════════════════════
def explain_oltp_vs_olap():
    return {
        "OLTP (Online Transaction Processing)": {
            "purpose": "Day-to-day operational transactions",
            "payroll_example": "Payroll processing, employee updates, attendance marking",
            "characteristics": {
                "query_type":   "Short INSERT/UPDATE/DELETE transactions",
                "data_volume":  "Current operational data (GBs)",
                "response_time":"Milliseconds",
                "concurrency":  "Thousands of concurrent users",
                "normalization":"Highly normalized (3NF+) to avoid anomalies",
                "indexes":      "On FK, status, emp_code for fast lookups",
            },
            "schema_example": "employees → payroll_records → payroll_periods (normalized)",
            "our_db_tables":  ["employees","payroll_records","attendance","leave_requests"],
        },
        "OLAP (Online Analytical Processing)": {
            "purpose": "Historical analysis, reporting, BI dashboards",
            "payroll_example": "Annual salary trends, dept cost analysis, TDS reports",
            "characteristics": {
                "query_type":   "Complex SELECT with GROUP BY, window functions",
                "data_volume":  "Historical aggregated data (TBs)",
                "response_time":"Seconds to minutes (acceptable for batch reports)",
                "concurrency":  "Few analytical users",
                "normalization":"Denormalized (star/snowflake) for fast reads",
                "indexes":      "Column-store indexes, partitioning by year/month",
            },
            "schema_example": "fact_payroll → dim_employee, dim_dept, dim_time (star schema)",
            "use_cases":      ["YTD reports","Dept cost dashboards","Tax liability forecasting"],
        },
        "Key Differences": {
            "Data Model":   "OLTP=Normalized | OLAP=Denormalized",
            "Query Pattern":"OLTP=CRUD | OLAP=Aggregations",
            "Optimization": "OLTP=Row-store | OLAP=Column-store",
            "Backup":       "OLTP=Continuous | OLAP=Periodic",
            "Tools":        "OLTP=PostgreSQL/MySQL/SQLite | OLAP=BigQuery/Redshift/Snowflake",
        }
    }

def run():
    print("="*60)
    print("  TASK 06: SQL Basics")
    print("  TASK 07: Advanced SQL")
    print("  TASK 08: OLTP vs OLAP")
    print("="*60)

    conn = get_conn()

    print("\n══ TASK 06: SQL BASICS QUERIES ══")
    basic_results = {}
    for qname, sql in BASIC_QUERIES.items():
        rows, elapsed = run_query(conn, qname, sql)
        print_table(rows, qname, elapsed, limit=5)
        basic_results[qname] = {"rows": len(rows), "elapsed_ms": round(elapsed,2)}

    print("\n══ TASK 07: ADVANCED SQL QUERIES ══")
    adv_results = {}
    for qname, sql in ADVANCED_QUERIES.items():
        rows, elapsed = run_query(conn, qname, sql)
        print_table(rows, qname, elapsed, limit=5)
        adv_results[qname] = {"rows": len(rows), "elapsed_ms": round(elapsed,2)}

    print("\n══ TASK 08: OLTP vs OLAP COMPARISON ══")
    comparison = explain_oltp_vs_olap()
    for system, info in comparison.items():
        print(f"\n  {system}:")
        for k, v in info.items():
            if isinstance(v, dict):
                print(f"    {k}:")
                for sk, sv in v.items():
                    print(f"      {sk}: {sv}")
            else:
                v_str = str(v)[:80]
                print(f"    {k}: {v_str}")

    conn.close()

    # Save results
    output = {
        "task06_basic_queries": basic_results,
        "task07_advanced_queries": adv_results,
        "task08_oltp_vs_olap": comparison,
        "timestamp": datetime.now().isoformat()
    }
    (OUT/"sql_results.json").write_text(json.dumps(output, indent=2, default=str))
    print(f"\n✓ SQL results saved: {OUT}/sql_results.json")
    return output

if __name__ == "__main__":
    run()
