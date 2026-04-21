"""
TASK 08: Database Concepts — OLTP vs OLAP
Schema design, use cases, and performance comparison
for the Payroll Automation System
"""
import sqlite3, json, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
DB   = Path(__file__).parent.parent / "shared/database/payroll.db"
OUT  = BASE / "output"
OUT.mkdir(exist_ok=True)

# ── OLTP Schema (already built — our payroll.db) ──────────────
OLTP_DESCRIPTION = {
    "name":    "Payroll OLTP (Online Transaction Processing)",
    "purpose": "Day-to-day payroll operations: process salaries, update attendance, approve leaves",
    "design_principles": [
        "Normalized to 3NF — no data redundancy",
        "Row-oriented storage — fast for single-row lookups",
        "Optimized for INSERT / UPDATE / DELETE",
        "Enforces referential integrity (FK constraints)",
        "Short-lived transactions (ms response time)",
        "Supports concurrent access by many users",
    ],
    "our_tables": {
        "employees":       "Employee master — updated on join/exit/promotion",
        "payroll_records": "One row per employee per month — written monthly",
        "attendance":      "Written daily for 30 employees = 900 rows/month",
        "leave_requests":  "CRUD operations as requests are raised/approved",
        "salary_grades":   "Lookup table — rarely changed",
    },
    "typical_queries": [
        "SELECT * FROM employees WHERE emp_id = 5",
        "INSERT INTO payroll_records (...) VALUES (...)",
        "UPDATE employees SET status='Inactive' WHERE emp_id=12",
        "SELECT * FROM attendance WHERE emp_id=3 AND att_date='2026-03-01'",
    ],
    "indexes_used": [
        "idx_emp_dept   — fast department-wise employee lookup",
        "idx_att_emp_date — composite: fast attendance lookup by emp+date",
        "idx_payroll_period — fast payroll run queries",
        "idx_emp_status — filter active employees quickly",
    ]
}

# ── OLAP Schema (analytical / reporting layer) ─────────────────
OLAP_SCHEMA_SQL = """
-- ═══════════════════════════════════════════════════════════════
--  PAYROLL OLAP SCHEMA (Star Schema)
--  Optimized for analytical queries, aggregations, BI dashboards
-- ═══════════════════════════════════════════════════════════════

-- Dimension: Employee (full snapshot, denormalized)
CREATE TABLE IF NOT EXISTS olap_dim_employee (
    emp_key         INTEGER PRIMARY KEY,
    emp_id          INTEGER,
    emp_code        TEXT,
    full_name       TEXT,
    gender          TEXT,
    age_group       TEXT,       -- Pre-computed: '25-30', '30-35' etc
    city            TEXT,
    state           TEXT,
    dept_name       TEXT,       -- Denormalized from departments
    dept_location   TEXT,
    desig_title     TEXT,       -- Denormalized from designations
    grade_name      TEXT,       -- Denormalized from salary_grades
    salary_band     TEXT,       -- Pre-computed: 'Low', 'Mid', 'High', 'Senior'
    employment_type TEXT,
    tenure_years    INTEGER,    -- Pre-computed at load time
    is_current      INTEGER DEFAULT 1
);

-- Dimension: Calendar (for time-series analysis)
CREATE TABLE IF NOT EXISTS olap_dim_date (
    date_key        INTEGER PRIMARY KEY,  -- YYYYMMDD format
    full_date       TEXT,
    day             INTEGER,
    month           INTEGER,
    month_name      TEXT,
    quarter         INTEGER,
    quarter_name    TEXT,       -- 'Q1 FY26', 'Q2 FY26' etc
    year            INTEGER,
    fiscal_year     TEXT,       -- 'FY2025-26'
    is_weekend      INTEGER,
    is_holiday      INTEGER DEFAULT 0,
    working_day_num INTEGER    -- Sequential working day number in month
);

-- Dimension: Pay Grade
CREATE TABLE IF NOT EXISTS olap_dim_grade (
    grade_key   INTEGER PRIMARY KEY,
    grade_code  TEXT,
    grade_name  TEXT,
    band        TEXT,       -- 'Junior','Mid','Senior','Lead','Management'
    basic_min   REAL,
    basic_max   REAL,
    hra_pct     REAL,
    da_pct      REAL
);

-- Fact: Payroll (central analytical table)
CREATE TABLE IF NOT EXISTS olap_fact_payroll (
    -- Keys
    payroll_key     INTEGER PRIMARY KEY,
    emp_key         INTEGER,
    date_key        INTEGER,    -- Points to month-start date
    grade_key       INTEGER,
    -- Degenerate dimensions
    payroll_id      INTEGER,
    period_name     TEXT,
    pay_status      TEXT,
    -- Attendance measures
    working_days    INTEGER,
    days_present    INTEGER,
    days_absent     INTEGER,
    attendance_pct  REAL,       -- Pre-computed
    -- Earnings measures
    basic_salary    REAL,
    hra             REAL,
    da              REAL,
    transport_allow REAL,
    gross_salary    REAL,
    -- Deduction measures
    pf_employee     REAL,
    pf_employer     REAL,       -- Employer cost
    esi_employee    REAL,
    esi_employer    REAL,
    professional_tax REAL,
    income_tax_tds  REAL,
    loan_deduction  REAL,
    total_deductions REAL,
    -- Net measures
    net_salary      REAL,
    annual_ctc      REAL,       -- Pre-computed: gross*12 + employer_pf*12
    -- Derived measures (pre-computed for performance)
    take_home_pct   REAL,
    tax_rate_pct    REAL,
    employer_cost   REAL,       -- gross + pf_employer + esi_employer
    -- Audit
    loaded_at       TEXT
);

-- Aggregate table: Pre-computed dept-month summaries (OLAP cube)
CREATE TABLE IF NOT EXISTS olap_agg_dept_month (
    dept_name       TEXT,
    year            INTEGER,
    month           INTEGER,
    quarter_name    TEXT,
    fiscal_year     TEXT,
    headcount       INTEGER,
    total_gross     REAL,
    total_net       REAL,
    total_tds       REAL,
    total_pf_emp    REAL,
    total_employer_cost REAL,
    avg_net         REAL,
    avg_basic       REAL,
    max_net         REAL,
    min_net         REAL,
    PRIMARY KEY (dept_name, year, month)
);
"""

OLAP_DESCRIPTION = {
    "name":    "Payroll OLAP (Online Analytical Processing)",
    "purpose": "Historical trend analysis, BI dashboards, executive reporting",
    "design_principles": [
        "Denormalized Star Schema — joins are expensive, pre-compute",
        "Column-oriented storage (Parquet/ORC) — fast aggregations",
        "Optimized for SELECT with GROUP BY, aggregates, window functions",
        "Pre-computed aggregates in aggregate tables",
        "Batch-loaded (ETL runs nightly/monthly)",
        "Few concurrent analytical users (not transactional)",
    ],
    "our_tables": {
        "olap_dim_employee": "Denormalized employee snapshot (all dept/desig/grade info in one row)",
        "olap_dim_date":     "Full calendar dimension with fiscal year, quarter pre-computed",
        "olap_dim_grade":    "Grade lookup with band categorization",
        "olap_fact_payroll": "Central fact table with ALL measures pre-joined and derived",
        "olap_agg_dept_month": "Pre-aggregated: total/avg/max by dept+month for fast dashboards",
    },
    "typical_queries": [
        "SELECT dept_name, SUM(net_salary) FROM olap_fact_payroll WHERE fiscal_year='FY2025-26' GROUP BY dept_name",
        "SELECT quarter_name, AVG(take_home_pct) FROM olap_fact_payroll JOIN olap_dim_date ... GROUP BY quarter_name",
        "SELECT * FROM olap_agg_dept_month WHERE fiscal_year='FY2025-26' ORDER BY total_gross DESC",
        "SELECT salary_band, COUNT(*), AVG(net_salary) FROM olap_fact_payroll JOIN olap_dim_employee ...",
    ],
}

COMPARISON_TABLE = {
    "Primary Goal":       {"OLTP": "Process transactions",       "OLAP": "Analyze historical data"},
    "Query Type":         {"OLTP": "INSERT/UPDATE/DELETE/SELECT", "OLAP": "Complex SELECT + GROUP BY + JOINs"},
    "Data Model":         {"OLTP": "Highly normalized (3NF+)",   "OLAP": "Denormalized (Star/Snowflake)"},
    "Data Volume":        {"OLTP": "Current data (GBs)",         "OLAP": "Historical data (TBs–PBs)"},
    "Response Time":      {"OLTP": "Milliseconds",               "OLAP": "Seconds to minutes"},
    "Concurrency":        {"OLTP": "1000s of users/transactions","OLAP": "10s of analytical users"},
    "Optimization":       {"OLTP": "Row storage, FK indexes",    "OLAP": "Column storage, pre-aggregates"},
    "Update Frequency":   {"OLTP": "Continuous (real-time)",     "OLAP": "Batch (nightly/monthly ETL)"},
    "Schema Flexibility": {"OLTP": "Rigid, normalized",          "OLAP": "Flexible, additive"},
    "Backup Strategy":    {"OLTP": "Continuous / WAL logs",      "OLAP": "Periodic snapshots"},
    "Tools":              {"OLTP": "SQLite/PostgreSQL/MySQL",     "OLAP": "BigQuery/Redshift/Snowflake"},
    "Payroll OLTP Eg":    {"OLTP": "Process April payroll run",  "OLAP": "Q4 salary trend analysis"},
    "Payroll OLAP Eg":    {"OLTP": "Mark attendance",            "OLAP": "3-year dept cost dashboard"},
}

def build_olap_db():
    """Build the OLAP schema and populate with denormalized payroll data."""
    olap_db = OUT / "payroll_olap.db"
    if olap_db.exists(): olap_db.unlink()

    olap_conn = sqlite3.connect(olap_db)
    olap_conn.executescript(OLAP_SCHEMA_SQL)

    # Load from OLTP
    oltp_conn = sqlite3.connect(DB); oltp_conn.row_factory = sqlite3.Row
    rows = oltp_conn.execute("""
        SELECT pr.payroll_id,
               e.emp_id, e.emp_code,
               e.first_name||' '||e.last_name  AS full_name,
               e.gender, e.city, e.state, e.employment_type,
               e.date_joined,
               d.dept_name, d.location         AS dept_location,
               ds.desig_title,
               sg.grade_code, sg.grade_name,
               pp.period_name, pp.year, pp.month, pp.working_days,
               pr.basic_salary, pr.hra, pr.da, pr.transport_allow,
               pr.gross_salary, pr.pf_employee, pr.pf_employer,
               pr.esi_employee, pr.esi_employer, pr.professional_tax,
               pr.income_tax_tds, pr.loan_deduction, pr.total_deductions,
               pr.net_salary, pr.days_present, pr.days_absent, pr.status
        FROM   payroll_records pr
        JOIN   employees       e  ON pr.emp_id    = e.emp_id
        JOIN   departments     d  ON e.dept_id    = d.dept_id
        JOIN   designations    ds ON e.desig_id   = ds.desig_id
        JOIN   salary_grades   sg ON e.grade_id   = sg.grade_id
        JOIN   payroll_periods pp ON pr.period_id = pp.period_id
        WHERE  pr.status = 'Paid'
    """).fetchall()
    oltp_conn.close()

    loaded = 0
    for r in rows:
        gross = r["gross_salary"] or 0
        net   = r["net_salary"]   or 0
        basic = r["basic_salary"] or 0

        salary_band = ("Senior" if basic >= 200000 else
                       "Lead"   if basic >= 100000 else
                       "Mid"    if basic >= 50000  else "Junior")

        tenure = max(0, int((datetime.now() -
                    datetime.strptime(r["date_joined"], "%Y-%m-%d")).days / 365))

        age_group = "N/A"  # we don't store age in payroll for privacy

        q = ((r["month"]-1)//3) + 1
        fy = (f"FY{r['year']}-{str(r['year']+1)[-2:]}"
              if r["month"] >= 4 else
              f"FY{r['year']-1}-{str(r['year'])[-2:]}")

        olap_conn.execute("""
            INSERT OR IGNORE INTO olap_dim_employee VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
        """, (r["emp_id"], r["emp_id"], r["emp_code"], r["full_name"], r["gender"],
              age_group, r["city"], r["state"], r["dept_name"], r["dept_location"],
              r["desig_title"], r["grade_name"], salary_band, r["employment_type"], tenure))

        date_key = r["year"] * 10000 + r["month"] * 100 + 1
        olap_conn.execute("""
            INSERT OR IGNORE INTO olap_dim_date VALUES(?,?,1,?,?,?,?,?,?,0,0,1)
        """, (date_key, f"{r['year']}-{r['month']:02d}-01",
              r["month"], f"Month {r['month']}", q,
              f"Q{q} FY{r['year']}", r["year"], fy))

        take_home = round(net/gross*100, 2) if gross else 0
        tax_rate  = round((r["income_tax_tds"] or 0)/gross*100, 2) if gross else 0
        emp_cost  = round(gross + (r["pf_employer"] or 0) + (r["esi_employer"] or 0), 2)
        annual_ctc= round(gross * 12 + (r["pf_employer"] or 0)*12, 2)

        olap_conn.execute("""
            INSERT OR IGNORE INTO olap_fact_payroll
            (emp_key,date_key,grade_key,payroll_id,period_name,pay_status,
             working_days,days_present,days_absent,attendance_pct,
             basic_salary,hra,da,transport_allow,gross_salary,
             pf_employee,pf_employer,esi_employee,esi_employer,professional_tax,
             income_tax_tds,loan_deduction,total_deductions,net_salary,
             annual_ctc,take_home_pct,tax_rate_pct,employer_cost,loaded_at)
            VALUES(?,?,1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (r["emp_id"], date_key,
              r["payroll_id"], r["period_name"], r["status"],
              r["working_days"], r["days_present"], r["days_absent"],
              round(r["days_present"]/(r["working_days"] or 1)*100,1),
              basic, r["hra"] or 0, r["da"] or 0, r["transport_allow"] or 0, gross,
              r["pf_employee"] or 0, r["pf_employer"] or 0,
              r["esi_employee"] or 0, r["esi_employer"] or 0,
              r["professional_tax"] or 0, r["income_tax_tds"] or 0,
              r["loan_deduction"] or 0, r["total_deductions"] or 0,
              net, annual_ctc, take_home, tax_rate, emp_cost,
              datetime.now().isoformat()))
        loaded += 1

    # Build aggregate table
    olap_conn.execute("DELETE FROM olap_agg_dept_month")
    olap_conn.execute("""
        INSERT INTO olap_agg_dept_month
        SELECT
            de.dept_name,
            dd.year, dd.month, dd.quarter_name, dd.fiscal_year,
            COUNT(*)                      AS headcount,
            ROUND(SUM(f.gross_salary),2)  AS total_gross,
            ROUND(SUM(f.net_salary),2)    AS total_net,
            ROUND(SUM(f.income_tax_tds),2) AS total_tds,
            ROUND(SUM(f.pf_employee),2)   AS total_pf_emp,
            ROUND(SUM(f.employer_cost),2) AS total_employer_cost,
            ROUND(AVG(f.net_salary),2)    AS avg_net,
            ROUND(AVG(f.basic_salary),2)  AS avg_basic,
            ROUND(MAX(f.net_salary),2)    AS max_net,
            ROUND(MIN(f.net_salary),2)    AS min_net
        FROM   olap_fact_payroll f
        JOIN   olap_dim_employee de ON f.emp_key = de.emp_key AND de.is_current=1
        JOIN   olap_dim_date     dd ON f.date_key = dd.date_key
        GROUP  BY de.dept_name, dd.year, dd.month
    """)

    olap_conn.commit()
    counts = {t: olap_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["olap_dim_employee","olap_dim_date","olap_fact_payroll","olap_agg_dept_month"]}
    olap_conn.close()
    return olap_db, counts

def run_olap_queries(olap_db):
    """Run analytical queries on the OLAP schema."""
    conn = sqlite3.connect(olap_db); conn.row_factory = sqlite3.Row

    queries = {
        "Dept Cost by Quarter (from agg table — fastest)": """
            SELECT dept_name, quarter_name, fiscal_year,
                   headcount, total_gross, total_net, avg_net, total_employer_cost
            FROM   olap_agg_dept_month
            ORDER  BY fiscal_year, quarter_name, total_gross DESC
            LIMIT  12
        """,
        "Salary Band Distribution": """
            SELECT de.salary_band,
                   COUNT(DISTINCT de.emp_key)  AS employees,
                   ROUND(AVG(f.net_salary),2)  AS avg_net,
                   ROUND(SUM(f.net_salary),2)  AS total_net
            FROM   olap_fact_payroll f
            JOIN   olap_dim_employee de ON f.emp_key = de.emp_key AND de.is_current=1
            GROUP  BY de.salary_band
            ORDER  BY avg_net DESC
        """,
        "Employment Type vs Net Salary": """
            SELECT de.employment_type,
                   COUNT(DISTINCT f.emp_key)  AS count,
                   ROUND(AVG(f.net_salary),2) AS avg_net,
                   ROUND(MIN(f.net_salary),2) AS min_net,
                   ROUND(MAX(f.net_salary),2) AS max_net
            FROM   olap_fact_payroll f
            JOIN   olap_dim_employee de ON f.emp_key = de.emp_key AND de.is_current=1
            GROUP  BY de.employment_type
        """,
    }

    results = {}
    for name, sql in queries.items():
        t0 = time.time()
        rows = [dict(r) for r in conn.execute(sql).fetchall()]
        ms   = round((time.time()-t0)*1000, 2)
        print(f"\n  [{name}] — {len(rows)} rows in {ms}ms")
        for row in rows[:5]:
            print(f"    {row}")
        results[name] = rows[:5]

    conn.close()
    return results

def run():
    print("="*65)
    print("  TASK 08: Database Concepts — OLTP vs OLAP")
    print("="*65)

    print("\n══ OLTP SYSTEM (Our payroll.db) ══")
    print(f"\n  Name: {OLTP_DESCRIPTION['name']}")
    print(f"  Purpose: {OLTP_DESCRIPTION['purpose']}")
    print(f"\n  Design Principles:")
    for p in OLTP_DESCRIPTION["design_principles"]:
        print(f"    • {p}")
    print(f"\n  Tables & Usage:")
    for t, desc in OLTP_DESCRIPTION["our_tables"].items():
        print(f"    {t:<20} → {desc}")
    print(f"\n  Typical Queries:")
    for q in OLTP_DESCRIPTION["typical_queries"]:
        print(f"    {q}")

    print("\n══ BUILDING OLAP SCHEMA ══")
    olap_db, counts = build_olap_db()
    print(f"\n  OLAP DB: {olap_db}")
    print(f"  Tables populated:")
    for t, c in counts.items():
        print(f"    {t:<30} {c:>4} rows")

    print("\n══ OLAP SYSTEM (payroll_olap.db) ══")
    print(f"\n  Name: {OLAP_DESCRIPTION['name']}")
    print(f"  Purpose: {OLAP_DESCRIPTION['purpose']}")
    print(f"\n  Design Principles:")
    for p in OLAP_DESCRIPTION["design_principles"]:
        print(f"    • {p}")

    print("\n══ RUNNING OLAP QUERIES ══")
    olap_results = run_olap_queries(olap_db)

    print("\n══ OLTP vs OLAP COMPARISON ══")
    print(f"\n  {'Feature':<22} {'OLTP':^30} {'OLAP':^30}")
    print("  " + "─"*84)
    for feat, vals in COMPARISON_TABLE.items():
        print(f"  {feat:<22} {vals['OLTP']:<30} {vals['OLAP']:<30}")

    # Performance comparison
    print("\n══ PERFORMANCE COMPARISON ══")
    oltp_conn = sqlite3.connect(DB); oltp_conn.row_factory = sqlite3.Row
    olap_conn = sqlite3.connect(olap_db); olap_conn.row_factory = sqlite3.Row

    test_queries = [
        ("Dept total net (OLTP — joins)", oltp_conn, """
            SELECT d.dept_name, ROUND(SUM(pr.net_salary),2) total_net
            FROM payroll_records pr JOIN employees e ON pr.emp_id=e.emp_id
            JOIN departments d ON e.dept_id=d.dept_id WHERE pr.period_id=24
            GROUP BY d.dept_id ORDER BY total_net DESC
        """),
        ("Dept total net (OLAP — agg table)", olap_conn, """
            SELECT dept_name, total_net FROM olap_agg_dept_month
            WHERE year=2026 AND month=3 ORDER BY total_net DESC
        """),
    ]
    print(f"\n  {'Query':<40} {'Time':>10} {'Rows':>6}")
    print("  " + "─"*60)
    for name, conn, sql in test_queries:
        t0 = time.time()
        rows = conn.execute(sql).fetchall()
        ms = round((time.time()-t0)*1000, 3)
        print(f"  {name:<40} {ms:>8.3f}ms {len(rows):>6}")

    oltp_conn.close(); olap_conn.close()

    result = {
        "oltp": OLTP_DESCRIPTION,
        "olap_counts": counts,
        "comparison": COMPARISON_TABLE,
        "olap_query_results": {k: len(v) for k, v in olap_results.items()},
        "timestamp": datetime.now().isoformat()
    }
    (OUT/"db_concepts_results.json").write_text(json.dumps(result, indent=2, default=str))
    print(f"\n✓ OLAP DB: {olap_db}")
    print(f"✓ Results: {OUT}/db_concepts_results.json")
    return result

if __name__ == "__main__":
    run()
