"""
PayrollWise — One-click Setup & Launch
=======================================
Run this from the project root to set up and start everything.

    python setup_and_run.py

Options:
    python setup_and_run.py --web     # Start web app only
    python setup_and_run.py --tasks   # Run all 30 tasks
    python setup_and_run.py --task 5  # Run specific task
"""
import sys
import os
import subprocess
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent

def print_banner():
    print()
    print("=" * 60)
    print("  💼  PayrollWise — Data Engineering System")
    print("  30 Tasks + Web Application + SQLite Database")
    print("=" * 60)
    print()

def check_python():
    v = sys.version_info
    if v < (3, 8):
        print(f"  ERROR: Python 3.8+ required. You have {v.major}.{v.minor}")
        sys.exit(1)
    print(f"  [OK] Python {v.major}.{v.minor}.{v.micro}")

def install_deps():
    print("\n  Installing dependencies...")
    packages = ["flask", "pandas", "numpy", "matplotlib"]
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg} already installed")
        except ImportError:
            print(f"  Installing {pkg}...")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"],
                           check=True)
            print(f"  [OK] {pkg} installed")

def ensure_database():
    """Make sure payroll.db exists in payroll_web/"""
    web_db = HERE / "payroll_web" / "payroll.db"
    if web_db.exists():
        print(f"\n  [OK] Database: {web_db} ({web_db.stat().st_size // 1024} KB)")
        return

    # Search for it
    candidates = [
        HERE / "shared" / "database" / "payroll.db",
        HERE / "payroll_automation_system" / "database" / "payroll.db",
    ]
    for c in candidates:
        if c.exists():
            shutil.copy2(c, web_db)
            print(f"\n  [OK] Database copied: {web_db}")
            return

    # Rebuild from scratch
    print("\n  Building database from scratch...")
    setup = HERE / "payroll_automation_system" / "database" / "setup_db.py"
    data  = HERE / "payroll_automation_system" / "database" / "sample_data.py"
    if setup.exists():
        subprocess.run([sys.executable, str(setup)], check=True)
        subprocess.run([sys.executable, str(data)],  check=True)
        src = HERE / "payroll_automation_system" / "database" / "payroll.db"
        if src.exists():
            shutil.copy2(src, web_db)
            print(f"  [OK] Database built and copied")
    else:
        print("  WARNING: Could not find or build payroll.db")
        print("           Copy payroll.db into payroll_web/ manually")

def start_web():
    print("\n" + "=" * 60)
    print("  Starting Web Application...")
    print("  Open browser at:  http://localhost:5000")
    print("  Stop server:      Ctrl + C")
    print("=" * 60)
    print()
    os.chdir(HERE / "payroll_web")
    from payroll_web.app import app
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)

def run_tasks(task_arg=None):
    cmd = [sys.executable, str(HERE / "run_all.py")]
    if task_arg:
        cmd += ["--task", str(task_arg)]
    subprocess.run(cmd, cwd=HERE)

def main():
    print_banner()
    check_python()
    install_deps()
    ensure_database()

    args = sys.argv[1:]

    if "--web" in args or not args:
        # Default: start web app
        print("\n  What would you like to do?")
        print("  1. Start web application (default)")
        print("  2. Run all 30 tasks")
        print("  3. Exit")
        print()
        choice = input("  Enter choice [1]: ").strip() or "1"
        if choice == "2":
            run_tasks()
        elif choice == "3":
            print("  Goodbye!")
        else:
            # Start web app
            print("\n  Starting web application...")
            print("  Open: http://localhost:5000")
            print("  Stop: Ctrl + C")
            print()
            os.chdir(HERE / "payroll_web")
            sys.path.insert(0, str(HERE / "payroll_web"))
            from app import app
            app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)

    elif "--tasks" in args:
        run_tasks()

    elif "--task" in args:
        idx = args.index("--task")
        task_num = args[idx + 1] if idx + 1 < len(args) else "1"
        run_tasks(task_num)

if __name__ == "__main__":
    main()
