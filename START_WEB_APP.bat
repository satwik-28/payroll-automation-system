@echo off
echo.
echo  PayrollWise - Starting Web Application
echo  =======================================
cd /d "%~dp0payroll_web"
pip install flask -q
python start.py
pause
