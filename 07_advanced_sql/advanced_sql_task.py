"""
TASK 07: Advanced SQL — Joins, Subqueries, Window Functions
Business Reporting Scenarios for Payroll System
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

def run_and_print(conn, title, sql, limit=8):
    t0 = time.time()
    rows = [dict(r) for r in conn.execute(sql).fetchall()]
    ms   = round((time.time()-t0)*1000, 2)
    cols = list(rows[0].keys()) if rows else []
    widths = [min(max(len(c), max((len(str(r.get(c,""))) for r in rows[:limit]), default=4)), 28) for c in cols]
    hdr = " | ".join(c[:w].ljust(w) for c,w in zip(cols,widths))
    sep = "-+-".join("-"*w for w in widths)
    print(f"\n  ── {title} ({len(rows)} rows, {ms}ms) ──")
    print(f"  {hdr}")
    print(f"  {sep}")
    for r in rows[:limit]:
        print("  " + " | ".join(str(r.get(c,""))[:w].ljust(w) for c,w in zip(cols,widths)))
    if len(rows) > limit:
        print(f"  ... {len(rows)-limit} more rows")
    return rows

QUERIES = {
    # ── JOINS ─────────────────────────────────────────────────
    "JOIN-1: 5-table INNER JOIN — Full Payslip View": """
        SELECT pr.payroll_id,
               pp.period_name,
               e.emp_code,
               e.first_name||' '||e.last_name        AS employee,
               d.dept_name,
               ds.desig_title,
               sg.grade_code,
               ROUND(pr.basic_salary,2)               AS basic,
               ROUND(pr.gross_salary,2)               AS gross,
               ROUND(pr.total_deductions,2)            AS deductions,
               ROUND(pr.net_salary,2)                  AS net,
               pr.status
        FROM   payroll_records pr
        JOIN   employees       e   ON pr.emp_id    = e.emp_id
        JOIN   payroll_periods pp  ON pr.period_id = pp.period_id
        JOIN   departments     d   ON e.dept_id    = d.dept_id
        JOIN   designations    ds  ON e.desig_id   = ds.desig_id
        JOIN   salary_grades   sg  ON e.grade_id   = sg.grade_id
        WHERE  pp.period_id = 24
        ORDER  BY pr.net_salary DESC
    """,

    "JOIN-2: LEFT JOIN — Employees With No Payroll This Period": """
        SELECT e.emp_code,
               e.first_name||' '||e.last_name  AS name,
               d.dept_name,
               e.status,
               CASE WHEN pr.payroll_id IS NULL
                    THEN '⚠ NO PAYROLL' ELSE '✓ Processed' END AS payroll_status
        FROM   employees e
        JOIN   departments d ON e.dept_id = d.dept_id
        LEFT   JOIN payroll_records pr
               ON e.emp_id = pr.emp_id AND pr.period_id = 25
        ORDER  BY payroll_status DESC, e.emp_code
    """,

    "JOIN-3: SELF JOIN — Employee vs Their Manager Salary": """
        SELECT e.emp_code                               AS emp_code,
               e.first_name||' '||e.last_name           AS employee,
               d.dept_name,
               e.basic_salary                            AS emp_salary,
               mgr.first_name||' '||mgr.last_name        AS manager_name,
               mgr.basic_salary                          AS mgr_salary,
               ROUND(e.basic_salary/mgr.basic_salary*100,1) AS pct_of_mgr_salary
        FROM   employees e
        JOIN   departments d   ON e.dept_id  = d.dept_id
        JOIN   employees   mgr ON d.manager_id = mgr.emp_id
        WHERE  d.manager_id IS NOT NULL
          AND  e.emp_id != d.manager_id
        ORDER  BY pct_of_mgr_salary DESC
        LIMIT  10
    """,

    # ── SUBQUERIES ─────────────────────────────────────────────
    "SUB-1: Scalar Subquery — vs Company Average Salary": """
        SELECT e.emp_code,
               e.first_name||' '||e.last_name  AS name,
               d.dept_name,
               e.basic_salary,
               (SELECT ROUND(AVG(basic_salary),2) FROM employees WHERE status='Active') AS company_avg,
               ROUND(e.basic_salary -
                     (SELECT AVG(basic_salary) FROM employees WHERE status='Active'), 2) AS vs_avg
        FROM   employees e
        JOIN   departments d ON e.dept_id = d.dept_id
        WHERE  e.status = 'Active'
        ORDER  BY vs_avg DESC
        LIMIT  10
    """,

    "SUB-2: IN Subquery — Depts Exceeding Budget 5%": """
        SELECT d.dept_code,
               d.dept_name,
               d.budget,
               ROUND(SUM(e.basic_salary)*12, 2)   AS annual_salary_cost,
               ROUND(SUM(e.basic_salary)*12 - d.budget, 2) AS over_budget
        FROM   departments d
        JOIN   employees   e ON d.dept_id = e.dept_id
        WHERE  e.status = 'Active'
          AND  d.dept_id IN (
               SELECT dept_id
               FROM   employees
               WHERE  status = 'Active'
               GROUP  BY dept_id
               HAVING SUM(basic_salary)*12 > 0
          )
        GROUP  BY d.dept_id
        HAVING annual_salary_cost > d.budget * 0.10
        ORDER  BY over_budget DESC
    """,

    "SUB-3: EXISTS — Employees With Active Loans": """
        SELECT e.emp_code,
               e.first_name||' '||e.last_name  AS name,
               d.dept_name,
               e.basic_salary,
               (SELECT ROUND(SUM(l.outstanding),2) FROM employee_loans l
                WHERE l.emp_id = e.emp_id AND l.status='Active') AS total_loan_outstanding,
               (SELECT COUNT(*) FROM employee_loans l
                WHERE l.emp_id = e.emp_id AND l.status='Active')  AS active_loans
        FROM   employees e
        JOIN   departments d ON e.dept_id = d.dept_id
        WHERE  EXISTS (
               SELECT 1 FROM employee_loans l
               WHERE l.emp_id = e.emp_id AND l.status = 'Active'
        )
        ORDER  BY total_loan_outstanding DESC
    """,

    # ── WINDOW FUNCTIONS ───────────────────────────────────────
    "WIN-1: RANK & DENSE_RANK — Salary Ranking": """
        SELECT e.emp_code,
               e.first_name||' '||e.last_name        AS name,
               d.dept_name,
               e.basic_salary,
               RANK()       OVER (ORDER BY e.basic_salary DESC)              AS company_rank,
               DENSE_RANK() OVER (ORDER BY e.basic_salary DESC)              AS company_dense_rank,
               RANK()       OVER (PARTITION BY d.dept_name
                                  ORDER BY e.basic_salary DESC)              AS dept_rank,
               ROUND(PERCENT_RANK() OVER (ORDER BY e.basic_salary)*100, 1)  AS percentile
        FROM   employees e
        JOIN   departments d ON e.dept_id = d.dept_id
        WHERE  e.status = 'Active'
        ORDER  BY e.basic_salary DESC
        LIMIT  15
    """,

    "WIN-2: LAG / LEAD — Month-over-Month Net Change": """
        WITH monthly AS (
            SELECT pp.period_name,
                   pp.year,
                   pp.month,
                   ROUND(SUM(pr.net_salary),2)  AS total_net
            FROM   payroll_records pr
            JOIN   payroll_periods pp ON pr.period_id = pp.period_id
            WHERE  pr.status = 'Paid'
            GROUP  BY pp.period_id
        )
        SELECT period_name,
               total_net,
               LAG(total_net)  OVER (ORDER BY year, month) AS prev_net,
               LEAD(total_net) OVER (ORDER BY year, month) AS next_net,
               ROUND(total_net -
                     LAG(total_net) OVER (ORDER BY year, month), 2)        AS mom_change,
               ROUND((total_net -
                     LAG(total_net) OVER (ORDER BY year, month)) /
                     LAG(total_net) OVER (ORDER BY year, month) * 100, 2)  AS mom_pct_change
        FROM   monthly
        ORDER  BY year DESC, month DESC
        LIMIT  8
    """,

    "WIN-3: RUNNING TOTAL & MOVING AVERAGE": """
        WITH monthly AS (
            SELECT pp.period_name,
                   pp.year,
                   pp.month,
                   ROUND(SUM(pr.net_salary),2) AS net
            FROM   payroll_records pr
            JOIN   payroll_periods pp ON pr.period_id = pp.period_id
            WHERE  pr.status = 'Paid'
            GROUP  BY pp.period_id
        )
        SELECT period_name,
               net,
               SUM(net) OVER (ORDER BY year, month
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)  AS running_total,
               ROUND(AVG(net) OVER (ORDER BY year, month
                              ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)      AS moving_avg_3m
        FROM   monthly
        ORDER  BY year, month
        LIMIT  12
    """,

    "WIN-4: NTILE & Salary Quartiles": """
        WITH ranked AS (
            SELECT e.emp_code,
                   e.first_name||' '||e.last_name   AS name,
                   d.dept_name,
                   e.basic_salary,
                   NTILE(4) OVER (ORDER BY e.basic_salary) AS quartile,
                   ROUND(PERCENT_RANK() OVER (ORDER BY e.basic_salary)*100,1) AS percentile
            FROM   employees e
            JOIN   departments d ON e.dept_id = d.dept_id
            WHERE  e.status = 'Active'
        )
        SELECT *,
               CASE quartile
                   WHEN 1 THEN 'Q1 Bottom 25%'
                   WHEN 2 THEN 'Q2 25-50%'
                   WHEN 3 THEN 'Q3 50-75%'
                   WHEN 4 THEN 'Q4 Top 25%'
               END AS quartile_label
        FROM   ranked
        ORDER  BY basic_salary DESC
    """,

    "WIN-5: FIRST_VALUE / LAST_VALUE per Dept": """
        SELECT d.dept_name,
               e.emp_code,
               e.first_name||' '||e.last_name                       AS name,
               e.basic_salary,
               FIRST_VALUE(e.first_name||' '||e.last_name)
                   OVER (PARTITION BY d.dept_name
                         ORDER BY e.basic_salary DESC
                         ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS highest_earner,
               FIRST_VALUE(e.first_name||' '||e.last_name)
                   OVER (PARTITION BY d.dept_name
                         ORDER BY e.basic_salary ASC
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS lowest_earner,
               ROUND(AVG(e.basic_salary)
                   OVER (PARTITION BY d.dept_name), 2)              AS dept_avg
        FROM   employees e
        JOIN   departments d ON e.dept_id = d.dept_id
        WHERE  e.status = 'Active'
        ORDER  BY d.dept_name, e.basic_salary DESC
        LIMIT  20
    """,

    # ── CTE + COMPLEX REPORTING ────────────────────────────────
    "CTE-1: Recursive-style YTD + MoM in one query": """
        WITH payroll_base AS (
            SELECT e.emp_id,
                   e.emp_code,
                   e.first_name||' '||e.last_name  AS name,
                   d.dept_name,
                   pp.year,
                   pp.month,
                   pp.period_name,
                   pr.gross_salary,
                   pr.net_salary,
                   pr.income_tax_tds                AS tds
            FROM   payroll_records pr
            JOIN   employees       e  ON pr.emp_id    = e.emp_id
            JOIN   departments     d  ON e.dept_id    = d.dept_id
            JOIN   payroll_periods pp ON pr.period_id = pp.period_id
            WHERE  pr.status = 'Paid'
        ),
        ytd AS (
            SELECT emp_id, emp_code, name, dept_name, year,
                   COUNT(*)                    AS months_paid,
                   ROUND(SUM(net_salary), 2)   AS ytd_net,
                   ROUND(SUM(tds), 2)          AS ytd_tds,
                   ROUND(AVG(net_salary), 2)   AS avg_monthly_net,
                   ROUND(MAX(net_salary), 2)   AS max_monthly_net,
                   ROUND(MIN(net_salary), 2)   AS min_monthly_net
            FROM   payroll_base
            WHERE  year = 2026
            GROUP  BY emp_id, year
        )
        SELECT ytd.*,
               ROUND(ytd_tds / ytd_net * 100, 2) AS effective_tax_rate_pct,
               RANK() OVER (ORDER BY ytd_net DESC) AS ytd_rank
        FROM   ytd
        ORDER  BY ytd_net DESC
        LIMIT  10
    """,

    "CTE-2: Payroll Cost vs Budget Report": """
        WITH dept_payroll AS (
            SELECT e.dept_id,
                   COUNT(DISTINCT pr.emp_id)       AS headcount,
                   ROUND(SUM(pr.gross_salary), 2)  AS monthly_gross,
                   ROUND(SUM(pr.net_salary), 2)    AS monthly_net,
                   ROUND(SUM(pr.pf_employer), 2)   AS employer_pf,
                   ROUND(SUM(pr.esi_employer), 2)  AS employer_esi
            FROM   payroll_records pr
            JOIN   employees e ON pr.emp_id = e.emp_id
            WHERE  pr.period_id = 24
            GROUP  BY e.dept_id
        )
        SELECT d.dept_code,
               d.dept_name,
               d.location,
               dp.headcount,
               dp.monthly_gross,
               dp.employer_pf + dp.employer_esi      AS employer_burden,
               ROUND(dp.monthly_gross * 12, 2)        AS projected_annual_cost,
               d.budget                               AS approved_budget,
               ROUND(dp.monthly_gross * 12 - d.budget, 2)  AS budget_variance,
               CASE
                   WHEN dp.monthly_gross * 12 > d.budget * 1.05 THEN '🔴 Over Budget'
                   WHEN dp.monthly_gross * 12 > d.budget * 0.90 THEN '🟡 On Track'
                   ELSE '🟢 Under Budget'
               END                                    AS budget_status
        FROM   departments d
        JOIN   dept_payroll dp ON d.dept_id = dp.dept_id
        ORDER  BY budget_variance DESC
    """,
}

def run():
    print("="*65)
    print("  TASK 07: Advanced SQL")
    print("  Joins, Subqueries, Window Functions, CTEs")
    print("  Business Reporting — Payroll Automation System")
    print("="*65)

    conn = get_conn()
    results = {}

    for title, sql in QUERIES.items():
        rows = run_and_print(conn, title, sql)
        results[title] = {"rows": len(rows), "sample": rows[:2]}

    conn.close()

    # Save results
    (OUT / "advanced_sql_results.json").write_text(
        json.dumps(results, indent=2, default=str))
    print(f"\n✓ {len(QUERIES)} advanced queries executed")
    print(f"✓ Results saved: {OUT}/advanced_sql_results.json")
    return results

if __name__ == "__main__":
    run()
