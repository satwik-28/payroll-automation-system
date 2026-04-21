"""
PayrollWise — Start Script
Run this file to launch the web application.

    python start.py

Then open your browser at: http://localhost:5000
"""
import sys
import os
import subprocess
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

def check_python():
    if sys.version_info < (3, 8):
        print(f"  [ERROR] Python 3.8+ required. You have {sys.version}")
        sys.exit(1)
    print(f"  [OK] Python {sys.version.split()[0]}")

def check_flask():
    try:
        import flask
        print(f"  [OK] Flask {flask.__version__}")
        return True
    except ImportError:
        print("  [MISSING] Flask not installed.")
        print("  Installing Flask now...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
        print("  [OK] Flask installed")
        return True

def check_database():
    db_path = THIS_DIR / "payroll.db"

    # If not found locally, search for it
    if not db_path.exists():
        search_paths = [
            THIS_DIR / ".." / "payroll_automation_system" / "database" / "payroll.db",
            THIS_DIR / ".." / "shared" / "database" / "payroll.db",
            THIS_DIR / ".." / "payroll_complete" / "shared" / "database" / "payroll.db",
        ]
        for candidate in search_paths:
            resolved = candidate.resolve()
            if resolved.exists():
                import shutil
                shutil.copy2(resolved, db_path)
                print(f"  [OK] Database copied from {resolved.name}")
                break

    if db_path.exists():
        size_kb = db_path.stat().st_size // 1024
        print(f"  [OK] Database found ({size_kb} KB): {db_path}")
        return True
    else:
        print("  [ERROR] payroll.db not found!")
        print()
        print("  FIX: Copy payroll.db into the payroll_web/ folder.")
        print("  The database is in:")
        print("    payroll_automation_system/database/payroll.db")
        print("    OR  shared/database/payroll.db")
        print()
        print("  Or run: python setup_db.py  (to rebuild it)")
        sys.exit(1)

def check_templates():
    tmpl_dir = THIS_DIR / "templates"
    required = ["base.html", "dashboard.html", "employees.html",
                "payroll.html", "attendance.html", "loans.html",
                "reports.html", "salary_revisions.html"]
    missing = [t for t in required if not (tmpl_dir / t).exists()]
    if missing:
        print(f"  [ERROR] Missing templates: {missing}")
        print(f"  Make sure you are running from the payroll_web/ folder.")
        sys.exit(1)
    print(f"  [OK] All {len(required)} templates found")

def check_port(port=5000):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) == 0:
            print(f"  [WARN] Port {port} is already in use.")
            print(f"         Another server may be running.")
            print(f"         Stop it or change the port in app.py")
        else:
            print(f"  [OK] Port {port} is available")

def main():
    print()
    print("=" * 55)
    print("  PayrollWise — Payroll Automation System")
    print("=" * 55)
    print()
    print("  Checking requirements...")

    check_python()
    check_flask()
    check_database()
    check_templates()
    check_port(5000)

    print()
    print("=" * 55)
    print("  Starting web server...")
    print("  Open browser at:  http://localhost:5000")
    print("  Stop server:      Ctrl + C")
    print("=" * 55)
    print()

    # Change to payroll_web directory so Flask finds templates
    os.chdir(THIS_DIR)

    # Import and run the app
    from app import app
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)

if __name__ == "__main__":
    main()
