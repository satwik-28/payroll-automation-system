# Task 09: Data Warehousing — Star Schema

## What This Implements
fact_payroll + 5 dimension tables (employee, department, designation, grade, period), populate from OLTP

## How to Run
```bash
cd 09_data_warehousing
python dw_etl_ingestion.py
```

## Output
All results are saved to `output/` inside this folder.

## Key Concepts
See the Python file for full implementation with comments.

---
*Part of PayrollWise — 30-Task Data Engineering System*  
*Run all 30 tasks: `python run_all.py` from the project root*
