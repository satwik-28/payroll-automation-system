"""
TASK 09: Data Warehousing — Star Schema for Payroll Analytics
TASK 10: ETL vs ELT Pipeline Comparison
TASK 11: Batch Data Ingestion (CSV → Database)
"""
import sqlite3, csv, json, time, os, shutil
from pathlib import Path
from datetime import datetime, timedelta
import random

BASE = Path(__file__).parent
DB_OLTP = Path(__file__).parent.parent / "shared/database/payroll.db"
DB_DW   = BASE / "payroll_datawarehouse.db"
DB_STAGING = BASE / "staging.db"
OUTPUT  = BASE / "output"
OUTPUT.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  TASK 09: STAR SCHEMA DATA WAREHOUSE
# ══════════════════════════════════════════════════════════════
STAR_SCHEMA_DDL = """
-- ═══════════════════════════════════════════════
--  PAYROLL ANALYTICS STAR SCHEMA
-- ═══════════════════════════════════════════════

PRAGMA foreign_keys = ON;

-- DIM: Time
CREATE TABLE IF NOT EXISTS dim_time (
    time_id     INTEGER PRIMARY KEY,
    full_date   TEXT NOT NULL UNIQUE,
    day         INTEGER, week INTEGER, month INTEGER, quarter INTEGER, year INTEGER,
    month_name  TEXT, day_name TEXT, is_weekend INTEGER, fiscal_year TEXT
);

-- DIM: Employee (slowly changing type 2)
CREATE TABLE IF NOT EXISTS dim_employee (
    emp_key     INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id      INTEGER NOT NULL,
    emp_code    TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    gender      TEXT, city TEXT, state TEXT,
    pan_number  TEXT,
    employment_type TEXT, status TEXT,
    effective_from TEXT, effective_to TEXT,
    is_current  INTEGER DEFAULT 1,
    row_hash    TEXT
);

-- DIM: Department
CREATE TABLE IF NOT EXISTS dim_department (
    dept_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_id     INTEGER NOT NULL UNIQUE,
    dept_code   TEXT, dept_name TEXT, location TEXT, budget REAL
);

-- DIM: Designation
CREATE TABLE IF NOT EXISTS dim_designation (
    desig_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    desig_id    INTEGER NOT NULL UNIQUE,
    desig_title TEXT, level_rank INTEGER
);

-- DIM: Salary Grade
CREATE TABLE IF NOT EXISTS dim_salary_grade (
    grade_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_id    INTEGER NOT NULL UNIQUE,
    grade_code  TEXT, grade_name TEXT,
    basic_min   REAL, basic_max REAL,
    hra_pct REAL, da_pct REAL, ta_flat REAL
);

-- DIM: Period
CREATE TABLE IF NOT EXISTS dim_period (
    period_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id   INTEGER NOT NULL UNIQUE,
    period_name TEXT, month INTEGER, year INTEGER,
    working_days INTEGER, start_date TEXT, end_date TEXT,
    quarter TEXT, fiscal_year TEXT
);

-- FACT: Payroll
CREATE TABLE IF NOT EXISTS fact_payroll (
    fact_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Foreign Keys to Dimensions
    emp_key         INTEGER NOT NULL REFERENCES dim_employee(emp_key),
    dept_key        INTEGER NOT NULL REFERENCES dim_department(dept_key),
    desig_key       INTEGER NOT NULL REFERENCES dim_designation(desig_key),
    grade_key       INTEGER NOT NULL REFERENCES dim_salary_grade(grade_key),
    period_key      INTEGER NOT NULL REFERENCES dim_period(period_key),
    -- Degenerate dimensions
    payroll_id      INTEGER,
    payment_ref     TEXT,
    pay_status      TEXT,
    payment_date    TEXT,
    -- Measures: Attendance
    working_days    INTEGER, days_present INTEGER, days_absent INTEGER, days_leave INTEGER,
    -- Measures: Earnings
    basic_salary    REAL, hra REAL, da REAL, transport_allow REAL,
    other_allowances REAL, gross_salary REAL,
    -- Measures: Deductions
    pf_employee     REAL, pf_employer REAL,
    esi_employee    REAL, esi_employer REAL,
    professional_tax REAL, income_tax_tds REAL,
    loan_deduction  REAL, other_deductions REAL, total_deductions REAL,
    -- Measures: Net
    net_salary      REAL,
    -- Derived measures
    effective_tax_rate REAL,
    take_home_ratio REAL,
    -- Audit
    loaded_at TEXT DEFAULT (datetime('now')),
    UNIQUE(payroll_id)
);

-- FACT: Attendance Daily
CREATE TABLE IF NOT EXISTS fact_attendance (
    att_fact_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_key       INTEGER NOT NULL REFERENCES dim_employee(emp_key),
    dept_key      INTEGER NOT NULL REFERENCES dim_department(dept_key),
    period_key    INTEGER NOT NULL REFERENCES dim_period(period_key),
    att_date      TEXT NOT NULL,
    att_status    TEXT,
    hours_worked  REAL DEFAULT 0,
    is_present    INTEGER DEFAULT 0,
    is_late       INTEGER DEFAULT 0
);

-- AGGREGATE: Pre-computed dept monthly summary (OLAP optimization)
CREATE TABLE IF NOT EXISTS agg_dept_monthly (
    agg_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_key     INTEGER REFERENCES dim_department(dept_key),
    period_key   INTEGER REFERENCES dim_period(period_key),
    headcount    INTEGER, total_gross REAL, total_net REAL,
    avg_net REAL, employer_cost REAL, total_tds REAL,
    last_updated TEXT DEFAULT (datetime('now'))
);

-- Indexes for analytical queries
CREATE INDEX IF NOT EXISTS idx_fact_payroll_period ON fact_payroll(period_key);
CREATE INDEX IF NOT EXISTS idx_fact_payroll_dept   ON fact_payroll(dept_key);
CREATE INDEX IF NOT EXISTS idx_fact_payroll_emp    ON fact_payroll(emp_key);
CREATE INDEX IF NOT EXISTS idx_dim_emp_current     ON dim_employee(is_current, emp_id);
"""

def build_star_schema():
    """Create and populate star schema DW."""
    print("[DW] Building star schema...")
    if DB_DW.exists(): DB_DW.unlink()

    dw = sqlite3.connect(DB_DW)
    dw.executescript(STAR_SCHEMA_DDL)
    dw.commit()

    # Load from OLTP
    oltp = sqlite3.connect(DB_OLTP)
    oltp.row_factory = sqlite3.Row

    # Populate dim_department
    depts = oltp.execute("SELECT * FROM departments").fetchall()
    dw.executemany("INSERT OR IGNORE INTO dim_department(dept_id,dept_code,dept_name,location,budget) VALUES(?,?,?,?,?)",
                   [(d["dept_id"],d["dept_code"],d["dept_name"],d["location"],d["budget"]) for d in depts])

    # Populate dim_designation
    desigs = oltp.execute("SELECT * FROM designations").fetchall()
    dw.executemany("INSERT OR IGNORE INTO dim_designation(desig_id,desig_title,level_rank) VALUES(?,?,?)",
                   [(d["desig_id"],d["desig_title"],d["level_rank"]) for d in desigs])

    # Populate dim_salary_grade
    grades = oltp.execute("SELECT * FROM salary_grades").fetchall()
    dw.executemany("INSERT OR IGNORE INTO dim_salary_grade(grade_id,grade_code,grade_name,basic_min,basic_max,hra_pct,da_pct,ta_flat) VALUES(?,?,?,?,?,?,?,?)",
                   [(g["grade_id"],g["grade_code"],g["grade_name"],g["basic_min"],g["basic_max"],g["hra_pct"],g["da_pct"],g["ta_flat"]) for g in grades])

    # Populate dim_period
    periods = oltp.execute("SELECT * FROM payroll_periods").fetchall()
    for p in periods:
        q = f"Q{((p['month']-1)//3)+1}"
        fy = f"FY{p['year']}-{str(p['year']+1)[-2:]}" if p["month"] >= 4 else f"FY{p['year']-1}-{str(p['year'])[-2:]}"
        dw.execute("INSERT OR IGNORE INTO dim_period(period_id,period_name,month,year,working_days,start_date,end_date,quarter,fiscal_year) VALUES(?,?,?,?,?,?,?,?,?)",
                   (p["period_id"],p["period_name"],p["month"],p["year"],p["working_days"],p["start_date"],p["end_date"],q,fy))

    # Populate dim_employee (SCD Type 2)
    emps = oltp.execute("SELECT * FROM employees").fetchall()
    import hashlib
    for e in emps:
        row_hash = hashlib.md5(f"{e['basic_salary']}{e['dept_id']}{e['desig_id']}{e['grade_id']}".encode()).hexdigest()
        dw.execute("""INSERT OR IGNORE INTO dim_employee
            (emp_id,emp_code,full_name,gender,city,state,pan_number,employment_type,status,effective_from,is_current,row_hash)
            VALUES(?,?,?,?,?,?,?,?,?,?,1,?)""",
            (e["emp_id"],e["emp_code"],e["first_name"]+" "+e["last_name"],e["gender"],
             e["city"],e["state"],e["pan_number"],e["employment_type"],e["status"],e["date_joined"],row_hash))

    # Populate fact_payroll
    payrolls = oltp.execute("SELECT * FROM payroll_records WHERE status='Paid'").fetchall()
    loaded = 0
    for pr in payrolls:
        emp_key   = dw.execute("SELECT emp_key FROM dim_employee WHERE emp_id=? AND is_current=1", (pr["emp_id"],)).fetchone()
        dept_key  = oltp.execute("SELECT dept_id FROM employees WHERE emp_id=?", (pr["emp_id"],)).fetchone()
        desig_key = oltp.execute("SELECT desig_id FROM employees WHERE emp_id=?", (pr["emp_id"],)).fetchone()
        grade_key = oltp.execute("SELECT grade_id FROM employees WHERE emp_id=?", (pr["emp_id"],)).fetchone()
        period_key = dw.execute("SELECT period_key FROM dim_period WHERE period_id=?", (pr["period_id"],)).fetchone()
        dept_key2 = dw.execute("SELECT dept_key FROM dim_department WHERE dept_id=?", (dept_key[0],)).fetchone() if dept_key else None
        desig_key2= dw.execute("SELECT desig_key FROM dim_designation WHERE desig_id=?", (desig_key[0],)).fetchone() if desig_key else None
        grade_key2= dw.execute("SELECT grade_key FROM dim_salary_grade WHERE grade_id=?", (grade_key[0],)).fetchone() if grade_key else None

        if all([emp_key, dept_key2, desig_key2, grade_key2, period_key]):
            eff_tax = round(pr["income_tax_tds"]/pr["gross_salary"]*100,2) if pr["gross_salary"] else 0
            take_home = round(pr["net_salary"]/pr["gross_salary"]*100,2) if pr["gross_salary"] else 0
            try:
                dw.execute("""INSERT OR IGNORE INTO fact_payroll
                    (payroll_id,emp_key,dept_key,desig_key,grade_key,period_key,
                     pay_status,payment_date,working_days,days_present,days_absent,days_leave,
                     basic_salary,hra,da,transport_allow,other_allowances,gross_salary,
                     pf_employee,pf_employer,esi_employee,esi_employer,professional_tax,income_tax_tds,
                     loan_deduction,other_deductions,total_deductions,net_salary,effective_tax_rate,take_home_ratio)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pr["payroll_id"],emp_key[0],dept_key2[0],desig_key2[0],grade_key2[0],period_key[0],
                     pr["status"],pr["payment_date"],pr["working_days"],pr["days_present"],pr["days_absent"],pr["days_leave"],
                     pr["basic_salary"],pr["hra"],pr["da"],pr["transport_allow"],pr["other_allowances"],pr["gross_salary"],
                     pr["pf_employee"],pr["pf_employer"],pr["esi_employee"],pr["esi_employer"],pr["professional_tax"],pr["income_tax_tds"],
                     pr["loan_deduction"],pr["other_deductions"],pr["total_deductions"],pr["net_salary"],eff_tax,take_home))
                loaded += 1
            except Exception:
                pass

    dw.commit()
    oltp.close()

    counts = {t: dw.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["dim_employee","dim_department","dim_period","fact_payroll"]}
    dw.close()

    print(f"  Star schema loaded: {counts}")
    return counts

def run_dw_queries():
    dw = sqlite3.connect(DB_DW)
    dw.row_factory = sqlite3.Row

    queries = {
        "Dept cost by period": """
            SELECT dd.dept_name, dp.period_name,
                   COUNT(*) hc, ROUND(SUM(f.gross_salary),2) gross,
                   ROUND(SUM(f.net_salary),2) net, ROUND(SUM(f.income_tax_tds),2) tds
            FROM fact_payroll f
            JOIN dim_department dd ON f.dept_key=dd.dept_key
            JOIN dim_period dp ON f.period_key=dp.period_key
            WHERE dp.year=2026
            GROUP BY dd.dept_name, dp.period_name
            ORDER BY dp.period_name, gross DESC
            LIMIT 12
        """,
        "YTD net by employee": """
            SELECT de.emp_code, de.full_name,
                   SUM(f.net_salary) ytd_net, AVG(f.take_home_ratio) avg_take_home_pct
            FROM fact_payroll f
            JOIN dim_employee de ON f.emp_key=de.emp_key
            JOIN dim_period dp ON f.period_key=dp.period_key
            WHERE dp.year=2026 AND de.is_current=1
            GROUP BY de.emp_key
            ORDER BY ytd_net DESC
            LIMIT 10
        """
    }
    print("\n  DW Analytics Queries:")
    for name, sql in queries.items():
        rows = dw.execute(sql).fetchall()
        print(f"  [{name}]: {len(rows)} rows")
        for r in rows[:3]:
            print(f"    {dict(r)}")
    dw.close()

# ══════════════════════════════════════════════════════════════
#  TASK 10: ETL vs ELT PIPELINES
# ══════════════════════════════════════════════════════════════
def etl_pipeline(source_csv: str, target_db: str) -> dict:
    """
    ETL: Extract → Transform (in Python) → Load
    Data is transformed BEFORE loading into the target.
    """
    print("\n[ETL] Extract → Transform → Load")
    t_total = time.time()
    result = {"pipeline": "ETL", "steps": {}}

    # EXTRACT
    t0 = time.time()
    rows = []
    with open(source_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    result["steps"]["extract"] = {"rows": len(rows), "ms": round((time.time()-t0)*1000, 2)}
    print(f"  E: Extracted {len(rows)} rows from CSV ({result['steps']['extract']['ms']}ms)")

    # TRANSFORM
    t0 = time.time()
    transformed = []
    skipped = 0
    for r in rows:
        try:
            basic = float(r.get("basic_salary", 0) or 0)
            if basic <= 0: skipped += 1; continue
            hra   = round(basic * 0.35, 2)
            da    = round(basic * 0.17, 2)
            gross = round(basic + hra + da + 1200, 2)
            pf    = round(min(basic, 15000) * 0.12, 2)
            net   = round(gross - pf, 2)
            transformed.append({
                "emp_code": r.get("emp_code",""),
                "full_name": f"{r.get('first_name','')} {r.get('last_name','')}".strip(),
                "dept": r.get("dept",""),
                "basic": basic, "hra": hra, "da": da,
                "gross": gross, "pf": pf, "net": net,
                "status": r.get("status","Active"),
                "load_ts": datetime.now().isoformat()
            })
        except Exception:
            skipped += 1
    result["steps"]["transform"] = {"transformed": len(transformed), "skipped": skipped,
                                     "ms": round((time.time()-t0)*1000, 2)}
    print(f"  T: Transformed {len(transformed)} rows, skipped {skipped} ({result['steps']['transform']['ms']}ms)")

    # LOAD
    t0 = time.time()
    conn = sqlite3.connect(target_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS etl_payroll(
        emp_code TEXT, full_name TEXT, dept TEXT,
        basic REAL, hra REAL, da REAL, gross REAL, pf REAL, net REAL,
        status TEXT, load_ts TEXT)""")
    conn.executemany("INSERT INTO etl_payroll VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                     [tuple(r.values()) for r in transformed])
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM etl_payroll").fetchone()[0]
    conn.close()
    result["steps"]["load"] = {"loaded": count, "ms": round((time.time()-t0)*1000, 2)}
    result["total_ms"] = round((time.time()-t_total)*1000, 2)
    print(f"  L: Loaded {count} rows into DB ({result['steps']['load']['ms']}ms)")
    print(f"  ETL Total: {result['total_ms']}ms")
    return result

def elt_pipeline(source_csv: str, target_db: str) -> dict:
    """
    ELT: Extract → Load raw → Transform (using SQL)
    Data is loaded raw FIRST, then transformed in-database.
    Better for large scale / cloud warehouses.
    """
    print("\n[ELT] Extract → Load → Transform")
    t_total = time.time()
    result = {"pipeline": "ELT", "steps": {}}

    # EXTRACT
    t0 = time.time()
    rows = []
    with open(source_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    result["steps"]["extract"] = {"rows": len(rows), "ms": round((time.time()-t0)*1000, 2)}
    print(f"  E: Extracted {len(rows)} rows ({result['steps']['extract']['ms']}ms)")

    # LOAD RAW
    t0 = time.time()
    conn = sqlite3.connect(target_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS elt_raw_employees(
        emp_id TEXT, emp_code TEXT, first_name TEXT, last_name TEXT,
        dept TEXT, designation TEXT, basic_salary TEXT, gender TEXT,
        dob TEXT, email TEXT, date_joined TEXT, status TEXT,
        _load_ts TEXT)""")
    conn.executemany("INSERT INTO elt_raw_employees VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     [[r.get(k,"") for k in ["emp_id","emp_code","first_name","last_name",
                       "dept","designation","basic_salary","gender","dob","email","date_joined","status"]] + [datetime.now().isoformat()] for r in rows])
    conn.commit()
    raw_count = conn.execute("SELECT COUNT(*) FROM elt_raw_employees").fetchone()[0]
    result["steps"]["load_raw"] = {"rows": raw_count, "ms": round((time.time()-t0)*1000, 2)}
    print(f"  L: Loaded {raw_count} raw rows ({result['steps']['load_raw']['ms']}ms)")

    # TRANSFORM IN-DATABASE (SQL)
    t0 = time.time()
    conn.execute("DROP TABLE IF EXISTS elt_transformed_payroll")
    conn.execute("""
        CREATE TABLE elt_transformed_payroll AS
        SELECT
            emp_code,
            first_name || ' ' || last_name AS full_name,
            dept,
            CAST(CASE WHEN basic_salary='' THEN 0 ELSE basic_salary END AS REAL) AS basic,
            ROUND(CAST(CASE WHEN basic_salary='' THEN 0 ELSE basic_salary END AS REAL) * 0.35, 2) AS hra,
            ROUND(CAST(CASE WHEN basic_salary='' THEN 0 ELSE basic_salary END AS REAL) * 0.17, 2) AS da,
            ROUND(CAST(CASE WHEN basic_salary='' THEN 0 ELSE basic_salary END AS REAL) * 1.52 + 1200, 2) AS gross_salary,
            ROUND(MIN(CAST(CASE WHEN basic_salary='' THEN 0 ELSE basic_salary END AS REAL), 15000) * 0.12, 2) AS pf,
            CASE WHEN status='' THEN 'Unknown' ELSE status END AS status,
            _load_ts,
            datetime('now') AS transform_ts
        FROM elt_raw_employees
        WHERE CAST(CASE WHEN basic_salary='' THEN '0' ELSE basic_salary END AS REAL) > 0
    """)
    conn.commit()
    t_count = conn.execute("SELECT COUNT(*) FROM elt_transformed_payroll").fetchone()[0]
    result["steps"]["transform_sql"] = {"rows": t_count, "ms": round((time.time()-t0)*1000, 2)}
    result["total_ms"] = round((time.time()-t_total)*1000, 2)
    print(f"  T: SQL-transformed {t_count} rows ({result['steps']['transform_sql']['ms']}ms)")
    print(f"  ELT Total: {result['total_ms']}ms")
    conn.close()
    return result

# ══════════════════════════════════════════════════════════════
#  TASK 11: BATCH DATA INGESTION (CSV → Database)
# ══════════════════════════════════════════════════════════════
def generate_ingestion_data(n=500):
    """Generate batch CSV for ingestion."""
    fp = OUTPUT / "batch_ingestion.csv"
    depts = ["IT","HR","Finance","Sales","Ops"]
    with open(fp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["emp_id","emp_code","first_name","last_name","dept",
                    "basic_salary","dob","email","date_joined","status"])
        for i in range(1, n+1):
            w.writerow([i, f"EMP{i:04d}", f"Employee{i}", f"Surname{i}",
                        random.choice(depts),
                        random.choice([25000,35000,45000,65000,90000,130000]),
                        f"198{random.randint(0,9)}-{random.randint(1,12):02d}-01",
                        f"emp{i}@payrollwise.in",
                        f"201{random.randint(5,9)}-{random.randint(1,12):02d}-01",
                        "Active"])
    return fp

class BatchIngestionPipeline:
    """Batch ingestion with checkpointing and error handling."""
    CHUNK_SIZE = 100

    def __init__(self, source_csv, target_db):
        self.source = Path(source_csv)
        self.db     = target_db
        self.log    = []
        self.stats  = {"total":0,"loaded":0,"failed":0,"chunks":0,"start":datetime.now().isoformat()}

    def read_chunks(self):
        with open(self.source, newline="") as f:
            reader = csv.DictReader(f)
            chunk = []
            for row in reader:
                self.stats["total"] += 1
                chunk.append(row)
                if len(chunk) >= self.CHUNK_SIZE:
                    yield chunk; chunk = []
            if chunk: yield chunk

    def validate_row(self, row):
        errors = []
        if not row.get("emp_code"): errors.append("missing emp_code")
        try:
            s = float(row.get("basic_salary",0) or 0)
            if s < 0: errors.append("negative salary")
        except: errors.append("invalid salary")
        return errors

    def transform_row(self, row):
        basic = float(row.get("basic_salary",0) or 0)
        return {
            "emp_id":     int(row["emp_id"]),
            "emp_code":   row["emp_code"],
            "full_name":  f"{row['first_name']} {row['last_name']}",
            "dept":       row["dept"],
            "basic":      basic,
            "gross":      round(basic * 1.52 + 1200, 2),
            "net":        round(basic * 1.52 + 1200 - min(basic,15000)*0.12, 2),
            "status":     row.get("status","Active"),
            "ingested_at":datetime.now().isoformat()
        }

    def load_chunk(self, conn, chunk_data):
        conn.executemany("""
            INSERT OR REPLACE INTO ingested_employees
            (emp_id,emp_code,full_name,dept,basic,gross,net,status,ingested_at)
            VALUES(:emp_id,:emp_code,:full_name,:dept,:basic,:gross,:net,:status,:ingested_at)
        """, chunk_data)
        conn.commit()

    def run(self):
        print(f"\n[Ingestion] Batch pipeline: {self.source.name}")
        conn = sqlite3.connect(self.db)
        conn.execute("""CREATE TABLE IF NOT EXISTS ingested_employees(
            emp_id INTEGER PRIMARY KEY, emp_code TEXT, full_name TEXT, dept TEXT,
            basic REAL, gross REAL, net REAL, status TEXT, ingested_at TEXT)""")
        conn.execute("CREATE TABLE IF NOT EXISTS ingestion_errors(emp_code TEXT, errors TEXT, ts TEXT)")

        t0 = time.time()
        for chunk_num, chunk in enumerate(self.read_chunks(), 1):
            valid_rows, error_rows = [], []
            for row in chunk:
                errs = self.validate_row(row)
                if errs:
                    self.stats["failed"] += 1
                    conn.execute("INSERT INTO ingestion_errors VALUES(?,?,?)",
                                 (row.get("emp_code","?"), str(errs), datetime.now().isoformat()))
                else:
                    valid_rows.append(self.transform_row(row))

            if valid_rows:
                self.load_chunk(conn, valid_rows)
                self.stats["loaded"] += len(valid_rows)
            self.stats["chunks"] += 1
            if chunk_num % 2 == 0:
                print(f"  Chunk {chunk_num}: +{len(valid_rows)} rows | Total loaded: {self.stats['loaded']}")

        self.stats["elapsed_ms"] = round((time.time()-t0)*1000, 2)
        self.stats["throughput_rps"] = round(self.stats["loaded"] / (time.time()-t0), 0)

        count = conn.execute("SELECT COUNT(*) FROM ingested_employees").fetchone()[0]
        conn.close()
        print(f"  ✓ Ingested: {count} rows | Elapsed: {self.stats['elapsed_ms']}ms | "
              f"Throughput: {self.stats['throughput_rps']:.0f} rows/s")
        return self.stats

def run():
    print("="*60)
    print("  TASK 09: Data Warehousing — Star Schema")
    print("  TASK 10: ETL vs ELT Pipelines")
    print("  TASK 11: Batch Data Ingestion")
    print("="*60)

    print("\n══ TASK 09: STAR SCHEMA ══")
    dw_counts = build_star_schema()
    run_dw_queries()
    print(f"\n  Schema Summary: {DB_DW.name}")
    print(f"  Tables: dim_employee({dw_counts['dim_employee']}), "
          f"dim_department({dw_counts['dim_department']}), "
          f"dim_period({dw_counts['dim_period']}), "
          f"fact_payroll({dw_counts['fact_payroll']})")

    # Create sample CSV for ETL/ELT
    sample_csv = OUTPUT / "etl_source.csv"
    sample_csv.write_text(
        "emp_id,emp_code,first_name,last_name,dept,designation,basic_salary,gender,dob,email,date_joined,status\n"
        "1,EMP001,Rajesh,Kumar,HR,Executive,45000,Male,1985-03-15,rajesh@pw.in,2018-06-01,Active\n"
        "2,EMP002,Priya,Sharma,HR,Manager,125000,Female,1990-07-22,priya@pw.in,2016-03-15,Active\n"
        "3,EMP003,Amit,Patel,IT,Engineer,65000,Male,1988-11-08,amit@pw.in,2019-09-01,Active\n"
        "4,EMP004,Sneha,Reddy,Support,Executive,,Female,1992-04-30,sneha@pw.in,2021-01-10,Active\n"
        "5,EMP005,Vikram,Singh,Sales,Executive,38000,Male,1983-12-19,,2017-08-20,Active\n"
    )

    print("\n══ TASK 10: ETL vs ELT ══")
    etl_db = str(BASE / "etl_output.db")
    elt_db = str(BASE / "elt_output.db")
    for db in [etl_db, elt_db]:
        if os.path.exists(db): os.remove(db)

    etl_result = etl_pipeline(str(sample_csv), etl_db)
    elt_result = elt_pipeline(str(sample_csv), elt_db)

    print("\n  Comparison:")
    print(f"  {'Metric':<25} {'ETL':>12} {'ELT':>12}")
    print("  " + "-"*52)
    print(f"  {'Total Time (ms)':<25} {etl_result['total_ms']:>12} {elt_result['total_ms']:>12}")
    print(f"  {'Transform Location':<25} {'Python code':>12} {'SQL in DB':>12}")
    print(f"  {'Best for':<25} {'Small-med data':>12} {'Large/cloud':>12}")

    print("\n══ TASK 11: BATCH INGESTION ══")
    csv_path = generate_ingestion_data(500)
    ingest_db = str(BASE / "ingested.db")
    if os.path.exists(ingest_db): os.remove(ingest_db)
    pipeline = BatchIngestionPipeline(csv_path, ingest_db)
    stats = pipeline.run()

    results = {"task09_dw": dw_counts, "task10_etl": etl_result, "task10_elt": elt_result, "task11_ingest": stats}
    (OUTPUT/"warehouse_etl_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results saved: {OUTPUT}/warehouse_etl_results.json")
    return results

if __name__ == "__main__":
    run()
