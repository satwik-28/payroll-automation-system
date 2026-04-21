"""
TASK 22: Airflow Basics — DAG for ETL Pipeline
TASK 23: Airflow Advanced — Scheduling, Monitoring, Retry

NOTE: This simulates Airflow DAG behavior in pure Python.
For production use, install Apache Airflow:  pip install apache-airflow
Then place these DAGs in the $AIRFLOW_HOME/dags/ folder.
"""
import time, json, random, traceback, sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from collections import defaultdict

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)
DB = Path(__file__).parent.parent / "shared/database/payroll.db"

# ══════════════════════════════════════════════════════════════
#  AIRFLOW SIMULATION FRAMEWORK
# ══════════════════════════════════════════════════════════════
class TaskStatus:
    PENDING = "pending"; RUNNING = "running"; SUCCESS = "success"
    FAILED  = "failed";  SKIPPED = "skipped"; RETRY   = "retry"

class TaskInstance:
    def __init__(self, task_id: str, task_fn: Callable, retries=1, retry_delay=2):
        self.task_id      = task_id
        self.task_fn      = task_fn
        self.retries      = retries
        self.retry_delay  = retry_delay
        self.status       = TaskStatus.PENDING
        self.start_time   = None
        self.end_time     = None
        self.duration_s   = None
        self.attempt      = 0
        self.result       = None
        self.error        = None
        self.upstream     = []
        self.xcom         = {}

    def run(self, context: dict):
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.now()

        for attempt in range(self.retries + 1):
            self.attempt = attempt + 1
            try:
                print(f"    [{self.task_id}] Attempt {self.attempt}/{self.retries+1} → RUNNING")
                self.result = self.task_fn(context, self)
                self.status = TaskStatus.SUCCESS
                self.end_time = datetime.now()
                self.duration_s = (self.end_time - self.start_time).total_seconds()
                print(f"    [{self.task_id}] ✓ SUCCESS ({self.duration_s:.2f}s)")
                return True
            except Exception as e:
                self.error = str(e)
                if attempt < self.retries:
                    self.status = TaskStatus.RETRY
                    print(f"    [{self.task_id}] ✗ FAILED (attempt {self.attempt}), retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay * 0.1)  # scaled down for simulation
                else:
                    self.status = TaskStatus.FAILED
                    self.end_time = datetime.now()
                    self.duration_s = (self.end_time - self.start_time).total_seconds()
                    print(f"    [{self.task_id}] ✗ FAILED after {self.retries+1} attempts: {e}")
                    return False

    def to_dict(self):
        return {
            "task_id": self.task_id, "status": self.status,
            "attempt": self.attempt, "duration_s": self.duration_s,
            "start": self.start_time.isoformat() if self.start_time else None,
            "end":   self.end_time.isoformat()   if self.end_time   else None,
            "error": self.error
        }

class DAGRun:
    def __init__(self, dag_id: str, run_id: str, execution_date: str):
        self.dag_id = dag_id; self.run_id = run_id
        self.execution_date = execution_date
        self.state = "running"; self.tasks = []
        self.start_time = datetime.now(); self.end_time = None

class DAG:
    """Simulates an Airflow DAG."""

    def __init__(self, dag_id: str, description: str = "",
                 schedule_interval: str = "@monthly",
                 start_date: str = "2026-01-01",
                 max_active_runs: int = 1,
                 default_args: dict = None):
        self.dag_id           = dag_id
        self.description      = description
        self.schedule         = schedule_interval
        self.start_date       = start_date
        self.max_active_runs  = max_active_runs
        self.default_args     = default_args or {}
        self._tasks: dict     = {}
        self._edges: dict     = defaultdict(list)  # task_id → [downstream_ids]
        self.dag_runs         = []

    def task(self, task_id: str, retries: int = None, retry_delay: int = None):
        """Decorator to register a task."""
        retries     = retries     or self.default_args.get("retries", 1)
        retry_delay = retry_delay or self.default_args.get("retry_delay_seconds", 30)
        def decorator(fn: Callable):
            ti = TaskInstance(task_id, fn, retries, retry_delay)
            self._tasks[task_id] = ti
            return fn
        return decorator

    def set_upstream(self, task_id: str, upstream_task_id: str):
        self._edges[upstream_task_id].append(task_id)
        self._tasks[task_id].upstream.append(upstream_task_id)

    def _topological_sort(self) -> list:
        """Kahn's topological sort for dependency resolution."""
        in_degree = {tid: 0 for tid in self._tasks}
        for upstream, downstreams in self._edges.items():
            for ds in downstreams:
                in_degree[ds] = in_degree.get(ds, 0) + 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            tid = queue.pop(0); order.append(tid)
            for ds in self._edges.get(tid, []):
                in_degree[ds] -= 1
                if in_degree[ds] == 0: queue.append(ds)
        return order

    def run(self, execution_date: str = None, context_overrides: dict = None):
        """Execute the DAG."""
        execution_date = execution_date or datetime.now().strftime("%Y-%m-%d")
        run_id = f"manual__{execution_date}__" + datetime.now().strftime("%H%M%S")
        dag_run = DAGRun(self.dag_id, run_id, execution_date)
        self.dag_runs.append(dag_run)

        context = {
            "dag_id": self.dag_id,
            "run_id": run_id,
            "execution_date": execution_date,
            "ds": execution_date,
            "next_ds": (datetime.strptime(execution_date, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d"),
            "xcom": {},
            **(context_overrides or {})
        }

        print(f"\n  DAG Run: {run_id}")
        print(f"  Execution date: {execution_date}")
        print(f"  Schedule: {self.schedule}")

        order = self._topological_sort()
        failed_tasks = set()

        for task_id in order:
            ti = self._tasks.get(task_id)
            if not ti: continue

            # Check if upstream failed
            upstream_failed = any(u in failed_tasks for u in ti.upstream)
            if upstream_failed:
                ti.status = TaskStatus.SKIPPED
                print(f"    [{task_id}] SKIPPED (upstream failed)")
                continue

            success = ti.run(context)
            if not success: failed_tasks.add(task_id)
            dag_run.tasks.append(ti.to_dict())
            if ti.result: context["xcom"][task_id] = ti.result

        dag_run.end_time = datetime.now()
        dag_run.state = "success" if not failed_tasks else "failed"
        total_duration = (dag_run.end_time - dag_run.start_time).total_seconds()

        print(f"\n  DAG completed: {dag_run.state.upper()}")
        print(f"  Duration: {total_duration:.2f}s")
        print(f"  Tasks: {len([t for t in dag_run.tasks if t['status']=='success'])} success, "
              f"{len(failed_tasks)} failed, "
              f"{len([t for t in dag_run.tasks if t['status']=='skipped'])} skipped")
        return dag_run

    def get_schedule_description(self):
        crons = {
            "@hourly":  "0 * * * *", "@daily": "0 0 * * *",
            "@weekly":  "0 0 * * 0", "@monthly": "0 0 1 * *",
            "@yearly":  "0 0 1 1 *",
        }
        return crons.get(self.schedule, self.schedule)


# ══════════════════════════════════════════════════════════════
#  TASK 22: PAYROLL ETL DAG
# ══════════════════════════════════════════════════════════════
def build_payroll_etl_dag():
    dag = DAG(
        dag_id="payroll_monthly_etl",
        description="Monthly payroll processing: extract, transform, calculate, distribute",
        schedule_interval="0 9 1 * *",  # 9 AM on 1st of every month
        start_date="2026-01-01",
        default_args={
            "retries": 2,
            "retry_delay_seconds": 300,
            "email_on_failure": True,
            "email": ["payroll_admin@company.com"],
        }
    )

    @dag.task("validate_period", retries=1)
    def validate_period(context, ti):
        """Validate that the payroll period is not already processed."""
        ds = context["ds"]
        time.sleep(0.05)
        conn = sqlite3.connect(DB)
        periods = conn.execute("SELECT period_id FROM payroll_periods WHERE status='Processing' LIMIT 1").fetchone()
        conn.close()
        result = {"period_found": bool(periods), "ds": ds, "validated_at": datetime.now().isoformat()}
        ti.xcom["period_validated"] = True
        return result

    @dag.task("extract_employee_data", retries=2)
    def extract_employee_data(context, ti):
        """Extract active employee data from OLTP database."""
        time.sleep(0.08)
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        emps = conn.execute("SELECT emp_id, basic_salary, grade_id FROM employees WHERE status='Active'").fetchall()
        conn.close()
        result = {"extracted_employees": len(emps), "source": "payroll.db"}
        return result

    @dag.task("extract_attendance_data", retries=2)
    def extract_attendance_data(context, ti):
        """Extract attendance records for the period."""
        time.sleep(0.06)
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        att = conn.execute("SELECT COUNT(*) c FROM attendance WHERE att_date BETWEEN '2026-03-01' AND '2026-03-31'").fetchone()
        conn.close()
        return {"attendance_records": att["c"]}

    @dag.task("calculate_payroll", retries=1)
    def calculate_payroll(context, ti):
        """Calculate gross, deductions, and net salary."""
        emp_data = context["xcom"].get("extract_employee_data", {})
        time.sleep(0.1)
        n = emp_data.get("extracted_employees", 30)
        return {"employees_calculated": n, "total_gross": 4813608.87, "total_net": 4064189.86}

    @dag.task("validate_payroll", retries=1)
    def validate_payroll(context, ti):
        """Data quality checks on calculated payroll."""
        calc = context["xcom"].get("calculate_payroll", {})
        time.sleep(0.04)
        total_net = calc.get("total_net", 0)
        n = calc.get("employees_calculated", 0)
        if n == 0: raise ValueError("No employees to validate!")
        checks = {
            "no_negative_net": True,
            "pf_computed": True,
            "tds_within_range": True,
            "employees_matched": n > 0
        }
        if not all(checks.values()):
            raise ValueError(f"Validation failed: {checks}")
        return {"checks_passed": sum(checks.values()), "total_checks": len(checks)}

    @dag.task("generate_payslips", retries=1)
    def generate_payslips(context, ti):
        """Generate PDF payslips for all employees."""
        calc = context["xcom"].get("calculate_payroll", {})
        n = calc.get("employees_calculated", 30)
        time.sleep(0.07)
        return {"payslips_generated": n, "format": "PDF"}

    @dag.task("transfer_to_bank", retries=3)
    def transfer_to_bank(context, ti):
        """Initiate bank NEFT transfers."""
        val = context["xcom"].get("validate_payroll", {})
        time.sleep(0.06)
        return {"neft_initiated": True, "transfers": 30, "total_amount": 4064189.86}

    @dag.task("send_payslip_emails", retries=2)
    def send_payslip_emails(context, ti):
        """Email payslips to employees."""
        time.sleep(0.05)
        return {"emails_sent": 30, "failed": 0}

    @dag.task("update_dw", retries=2)
    def update_dw(context, ti):
        """Update data warehouse with paid payroll records."""
        time.sleep(0.06)
        return {"dw_records_inserted": 30}

    @dag.task("send_summary_report", retries=1)
    def send_summary_report(context, ti):
        """Send payroll summary to management."""
        time.sleep(0.03)
        return {"report_sent": True, "recipients": ["ceo@company.com", "cfo@company.com"]}

    @dag.task("archive_payroll_data", retries=1)
    def archive_payroll_data(context, ti):
        """Archive processed data to HDFS / S3."""
        time.sleep(0.04)
        return {"archived": True, "location": "s3://payroll-archive/2026/03/"}

    # Set dependencies
    dag.set_upstream("extract_employee_data", "validate_period")
    dag.set_upstream("extract_attendance_data", "validate_period")
    dag.set_upstream("calculate_payroll", "extract_employee_data")
    dag.set_upstream("calculate_payroll", "extract_attendance_data")
    dag.set_upstream("validate_payroll", "calculate_payroll")
    dag.set_upstream("generate_payslips", "validate_payroll")
    dag.set_upstream("transfer_to_bank", "validate_payroll")
    dag.set_upstream("send_payslip_emails", "generate_payslips")
    dag.set_upstream("update_dw", "transfer_to_bank")
    dag.set_upstream("send_summary_report", "update_dw")
    dag.set_upstream("archive_payroll_data", "update_dw")

    return dag


# ══════════════════════════════════════════════════════════════
#  TASK 23: ADVANCED — Scheduling, Monitoring, Retry
# ══════════════════════════════════════════════════════════════
class DAGMonitor:
    """Monitors DAG run history and computes SLAs."""

    def __init__(self):
        self.dag_runs = []
        self.alerts = []

    def record_run(self, dag_run: DAGRun):
        self.dag_runs.append(dag_run)
        duration = (dag_run.end_time - dag_run.start_time).total_seconds() if dag_run.end_time else 0
        # SLA check: payroll DAG should complete < 30 minutes
        if duration > 30 and dag_run.dag_id == "payroll_monthly_etl":
            self.alerts.append(f"SLA BREACH: {dag_run.dag_id} took {duration:.1f}s (limit: 30s)")

    def get_statistics(self):
        if not self.dag_runs: return {}
        durations = [(r.end_time - r.start_time).total_seconds()
                     for r in self.dag_runs if r.end_time]
        success = sum(1 for r in self.dag_runs if r.state == "success")
        return {
            "total_runs":       len(self.dag_runs),
            "successful":       success,
            "failed":           len(self.dag_runs) - success,
            "success_rate_pct": round(success/len(self.dag_runs)*100, 1),
            "avg_duration_s":   round(sum(durations)/len(durations), 2) if durations else 0,
            "max_duration_s":   round(max(durations), 2) if durations else 0,
            "sla_breaches":     len(self.alerts),
            "alerts":           self.alerts
        }

def build_dependency_dag():
    """DAG with intentional failure to demo retry."""
    dag = DAG("payroll_dependency_demo", schedule_interval="@daily")
    attempt_counter = {"n": 0}

    @dag.task("start_task", retries=0)
    def start_task(ctx, ti): time.sleep(0.02); return {"started": True}

    @dag.task("flaky_task", retries=2, retry_delay=1)
    def flaky_task(ctx, ti):
        """Fails on first attempt, succeeds on second (retry demo)."""
        attempt_counter["n"] += 1
        if attempt_counter["n"] < 2:
            raise ConnectionError("DB connection timed out (simulated)")
        time.sleep(0.03); return {"recovered": True, "attempt": attempt_counter["n"]}

    @dag.task("end_task", retries=0)
    def end_task(ctx, ti): time.sleep(0.02); return {"completed": True}

    dag.set_upstream("flaky_task", "start_task")
    dag.set_upstream("end_task", "flaky_task")
    return dag


def run():
    print("="*60)
    print("  TASK 22: Airflow Basics — Payroll ETL DAG")
    print("  TASK 23: Airflow Advanced — Scheduling & Monitoring")
    print("="*60)

    monitor = DAGMonitor()

    # Task 22: Run payroll ETL DAG
    print("\n══ TASK 22: PAYROLL ETL DAG ══")
    payroll_dag = build_payroll_etl_dag()
    print(f"  DAG: {payroll_dag.dag_id}")
    print(f"  Schedule: {payroll_dag.schedule} ({payroll_dag.get_schedule_description()})")
    print(f"  Tasks: {list(payroll_dag._tasks.keys())}")
    print("\n  Executing DAG run (March 2026 payroll):")
    run1 = payroll_dag.run("2026-03-01", {"period": "March-2026"})
    monitor.record_run(run1)

    # Task 23: Advanced — Retry demo + scheduling
    print("\n══ TASK 23: ADVANCED — Retry & Monitoring ══")
    print("\n  [1] Retry Demo DAG:")
    dep_dag = build_dependency_dag()
    run2 = dep_dag.run("2026-04-01")
    monitor.record_run(run2)

    print("\n  [2] Simulating 3 historical runs for statistics:")
    for i, (ds, state_override) in enumerate([("2026-01-01", None),
                                               ("2026-02-01", None),
                                               ("2026-03-01", None)], 1):
        dag2 = build_payroll_etl_dag()
        r = dag2.run(ds)
        monitor.record_run(r)

    print("\n  [3] DAG Monitoring Statistics:")
    stats = monitor.get_statistics()
    for k, v in stats.items():
        print(f"    {k}: {v}")

    print("\n  [4] Scheduling Configuration:")
    schedules = {
        "Monthly payroll":  "0 9 1 * *   → 9 AM on 1st of every month",
        "Daily attendance": "0 23 * * *  → 11 PM daily",
        "Weekly reports":   "0 8 * * MON → 8 AM every Monday",
        "Yearly tax":       "0 10 1 4 *  → 10 AM on April 1st (year-end)",
        "Hourly sync":      "0 * * * *   → Top of every hour",
    }
    for name, schedule in schedules.items():
        print(f"    {name}: {schedule}")

    print("\n  [5] Airflow Production Config (reference):")
    airflow_config = {
        "executor":         "CeleryExecutor (distributed) or LocalExecutor (single node)",
        "metadata_db":      "PostgreSQL (recommended for production)",
        "message_broker":   "Redis or RabbitMQ (for CeleryExecutor)",
        "webserver_port":   8080,
        "max_active_runs":  3,
        "dagbag_import_timeout": 60,
        "smtp_host":        "smtp.company.com",
        "alerting":         "PagerDuty / Slack webhook on failure",
    }
    for k, v in airflow_config.items():
        print(f"    {k}: {v}")

    # Save results
    all_results = {
        "task22_etl_dag": {
            "dag_id": payroll_dag.dag_id,
            "schedule": payroll_dag.schedule,
            "tasks_count": len(payroll_dag._tasks),
            "last_run_state": run1.state,
            "task_results": run1.tasks,
        },
        "task23_monitoring": stats,
        "schedules": list(schedules.keys()),
        "timestamp": datetime.now().isoformat()
    }
    (OUTPUT/"airflow_results.json").write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\n✓ Results saved: {OUTPUT}/airflow_results.json")
    return all_results

if __name__ == "__main__":
    run()
