#!/bin/bash
echo ""
echo "  PayrollWise - Starting Web Application"
echo "  ======================================="
cd "$(dirname "$0")/payroll_web"
pip install flask -q
python start.py
