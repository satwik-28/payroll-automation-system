# PAYROLL AUTOMATION SYSTEM — DATABASE DESIGN DOCUMENTATION

## ER Diagram

See `diagrams/er_diagram.png` (generate with `python diagrams/er_diagram.py`)

---

## 1. NORMALIZATION ANALYSIS

### First Normal Form (1NF)
All tables satisfy 1NF:
- Every column holds **atomic** values (no multi-valued or composite attributes)
- Each table has a **primary key**
- No repeating groups

**Example — employees table:**
- `address` stores one address (not a CSV of multiple)
- `phone` holds one contact number
- Multiple allowances (HRA, DA, TA) are NOT stored in one column — they are computed from `salary_grades`

---

### Second Normal Form (2NF)
All tables satisfy 2NF (no partial dependencies on composite keys):

**Example — payroll_records:**
- Composite key candidate: `(emp_id, period_id)` — used as a UNIQUE constraint
- `basic_salary` depends on emp_id (through employees) — NOT stored redundantly
- Earnings (hra, da, gross) depend on the whole composite context (period + emp), not just one part
- `hra_pct`, `da_pct`, `ta_flat` moved to `salary_grades` — eliminating partial dependency

**Before (not 2NF):**
```
payroll(emp_id, period_id, emp_name, hra_pct, gross)
         ↑ emp_name depends only on emp_id — partial dependency!
```

**After (2NF compliant):**
```
payroll_records(emp_id, period_id, gross)
employees(emp_id, emp_name, ...)        ← emp_name belongs here
```

---

### Third Normal Form (3NF)
All tables satisfy 3NF (no transitive dependencies):

**Problem eliminated:**
```
employees(emp_id, dept_id, dept_name, dept_location)
         dept_name → dept_location  — transitive via dept_id!
```

**After (3NF):**
```
employees(emp_id, dept_id)                  ← only FK
departments(dept_id, dept_name, location)   ← dept attributes here
```

**Another transitive removed:**
```
payroll_records BEFORE: (emp_id, period_id, hra_pct, da_pct, grade_name)
                         grade_name → hra_pct, da_pct via grade_id (transitive!)
```
Resolved by extracting `salary_grades(grade_id, hra_pct, da_pct, grade_name)`.

**Leave type transitive removed:**
```
leave_requests BEFORE: (leave_id, leave_code, max_days, is_paid)
                        max_days → is_paid via leave_code (transitive!)
```
Resolved with `leave_types(leave_type_id, leave_code, max_days, is_paid)`.

---

## 2. ENTITY DESCRIPTIONS & SCHEMA

### Table 1: departments
| Column      | Type    | Constraints        | Description                  |
|-------------|---------|-------------------|------------------------------|
| dept_id     | INTEGER | PK, AUTOINCREMENT | Surrogate primary key        |
| dept_code   | TEXT    | NOT NULL, UNIQUE  | Short code e.g. DEPT001      |
| dept_name   | TEXT    | NOT NULL, UNIQUE  | Full department name         |
| manager_id  | INTEGER | FK → employees    | Head of department           |
| location    | TEXT    | NOT NULL          | City of operation            |
| budget      | REAL    | NOT NULL          | Annual budget in INR         |
| is_active   | INTEGER | DEFAULT 1         | Soft delete flag             |

### Table 2: designations
| Column     | Type    | Constraints       | Description              |
|------------|---------|------------------|--------------------------|
| desig_id   | INTEGER | PK               | Surrogate key            |
| desig_code | TEXT    | UNIQUE           | e.g. D001                |
| desig_title| TEXT    | NOT NULL         | Job title                |
| dept_id    | INTEGER | FK → departments | Which department         |
| level_rank | INTEGER | DEFAULT 1        | Hierarchy 1=junior..5=sr |

### Table 3: salary_grades
| Column    | Type | Description                              |
|-----------|------|------------------------------------------|
| grade_id  | PK   | Surrogate                               |
| grade_code| TEXT | G1 through G22                          |
| basic_min | REAL | Minimum basic for this grade            |
| basic_max | REAL | Maximum basic for this grade            |
| hra_pct   | REAL | HRA = basic × hra_pct/100              |
| da_pct    | REAL | DA = basic × da_pct/100               |
| ta_flat   | REAL | Fixed transport allowance in INR        |

### Table 4: employees (Core Entity)
Central entity — references departments, designations, salary_grades.
| Column          | Type    | Description                 |
|-----------------|---------|----------------------------|
| emp_id          | PK      | Surrogate key               |
| emp_code        | UNIQUE  | e.g. EMP001                |
| first_name      | TEXT    | First name                  |
| last_name       | TEXT    | Last name                   |
| gender          | TEXT    | CHECK: Male/Female/Other    |
| dob             | TEXT    | Date of birth ISO           |
| email           | UNIQUE  | Work email                  |
| pan_number      | UNIQUE  | PAN for TDS                 |
| dept_id         | FK      | → departments               |
| desig_id        | FK      | → designations              |
| grade_id        | FK      | → salary_grades             |
| basic_salary    | REAL    | Current basic pay           |
| employment_type | TEXT    | Full-Time/Part-Time/Contract|
| status          | TEXT    | Active/Inactive/Terminated  |

### Table 5: payroll_periods
| Column       | Type | Description                  |
|--------------|------|------------------------------|
| period_id    | PK   | Surrogate                    |
| period_name  | TEXT | e.g. "March 2026" (UNIQUE)  |
| month / year | INT  | Period calendar info         |
| working_days | INT  | Effective working days       |
| status       | TEXT | Open/Processing/Closed/Paid  |

### Table 6: payroll_records (Fact Table)
| Column            | Type | Description                     |
|-------------------|------|---------------------------------|
| payroll_id        | PK   | Surrogate                       |
| emp_id            | FK   | → employees                    |
| period_id         | FK   | → payroll_periods               |
| days_present      | INT  | Computed from attendance        |
| basic_salary      | REAL | Effective basic (after LOP)     |
| hra / da / ta     | REAL | Computed allowances             |
| gross_salary      | REAL | Sum of all earnings             |
| pf_employee       | REAL | 12% of min(basic,15000)         |
| esi_employee      | REAL | 0.75% if gross<=21000           |
| income_tax_tds    | REAL | Monthly TDS                     |
| net_salary        | REAL | gross - total_deductions        |
| status            | TEXT | Draft/Approved/Paid             |
| UNIQUE(emp_id, period_id) | Prevents duplicate payroll |

### Table 7: attendance
| Column      | Type | Description               |
|-------------|------|---------------------------|
| att_id      | PK   |                           |
| emp_id      | FK   | → employees               |
| att_date    | TEXT | ISO date (YYYY-MM-DD)     |
| check_in    | TEXT | HH:MM                     |
| hours_worked| REAL | Computed hours            |
| status      | TEXT | Present/Absent/Half-Day.. |
| UNIQUE(emp_id, att_date) | One record per employee per day |

---

## 3. RELATIONSHIP MAP

```
departments ──1:N──> designations
departments ──1:N──> employees
designations ─1:N──> employees
salary_grades ─1:N──> employees
employees ───1:N──> payroll_records
employees ───1:N──> attendance
employees ───1:N──> leave_requests
employees ───1:N──> employee_loans
employees ───1:N──> salary_revisions
payroll_periods ─1:N──> payroll_records
payroll_records ─1:N──> payroll_deductions
deduction_types ─1:N──> payroll_deductions
leave_types ────1:N──> leave_requests
```

---

## 4. VIEWS

| View Name               | Purpose                                         |
|-------------------------|-------------------------------------------------|
| vw_employee_profile     | Full employee info with dept, desig, grade      |
| vw_payroll_summary      | Payroll details with employee & period names    |
| vw_dept_payroll_cost    | Department-wise payroll cost aggregation        |
| vw_attendance_summary   | Monthly attendance stats per employee           |
| vw_loan_status          | Loan outstanding with employee details          |
| vw_ytd_salary           | Year-to-date earnings per employee              |

---

## 5. INDEXES

| Index Name          | Table            | Column(s)         | Purpose                      |
|---------------------|------------------|-------------------|------------------------------|
| idx_emp_dept        | employees        | dept_id           | Dept-wise employee queries   |
| idx_emp_status      | employees        | status            | Active employee filter       |
| idx_att_emp_date    | attendance       | emp_id, att_date  | Attendance lookup (composite)|
| idx_payroll_period  | payroll_records  | period_id         | Period payroll run queries   |
| idx_payroll_status  | payroll_records  | status            | Approval workflow queries    |
| idx_audit_table     | audit_logs       | table_name, rec_id| Audit trail lookups          |

---

## 6. TRIGGERS

| Trigger                    | Event                   | Action                                 |
|----------------------------|-------------------------|----------------------------------------|
| trg_emp_updated_at         | AFTER UPDATE employees  | Sets updated_at = now                 |
| trg_audit_emp_update       | AFTER UPDATE employees  | Inserts audit log row                 |
| trg_payroll_calc_insert    | BEFORE INSERT payroll   | Validates net >= 0                    |
| trg_payroll_lock_paid      | BEFORE UPDATE payroll   | Blocks changes to Paid records        |
| trg_audit_payroll_status   | AFTER UPDATE status     | Logs status changes                   |
| trg_update_loan_on_deduction| AFTER INSERT deductions| Updates loan outstanding & EMI count  |
| trg_payroll_active_emp     | BEFORE INSERT payroll   | Prevents payroll for Terminated emp   |
| trg_audit_salary_revision  | AFTER INSERT revisions  | Audit logs every salary revision      |

---

## 7. STATUTORY COMPLIANCE

| Component        | Calculation                                          |
|------------------|------------------------------------------------------|
| PF Employee      | 12% of min(basic, ₹15,000)                          |
| PF Employer      | 12% of min(basic, ₹15,000)                          |
| ESI Employee     | 0.75% of gross (if gross ≤ ₹21,000)                |
| ESI Employer     | 3.25% of gross (if gross ≤ ₹21,000)                |
| Professional Tax | ₹200/month (if gross > ₹10,000) — varies by state   |
| TDS              | Per FY2025-26 new regime slabs, with 87A rebate      |
| Health & Ed Cess | 4% on computed income tax                           |

---

## 8. QUICK START

```bash
# 1. Install dependencies
pip install matplotlib

# 2. Initialize database
python database/setup_db.py

# 3. Load sample data (20+ records per table)
python database/sample_data.py

# 4. Generate ER Diagram
python diagrams/er_diagram.py

# 5. Launch CLI
python main.py
```
