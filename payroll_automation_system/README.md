# 💼 PAYROLL AUTOMATION SYSTEM

A full-featured **Payroll Automation System** built with **Python** and **SQLite** — covering database design, normalization, SQL implementation, advanced SQL features (views, indexes, triggers, stored procedures), sample data, and a CLI application.

---

## 📁 Project Structure

```
payroll_automation_system/
├── main.py                    ← CLI Application Entry Point
├── requirements.txt
│
├── database/
│   ├── schema.sql             ← Full SQL schema (DDL)
│   ├── setup_db.py            ← Database initializer
│   ├── sample_data.py         ← 20+ records per table
│   └── payroll.db             ← SQLite database (generated)
│
├── services/
│   ├── payroll_service.py     ← Payroll calculation engine
│   └── report_service.py     ← All report generators
│
├── utils/
│   └── db_connection.py       ← DB connection utilities
│
├── diagrams/
│   ├── er_diagram.py          ← ER diagram generator
│   └── er_diagram.png         ← Generated ER diagram
│
├── reports/
│   └── payroll_period_*.csv   ← Exported CSV reports
│
└── docs/
    └── SCHEMA_DESIGN.md       ← Full normalization documentation
```

---

## 🚀 Quick Start

```bash
# Step 1: Install dependencies
pip install matplotlib

# Step 2: Initialize database (creates all tables, views, indexes, triggers)
python database/setup_db.py

# Step 3: Insert sample data (20+ records per main table)
python database/sample_data.py

# Step 4: Generate ER Diagram (optional)
python diagrams/er_diagram.py

# Step 5: Launch the CLI application
python main.py
```

---

## 🗄️ Database Schema — 15 Tables

| Table                | Description                            | Sample Records |
|----------------------|----------------------------------------|----------------|
| `departments`        | Organizational departments             | 22             |
| `designations`       | Job titles linked to departments       | 35             |
| `salary_grades`      | Pay grades with allowance percentages  | 22             |
| `employees`          | Core employee master data              | 30             |
| `payroll_periods`    | Monthly payroll periods                | 25             |
| `attendance`         | Daily attendance records               | 1,770+         |
| `leave_types`        | Types of leave (CL, SL, PL, etc.)     | 12             |
| `leave_requests`     | Employee leave applications            | 25             |
| `deduction_types`    | PF, ESI, TDS, loans, etc.             | 22             |
| `tax_slabs`          | Income tax slabs FY2024-25 & 2025-26  | 22             |
| `payroll_records`    | Monthly payroll fact table             | 90             |
| `payroll_deductions` | Deduction details per payroll          | —              |
| `salary_revisions`   | Salary history / increments            | 22             |
| `employee_loans`     | Employee loans & EMI tracking          | 22             |
| `audit_logs`         | Automated audit trail                  | Auto-generated |

---

## 🔍 Advanced SQL Features

### 6 Views
- `vw_employee_profile` — Full profile with dept, designation, grade
- `vw_payroll_summary` — Payroll details with all joins resolved
- `vw_dept_payroll_cost` — Department-wise cost aggregation
- `vw_attendance_summary` — Monthly attendance stats
- `vw_loan_status` — Loan outstanding with employee info
- `vw_ytd_salary` — Year-to-date earnings

### 13+ Indexes
- Composite index on `attendance(emp_id, att_date)` for fast lookups
- Indexes on all FK columns, status fields, and audit columns

### 8 Triggers
| Trigger | Purpose |
|---------|---------|
| `trg_emp_updated_at` | Auto-set updated_at timestamp |
| `trg_audit_emp_update` | Audit log on every employee change |
| `trg_payroll_calc_insert` | Validate net salary ≥ 0 |
| `trg_payroll_lock_paid` | Prevent editing Paid records |
| `trg_audit_payroll_status` | Log payroll status changes |
| `trg_update_loan_on_deduction` | Auto-update loan outstanding |
| `trg_payroll_active_emp` | Block payroll for Terminated emp |
| `trg_audit_salary_revision` | Audit every salary change |

---

## 🧮 Payroll Calculation Logic

| Component | Formula |
|-----------|---------|
| Basic (effective) | `basic - (absent_days × per_day_rate)` |
| HRA | `basic × hra_pct%` (grade-dependent) |
| DA | `basic × da_pct%` (grade-dependent) |
| Transport Allow. | Flat amount per grade |
| Gross Salary | `basic + HRA + DA + TA` |
| PF (Employee) | `12% of min(basic, ₹15,000)` |
| ESI (Employee) | `0.75% of gross` (if gross ≤ ₹21,000) |
| Professional Tax | `₹200/month` (if gross > ₹10,000) |
| TDS | Per FY2025-26 slabs with 87A rebate |
| Net Salary | `Gross − Total Deductions` |

---

## 📊 Normalization

- **1NF**: All attributes atomic; no repeating groups
- **2NF**: No partial dependencies — allowances moved to `salary_grades`
- **3NF**: No transitive dependencies — dept info in `departments`, leave metadata in `leave_types`

See `docs/SCHEMA_DESIGN.md` for full normalization analysis.

---

## 📋 Available Reports

1. **Payroll Register** — Full employee payroll for any period
2. **Individual Payslip** — Earnings & deductions breakdown
3. **Department Summary** — Cost analysis by department
4. **Year-to-Date (YTD)** — Cumulative salary totals
5. **Attendance Summary** — Monthly attendance stats
6. **Loan Outstanding** — Employee loan tracker
7. **Salary Revision History** — Increment and promotion log
8. **Audit Trail** — Full change log
9. **CSV Export** — Machine-readable payroll data

---

## 🏦 Statutory Compliance

- **PF**: 12% employee + 12% employer contribution
- **ESI**: 0.75% employee + 3.25% employer (below ₹21,000 gross)
- **Professional Tax**: State-wise flat deduction
- **TDS**: FY2025-26 new tax regime with 87A rebate and 4% cess
- **Tax Slabs**: Both FY2024-25 and FY2025-26 (old and new regime) stored

---

## 🔗 Reference
Inspired by [PayrollWise](https://github.com/Aarya94/payrollwise) — rebuilt from scratch in Python + SQLite with full normalization and advanced SQL.
