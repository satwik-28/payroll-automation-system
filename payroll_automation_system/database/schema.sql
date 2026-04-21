-- ============================================================
-- PAYROLL AUTOMATION SYSTEM - DATABASE SCHEMA
-- Database: SQLite | Normalization: 3NF
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- TABLE 1: DEPARTMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    dept_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_code     TEXT NOT NULL UNIQUE,
    dept_name     TEXT NOT NULL UNIQUE,
    manager_id    INTEGER,                        -- FK to employees (set later)
    location      TEXT NOT NULL,
    budget        REAL NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- TABLE 2: DESIGNATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS designations (
    desig_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    desig_code    TEXT NOT NULL UNIQUE,
    desig_title   TEXT NOT NULL,
    dept_id       INTEGER NOT NULL,
    level_rank    INTEGER NOT NULL DEFAULT 1,      -- 1=junior, 5=senior/lead
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE RESTRICT
);

-- ============================================================
-- TABLE 3: SALARY GRADES (separate to avoid update anomalies)
-- ============================================================
CREATE TABLE IF NOT EXISTS salary_grades (
    grade_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_code    TEXT NOT NULL UNIQUE,
    grade_name    TEXT NOT NULL,
    basic_min     REAL NOT NULL,
    basic_max     REAL NOT NULL,
    hra_pct       REAL NOT NULL DEFAULT 40.0,     -- % of basic
    da_pct        REAL NOT NULL DEFAULT 20.0,     -- % of basic
    ta_flat       REAL NOT NULL DEFAULT 0,        -- flat transport allowance
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- TABLE 4: EMPLOYEES (core entity)
-- ============================================================
CREATE TABLE IF NOT EXISTS employees (
    emp_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_code      TEXT NOT NULL UNIQUE,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    gender        TEXT NOT NULL CHECK(gender IN ('Male','Female','Other')),
    dob           TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT NOT NULL,
    address       TEXT NOT NULL,
    city          TEXT NOT NULL,
    state         TEXT NOT NULL,
    pan_number    TEXT NOT NULL UNIQUE,
    aadhaar_last4 TEXT NOT NULL,
    bank_account  TEXT NOT NULL,
    bank_name     TEXT NOT NULL,
    ifsc_code     TEXT NOT NULL,
    dept_id       INTEGER NOT NULL,
    desig_id      INTEGER NOT NULL,
    grade_id      INTEGER NOT NULL,
    basic_salary  REAL NOT NULL,
    date_joined   TEXT NOT NULL,
    employment_type TEXT NOT NULL DEFAULT 'Full-Time'
                   CHECK(employment_type IN ('Full-Time','Part-Time','Contract','Intern')),
    status        TEXT NOT NULL DEFAULT 'Active'
                   CHECK(status IN ('Active','Inactive','Terminated','On-Leave')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dept_id)  REFERENCES departments(dept_id)  ON DELETE RESTRICT,
    FOREIGN KEY (desig_id) REFERENCES designations(desig_id) ON DELETE RESTRICT,
    FOREIGN KEY (grade_id) REFERENCES salary_grades(grade_id) ON DELETE RESTRICT
);

-- ============================================================
-- TABLE 5: PAYROLL PERIODS
-- ============================================================
CREATE TABLE IF NOT EXISTS payroll_periods (
    period_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    period_name   TEXT NOT NULL UNIQUE,
    month         INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    year          INTEGER NOT NULL,
    start_date    TEXT NOT NULL,
    end_date      TEXT NOT NULL,
    total_days    INTEGER NOT NULL DEFAULT 30,
    working_days  INTEGER NOT NULL DEFAULT 26,
    status        TEXT NOT NULL DEFAULT 'Open'
                   CHECK(status IN ('Open','Processing','Closed','Paid')),
    processed_at  TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- TABLE 6: ATTENDANCE
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance (
    att_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id        INTEGER NOT NULL,
    att_date      TEXT NOT NULL,
    check_in      TEXT,
    check_out     TEXT,
    hours_worked  REAL NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'Present'
                   CHECK(status IN ('Present','Absent','Half-Day','Holiday','Weekend','On-Leave')),
    remarks       TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(emp_id, att_date),
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 7: LEAVE TYPES (lookup - 2NF compliance)
-- ============================================================
CREATE TABLE IF NOT EXISTS leave_types (
    leave_type_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    leave_code      TEXT NOT NULL UNIQUE,
    leave_name      TEXT NOT NULL,
    max_days_year   INTEGER NOT NULL DEFAULT 12,
    is_paid         INTEGER NOT NULL DEFAULT 1,
    carry_forward   INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- TABLE 8: LEAVE REQUESTS
-- ============================================================
CREATE TABLE IF NOT EXISTS leave_requests (
    leave_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id        INTEGER NOT NULL,
    leave_type_id INTEGER NOT NULL,
    start_date    TEXT NOT NULL,
    end_date      TEXT NOT NULL,
    days_requested REAL NOT NULL,
    reason        TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'Pending'
                   CHECK(status IN ('Pending','Approved','Rejected','Cancelled')),
    approved_by   INTEGER,
    approved_at   TEXT,
    period_id     INTEGER,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (emp_id)        REFERENCES employees(emp_id)   ON DELETE CASCADE,
    FOREIGN KEY (leave_type_id) REFERENCES leave_types(leave_type_id),
    FOREIGN KEY (approved_by)   REFERENCES employees(emp_id),
    FOREIGN KEY (period_id)     REFERENCES payroll_periods(period_id)
);

-- ============================================================
-- TABLE 9: DEDUCTION TYPES (master)
-- ============================================================
CREATE TABLE IF NOT EXISTS deduction_types (
    deduction_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deduction_code    TEXT NOT NULL UNIQUE,
    deduction_name    TEXT NOT NULL,
    is_percentage     INTEGER NOT NULL DEFAULT 1,  -- 1=pct of gross, 0=flat
    default_value     REAL NOT NULL DEFAULT 0,
    is_mandatory      INTEGER NOT NULL DEFAULT 0,
    description       TEXT
);

-- ============================================================
-- TABLE 10: TAX SLABS
-- ============================================================
CREATE TABLE IF NOT EXISTS tax_slabs (
    slab_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year   TEXT NOT NULL,
    income_from   REAL NOT NULL,
    income_to     REAL,                            -- NULL = no upper limit
    tax_rate_pct  REAL NOT NULL,
    surcharge_pct REAL NOT NULL DEFAULT 0,
    description   TEXT
);

-- ============================================================
-- TABLE 11: PAYROLL RECORDS (main fact table)
-- ============================================================
CREATE TABLE IF NOT EXISTS payroll_records (
    payroll_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id            INTEGER NOT NULL,
    period_id         INTEGER NOT NULL,
    -- Working days
    total_days        INTEGER NOT NULL DEFAULT 30,
    working_days      INTEGER NOT NULL DEFAULT 26,
    days_present      INTEGER NOT NULL DEFAULT 0,
    days_absent       INTEGER NOT NULL DEFAULT 0,
    days_leave        INTEGER NOT NULL DEFAULT 0,
    -- Earnings
    basic_salary      REAL NOT NULL DEFAULT 0,
    hra               REAL NOT NULL DEFAULT 0,
    da                REAL NOT NULL DEFAULT 0,
    transport_allow   REAL NOT NULL DEFAULT 0,
    other_allowances  REAL NOT NULL DEFAULT 0,
    gross_salary      REAL NOT NULL DEFAULT 0,
    -- Deductions
    pf_employee       REAL NOT NULL DEFAULT 0,     -- 12% of basic
    pf_employer       REAL NOT NULL DEFAULT 0,     -- 12% of basic (cost)
    esi_employee      REAL NOT NULL DEFAULT 0,     -- 0.75% of gross if <=21000
    esi_employer      REAL NOT NULL DEFAULT 0,     -- 3.25% of gross
    professional_tax  REAL NOT NULL DEFAULT 0,
    income_tax_tds    REAL NOT NULL DEFAULT 0,
    loan_deduction    REAL NOT NULL DEFAULT 0,
    other_deductions  REAL NOT NULL DEFAULT 0,
    total_deductions  REAL NOT NULL DEFAULT 0,
    -- Net
    net_salary        REAL NOT NULL DEFAULT 0,
    -- Status
    status            TEXT NOT NULL DEFAULT 'Draft'
                       CHECK(status IN ('Draft','Approved','Paid','Revised','Cancelled')),
    payment_date      TEXT,
    payment_ref       TEXT,
    remarks           TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(emp_id, period_id),
    FOREIGN KEY (emp_id)    REFERENCES employees(emp_id)        ON DELETE RESTRICT,
    FOREIGN KEY (period_id) REFERENCES payroll_periods(period_id) ON DELETE RESTRICT
);

-- ============================================================
-- TABLE 12: PAYROLL DEDUCTION DETAILS (normalized breakdown)
-- ============================================================
CREATE TABLE IF NOT EXISTS payroll_deductions (
    ded_detail_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    payroll_id        INTEGER NOT NULL,
    deduction_type_id INTEGER NOT NULL,
    amount            REAL NOT NULL DEFAULT 0,
    remarks           TEXT,
    FOREIGN KEY (payroll_id)        REFERENCES payroll_records(payroll_id)  ON DELETE CASCADE,
    FOREIGN KEY (deduction_type_id) REFERENCES deduction_types(deduction_type_id)
);

-- ============================================================
-- TABLE 13: SALARY REVISIONS (history / audit)
-- ============================================================
CREATE TABLE IF NOT EXISTS salary_revisions (
    revision_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id        INTEGER NOT NULL,
    old_basic     REAL NOT NULL,
    new_basic     REAL NOT NULL,
    old_grade_id  INTEGER,
    new_grade_id  INTEGER,
    effective_date TEXT NOT NULL,
    reason        TEXT NOT NULL,
    approved_by   INTEGER,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (emp_id)       REFERENCES employees(emp_id) ON DELETE CASCADE,
    FOREIGN KEY (old_grade_id) REFERENCES salary_grades(grade_id),
    FOREIGN KEY (new_grade_id) REFERENCES salary_grades(grade_id),
    FOREIGN KEY (approved_by)  REFERENCES employees(emp_id)
);

-- ============================================================
-- TABLE 14: AUDIT LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name    TEXT NOT NULL,
    record_id     INTEGER NOT NULL,
    action        TEXT NOT NULL CHECK(action IN ('INSERT','UPDATE','DELETE')),
    old_data      TEXT,
    new_data      TEXT,
    performed_by  TEXT NOT NULL DEFAULT 'SYSTEM',
    performed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- TABLE 15: LOANS (employee loans/advances)
-- ============================================================
CREATE TABLE IF NOT EXISTS employee_loans (
    loan_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id        INTEGER NOT NULL,
    loan_amount   REAL NOT NULL,
    loan_date     TEXT NOT NULL,
    emi_amount    REAL NOT NULL,
    total_emis    INTEGER NOT NULL,
    emis_paid     INTEGER NOT NULL DEFAULT 0,
    outstanding   REAL NOT NULL,
    purpose       TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'Active'
                   CHECK(status IN ('Active','Closed','Defaulted')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE RESTRICT
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_emp_dept      ON employees(dept_id);
CREATE INDEX IF NOT EXISTS idx_emp_desig     ON employees(desig_id);
CREATE INDEX IF NOT EXISTS idx_emp_grade     ON employees(grade_id);
CREATE INDEX IF NOT EXISTS idx_emp_status    ON employees(status);
CREATE INDEX IF NOT EXISTS idx_att_emp_date  ON attendance(emp_id, att_date);
CREATE INDEX IF NOT EXISTS idx_att_date      ON attendance(att_date);
CREATE INDEX IF NOT EXISTS idx_leave_emp     ON leave_requests(emp_id);
CREATE INDEX IF NOT EXISTS idx_leave_status  ON leave_requests(status);
CREATE INDEX IF NOT EXISTS idx_payroll_emp   ON payroll_records(emp_id);
CREATE INDEX IF NOT EXISTS idx_payroll_period ON payroll_records(period_id);
CREATE INDEX IF NOT EXISTS idx_payroll_status ON payroll_records(status);
CREATE INDEX IF NOT EXISTS idx_desig_dept    ON designations(dept_id);
CREATE INDEX IF NOT EXISTS idx_audit_table   ON audit_logs(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_loan_emp      ON employee_loans(emp_id);

-- ============================================================
-- VIEWS
-- ============================================================

-- VIEW 1: Employee Full Profile
CREATE VIEW IF NOT EXISTS vw_employee_profile AS
SELECT
    e.emp_id,
    e.emp_code,
    e.first_name || ' ' || e.last_name AS full_name,
    e.gender,
    e.email,
    e.phone,
    e.employment_type,
    e.status,
    d.dept_name,
    d.dept_code,
    ds.desig_title,
    ds.level_rank,
    sg.grade_code,
    sg.grade_name,
    e.basic_salary,
    ROUND(e.basic_salary * sg.hra_pct / 100, 2)         AS hra,
    ROUND(e.basic_salary * sg.da_pct  / 100, 2)         AS da,
    sg.ta_flat                                            AS transport_allowance,
    ROUND(e.basic_salary * (1 + sg.hra_pct/100 + sg.da_pct/100) + sg.ta_flat, 2) AS gross_ctc,
    e.date_joined,
    CAST((julianday('now') - julianday(e.date_joined)) / 365 AS INTEGER) AS years_experience,
    e.bank_name,
    e.ifsc_code
FROM employees e
JOIN departments   d  ON e.dept_id  = d.dept_id
JOIN designations  ds ON e.desig_id = ds.desig_id
JOIN salary_grades sg ON e.grade_id = sg.grade_id;

-- VIEW 2: Payroll Summary View
CREATE VIEW IF NOT EXISTS vw_payroll_summary AS
SELECT
    pr.payroll_id,
    pp.period_name,
    pp.month,
    pp.year,
    e.emp_code,
    e.first_name || ' ' || e.last_name AS employee_name,
    d.dept_name,
    ds.desig_title,
    pr.days_present,
    pr.days_absent,
    pr.basic_salary,
    pr.hra,
    pr.da,
    pr.transport_allow,
    pr.gross_salary,
    pr.pf_employee,
    pr.esi_employee,
    pr.professional_tax,
    pr.income_tax_tds,
    pr.total_deductions,
    pr.net_salary,
    pr.status,
    pr.payment_date
FROM payroll_records pr
JOIN employees       e  ON pr.emp_id    = e.emp_id
JOIN payroll_periods pp ON pr.period_id = pp.period_id
JOIN departments     d  ON e.dept_id    = d.dept_id
JOIN designations    ds ON e.desig_id   = ds.desig_id;

-- VIEW 3: Department Payroll Cost
CREATE VIEW IF NOT EXISTS vw_dept_payroll_cost AS
SELECT
    d.dept_id,
    d.dept_name,
    pp.period_name,
    pp.year,
    pp.month,
    COUNT(pr.payroll_id)         AS headcount,
    ROUND(SUM(pr.gross_salary),2) AS total_gross,
    ROUND(SUM(pr.net_salary),2)   AS total_net,
    ROUND(AVG(pr.net_salary),2)   AS avg_net_salary,
    ROUND(SUM(pr.pf_employer),2)  AS employer_pf,
    ROUND(SUM(pr.esi_employer),2) AS employer_esi,
    ROUND(SUM(pr.gross_salary) + SUM(pr.pf_employer) + SUM(pr.esi_employer), 2) AS total_cost
FROM payroll_records pr
JOIN employees       e  ON pr.emp_id    = e.emp_id
JOIN departments     d  ON e.dept_id    = d.dept_id
JOIN payroll_periods pp ON pr.period_id = pp.period_id
GROUP BY d.dept_id, pp.period_id;

-- VIEW 4: Attendance Summary per Employee per Month
CREATE VIEW IF NOT EXISTS vw_attendance_summary AS
SELECT
    a.emp_id,
    e.emp_code,
    e.first_name || ' ' || e.last_name AS employee_name,
    strftime('%Y', a.att_date) AS year,
    strftime('%m', a.att_date) AS month,
    COUNT(*)                                          AS total_records,
    SUM(CASE WHEN a.status = 'Present'  THEN 1 ELSE 0 END)  AS days_present,
    SUM(CASE WHEN a.status = 'Absent'   THEN 1 ELSE 0 END)  AS days_absent,
    SUM(CASE WHEN a.status = 'Half-Day' THEN 0.5 ELSE 0 END) AS half_days,
    SUM(CASE WHEN a.status = 'On-Leave' THEN 1 ELSE 0 END)  AS leave_days,
    ROUND(SUM(a.hours_worked), 2)                     AS total_hours,
    ROUND(AVG(CASE WHEN a.status='Present' THEN a.hours_worked END), 2) AS avg_hours
FROM attendance a
JOIN employees e ON a.emp_id = e.emp_id
GROUP BY a.emp_id, year, month;

-- VIEW 5: Employee Loan Status
CREATE VIEW IF NOT EXISTS vw_loan_status AS
SELECT
    l.loan_id,
    e.emp_code,
    e.first_name || ' ' || e.last_name AS employee_name,
    d.dept_name,
    l.loan_amount,
    l.emi_amount,
    l.total_emis,
    l.emis_paid,
    (l.total_emis - l.emis_paid)         AS emis_remaining,
    ROUND(l.outstanding, 2)               AS outstanding_balance,
    l.purpose,
    l.status,
    l.loan_date
FROM employee_loans l
JOIN employees   e ON l.emp_id   = e.emp_id
JOIN departments d ON e.dept_id  = d.dept_id;

-- VIEW 6: YTD Salary View (Year-To-Date earnings per employee)
CREATE VIEW IF NOT EXISTS vw_ytd_salary AS
SELECT
    e.emp_id,
    e.emp_code,
    e.first_name || ' ' || e.last_name AS employee_name,
    pp.year,
    COUNT(pr.payroll_id)                AS months_processed,
    ROUND(SUM(pr.basic_salary),2)       AS ytd_basic,
    ROUND(SUM(pr.gross_salary),2)       AS ytd_gross,
    ROUND(SUM(pr.total_deductions),2)   AS ytd_deductions,
    ROUND(SUM(pr.net_salary),2)         AS ytd_net,
    ROUND(SUM(pr.income_tax_tds),2)     AS ytd_tds,
    ROUND(SUM(pr.pf_employee),2)        AS ytd_pf
FROM payroll_records pr
JOIN employees       e  ON pr.emp_id    = e.emp_id
JOIN payroll_periods pp ON pr.period_id = pp.period_id
WHERE pr.status IN ('Approved','Paid')
GROUP BY e.emp_id, pp.year;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- TRIGGER 1: Auto-update employees.updated_at on update
CREATE TRIGGER IF NOT EXISTS trg_emp_updated_at
    AFTER UPDATE ON employees
    FOR EACH ROW
BEGIN
    UPDATE employees SET updated_at = datetime('now') WHERE emp_id = NEW.emp_id;
END;

-- TRIGGER 2: Audit log on employee update
CREATE TRIGGER IF NOT EXISTS trg_audit_emp_update
    AFTER UPDATE ON employees
    FOR EACH ROW
BEGIN
    INSERT INTO audit_logs(table_name, record_id, action, old_data, new_data, performed_by)
    VALUES(
        'employees',
        NEW.emp_id,
        'UPDATE',
        json_object(
            'status', OLD.status,
            'basic_salary', OLD.basic_salary,
            'dept_id', OLD.dept_id,
            'desig_id', OLD.desig_id
        ),
        json_object(
            'status', NEW.status,
            'basic_salary', NEW.basic_salary,
            'dept_id', NEW.dept_id,
            'desig_id', NEW.desig_id
        ),
        'SYSTEM'
    );
END;

-- TRIGGER 3: Auto-calculate payroll totals on insert/update
CREATE TRIGGER IF NOT EXISTS trg_payroll_calc_insert
    BEFORE INSERT ON payroll_records
    FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Net salary cannot be negative')
    WHERE (NEW.gross_salary - NEW.total_deductions) < 0;
END;

-- TRIGGER 4: Prevent payroll update if status is 'Paid'
CREATE TRIGGER IF NOT EXISTS trg_payroll_lock_paid
    BEFORE UPDATE ON payroll_records
    FOR EACH ROW
    WHEN OLD.status = 'Paid'
BEGIN
    SELECT RAISE(ABORT, 'Cannot modify a Paid payroll record. Create a revision instead.');
END;

-- TRIGGER 5: Auto log payroll status change
CREATE TRIGGER IF NOT EXISTS trg_audit_payroll_status
    AFTER UPDATE OF status ON payroll_records
    FOR EACH ROW
    WHEN OLD.status != NEW.status
BEGIN
    INSERT INTO audit_logs(table_name, record_id, action, old_data, new_data, performed_by)
    VALUES(
        'payroll_records',
        NEW.payroll_id,
        'UPDATE',
        json_object('status', OLD.status, 'net_salary', OLD.net_salary),
        json_object('status', NEW.status, 'net_salary', NEW.net_salary, 'payment_date', NEW.payment_date),
        'SYSTEM'
    );
END;

-- TRIGGER 6: Update loan outstanding on payroll deduction
CREATE TRIGGER IF NOT EXISTS trg_update_loan_on_deduction
    AFTER INSERT ON payroll_deductions
    FOR EACH ROW
BEGIN
    UPDATE employee_loans
    SET
        outstanding = outstanding - NEW.amount,
        emis_paid   = emis_paid + 1,
        status      = CASE WHEN (outstanding - NEW.amount) <= 0 THEN 'Closed' ELSE status END
    WHERE emp_id = (SELECT emp_id FROM payroll_records WHERE payroll_id = NEW.payroll_id)
      AND status = 'Active'
      AND NEW.deduction_type_id = (SELECT deduction_type_id FROM deduction_types WHERE deduction_code = 'LOAN');
END;

-- TRIGGER 7: Enforce employee must be Active to have payroll
CREATE TRIGGER IF NOT EXISTS trg_payroll_active_emp
    BEFORE INSERT ON payroll_records
    FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Cannot process payroll for inactive/terminated employee')
    WHERE (SELECT status FROM employees WHERE emp_id = NEW.emp_id) IN ('Terminated');
END;

-- TRIGGER 8: Audit employee salary revision
CREATE TRIGGER IF NOT EXISTS trg_audit_salary_revision
    AFTER INSERT ON salary_revisions
    FOR EACH ROW
BEGIN
    INSERT INTO audit_logs(table_name, record_id, action, old_data, new_data, performed_by)
    VALUES(
        'salary_revisions',
        NEW.revision_id,
        'INSERT',
        json_object('old_basic', NEW.old_basic, 'old_grade_id', NEW.old_grade_id),
        json_object('new_basic', NEW.new_basic, 'new_grade_id', NEW.new_grade_id, 'reason', NEW.reason),
        'SYSTEM'
    );
END;
