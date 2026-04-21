"""
ER Diagram Generator for Payroll Automation System
Uses matplotlib to render an Entity-Relationship diagram
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


ENTITIES = {
    "departments": {
        "pos": (1.0, 8.5),
        "color": "#1a73e8",
        "attrs": ["PK dept_id", "dept_code", "dept_name", "location", "budget", "is_active"]
    },
    "designations": {
        "pos": (5.5, 8.5),
        "color": "#1a73e8",
        "attrs": ["PK desig_id", "desig_code", "desig_title", "FK dept_id", "level_rank"]
    },
    "salary_grades": {
        "pos": (10.0, 8.5),
        "color": "#0f9d58",
        "attrs": ["PK grade_id", "grade_code", "grade_name", "basic_min", "basic_max",
                  "hra_pct", "da_pct", "ta_flat"]
    },
    "employees": {
        "pos": (5.5, 5.5),
        "color": "#e53935",
        "attrs": ["PK emp_id", "emp_code", "first_name", "last_name", "gender", "dob",
                  "email", "pan_number", "FK dept_id", "FK desig_id", "FK grade_id",
                  "basic_salary", "date_joined", "status"]
    },
    "payroll_periods": {
        "pos": (1.0, 2.5),
        "color": "#6200ea",
        "attrs": ["PK period_id", "period_name", "month", "year",
                  "start_date", "end_date", "working_days", "status"]
    },
    "payroll_records": {
        "pos": (5.5, 2.5),
        "color": "#e53935",
        "attrs": ["PK payroll_id", "FK emp_id", "FK period_id", "basic_salary",
                  "hra", "da", "gross_salary", "pf_employee", "income_tax_tds",
                  "total_deductions", "net_salary", "status"]
    },
    "attendance": {
        "pos": (10.0, 5.5),
        "color": "#f57c00",
        "attrs": ["PK att_id", "FK emp_id", "att_date", "check_in",
                  "check_out", "hours_worked", "status"]
    },
    "leave_requests": {
        "pos": (10.0, 2.5),
        "color": "#f57c00",
        "attrs": ["PK leave_id", "FK emp_id", "FK leave_type_id",
                  "start_date", "end_date", "days_requested", "status"]
    },
    "leave_types": {
        "pos": (13.5, 2.5),
        "color": "#00838f",
        "attrs": ["PK leave_type_id", "leave_code", "leave_name",
                  "max_days_year", "is_paid"]
    },
    "deduction_types": {
        "pos": (1.0, 5.5),
        "color": "#00838f",
        "attrs": ["PK deduction_type_id", "deduction_code", "deduction_name",
                  "is_percentage", "default_value"]
    },
    "tax_slabs": {
        "pos": (13.5, 5.5),
        "color": "#0f9d58",
        "attrs": ["PK slab_id", "fiscal_year", "income_from",
                  "income_to", "tax_rate_pct"]
    },
    "employee_loans": {
        "pos": (13.5, 8.5),
        "color": "#6200ea",
        "attrs": ["PK loan_id", "FK emp_id", "loan_amount",
                  "emi_amount", "outstanding", "status"]
    },
    "salary_revisions": {
        "pos": (1.0, 0.0),
        "color": "#5d4037",
        "attrs": ["PK revision_id", "FK emp_id", "old_basic",
                  "new_basic", "effective_date", "reason"]
    },
    "audit_logs": {
        "pos": (5.5, 0.0),
        "color": "#546e7a",
        "attrs": ["PK log_id", "table_name", "record_id",
                  "action", "performed_at"]
    },
    "payroll_deductions": {
        "pos": (10.0, 0.0),
        "color": "#546e7a",
        "attrs": ["PK ded_detail_id", "FK payroll_id",
                  "FK deduction_type_id", "amount"]
    },
}

RELATIONSHIPS = [
    ("departments",    "designations",      "1:N"),
    ("departments",    "employees",         "1:N"),
    ("designations",   "employees",         "1:N"),
    ("salary_grades",  "employees",         "1:N"),
    ("employees",      "payroll_records",   "1:N"),
    ("employees",      "attendance",        "1:N"),
    ("employees",      "leave_requests",    "1:N"),
    ("employees",      "employee_loans",    "1:N"),
    ("employees",      "salary_revisions",  "1:N"),
    ("payroll_periods","payroll_records",   "1:N"),
    ("payroll_records","payroll_deductions","1:N"),
    ("deduction_types","payroll_deductions","1:N"),
    ("leave_types",    "leave_requests",    "1:N"),
]


def generate_er_diagram(output_path: str = None) -> str:
    if not HAS_MPL:
        return "matplotlib not installed. Run: pip install matplotlib"

    if output_path is None:
        output_path = os.path.join(BASE_DIR, "diagrams", "er_diagram.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(22, 14))
    ax.set_xlim(-0.5, 16.5)
    ax.set_ylim(-1.2, 11.0)
    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("#f0f2f5")
    ax.axis("off")

    # Draw title
    ax.text(8, 10.6, "PAYROLL AUTOMATION SYSTEM — ER DIAGRAM",
            ha="center", va="center", fontsize=16, fontweight="bold",
            color="#1a1a2e",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#dde3f0", edgecolor="#1a73e8", linewidth=2))

    ax.text(8, 10.2, "15 Entities | 13 Relationships | Normalized to 3NF",
            ha="center", va="center", fontsize=9, color="#555")

    entity_centers = {}

    for name, info in ENTITIES.items():
        x, y = info["pos"]
        color = info["color"]
        attrs = info["attrs"]
        box_h = 0.28 * (len(attrs) + 1.5)
        box_w = 2.8

        # Shadow
        shadow = FancyBboxPatch((x - box_w/2 + 0.05, y - box_h - 0.05),
                                 box_w, box_h,
                                 boxstyle="round,pad=0.05",
                                 linewidth=0, facecolor="#00000022")
        ax.add_patch(shadow)

        # Entity box
        box = FancyBboxPatch((x - box_w/2, y - box_h),
                              box_w, box_h,
                              boxstyle="round,pad=0.05",
                              linewidth=1.5, edgecolor=color,
                              facecolor="white")
        ax.add_patch(box)

        # Header
        header = FancyBboxPatch((x - box_w/2, y - 0.3),
                                 box_w, 0.3,
                                 boxstyle="round,pad=0.02",
                                 linewidth=0, facecolor=color)
        ax.add_patch(header)

        ax.text(x, y - 0.15, name.upper().replace("_", " "),
                ha="center", va="center", fontsize=6.5, fontweight="bold",
                color="white")

        for j, attr in enumerate(attrs):
            ay = y - 0.42 - j * 0.26
            is_pk = attr.startswith("PK ")
            is_fk = attr.startswith("FK ")
            disp  = attr[3:] if (is_pk or is_fk) else attr
            prefix = "🔑" if is_pk else ("🔗" if is_fk else "  ")
            fc = "#fff9c4" if is_pk else ("#e3f2fd" if is_fk else "white")

            if is_pk or is_fk:
                ax.add_patch(FancyBboxPatch(
                    (x - box_w/2 + 0.05, ay - 0.10),
                    box_w - 0.1, 0.22,
                    boxstyle="round,pad=0.01",
                    linewidth=0, facecolor=fc
                ))

            ax.text(x - box_w/2 + 0.18, ay,
                    f"{'PK' if is_pk else 'FK' if is_fk else '  '} {disp}",
                    ha="left", va="center", fontsize=5.5,
                    color="#b71c1c" if is_pk else ("#0d47a1" if is_fk else "#333"),
                    fontweight="bold" if (is_pk or is_fk) else "normal")

        entity_centers[name] = (x, y - box_h / 2)

    # Draw relationships
    for src, tgt, card in RELATIONSHIPS:
        if src not in entity_centers or tgt not in entity_centers:
            continue
        sx, sy = entity_centers[src]
        tx, ty = entity_centers[tgt]
        ax.annotate("",
            xy=(tx, ty), xytext=(sx, sy),
            arrowprops=dict(
                arrowstyle="-|>",
                color="#78909c",
                lw=1.2,
                connectionstyle="arc3,rad=0.05"
            ))
        mx, my = (sx + tx) / 2, (sy + ty) / 2
        ax.text(mx, my + 0.12, card,
                ha="center", va="center", fontsize=5.5,
                color="#37474f",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", edgecolor="#ccc", alpha=0.9))

    # Legend
    legend_items = [
        mpatches.Patch(facecolor="#e53935", label="Core Entities"),
        mpatches.Patch(facecolor="#1a73e8", label="Org Structure"),
        mpatches.Patch(facecolor="#0f9d58", label="Financial"),
        mpatches.Patch(facecolor="#6200ea", label="Payroll Periods & Loans"),
        mpatches.Patch(facecolor="#f57c00", label="Attendance & Leave"),
        mpatches.Patch(facecolor="#00838f", label="Lookup Tables"),
        mpatches.Patch(facecolor="#546e7a", label="Audit & Detail"),
    ]
    ax.legend(handles=legend_items, loc="lower right",
              fontsize=7, title="Entity Categories",
              title_fontsize=8, framealpha=0.95)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()

    return output_path


if __name__ == "__main__":
    path = generate_er_diagram()
    print(f"[✓] ER Diagram saved to: {path}")
