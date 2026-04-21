"""
TASK 04: Advanced Python — Reusable Data Transformation Modules
Normalization, Aggregation, and Validation functions for Payroll.
"""
import math, re, json, statistics
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, date
from functools import wraps
from collections import defaultdict

# ════════════════════════════════════════════════════════════════
#  MODULE 1: NORMALIZATION
# ════════════════════════════════════════════════════════════════
class Normalizer:
    """Min-max, z-score, decimal scaling, and log normalization."""

    @staticmethod
    def min_max(values: List[float], feature_range=(0, 1)) -> List[float]:
        """Scale to [a, b] range."""
        lo, hi = min(values), max(values)
        a, b = feature_range
        if lo == hi: return [a] * len(values)
        return [round(a + (v - lo) * (b - a) / (hi - lo), 6) for v in values]

    @staticmethod
    def z_score(values: List[float]) -> List[float]:
        """Standardize to mean=0, std=1."""
        mu = statistics.mean(values)
        sigma = statistics.stdev(values) if len(values) > 1 else 1
        if sigma == 0: return [0.0] * len(values)
        return [round((v - mu) / sigma, 6) for v in values]

    @staticmethod
    def decimal_scaling(values: List[float]) -> List[float]:
        """Scale by dividing by 10^j where j makes max|v|<1."""
        max_abs = max(abs(v) for v in values)
        j = math.ceil(math.log10(max_abs + 1))
        scale = 10 ** j
        return [round(v / scale, 6) for v in values]

    @staticmethod
    def log_normalize(values: List[float]) -> List[float]:
        """Log normalization (for skewed salary distributions)."""
        return [round(math.log1p(max(v, 0)), 6) for v in values]

    @classmethod
    def normalize_payroll_field(cls, records: List[Dict], field: str,
                                 method: str = "min_max") -> List[Dict]:
        """Normalize a numeric field across all records in-place."""
        values = [float(r.get(field, 0) or 0) for r in records]
        methods = {"min_max": cls.min_max, "z_score": cls.z_score,
                   "decimal": cls.decimal_scaling, "log": cls.log_normalize}
        normalized = methods[method](values)
        for r, n in zip(records, normalized):
            r[f"{field}_norm_{method}"] = n
        return records


# ════════════════════════════════════════════════════════════════
#  MODULE 2: AGGREGATION
# ════════════════════════════════════════════════════════════════
class Aggregator:
    """Group-by aggregation with multiple functions."""

    FUNCS: Dict[str, Callable] = {
        "sum":    sum,
        "count":  len,
        "mean":   statistics.mean,
        "median": statistics.median,
        "min":    min,
        "max":    max,
        "std":    lambda x: statistics.stdev(x) if len(x) > 1 else 0,
        "range":  lambda x: max(x) - min(x),
        "pct_25": lambda x: sorted(x)[len(x)//4],
        "pct_75": lambda x: sorted(x)[3*len(x)//4],
    }

    @classmethod
    def group_by(cls, records: List[Dict], group_key: str,
                  agg_fields: Dict[str, List[str]]) -> List[Dict]:
        """
        Group records by key and apply aggregation functions.
        agg_fields = {"net_salary": ["sum","mean","max"], "days_present": ["mean"]}
        """
        groups: Dict[Any, List[Dict]] = defaultdict(list)
        for r in records:
            groups[r.get(group_key, "Unknown")].append(r)

        result = []
        for key, grp in sorted(groups.items()):
            row = {group_key: key, "record_count": len(grp)}
            for field, funcs in agg_fields.items():
                vals = [float(r.get(field, 0) or 0) for r in grp]
                for fn in funcs:
                    if fn in cls.FUNCS and vals:
                        try:
                            row[f"{field}_{fn}"] = round(cls.FUNCS[fn](vals), 2)
                        except Exception:
                            row[f"{field}_{fn}"] = None
            result.append(row)
        return result

    @staticmethod
    def pivot_table(records: List[Dict], index: str, columns: str,
                    values: str, aggfunc: str = "sum") -> Dict:
        """Create a pivot table."""
        func = Aggregator.FUNCS.get(aggfunc, sum)
        data: Dict[Any, Dict[Any, List]] = defaultdict(lambda: defaultdict(list))
        for r in records:
            data[r.get(index)][r.get(columns)].append(float(r.get(values, 0) or 0))
        all_cols = sorted({r.get(columns) for r in records})
        result = {}
        for row_key, col_data in data.items():
            result[row_key] = {col: round(func(col_data[col]), 2)
                                if col_data[col] else 0 for col in all_cols}
        return result

    @staticmethod
    def running_total(records: List[Dict], value_field: str,
                       label_field: str = "") -> List[Dict]:
        """Add running total column."""
        total = 0
        for r in records:
            total += float(r.get(value_field, 0) or 0)
            r[f"{value_field}_cumulative"] = round(total, 2)
        return records

    @staticmethod
    def percent_of_total(records: List[Dict], value_field: str) -> List[Dict]:
        """Add % of total column."""
        total = sum(float(r.get(value_field, 0) or 0) for r in records) or 1
        for r in records:
            pct = float(r.get(value_field, 0) or 0) / total * 100
            r[f"{value_field}_pct_of_total"] = round(pct, 2)
        return records


# ════════════════════════════════════════════════════════════════
#  MODULE 3: VALIDATION
# ════════════════════════════════════════════════════════════════
class ValidationError(Exception):
    def __init__(self, field, value, message):
        self.field = field; self.value = value; self.message = message
        super().__init__(f"[{field}] {message} (got: {value!r})")

class Validator:
    """Reusable validation rules for payroll data."""

    @staticmethod
    def required(value: Any, field: str = "field") -> Any:
        if value is None or str(value).strip() == "":
            raise ValidationError(field, value, "Required field is empty")
        return value

    @staticmethod
    def positive_number(value: Any, field: str = "field") -> float:
        try:
            n = float(value)
        except (TypeError, ValueError):
            raise ValidationError(field, value, "Must be a number")
        if n < 0:
            raise ValidationError(field, value, "Must be positive")
        return n

    @staticmethod
    def in_range(value: Any, lo: float, hi: float, field: str = "field") -> float:
        n = Validator.positive_number(value, field)
        if not (lo <= n <= hi):
            raise ValidationError(field, value, f"Must be between {lo} and {hi}")
        return n

    @staticmethod
    def pan_number(value: str, field: str = "pan") -> str:
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
        if not re.match(pattern, str(value).upper()):
            raise ValidationError(field, value, "Invalid PAN format (ABCDE1234F)")
        return str(value).upper()

    @staticmethod
    def email(value: str, field: str = "email") -> str:
        pattern = r'^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, str(value)):
            raise ValidationError(field, value, "Invalid email format")
        return str(value).lower()

    @staticmethod
    def date_format(value: str, fmt: str = "%Y-%m-%d", field: str = "date") -> date:
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            raise ValidationError(field, value, f"Invalid date format (expected {fmt})")

    @staticmethod
    def enum(value: Any, choices: List[Any], field: str = "field") -> Any:
        if value not in choices:
            raise ValidationError(field, value, f"Must be one of: {choices}")
        return value

    @staticmethod
    def salary_consistency(basic: float, gross: float, field: str = "salary") -> bool:
        """Gross should be 1.3x-2.5x of basic."""
        if basic <= 0: return True
        ratio = gross / basic
        if not (1.0 <= ratio <= 3.0):
            raise ValidationError(field, gross,
                f"Gross/Basic ratio {ratio:.2f} unusual (expected 1.0-3.0)")
        return True

class PayrollValidator:
    """Validate a complete payroll record."""

    REQUIRED_FIELDS = ["emp_id", "emp_code", "basic", "gross", "net", "period"]
    VALID_STATUSES  = ["Draft", "Approved", "Paid", "Cancelled", "Revised"]
    VALID_GENDERS   = ["Male", "Female", "Other"]

    @classmethod
    def validate_record(cls, record: Dict) -> Tuple[bool, List[str]]:
        errors = []
        for field in cls.REQUIRED_FIELDS:
            try:
                Validator.required(record.get(field), field)
            except ValidationError as e:
                errors.append(str(e))

        # Numeric checks
        for f in ["basic", "gross", "net"]:
            try:
                Validator.positive_number(record.get(f, 0), f)
            except ValidationError as e:
                errors.append(str(e))

        # Salary consistency
        try:
            basic = float(record.get("basic", 0))
            gross = float(record.get("gross", 0))
            Validator.salary_consistency(basic, gross)
        except ValidationError as e:
            errors.append(str(e))

        # Net ≤ Gross
        try:
            net = float(record.get("net", 0))
            gross = float(record.get("gross", 0))
            if net > gross:
                errors.append(f"[net] Net ({net}) cannot exceed Gross ({gross})")
        except (TypeError, ValueError):
            pass

        return len(errors) == 0, errors

    @classmethod
    def validate_batch(cls, records: List[Dict]) -> Dict:
        valid, invalid = [], []
        for r in records:
            ok, errs = cls.validate_record(r)
            if ok: valid.append(r)
            else:  invalid.append({**r, "_errors": errs})
        return {"valid": valid, "invalid": invalid,
                "total": len(records), "pass_rate": round(len(valid)/len(records)*100,1)}


# ════════════════════════════════════════════════════════════════
#  MODULE 4: DECORATORS & UTILITIES
# ════════════════════════════════════════════════════════════════
def timed(fn):
    """Measure execution time."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = datetime.now()
        result = fn(*args, **kwargs)
        elapsed = (datetime.now() - start).total_seconds()
        print(f"  [{fn.__name__}] completed in {elapsed:.4f}s")
        return result
    return wrapper

def cached(fn):
    """Simple in-memory cache."""
    _cache = {}
    @wraps(fn)
    def wrapper(*args):
        if args not in _cache:
            _cache[args] = fn(*args)
        return _cache[args]
    return wrapper

def chunked(iterable, size: int):
    """Split a list into chunks of given size."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i+size]

def flatten(nested: List[List]) -> List:
    """Flatten nested list."""
    return [item for sub in nested for item in sub]

def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ════════════════════════════════════════════════════════════════
#  DEMO / RUNNER
# ════════════════════════════════════════════════════════════════
SAMPLE_RECORDS = [
    {"emp_id":1,"emp_code":"EMP001","dept":"HR","period":"Jan-2026",
     "basic":45000,"hra":13500,"da":7650,"gross":67650,"pf":1800,"tds":0,"net":65850,"status":"Paid","days_present":25},
    {"emp_id":2,"emp_code":"EMP002","dept":"HR","period":"Jan-2026",
     "basic":125000,"hra":50000,"da":22500,"gross":202500,"pf":1800,"tds":25500,"net":175200,"status":"Paid","days_present":27},
    {"emp_id":3,"emp_code":"EMP003","dept":"IT","period":"Jan-2026",
     "basic":65000,"hra":19500,"da":11050,"gross":96850,"pf":1800,"tds":5600,"net":89450,"status":"Paid","days_present":26},
    {"emp_id":4,"emp_code":"EMP004","dept":"Support","period":"Jan-2026",
     "basic":30000,"hra":3000,"da":4500,"gross":37500,"pf":1800,"tds":0,"net":35700,"status":"Paid","days_present":27},
    {"emp_id":5,"emp_code":"EMP005","dept":"Sales","period":"Jan-2026",
     "basic":38000,"hra":7600,"da":6460,"gross":53460,"pf":1800,"tds":0,"net":51660,"status":"Paid","days_present":25},
    {"emp_id":6,"emp_code":"EMP006","dept":"Finance","period":"Jan-2026",
     "basic":28000,"hra":2800,"da":4200,"gross":34200,"pf":1800,"tds":0,"net":32400,"status":"Paid","days_present":24},
    {"emp_id":7,"emp_code":"EMP007","dept":"IT","period":"Jan-2026",
     "basic":88000,"hra":33440,"da":15840,"gross":137920,"pf":1800,"tds":5200,"net":130920,"status":"Paid","days_present":27},
    {"emp_id":8,"emp_code":"EMP008","dept":"Analytics","period":"Jan-2026",
     "basic":72000,"hra":21600,"da":12240,"gross":107640,"pf":1800,"tds":3500,"net":102340,"status":"Paid","days_present":26},
    {"emp_id":9,"emp_code":"EMP009","dept":"Ops","period":"Jan-2026",
     "basic":44000,"hra":13200,"da":7480,"gross":65000,"pf":1800,"tds":0,"net":63200,"status":"Paid","days_present":20},
    {"emp_id":10,"emp_code":"EMP010","dept":"R&D","period":"Jan-2026",
     "basic":95000,"hra":38000,"da":17100,"gross":151300,"pf":1800,"tds":14400,"net":135100,"status":"Paid","days_present":27},
]

@timed
def run():
    print("="*60)
    print("  TASK 04: Advanced Python — Reusable Modules")
    print("="*60)

    # ── 1. Normalization ──────────────────────────────────────
    print("\n[1] NORMALIZATION")
    salaries = [r["basic"] for r in SAMPLE_RECORDS]
    mm  = Normalizer.min_max(salaries)
    zs  = Normalizer.z_score(salaries)
    log = Normalizer.log_normalize(salaries)
    print(f"  {'EMP':<8} {'Basic':>10} {'Min-Max':>10} {'Z-Score':>10} {'Log':>10}")
    print("  " + "-"*50)
    for r, m, z, lg in zip(SAMPLE_RECORDS, mm, zs, log):
        print(f"  {r['emp_code']:<8} {r['basic']:>10,.0f} {m:>10.4f} {z:>10.4f} {lg:>10.4f}")

    # ── 2. Aggregation ────────────────────────────────────────
    print("\n[2] AGGREGATION — Group by Department")
    dept_agg = Aggregator.group_by(
        SAMPLE_RECORDS, "dept",
        {"net":  ["sum","mean","max","min"],
         "basic":["mean","std"],
         "days_present":["mean"]}
    )
    print(f"  {'Dept':<12} {'Count':>5} {'Net Sum':>12} {'Net Avg':>12} {'Basic Avg':>12}")
    print("  " + "-"*58)
    for d in dept_agg:
        print(f"  {d['dept']:<12} {d['record_count']:>5} "
              f"{d.get('net_sum',0):>12,.2f} {d.get('net_mean',0):>12,.2f} "
              f"{d.get('basic_mean',0):>12,.2f}")

    print("\n  Running Total (sorted by net):")
    sorted_recs = sorted(SAMPLE_RECORDS, key=lambda x: x["net"], reverse=True)
    Aggregator.running_total(sorted_recs, "net")
    Aggregator.percent_of_total(sorted_recs, "net")
    for r in sorted_recs[:5]:
        print(f"    {r['emp_code']}: net=₹{r['net']:,.0f} | "
              f"cumulative=₹{r['net_cumulative']:,.0f} | "
              f"share={r['net_pct_of_total']}%")

    # ── 3. Validation ─────────────────────────────────────────
    print("\n[3] VALIDATION")
    # Valid records
    result = PayrollValidator.validate_batch(SAMPLE_RECORDS)
    print(f"  Batch: {result['total']} records, Pass rate: {result['pass_rate']}%")
    print(f"  Valid: {len(result['valid'])} | Invalid: {len(result['invalid'])}")

    # Intentionally bad records
    bad = [
        {"emp_id":"","emp_code":"","basic":-5000,"gross":50000,"net":55000,"period":"Jan-2026"},
        {"emp_id":99,"emp_code":"EMP099","basic":40000,"gross":35000,"net":38000,"period":""},
    ]
    bad_result = PayrollValidator.validate_batch(bad)
    print(f"\n  Bad records test ({len(bad)} records):")
    for r in bad_result["invalid"]:
        print(f"    • {r['emp_code'] or 'EMPTY'}: {'; '.join(r['_errors'])}")

    # Field validators
    print("\n  Individual field tests:")
    tests = [
        ("PAN", lambda: Validator.pan_number("AABPK1234C"), True),
        ("PAN bad", lambda: Validator.pan_number("INVALID"), False),
        ("Email", lambda: Validator.email("priya@payrollwise.in"), True),
        ("Email bad", lambda: Validator.email("not-an-email"), False),
        ("Range", lambda: Validator.in_range(45000, 10000, 500000, "salary"), True),
        ("Range out", lambda: Validator.in_range(9999, 10000, 500000, "salary"), False),
    ]
    for name, fn, should_pass in tests:
        try:
            fn()
            status = "✓ PASS" if should_pass else "✗ UNEXPECTED PASS"
        except ValidationError as e:
            status = "✗ FAIL" if should_pass else f"✓ Correctly rejected: {e.message}"
        print(f"    {name:15}: {status}")

    # ── 4. Utilities ──────────────────────────────────────────
    print("\n[4] UTILITIES")
    chunks = list(chunked(SAMPLE_RECORDS, 3))
    print(f"  chunked(10 records, size=3) → {len(chunks)} chunks: {[len(c) for c in chunks]}")
    flat = flatten([[1,2],[3,4],[5]])
    print(f"  flatten([[1,2],[3,4],[5]]) → {flat}")
    merged = deep_merge({"a":1,"b":{"x":10}}, {"b":{"y":20},"c":3})
    print(f"  deep_merge → {merged}")

    # Save results
    out = Path(__file__).parent / "output"
    out.mkdir(exist_ok=True)
    (out/"normalization_results.json").write_text(
        json.dumps({"min_max":mm,"z_score":zs,"log":log}, indent=2))
    (out/"dept_aggregation.json").write_text(
        json.dumps(dept_agg, indent=2))
    (out/"validation_report.json").write_text(
        json.dumps(result, indent=2, default=str))
    print(f"\n✓ Results saved to {out}/")

if __name__ == "__main__":
    run()
