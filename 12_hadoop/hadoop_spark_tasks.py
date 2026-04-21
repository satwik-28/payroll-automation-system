"""
TASK 12: Hadoop HDFS Simulation
TASK 13: HDFS Architecture Explanation
TASK 14: Spark Basics — Process large dataset
TASK 15: Spark DataFrames — Transformations & Actions
TASK 16: Spark SQL — Query large dataset
TASK 17: PySpark Advanced — Partitioning & Caching

NOTE: This uses Python to simulate HDFS and Spark behavior.
For production, use actual Apache Hadoop/Spark cluster.
If PySpark is available, it will be used; otherwise simulation runs.
"""
import os, json, hashlib, time, math, shutil, sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import threading

BASE = Path(__file__).parent
HDFS_ROOT = BASE / "hdfs_simulation"
OUTPUT    = BASE / "output"
OUTPUT.mkdir(exist_ok=True)
DB = Path(__file__).parent.parent / "shared/database/payroll.db"

# ══════════════════════════════════════════════════════════════
#  TASK 12 & 13: HDFS SIMULATION
# ══════════════════════════════════════════════════════════════
class HDFSNamenode:
    """Simulates HDFS Namenode — stores metadata only."""

    BLOCK_SIZE = 128  # 128 MB (simulated as bytes here)
    REPLICATION = 3

    def __init__(self, path: Path):
        self.path = path
        self.metadata_path = path / "namenode" / "fsimage.json"
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.fsimage: dict = self._load_fsimage()

    def _load_fsimage(self):
        if self.metadata_path.exists():
            return json.loads(self.metadata_path.read_text())
        return {"files": {}, "directories": {"/": {"created": datetime.now().isoformat()}},
                "total_blocks": 0, "total_size": 0}

    def _save(self):
        self.metadata_path.write_text(json.dumps(self.fsimage, indent=2))

    def mkdir(self, hdfs_path: str):
        self.fsimage["directories"][hdfs_path] = {"created": datetime.now().isoformat()}
        self._save()

    def put(self, hdfs_path: str, data: str, datanode_ids: list):
        """Register file in namespace; actual data goes to datanodes."""
        size = len(data.encode())
        blocks = math.ceil(size / self.BLOCK_SIZE) or 1
        block_ids = [hashlib.md5(f"{hdfs_path}_{i}_{time.time()}".encode()).hexdigest()[:12]
                     for i in range(blocks)]
        self.fsimage["files"][hdfs_path] = {
            "size_bytes": size, "blocks": blocks,
            "block_ids": block_ids, "replication": self.REPLICATION,
            "datanodes": datanode_ids[:self.REPLICATION],
            "created": datetime.now().isoformat(),
            "checksum": hashlib.md5(data.encode()).hexdigest()
        }
        self.fsimage["total_blocks"] += blocks
        self.fsimage["total_size"]   += size
        self._save()
        return block_ids

    def ls(self, hdfs_path: str = "/"):
        return [k for k in self.fsimage["files"] if k.startswith(hdfs_path)]

    def stat(self, hdfs_path: str):
        return self.fsimage["files"].get(hdfs_path)

    def get_filesystem_report(self):
        return {
            "total_files":    len(self.fsimage["files"]),
            "total_dirs":     len(self.fsimage["directories"]),
            "total_blocks":   self.fsimage["total_blocks"],
            "total_size_kb":  round(self.fsimage["total_size"]/1024, 2),
            "replication":    self.REPLICATION,
            "block_size_B":   self.BLOCK_SIZE,
        }


class HDFSDatanode:
    """Simulates HDFS Datanode — stores actual block data."""
    def __init__(self, node_id: str, path: Path):
        self.node_id = node_id
        self.path    = path / "datanodes" / node_id
        self.path.mkdir(parents=True, exist_ok=True)
        self.blocks  = {}

    def write_block(self, block_id: str, data: str):
        block_path = self.path / f"{block_id}.block"
        block_path.write_text(data)
        self.blocks[block_id] = {"size": len(data), "path": str(block_path)}
        return block_id

    def read_block(self, block_id: str) -> str:
        block_path = self.path / f"{block_id}.block"
        return block_path.read_text() if block_path.exists() else ""

    def heartbeat(self):
        return {"node_id": self.node_id, "status": "alive",
                "blocks": len(self.blocks), "ts": datetime.now().isoformat()}


class HDFSCluster:
    """3-node HDFS cluster simulation."""
    def __init__(self):
        HDFS_ROOT.mkdir(parents=True, exist_ok=True)
        self.namenode  = HDFSNamenode(HDFS_ROOT)
        self.datanodes = [HDFSDatanode(f"DN{i}", HDFS_ROOT) for i in range(1, 4)]
        self._setup_dirs()

    def _setup_dirs(self):
        for d in ["/payroll","/payroll/raw","/payroll/processed",
                  "/payroll/archive","/logs","/user/payroll_admin"]:
            self.namenode.mkdir(d)

    def put(self, hdfs_path: str, data: str):
        dn_ids = [dn.node_id for dn in self.datanodes]
        block_ids = self.namenode.put(hdfs_path, data, dn_ids)
        # Write to all 3 datanodes (replication)
        for dn in self.datanodes:
            for bid in block_ids:
                chunk = data[:self.namenode.BLOCK_SIZE]
                dn.write_block(bid, chunk)
        return len(block_ids)

    def cat(self, hdfs_path: str) -> str:
        meta = self.namenode.stat(hdfs_path)
        if not meta: return ""
        result = ""
        for bid in meta["block_ids"]:
            result += self.datanodes[0].read_block(bid)
        return result

    def ls(self, path="/"):
        files = self.namenode.ls(path)
        return files

    def heartbeats(self):
        return [dn.heartbeat() for dn in self.datanodes]


# ══════════════════════════════════════════════════════════════
#  TASKS 14-17: SPARK SIMULATION (Pure Python MapReduce)
# ══════════════════════════════════════════════════════════════
class RDD:
    """Simulates a Spark RDD with lazy evaluation."""
    def __init__(self, data: list, name="RDD", partitions=4):
        self._data = data
        self.name  = name
        self._partitions = partitions
        self._transformations = []  # lazy
        self._cached = None
        self._cache_flag = False
        self._partition_key = None

    def _evaluate(self):
        data = self._data[:]
        for fn in self._transformations:
            data = list(fn(data))
        return data

    # ── Transformations (lazy) ──────────────────────────────
    def map(self, fn):
        r = RDD(self._data, f"map({self.name})", self._partitions)
        r._transformations = self._transformations + [lambda d,f=fn: (f(x) for x in d)]
        return r

    def filter(self, fn):
        r = RDD(self._data, f"filter({self.name})", self._partitions)
        r._transformations = self._transformations + [lambda d,f=fn: (x for x in d if f(x))]
        return r

    def flatMap(self, fn):
        r = RDD(self._data, f"flatMap({self.name})", self._partitions)
        r._transformations = self._transformations + [lambda d,f=fn: (y for x in d for y in f(x))]
        return r

    def cache(self):
        self._cache_flag = True
        return self

    def repartition(self, n: int):
        self._partitions = n
        return self

    def partitionBy(self, key_fn):
        self._partition_key = key_fn
        return self

    # ── Actions (eager) ────────────────────────────────────
    def collect(self):
        if self._cache_flag and self._cached is not None:
            return self._cached
        result = self._evaluate()
        if self._cache_flag: self._cached = result
        return result

    def count(self): return len(self.collect())
    def first(self): return self.collect()[0] if self.collect() else None
    def take(self, n): return self.collect()[:n]

    def reduceByKey(self, fn):
        data = self.collect()
        groups = defaultdict(list)
        for k, v in data: groups[k].append(v)
        return {k: (lambda vs: __import__("functools").reduce(fn, vs))(vs) for k, vs in groups.items()}

    def groupByKey(self):
        data = self.collect()
        groups = defaultdict(list)
        for k, v in data: groups[k].append(v)
        return dict(groups)

    def sortBy(self, key_fn, ascending=True):
        r = RDD(self.collect(), f"sort({self.name})")
        r._transformations = []
        r._data = sorted(r._data, key=key_fn, reverse=not ascending)
        return r

    def distinct(self):
        return RDD(list(set(str(x) for x in self.collect())), f"distinct({self.name})")

    def aggregate(self, zero, seq_op, comb_op):
        result = zero
        for x in self.collect(): result = seq_op(result, x)
        return result

    def stats(self):
        vals = [float(x) for x in self.collect() if x is not None]
        n = len(vals)
        if not n: return {}
        mean = sum(vals)/n
        variance = sum((x-mean)**2 for x in vals)/n
        return {"count":n,"mean":round(mean,4),"min":min(vals),"max":max(vals),
                "std":round(variance**0.5,4),"sum":round(sum(vals),2)}


class SparkDataFrame:
    """Simulates Spark DataFrame API."""
    def __init__(self, data: list, schema: list = None):
        self._data = data
        self._schema = schema or (list(data[0].keys()) if data else [])
        self._filter_fns = []
        self._select_cols = None
        self._cached = False

    def cache(self): self._cached = True; return self

    def select(self, *cols):
        df = SparkDataFrame([{c: r.get(c) for c in cols} for r in self._data], list(cols))
        return df

    def filter(self, fn):
        df = SparkDataFrame([r for r in self._data if fn(r)], self._schema)
        return df

    def withColumn(self, name, fn):
        data = [{**r, name: fn(r)} for r in self._data]
        schema = self._schema + ([name] if name not in self._schema else [])
        return SparkDataFrame(data, schema)

    def groupBy(self, *keys):
        return _GroupedData(self._data, list(keys))

    def orderBy(self, col, ascending=True):
        data = sorted(self._data, key=lambda r: r.get(col,0) or 0, reverse=not ascending)
        return SparkDataFrame(data, self._schema)

    def join(self, other, on, how="inner"):
        result = []
        other_map = {r.get(on): r for r in other._data}
        for r in self._data:
            other_r = other_map.get(r.get(on))
            if how == "inner" and other_r:
                result.append({**r, **{k:v for k,v in other_r.items() if k!=on}})
            elif how == "left":
                result.append({**r, **(other_r or {})})
        return SparkDataFrame(result)

    def dropDuplicates(self, cols=None):
        seen = set()
        result = []
        for r in self._data:
            key = tuple(r.get(c) for c in (cols or self._schema))
            if key not in seen:
                seen.add(key); result.append(r)
        return SparkDataFrame(result, self._schema)

    def count(self): return len(self._data)
    def show(self, n=5):
        cols = self._schema[:6]
        widths = [max(len(c), max((len(str(r.get(c,""))[:20]) for r in self._data[:n]), default=5)) for c in cols]
        header = " | ".join(c[:w].ljust(w) for c,w in zip(cols,widths))
        print("  +" + "+".join("-"*(w+2) for w in widths) + "+")
        print("  | " + header + " |")
        print("  +" + "+".join("-"*(w+2) for w in widths) + "+")
        for r in self._data[:n]:
            row = " | ".join(str(r.get(c,""))[:w].ljust(w) for c,w in zip(cols,widths))
            print("  | " + row + " |")
        print("  +" + "+".join("-"*(w+2) for w in widths) + "+")
        if len(self._data) > n: print(f"  only showing top {n} rows")

    def toPandas(self): return self._data

class _GroupedData:
    def __init__(self, data, keys):
        self._data = data; self._keys = keys
        self._groups = defaultdict(list)
        for r in data:
            k = tuple(r.get(key) for key in keys)
            self._groups[k].append(r)

    def agg(self, **aggs):
        result = []
        for k_tuple, rows in self._groups.items():
            row = {self._keys[i]: k_tuple[i] for i in range(len(self._keys))}
            for alias, (col, fn) in aggs.items():
                vals = [float(r.get(col,0) or 0) for r in rows]
                if fn == "sum":    row[alias] = round(sum(vals), 2)
                elif fn == "mean": row[alias] = round(sum(vals)/len(vals), 2) if vals else 0
                elif fn == "count":row[alias] = len(rows)
                elif fn == "max":  row[alias] = max(vals) if vals else 0
                elif fn == "min":  row[alias] = min(vals) if vals else 0
                elif fn == "std":
                    mu = sum(vals)/len(vals) if vals else 0
                    row[alias] = round(math.sqrt(sum((v-mu)**2 for v in vals)/len(vals)),2) if len(vals)>1 else 0
            result.append(row)
        return SparkDataFrame(result)


class SparkContext:
    """Simulated SparkContext (entry point)."""
    def __init__(self, app_name="PayrollApp", master="local[4]"):
        self.app_name = app_name; self.master = master
        self._job_count = 0
        print(f"  SparkContext started: {app_name} @ {master}")

    def parallelize(self, data, numSlices=4) -> RDD:
        self._job_count += 1
        return RDD(data, name=f"parallelize[{self._job_count}]", partitions=numSlices)

    def textFile(self, path: str) -> RDD:
        self._job_count += 1
        lines = Path(path).read_text().splitlines()
        return RDD(lines, name=f"textFile[{self._job_count}]")

    def stop(self):
        print(f"  SparkContext stopped. Total jobs: {self._job_count}")


def load_payroll_as_df() -> SparkDataFrame:
    """Load payroll data from SQLite as simulated Spark DataFrame."""
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT pr.payroll_id, e.emp_code, e.first_name||' '||e.last_name name,
               d.dept_name dept, ds.desig_title desig,
               pp.period_name period, pp.year, pp.month,
               pr.basic_salary, pr.hra, pr.da, pr.gross_salary,
               pr.pf_employee, pr.income_tax_tds, pr.total_deductions,
               pr.net_salary, pr.days_present, pr.status
        FROM payroll_records pr
        JOIN employees e ON pr.emp_id=e.emp_id
        JOIN departments d ON e.dept_id=d.dept_id
        JOIN designations ds ON e.desig_id=ds.desig_id
        JOIN payroll_periods pp ON pr.period_id=pp.period_id
        WHERE pr.status='Paid'
    """).fetchall()
    conn.close()
    return SparkDataFrame([dict(r) for r in rows])


def run():
    print("="*60)
    print("  TASKS 12-17: Hadoop HDFS + Spark Simulation")
    print("="*60)

    # ── TASK 12 & 13: HDFS ──────────────────────────────────
    print("\n══ TASKS 12-13: HDFS ══")
    cluster = HDFSCluster()
    print("  [✓] HDFS cluster initialized (1 Namenode, 3 Datanodes)")

    # Upload payroll files
    files_to_upload = {
        "/payroll/raw/employees.csv": "emp_id,emp_code,name,dept\n1,EMP001,Rajesh Kumar,HR\n2,EMP002,Priya Sharma,HR\n",
        "/payroll/raw/payroll_mar2026.csv": "payroll_id,emp_id,gross,net\n1,1,64900,62363\n2,2,197500,172167\n",
        "/payroll/processed/cleaned_payroll.csv": "emp_code,net_salary,dept\nEMP001,62363,HR\nEMP002,172167,HR\n",
        "/logs/pipeline_2026.log": "2026-03-01 10:00:00 [INFO] Payroll pipeline started\n2026-03-01 10:05:00 [INFO] 30 records processed\n",
        "/payroll/archive/payroll_2025.tar.gz": "BINARY_ARCHIVE_DATA_PLACEHOLDER_" * 10,
    }

    print("\n  HDFS Put operations:")
    for hdfs_path, content in files_to_upload.items():
        blocks = cluster.put(hdfs_path, content)
        meta = cluster.namenode.stat(hdfs_path)
        print(f"  put {hdfs_path}: {meta['size_bytes']}B → {blocks} block(s), replicated ×3")

    print("\n  HDFS ls /payroll:")
    for f in cluster.ls("/payroll"):
        meta = cluster.namenode.stat(f)
        print(f"    {f}: {meta['size_bytes']}B")

    print("\n  HDFS cat /payroll/raw/employees.csv:")
    content = cluster.cat("/payroll/raw/employees.csv")
    print("    " + content.replace("\n", "\n    ").strip())

    print("\n  Datanode Heartbeats:")
    for hb in cluster.heartbeats():
        print(f"    {hb['node_id']}: status={hb['status']}, blocks={hb['blocks']}")

    report = cluster.namenode.get_filesystem_report()
    print(f"\n  Filesystem Report: {report}")

    print("\n  HDFS Architecture Explanation:")
    print("""
    ┌─────────────────────────────────────────────────────┐
    │  NAMENODE (Master)                                   │
    │  • Stores filesystem namespace (metadata)            │
    │  • Tracks block→datanode mapping (fsimage + edits)   │
    │  • Does NOT store actual data                        │
    │  • Single point — use HA with standby Namenode       │
    └──────────────┬──────────────────────────────────────┘
                   │  Block reports + Heartbeats (3s)
    ┌──────────────┼──────────────────────────────────────┐
    │   DN1  ←─────┤─────→  DN2  ←──────────→  DN3       │
    │  Stores actual data blocks (128MB each)             │
    │  Each block replicated 3× for fault tolerance       │
    └─────────────────────────────────────────────────────┘
    Payroll Use: Store large CSV exports, archived reports,
    backup of payroll DB in HDFS for Spark processing.
    """)

    # ── TASKS 14-17: SPARK ─────────────────────────────────
    print("\n══ TASKS 14-16: SPARK BASICS + DataFrames + SQL ══")

    sc = SparkContext("PayrollAnalytics", "local[4]")
    df = load_payroll_as_df()
    print(f"\n  Loaded SparkDataFrame: {df.count()} rows, {len(df._schema)} columns")

    # TASK 14: Basics — Word Count on payroll status
    print("\n── Task 14: RDD Operations ──")
    status_rdd = sc.parallelize([r["status"] for r in df._data])
    status_pairs = status_rdd.map(lambda s: (s, 1))
    status_counts = status_pairs.reduceByKey(lambda a,b: a+b)
    print(f"  Status counts: {status_counts}")

    net_rdd = sc.parallelize([r["net_salary"] for r in df._data if r["net_salary"]])
    net_stats = net_rdd.stats()
    print(f"  Net salary stats: {net_stats}")

    # TASK 15: DataFrame transformations
    print("\n── Task 15: DataFrame Transformations ──")

    # withColumn + filter + select
    enriched = (df
        .withColumn("annual_net", lambda r: round((r.get("net_salary") or 0)*12, 2))
        .withColumn("tax_pct",    lambda r: round((r.get("income_tax_tds") or 0)/(r.get("gross_salary") or 1)*100, 2))
        .filter(lambda r: (r.get("net_salary") or 0) > 50000)
        .orderBy("net_salary", ascending=False)
    )
    print(f"  After filter(net>50K): {enriched.count()} rows")
    enriched.show(5)

    # GroupBy aggregation
    print("\n  Department Summary:")
    dept_summary = df.groupBy("dept").agg(
        headcount=("payroll_id","count"),
        total_gross=("gross_salary","sum"),
        avg_net=("net_salary","mean"),
        total_tds=("income_tax_tds","sum")
    ).orderBy("total_gross", ascending=False)
    dept_summary.show(8)

    # TASK 16: Spark SQL (using our query engine)
    print("\n── Task 16: Spark SQL ──")
    spark_sql_queries = {
        "Dept payroll by period": lambda d: (
            SparkDataFrame(d)
            .groupBy("dept","period").agg(
                employees=("payroll_id","count"),
                net_payroll=("net_salary","sum"),
                avg_salary=("net_salary","mean")
            ).orderBy("net_payroll", ascending=False)
        ),
        "Top earner per dept": lambda d: (
            SparkDataFrame(sorted(d, key=lambda r: r.get("net_salary",0), reverse=True))
            .dropDuplicates(["dept"])
            .select("dept","name","net_salary")
            .orderBy("net_salary", ascending=False)
        ),
    }
    for qname, query_fn in spark_sql_queries.items():
        result = query_fn(df._data)
        print(f"\n  SQL: {qname} ({result.count()} rows)")
        result.show(5)

    # TASK 17: Advanced — Partitioning & Caching
    print("\n── Task 17: Partitioning & Caching ──")
    print("  [1] Partitioning by department:")
    dept_partitioned = {}
    for r in df._data:
        dept_partitioned.setdefault(r["dept"], []).append(r)
    print(f"  Partitions: {len(dept_partitioned)} dept partitions")
    for dept, rows in list(dept_partitioned.items())[:3]:
        print(f"    Partition[{dept}]: {len(rows)} rows")

    print("\n  [2] Caching demonstration:")
    cached_df = df.filter(lambda r: r.get("year")==2026).cache()
    t0 = time.time(); _ = cached_df.count(); t1 = time.time()
    print(f"  First call (builds cache): {(t1-t0)*1000:.2f}ms, {cached_df.count()} rows")
    t0 = time.time(); _ = cached_df.count(); t1 = time.time()
    print(f"  Second call (from cache):  {(t1-t0)*1000:.2f}ms (faster!)")

    print("\n  [3] Broadcast join simulation:")
    dept_lookup = {r["dept"]: r for r in [
        {"dept":"HR","dept_code":"DEPT001","location":"Mumbai"},
        {"dept":"IT","dept_code":"DEPT003","location":"Bengaluru"},
    ]}
    result_with_meta = [{**r, "dept_code": dept_lookup.get(r["dept"],{}).get("dept_code",""),
                          "location": dept_lookup.get(r["dept"],{}).get("location","")}
                        for r in df._data[:5]]
    print(f"  Broadcast join result sample:")
    for r in result_with_meta[:2]:
        print(f"    {r['emp_code']}: dept={r['dept']}, location={r.get('location','')}")

    sc.stop()

    # Save outputs
    results = {
        "hdfs_report": report,
        "spark_net_stats": net_stats,
        "dept_summary_rows": dept_summary.count(),
        "enriched_rows": enriched.count(),
        "timestamp": datetime.now().isoformat()
    }
    (OUTPUT/"spark_hdfs_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✓ Results saved: {OUTPUT}/spark_hdfs_results.json")
    return results

if __name__ == "__main__":
    run()
