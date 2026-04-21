"""
PayrollWise — Simple Interactive Web Application
================================================
Run:   python app.py
Open:  http://localhost:5000
Stop:  Ctrl + C
"""
import os, sys, sqlite3, json, csv, io
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, send_file

# ── Database ──────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
DB   = HERE / "payroll.db"

if not DB.exists():
    for candidate in [
        HERE / ".." / "payroll_complete" / "payroll_web" / "payroll.db",
        HERE / ".." / "payroll_complete" / "shared" / "database" / "payroll.db",
        HERE / ".." / "payroll_automation_system" / "database" / "payroll.db",
    ]:
        c = candidate.resolve()
        if c.exists():
            import shutil; shutil.copy2(c, DB)
            print(f"  Copied DB from {c.name}")
            break

if not DB.exists():
    print("ERROR: payroll.db not found! Copy it into this folder.")
    sys.exit(1)

print(f"  Database: {DB} ({DB.stat().st_size//1024} KB)")

app = Flask(__name__)

def db():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def q(sql, params=()):
    with db() as conn:
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except Exception as e:
            print(f"  SQL ERROR: {e}")
            return []

def ex(sql, params=()):
    conn = db()
    cur  = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid

# ══════════════════════════════════════════════════════════════
#  THE COMPLETE SINGLE-PAGE APPLICATION (HTML + CSS + JS)
# ══════════════════════════════════════════════════════════════
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PayrollWise</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg:#0f1117; --bg2:#161b27; --bg3:#1e2535; --bg4:#252d40;
  --border:#2a3347; --border2:#344060;
  --text:#eaf0fb; --t2:#8a9ab8; --t3:#4a5a78;
  --gold:#f5a623; --gold2:#e09515;
  --green:#2ecc71; --red:#e74c3c; --blue:#3498db;
  --teal:#1abc9c; --purple:#9b59b6; --orange:#e67e22;
  --r:10px; --shadow:0 4px 20px rgba(0,0,0,.4);
}
*{box-sizing:border-box;margin:0;padding:0}
html{font-size:14px;scroll-behavior:smooth}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh;overflow-x:hidden}

/* SIDEBAR */
.sidebar{width:220px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;position:fixed;height:100vh;z-index:100;transition:.3s}
.logo{padding:20px 16px 16px;border-bottom:1px solid var(--border)}
.logo-title{font-size:17px;font-weight:700;color:var(--gold);letter-spacing:-.3px}
.logo-sub{font-size:10px;color:var(--t3);letter-spacing:1px;text-transform:uppercase;margin-top:2px;font-family:'JetBrains Mono',monospace}
nav{flex:1;padding:12px 0;overflow-y:auto}
.nav-group{padding:14px 14px 4px;font-size:9px;font-weight:600;color:var(--t3);letter-spacing:2px;text-transform:uppercase;font-family:'JetBrains Mono',monospace}
.nav-item{display:flex;align-items:center;gap:9px;padding:8px 14px;margin:1px 6px;border-radius:7px;color:var(--t2);font-size:12.5px;font-weight:500;cursor:pointer;transition:.15s;border:none;background:none;width:calc(100% - 12px);text-align:left}
.nav-item:hover{background:var(--bg3);color:var(--text)}
.nav-item.active{background:linear-gradient(90deg,rgba(245,166,35,.15),transparent);color:var(--gold);border-left:2px solid var(--gold);margin-left:4px;padding-left:12px}
.nav-icon{font-size:14px;width:18px;text-align:center;flex-shrink:0}
.sidebar-footer{padding:12px 14px;border-top:1px solid var(--border);font-size:10px;color:var(--t3);font-family:'JetBrains Mono',monospace}
.dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:blink 2s infinite;display:inline-block;margin-right:6px}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* MAIN */
.main{margin-left:220px;flex:1;display:flex;flex-direction:column;min-height:100vh}
.topbar{height:52px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;gap:12px;position:sticky;top:0;z-index:90}
.page-title{font-size:16px;font-weight:600}
.page-sub{font-size:11px;color:var(--t3);font-family:'JetBrains Mono',monospace}
.topbar-actions{margin-left:auto;display:flex;gap:8px;align-items:center}
.time-display{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--t3)}
.content{padding:24px;flex:1}
.page{display:none}
.page.active{display:block}

/* CARDS */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);margin-bottom:18px;overflow:hidden}
.card-header{display:flex;align-items:center;padding:14px 18px;border-bottom:1px solid var(--border);gap:10px}
.card-title{font-size:13.5px;font-weight:600}
.card-sub{font-size:11px;color:var(--t3);font-family:'JetBrains Mono',monospace}
.card-actions{margin-left:auto;display:flex;gap:8px;align-items:center}
.card-body{padding:18px}

/* STATS GRID */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px;margin-bottom:20px}
.stat{background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:16px;position:relative;overflow:hidden;transition:.2s}
.stat:hover{border-color:var(--border2);transform:translateY(-2px)}
.stat::after{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.stat.gold::after{background:var(--gold)}.stat.green::after{background:var(--green)}
.stat.blue::after{background:var(--blue)}.stat.red::after{background:var(--red)}
.stat.teal::after{background:var(--teal)}.stat.purple::after{background:var(--purple)}
.stat.orange::after{background:var(--orange)}
.stat-label{font-size:9.5px;color:var(--t3);text-transform:uppercase;letter-spacing:1.5px;font-family:'JetBrains Mono',monospace;margin-bottom:8px}
.stat-value{font-family:'JetBrains Mono',monospace;font-size:21px;font-weight:600;line-height:1}
.stat-sub{font-size:10.5px;color:var(--t3);margin-top:6px}
.stat-icon{position:absolute;right:14px;top:14px;font-size:20px;opacity:.12}

/* GRID LAYOUTS */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px}
@media(max-width:1000px){.g2,.g3{grid-template-columns:1fr}}

/* TABLE */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse}
thead th{background:var(--bg3);padding:9px 13px;text-align:left;font-size:9.5px;font-weight:600;color:var(--t3);letter-spacing:1.5px;text-transform:uppercase;font-family:'JetBrains Mono',monospace;border-bottom:1px solid var(--border);white-space:nowrap}
tbody tr{border-bottom:1px solid var(--border);transition:.1s}
tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:var(--bg3)}
td{padding:10px 13px;font-size:12.5px;vertical-align:middle;white-space:nowrap}
.num{text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px}
.mono{font-family:'JetBrains Mono',monospace;font-size:11.5px}
.tbl-footer{padding:10px 18px;background:var(--bg3);border-top:1px solid var(--border);font-family:'JetBrains Mono',monospace;font-size:11.5px;display:flex;gap:20px;color:var(--t2)}

/* BADGES */
.badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:600;font-family:'JetBrains Mono',monospace;letter-spacing:.3px;text-transform:uppercase}
.bg{background:rgba(46,204,113,.14);color:var(--green)}.br{background:rgba(231,76,60,.14);color:var(--red)}
.bb{background:rgba(52,152,219,.14);color:var(--blue)}.bo{background:rgba(230,126,34,.14);color:var(--orange)}
.bgold{background:rgba(245,166,35,.14);color:var(--gold)}.bgray{background:rgba(138,154,184,.1);color:var(--t2)}
.bteal{background:rgba(26,188,156,.14);color:var(--teal)}.bpur{background:rgba(155,89,182,.14);color:var(--purple)}

/* BUTTONS */
.btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:7px;font-size:12px;font-weight:600;border:none;cursor:pointer;transition:.15s;font-family:'Inter',sans-serif;white-space:nowrap}
.btn-gold{background:var(--gold);color:#111}.btn-gold:hover{background:var(--gold2)}
.btn-ghost{background:var(--bg3);color:var(--text);border:1px solid var(--border2)}.btn-ghost:hover{background:var(--bg4)}
.btn-red{background:rgba(231,76,60,.15);color:var(--red);border:1px solid rgba(231,76,60,.3)}.btn-red:hover{background:rgba(231,76,60,.25)}
.btn-sm{padding:5px 10px;font-size:11px}.btn-xs{padding:3px 7px;font-size:10px}

/* FORMS */
.form-group{display:flex;flex-direction:column;gap:5px;margin-bottom:14px}
.form-label{font-size:9.5px;font-weight:600;color:var(--t3);letter-spacing:1.5px;text-transform:uppercase;font-family:'JetBrains Mono',monospace}
.form-control{background:var(--bg3);border:1px solid var(--border2);border-radius:7px;padding:8px 12px;color:var(--text);font-size:12.5px;outline:none;transition:.15s;font-family:'Inter',sans-serif}
.form-control:focus{border-color:var(--gold);box-shadow:0 0 0 2px rgba(245,166,35,.12)}
.form-control::placeholder{color:var(--t3)}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.form-row-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
select.form-control option{background:var(--bg3)}

/* SEARCH */
.search-bar{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.search-wrap{position:relative;flex:1;min-width:180px}
.search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--t3);font-size:13px;pointer-events:none}
.search-wrap .form-control{padding-left:32px;width:100%}

/* MODAL */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);backdrop-filter:blur(4px);z-index:1000;display:none;align-items:center;justify-content:center;padding:16px}
.overlay.open{display:flex}
.modal{background:var(--bg2);border:1px solid var(--border2);border-radius:14px;width:100%;max-width:580px;max-height:90vh;overflow-y:auto;box-shadow:0 24px 80px rgba(0,0,0,.7)}
.modal-header{display:flex;align-items:center;padding:18px 22px;border-bottom:1px solid var(--border)}
.modal-title{font-size:16px;font-weight:600;flex:1}
.modal-close{background:none;border:none;color:var(--t3);font-size:18px;cursor:pointer;padding:2px 6px;border-radius:5px;transition:.1s}
.modal-close:hover{color:var(--text);background:var(--bg3)}
.modal-body{padding:22px}
.modal-footer{padding:14px 22px;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:10px}

/* TABS */
.tabs{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:18px}
.tab{padding:9px 16px;font-size:12px;font-weight:600;color:var(--t2);cursor:pointer;border-bottom:2px solid transparent;transition:.15s;margin-bottom:-1px}
.tab:hover{color:var(--text)}.tab.active{color:var(--gold);border-bottom-color:var(--gold)}
.tab-pane{display:none}.tab-pane.active{display:block}

/* CHARTS */
.chart-box{position:relative;height:220px}

/* BAR CHART */
.bar-chart{display:flex;flex-direction:column;gap:10px}
.bar-row{display:flex;align-items:center;gap:10px}
.bar-lbl{width:130px;font-size:11px;color:var(--t2);flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-track{flex:1;height:7px;background:var(--bg4);border-radius:4px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px;transition:width .5s}
.bar-val{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--t2);width:90px;text-align:right;flex-shrink:0}

/* PAYSLIP */
.payslip{font-family:'JetBrains Mono',monospace}
.ps-header{text-align:center;padding:12px 0 14px;border-bottom:2px solid var(--border2);margin-bottom:14px}
.ps-company{font-size:18px;color:var(--gold);font-weight:600}
.ps-grid{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--border);border-radius:7px;overflow:hidden}
.ps-col{padding:12px}
.ps-col:first-child{border-right:1px solid var(--border)}
.ps-section-title{font-size:9px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:2px;margin-bottom:10px}
.ps-row{display:flex;justify-content:space-between;padding:4px 0;font-size:11.5px;border-bottom:1px dashed rgba(255,255,255,.05)}
.ps-row:last-child{border:none}
.ps-total{display:flex;justify-content:space-between;padding:8px 12px;background:var(--bg3);font-weight:600;font-size:12px;border-top:2px solid var(--border2);margin-top:6px}
.ps-net{background:linear-gradient(135deg,rgba(245,166,35,.12),rgba(245,166,35,.03));border:1px solid rgba(245,166,35,.25);border-radius:8px;padding:14px;text-align:center;margin-top:14px}
.ps-net-label{font-size:9px;color:var(--t3);letter-spacing:2px;text-transform:uppercase}
.ps-net-value{font-size:26px;color:var(--gold);margin-top:4px;font-weight:600}

/* TOASTS */
.toast-box{position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px}
.toast{background:var(--bg3);border:1px solid var(--border2);border-radius:8px;padding:10px 14px;font-size:12.5px;display:flex;align-items:center;gap:9px;box-shadow:var(--shadow);animation:slideIn .25s ease;max-width:300px}
.toast.s{border-left:3px solid var(--green)}.toast.e{border-left:3px solid var(--red)}.toast.i{border-left:3px solid var(--blue)}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}
.loader{display:inline-block;width:16px;height:16px;border:2px solid var(--border2);border-top-color:var(--gold);border-radius:50%;animation:spin .7s linear infinite}
.big-loader{width:30px;height:30px;border-width:3px}
@keyframes spin{to{transform:rotate(360deg)}}
.loading{display:flex;align-items:center;justify-content:center;height:160px}
.empty-state{text-align:center;padding:40px;color:var(--t3)}
.empty-state .ei{font-size:36px;margin-bottom:10px;opacity:.4}

/* SCROLLBAR */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}

/* UTILS */
.flex{display:flex;align-items:center;gap:8px}
.flex-between{display:flex;align-items:center;justify-content:space-between}
.gold{color:var(--gold)}.green{color:var(--green)}.red{color:var(--red)}.blue{color:var(--blue)}.muted{color:var(--t3)}
.bold{font-weight:600}.small{font-size:11px}.mt8{margin-top:8px}.mt16{margin-top:16px}
</style>
</head>
<body>

<!-- ═══════════════ SIDEBAR ═══════════════ -->
<div class="sidebar">
  <div class="logo">
    <div class="logo-title">💼 PayrollWise</div>
    <div class="logo-sub">Payroll Automation</div>
  </div>
  <nav>
    <div class="nav-group">Overview</div>
    <button class="nav-item active" onclick="show('dashboard',this)">
      <span class="nav-icon">⬡</span> Dashboard
    </button>
    <div class="nav-group">Finance</div>
    <button class="nav-item" onclick="show('payroll',this)">
      <span class="nav-icon">💰</span> Payroll
    </button>
    <button class="nav-item" onclick="show('loans',this)">
      <span class="nav-icon">🏦</span> Loans
    </button>
    <button class="nav-item" onclick="show('tax',this)">
      <span class="nav-icon">🧮</span> Tax Calculator
    </button>
    <div class="nav-group">People</div>
    <button class="nav-item" onclick="show('employees',this)">
      <span class="nav-icon">👥</span> Employees
    </button>
    <button class="nav-item" onclick="show('attendance',this)">
      <span class="nav-icon">📋</span> Attendance
    </button>
    <button class="nav-item" onclick="show('leave',this)">
      <span class="nav-icon">🏖️</span> Leave
    </button>
    <div class="nav-group">Analytics</div>
    <button class="nav-item" onclick="show('reports',this)">
      <span class="nav-icon">📊</span> Reports
    </button>
    <button class="nav-item" onclick="show('revisions',this)">
      <span class="nav-icon">📈</span> Salary Revisions
    </button>
  </nav>
  <div class="sidebar-footer">
    <div><span class="dot"></span>SQLite · Live</div>
    <div style="margin-top:3px">PayrollWise v2.0</div>
  </div>
</div>

<!-- ═══════════════ MAIN ═══════════════ -->
<div class="main">
  <div class="topbar">
    <div>
      <div class="page-title" id="topbar-title">Dashboard</div>
      <div class="page-sub" id="topbar-sub">Overview</div>
    </div>
    <div class="topbar-actions">
      <div class="time-display" id="clock"></div>
    </div>
  </div>
  <div class="content">

<!-- ───────── DASHBOARD ───────── -->
<div id="page-dashboard" class="page active">
  <div class="stats-grid" id="dash-stats">
    <div class="loading"><div class="loader big-loader"></div></div>
  </div>
  <div class="g2">
    <div class="card">
      <div class="card-header">
        <div><div class="card-title">Monthly Payroll Trend</div><div class="card-sub">Net salary · last 12 months</div></div>
      </div>
      <div class="card-body"><div class="chart-box"><canvas id="trendChart"></canvas></div></div>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Dept. Cost Breakdown</div></div>
      <div class="card-body"><div class="bar-chart" id="deptBars"><div class="loading"><div class="loader"></div></div></div></div>
    </div>
  </div>
  <div class="g2">
    <div class="card">
      <div class="card-header"><div class="card-title">Top Earners</div></div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>#</th><th>Employee</th><th>Department</th><th class="num">Net Salary</th></tr></thead>
        <tbody id="topEarners"></tbody>
      </table></div>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Quick Actions</div></div>
      <div class="card-body" style="display:flex;flex-direction:column;gap:10px">
        <button class="btn btn-ghost" style="justify-content:flex-start;padding:12px 14px;gap:12px" onclick="show('payroll',document.querySelector('[onclick*=payroll]'))">
          <span style="font-size:18px">💰</span><div style="text-align:left"><div class="bold">Run Payroll</div><div class="small muted">Generate monthly payroll</div></div>
        </button>
        <button class="btn btn-ghost" style="justify-content:flex-start;padding:12px 14px;gap:12px" onclick="show('employees',document.querySelectorAll('.nav-item')[4]);openModal('addEmpModal')">
          <span style="font-size:18px">➕</span><div style="text-align:left"><div class="bold">Add Employee</div><div class="small muted">Onboard new team member</div></div>
        </button>
        <button class="btn btn-ghost" style="justify-content:flex-start;padding:12px 14px;gap:12px" onclick="show('reports',document.querySelector('[onclick*=reports]'))">
          <span style="font-size:18px">📊</span><div style="text-align:left"><div class="bold">View Reports</div><div class="small muted">Analytics & exports</div></div>
        </button>
        <button class="btn btn-ghost" style="justify-content:flex-start;padding:12px 14px;gap:12px" onclick="show('tax',document.querySelector('[onclick*=tax]'))">
          <span style="font-size:18px">🧮</span><div style="text-align:left"><div class="bold">Tax Calculator</div><div class="small muted">New vs old regime</div></div>
        </button>
      </div>
    </div>
  </div>
</div>

<!-- ───────── EMPLOYEES ───────── -->
<div id="page-employees" class="page">
  <div class="flex-between" style="margin-bottom:14px;flex-wrap:wrap;gap:10px">
    <div class="search-bar" style="margin:0;flex:1">
      <div class="search-wrap"><span class="search-icon">🔍</span><input class="form-control" id="empSearch" placeholder="Search name, code, email…" oninput="loadEmps()"></div>
      <select class="form-control" id="empDept" onchange="loadEmps()" style="width:170px"><option value="">All Departments</option></select>
      <select class="form-control" id="empStatus" onchange="loadEmps()" style="width:130px">
        <option value="">All Status</option><option>Active</option><option>Inactive</option><option>Terminated</option>
      </select>
    </div>
    <button class="btn btn-gold" onclick="openModal('addEmpModal')">＋ Add Employee</button>
  </div>
  <div class="card">
    <div class="card-header">
      <div class="card-title">Employee Directory</div>
      <div class="card-actions"><span id="empCount" class="badge bgray">—</span></div>
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Code</th><th>Name</th><th>Department</th><th>Designation</th><th>Grade</th><th class="num">Basic</th><th>Joined</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody id="empTable"></tbody>
    </table></div>
  </div>
</div>

<!-- ───────── PAYROLL ───────── -->
<div id="page-payroll" class="page">
  <div class="g2" style="align-items:start">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Payroll Periods</div>
        <div class="card-actions"><button class="btn btn-sm btn-ghost" onclick="loadPeriods()">↻</button></div>
      </div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>Period</th><th>Days</th><th>Records</th><th class="num">Total Net</th><th>Status</th><th></th></tr></thead>
        <tbody id="periodsTable"></tbody>
      </table></div>
    </div>
    <div>
      <div class="card" id="periodPanel" style="display:none">
        <div class="card-header">
          <div><div class="card-title" id="selPeriodName">—</div><div class="card-sub">Selected Period</div></div>
          <div class="card-actions"><span id="selPeriodBadge"></span></div>
        </div>
        <div class="card-body">
          <div style="display:flex;flex-direction:column;gap:9px">
            <button class="btn btn-gold" onclick="doGenerate()">▶ Generate Payroll</button>
            <button class="btn btn-ghost" onclick="doApprove()">✓ Approve All Draft</button>
            <button class="btn btn-ghost" onclick="openMarkPaid()">💳 Mark as Paid</button>
            <button class="btn btn-ghost" onclick="exportCSV()">⬇ Export CSV</button>
          </div>
          <div class="mt16" id="periodStats" style="display:grid;grid-template-columns:1fr 1fr;gap:10px"></div>
        </div>
      </div>
      <div class="card" id="noPeriodMsg">
        <div class="card-body"><div class="empty-state"><div class="ei">💰</div><div>Select a period to manage payroll</div></div></div>
      </div>
    </div>
  </div>
  <div class="card" id="registerCard" style="display:none">
    <div class="card-header">
      <div class="card-title" id="registerTitle">Payroll Register</div>
      <div class="card-actions">
        <input class="form-control" id="regSearch" placeholder="Search…" oninput="filterReg()" style="width:170px">
        <span id="regCount" class="badge bgray">—</span>
      </div>
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Code</th><th>Employee</th><th>Dept</th><th class="num">Basic</th><th class="num">Gross</th><th class="num">PF</th><th class="num">TDS</th><th class="num">Deductions</th><th class="num">Net</th><th>Status</th><th>Payslip</th></tr></thead>
      <tbody id="regTable"></tbody>
    </table></div>
    <div class="tbl-footer">
      <span>Headcount: <b id="regHC">—</b></span>
      <span>Gross: <b class="gold" id="regGross">—</b></span>
      <span>Deductions: <b class="red" id="regDed">—</b></span>
      <span>Net: <b class="green" id="regNet">—</b></span>
    </div>
  </div>
</div>

<!-- ───────── ATTENDANCE ───────── -->
<div id="page-attendance" class="page">
  <div class="flex" style="margin-bottom:16px;flex-wrap:wrap;gap:10px">
    <select class="form-control" id="attYear" onchange="loadAtt()" style="width:100px"><option value="2026">2026</option><option value="2025">2025</option></select>
    <select class="form-control" id="attMonth" onchange="loadAtt()" style="width:130px">
      <option value="1">January</option><option value="2">February</option><option value="3" selected>March</option>
      <option value="4">April</option><option value="5">May</option><option value="6">June</option>
      <option value="7">July</option><option value="8">August</option><option value="9">September</option>
      <option value="10">October</option><option value="11">November</option><option value="12">December</option>
    </select>
    <button class="btn btn-gold" style="margin-left:auto" onclick="openModal('markAttModal')">＋ Mark Attendance</button>
  </div>
  <div class="stats-grid" id="attStats"></div>
  <div class="card">
    <div class="card-header">
      <div class="card-title">Monthly Attendance Summary</div>
      <div class="card-actions"><span id="attCount" class="badge bgray">—</span></div>
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Code</th><th>Employee</th><th class="num">Present</th><th class="num">Absent</th><th class="num">Leave</th><th class="num">Total Hours</th><th class="num">Avg Hours</th></tr></thead>
      <tbody id="attTable"></tbody>
    </table></div>
  </div>
</div>

<!-- ───────── LEAVE ───────── -->
<div id="page-leave" class="page">
  <div class="flex-between" style="margin-bottom:14px">
    <div class="tabs" style="margin:0;border:none">
      <div class="tab active" onclick="switchLeaveTab('all',this)">All Requests</div>
      <div class="tab" onclick="switchLeaveTab('pending',this)">Pending</div>
    </div>
    <button class="btn btn-gold" onclick="openModal('applyLeaveModal')">＋ Apply Leave</button>
  </div>
  <div class="stats-grid" id="leaveStats"></div>
  <div class="card">
    <div class="card-header">
      <div class="card-title">Leave Requests</div>
      <div class="card-actions">
        <button id="approveAllBtn" class="btn btn-sm btn-ghost" onclick="approveAllLeaves()" style="display:none">✓ Approve All</button>
        <span id="leaveCount" class="badge bgray">—</span>
      </div>
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Employee</th><th>Type</th><th>From</th><th>To</th><th class="num">Days</th><th>Reason</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody id="leaveTable"></tbody>
    </table></div>
  </div>
</div>

<!-- ───────── LOANS ───────── -->
<div id="page-loans" class="page">
  <div class="flex-between" style="margin-bottom:14px">
    <select class="form-control" id="loanStatus" onchange="loadLoans()" style="width:150px">
      <option value="">All Loans</option><option value="Active">Active</option><option value="Closed">Closed</option>
    </select>
    <button class="btn btn-gold" onclick="openModal('addLoanModal')">＋ New Loan</button>
  </div>
  <div class="stats-grid" id="loanStats"></div>
  <div class="card">
    <div class="card-header"><div class="card-title">Loan Register</div><div class="card-actions"><span id="loanCount" class="badge bgray">—</span></div></div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Code</th><th>Employee</th><th>Purpose</th><th class="num">Amount</th><th class="num">EMI</th><th>Progress</th><th class="num">Outstanding</th><th>Status</th></tr></thead>
      <tbody id="loanTable"></tbody>
    </table></div>
  </div>
</div>

<!-- ───────── TAX CALCULATOR ───────── -->
<div id="page-tax" class="page">
  <div class="g2">
    <div>
      <div class="card">
        <div class="card-header"><div class="card-title">Income Details</div><div class="card-sub">FY 2025-26</div></div>
        <div class="card-body">
          <div class="form-group">
            <div class="form-label">Employee (auto-fill salary)</div>
            <select class="form-control" id="taxEmp" onchange="taxAutoFill()"><option value="">— Enter manually —</option></select>
          </div>
          <div class="form-group">
            <div class="form-label">Monthly Gross Salary (₹)</div>
            <input class="form-control" type="number" id="taxGross" placeholder="e.g. 85000" oninput="calcTax()" style="font-size:16px;font-family:'JetBrains Mono',monospace">
          </div>
          <div class="form-group">
            <div class="form-label">Tax Regime</div>
            <div style="display:flex;gap:10px">
              <label style="flex:1;display:flex;align-items:center;gap:8px;padding:9px 12px;background:var(--bg3);border:1px solid var(--border2);border-radius:7px;cursor:pointer">
                <input type="radio" name="regime" value="new" checked onchange="calcTax()">
                <div><div class="bold small">New Regime</div><div class="small muted">Lower rates</div></div>
              </label>
              <label style="flex:1;display:flex;align-items:center;gap:8px;padding:9px 12px;background:var(--bg3);border:1px solid var(--border2);border-radius:7px;cursor:pointer">
                <input type="radio" name="regime" value="old" onchange="calcTax()">
                <div><div class="bold small">Old Regime</div><div class="small muted">More exemptions</div></div>
              </label>
            </div>
          </div>
          <div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:12px;font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--t3);line-height:1.8">
            <div style="color:var(--t2);font-weight:600;margin-bottom:4px">New Regime Slabs</div>
            ₹0–4L: 0%  &nbsp; ₹4–8L: 5%  &nbsp; ₹8–12L: 10%<br>
            ₹12–16L: 15%  &nbsp; ₹16–20L: 20%  &nbsp; ₹20–24L: 25%<br>
            Above ₹24L: 30%  +  4% Cess<br>
            <span style="color:var(--green)">Rebate 87A: ₹60,000 if income ≤ ₹12L</span>
          </div>
        </div>
      </div>
      <div class="card mt16" id="compareCard" style="display:none">
        <div class="card-header"><div class="card-title">Regime Comparison</div></div>
        <div class="card-body" id="compareBody"></div>
      </div>
    </div>
    <div>
      <div class="card">
        <div class="card-header"><div class="card-title">Tax Result</div><div class="card-actions"><span id="taxBadge" class="badge bgray">Enter salary</span></div></div>
        <div class="card-body" id="taxResult">
          <div class="empty-state"><div class="ei">🧮</div><div>Enter monthly gross salary to calculate</div></div>
        </div>
      </div>
      <div class="card mt16" id="slabCard" style="display:none">
        <div class="card-header"><div class="card-title">Slab-wise Breakdown</div></div>
        <div class="card-body"><div class="bar-chart" id="slabBars"></div></div>
      </div>
    </div>
  </div>
</div>

<!-- ───────── REPORTS ───────── -->
<div id="page-reports" class="page">
  <div class="tabs" id="reportTabs">
    <div class="tab active" onclick="switchReportTab('ytd',this)">YTD Salary</div>
    <div class="tab" onclick="switchReportTab('dept',this)">Dept Summary</div>
    <div class="tab" onclick="switchReportTab('audit',this)">Audit Trail</div>
  </div>
  <div id="rp-ytd" class="tab-pane active">
    <div class="flex" style="margin-bottom:14px;gap:10px">
      <select class="form-control" id="ytdYear" style="width:110px"><option value="2026">2026</option><option value="2025">2025</option></select>
      <button class="btn btn-gold" onclick="loadYTD()">Load</button>
      <button class="btn btn-ghost" onclick="exportYTD()">⬇ CSV</button>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Year-to-Date Salary</div><div class="card-actions"><span id="ytdCount" class="badge bgray">—</span></div></div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>Code</th><th>Employee</th><th class="num">Months</th><th class="num">YTD Gross</th><th class="num">YTD TDS</th><th class="num">YTD PF</th><th class="num">YTD Net</th></tr></thead>
        <tbody id="ytdTable"></tbody>
      </table></div>
      <div class="tbl-footer"><span id="ytdTotals"></span></div>
    </div>
  </div>
  <div id="rp-dept" class="tab-pane">
    <div class="flex" style="margin-bottom:14px;gap:10px">
      <select class="form-control" id="deptPeriod" style="width:180px"></select>
      <button class="btn btn-gold" onclick="loadDeptSummary()">Load</button>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Department Payroll Cost</div></div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>Department</th><th class="num">HC</th><th class="num">Gross</th><th class="num">Net</th><th class="num">Avg Net</th><th class="num">PF</th><th class="num">TDS</th></tr></thead>
        <tbody id="deptTable"></tbody>
      </table></div>
    </div>
    <div class="card mt16">
      <div class="card-header"><div class="card-title">Cost Distribution</div></div>
      <div class="card-body"><div class="bar-chart" id="deptBarsReport"></div></div>
    </div>
  </div>
  <div id="rp-audit" class="tab-pane">
    <div class="flex" style="margin-bottom:14px;gap:10px">
      <select class="form-control" id="auditTable" style="width:180px">
        <option value="">All Tables</option>
        <option value="employees">employees</option>
        <option value="payroll_records">payroll_records</option>
        <option value="salary_revisions">salary_revisions</option>
      </select>
      <select class="form-control" id="auditLimit" style="width:100px">
        <option value="20">20 rows</option><option value="50">50 rows</option><option value="100">100 rows</option>
      </select>
      <button class="btn btn-gold" onclick="loadAudit()">Load</button>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Audit Trail</div><div class="card-actions"><span id="auditCount" class="badge bgray">—</span></div></div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>#</th><th>Table</th><th>Record</th><th>Action</th><th>When</th><th>Old Data</th></tr></thead>
        <tbody id="auditTable2"></tbody>
      </table></div>
    </div>
  </div>
</div>

<!-- ───────── SALARY REVISIONS ───────── -->
<div id="page-revisions" class="page">
  <div class="flex-between" style="margin-bottom:14px">
    <div></div>
    <button class="btn btn-gold" onclick="openModal('addRevModal')">＋ Add Revision</button>
  </div>
  <div class="card">
    <div class="card-header"><div class="card-title">Hike Distribution (Top 10)</div></div>
    <div class="card-body"><div class="bar-chart" id="hikeBars"></div></div>
  </div>
  <div class="card">
    <div class="card-header"><div class="card-title">Revision History</div><div class="card-actions"><span id="revCount" class="badge bgray">—</span></div></div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Code</th><th>Employee</th><th>Dept</th><th class="num">Old Basic</th><th class="num">New Basic</th><th class="num">% Hike</th><th>Effective</th><th>Reason</th></tr></thead>
      <tbody id="revTable"></tbody>
    </table></div>
  </div>
</div>

  </div><!-- end content -->
</div><!-- end main -->

<!-- ════════════ MODALS ════════════ -->

<!-- Add Employee -->
<div class="overlay" id="addEmpModal">
  <div class="modal">
    <div class="modal-header"><div class="modal-title">Add Employee</div><button class="modal-close" onclick="closeModal('addEmpModal')">✕</button></div>
    <div class="modal-body">
      <div class="tabs" id="addEmpTabs">
        <div class="tab active" onclick="empTab('p',this)">Personal</div>
        <div class="tab" onclick="empTab('j',this)">Job</div>
        <div class="tab" onclick="empTab('b',this)">Bank</div>
      </div>
      <div id="emp-p">
        <div class="form-row"><div class="form-group"><div class="form-label">Code *</div><input class="form-control" id="nCode" placeholder="EMP031"></div><div class="form-group"><div class="form-label">Gender *</div><select class="form-control" id="nGender"><option>Male</option><option>Female</option><option>Other</option></select></div></div>
        <div class="form-row"><div class="form-group"><div class="form-label">First Name *</div><input class="form-control" id="nFN"></div><div class="form-group"><div class="form-label">Last Name *</div><input class="form-control" id="nLN"></div></div>
        <div class="form-row"><div class="form-group"><div class="form-label">Date of Birth</div><input class="form-control" id="nDOB" type="date"></div><div class="form-group"><div class="form-label">Phone</div><input class="form-control" id="nPhone"></div></div>
        <div class="form-group"><div class="form-label">Email *</div><input class="form-control" id="nEmail" type="email"></div>
        <div class="form-row"><div class="form-group"><div class="form-label">City</div><input class="form-control" id="nCity"></div><div class="form-group"><div class="form-label">State</div><input class="form-control" id="nState"></div></div>
        <div class="form-group"><div class="form-label">Address</div><input class="form-control" id="nAddr"></div>
      </div>
      <div id="emp-j" style="display:none">
        <div class="form-row"><div class="form-group"><div class="form-label">Department *</div><select class="form-control" id="nDept" onchange="loadDesigs()"><option value="">Select…</option></select></div><div class="form-group"><div class="form-label">Designation *</div><select class="form-control" id="nDesig"><option value="">Select dept first</option></select></div></div>
        <div class="form-row"><div class="form-group"><div class="form-label">Grade *</div><select class="form-control" id="nGrade"><option value="">Select…</option></select></div><div class="form-group"><div class="form-label">Basic Salary (₹) *</div><input class="form-control" id="nBasic" type="number"></div></div>
        <div class="form-row"><div class="form-group"><div class="form-label">Date Joined *</div><input class="form-control" id="nJoined" type="date"></div><div class="form-group"><div class="form-label">Employment Type</div><select class="form-control" id="nType"><option>Full-Time</option><option>Part-Time</option><option>Contract</option><option>Intern</option></select></div></div>
      </div>
      <div id="emp-b" style="display:none">
        <div class="form-row"><div class="form-group"><div class="form-label">PAN Number *</div><input class="form-control" id="nPAN" placeholder="ABCDE1234F"></div><div class="form-group"><div class="form-label">Last 4 Aadhaar *</div><input class="form-control" id="nAadh" maxlength="4"></div></div>
        <div class="form-row"><div class="form-group"><div class="form-label">Bank Account *</div><input class="form-control" id="nBankAcc"></div><div class="form-group"><div class="form-label">Bank Name *</div><input class="form-control" id="nBankName"></div></div>
        <div class="form-group"><div class="form-label">IFSC Code *</div><input class="form-control" id="nIFSC"></div>
      </div>
    </div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal('addEmpModal')">Cancel</button><button class="btn btn-gold" onclick="saveEmployee()">Save Employee</button></div>
  </div>
</div>

<!-- Employee Detail -->
<div class="overlay" id="empDetailModal">
  <div class="modal" style="max-width:700px">
    <div class="modal-header">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:38px;height:38px;background:var(--gold);border-radius:9px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#111;font-size:16px" id="detAvatar">?</div>
        <div><div class="modal-title" id="detName">—</div><div class="small muted" id="detCode">—</div></div>
      </div>
      <button class="modal-close" onclick="closeModal('empDetailModal')">✕</button>
    </div>
    <div class="modal-body" id="detBody"><div class="loading"><div class="loader big-loader"></div></div></div>
  </div>
</div>

<!-- Payslip -->
<div class="overlay" id="payslipModal">
  <div class="modal" style="max-width:520px">
    <div class="modal-header"><div class="modal-title">Salary Slip</div><button class="modal-close" onclick="closeModal('payslipModal')">✕</button></div>
    <div class="modal-body payslip" id="payslipBody"><div class="loading"><div class="loader big-loader"></div></div></div>
  </div>
</div>

<!-- Mark Paid -->
<div class="overlay" id="markPaidModal">
  <div class="modal" style="max-width:360px">
    <div class="modal-header"><div class="modal-title">Mark as Paid</div><button class="modal-close" onclick="closeModal('markPaidModal')">✕</button></div>
    <div class="modal-body">
      <div class="form-group"><div class="form-label">Payment Date</div><input class="form-control" type="date" id="payDate"></div>
    </div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal('markPaidModal')">Cancel</button><button class="btn btn-gold" onclick="confirmPaid()">Confirm</button></div>
  </div>
</div>

<!-- Mark Attendance -->
<div class="overlay" id="markAttModal">
  <div class="modal" style="max-width:420px">
    <div class="modal-header"><div class="modal-title">Mark Attendance</div><button class="modal-close" onclick="closeModal('markAttModal')">✕</button></div>
    <div class="modal-body">
      <div class="form-group"><div class="form-label">Employee</div><select class="form-control" id="attEmp"></select></div>
      <div class="form-row">
        <div class="form-group"><div class="form-label">Date</div><input class="form-control" type="date" id="attDate"></div>
        <div class="form-group"><div class="form-label">Status</div><select class="form-control" id="attStatus"><option>Present</option><option>Absent</option><option>Half-Day</option><option>On-Leave</option></select></div>
      </div>
      <div class="form-row">
        <div class="form-group"><div class="form-label">Check In</div><input class="form-control" type="time" id="attIn" value="09:00"></div>
        <div class="form-group"><div class="form-label">Check Out</div><input class="form-control" type="time" id="attOut" value="18:00"></div>
      </div>
      <div class="form-group"><div class="form-label">Hours Worked</div><input class="form-control" type="number" id="attHours" value="9" step="0.5"></div>
    </div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal('markAttModal')">Cancel</button><button class="btn btn-gold" onclick="saveAttendance()">Save</button></div>
  </div>
</div>

<!-- Apply Leave -->
<div class="overlay" id="applyLeaveModal">
  <div class="modal" style="max-width:420px">
    <div class="modal-header"><div class="modal-title">Apply for Leave</div><button class="modal-close" onclick="closeModal('applyLeaveModal')">✕</button></div>
    <div class="modal-body">
      <div class="form-group"><div class="form-label">Employee</div><select class="form-control" id="lvEmp"></select></div>
      <div class="form-group"><div class="form-label">Leave Type</div><select class="form-control" id="lvType"></select></div>
      <div class="form-row">
        <div class="form-group"><div class="form-label">From</div><input class="form-control" type="date" id="lvFrom" onchange="calcLvDays()"></div>
        <div class="form-group"><div class="form-label">To</div><input class="form-control" type="date" id="lvTo" onchange="calcLvDays()"></div>
      </div>
      <div class="form-group"><div class="form-label">Days</div><input class="form-control" id="lvDays" readonly style="opacity:.7"></div>
      <div class="form-group"><div class="form-label">Reason *</div><input class="form-control" id="lvReason" placeholder="Brief reason"></div>
    </div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal('applyLeaveModal')">Cancel</button><button class="btn btn-gold" onclick="submitLeave()">Apply</button></div>
  </div>
</div>

<!-- Add Loan -->
<div class="overlay" id="addLoanModal">
  <div class="modal" style="max-width:420px">
    <div class="modal-header"><div class="modal-title">New Employee Loan</div><button class="modal-close" onclick="closeModal('addLoanModal')">✕</button></div>
    <div class="modal-body">
      <div class="form-group"><div class="form-label">Employee</div><select class="form-control" id="lnEmp"></select></div>
      <div class="form-row">
        <div class="form-group"><div class="form-label">Loan Amount (₹)</div><input class="form-control" type="number" id="lnAmt" oninput="calcEMI()"></div>
        <div class="form-group"><div class="form-label">Total EMIs</div><input class="form-control" type="number" id="lnEmis" value="12" oninput="calcEMI()"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><div class="form-label">Loan Date</div><input class="form-control" type="date" id="lnDate"></div>
        <div class="form-group"><div class="form-label">EMI Amount (₹)</div><input class="form-control" id="lnEMI" readonly style="opacity:.7"></div>
      </div>
      <div class="form-group"><div class="form-label">Purpose</div><input class="form-control" id="lnPurpose" placeholder="e.g. Medical emergency"></div>
    </div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal('addLoanModal')">Cancel</button><button class="btn btn-gold" onclick="saveLoan()">Create Loan</button></div>
  </div>
</div>

<!-- Add Revision -->
<div class="overlay" id="addRevModal">
  <div class="modal" style="max-width:420px">
    <div class="modal-header"><div class="modal-title">Add Salary Revision</div><button class="modal-close" onclick="closeModal('addRevModal')">✕</button></div>
    <div class="modal-body">
      <div class="form-group"><div class="form-label">Employee</div><select class="form-control" id="rvEmp" onchange="loadEmpBasic()"></select></div>
      <div class="form-row">
        <div class="form-group"><div class="form-label">Current Basic (₹)</div><input class="form-control" id="rvOld" readonly style="opacity:.7"></div>
        <div class="form-group"><div class="form-label">New Basic (₹)</div><input class="form-control" type="number" id="rvNew" oninput="calcHike()"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><div class="form-label">Hike %</div><input class="form-control" id="rvHike" readonly style="opacity:.7"></div>
        <div class="form-group"><div class="form-label">Effective Date</div><input class="form-control" type="date" id="rvDate"></div>
      </div>
      <div class="form-group"><div class="form-label">Reason</div><select class="form-control" id="rvReason"><option>Annual Increment 2026</option><option>Promotion</option><option>Mid-Year Revision</option><option>Performance Recognition</option><option>Market Correction</option></select></div>
    </div>
    <div class="modal-footer"><button class="btn btn-ghost" onclick="closeModal('addRevModal')">Cancel</button><button class="btn btn-gold" onclick="saveRevision()">Save</button></div>
  </div>
</div>

<!-- TOAST CONTAINER -->
<div class="toast-box" id="toasts"></div>

<!-- ════════════ JAVASCRIPT ════════════ -->
<script>
// ── State ──────────────────────────────────────────────────────
let currentPid = null, regData = [], allLeaves = [], allEmps = [], allDepts = [], allGrades = [], ytdData = [];
let trendChart = null;

// ── Helpers ────────────────────────────────────────────────────
const fmt = n => n==null ? '—' : '₹' + Number(n).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtK = n => {
  if(n==null) return '—'; n=Number(n);
  if(n>=10000000) return '₹'+(n/10000000).toFixed(2)+'Cr';
  if(n>=100000)   return '₹'+(n/100000).toFixed(2)+'L';
  if(n>=1000)     return '₹'+(n/1000).toFixed(1)+'K';
  return '₹'+n.toFixed(0);
};

function badge(s) {
  const m = {Active:'bg',Inactive:'bgray',Terminated:'br','On-Leave':'bo',
             Paid:'bg',Approved:'bb',Draft:'bgray',Revised:'bo',Cancelled:'br',
             Present:'bg',Absent:'br','Half-Day':'bo','On-Leave2':'bgold',
             Pending:'bgold',Approved2:'bg',Rejected:'br',
             'Full-Time':'bb','Part-Time':'bo',Contract:'bteal',Intern:'bpur',
             Open:'bgray',Processing:'bb',Closed:'bteal',Defaulted:'br'};
  const k = m[s]||'bgray';
  return `<span class="badge ${k}">${s}</span>`;
}

function toast(msg, type='i') {
  const icons = {s:'✓',e:'✗',i:'ℹ'};
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  document.getElementById('toasts').appendChild(el);
  setTimeout(()=>el.remove(), 3500);
}

async function api(url, method='GET', body=null) {
  const opts = {method, headers:{'Content-Type':'application/json'}};
  if(body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  return r.json().catch(()=>({}));
}

// ── Navigation ─────────────────────────────────────────────────
const pageTitles = {
  dashboard:['Dashboard','Overview'], employees:['Employees','People / Directory'],
  payroll:['Payroll','Finance / Payroll Processing'], attendance:['Attendance','People / Attendance Tracker'],
  leave:['Leave','People / Leave Management'], loans:['Loans','Finance / Loan Register'],
  tax:['Tax Calculator','Finance / Income Tax FY 2025-26'],
  reports:['Reports','Analytics / Reports'], revisions:['Salary Revisions','Finance / Increment History']
};

function show(page, btn) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(i=>i.classList.remove('active'));
  document.getElementById('page-'+page).classList.add('active');
  if(btn) btn.classList.add('active');
  const [title,sub] = pageTitles[page]||['',''];
  document.getElementById('topbar-title').textContent = title;
  document.getElementById('topbar-sub').textContent   = sub;
  loaders[page]?.();
}

const loaders = {
  dashboard:  loadDashboard,
  employees:  ()=>{if(!allEmps.length)initEmps()},
  payroll:    loadPeriods,
  attendance: loadAtt,
  leave:      loadLeaves,
  loans:      loadLoans,
  revisions:  loadRevisions,
  reports:    ()=>loadYTD(),
  tax:        initTax,
};

// ── CLOCK ──────────────────────────────────────────────────────
function tick(){document.getElementById('clock').textContent=new Date().toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})+' '+new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});}
tick(); setInterval(tick,1000);

// ── DASHBOARD ──────────────────────────────────────────────────
async function loadDashboard() {
  const d = await api('/api/stats');
  document.getElementById('dash-stats').innerHTML = `
    <div class="stat gold"><div class="stat-icon">👥</div><div class="stat-label">Active Employees</div><div class="stat-value">${d.emp_active}</div><div class="stat-sub">${d.emp_total} total · ${d.dept_count} depts</div></div>
    <div class="stat blue"><div class="stat-icon">💰</div><div class="stat-label">Gross Payroll</div><div class="stat-value" style="font-size:17px">${fmtK(d.gross_payroll)}</div><div class="stat-sub">${d.period_name}</div></div>
    <div class="stat green"><div class="stat-icon">🏦</div><div class="stat-label">Net Disbursed</div><div class="stat-value" style="font-size:17px">${fmtK(d.net_payroll)}</div><div class="stat-sub">${d.payroll_headcount} paid</div></div>
    <div class="stat teal"><div class="stat-icon">📅</div><div class="stat-label">Leave Pending</div><div class="stat-value">${d.leave_pending}</div><div class="stat-sub">awaiting approval</div></div>
    <div class="stat orange"><div class="stat-icon">🏦</div><div class="stat-label">Loan Outstanding</div><div class="stat-value" style="font-size:17px">${fmtK(d.loan_outstanding)}</div><div class="stat-sub">active loans</div></div>
  `;

  // Trend chart
  const trend = d.monthly_trend || [];
  const labels = trend.map(t=>t.period_name.slice(0,3)+" '"+String(t.year).slice(2));
  const nets   = trend.map(t=>t.net_k);
  const gross  = trend.map(t=>t.gross_k);
  if(trendChart) trendChart.destroy();
  trendChart = new Chart(document.getElementById('trendChart').getContext('2d'), {
    type:'line',
    data:{labels, datasets:[
      {label:'Gross (K)',data:gross,borderColor:'#f5a623',backgroundColor:'rgba(245,166,35,.08)',tension:.4,pointRadius:3},
      {label:'Net (K)',  data:nets, borderColor:'#2ecc71',backgroundColor:'rgba(46,204,113,.08)', tension:.4,pointRadius:3}
    ]},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index'},
      plugins:{legend:{labels:{color:'#8a9ab8',font:{size:11}}}},
      scales:{x:{grid:{color:'#2a3347'},ticks:{color:'#8a9ab8',font:{size:10}}},
              y:{grid:{color:'#2a3347'},ticks:{color:'#8a9ab8',font:{size:10},callback:v=>'₹'+v+'K'}}}}
  });

  // Dept bars
  const costs = d.dept_costs||[];
  const max = Math.max(...costs.map(c=>c.net),1);
  const colors=['#f5a623','#3498db','#2ecc71','#1abc9c','#9b59b6','#e67e22','#e74c3c','#34495e'];
  document.getElementById('deptBars').innerHTML = costs.map((c,i)=>`
    <div class="bar-row">
      <div class="bar-lbl">${c.dept_name}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(c.net/max*100).toFixed(1)}%;background:${colors[i%colors.length]}"></div></div>
      <div class="bar-val">${fmtK(c.net)} <span class="muted">(${c.hc})</span></div>
    </div>`).join('');

  // Top earners
  document.getElementById('topEarners').innerHTML = (d.top_earners||[]).map((e,i)=>`<tr>
    <td class="muted mono">${i+1}</td>
    <td class="bold">${e.name}</td>
    <td class="muted small">${e.dept}</td>
    <td class="num gold">${fmt(e.net)}</td>
  </tr>`).join('');
}

// ── EMPLOYEES ──────────────────────────────────────────────────
async function initEmps() {
  allDepts = await api('/api/departments');
  allGrades= await api('/api/grades');
  const sel = document.getElementById('empDept');
  allDepts.forEach(d=>sel.innerHTML+=`<option value="${d.dept_id}">${d.dept_name}</option>`);
  const nd = document.getElementById('nDept');
  allDepts.forEach(d=>nd.innerHTML+=`<option value="${d.dept_id}">${d.dept_name}</option>`);
  const ng = document.getElementById('nGrade');
  allGrades.forEach(g=>ng.innerHTML+=`<option value="${g.grade_id}">${g.grade_code} — ${g.grade_name}</option>`);
  loadEmps();
}

async function loadEmps() {
  const q = document.getElementById('empSearch').value;
  const d = document.getElementById('empDept').value;
  const s = document.getElementById('empStatus').value;
  const p = new URLSearchParams();
  if(q) p.set('q',q); if(d) p.set('dept',d); if(s) p.set('status',s);
  allEmps = await api('/api/employees?'+p);
  document.getElementById('empCount').textContent = allEmps.length+' employees';
  document.getElementById('empTable').innerHTML = allEmps.map(e=>`<tr>
    <td class="mono gold" style="cursor:pointer" onclick="viewEmp(${e.emp_id})">${e.emp_code}</td>
    <td class="bold" style="cursor:pointer" onclick="viewEmp(${e.emp_id})">${e.full_name}</td>
    <td class="muted small">${e.dept_name}</td>
    <td class="small">${e.desig_title}</td>
    <td><span class="badge bgray">${e.grade_code}</span></td>
    <td class="num">${fmt(e.basic_salary)}</td>
    <td class="mono muted">${e.date_joined}</td>
    <td>${badge(e.status)}</td>
    <td>
      <div class="flex">
        <button class="btn btn-xs btn-ghost" onclick="viewEmp(${e.emp_id})">View</button>
        ${e.status==='Active'?`<button class="btn btn-xs btn-red" onclick="toggleStatus(${e.emp_id},'Inactive')">Deactivate</button>`:''}
        ${e.status==='Inactive'?`<button class="btn btn-xs btn-ghost" onclick="toggleStatus(${e.emp_id},'Active')">Activate</button>`:''}
      </div>
    </td>
  </tr>`).join('')||'<tr><td colspan="9"><div class="empty-state"><div class="ei">👥</div><div>No employees found</div></div></td></tr>';
}

async function viewEmp(id) {
  openModal('empDetailModal');
  document.getElementById('detBody').innerHTML = '<div class="loading"><div class="loader big-loader"></div></div>';
  const d = await api(`/api/employees/${id}`);
  document.getElementById('detName').textContent = d.full_name;
  document.getElementById('detCode').textContent = `${d.emp_code} · ${d.dept_name}`;
  document.getElementById('detAvatar').textContent = (d.full_name||'?')[0];
  const ii = (l,v)=>`<div style="background:var(--bg3);border:1px solid var(--border);border-radius:7px;padding:9px 12px"><div style="font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;font-family:'JetBrains Mono',monospace;margin-bottom:3px">${l}</div><div style="font-size:12.5px;font-weight:500">${v||'—'}</div></div>`;
  document.getElementById('detBody').innerHTML = `
    <div class="g2" style="gap:10px;margin-bottom:14px">
      ${ii('Email',d.email)}${ii('Phone',d.phone)}${ii('Designation',d.desig_title)}${ii('Grade',d.grade_name)}
      ${ii('Basic Salary',fmt(d.basic_salary))}${ii('Gross CTC',fmt(d.gross_ctc))}${ii('Date Joined',d.date_joined)}${ii('Status',badge(d.status))}
    </div>
    <div class="bold" style="margin-bottom:8px;font-size:12px">Recent Payslips</div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Period</th><th class="num">Gross</th><th class="num">Net</th><th>Days</th><th>Status</th></tr></thead>
      <tbody>${(d.payslips||[]).map(p=>`<tr><td class="mono small">${p.period_name}</td><td class="num">${fmt(p.gross_salary)}</td><td class="num green">${fmt(p.net_salary)}</td><td class="mono">${p.days_present}</td><td>${badge(p.status)}</td></tr>`).join('')||'<tr><td colspan="5" class="muted">No records</td></tr>'}</tbody>
    </table></div>`;
}

async function loadDesigs() {
  const dept = document.getElementById('nDept').value;
  const sel  = document.getElementById('nDesig');
  if(!dept){sel.innerHTML='<option>Select dept first</option>';return;}
  const ds = await api(`/api/designations?dept_id=${dept}`);
  sel.innerHTML = ds.map(d=>`<option value="${d.desig_id}">${d.desig_title}</option>`).join('');
}

function empTab(t, btn) {
  ['p','j','b'].forEach(x=>document.getElementById('emp-'+x).style.display='none');
  document.getElementById('emp-'+t).style.display='';
  document.querySelectorAll('#addEmpTabs .tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
}

async function saveEmployee() {
  const data = {
    emp_code:document.getElementById('nCode').value,
    first_name:document.getElementById('nFN').value,
    last_name:document.getElementById('nLN').value,
    gender:document.getElementById('nGender').value,
    dob:document.getElementById('nDOB').value,
    email:document.getElementById('nEmail').value,
    phone:document.getElementById('nPhone').value,
    address:document.getElementById('nAddr').value,
    city:document.getElementById('nCity').value,
    state:document.getElementById('nState').value,
    dept_id:document.getElementById('nDept').value,
    desig_id:document.getElementById('nDesig').value,
    grade_id:document.getElementById('nGrade').value,
    basic_salary:document.getElementById('nBasic').value,
    date_joined:document.getElementById('nJoined').value,
    employment_type:document.getElementById('nType').value,
    pan_number:document.getElementById('nPAN').value,
    aadhaar_last4:document.getElementById('nAadh').value,
    bank_account:document.getElementById('nBankAcc').value,
    bank_name:document.getElementById('nBankName').value,
    ifsc_code:document.getElementById('nIFSC').value,
  };
  const r = await api('/api/employees','POST',data);
  if(r.success){toast('Employee added!','s');closeModal('addEmpModal');loadEmps();}
  else toast(r.error||'Error saving','e');
}

async function toggleStatus(id, status) {
  await api(`/api/employees/${id}/status`,'PATCH',{status});
  toast(`Status → ${status}`,'s');
  loadEmps();
}

// ── PAYROLL ────────────────────────────────────────────────────
async function loadPeriods() {
  const data = await api('/api/payroll/periods');
  document.getElementById('periodsTable').innerHTML = data.map(p=>`<tr style="cursor:pointer" onclick="selectPeriod(${p.period_id},'${p.period_name}','${p.status}',${p.records||0},${p.total_net||0},${p.working_days})">
    <td class="bold">${p.period_name}</td>
    <td class="mono">${p.working_days}</td>
    <td class="mono">${p.records||0}</td>
    <td class="num">${fmtK(p.total_net||0)}</td>
    <td>${badge(p.status)}</td>
    <td><button class="btn btn-xs btn-ghost">Select</button></td>
  </tr>`).join('');

  // Populate period selector in reports
  const sel = document.getElementById('deptPeriod');
  if(!sel.children.length) data.filter(p=>p.records>0).forEach(p=>sel.innerHTML+=`<option value="${p.period_id}">${p.period_name}</option>`);
}

async function selectPeriod(pid, name, status, records, net, wdays) {
  currentPid = pid;
  document.getElementById('selPeriodName').textContent = name;
  document.getElementById('selPeriodBadge').innerHTML  = badge(status);
  document.getElementById('periodPanel').style.display = '';
  document.getElementById('noPeriodMsg').style.display = 'none';
  document.getElementById('periodStats').innerHTML = `
    <div style="background:var(--bg3);border:1px solid var(--border);border-radius:7px;padding:10px"><div class="stat-label">Records</div><div class="stat-value" style="font-size:18px">${records}</div></div>
    <div style="background:var(--bg3);border:1px solid var(--border);border-radius:7px;padding:10px"><div class="stat-label">Net Total</div><div class="stat-value" style="font-size:16px">${fmtK(net)}</div></div>
  `;
  loadPeriods();
  if(records>0) loadRegister(pid, name);
}

async function loadRegister(pid, name) {
  document.getElementById('registerCard').style.display = '';
  document.getElementById('registerTitle').textContent  = `Register — ${name}`;
  document.getElementById('regTable').innerHTML = '<tr><td colspan="11"><div class="loading"><div class="loader"></div></div></td></tr>';
  regData = await api(`/api/payroll/register/${pid}`);
  renderReg(regData);
}

function renderReg(rows) {
  let tg=0,td=0,tn=0;
  document.getElementById('regTable').innerHTML = rows.map(r=>{
    tg+=r.gross_salary||0; td+=r.total_deductions||0; tn+=r.net_salary||0;
    return `<tr>
      <td class="mono gold">${r.emp_code||''}</td>
      <td class="bold">${r.name}</td>
      <td class="muted small">${r.dept_name}</td>
      <td class="num">${fmt(r.basic_salary)}</td>
      <td class="num">${fmt(r.gross_salary)}</td>
      <td class="num muted">${fmt(r.pf_employee)}</td>
      <td class="num muted">${fmt(r.income_tax_tds)}</td>
      <td class="num red">${fmt(r.total_deductions)}</td>
      <td class="num green bold">${fmt(r.net_salary)}</td>
      <td>${badge(r.status)}</td>
      <td><button class="btn btn-xs btn-ghost" onclick="viewPayslip(${r.emp_id||0},${currentPid})">Slip</button></td>
    </tr>`;
  }).join('')||'<tr><td colspan="11"><div class="empty-state"><div>No records</div></div></td></tr>';
  document.getElementById('regHC').textContent    = rows.length;
  document.getElementById('regGross').textContent = fmtK(tg);
  document.getElementById('regDed').textContent   = fmtK(td);
  document.getElementById('regNet').textContent   = fmtK(tn);
  document.getElementById('regCount').textContent = rows.length+' records';
}

function filterReg() {
  const q = document.getElementById('regSearch').value.toLowerCase();
  renderReg(regData.filter(r=>(r.name||'').toLowerCase().includes(q)||(r.emp_code||'').toLowerCase().includes(q)||(r.dept_name||'').toLowerCase().includes(q)));
}

async function viewPayslip(eid, pid) {
  openModal('payslipModal');
  if(!eid) {toast('Employee ID not found','e');return;}
  const d = await api(`/api/payroll/payslip/${eid}/${pid}`);
  if(!d.emp_code){document.getElementById('payslipBody').innerHTML='<div class="empty-state"><div>Payslip not found</div></div>';return;}
  const ps=(l,v)=>`<div class="ps-row"><span>${l}</span><span>${v}</span></div>`;
  document.getElementById('payslipBody').innerHTML = `
    <div class="ps-header"><div class="ps-company">PayrollWise Ltd</div><div class="small muted">Salary Slip · ${d.period_name}</div></div>
    <div class="g2" style="gap:8px;margin-bottom:14px;font-family:'JetBrains Mono',monospace;font-size:11px">
      ${['Code|'+d.emp_code,'Period|'+d.period_name,'Name|'+d.name,'Dept|'+d.dept_name,'Designation|'+d.desig_title,'Grade|'+d.grade_name,'PAN|'+d.pan_number,'Bank|'+d.bank_name,'Days Present|'+d.days_present,'Days Absent|'+d.days_absent].map(x=>{const[l,v]=x.split('|');return `<div style="background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:7px 10px"><div style="font-size:8.5px;color:var(--t3);text-transform:uppercase;letter-spacing:1px">${l}</div><div style="margin-top:2px">${v||'—'}</div></div>`;}).join('')}
    </div>
    <div class="ps-grid">
      <div class="ps-col"><div class="ps-section-title">Earnings</div>${ps('Basic Salary',fmt(d.basic_salary))}${ps('HRA',fmt(d.hra))}${ps('Dearness Allowance',fmt(d.da))}${ps('Transport Allowance',fmt(d.transport_allow))}${ps('Other Allowances',fmt(d.other_allowances))}<div class="ps-total"><span>Gross</span><span class="gold">${fmt(d.gross_salary)}</span></div></div>
      <div class="ps-col"><div class="ps-section-title">Deductions</div>${ps('PF (Employee)',fmt(d.pf_employee))}${ps('ESI (Employee)',fmt(d.esi_employee))}${ps('Professional Tax',fmt(d.professional_tax))}${ps('Income Tax TDS',fmt(d.income_tax_tds))}${ps('Loan EMI',fmt(d.loan_deduction))}${ps('Other',fmt(d.other_deductions))}<div class="ps-total"><span>Total Deductions</span><span class="red">${fmt(d.total_deductions)}</span></div></div>
    </div>
    <div class="ps-net"><div class="ps-net-label">Net Salary (Take Home)</div><div class="ps-net-value">${fmt(d.net_salary)}</div><div class="small muted mt8">${badge(d.status)} · ${d.payment_date||'—'}</div></div>`;
}

async function doGenerate() {
  if(!currentPid) return;
  const r = await api(`/api/payroll/generate/${currentPid}`,'POST',{});
  toast(`Generated for ${(r.success||[]).length} employees`,'s');
  loadPeriods();
  loadRegister(currentPid, document.getElementById('selPeriodName').textContent);
}

async function doApprove() {
  if(!currentPid) return;
  const r = await api(`/api/payroll/approve/${currentPid}`,'POST',{});
  toast(`Approved ${r.approved||0} records`,'s');
  loadPeriods();
}

function openMarkPaid() {
  document.getElementById('payDate').value = new Date().toISOString().slice(0,10);
  openModal('markPaidModal');
}
async function confirmPaid() {
  const r = await api(`/api/payroll/mark-paid/${currentPid}`,'POST',{payment_date:document.getElementById('payDate').value});
  toast(`${r.paid||0} records marked Paid`,'s');
  closeModal('markPaidModal'); loadPeriods();
}

function exportCSV() {
  if(!currentPid) return;
  window.location.href = `/api/payroll/export/${currentPid}`;
  toast('CSV download started','i');
}

// ── ATTENDANCE ─────────────────────────────────────────────────
async function loadAtt() {
  const yr = document.getElementById('attYear').value;
  const mo = document.getElementById('attMonth').value;
  const rows = await api(`/api/attendance/summary?year=${yr}&month=${mo}`);
  document.getElementById('attCount').textContent = rows.length+' employees';
  const present=rows.reduce((a,r)=>a+(r.days_present||0),0);
  const absent =rows.reduce((a,r)=>a+(r.days_absent||0),0);
  const hours  =rows.reduce((a,r)=>a+(r.total_hours||0),0);
  document.getElementById('attStats').innerHTML = `
    <div class="stat green"><div class="stat-label">Total Present Days</div><div class="stat-value">${present}</div></div>
    <div class="stat red"><div class="stat-label">Total Absent Days</div><div class="stat-value">${absent}</div></div>
    <div class="stat blue"><div class="stat-label">Total Hours Worked</div><div class="stat-value">${hours.toFixed(0)}</div></div>
    <div class="stat gold"><div class="stat-label">Employees</div><div class="stat-value">${rows.length}</div></div>
  `;
  document.getElementById('attTable').innerHTML = rows.map(r=>`<tr>
    <td class="mono gold">${r.emp_code}</td>
    <td class="bold">${r.employee_name}</td>
    <td class="num green">${r.days_present}</td>
    <td class="num ${(r.days_absent||0)>3?'red':''}">${r.days_absent||0}</td>
    <td class="num blue">${r.leave_days||0}</td>
    <td class="num">${(r.total_hours||0).toFixed(1)}</td>
    <td class="num muted">${(r.avg_hours||0).toFixed(1)}</td>
  </tr>`).join('')||'<tr><td colspan="7"><div class="empty-state"><div>No attendance data</div></div></td></tr>';
}

async function saveAttendance() {
  const r = await api('/api/attendance/mark','POST',{
    emp_id:document.getElementById('attEmp').value,
    att_date:document.getElementById('attDate').value,
    status:document.getElementById('attStatus').value,
    check_in:document.getElementById('attIn').value,
    check_out:document.getElementById('attOut').value,
    hours_worked:document.getElementById('attHours').value,
  });
  if(r.success){toast('Attendance saved','s');closeModal('markAttModal');loadAtt();}
  else toast(r.error,'e');
}

// ── LEAVE ──────────────────────────────────────────────────────
let leaveFilter='all';
function switchLeaveTab(f, btn) {
  leaveFilter=f;
  document.querySelectorAll('#page-leave .tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('approveAllBtn').style.display = f==='pending'?'':'none';
  renderLeaves();
}

async function loadLeaves() {
  allLeaves = await api('/api/leave/requests');
  const P=allLeaves.filter(r=>r.status==='Pending').length;
  const A=allLeaves.filter(r=>r.status==='Approved').length;
  const R=allLeaves.filter(r=>r.status==='Rejected').length;
  document.getElementById('leaveStats').innerHTML = `
    <div class="stat gold"><div class="stat-label">Total</div><div class="stat-value">${allLeaves.length}</div></div>
    <div class="stat orange"><div class="stat-label">Pending</div><div class="stat-value">${P}</div></div>
    <div class="stat green"><div class="stat-label">Approved</div><div class="stat-value">${A}</div></div>
    <div class="stat red"><div class="stat-label">Rejected</div><div class="stat-value">${R}</div></div>
  `;
  renderLeaves();
}

function renderLeaves() {
  const rows = leaveFilter==='pending' ? allLeaves.filter(r=>r.status==='Pending') : allLeaves;
  document.getElementById('leaveCount').textContent = rows.length+' requests';
  document.getElementById('leaveTable').innerHTML = rows.map(r=>`<tr>
    <td><div class="bold" style="font-size:12.5px">${r.name}</div><div class="mono muted" style="font-size:10px">${r.emp_code}</div></td>
    <td><span class="badge bb">${r.leave_code}</span></td>
    <td class="mono small">${r.start_date}</td>
    <td class="mono small">${r.end_date}</td>
    <td class="num">${r.days_requested}</td>
    <td class="small muted" style="max-width:140px;overflow:hidden;text-overflow:ellipsis">${r.reason}</td>
    <td>${badge(r.status)}</td>
    <td>${r.status==='Pending'?`<div class="flex"><button class="btn btn-xs btn-ghost" onclick="actLeave(${r.leave_id},'Approved')">✓</button><button class="btn btn-xs btn-red" onclick="actLeave(${r.leave_id},'Rejected')">✗</button></div>`:'<span class="muted small">'+(r.approved_at?r.approved_at.slice(0,10):'—')+'</span>'}</td>
  </tr>`).join('')||'<tr><td colspan="8"><div class="empty-state"><div class="ei">✓</div><div>No requests</div></div></td></tr>';
}

async function actLeave(id, action) {
  await api(`/api/leave/requests/${id}/approve`,'PATCH',{action});
  toast(`Leave ${action}`,'s'); loadLeaves();
}
async function approveAllLeaves() {
  const pending = allLeaves.filter(r=>r.status==='Pending');
  await Promise.all(pending.map(r=>api(`/api/leave/requests/${r.leave_id}/approve`,'PATCH',{action:'Approved'})));
  toast(`${pending.length} requests approved`,'s'); loadLeaves();
}

function calcLvDays() {
  const f=new Date(document.getElementById('lvFrom').value), t=new Date(document.getElementById('lvTo').value);
  if(f&&t&&t>=f) document.getElementById('lvDays').value=Math.round((t-f)/86400000)+1;
}
async function submitLeave() {
  const r = await api('/api/leave/requests','POST',{
    emp_id:document.getElementById('lvEmp').value,
    leave_type_id:document.getElementById('lvType').value,
    start_date:document.getElementById('lvFrom').value,
    end_date:document.getElementById('lvTo').value,
    days_requested:document.getElementById('lvDays').value,
    reason:document.getElementById('lvReason').value,
  });
  if(r.success){toast('Leave applied','s');closeModal('applyLeaveModal');loadLeaves();}
  else toast(r.error,'e');
}

// ── LOANS ──────────────────────────────────────────────────────
async function loadLoans() {
  const s = document.getElementById('loanStatus').value;
  const rows = await api('/api/loans'+(s?'?status='+s:''));
  document.getElementById('loanCount').textContent = rows.length+' loans';
  const tot=rows.reduce((a,r)=>a+(r.loan_amount||0),0);
  const out=rows.reduce((a,r)=>a+(r.outstanding||0),0);
  const act=rows.filter(r=>r.status==='Active').length;
  document.getElementById('loanStats').innerHTML = `
    <div class="stat red"><div class="stat-label">Outstanding</div><div class="stat-value" style="font-size:17px">${fmtK(out)}</div></div>
    <div class="stat gold"><div class="stat-label">Sanctioned</div><div class="stat-value" style="font-size:17px">${fmtK(tot)}</div></div>
    <div class="stat green"><div class="stat-label">Active Loans</div><div class="stat-value">${act}</div></div>
    <div class="stat blue"><div class="stat-label">Total Loans</div><div class="stat-value">${rows.length}</div></div>
  `;
  document.getElementById('loanTable').innerHTML = rows.map(r=>{
    const pct=Math.round((r.emis_paid||0)/(r.total_emis||1)*100);
    return `<tr>
      <td class="mono gold">${r.emp_code}</td>
      <td class="bold">${r.name}</td>
      <td class="small">${r.purpose}</td>
      <td class="num">${fmt(r.loan_amount)}</td>
      <td class="num">${fmt(r.emi_amount)}</td>
      <td style="min-width:120px">
        <div style="font-size:10px;font-family:'JetBrains Mono',monospace;margin-bottom:3px"><span class="green">${r.emis_paid}</span><span class="muted">/${r.total_emis} EMIs</span></div>
        <div style="height:4px;background:var(--bg4);border-radius:2px"><div style="height:100%;background:var(--green);border-radius:2px;width:${pct}%"></div></div>
      </td>
      <td class="num ${(r.outstanding||0)>0?'red':''}">${fmt(r.outstanding)}</td>
      <td>${badge(r.status)}</td>
    </tr>`;
  }).join('')||'<tr><td colspan="8"><div class="empty-state"><div>No loans</div></div></td></tr>';
}

function calcEMI(){const a=parseFloat(document.getElementById('lnAmt').value)||0,n=parseInt(document.getElementById('lnEmis').value)||1;document.getElementById('lnEMI').value=(a/n).toFixed(2);}
async function saveLoan() {
  const r = await api('/api/loans','POST',{emp_id:document.getElementById('lnEmp').value,loan_amount:document.getElementById('lnAmt').value,loan_date:document.getElementById('lnDate').value,emi_amount:document.getElementById('lnEMI').value,total_emis:document.getElementById('lnEmis').value,purpose:document.getElementById('lnPurpose').value});
  if(r.success){toast('Loan created','s');closeModal('addLoanModal');loadLoans();}else toast(r.error,'e');
}

// ── TAX CALCULATOR ─────────────────────────────────────────────
async function initTax() {
  const emps = await api('/api/employees?status=Active');
  const sel  = document.getElementById('taxEmp');
  if(!sel.options.length||sel.options.length<2) emps.forEach(e=>sel.innerHTML+=`<option value="${e.basic_salary}">${e.emp_code} — ${e.full_name}</option>`);
}
function taxAutoFill(){const s=document.getElementById('taxEmp');if(s.value){const b=parseFloat(s.value);document.getElementById('taxGross').value=Math.round(b*1.52+1200);calcTax();}}

async function calcTax() {
  const gross = parseFloat(document.getElementById('taxGross').value)||0;
  if(!gross) return;
  const regime = document.querySelector('input[name="regime"]:checked').value;
  const [rn, ro] = await Promise.all([
    api('/api/tax/calculate','POST',{gross_monthly:gross,regime:'new'}),
    api('/api/tax/calculate','POST',{gross_monthly:gross,regime:'old'}),
  ]);
  const d = regime==='new'?rn:ro;
  document.getElementById('taxBadge').textContent = fmt(gross)+'/mo';
  const ri=(l,v,c='')=>`<div style="background:var(--bg3);border:1px solid var(--border);border-radius:7px;padding:9px 12px"><div style="font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:1px;font-family:'JetBrains Mono',monospace;margin-bottom:3px">${l}</div><div class="mono bold ${c}" style="font-size:14px">${v}</div></div>`;
  document.getElementById('taxResult').innerHTML = `
    <div class="g2" style="gap:10px;margin-bottom:14px">
      ${ri('Annual Gross',fmt(d.gross_annual),'gold')}${ri('Tax Before Cess',fmt(d.tax_before_cess),'red')}
      ${ri('Health & Ed Cess (4%)',fmt(d.cess_4pct),'orange')}${ri('Total Annual Tax',fmt(d.total_annual_tax),'red bold')}
      ${ri('Monthly TDS',fmt(d.monthly_tds),'red')}${ri('Effective Rate',d.effective_rate+'%',d.effective_rate>20?'red':'green')}
    </div>
    <div style="background:linear-gradient(135deg,rgba(46,204,113,.1),rgba(46,204,113,.02));border:1px solid rgba(46,204,113,.2);border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:2px;font-family:'JetBrains Mono',monospace">Monthly Take-Home (est.)</div>
      <div class="mono bold green" style="font-size:24px;margin-top:6px">${fmt(gross-d.monthly_tds-Math.round(Math.min(gross*.52,15000)*.12)-(gross>10000?200:0))}</div>
    </div>`;

  // Slab bars
  document.getElementById('slabCard').style.display='';
  const maxT=Math.max(...(d.slab_breakdown||[]).map(s=>s.tax),1);
  document.getElementById('slabBars').innerHTML=(d.slab_breakdown||[]).filter(s=>s.tax>0).map(s=>`
    <div class="bar-row">
      <div class="bar-lbl">${s.range}</div>
      <div class="mono muted" style="width:28px;text-align:right;font-size:10px;flex-shrink:0">${s.rate}%</div>
      <div class="bar-track" style="margin:0 8px"><div class="bar-fill" style="width:${(s.tax/maxT*100).toFixed(1)}%;background:var(--red)"></div></div>
      <div class="bar-val">${fmt(s.tax)}</div>
    </div>`).join('');

  // Regime compare
  document.getElementById('compareCard').style.display='';
  const save=Math.abs(rn.total_annual_tax-ro.total_annual_tax);
  const better=rn.total_annual_tax<=ro.total_annual_tax?'New Regime':'Old Regime';
  document.getElementById('compareBody').innerHTML=`
    <div class="g2" style="gap:10px;margin-bottom:12px">
      <div style="padding:12px;background:var(--bg3);border:2px solid ${regime==='new'?'var(--gold)':'var(--border)'};border-radius:8px;text-align:center"><div class="small muted">NEW REGIME</div><div class="mono bold" style="font-size:18px;margin:6px 0">${fmt(rn.total_annual_tax)}</div><div class="small muted">${rn.effective_rate}% effective</div></div>
      <div style="padding:12px;background:var(--bg3);border:2px solid ${regime==='old'?'var(--gold)':'var(--border)'};border-radius:8px;text-align:center"><div class="small muted">OLD REGIME</div><div class="mono bold" style="font-size:18px;margin:6px 0">${fmt(ro.total_annual_tax)}</div><div class="small muted">${ro.effective_rate}% effective</div></div>
    </div>
    <div style="padding:10px;background:rgba(46,204,113,.08);border:1px solid rgba(46,204,113,.2);border-radius:7px;text-align:center;font-size:12px"><b>${better}</b> saves <b class="green">${fmt(save)}/yr</b> (${fmt(save/12)}/mo)</div>`;
}

// ── REPORTS ────────────────────────────────────────────────────
function switchReportTab(t, btn) {
  document.querySelectorAll('#rp-ytd,#rp-dept,#rp-audit').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('#reportTabs .tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('rp-'+t).classList.add('active');
  btn.classList.add('active');
  if(t==='dept'&&!document.getElementById('deptPeriod').value) loadPeriods();
  if(t==='audit') loadAudit();
}

async function loadYTD() {
  const yr = document.getElementById('ytdYear').value;
  ytdData = await api(`/api/reports/ytd/${yr}`);
  document.getElementById('ytdCount').textContent = ytdData.length+' employees';
  let tg=0,tt=0,tn=0;
  document.getElementById('ytdTable').innerHTML = ytdData.map(r=>{tg+=r.ytd_gross||0;tt+=r.ytd_tds||0;tn+=r.ytd_net||0;return`<tr>
    <td class="mono gold">${r.emp_code}</td>
    <td class="bold">${r.employee_name}</td>
    <td class="num mono">${r.months_processed}</td>
    <td class="num">${fmt(r.ytd_gross)}</td>
    <td class="num red">${fmt(r.ytd_tds)}</td>
    <td class="num muted">${fmt(r.ytd_pf)}</td>
    <td class="num green bold">${fmt(r.ytd_net)}</td>
  </tr>`}).join('')||'<tr><td colspan="7"><div class="empty-state"><div>No data</div></div></td></tr>';
  document.getElementById('ytdTotals').innerHTML=`Gross: <b class="gold">${fmtK(tg)}</b>&nbsp;&nbsp;TDS: <b class="red">${fmtK(tt)}</b>&nbsp;&nbsp;Net: <b class="green">${fmtK(tn)}</b>`;
}

function exportYTD(){if(!ytdData.length){toast('Load data first','e');return;}const hdr=Object.keys(ytdData[0]).join(',');const rows=ytdData.map(r=>Object.values(r).join(',')).join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([hdr+'\n'+rows],{type:'text/csv'}));a.download='ytd_salary_'+document.getElementById('ytdYear').value+'.csv';a.click();toast('CSV exported','s');}

async function loadDeptSummary() {
  const pid = document.getElementById('deptPeriod').value;
  if(!pid) return;
  const rows = await api(`/api/reports/dept-summary/${pid}`);
  document.getElementById('deptTable').innerHTML = rows.map(r=>`<tr>
    <td class="bold">${r.dept_name}</td>
    <td class="num">${r.headcount}</td>
    <td class="num">${fmt(r.total_gross)}</td>
    <td class="num green bold">${fmt(r.total_net)}</td>
    <td class="num muted">${fmt(r.avg_net)}</td>
    <td class="num muted">${fmt(r.total_pf)}</td>
    <td class="num red">${fmt(r.total_tds)}</td>
  </tr>`).join('');
  const max=Math.max(...rows.map(r=>r.total_net),1);
  const colors=['#f5a623','#3498db','#2ecc71','#1abc9c','#9b59b6','#e67e22','#e74c3c','#34495e','#16a085','#8e44ad'];
  document.getElementById('deptBarsReport').innerHTML=rows.map((r,i)=>`
    <div class="bar-row">
      <div class="bar-lbl">${r.dept_name}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(r.total_net/max*100).toFixed(1)}%;background:${colors[i%colors.length]}"></div></div>
      <div class="bar-val">${fmtK(r.total_net)} <span class="muted">(${r.headcount})</span></div>
    </div>`).join('');
}

async function loadAudit() {
  const tbl=document.getElementById('auditTable').value;
  const lim=document.getElementById('auditLimit').value;
  const rows=await api(`/api/reports/audit?table=${tbl}&limit=${lim}`);
  document.getElementById('auditCount').textContent=rows.length+' entries';
  const ab={INSERT:'bg',UPDATE:'bgold',DELETE:'br'};
  document.getElementById('auditTable2').innerHTML=rows.map((r,i)=>`<tr>
    <td class="mono muted">${i+1}</td>
    <td class="mono blue">${r.table_name}</td>
    <td class="mono">${r.record_id}</td>
    <td><span class="badge ${ab[r.action]||'bgray'}">${r.action}</span></td>
    <td class="mono muted small">${r.performed_at}</td>
    <td class="muted small" style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${r.old_data||'—'}</td>
  </tr>`).join('')||'<tr><td colspan="6"><div class="empty-state"><div>No audit entries</div></div></td></tr>';
}

// ── SALARY REVISIONS ──────────────────────────────────────────
async function loadRevisions() {
  const rows = await api('/api/reports/salary-revisions');
  document.getElementById('revCount').textContent = rows.length+' revisions';
  const top=rows.slice().sort((a,b)=>b.pct_hike-a.pct_hike).slice(0,10);
  const max=top[0]?.pct_hike||1;
  document.getElementById('hikeBars').innerHTML=top.map(r=>{
    const c=r.pct_hike>=15?'#2ecc71':r.pct_hike>=10?'#f5a623':r.pct_hike>=5?'#3498db':'#8a9ab8';
    return`<div class="bar-row"><div class="bar-lbl">${r.name}</div><div class="bar-track"><div class="bar-fill" style="width:${(r.pct_hike/max*100).toFixed(1)}%;background:${c}"></div></div><div class="bar-val" style="color:${c}">${r.pct_hike}%</div></div>`;
  }).join('');
  document.getElementById('revTable').innerHTML=rows.map(r=>{
    const c=r.pct_hike>15?'green':r.pct_hike>5?'gold':'muted';
    return`<tr>
      <td class="mono gold">${r.emp_code}</td>
      <td class="bold">${r.name}</td>
      <td class="muted small">${r.dept_name}</td>
      <td class="num">${fmt(r.old_basic)}</td>
      <td class="num green">${fmt(r.new_basic)}</td>
      <td class="num ${c} bold">${r.pct_hike}%</td>
      <td class="mono muted">${r.effective_date}</td>
      <td class="small">${r.reason}</td>
    </tr>`}).join('');
}

async function loadEmpBasic(){const s=document.getElementById('rvEmp');const o=s.options[s.selectedIndex];document.getElementById('rvOld').value=o?.dataset.basic||'';calcHike();}
function calcHike(){const o=parseFloat(document.getElementById('rvOld').value)||0,n=parseFloat(document.getElementById('rvNew').value)||0;if(o&&n)document.getElementById('rvHike').value=((n-o)/o*100).toFixed(2)+'%';else document.getElementById('rvHike').value='';}
async function saveRevision(){
  const eid=document.getElementById('rvEmp').value,nb=parseFloat(document.getElementById('rvNew').value),ob=parseFloat(document.getElementById('rvOld').value);
  if(!eid||!nb){toast('Fill all fields','e');return;}
  const r=await api('/api/reports/salary-revisions','POST',{emp_id:eid,old_basic:ob,new_basic:nb,effective_date:document.getElementById('rvDate').value,reason:document.getElementById('rvReason').value});
  if(r.success){toast('Revision saved','s');closeModal('addRevModal');loadRevisions();}else toast(r.error,'e');
}

// ── MODAL HELPERS ──────────────────────────────────────────────
function openModal(id){document.getElementById(id).classList.add('open');}
function closeModal(id){document.getElementById(id).classList.remove('open');}
document.addEventListener('click',e=>{if(e.target.classList.contains('overlay'))e.target.classList.remove('open');});

// ── INIT ALL DROPDOWNS ─────────────────────────────────────────
async function initDropdowns() {
  const [emps, types] = await Promise.all([
    api('/api/employees?status=Active'),
    api('/api/leave/types'),
  ]);
  const today = new Date().toISOString().slice(0,10);
  ['attEmp','lvEmp','lnEmp'].forEach(id=>{
    const s=document.getElementById(id);
    if(s&&!s.options.length) emps.forEach(e=>s.innerHTML+=`<option value="${e.emp_id}">${e.emp_code} — ${e.full_name}</option>`);
  });
  ['attDate','lvFrom','lvTo','lnDate','rvDate'].forEach(id=>{const el=document.getElementById(id);if(el)el.value=today;});
  const lt=document.getElementById('lvType');
  if(lt&&!lt.options.length) types.forEach(t=>lt.innerHTML+=`<option value="${t.leave_type_id}">${t.leave_name} (${t.leave_code})</option>`);

  // Revision employee dropdown with salary data
  const rv=document.getElementById('rvEmp');
  if(rv&&!rv.options.length) emps.forEach(e=>rv.innerHTML+=`<option value="${e.emp_id}" data-basic="${e.basic_salary}">${e.emp_code} — ${e.full_name}</option>`);
}

// ── BOOT ───────────────────────────────────────────────────────
(async()=>{
  await initDropdowns();
  loadDashboard();
})();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)

# ══════════════════════════════════════════════════════════════
#  ALL API ROUTES (same as before)
# ══════════════════════════════════════════════════════════════
@app.route("/api/stats")
def api_stats():
    latest = q("SELECT period_id,period_name FROM payroll_periods WHERE status='Paid' ORDER BY year DESC,month DESC LIMIT 1")
    pid    = latest[0]["period_id"] if latest else 24
    pname  = latest[0]["period_name"] if latest else "March 2026"
    pay    = q(f"SELECT ROUND(SUM(gross_salary),2) g,ROUND(SUM(net_salary),2) n,COUNT(*) c FROM payroll_records WHERE period_id={pid} AND status='Paid'")
    pay    = pay[0] if pay else {"g":0,"n":0,"c":0}
    return jsonify({
        "emp_active":   (q("SELECT COUNT(*) c FROM employees WHERE status='Active'") or [{"c":0}])[0]["c"],
        "emp_total":    (q("SELECT COUNT(*) c FROM employees") or [{"c":0}])[0]["c"],
        "dept_count":   (q("SELECT COUNT(*) c FROM departments WHERE is_active=1") or [{"c":0}])[0]["c"],
        "period_name":  pname,
        "gross_payroll":float(pay["g"] or 0),
        "net_payroll":  float(pay["n"] or 0),
        "payroll_headcount": pay["c"] or 0,
        "loan_outstanding": float((q("SELECT ROUND(SUM(outstanding),2) t FROM employee_loans WHERE status='Active'") or [{"t":0}])[0]["t"] or 0),
        "leave_pending":(q("SELECT COUNT(*) c FROM leave_requests WHERE status='Pending'") or [{"c":0}])[0]["c"],
        "attendance_today": 0,
        "dept_costs":   q(f"SELECT d.dept_name,ROUND(SUM(pr.net_salary),2) net,COUNT(*) hc FROM payroll_records pr JOIN employees e ON pr.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id WHERE pr.period_id={pid} GROUP BY d.dept_id ORDER BY net DESC LIMIT 8"),
        "monthly_trend":q("SELECT pp.period_name,pp.month,pp.year,ROUND(SUM(pr.gross_salary)/1000,1) gross_k,ROUND(SUM(pr.net_salary)/1000,1) net_k FROM payroll_records pr JOIN payroll_periods pp ON pr.period_id=pp.period_id WHERE pr.status='Paid' GROUP BY pp.period_id ORDER BY pp.year,pp.month LIMIT 12"),
        "top_earners":  q(f"SELECT e.first_name||' '||e.last_name name,d.dept_name dept,pr.net_salary net FROM payroll_records pr JOIN employees e ON pr.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id WHERE pr.period_id={pid} ORDER BY net DESC LIMIT 5"),
        "gender_split": q("SELECT gender,COUNT(*) c FROM employees WHERE status='Active' GROUP BY gender"),
    })

@app.route("/api/employees", methods=["GET","POST"])
def api_employees():
    if request.method == "POST":
        d = request.json or {}
        try:
            eid = ex("""INSERT INTO employees(emp_code,first_name,last_name,gender,dob,email,phone,address,city,state,pan_number,aadhaar_last4,bank_account,bank_name,ifsc_code,dept_id,desig_id,grade_id,basic_salary,date_joined,employment_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d.get("emp_code",""),d.get("first_name",""),d.get("last_name",""),d.get("gender","Male"),d.get("dob","1990-01-01"),d.get("email",""),d.get("phone",""),d.get("address",""),d.get("city",""),d.get("state",""),d.get("pan_number",""),d.get("aadhaar_last4",""),d.get("bank_account",""),d.get("bank_name",""),d.get("ifsc_code",""),int(d.get("dept_id",1)),int(d.get("desig_id",1)),int(d.get("grade_id",1)),float(d.get("basic_salary",0)),d.get("date_joined",datetime.now().strftime("%Y-%m-%d")),d.get("employment_type","Full-Time")))
            return jsonify({"success":True,"emp_id":eid})
        except Exception as e:
            return jsonify({"success":False,"error":str(e)}),400
    srch=request.args.get("q",""); dept=request.args.get("dept",""); status=request.args.get("status","")
    where,params=["1=1"],[]
    if srch: where.append("(e.first_name||' '||e.last_name LIKE ? OR e.emp_code LIKE ? OR e.email LIKE ?)"); params+=[f"%{srch}%"]*3
    if dept: where.append("e.dept_id=?"); params.append(dept)
    if status: where.append("e.status=?"); params.append(status)
    return jsonify(q(f"SELECT e.emp_id,e.emp_code,e.first_name||' '||e.last_name AS full_name,e.gender,e.email,e.phone,e.status,e.employment_type,e.basic_salary,e.date_joined,d.dept_name,ds.desig_title,sg.grade_name,sg.grade_code FROM employees e JOIN departments d ON e.dept_id=d.dept_id JOIN designations ds ON e.desig_id=ds.desig_id JOIN salary_grades sg ON e.grade_id=sg.grade_id WHERE {' AND '.join(where)} ORDER BY e.emp_code",params))

@app.route("/api/employees/<int:eid>", methods=["GET"])
def api_emp_detail(eid):
    r = q("SELECT * FROM vw_employee_profile WHERE emp_id=?", (eid,))
    if not r: return jsonify({"error":"Not found"}),404
    emp = r[0]
    emp["payslips"]  = q("SELECT pp.period_name,pr.gross_salary,pr.net_salary,pr.days_present,pr.days_absent,pr.status,pr.payment_date FROM payroll_records pr JOIN payroll_periods pp ON pr.period_id=pp.period_id WHERE pr.emp_id=? ORDER BY pp.year DESC,pp.month DESC LIMIT 6",(eid,))
    emp["loans"]     = q("SELECT l.loan_id,l.loan_amount,l.emi_amount,l.total_emis,l.emis_paid,l.outstanding,l.purpose,l.status FROM employee_loans l WHERE l.emp_id=? AND l.status='Active'",(eid,))
    emp["revisions"] = q("SELECT old_basic,new_basic,effective_date,reason FROM salary_revisions WHERE emp_id=? ORDER BY effective_date DESC LIMIT 5",(eid,))
    return jsonify(emp)

@app.route("/api/employees/<int:eid>/status", methods=["PATCH"])
def api_emp_status(eid):
    ex("UPDATE employees SET status=? WHERE emp_id=?",((request.json or {}).get("status","Active"),eid))
    return jsonify({"success":True})

@app.route("/api/departments")
def api_depts():
    return jsonify(q("SELECT dept_id,dept_name,dept_code,location FROM departments WHERE is_active=1 ORDER BY dept_name"))

@app.route("/api/designations")
def api_desigs():
    dept=request.args.get("dept_id")
    return jsonify(q("SELECT desig_id,desig_title FROM designations WHERE dept_id=? AND is_active=1",(dept,)) if dept else q("SELECT desig_id,desig_title,dept_id FROM designations WHERE is_active=1 ORDER BY desig_title"))

@app.route("/api/grades")
def api_grades():
    return jsonify(q("SELECT grade_id,grade_code,grade_name,basic_min,basic_max FROM salary_grades ORDER BY grade_id"))

@app.route("/api/payroll/periods")
def api_periods():
    return jsonify(q("SELECT p.period_id,p.period_name,p.month,p.year,p.working_days,p.status,COUNT(pr.payroll_id) records,ROUND(SUM(pr.net_salary),2) total_net FROM payroll_periods p LEFT JOIN payroll_records pr ON p.period_id=pr.period_id GROUP BY p.period_id ORDER BY p.year DESC,p.month DESC"))

@app.route("/api/payroll/register/<int:pid>")
def api_register(pid):
    return jsonify(q("SELECT pr.payroll_id,e.emp_id,e.emp_code,e.first_name||' '||e.last_name name,d.dept_name,ds.desig_title,pr.days_present,pr.days_absent,pr.days_leave,pr.basic_salary,pr.hra,pr.da,pr.transport_allow,pr.gross_salary,pr.pf_employee,pr.esi_employee,pr.professional_tax,pr.income_tax_tds,pr.loan_deduction,pr.total_deductions,pr.net_salary,pr.status,pr.payment_date FROM payroll_records pr JOIN employees e ON pr.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id JOIN designations ds ON e.desig_id=ds.desig_id WHERE pr.period_id=? ORDER BY d.dept_name,name",(pid,)))

@app.route("/api/payroll/payslip/<int:eid>/<int:pid>")
def api_payslip(eid,pid):
    rows=q("SELECT pr.*,pp.period_name,pp.month,pp.year,e.emp_code,e.first_name||' '||e.last_name name,e.pan_number,e.bank_name,e.bank_account,d.dept_name,ds.desig_title,sg.grade_name FROM payroll_records pr JOIN employees e ON pr.emp_id=e.emp_id JOIN payroll_periods pp ON pr.period_id=pp.period_id JOIN departments d ON e.dept_id=d.dept_id JOIN designations ds ON e.desig_id=ds.desig_id JOIN salary_grades sg ON e.grade_id=sg.grade_id WHERE pr.emp_id=? AND pr.period_id=?",(eid,pid))
    return jsonify(rows[0] if rows else {})

@app.route("/api/payroll/generate/<int:pid>", methods=["POST"])
def api_generate(pid):
    period=q("SELECT * FROM payroll_periods WHERE period_id=?",(pid,))
    if not period: return jsonify({"error":"Period not found"}),404
    p=period[0]; wdays=p["working_days"]; success=[]; failed=[]
    for emp in q("SELECT emp_id,grade_id,basic_salary FROM employees WHERE status='Active'"):
        try:
            eid=emp["emp_id"]; basic=float(emp["basic_salary"])
            g=(q("SELECT hra_pct,da_pct,ta_flat FROM salary_grades WHERE grade_id=?",(emp["grade_id"],)) or [{"hra_pct":35,"da_pct":17,"ta_flat":1200}])[0]
            gross=round(basic*(1+g["hra_pct"]/100+g["da_pct"]/100)+g["ta_flat"],2)
            pf=round(min(basic,15000)*.12,2); esi=round(gross*.0075,2) if gross<=21000 else 0
            pt=200 if gross>10000 else 0; tds=round(max(gross*12-400000,0)*.05/12,2)
            td=round(pf+esi+pt+tds,2); net=round(gross-td,2)
            exists=q("SELECT payroll_id FROM payroll_records WHERE emp_id=? AND period_id=?",(eid,pid))
            if exists:
                ex("UPDATE payroll_records SET basic_salary=?,hra=?,da=?,transport_allow=?,gross_salary=?,pf_employee=?,pf_employer=?,esi_employee=?,esi_employer=?,professional_tax=?,income_tax_tds=?,total_deductions=?,net_salary=?,working_days=?,days_present=?,status='Draft',updated_at=datetime('now') WHERE emp_id=? AND period_id=?",(basic,round(basic*g["hra_pct"]/100,2),round(basic*g["da_pct"]/100,2),g["ta_flat"],gross,pf,pf,esi,round(gross*.0325,2) if gross<=21000 else 0,pt,tds,td,net,wdays,wdays,eid,pid))
            else:
                ex("INSERT INTO payroll_records(emp_id,period_id,total_days,working_days,days_present,days_absent,days_leave,basic_salary,hra,da,transport_allow,other_allowances,gross_salary,pf_employee,pf_employer,esi_employee,esi_employer,professional_tax,income_tax_tds,loan_deduction,other_deductions,total_deductions,net_salary,status) VALUES(?,?,?,?,?,0,0,?,?,?,?,0,?,?,?,?,?,?,?,0,0,?,?)",(eid,pid,wdays+5,wdays,wdays,basic,round(basic*g["hra_pct"]/100,2),round(basic*g["da_pct"]/100,2),g["ta_flat"],gross,pf,pf,esi,round(gross*.0325,2) if gross<=21000 else 0,pt,tds,td,net,"Draft"))
            success.append(eid)
        except Exception as e: failed.append({"emp_id":emp["emp_id"],"error":str(e)})
    return jsonify({"success":success,"failed":failed,"total":len(success)+len(failed)})

@app.route("/api/payroll/approve/<int:pid>", methods=["POST"])
def api_approve(pid):
    conn=db(); conn.execute("UPDATE payroll_records SET status='Approved' WHERE period_id=? AND status='Draft'",(pid,)); n=conn.total_changes; conn.commit(); conn.close()
    return jsonify({"approved":n})

@app.route("/api/payroll/mark-paid/<int:pid>", methods=["POST"])
def api_paid(pid):
    pd=(request.json or {}).get("payment_date",datetime.now().strftime("%Y-%m-%d"))
    conn=db(); conn.execute("UPDATE payroll_records SET status='Paid',payment_date=? WHERE period_id=? AND status='Approved'",(pd,pid)); n=conn.total_changes; conn.execute("UPDATE payroll_periods SET status='Paid',processed_at=datetime('now') WHERE period_id=?",(pid,)); conn.commit(); conn.close()
    return jsonify({"paid":n})

@app.route("/api/payroll/export/<int:pid>")
def api_export(pid):
    rows=q("SELECT e.emp_code,e.first_name||' '||e.last_name name,d.dept_name,pr.basic_salary,pr.gross_salary,pr.pf_employee,pr.income_tax_tds,pr.total_deductions,pr.net_salary,pr.status FROM payroll_records pr JOIN employees e ON pr.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id WHERE pr.period_id=? ORDER BY d.dept_name",(pid,))
    buf=io.StringIO()
    if rows: w=csv.DictWriter(buf,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode()),mimetype="text/csv",as_attachment=True,download_name=f"payroll_{pid}.csv")

@app.route("/api/attendance/summary")
def api_att_summary():
    return jsonify(q("SELECT * FROM vw_attendance_summary WHERE year=? AND month=? ORDER BY days_absent DESC",(request.args.get("year","2026"),request.args.get("month","03").zfill(2))))

@app.route("/api/attendance/mark", methods=["POST"])
def api_att_mark():
    d=request.json or {}
    try:
        ex("INSERT OR REPLACE INTO attendance(emp_id,att_date,check_in,check_out,hours_worked,status,remarks) VALUES(?,?,?,?,?,?,?)",(d.get("emp_id"),d.get("att_date"),d.get("check_in"),d.get("check_out"),float(d.get("hours_worked",8)),d.get("status","Present"),d.get("remarks","")))
        return jsonify({"success":True})
    except Exception as e: return jsonify({"success":False,"error":str(e)}),400

@app.route("/api/leave/types")
def api_leave_types():
    return jsonify(q("SELECT leave_type_id,leave_code,leave_name,max_days_year,is_paid FROM leave_types ORDER BY leave_name"))

@app.route("/api/leave/requests", methods=["GET","POST"])
def api_leave():
    if request.method=="POST":
        d=request.json or {}
        try:
            lid=ex("INSERT INTO leave_requests(emp_id,leave_type_id,start_date,end_date,days_requested,reason,status) VALUES(?,?,?,?,?,?,'Pending')",(d.get("emp_id"),d.get("leave_type_id"),d.get("start_date"),d.get("end_date"),float(d.get("days_requested",1)),d.get("reason","")))
            return jsonify({"success":True,"leave_id":lid})
        except Exception as e: return jsonify({"success":False,"error":str(e)}),400
    return jsonify(q("SELECT lr.leave_id,e.emp_code,e.first_name||' '||e.last_name name,d.dept_name,lt.leave_name,lt.leave_code,lr.start_date,lr.end_date,lr.days_requested,lr.reason,lr.status,lr.approved_at FROM leave_requests lr JOIN employees e ON lr.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id JOIN leave_types lt ON lr.leave_type_id=lt.leave_type_id ORDER BY lr.created_at DESC"))

@app.route("/api/leave/requests/<int:lid>/approve", methods=["PATCH"])
def api_leave_approve(lid):
    ex("UPDATE leave_requests SET status=?,approved_at=datetime('now') WHERE leave_id=?",((request.json or {}).get("action","Approved"),lid))
    return jsonify({"success":True})

@app.route("/api/loans", methods=["GET","POST"])
def api_loans():
    if request.method=="POST":
        d=request.json or {}
        try:
            lid=ex("INSERT INTO employee_loans(emp_id,loan_amount,loan_date,emi_amount,total_emis,outstanding,purpose) VALUES(?,?,?,?,?,?,?)",(d.get("emp_id"),float(d.get("loan_amount",0)),d.get("loan_date"),float(d.get("emi_amount",0)),int(d.get("total_emis",12)),float(d.get("loan_amount",0)),d.get("purpose","")))
            return jsonify({"success":True,"loan_id":lid})
        except Exception as e: return jsonify({"success":False,"error":str(e)}),400
    s=request.args.get("status","")
    sql="SELECT l.loan_id,l.emp_id,e.emp_code,e.first_name||' '||e.last_name name,d.dept_name,l.loan_amount,l.loan_date,l.emi_amount,l.total_emis,l.emis_paid,(l.total_emis-l.emis_paid) emis_rem,l.outstanding,l.purpose,l.status FROM employee_loans l JOIN employees e ON l.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id"
    params=()
    if s: sql+=" WHERE l.status=?"; params=(s,)
    return jsonify(q(sql+" ORDER BY l.outstanding DESC",params))

@app.route("/api/tax/calculate", methods=["POST"])
def api_tax():
    d=request.json or {}; gross=float(d.get("gross_monthly",0)); annual=gross*12; regime=d.get("regime","new")
    if regime=="new": slabs=[(400000,0),(800000,5),(1200000,10),(1600000,15),(2000000,20),(2400000,25),(float('inf'),30)]; rl=1200000
    else:             slabs=[(250000,0),(500000,5),(1000000,20),(float('inf'),30)]; rl=500000
    tax=0; prev=0; bd=[]
    for upper,rate in slabs:
        if annual<=prev: break
        taxable=min(annual,upper)-prev; st=taxable*rate/100; tax+=st
        bd.append({"range":f"₹{int(prev//100000)}L–₹{min(int(annual),int(upper))//100000}L","rate":rate,"tax":round(st,2)})
        prev=min(annual,upper)
        if annual<=upper: break
    if annual<=rl: tax=max(tax-60000,0)
    cess=round(tax*.04,2); total=round(tax+cess,2)
    return jsonify({"gross_monthly":gross,"gross_annual":annual,"regime":regime,"tax_before_cess":round(tax,2),"cess_4pct":cess,"total_annual_tax":total,"monthly_tds":round(total/12,2),"effective_rate":round(total/annual*100,2) if annual else 0,"slab_breakdown":bd})

@app.route("/api/reports/ytd/<int:year>")
def api_ytd(year):
    return jsonify(q("SELECT * FROM vw_ytd_salary WHERE year=? ORDER BY ytd_gross DESC",(year,)))

@app.route("/api/reports/dept-summary/<int:pid>")
def api_dept_sum(pid):
    return jsonify(q("SELECT d.dept_name,COUNT(pr.payroll_id) headcount,ROUND(SUM(pr.gross_salary),2) total_gross,ROUND(SUM(pr.net_salary),2) total_net,ROUND(AVG(pr.net_salary),2) avg_net,ROUND(SUM(pr.pf_employee),2) total_pf,ROUND(SUM(pr.income_tax_tds),2) total_tds FROM payroll_records pr JOIN employees e ON pr.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id WHERE pr.period_id=? GROUP BY d.dept_id ORDER BY total_gross DESC",(pid,)))

@app.route("/api/reports/salary-revisions", methods=["GET","POST"])
def api_revisions():
    if request.method=="POST":
        d=request.json or {}
        try:
            rid=ex("INSERT INTO salary_revisions(emp_id,old_basic,new_basic,effective_date,reason) VALUES(?,?,?,?,?)",(d.get("emp_id"),float(d.get("old_basic",0)),float(d.get("new_basic",0)),d.get("effective_date"),d.get("reason","")))
            ex("UPDATE employees SET basic_salary=?,updated_at=datetime('now') WHERE emp_id=?",(float(d.get("new_basic",0)),d.get("emp_id")))
            return jsonify({"success":True,"revision_id":rid})
        except Exception as e: return jsonify({"success":False,"error":str(e)}),400
    return jsonify(q("SELECT sr.revision_id,e.emp_code,e.first_name||' '||e.last_name name,d.dept_name,sr.old_basic,sr.new_basic,ROUND((sr.new_basic-sr.old_basic)*100.0/sr.old_basic,1) pct_hike,sr.effective_date,sr.reason FROM salary_revisions sr JOIN employees e ON sr.emp_id=e.emp_id JOIN departments d ON e.dept_id=d.dept_id ORDER BY sr.effective_date DESC"))

@app.route("/api/reports/audit")
def api_audit():
    tbl=request.args.get("table",""); lim=int(request.args.get("limit",50))
    return jsonify(q("SELECT * FROM audit_logs WHERE table_name=? ORDER BY performed_at DESC LIMIT ?",(tbl,lim)) if tbl else q("SELECT * FROM audit_logs ORDER BY performed_at DESC LIMIT ?",(lim,)))

if __name__ == "__main__":
    print()
    print("=" * 50)
    print("  PayrollWise — Payroll Web Application")
    print(f"  Database : {DB}")
    print("  Open at  : http://localhost:5000")
    print("  Stop     : Ctrl + C")
    print("=" * 50)
    print()
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
