# PayrollWise — Web Application

A full-featured payroll management system running on your local machine.
No internet or cloud account required.

---

## Quick Start (3 steps)

```bash
# Step 1 — Go into the web folder
cd payroll_web

# Step 2 — Install Flask (one time only)
pip install flask

# Step 3 — Start the server
python start.py
```

Open your browser at **http://localhost:5000**

---

## Pages

| Page | URL | What you can do |
|---|---|---|
| Dashboard | `/` | Stats, charts, payroll trends, top earners |
| Employees | `/employees` | View/search/add employees, payslip history |
| Payroll | `/payroll` | Generate, approve, mark-paid, export CSV |
| Attendance | `/attendance` | Monthly summary, mark attendance |
| Leave | `/leave` | Apply leave, approve/reject requests |
| Loans | `/loans` | View loans, add new loan, EMI tracker |
| Salary Revisions | `/salary-revisions` | Increment history and add new revisions |
| Tax Calculator | `/tax-calculator` | Income tax calculator (new & old regime) |
| Reports | `/reports` | YTD salary, dept cost, audit trail |

---

## Features

### Dashboard
- Real-time stats: active employees, gross payroll, net disbursed, TDS
- Monthly payroll trend chart (Chart.js)
- Department cost bar chart
- Top earners table

### Employees
- Search by name, code, or email
- Filter by department and status
- Add new employees (3-tab form: Personal / Job / Bank)
- View detailed profile with payslip history and loans
- Activate / Deactivate employees

### Payroll Processing
- Select any payroll period
- **Generate** — auto-calculates PF, ESI, TDS, net salary for all employees
- **Approve** — move from Draft to Approved
- **Mark Paid** — finalize with payment date
- **Export CSV** — download the full payroll register
- **View Payslip** — formatted salary slip for any employee

### Leave Management
- Apply for leave (CL, SL, PL, ML, EL etc.)
- Approve / Reject pending requests
- Leave calendar showing upcoming leaves
- Status dashboard (Pending / Approved / Rejected)

### Tax Calculator
- Enter monthly gross or select an employee to auto-fill
- Compares New Regime vs Old Regime side by side
- Shows slab-wise tax breakdown with bar chart
- Calculates effective tax rate and monthly take-home
- Table of all employees with their TDS and tax brackets

---

## Troubleshooting

### "Module not found: flask"
```bash
pip install flask
```

### "payroll.db not found"
The database must be in the `payroll_web/` folder.
```bash
# Option 1: copy it in
copy ..\payroll_automation_system\database\payroll.db .   (Windows)
cp ../payroll_automation_system/database/payroll.db .     (Mac/Linux)

# Option 2: rebuild it
cd ../payroll_automation_system
python database/setup_db.py
python database/sample_data.py
copy database\payroll.db ..\payroll_web\   (Windows)
```

### "Address already in use" / Port 5000 busy
Something else is using port 5000. Either:
- Stop the other program
- Change the port in `app.py`: `app.run(port=5001)`

### Page shows but data is empty
1. Check the terminal for error messages
2. Make sure `payroll.db` has data: open it with **SQLite Viewer** in VS Code

### "TemplateNotFound" error
You must run the server **from inside the payroll_web folder**:
```bash
cd payroll_web       ← important!
python start.py
```

### Charts not showing
The app loads Chart.js from CDN (cdnjs.cloudflare.com).
If you're offline, charts won't render — the rest of the app still works.

---

## VS Code Setup

1. Install extensions: **Python** (Microsoft), **SQLite Viewer**, **Rainbow CSV**
2. Open the `payroll_complete` folder in VS Code
3. Open terminal: `` Ctrl+` ``
4. Run:
   ```bash
   cd payroll_web
   python start.py
   ```
5. Click the link or open http://localhost:5000

To view the database visually:
- In the file explorer, click `payroll_web/payroll.db`
- SQLite Viewer opens it as a table browser

---

## API Reference (REST)

All API endpoints return JSON.

```
GET  /api/stats                          Dashboard summary
GET  /api/employees                      List all employees
GET  /api/employees?q=Rajesh             Search employees
GET  /api/employees/<id>                 Employee detail + payslips
POST /api/employees                      Add new employee
GET  /api/departments                    All departments
GET  /api/payroll/periods                All payroll periods
GET  /api/payroll/register/<period_id>   Payroll register
POST /api/payroll/generate/<period_id>   Run payroll calculation
POST /api/payroll/approve/<period_id>    Approve all Draft records
POST /api/payroll/mark-paid/<period_id>  Mark Approved as Paid
GET  /api/payroll/export/<period_id>     Download CSV
GET  /api/attendance/summary             Monthly attendance stats
GET  /api/loans                          All employee loans
POST /api/loans                          Add new loan
GET  /api/leave/requests                 All leave requests
POST /api/leave/requests                 Apply for leave
PATCH /api/leave/requests/<id>/approve  Approve/reject leave
POST /api/tax/calculate                  Calculate income tax
GET  /api/reports/ytd/<year>             Year-to-date salary
GET  /api/reports/salary-revisions       All salary revisions
GET  /api/reports/audit                  Audit trail
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.8+ + Flask |
| Database | SQLite (single file, no server) |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Charts | Chart.js (CDN) |
| Fonts | Google Fonts (DM Serif Display, IBM Plex Mono, Syne) |

No React, no Node.js, no npm — just Python and a browser.
