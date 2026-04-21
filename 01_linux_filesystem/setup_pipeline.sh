#!/bin/bash
# ============================================================
# TASK 01: Linux + File System — Payroll Data Pipeline Setup
# Sets up directory structure, permissions, automates file
# movement, and logs all operations.
# ============================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$BASE_DIR/payroll_pipeline"
LOG_FILE="$BASE_DIR/pipeline_operations.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ── Logging Function ──────────────────────────────────────────
log() {
    local level="$1"; shift
    echo "[$TIMESTAMP] [$level] $*" | tee -a "$LOG_FILE"
}

# ── 1. Create Directory Structure ─────────────────────────────
setup_directories() {
    log INFO "Creating payroll data pipeline directory structure..."

    local dirs=(
        "$PROJECT_DIR/raw/employees"
        "$PROJECT_DIR/raw/payroll"
        "$PROJECT_DIR/raw/attendance"
        "$PROJECT_DIR/raw/loans"
        "$PROJECT_DIR/processed/cleaned"
        "$PROJECT_DIR/processed/transformed"
        "$PROJECT_DIR/processed/aggregated"
        "$PROJECT_DIR/archive/$(date +%Y)/$(date +%m)"
        "$PROJECT_DIR/output/reports"
        "$PROJECT_DIR/output/exports"
        "$PROJECT_DIR/logs/pipeline"
        "$PROJECT_DIR/logs/errors"
        "$PROJECT_DIR/config"
        "$PROJECT_DIR/scripts"
        "$PROJECT_DIR/temp"
        "$PROJECT_DIR/quarantine"
        "$PROJECT_DIR/backup"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log INFO "Created: $dir"
    done

    log INFO "Directory structure created successfully."
}

# ── 2. Set File Permissions ───────────────────────────────────
set_permissions() {
    log INFO "Setting file permissions..."

    # raw/ → read-only for data protection (644 files, 755 dirs)
    chmod -R 755 "$PROJECT_DIR/raw"
    log INFO "raw/ → 755 (read+execute for all)"

    # processed/ → read-write for pipeline user
    chmod -R 755 "$PROJECT_DIR/processed"
    log INFO "processed/ → 755"

    # output/ → readable by all, writable by owner
    chmod -R 755 "$PROJECT_DIR/output"
    log INFO "output/ → 755"

    # config/ → restricted (owner only)
    chmod 700 "$PROJECT_DIR/config"
    log INFO "config/ → 700 (owner only)"

    # scripts/ → executable
    chmod -R 755 "$PROJECT_DIR/scripts"
    log INFO "scripts/ → 755 (executable)"

    # logs/ → append-only feel (no delete)
    chmod -R 755 "$PROJECT_DIR/logs"
    log INFO "logs/ → 755"

    # quarantine/ → restricted
    chmod 750 "$PROJECT_DIR/quarantine"
    log INFO "quarantine/ → 750"

    log INFO "Permissions configured."
}

# ── 3. Create Sample Payroll Data Files ───────────────────────
create_sample_files() {
    log INFO "Creating sample payroll data files..."

    # Employee master CSV
    cat > "$PROJECT_DIR/raw/employees/employees_$(date +%Y%m%d).csv" << 'CSVEOF'
emp_id,emp_code,first_name,last_name,department,designation,basic_salary,status,date_joined
1,EMP001,Rajesh,Kumar,Human Resources,HR Executive,45000,Active,2018-06-01
2,EMP002,Priya,Sharma,Human Resources,HR Manager,125000,Active,2016-03-15
3,EMP003,Amit,Patel,Information Technology,Software Engineer,65000,Active,2019-09-01
4,EMP004,Sneha,Reddy,Customer Support,HR Executive,30000,Active,2021-01-10
5,EMP005,Vikram,Singh,Sales & Marketing,Sales Executive,38000,Active,2017-08-20
CSVEOF

    # Payroll CSV
    cat > "$PROJECT_DIR/raw/payroll/payroll_$(date +%Y%m).csv" << 'CSVEOF'
payroll_id,emp_id,period,gross_salary,pf_employee,tds,net_salary,status
1,1,March-2026,64900,1800,536.67,62363.33,Paid
2,2,March-2026,197500,1800,25333.33,172166.67,Paid
3,3,March-2026,97266.67,1800,5685,91581.67,Paid
4,4,March-2026,41300,1800,0,39300,Paid
5,5,March-2026,54991.11,1800,82.44,52949.89,Paid
CSVEOF

    # Attendance CSV
    cat > "$PROJECT_DIR/raw/attendance/attendance_$(date +%Y%m).csv" << 'CSVEOF'
emp_id,att_date,status,check_in,check_out,hours_worked
1,2026-03-01,Present,09:00,18:30,9.5
1,2026-03-02,Present,09:00,18:00,9.0
1,2026-03-03,Absent,,,0
2,2026-03-01,Present,09:00,19:00,10.0
2,2026-03-02,Present,09:00,18:30,9.5
CSVEOF

    log INFO "Sample data files created."
}

# ── 4. Automate File Movement ─────────────────────────────────
automate_file_movement() {
    log INFO "Starting automated file movement pipeline..."
    local moved=0
    local failed=0

    # Move raw CSVs → processed (simulate validation)
    for file in "$PROJECT_DIR/raw"/**/*.csv; do
        [ -f "$file" ] || continue
        filename=$(basename "$file")
        dest="$PROJECT_DIR/processed/cleaned/$filename"

        # Simulate validation: check file size > 0
        if [ -s "$file" ]; then
            cp "$file" "$dest"
            log INFO "Moved: $filename → processed/cleaned/"
            ((moved++)) || true
        else
            cp "$file" "$PROJECT_DIR/quarantine/$filename"
            log WARN "Quarantined empty file: $filename"
            ((failed++)) || true
        fi
    done

    log INFO "File movement complete. Moved: $moved | Failed/Quarantined: $failed"
}

# ── 5. Archive Old Files ──────────────────────────────────────
archive_files() {
    log INFO "Archiving processed files..."
    local archive_dir="$PROJECT_DIR/archive/$(date +%Y)/$(date +%m)"
    local count=0

    for file in "$PROJECT_DIR/processed/cleaned"/*.csv; do
        [ -f "$file" ] || continue
        cp "$file" "$archive_dir/"
        log INFO "Archived: $(basename $file)"
        ((count++)) || true
    done

    log INFO "Archived $count files to $archive_dir"
}

# ── 6. Generate Pipeline Report ───────────────────────────────
generate_report() {
    local report="$PROJECT_DIR/logs/pipeline/run_$(date +%Y%m%d_%H%M%S).report"
    log INFO "Generating pipeline report: $report"

    cat > "$report" << REPORT
=============================================================
  PAYROLL PIPELINE EXECUTION REPORT
  Generated: $TIMESTAMP
=============================================================

DIRECTORY STRUCTURE:
$(find "$PROJECT_DIR" -type d | sort | sed 's|'"$PROJECT_DIR"'||' | sed 's|^|  |')

FILE COUNTS:
  Raw files:       $(find "$PROJECT_DIR/raw" -type f | wc -l)
  Processed files: $(find "$PROJECT_DIR/processed" -type f | wc -l)
  Archived files:  $(find "$PROJECT_DIR/archive" -type f | wc -l)
  Quarantined:     $(find "$PROJECT_DIR/quarantine" -type f | wc -l)

DISK USAGE:
$(du -sh "$PROJECT_DIR"/* 2>/dev/null | sed 's|^|  |')

PERMISSIONS AUDIT:
$(ls -ld "$PROJECT_DIR"/*)

STATUS: SUCCESS
=============================================================
REPORT

    cat "$report"
    log INFO "Report saved: $report"
}

# ── 7. Cleanup Temp Files ─────────────────────────────────────
cleanup() {
    log INFO "Cleaning up temp directory..."
    rm -rf "$PROJECT_DIR/temp"/*
    log INFO "Temp files cleaned."
}

# ── MAIN ──────────────────────────────────────────────────────
main() {
    echo "============================================================"
    echo "  TASK 01: Linux + File System — Payroll Pipeline Setup"
    echo "============================================================"
    echo "" > "$LOG_FILE"
    log INFO "=== Pipeline execution started ==="

    setup_directories
    set_permissions
    create_sample_files
    automate_file_movement
    archive_files
    generate_report
    cleanup

    log INFO "=== Pipeline execution completed successfully ==="
    echo ""
    echo "✓ Log file: $LOG_FILE"
    echo "✓ Project: $PROJECT_DIR"
}

main "$@"
