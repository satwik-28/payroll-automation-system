"""
TASK 24: Cloud Basics — AWS vs GCP vs Azure comparison
TASK 25: Cloud Storage — S3/GCS simulation
TASK 26: Cloud Compute — EC2/deployment simulation
TASK 27: Cloud Data Warehouse — BigQuery/Redshift simulation
"""
import json, time, hashlib, os, shutil, sqlite3, random
from pathlib import Path
from datetime import datetime
from typing import Dict, List

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)
DB = Path(__file__).parent.parent / "shared/database/payroll.db"

# ══════════════════════════════════════════════════════════════
#  TASK 24: CLOUD COMPARISON
# ══════════════════════════════════════════════════════════════
CLOUD_COMPARISON = {
    "Storage": {
        "AWS":   {"service":"S3","type":"Object Store","cost_gb_mo":"$0.023","sla":"99.999999999% (11 nines)","payroll_use":"Payroll CSV exports, payslip PDFs, DB backups"},
        "GCP":   {"service":"Cloud Storage","type":"Object Store","cost_gb_mo":"$0.020","sla":"99.999999999%","payroll_use":"Archive attendance data, ML training datasets"},
        "Azure": {"service":"Blob Storage","type":"Object Store","cost_gb_mo":"$0.018","sla":"99.9% (LRS)","payroll_use":"Payroll reports, compliance archives"},
    },
    "Compute": {
        "AWS":   {"service":"EC2","type":"Virtual Machines","min_cost":"$0.0116/hr (t3.micro)","payroll_use":"Run Flask payroll API, batch processing"},
        "GCP":   {"service":"Compute Engine","type":"Virtual Machines","min_cost":"$0.0104/hr (e2-micro)","payroll_use":"Payroll calculation jobs, reports"},
        "Azure": {"service":"Virtual Machines","type":"Virtual Machines","min_cost":"$0.0104/hr (B1s)","payroll_use":"Payroll web server, ETL workers"},
    },
    "Data Warehouse": {
        "AWS":   {"service":"Redshift","type":"Columnar DW","cost":"$0.25/hr (dc2.large)","payroll_use":"YTD analytics, multi-year payroll trends"},
        "GCP":   {"service":"BigQuery","type":"Serverless DW","cost":"$5/TB queried","payroll_use":"Ad-hoc payroll analysis, BI dashboards"},
        "Azure": {"service":"Synapse Analytics","type":"Columnar DW","cost":"$0.30/hr","payroll_use":"HR analytics, salary benchmarking"},
    },
    "Managed Database": {
        "AWS":   {"service":"RDS PostgreSQL","cost":"$0.017/hr (db.t3.micro)","payroll_use":"OLTP payroll DB with automated backups"},
        "GCP":   {"service":"Cloud SQL","cost":"$0.0150/hr","payroll_use":"Payroll records, employee master data"},
        "Azure": {"service":"Azure SQL Database","cost":"$0.005 DTU model","payroll_use":"Payroll transactions, attendance DB"},
    },
    "Streaming": {
        "AWS":   {"service":"Kinesis","type":"Managed Kafka-like","payroll_use":"Real-time attendance events, payroll alerts"},
        "GCP":   {"service":"Pub/Sub","type":"Messaging","payroll_use":"Event-driven payroll notifications"},
        "Azure": {"service":"Event Hubs","type":"Managed Kafka","payroll_use":"Payroll pipeline event streaming"},
    },
    "Orchestration": {
        "AWS":   {"service":"MWAA (Managed Airflow)","payroll_use":"Payroll ETL DAGs"},
        "GCP":   {"service":"Cloud Composer","payroll_use":"Monthly payroll pipeline scheduling"},
        "Azure": {"service":"Azure Data Factory","payroll_use":"Payroll data movement & transformation"},
    },
    "Serverless": {
        "AWS":   {"service":"Lambda","trigger":"S3/API/Schedule","payroll_use":"Auto-trigger payslip generation when payroll is approved"},
        "GCP":   {"service":"Cloud Functions","trigger":"Pub/Sub/HTTP","payroll_use":"Send payslip email on payment confirmation"},
        "Azure": {"service":"Azure Functions","trigger":"Event/Timer","payroll_use":"Monthly TDS calculation trigger"},
    }
}

# ══════════════════════════════════════════════════════════════
#  TASK 25: CLOUD STORAGE SIMULATION (S3/GCS)
# ══════════════════════════════════════════════════════════════
class CloudBucket:
    """Simulates AWS S3 / GCP Cloud Storage bucket."""
    STORAGE_CLASSES = {"STANDARD":0.023,"IA":0.0125,"GLACIER":0.004,"DEEP_ARCHIVE":0.00099}

    def __init__(self, name: str, provider: str = "AWS S3", region: str = "ap-south-1"):
        self.name = name; self.provider = provider; self.region = region
        self._store: Dict[str, dict] = {}
        self._local = OUTPUT / "cloud_storage" / name
        self._local.mkdir(parents=True, exist_ok=True)
        self.versioning = True; self._versions: Dict[str, list] = {}
        self.lifecycle_rules = []
        self.total_size = 0

    def put_object(self, key: str, content: str, metadata: dict = None,
                   storage_class: str = "STANDARD") -> dict:
        """Upload object (simulates S3 PutObject)."""
        version_id = hashlib.md5(f"{key}{time.time()}".encode()).hexdigest()[:8]
        size = len(content.encode())
        obj = {
            "key": key, "size": size, "etag": hashlib.md5(content.encode()).hexdigest(),
            "storage_class": storage_class, "version_id": version_id,
            "last_modified": datetime.now().isoformat(),
            "metadata": metadata or {}, "content_type": "text/csv"
        }
        self._store[key] = obj
        self._versions.setdefault(key, []).append(version_id)
        (self._local / key.replace("/", "_")).write_text(content)
        self.total_size += size
        return {"ETag": obj["etag"], "VersionId": version_id, "Location": f"s3://{self.name}/{key}"}

    def get_object(self, key: str) -> dict:
        """Download object (simulates S3 GetObject)."""
        obj = self._store.get(key)
        if not obj: raise FileNotFoundError(f"Key '{key}' not found in bucket '{self.name}'")
        local = self._local / key.replace("/", "_")
        content = local.read_text() if local.exists() else ""
        return {"Body": content, "ContentLength": obj["size"], "ETag": obj["etag"],
                "VersionId": obj["version_id"], "Metadata": obj["metadata"]}

    def list_objects(self, prefix: str = "") -> list:
        """List objects (simulates S3 ListObjectsV2)."""
        return [v for k, v in self._store.items() if k.startswith(prefix)]

    def delete_object(self, key: str) -> dict:
        if key in self._store:
            del self._store[key]
            return {"DeleteMarker": True, "VersionId": "dm_" + hashlib.md5(key.encode()).hexdigest()[:6]}
        return {}

    def generate_presigned_url(self, key: str, expiry_seconds: int = 3600) -> str:
        token = hashlib.md5(f"{key}{time.time()}".encode()).hexdigest()
        return f"https://{self.name}.s3.{self.region}.amazonaws.com/{key}?X-Amz-Expires={expiry_seconds}&token={token}"

    def add_lifecycle_rule(self, prefix: str, transition_days: int, delete_days: int):
        self.lifecycle_rules.append({"prefix":prefix,"transition_days":transition_days,"delete_days":delete_days})

    def cost_estimate(self) -> dict:
        size_gb = self.total_size / (1024**3)
        cost = size_gb * self.STORAGE_CLASSES.get("STANDARD", 0.023)
        return {"size_bytes": self.total_size, "size_gb": round(size_gb,6), "monthly_cost_usd": round(cost,6)}

    def bucket_policy(self) -> dict:
        return {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789:role/PayrollApp"},
                 "Action":["s3:GetObject","s3:PutObject"],"Resource":f"arn:aws:s3:::{self.name}/*"},
                {"Effect":"Deny","Principal":"*","Action":"s3:DeleteObject",
                 "Resource":f"arn:aws:s3:::{self.name}/archive/*",
                 "Condition":{"StringNotEquals":{"aws:PrincipalArn":"arn:aws:iam::123456789:role/AdminRole"}}}
            ]
        }


# ══════════════════════════════════════════════════════════════
#  TASK 26: CLOUD COMPUTE SIMULATION (EC2)
# ══════════════════════════════════════════════════════════════
class EC2Instance:
    """Simulates an AWS EC2 instance lifecycle."""
    INSTANCE_TYPES = {
        "t3.micro":  {"vcpu":2,"ram_gb":1,"cost_hr":0.0116,"network":"Low"},
        "t3.small":  {"vcpu":2,"ram_gb":2,"cost_hr":0.0232,"network":"Low"},
        "t3.medium": {"vcpu":2,"ram_gb":4,"cost_hr":0.0464,"network":"Moderate"},
        "m5.large":  {"vcpu":2,"ram_gb":8,"cost_hr":0.0960,"network":"High"},
        "c5.xlarge": {"vcpu":4,"ram_gb":8,"cost_hr":0.1700,"network":"High"},
    }

    def __init__(self, instance_type="t3.small", ami="ami-0b09fd8b5e4d76f3b", region="ap-south-1"):
        self.instance_type = instance_type
        self.ami = ami; self.region = region
        self.instance_id = "i-" + hashlib.md5(f"{time.time()}".encode()).hexdigest()[:17]
        self.state = "stopped"; self.public_ip = None; self.private_ip = None
        self.launch_time = None; self.uptime_s = 0
        self.specs = self.INSTANCE_TYPES.get(instance_type, self.INSTANCE_TYPES["t3.small"])
        self.security_groups = []
        self.tags = {}

    def start(self):
        time.sleep(0.05)
        self.state = "running"
        self.public_ip  = f"13.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        self.private_ip = f"10.0.{random.randint(0,255)}.{random.randint(1,254)}"
        self.launch_time = datetime.now().isoformat()
        return {"InstanceId": self.instance_id, "State": {"Name":"running"}, "PublicIpAddress": self.public_ip}

    def stop(self):
        self.uptime_s = random.randint(3600, 86400)
        self.state = "stopped"
        return {"InstanceId": self.instance_id, "State": {"Name":"stopped"}}

    def describe(self):
        return {
            "InstanceId": self.instance_id, "InstanceType": self.instance_type,
            "State": {"Name": self.state}, "PublicIpAddress": self.public_ip,
            "PrivateIpAddress": self.private_ip, "LaunchTime": self.launch_time,
            "AMI": self.ami, "Region": self.region, "Specs": self.specs,
            "Tags": self.tags
        }

    def cost_estimate(self, hours=730):
        return round(hours * self.specs["cost_hr"], 2)

class DeploymentPipeline:
    """Simulates CI/CD deployment to EC2."""
    def __init__(self, instance: EC2Instance):
        self.instance = instance
        self.steps = []

    def run_step(self, name: str, command: str, simulate_seconds=0.05):
        t0 = time.time()
        time.sleep(simulate_seconds)
        result = {"step": name, "command": command, "status": "success",
                  "duration_s": round(time.time()-t0, 3), "ts": datetime.now().isoformat()}
        self.steps.append(result)
        print(f"    [{name}] {command[:50]} → ✓ ({result['duration_s']}s)")
        return result

    def deploy_payroll_app(self):
        print(f"  Deploying PayrollWise to {self.instance.instance_id} ({self.instance.public_ip})")
        steps = [
            ("SSH Connect",          f"ssh -i payroll.pem ubuntu@{self.instance.public_ip}"),
            ("Update packages",      "sudo apt-get update -y && sudo apt-get upgrade -y"),
            ("Install Python",       "sudo apt-get install python3.11 python3-pip -y"),
            ("Install dependencies", "pip install flask pandas numpy matplotlib"),
            ("Clone repository",     "git clone https://github.com/payrollwise/payroll-system.git"),
            ("Configure env",        "cp .env.example .env && nano .env"),
            ("Setup database",       "python database/setup_db.py && python database/sample_data.py"),
            ("Configure nginx",      "sudo apt install nginx -y && sudo cp nginx.conf /etc/nginx/sites-available/payroll"),
            ("Enable nginx",         "sudo nginx -t && sudo systemctl reload nginx"),
            ("Setup systemd",        "sudo cp payroll.service /etc/systemd/system/ && sudo systemctl enable payroll"),
            ("Start application",    "sudo systemctl start payroll"),
            ("Health check",         f"curl -f http://{self.instance.public_ip}/api/health"),
            ("Configure CloudWatch", "sudo apt install amazon-cloudwatch-agent -y"),
        ]
        for name, cmd in steps:
            self.run_step(name, cmd)
        return {"deployed_to": self.instance.public_ip, "steps": len(self.steps), "status": "success"}


# ══════════════════════════════════════════════════════════════
#  TASK 27: CLOUD DATA WAREHOUSE SIMULATION (BigQuery/Redshift)
# ══════════════════════════════════════════════════════════════
class CloudDataWarehouse:
    """Simulates BigQuery / Redshift analytical queries."""

    def __init__(self, provider: str = "BigQuery", project: str = "payroll-analytics"):
        self.provider = provider; self.project = project
        self.tables = {}; self.query_history = []
        self.total_bytes_processed = 0

    def load_table(self, table_name: str, data: list, schema: list):
        self.tables[table_name] = {"data": data, "schema": schema,
                                    "rows": len(data), "created": datetime.now().isoformat()}
        size_mb = len(json.dumps(data).encode()) / 1024 / 1024
        print(f"  Loaded: {table_name} ({len(data)} rows, {size_mb:.2f} MB)")

    def query(self, sql: str, description: str = "") -> dict:
        """Execute an analytical SQL query (delegates to SQLite for real results)."""
        t0 = time.time()
        bytes_p = random.randint(10_000_000, 500_000_000)  # simulate bytes scanned
        self.total_bytes_processed += bytes_p

        # Actually run on real SQLite DB for correct results
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in conn.execute(sql).fetchall()]
        except Exception as e:
            rows = [{"error": str(e)}]
        conn.close()

        elapsed = time.time() - t0
        cost = bytes_p / 1e12 * 5  # BigQuery: $5/TB

        result = {
            "description": description, "rows": len(rows),
            "bytes_processed": bytes_p, "cost_usd": round(cost, 6),
            "elapsed_ms": round(elapsed * 1000, 2),
            "provider": self.provider, "data": rows[:5]
        }
        self.query_history.append({k:v for k,v in result.items() if k != "data"})
        return result

    def get_usage_report(self):
        total_cost = sum(q["cost_usd"] for q in self.query_history)
        return {
            "provider": self.provider,
            "total_queries": len(self.query_history),
            "total_bytes_tb": round(self.total_bytes_processed / 1e12, 6),
            "estimated_cost_usd": round(total_cost, 4),
            "avg_query_ms": round(sum(q["elapsed_ms"] for q in self.query_history)
                                   / max(len(self.query_history),1), 2)
        }


DW_QUERIES = {
    "Monthly Payroll Cost by Department (2026)": """
        SELECT d.dept_name,
               COUNT(pr.payroll_id) headcount,
               ROUND(SUM(pr.gross_salary),2) total_gross,
               ROUND(SUM(pr.net_salary),2) total_net,
               ROUND(AVG(pr.net_salary),2) avg_net,
               ROUND(SUM(pr.income_tax_tds),2) total_tds
        FROM payroll_records pr
        JOIN employees e ON pr.emp_id=e.emp_id
        JOIN departments d ON e.dept_id=d.dept_id
        JOIN payroll_periods pp ON pr.period_id=pp.period_id
        WHERE pp.year=2026 AND pr.status='Paid'
        GROUP BY d.dept_name ORDER BY total_gross DESC
    """,
    "Employee Salary Percentile (Top 10%)": """
        SELECT e.emp_code, e.first_name||' '||e.last_name name,
               d.dept_name, e.basic_salary,
               ROUND(PERCENT_RANK() OVER (ORDER BY e.basic_salary)*100,1) percentile
        FROM employees e
        JOIN departments d ON e.dept_id=d.dept_id
        WHERE e.status='Active'
        ORDER BY e.basic_salary DESC LIMIT 5
    """,
    "Quarter-over-Quarter Payroll Trend": """
        SELECT CASE
            WHEN pp.month BETWEEN 4 AND 6 THEN pp.year||'-Q1'
            WHEN pp.month BETWEEN 7 AND 9 THEN pp.year||'-Q2'
            WHEN pp.month BETWEEN 10 AND 12 THEN pp.year||'-Q3'
            ELSE (pp.year-1)||'-Q4' END AS fiscal_quarter,
            COUNT(DISTINCT pr.emp_id) headcount,
            ROUND(SUM(pr.gross_salary)/1000,1) gross_k,
            ROUND(SUM(pr.net_salary)/1000,1) net_k
        FROM payroll_records pr
        JOIN payroll_periods pp ON pr.period_id=pp.period_id
        WHERE pr.status='Paid'
        GROUP BY fiscal_quarter ORDER BY pp.year, pp.month LIMIT 6
    """,
    "TDS Liability Analysis by Income Bracket": """
        SELECT
            CASE
                WHEN e.basic_salary*12 < 400000  THEN '0-4L (No Tax)'
                WHEN e.basic_salary*12 < 800000  THEN '4L-8L (5%)'
                WHEN e.basic_salary*12 < 1200000 THEN '8L-12L (10%)'
                WHEN e.basic_salary*12 < 1600000 THEN '12L-16L (15%)'
                ELSE 'Above 16L (20%+)' END AS bracket,
            COUNT(*) employees,
            ROUND(AVG(pr.income_tax_tds)*12,0) avg_annual_tds,
            ROUND(SUM(pr.income_tax_tds),2) period_tds
        FROM employees e
        JOIN payroll_records pr ON e.emp_id=pr.emp_id
        WHERE pr.period_id=24
        GROUP BY bracket ORDER BY avg_annual_tds DESC
    """,
    "Loan Repayment Status Dashboard": """
        SELECT
            l.status,
            COUNT(*) loan_count,
            ROUND(SUM(l.loan_amount),2) total_sanctioned,
            ROUND(SUM(l.outstanding),2) total_outstanding,
            ROUND(AVG(l.emi_amount),2) avg_emi,
            ROUND((1-SUM(l.outstanding)/SUM(l.loan_amount))*100,1) repaid_pct
        FROM employee_loans l
        GROUP BY l.status
    """,
}

def run():
    print("="*60)
    print("  TASK 24: Cloud Basics — AWS vs GCP vs Azure")
    print("  TASK 25: Cloud Storage — S3/GCS Simulation")
    print("  TASK 26: Cloud Compute — EC2 Deployment")
    print("  TASK 27: Cloud DW — BigQuery/Redshift Queries")
    print("="*60)

    # ── TASK 24 ───────────────────────────────────────────────
    print("\n══ TASK 24: CLOUD COMPARISON ══")
    for category, providers in CLOUD_COMPARISON.items():
        print(f"\n  {category}:")
        for prov, info in providers.items():
            svc = info.get("service","")
            use = info.get("payroll_use","")[:60]
            print(f"    {prov:6} | {svc:25} | {use}")

    # ── TASK 25 ───────────────────────────────────────────────
    print("\n══ TASK 25: CLOUD STORAGE ══")
    bucket = CloudBucket("payrollwise-data-ap-south", "AWS S3", "ap-south-1")

    bucket.add_lifecycle_rule("archive/", transition_days=30, delete_days=2555)
    print(f"\n  Bucket: s3://{bucket.name}")
    print(f"  Lifecycle rule: archive/ → Glacier after 30d, delete after 7 years")
    print(f"  Bucket policy: IAM role-based access + deny delete on archive/\n")

    # Upload payroll files
    uploads = {
        "payroll/2026/03/payroll_register.csv": "emp_code,net_salary\nEMP001,62363.33\nEMP002,172166.67\n"*15,
        "payroll/2026/03/payslips/EMP001_payslip.pdf": "BINARY_PDF_CONTENT_EMP001_MARCH_2026" * 50,
        "payroll/2026/03/payslips/EMP002_payslip.pdf": "BINARY_PDF_CONTENT_EMP002_MARCH_2026" * 50,
        "reports/2026/ytd_salary_2026.xlsx": "EXCEL_YTD_REPORT_CONTENT" * 30,
        "reports/2026/tds_q4_2025.pdf": "TDS_CERTIFICATE_Q4_2025_CONTENT" * 25,
        "archive/2025/payroll_annual_2025.tar.gz": "ARCHIVE_DATA_2025" * 100,
        "logs/etl_pipeline_2026-03-01.log": "2026-03-01 09:00 INFO Pipeline started\n2026-03-01 09:05 INFO 30 records processed\n2026-03-01 09:07 INFO Pipeline complete\n",
    }
    print("  PutObject operations:")
    for key, content in uploads.items():
        result = bucket.put_object(key, content,
                                   metadata={"period":"2026-03","uploaded_by":"airflow"},
                                   storage_class="STANDARD" if "archive" not in key else "GLACIER")
        print(f"  ✓ s3://{bucket.name}/{key} | ETag: {result['ETag'][:8]}.. | Version: {result['VersionId']}")

    # GetObject
    print("\n  GetObject: payroll_register.csv")
    obj = bucket.get_object("payroll/2026/03/payroll_register.csv")
    print(f"  Downloaded: {obj['ContentLength']} bytes | ETag: {obj['ETag'][:12]}...")

    # ListObjects
    print("\n  ListObjects (prefix=payroll/2026/03/):")
    objs = bucket.list_objects("payroll/2026/03/")
    for o in objs:
        print(f"  {o['key']:55} {o['size']:>8}B {o['storage_class']}")

    # Presigned URL
    url = bucket.generate_presigned_url("payroll/2026/03/payslips/EMP001_payslip.pdf", 3600)
    print(f"\n  Presigned URL (1hr): {url[:80]}...")

    # Cost
    cost = bucket.cost_estimate()
    print(f"\n  Storage cost estimate: {cost}")

    # ── TASK 26 ───────────────────────────────────────────────
    print("\n══ TASK 26: CLOUD COMPUTE ══")
    instance = EC2Instance(instance_type="t3.small", region="ap-south-1")
    instance.tags = {"Name":"payrollwise-prod","Project":"PayrollWise","Env":"production"}
    instance.security_groups = ["sg-payroll-web","sg-payroll-db"]

    print(f"\n  Launching EC2 instance...")
    start_result = instance.start()
    print(f"  Instance ID:  {instance.instance_id}")
    print(f"  Instance Type:{instance.instance_type} ({instance.specs['vcpu']} vCPU, {instance.specs['ram_gb']}GB RAM)")
    print(f"  Public IP:    {instance.public_ip}")
    print(f"  Private IP:   {instance.private_ip}")
    print(f"  Region:       {instance.region}")
    print(f"  Tags:         {instance.tags}")
    print(f"  Cost (1 month): ${instance.cost_estimate(730):.2f}/month")

    print("\n  Running deployment pipeline:")
    pipeline = DeploymentPipeline(instance)
    deploy_result = pipeline.deploy_payroll_app()
    print(f"\n  Deployment complete: {deploy_result['steps']} steps, status={deploy_result['status']}")
    print(f"  PayrollWise live at: http://{instance.public_ip}:5000")

    print("\n  Auto Scaling configuration (reference):")
    asg_config = {
        "min_instances": 2, "max_instances": 10, "desired": 2,
        "scale_out_policy": "CPUUtilization > 70% for 2 minutes → add 1 instance",
        "scale_in_policy": "CPUUtilization < 20% for 10 minutes → remove 1 instance",
        "health_check": "ELB health check every 30s",
        "payroll_consideration": "Scale out on month-end payroll processing day (1st of month)"
    }
    for k, v in asg_config.items():
        print(f"    {k}: {v}")

    stop_result = instance.stop()
    print(f"\n  Instance stopped: {stop_result['State']['Name']}")

    # ── TASK 27 ───────────────────────────────────────────────
    print("\n══ TASK 27: CLOUD DATA WAREHOUSE ══")
    dw = CloudDataWarehouse("BigQuery", "payroll-analytics-prod")

    print(f"\n  Running analytical queries on {dw.provider}:")
    all_results = {}
    for query_name, sql in DW_QUERIES.items():
        result = dw.query(sql, description=query_name)
        print(f"\n  [{query_name}]")
        print(f"  Rows: {result['rows']} | Bytes: {result['bytes_processed']/1e6:.1f}MB | "
              f"Cost: ${result['cost_usd']:.5f} | Time: {result['elapsed_ms']:.1f}ms")
        for row in result["data"][:3]:
            print(f"    {row}")
        all_results[query_name] = {"rows": result["rows"], "cost_usd": result["cost_usd"]}

    usage = dw.get_usage_report()
    print(f"\n  BigQuery Usage Summary:")
    for k, v in usage.items():
        print(f"    {k}: {v}")

    print("\n  Redshift vs BigQuery vs Synapse:")
    print(f"    {'Feature':<30} {'Redshift':>15} {'BigQuery':>15} {'Synapse':>15}")
    print("    " + "-"*77)
    comparisons = [
        ("Architecture",   "Cluster-based","Serverless","Hybrid"),
        ("Pricing model",  "Per hour","Per TB queried","Per DWU hour"),
        ("Auto-scaling",   "Manual","Automatic","Automatic"),
        ("Best for",       "Fixed workloads","Ad-hoc queries","Azure ecosystem"),
        ("Payroll query(s)","~2-5s","~1-3s","~2-6s"),
    ]
    for row in comparisons:
        print(f"    {row[0]:<30} {row[1]:>15} {row[2]:>15} {row[3]:>15}")

    # Save all results
    results = {
        "task24_cloud_comparison": {k: list(v.keys()) for k, v in CLOUD_COMPARISON.items()},
        "task25_storage": {"bucket": bucket.name, "objects": len(bucket._store),
                           "cost_estimate": cost},
        "task26_compute": {"instance_id": instance.instance_id,
                           "deployment_steps": len(pipeline.steps),
                           "monthly_cost_usd": instance.cost_estimate(730)},
        "task27_dw": {"queries_run": len(DW_QUERIES), "usage": usage,
                      "query_results": all_results},
        "timestamp": datetime.now().isoformat()
    }
    (OUTPUT/"cloud_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results saved: {OUTPUT}/cloud_results.json")
    return results

if __name__ == "__main__":
    run()
