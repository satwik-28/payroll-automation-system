# 💼 PayrollWise — Complete Data Engineering System

A production-grade **Payroll Automation System** covering all 30 Data Engineering
tasks from basic Python to cloud data warehouses, implemented entirely in
**Python + SQLite** with no external cluster required.

for file 05_pandas_numpy one large file, link for that - https://drive.google.com/file/d/1iQsBT-hOw-LnFWnh0bf10TX5wSnBzH03/view?usp=sharing
---

## ⚡ Quick Start

```bash
# 1. Install dependencies (one time)
pip install pandas numpy flask faker matplotlib

# 2. Run the web application
cd payroll_web
python start.py
# → Open http://localhost:5000

# 3. Run all 30 data engineering tasks
cd ..
python run_all.py

# 4. Run a specific task
python run_all.py --task 5

# 5. Run a range of tasks
python run_all.py --task 1-10
```

---

## 🗂️ Project Structure

```
PayrollWise_Complete/
│
├── README.md                    ← You are here
├── run_all.py                   ← Master runner for all 30 tasks
│
├── 📁 payroll_web/              ← 🌐 WEB APPLICATION
│   ├── app.py                   ← Flask server (single file, all pages + APIs)
│   ├── start.py                 ← Smart startup with checks
│   ├── payroll.db               ← Self-contained database
│   ├── README.md                ← Web app documentation
│   └── templates/               ← 9 HTML pages
│       ├── base.html            ← Shared layout (dark fintech theme)
│       ├── dashboard.html       ← Stats, charts, trends
│       ├── employees.html       ← Directory, add/view employees
│       ├── payroll.html         ← Generate/approve/pay, payslips, CSV export
│       ├── attendance.html      ← Monthly summary, mark attendance
│       ├── leave.html           ← Apply/approve leave, calendar
│       ├── loans.html           ← Loan register, EMI tracker
│       ├── tax_calculator.html  ← New vs old regime, slab breakdown
│       ├── reports.html         ← YTD, dept cost, audit trail
│       └── salary_revisions.html← Increment history
│
├── 📁 shared/
│   └── database/payroll.db      ← Main SQLite database (15 tables, 30 emp)
│
├── 📁 01_linux_filesystem/      ← Task 1
├── 📁 02_networking/            ← Task 2
├── 📁 03_python_basics/         ← Task 3
├── 📁 04_advanced_python/       ← Task 4
├── 📁 05_pandas_numpy/          ← Task 5
├── 📁 06_sql_basics/            ← Tasks 6–8 (combined)
├── 📁 07_advanced_sql/          ← Task 7
├── 📁 08_database_concepts/     ← Task 8
├── 📁 09_data_warehousing/      ← Tasks 9–11 (combined)
├── 📁 10_etl_elt/               ← Task 10
├── 📁 11_data_ingestion/        ← Task 11
├── 📁 12_hadoop/                ← Tasks 12–17 (combined)
├── 📁 13_hdfs_architecture/     ← Task 13
├── 📁 14_spark_basics/          ← Task 14
├── 📁 15_spark_dataframes/      ← Task 15
├── 📁 16_spark_sql/             ← Task 16
├── 📁 17_pyspark_advanced/      ← Task 17
├── 📁 18_streaming_concepts/    ← Tasks 18–21 (combined)
├── 📁 19_kafka_basics/          ← Task 19
├── 📁 20_kafka_advanced/        ← Task 20
├── 📁 21_structured_streaming/  ← Task 21
├── 📁 22_airflow_basics/        ← Tasks 22–23 (combined)
├── 📁 23_airflow_advanced/      ← Task 23
├── 📁 24_cloud_basics/          ← Tasks 24–27 (combined)
├── 📁 25_cloud_storage/         ← Task 25
├── 📁 26_cloud_compute/         ← Task 26
├── 📁 27_data_warehouse_cloud/  ← Task 27
├── 📁 28_lakehouse/             ← Tasks 28–29 (combined)
├── 📁 29_data_quality/          ← Task 29
└── 📁 30_final_project/         ← Task 30 — E2E pipeline + HTML dashboard
```

---

## 📋 All 30 Tasks

| # | Task | Key Concepts | File |
|---|------|-------------|------|
| 01 | Linux + File System | Directories, permissions, shell scripts, logging | `01_linux_filesystem/filesystem_task.py` |
| 02 | Networking & APIs | HTTP server, FTP sim, packet analysis, TLS flow | `02_networking/networking_task.py` |
| 03 | Python Basics | CSV read, null handling, dataset merge | `03_python_basics/python_basics_task.py` |
| 04 | Advanced Python | Normalization, aggregation, validation modules | `04_advanced_python/advanced_python_task.py` |
| 05 | Pandas + NumPy | 1.2M rows, dtype optimization, benchmarks | `05_pandas_numpy/pandas_numpy_task.py` |
| 06 | SQL Basics | SELECT, WHERE, GROUP BY, HAVING, ORDER BY | `06_sql_basics/sql_tasks_06_07_08.py` |
| 07 | Advanced SQL | JOINs, window functions, CTEs, subqueries | `07_advanced_sql/advanced_sql_task.py` |
| 08 | DB Concepts | OLTP schema, OLAP star schema, perf compare | `08_database_concepts/db_concepts_task.py` |
| 09 | Data Warehousing | Star schema: fact + 5 dims, ETL from OLTP | `09_data_warehousing/dw_etl_ingestion.py` |
| 10 | ETL vs ELT | Both pipelines built + benchmarked | `10_etl_elt/etl_elt_task.py` |
| 11 | Data Ingestion | Chunked batch CSV→SQLite, checkpoint | `11_data_ingestion/ingestion_task.py` |
| 12 | Hadoop + HDFS | 3-node cluster, Namenode, block replication | `12_hadoop/hadoop_spark_tasks.py` |
| 13 | HDFS Architecture | Rack awareness, fault tolerance, block ops | `13_hdfs_architecture/hdfs_arch_task.py` |
| 14 | Spark Basics | RDD: parallelize, map, filter, reduce | `14_spark_basics/task_14.py` |
| 15 | Spark DataFrames | withColumn, groupBy, join, orderBy | `15_spark_dataframes/task_15.py` |
| 16 | Spark SQL | Pivot, top-earner-per-dept, YTD queries | `16_spark_sql/task_16.py` |
| 17 | PySpark Advanced | Partitioning, caching, broadcast joins | `17_pyspark_advanced/task_17.py` |
| 18 | Streaming Concepts | Event stream, producer/consumer, windowing | `18_streaming_concepts/streaming_kafka_tasks.py` |
| 19 | Kafka Basics | Topics, partitions, producer, consumer | `19_kafka_basics/task_19.py` |
| 20 | Kafka Advanced | Offsets, consumer lag, replay, rebalancing | `20_kafka_advanced/task_20.py` |
| 21 | Structured Streaming | Micro-batches, watermark, checkpoint | `21_structured_streaming/task_21.py` |
| 22 | Airflow DAG | 10-task DAG, topological sort, XCom | `22_airflow_basics/airflow_tasks.py` |
| 23 | Airflow Advanced | Retry, SLA monitoring, scheduling | `23_airflow_advanced/task_23.py` |
| 24 | Cloud Basics | AWS vs GCP vs Azure — 7 service categories | `24_cloud_basics/cloud_tasks.py` |
| 25 | Cloud Storage | S3 simulation: put/get/list/presign/lifecycle | `25_cloud_storage/task_25.py` |
| 26 | Cloud Compute | EC2 lifecycle, 13-step CI/CD deploy | `26_cloud_compute/task_26.py` |
| 27 | Cloud DW | BigQuery queries: bytes/cost/latency | `27_data_warehouse_cloud/task_27.py` |
| 28 | Lakehouse | Delta Lake: ACID, time travel, schema evolve | `28_lakehouse/lakehouse_dq_tasks.py` |
| 29 | Data Quality | 30 checks, Z-score anomalies, IQR outliers | `29_data_quality/data_quality_task.py` |
| 30 | Final Pipeline | E2E: ingest→process→store→notify→dashboard | `30_final_project/final_pipeline.py` |

---

## 🌐 Web Application Pages

| Page | URL | Features |
|------|-----|---------|
| Dashboard | `/` | KPI stats, payroll trend chart, dept cost bars, top earners |
| Payroll | `/payroll` | Generate → Approve → Mark Paid → Export CSV → Payslip popup |
| Employees | `/employees` | Search, filter, add employee, view full profile |
| Attendance | `/attendance` | Monthly summary, mark attendance |
| Leave | `/leave` | Apply, approve/reject, leave calendar |
| Loans | `/loans` | Loan register, EMI progress tracker, add loan |
| Tax Calculator | `/tax-calculator` | New vs Old regime, slab breakdown, take-home estimate |
| Reports | `/reports` | YTD salary, dept cost analysis, audit trail |
| Salary Revisions | `/salary-revisions` | Increment history, add new revision |

---

## 🗄️ Database

**File:** `shared/database/payroll.db` (SQLite, ~450 KB)

| Object | Count | Details |
|--------|-------|---------|
| Tables | 15 | employees, payroll_records, attendance, leave_requests, employee_loans, salary_grades, designations, departments, payroll_periods, leave_types, deduction_types, tax_slabs, salary_revisions, payroll_deductions, audit_logs |
| Views | 6 | vw_employee_profile, vw_payroll_summary, vw_dept_payroll_cost, vw_attendance_summary, vw_loan_status, vw_ytd_salary |
| Indexes | 13 | Composite + FK column indexes |
| Triggers | 8 | Audit trail, lock paid records, loan update, validation |
| Employees | 30 | Across 22 departments, 35 designations, 22 grades |
| Payroll Records | 90 | 3 months of paid payroll (Jan–Mar 2026) |
| Attendance | 1,770+ | 2 months of daily records |

---

## 💡 Payroll Calculation Logic

| Component | Formula |
|-----------|---------|
| Basic Salary | Employee's grade-based salary |
| HRA | Basic × HRA% (grade-dependent, 10–45%) |
| DA | Basic × DA% (grade-dependent, 10–25%) |
| Transport | Flat allowance per grade (₹500–₹30,000) |
| Gross | Basic + HRA + DA + Transport |
| PF Employee | 12% of min(Basic, ₹15,000) |
| PF Employer | 12% of min(Basic, ₹15,000) |
| ESI Employee | 0.75% of Gross (if Gross ≤ ₹21,000) |
| ESI Employer | 3.25% of Gross (if Gross ≤ ₹21,000) |
| Professional Tax | ₹200/month (if Gross > ₹10,000) |
| TDS | Per FY2025-26 slabs with 87A rebate + 4% cess |
| Net Salary | Gross − Total Deductions |

---

## 🔧 Tech Stack

| Layer | Technology | Used For |
|-------|-----------|---------|
| Language | Python 3.8+ | All 30 tasks |
| Database | SQLite | OLTP payroll DB (no server needed) |
| Web Framework | Flask | REST API + web pages |
| Data Analysis | Pandas + NumPy | Task 5, large-scale analysis |
| Visualization | Chart.js (CDN) | Web app charts |
| ER Diagram | Matplotlib | Diagram generation |
| Simulation | Pure Python | Spark, Kafka, Hadoop, Airflow, Cloud |

**No external cluster required** — everything runs on a single machine.

---

## 🚀 VS Code Setup

1. Open the `PayrollWise_Complete` folder in VS Code
2. Install extensions: **Python** (Microsoft), **SQLite Viewer**, **Rainbow CSV**
3. Open terminal: `` Ctrl+` ``
4. Run: `cd payroll_web && python start.py`
5. Click the link or open **http://localhost:5000**
6. To view database visually: click `shared/database/payroll.db` in the file explorer

---

## ❓ Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: flask` | `pip install flask` |
| `ModuleNotFoundError: pandas` | `pip install pandas numpy matplotlib` |
| `payroll.db not found` | Copy `shared/database/payroll.db` into `payroll_web/` |
| Port 5000 already in use | Change `port=5000` to `port=5001` in `payroll_web/app.py` |
| `UnicodeEncodeError` on Windows | All files use `encoding="utf-8"` — fixed |
| Charts not showing | App loads Chart.js from CDN; needs internet for charts |
| Task fails with import error | Run from the project root: `python run_all.py --task N` |
