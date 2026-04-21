"""
TASK 05: Pandas + NumPy — Large-Scale Data Analysis (1M+ rows)
Memory optimization, vectorized operations, performance benchmarks.
"""
import numpy as np
import pandas as pd
import time, gc, json, os
from pathlib import Path
from datetime import datetime, timedelta
import random

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(exist_ok=True)

# ── 1. Generate 1M+ Row Dataset ───────────────────────────────
def generate_large_dataset(n_rows: int = 1_200_000) -> str:
    """Generate synthetic payroll dataset with 1M+ rows."""
    print(f"  Generating {n_rows:,} row payroll dataset...")
    np.random.seed(42)
    rng = np.random.default_rng(42)

    depts = ["IT","HR","Finance","Sales","Ops","R&D","Support","Analytics","Legal","Cloud"]
    grades = ["G1","G2","G3","G4","G5","G6","G7","G8","G9","G10"]
    statuses = ["Active","Active","Active","Active","Inactive","Terminated"]

    # Vectorized generation using NumPy
    emp_ids  = np.arange(1, n_rows + 1)
    dept_idx = rng.integers(0, len(depts), n_rows)
    grade_idx= rng.integers(0, len(grades), n_rows)
    status_idx=rng.integers(0, len(statuses), n_rows)

    basic_by_grade = np.array([20000,30000,45000,65000,90000,130000,175000,225000,300000,420000])
    basic = basic_by_grade[grade_idx] * rng.uniform(0.85, 1.15, n_rows)
    hra   = basic * rng.uniform(0.35, 0.45, n_rows)
    da    = basic * rng.uniform(0.15, 0.25, n_rows)
    ta    = rng.choice([800,1200,1500,2000,2500,3000,5000], n_rows)
    gross = basic + hra + da + ta

    pf   = np.minimum(basic, 15000) * 0.12
    esi  = np.where(gross <= 21000, gross * 0.0075, 0)
    pt   = np.where(gross > 10000, 200, 0)
    tds  = np.where(gross * 12 > 500000, (gross * 12 - 500000) * 0.05 / 12, 0)
    total_ded = pf + esi + pt + tds
    net = gross - total_ded

    years = rng.integers(2018, 2026, n_rows)
    months= rng.integers(1, 13, n_rows)
    days  = rng.integers(20, 28, n_rows)
    days_present = rng.integers(18, 27, n_rows)

    df = pd.DataFrame({
        "emp_id":       emp_ids.astype(np.int32),
        "dept":         pd.Categorical([depts[i] for i in dept_idx]),
        "grade":        pd.Categorical([grades[i] for i in grade_idx]),
        "status":       pd.Categorical([statuses[i] for i in status_idx]),
        "year":         years.astype(np.int16),
        "month":        months.astype(np.int8),
        "days_present": days_present.astype(np.int8),
        "basic":        basic.round(2).astype(np.float32),
        "hra":          hra.round(2).astype(np.float32),
        "da":           da.round(2).astype(np.float32),
        "ta":           ta.astype(np.float32),
        "gross":        gross.round(2).astype(np.float32),
        "pf":           pf.round(2).astype(np.float32),
        "esi":          esi.round(2).astype(np.float32),
        "tds":          tds.round(2).astype(np.float32),
        "net":          net.round(2).astype(np.float32),
    })

    csv_path = OUTPUT / "payroll_large.csv"
    df.to_csv(csv_path, index=False)
    size_mb = csv_path.stat().st_size / 1024 / 1024
    print(f"  Saved: {csv_path.name} ({size_mb:.1f} MB, {n_rows:,} rows, {len(df.columns)} cols)")
    return str(csv_path)

# ── 2. Memory Comparison ──────────────────────────────────────
def compare_memory_usage(csv_path: str):
    print("\n  [A] Default dtypes (no optimization):")
    t0 = time.time()
    df_default = pd.read_csv(csv_path)
    t1 = time.time()
    mem_default = df_default.memory_usage(deep=True).sum() / 1024**2
    print(f"    Load time : {t1-t0:.2f}s")
    print(f"    Memory    : {mem_default:.1f} MB")
    print(f"    Dtypes    : {dict(df_default.dtypes.value_counts())}")

    print("\n  [B] Optimized dtypes:")
    t0 = time.time()
    dtypes = {
        "emp_id":       np.int32,
        "year":         np.int16,
        "month":        np.int8,
        "days_present": np.int8,
        "basic":        np.float32,
        "hra":          np.float32,
        "da":           np.float32,
        "ta":           np.float32,
        "gross":        np.float32,
        "pf":           np.float32,
        "esi":          np.float32,
        "tds":          np.float32,
        "net":          np.float32,
    }
    df_opt = pd.read_csv(csv_path, dtype=dtypes)
    df_opt["dept"]   = pd.Categorical(df_opt["dept"])
    df_opt["grade"]  = pd.Categorical(df_opt["grade"])
    df_opt["status"] = pd.Categorical(df_opt["status"])
    t1 = time.time()
    mem_opt = df_opt.memory_usage(deep=True).sum() / 1024**2
    print(f"    Load time : {t1-t0:.2f}s")
    print(f"    Memory    : {mem_opt:.1f} MB")
    print(f"    Reduction : {(1 - mem_opt/mem_default)*100:.1f}%")

    print("\n  [C] Chunked processing (10 chunks of 120K each):")
    t0 = time.time()
    chunk_totals = []
    for chunk in pd.read_csv(csv_path, chunksize=120_000):
        chunk_totals.append(chunk["net"].sum())
    t1 = time.time()
    print(f"    Chunk time: {t1-t0:.2f}s | Total net: ₹{sum(chunk_totals):,.0f}")

    return df_opt

# ── 3. Large-Scale Analysis ───────────────────────────────────
def run_analysis(df: pd.DataFrame):
    results = {}

    print("\n  [1] Department-wise Payroll Summary:")
    t0 = time.time()
    dept_summary = df.groupby("dept", observed=True).agg(
        headcount=("emp_id","count"),
        avg_basic=("basic","mean"),
        avg_gross=("gross","mean"),
        total_net=("net","sum"),
        avg_net=("net","mean"),
        total_tds=("tds","sum"),
        median_net=("net","median"),
    ).round(2)
    print(f"    Computed in {time.time()-t0:.3f}s")
    print(dept_summary.to_string())
    results["dept_summary"] = dept_summary.reset_index().to_dict(orient="records")

    print("\n  [2] Grade Distribution (Net Salary Percentiles):")
    t0 = time.time()
    grade_pct = df.groupby("grade", observed=True)["net"].describe(
        percentiles=[.25,.5,.75,.9,.95])
    print(f"    Computed in {time.time()-t0:.3f}s")
    print(grade_pct[["count","mean","25%","50%","75%","95%"]].round(2).to_string())

    print("\n  [3] Yearly Payroll Trend:")
    t0 = time.time()
    yearly = df.groupby("year", observed=True).agg(
        total_gross=("gross","sum"),
        total_net=("net","sum"),
        headcount=("emp_id","count"),
        avg_salary=("net","mean")
    ).round(2)
    print(f"    Computed in {time.time()-t0:.3f}s")
    print(yearly.to_string())

    print("\n  [4] NumPy Vectorized Stats (faster than pandas for pure math):")
    t0 = time.time()
    net_arr = df["net"].to_numpy()
    gini = _gini_coefficient(net_arr)
    print(f"    Time: {time.time()-t0:.3f}s")
    print(f"    Net Mean   : ₹{net_arr.mean():,.2f}")
    print(f"    Net Std Dev: ₹{net_arr.std():,.2f}")
    print(f"    Skewness   : {_skewness(net_arr):.4f} (positive=right-tailed)")
    print(f"    Gini Coeff : {gini:.4f} (salary inequality, 0=equal, 1=max unequal)")
    print(f"    Kurtosis   : {_kurtosis(net_arr):.4f}")

    print("\n  [5] Anomaly Detection (salary outliers):")
    t0 = time.time()
    mean, std = net_arr.mean(), net_arr.std()
    z_scores = np.abs((net_arr - mean) / std)
    outliers = df[z_scores > 3]
    print(f"    Time: {time.time()-t0:.3f}s")
    print(f"    Z-score > 3 outliers: {len(outliers):,} ({len(outliers)/len(df)*100:.2f}%)")
    print(f"    Max outlier net: ₹{outliers['net'].max():,.2f}")

    print("\n  [6] Department × Year Cross-tab (pivot):")
    t0 = time.time()
    pivot = df.pivot_table(
        values="net", index="dept", columns="year",
        aggfunc="sum", observed=True
    ).round(0)
    print(f"    Computed in {time.time()-t0:.3f}s | Shape: {pivot.shape}")
    print(pivot.to_string())

    results["yearly"] = yearly.reset_index().to_dict(orient="records")
    return results

# ── NumPy Statistical Functions ───────────────────────────────
def _gini_coefficient(arr: np.ndarray) -> float:
    sorted_arr = np.sort(arr)
    n = len(sorted_arr)
    cumsum = np.cumsum(sorted_arr)
    return float((n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n)

def _skewness(arr: np.ndarray) -> float:
    mu = arr.mean(); sigma = arr.std()
    return float(np.mean(((arr - mu) / sigma) ** 3))

def _kurtosis(arr: np.ndarray) -> float:
    mu = arr.mean(); sigma = arr.std()
    return float(np.mean(((arr - mu) / sigma) ** 4) - 3)

# ── 4. Performance Benchmark ──────────────────────────────────
def performance_benchmark(df: pd.DataFrame):
    print("\n  Performance Benchmarks:")
    benchmarks = {}

    ops = {
        "GroupBy dept sum":     lambda: df.groupby("dept", observed=True)["net"].sum(),
        "Filter Active status": lambda: df[df["status"] == "Active"],
        "Sort by gross desc":   lambda: df.sort_values("gross", ascending=False),
        "Vectorized: net*1.05": lambda: df["net"] * 1.05,
        "NumPy mean(net)":      lambda: np.mean(df["net"].values),
        "Rolling mean(50)":     lambda: df["net"].rolling(50).mean(),
        "Merge on emp_id":      lambda: df.merge(df[["emp_id","dept"]].drop_duplicates(),on="emp_id",how="left"),
    }

    for name, op in ops.items():
        gc.collect()
        t0 = time.time()
        result = op()
        elapsed = (time.time() - t0) * 1000
        benchmarks[name] = round(elapsed, 2)
        print(f"    {name:<35}: {elapsed:>8.2f} ms")

    return benchmarks

def run():
    print("="*60)
    print("  TASK 05: Pandas + NumPy — 1M+ Row Analysis")
    print("="*60)

    print("\n[1] Generating large dataset...")
    csv_path = generate_large_dataset(1_200_000)

    print("\n[2] Memory Usage Comparison...")
    df = compare_memory_usage(csv_path)

    print("\n[3] Large-Scale Analysis...")
    analysis = run_analysis(df)

    print("\n[4] Performance Benchmarks...")
    benchmarks = performance_benchmark(df)

    # Save outputs
    summary = {
        "dataset_rows": len(df),
        "dataset_cols": len(df.columns),
        "memory_mb_optimized": round(df.memory_usage(deep=True).sum()/1024**2, 2),
        "benchmarks_ms": benchmarks,
        "global_stats": {
            "total_net_payroll": float(df["net"].sum()),
            "avg_net_salary": float(df["net"].mean()),
            "min_net": float(df["net"].min()),
            "max_net": float(df["net"].max()),
            "gini_index": round(_gini_coefficient(df["net"].values), 4)
        }
    }
    (OUTPUT/"analysis_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"\n✓ Analysis saved: {OUTPUT}/analysis_summary.json")
    return df, analysis

if __name__ == "__main__":
    run()
