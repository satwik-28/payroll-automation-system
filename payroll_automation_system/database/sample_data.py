"""
Sample Data Insertion Script
Inserts 20+ records per main table into the Payroll database
"""
import os
import sys
import sqlite3
import random
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "database", "payroll.db")
sys.path.insert(0, BASE_DIR)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def insert_departments(conn):
    departments = [
        ("DEPT001", "Human Resources",          "Mumbai",    4500000),
        ("DEPT002", "Finance & Accounts",        "Mumbai",    3800000),
        ("DEPT003", "Information Technology",    "Bengaluru", 8500000),
        ("DEPT004", "Sales & Marketing",         "Delhi",     6200000),
        ("DEPT005", "Operations",                "Pune",      5100000),
        ("DEPT006", "Research & Development",    "Bengaluru", 9200000),
        ("DEPT007", "Customer Support",          "Hyderabad", 3200000),
        ("DEPT008", "Legal & Compliance",        "Mumbai",    2800000),
        ("DEPT009", "Supply Chain & Logistics",  "Chennai",   4100000),
        ("DEPT010", "Product Management",        "Bengaluru", 5600000),
        ("DEPT011", "Data Science & Analytics",  "Bengaluru", 7200000),
        ("DEPT012", "Quality Assurance",         "Pune",      3900000),
        ("DEPT013", "Administration",            "Mumbai",    2200000),
        ("DEPT014", "Business Development",      "Delhi",     4700000),
        ("DEPT015", "Cloud Infrastructure",      "Bengaluru", 6800000),
        ("DEPT016", "Cyber Security",            "Bengaluru", 5400000),
        ("DEPT017", "Enterprise Architecture",   "Bengaluru", 4900000),
        ("DEPT018", "Procurement",               "Mumbai",    3100000),
        ("DEPT019", "Training & Development",    "Pune",      2600000),
        ("DEPT020", "Corporate Strategy",        "Mumbai",    5900000),
        ("DEPT021", "Digital Marketing",         "Delhi",     3700000),
        ("DEPT022", "DevOps & Platform Eng",     "Bengaluru", 7500000),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO departments(dept_code, dept_name, location, budget)
        VALUES(?,?,?,?)
    """, departments)
    conn.commit()
    print(f"  [✓] Inserted {len(departments)} departments")


def insert_salary_grades(conn):
    grades = [
        ("G1",  "Intern/Trainee",      15000,  25000,  10, 10, 500),
        ("G2",  "Junior Associate",    25000,  40000,  20, 15, 800),
        ("G3",  "Associate",           40000,  60000,  30, 17, 1200),
        ("G4",  "Senior Associate",    60000,  85000,  35, 18, 1500),
        ("G5",  "Team Lead",           85000,  120000, 38, 20, 2000),
        ("G6",  "Assistant Manager",   120000, 160000, 40, 22, 2500),
        ("G7",  "Deputy Manager",      160000, 200000, 42, 23, 3000),
        ("G8",  "Manager",             200000, 250000, 44, 24, 3500),
        ("G9",  "Senior Manager",      250000, 320000, 45, 25, 4000),
        ("G10", "General Manager",     320000, 420000, 45, 25, 5000),
        ("G11", "Vice President",      420000, 600000, 45, 25, 7000),
        ("G12", "Senior Vice Pres.",   600000, 900000, 45, 25, 10000),
        ("G13", "Director",            900000, 1400000,45, 25, 15000),
        ("G14", "Senior Director",    1400000, 2000000,45, 25, 20000),
        ("G15", "C-Suite Executive",  2000000, 5000000,45, 25, 30000),
        ("G16", "Specialist L1",       50000,  75000,  30, 17, 1200),
        ("G17", "Specialist L2",       75000,  110000, 35, 18, 1800),
        ("G18", "Specialist L3",      110000,  160000, 40, 20, 2500),
        ("G19", "Principal Engineer", 180000,  280000, 42, 22, 3500),
        ("G20", "Distinguished Eng.", 280000,  450000, 45, 25, 5000),
        ("G21", "Fellow",             450000,  800000, 45, 25, 8000),
        ("G22", "Part-Time Assoc.",    12000,   20000,  0,  0, 0),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO salary_grades(grade_code, grade_name, basic_min, basic_max, hra_pct, da_pct, ta_flat)
        VALUES(?,?,?,?,?,?,?)
    """, grades)
    conn.commit()
    print(f"  [✓] Inserted {len(grades)} salary grades")


def insert_designations(conn):
    # dept_id 1=HR, 2=Finance, 3=IT, 4=Sales, 5=Ops, 6=R&D, 7=Support
    designations = [
        ("D001", "HR Executive",              1, 2),
        ("D002", "HR Manager",                1, 5),
        ("D003", "HR Director",               1, 9),
        ("D004", "Accounts Executive",        2, 2),
        ("D005", "Senior Accountant",         2, 4),
        ("D006", "Finance Manager",           2, 7),
        ("D007", "CFO",                       2, 14),
        ("D008", "Junior Software Engineer",  3, 2),
        ("D009", "Software Engineer",         3, 3),
        ("D010", "Senior Software Engineer",  3, 4),
        ("D011", "Tech Lead",                 3, 5),
        ("D012", "Engineering Manager",       3, 8),
        ("D013", "VP Engineering",            3, 11),
        ("D014", "Sales Executive",           4, 2),
        ("D015", "Senior Sales Executive",    4, 3),
        ("D016", "Sales Manager",             4, 7),
        ("D017", "Regional Sales Director",   4, 9),
        ("D018", "Operations Analyst",        5, 2),
        ("D019", "Operations Manager",        5, 7),
        ("D020", "VP Operations",             5, 11),
        ("D021", "Research Scientist",        6, 4),
        ("D022", "Senior Research Scientist", 6, 5),
        ("D023", "Principal Scientist",       6, 8),
        ("D024", "Data Scientist",           11, 3),
        ("D025", "Senior Data Scientist",    11, 5),
        ("D026", "Data Science Manager",     11, 8),
        ("D027", "QA Engineer",             12, 2),
        ("D028", "Senior QA Engineer",      12, 4),
        ("D029", "QA Lead",                 12, 5),
        ("D030", "DevOps Engineer",         22, 3),
        ("D031", "Senior DevOps Engineer",  22, 5),
        ("D032", "Platform Engineering Mgr",22, 8),
        ("D033", "Security Analyst",        16, 3),
        ("D034", "Senior Security Analyst", 16, 5),
        ("D035", "CISO",                    16, 13),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO designations(desig_code, desig_title, dept_id, level_rank)
        VALUES(?,?,?,?)
    """, designations)
    conn.commit()
    print(f"  [✓] Inserted {len(designations)} designations")


def insert_employees(conn):
    employees = [
        # emp_code, first, last, gender, dob, email, phone, address, city, state, pan, aadhaar, bank_acc, bank, ifsc, dept_id, desig_id, grade_id, basic, joined, type, status
        ("EMP001","Rajesh","Kumar","Male","1985-03-15","rajesh.kumar@payrollwise.in","9876543210","A-12 Green Park","Delhi","Delhi","AABPK1234C","5678","123456789012","HDFC Bank","HDFC0001234",1,1,3,45000,"2018-06-01","Full-Time","Active"),
        ("EMP002","Priya","Sharma","Female","1990-07-22","priya.sharma@payrollwise.in","9845231078","B-45 Andheri East","Mumbai","Maharashtra","BCDPS5678D","9012","234567890123","ICICI Bank","ICIC0002345",1,2,6,125000,"2016-03-15","Full-Time","Active"),
        ("EMP003","Amit","Patel","Male","1988-11-08","amit.patel@payrollwise.in","9912345670","C-78 Koramangala","Bengaluru","Karnataka","CDEAP2345E","3456","345678901234","SBI","SBIN0003456",3,9,4,65000,"2019-09-01","Full-Time","Active"),
        ("EMP004","Sneha","Reddy","Female","1992-04-30","sneha.reddy@payrollwise.in","9823456789","D-23 Banjara Hills","Hyderabad","Telangana","DEFSR3456F","7890","456789012345","Axis Bank","UTIB0004567",7,1,2,30000,"2021-01-10","Full-Time","Active"),
        ("EMP005","Vikram","Singh","Male","1983-12-19","vikram.singh@payrollwise.in","9756789012","E-67 Vasant Kunj","Delhi","Delhi","EFGVS4567G","1234","567890123456","Kotak Bank","KKBK0005678",4,14,3,38000,"2017-08-20","Full-Time","Active"),
        ("EMP006","Ananya","Iyer","Female","1994-06-14","ananya.iyer@payrollwise.in","9634512378","F-89 Adyar","Chennai","Tamil Nadu","FGHAI5678H","5678","678901234567","Indian Bank","IDIB0006789",2,4,2,28000,"2022-03-01","Full-Time","Active"),
        ("EMP007","Rohit","Gupta","Male","1987-09-25","rohit.gupta@payrollwise.in","9578901234","G-34 Kalyani Nagar","Pune","Maharashtra","GHIRG6789I","9012","789012345678","Bank of Baroda","BARB0007890",3,10,5,88000,"2015-05-12","Full-Time","Active"),
        ("EMP008","Kavitha","Menon","Female","1991-02-18","kavitha.menon@payrollwise.in","9467890123","H-56 MG Road","Bengaluru","Karnataka","HIJKM7890J","3456","890123456789","Federal Bank","FDRL0008901",11,24,4,72000,"2020-07-01","Full-Time","Active"),
        ("EMP009","Sanjay","Nair","Male","1986-08-07","sanjay.nair@payrollwise.in","9356789012","I-12 Marine Lines","Mumbai","Maharashtra","IJKSN8901K","7890","901234567890","HDFC Bank","HDFC0009012",5,18,3,44000,"2018-11-15","Full-Time","Active"),
        ("EMP010","Deepa","Joshi","Female","1993-05-28","deepa.joshi@payrollwise.in","9245678901","J-78 Shivajinagar","Pune","Maharashtra","JKLDJ9012L","1234","012345678901","ICICI Bank","ICIC0000123",6,21,5,95000,"2019-02-01","Full-Time","Active"),
        ("EMP011","Arjun","Mehta","Male","1989-10-11","arjun.mehta@payrollwise.in","9134567890","K-45 Powai","Mumbai","Maharashtra","KLMAM0123M","5678","123456789013","Axis Bank","UTIB0001234",3,11,6,135000,"2016-07-20","Full-Time","Active"),
        ("EMP012","Pooja","Verma","Female","1995-01-24","pooja.verma@payrollwise.in","9023456789","L-23 HSR Layout","Bengaluru","Karnataka","LMNPV1234N","9012","234567890124","SBI","SBIN0002345",12,27,3,42000,"2021-08-01","Full-Time","Active"),
        ("EMP013","Kiran","Rao","Male","1984-07-06","kiran.rao@payrollwise.in","8912345678","M-67 Jubilee Hills","Hyderabad","Telangana","MNOKR2345O","3456","345678901235","Kotak Bank","KKBK0003456",4,16,7,185000,"2014-04-01","Full-Time","Active"),
        ("EMP014","Nisha","Shah","Female","1990-11-17","nisha.shah@payrollwise.in","8823456789","N-89 CG Road","Ahmedabad","Gujarat","NOPNS3456P","7890","456789012346","HDFC Bank","HDFC0004567",2,5,4,62000,"2018-09-15","Full-Time","Active"),
        ("EMP015","Rahul","Desai","Male","1988-03-29","rahul.desai@payrollwise.in","8756789012","O-12 FC Road","Pune","Maharashtra","OPQRD4567Q","1234","567890123457","Indian Bank","IDIB0005678",22,30,4,68000,"2019-12-01","Full-Time","Active"),
        ("EMP016","Swati","Kulkarni","Female","1992-09-03","swati.kulkarni@payrollwise.in","8645678901","P-34 Kothrud","Pune","Maharashtra","PQRSK5678R","5678","678901234568","Bank of Maharashtra","MAHB0006789",12,28,4,55000,"2020-04-01","Full-Time","Active"),
        ("EMP017","Manoj","Tiwari","Male","1981-06-22","manoj.tiwari@payrollwise.in","8534567890","Q-56 Civil Lines","Allahabad","UP","QRSMT6789S","9012","789012345679","PNB","PUNB0007890",5,19,8,215000,"2012-01-10","Full-Time","Active"),
        ("EMP018","Anjali","Bose","Female","1996-04-15","anjali.bose@payrollwise.in","8423456789","R-78 Park Street","Kolkata","West Bengal","RSTAB7890T","3456","890123456780","HDFC Bank","HDFC0008901",6,22,5,98000,"2021-06-01","Full-Time","Active"),
        ("EMP019","Suresh","Pillai","Male","1985-12-08","suresh.pillai@payrollwise.in","8312345678","S-23 Vashi","Navi Mumbai","Maharashtra","STUSP8901U","7890","901234567891","Union Bank","UBIN0009012",16,33,4,73000,"2018-03-20","Full-Time","Active"),
        ("EMP020","Meena","Krishnan","Female","1991-08-19","meena.krishnan@payrollwise.in","8234567890","T-45 Anna Nagar","Chennai","Tamil Nadu","TUVMK9012V","1234","012345678902","Indian Bank","IDIB0000123",11,25,5,86000,"2019-10-01","Full-Time","Active"),
        ("EMP021","Aakash","Goel","Male","1993-02-27","aakash.goel@payrollwise.in","8145678901","U-67 Rohini","Delhi","Delhi","UVWAG0123W","5678","123456789014","ICICI Bank","ICIC0001234",3,8,2,28000,"2023-01-15","Full-Time","Active"),
        ("EMP022","Ritu","Agarwal","Female","1987-07-14","ritu.agarwal@payrollwise.in","8056789012","V-89 Tilak Nagar","Delhi","Delhi","VWXRA1234X","9012","234567890125","Axis Bank","UTIB0002345",4,15,3,41000,"2017-05-01","Full-Time","Active"),
        ("EMP023","Dinesh","Sharma","Male","1980-04-03","dinesh.sharma@payrollwise.in","7945678901","W-12 Vastrapur","Ahmedabad","Gujarat","WXYDS2345Y","3456","345678901236","SBI","SBIN0003456",2,7,15,325000,"2010-08-01","Full-Time","Active"),
        ("EMP024","Lakshmi","Prasad","Female","1994-10-26","lakshmi.prasad@payrollwise.in","7856789012","X-34 Whitefield","Bengaluru","Karnataka","XYZLP3456Z","7890","456789012347","HDFC Bank","HDFC0004567",3,13,11,480000,"2020-11-01","Full-Time","Active"),
        ("EMP025","Harish","Chandra","Male","1983-05-17","harish.chandra@payrollwise.in","7745678901","Y-56 Saket","Delhi","Delhi","YABHC4567A","1234","567890123458","Kotak Bank","KKBK0005678",20,1,3,35000,"2022-07-01","Full-Time","Active"),
        ("EMP026","Preethi","Nambiar","Female","1989-01-09","preethi.nambiar@payrollwise.in","7634567890","Z-78 Palarivattom","Kochi","Kerala","ZABPN5678B","5678","678901234569","Federal Bank","FDRL0006789",7,1,2,29000,"2021-03-15","Full-Time","Active"),
        ("EMP027","Gaurav","Khanna","Male","1992-06-30","gaurav.khanna@payrollwise.in","7523456789","A-23 Panchkula","Chandigarh","Punjab","ABCGK6789C","9012","789012345670","PNB","PUNB0007890",22,31,5,92000,"2019-04-01","Full-Time","Active"),
        ("EMP028","Shweta","Pandey","Female","1995-03-12","shweta.pandey@payrollwise.in","7456789012","B-45 Gomti Nagar","Lucknow","UP","BCDSP7890D","3456","890123456781","SBI","SBIN0008901",1,1,2,27000,"2023-06-01","Full-Time","Active"),
        ("EMP029","Naveen","Reddy","Male","1986-11-23","naveen.reddy@payrollwise.in","7345678901","C-67 Gachibowli","Hyderabad","Telangana","CDENR8901E","7890","901234567892","HDFC Bank","HDFC0009012",16,34,5,88000,"2017-10-01","Full-Time","Active"),
        ("EMP030","Divya","Mohan","Female","1993-08-05","divya.mohan@payrollwise.in","7256789012","D-89 Mylapore","Chennai","Tamil Nadu","DEFIDM9012F","1234","012345678903","Indian Bank","IDIB0000123",6,23,9,265000,"2018-01-15","Full-Time","Active"),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO employees(
            emp_code, first_name, last_name, gender, dob, email, phone, address, city, state,
            pan_number, aadhaar_last4, bank_account, bank_name, ifsc_code,
            dept_id, desig_id, grade_id, basic_salary, date_joined, employment_type, status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, employees)
    conn.commit()
    print(f"  [✓] Inserted {len(employees)} employees")


def insert_payroll_periods(conn):
    periods = [
        ("April 2024",     4, 2024, "2024-04-01", "2024-04-30", 30, 26, "Paid"),
        ("May 2024",       5, 2024, "2024-05-01", "2024-05-31", 31, 27, "Paid"),
        ("June 2024",      6, 2024, "2024-06-01", "2024-06-30", 30, 25, "Paid"),
        ("July 2024",      7, 2024, "2024-07-01", "2024-07-31", 31, 27, "Paid"),
        ("August 2024",    8, 2024, "2024-08-01", "2024-08-31", 31, 26, "Paid"),
        ("September 2024", 9, 2024, "2024-09-01", "2024-09-30", 30, 25, "Paid"),
        ("October 2024",  10, 2024, "2024-10-01", "2024-10-31", 31, 27, "Paid"),
        ("November 2024", 11, 2024, "2024-11-01", "2024-11-30", 30, 25, "Paid"),
        ("December 2024", 12, 2024, "2024-12-01", "2024-12-31", 31, 26, "Paid"),
        ("January 2025",   1, 2025, "2025-01-01", "2025-01-31", 31, 27, "Paid"),
        ("February 2025",  2, 2025, "2025-02-01", "2025-02-28", 28, 24, "Paid"),
        ("March 2025",     3, 2025, "2025-03-01", "2025-03-31", 31, 27, "Paid"),
        ("April 2025",     4, 2025, "2025-04-01", "2025-04-30", 30, 26, "Paid"),
        ("May 2025",       5, 2025, "2025-05-01", "2025-05-31", 31, 27, "Paid"),
        ("June 2025",      6, 2025, "2025-06-01", "2025-06-30", 30, 25, "Paid"),
        ("July 2025",      7, 2025, "2025-07-01", "2025-07-31", 31, 27, "Paid"),
        ("August 2025",    8, 2025, "2025-08-01", "2025-08-31", 31, 26, "Paid"),
        ("September 2025", 9, 2025, "2025-09-01", "2025-09-30", 30, 25, "Paid"),
        ("October 2025",  10, 2025, "2025-10-01", "2025-10-31", 31, 27, "Paid"),
        ("November 2025", 11, 2025, "2025-11-01", "2025-11-30", 30, 25, "Paid"),
        ("December 2025", 12, 2025, "2025-12-01", "2025-12-31", 31, 26, "Paid"),
        ("January 2026",   1, 2026, "2026-01-01", "2026-01-31", 31, 27, "Paid"),
        ("February 2026",  2, 2026, "2026-02-01", "2026-02-28", 28, 24, "Paid"),
        ("March 2026",     3, 2026, "2026-03-01", "2026-03-31", 31, 27, "Paid"),
        ("April 2026",     4, 2026, "2026-04-01", "2026-04-30", 30, 26, "Processing"),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO payroll_periods(period_name, month, year, start_date, end_date, total_days, working_days, status)
        VALUES(?,?,?,?,?,?,?,?)
    """, periods)
    conn.commit()
    print(f"  [✓] Inserted {len(periods)} payroll periods")


def insert_leave_types(conn):
    leave_types = [
        ("CL",  "Casual Leave",          12, 1, 0),
        ("SL",  "Sick Leave",            12, 1, 0),
        ("PL",  "Privilege Leave",       15, 1, 1),
        ("ML",  "Maternity Leave",       26, 1, 0),
        ("PAL", "Paternity Leave",        5, 1, 0),
        ("BL",  "Bereavement Leave",      3, 1, 0),
        ("COL", "Compensatory Off",      10, 1, 0),
        ("LOP", "Loss of Pay",          999, 0, 0),
        ("EL",  "Earned Leave",          30, 1, 1),
        ("VOL", "Voluntary Leave",        5, 0, 0),
        ("WFH", "Work From Home",        24, 1, 0),
        ("QUARL","Quarantine Leave",     14, 1, 0),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO leave_types(leave_code, leave_name, max_days_year, is_paid, carry_forward)
        VALUES(?,?,?,?,?)
    """, leave_types)
    conn.commit()
    print(f"  [✓] Inserted {len(leave_types)} leave types")


def insert_deduction_types(conn):
    ded_types = [
        ("PF",      "Provident Fund (Employee)",         1, 12.00, 1, "12% of basic salary"),
        ("ESI",     "ESI (Employee)",                    1,  0.75, 0, "0.75% of gross (if gross<=21000)"),
        ("PT",      "Professional Tax",                  0,  200,  1, "State professional tax (flat)"),
        ("TDS",     "Income Tax TDS",                    1,  0,    1, "Calculated per IT slabs"),
        ("LOAN",    "Loan EMI Deduction",                0,  0,    0, "Employee loan EMI"),
        ("ADV",     "Advance Recovery",                  0,  0,    0, "Salary advance recovery"),
        ("ABSENT",  "Absent Day Deduction",              0,  0,    0, "Per-day deduction for absences"),
        ("LATE",    "Late Arrival Penalty",              0,  0,    0, "Penalty for late arrivals"),
        ("VOLUNTPF","Voluntary PF (Additional)",         1,  0,    0, "Additional voluntary PF contribution"),
        ("GROUP_INS","Group Health Insurance",           0, 500,   1, "Group mediclaim premium"),
        ("CANTEEN", "Canteen Recovery",                  0,  150,  0, "Monthly canteen charges"),
        ("CLUB",    "Club Membership",                   0,  200,  0, "Corporate club membership fee"),
        ("PARKING", "Parking Fee",                       0,  300,  0, "Office parking charges"),
        ("UNIFORM", "Uniform Deduction",                 0,  100,  0, "Uniform issuance recovery"),
        ("SALARY_ADV","Salary Advance (Full Month)",     0,  0,    0, "Full month salary advance deduction"),
        ("NEFT_FEE", "NEFT Transfer Fee",                0,   10,  0, "Bank transfer charges"),
        ("BOND_RECOV","Bond Recovery",                   0,  0,    0, "Training bond recovery"),
        ("NOTICE_PAY","Notice Period Recovery",          0,  0,    0, "Short notice period deduction"),
        ("FINE",     "Disciplinary Fine",                0,  0,    0, "Performance related fine"),
        ("MISC_DED", "Miscellaneous Deduction",          0,  0,    0, "Other miscellaneous"),
        ("VPFADD",   "VPF Additional",                   1,  0,    0, "Additional PF beyond mandatory"),
        ("NPS",      "National Pension System",          1,  0,    0, "NPS Tier-1 contribution"),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO deduction_types(deduction_code, deduction_name, is_percentage, default_value, is_mandatory, description)
        VALUES(?,?,?,?,?,?)
    """, ded_types)
    conn.commit()
    print(f"  [✓] Inserted {len(ded_types)} deduction types")


def insert_tax_slabs(conn):
    slabs = [
        ("FY2024-25",         0,  300000, 0,   0, "No tax upto 3L (new regime)"),
        ("FY2024-25",    300000,  600000, 5,   0, "5% (3L-6L)"),
        ("FY2024-25",    600000,  900000, 10,  0, "10% (6L-9L)"),
        ("FY2024-25",    900000, 1200000, 15,  0, "15% (9L-12L)"),
        ("FY2024-25",   1200000, 1500000, 20,  0, "20% (12L-15L)"),
        ("FY2024-25",   1500000, None,    30,  0, "30% above 15L"),
        ("FY2025-26",         0,  400000,  0,  0, "No tax upto 4L (new regime)"),
        ("FY2025-26",    400000,  800000,  5,  0, "5% (4L-8L)"),
        ("FY2025-26",    800000, 1200000, 10,  0, "10% (8L-12L)"),
        ("FY2025-26",   1200000, 1600000, 15,  0, "15% (12L-16L)"),
        ("FY2025-26",   1600000, 2000000, 20,  0, "20% (16L-20L)"),
        ("FY2025-26",   2000000, 2400000, 25,  0, "25% (20L-24L)"),
        ("FY2025-26",   2400000, None,    30,  0, "30% above 24L"),
        ("FY2024-25-OLD",     0,  250000,  0,  0, "Old regime: No tax upto 2.5L"),
        ("FY2024-25-OLD",250000,  500000,  5,  0, "Old regime: 5% (2.5L-5L)"),
        ("FY2024-25-OLD",500000, 1000000, 20,  0, "Old regime: 20% (5L-10L)"),
        ("FY2024-25-OLD",1000000,None,    30,  0, "Old regime: 30% above 10L"),
        ("FY2025-26",   5000000, None,    30, 10, "Surcharge: 10% if income > 50L"),
        ("FY2025-26",  10000000, None,    30, 15, "Surcharge: 15% if income > 1Cr"),
        ("FY2025-26",  20000000, None,    30, 25, "Surcharge: 25% if income > 2Cr"),
        ("FY2025-26",  50000000, None,    30, 37, "Surcharge: 37% if income > 5Cr"),
        ("CESS",              0, None,     4,  0, "Health & Education Cess on tax"),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO tax_slabs(fiscal_year, income_from, income_to, tax_rate_pct, surcharge_pct, description)
        VALUES(?,?,?,?,?,?)
    """, slabs)
    conn.commit()
    print(f"  [✓] Inserted {len(slabs)} tax slabs")


def calc_payroll(basic, grade_id, working_days, days_present, days_absent, conn):
    """Calculate payroll components."""
    cur = conn.cursor()
    cur.execute("SELECT hra_pct, da_pct, ta_flat FROM salary_grades WHERE grade_id=?", (grade_id,))
    g = cur.fetchone()

    per_day = basic / working_days
    effective_basic = basic - (days_absent * per_day)

    hra = round(effective_basic * g[0] / 100, 2)
    da  = round(effective_basic * g[1] / 100, 2)
    ta  = g[2] if days_absent < working_days * 0.5 else 0
    gross = round(effective_basic + hra + da + ta, 2)

    pf_emp  = round(min(effective_basic, 15000) * 0.12, 2)
    pf_er   = round(min(effective_basic, 15000) * 0.12, 2)
    esi_emp = round(gross * 0.0075, 2) if gross <= 21000 else 0
    esi_er  = round(gross * 0.0325, 2) if gross <= 21000 else 0
    pt      = 200 if gross > 10000 else 0
    annual_gross = gross * 12
    tds     = calc_tds(annual_gross) / 12

    total_ded = round(pf_emp + esi_emp + pt + tds, 2)
    net       = round(gross - total_ded, 2)

    return {
        "basic": round(effective_basic, 2), "hra": hra, "da": da, "ta": ta,
        "gross": gross, "pf_emp": pf_emp, "pf_er": pf_er,
        "esi_emp": esi_emp, "esi_er": esi_er, "pt": pt, "tds": round(tds, 2),
        "total_ded": total_ded, "net": net
    }


def calc_tds(annual_income):
    """Simple TDS calculation using FY2025-26 slabs."""
    slabs = [(400000, 0), (800000, 5), (1200000, 10), (1600000, 15),
             (2000000, 20), (2400000, 25), (float('inf'), 30)]
    tax   = 0
    prev  = 0
    for upper, rate in slabs:
        if annual_income <= prev:
            break
        taxable = min(annual_income, upper) - prev
        tax += taxable * rate / 100
        prev = upper
        if annual_income <= upper:
            break
    return max(tax - 12500, 0)  # 87A rebate


def insert_attendance(conn):
    """Insert 26+ attendance records per employee for last 2 months."""
    cur = conn.cursor()
    cur.execute("SELECT emp_id FROM employees WHERE status='Active'")
    emp_ids = [r[0] for r in cur.fetchall()]

    records = []
    statuses = ['Present', 'Present', 'Present', 'Present', 'Present',
                'Present', 'Present', 'Present', 'Present', 'Present',
                'Present', 'Present', 'Present', 'Present', 'Present',
                'Present', 'Present', 'Present', 'Present', 'Present',
                'Present', 'Present', 'Present', 'Present', 'Present',
                'Absent', 'Half-Day', 'On-Leave']
    random.seed(42)

    months = [
        ("2026-02", 2026, 2, list(range(1, 29))),
        ("2026-03", 2026, 3, list(range(1, 32))),
    ]

    for emp_id in emp_ids:
        for ym, yr, mo, days in months:
            st_list = statuses.copy()
            random.shuffle(st_list)
            idx = 0
            for day in days:
                try:
                    d = date(yr, mo, day)
                except ValueError:
                    continue
                dow = d.weekday()
                if dow >= 5:
                    status = 'Weekend'
                    check_in = None; check_out = None; hours = 0
                else:
                    status = st_list[idx % len(st_list)]
                    idx += 1
                    if status == 'Present':
                        check_in = "09:00"
                        hours = round(random.uniform(7.5, 9.5), 1)
                        check_out = f"{9 + int(hours):02d}:{int((hours % 1)*60):02d}"
                    elif status == 'Half-Day':
                        check_in = "09:00"; check_out = "13:00"; hours = 4.0
                    else:
                        check_in = None; check_out = None; hours = 0
                records.append((emp_id, d.isoformat(), check_in, check_out, hours, status))

    cur.executemany("""
        INSERT OR IGNORE INTO attendance(emp_id, att_date, check_in, check_out, hours_worked, status)
        VALUES(?,?,?,?,?,?)
    """, records)
    conn.commit()
    print(f"  [✓] Inserted {len(records)} attendance records")


def insert_leave_requests(conn):
    cur = conn.cursor()
    leaves = [
        (1,  1, "2026-01-05","2026-01-06", 2, "Personal work",          "Approved", 2,  "2025-12-30", 22),
        (2,  2, "2026-01-10","2026-01-10", 1, "Feeling unwell",         "Approved", 2,  "2026-01-09", 22),
        (3,  3, "2026-01-08","2026-01-09", 2, "Family function",        "Approved", 11, "2026-01-07", 22),
        (4,  4, "2026-01-12","2026-01-14", 3, "Sick (flu)",             "Approved", 2,  "2026-01-11", 22),
        (5,  1, "2026-02-03","2026-02-04", 2, "Outstation travel",      "Approved", 2,  "2026-02-01", 23),
        (6,  2, "2026-02-14","2026-02-14", 1, "Personal",               "Approved", 2,  "2026-02-12", 23),
        (7,  5, "2026-01-20","2026-01-22", 3, "Medical appointment",    "Approved", 13, "2026-01-19", 22),
        (8,  6, "2026-02-05","2026-02-05", 1, "Religious holiday",      "Approved", 2,  "2026-02-04", 23),
        (9,  7, "2026-01-27","2026-01-28", 2, "Child's school event",   "Approved", 17, "2026-01-26", 22),
        (10, 8, "2026-02-10","2026-02-12", 3, "Viral fever",            "Approved", 20, "2026-02-09", 23),
        (11, 9, "2026-01-15","2026-01-16", 2, "Home repair",            "Approved", 17, "2026-01-14", 22),
        (12,10, "2026-02-19","2026-02-20", 2, "Conference travel",      "Approved", 30, "2026-02-18", 23),
        (13,11, "2026-01-05","2026-01-08", 4, "Annual vacation",        "Approved", 23, "2026-01-03", 22),
        (14,12, "2026-02-25","2026-02-25", 1, "Doctor appointment",     "Approved", 11, "2026-02-24", 23),
        (15, 1, "2026-01-22","2026-01-22", 1, "Personal work",          "Approved", 23, "2026-01-21", 22),
        (16, 2, "2026-02-03","2026-02-04", 2, "Family emergency",       "Approved", 2,  "2026-02-02", 23),
        (17, 1, "2026-01-13","2026-01-13", 1, "Outstation",             "Approved", 27, "2026-01-12", 22),
        (18, 2, "2026-02-17","2026-02-18", 2, "Wedding function",       "Approved", 2,  "2026-02-16", 23),
        (19, 3, "2026-01-06","2026-01-07", 2, "Medical checkup",        "Approved", 2,  "2026-01-05", 22),
        (20, 4, "2026-02-09","2026-02-09", 1, "Personal",               "Approved", 30, "2026-02-08", 23),
        (21, 5, "2026-01-29","2026-01-30", 2, "Vehicle breakdown",      "Approved", 29, "2026-01-28", 22),
        (22, 6, "2026-03-10","2026-03-11", 2, "Annual leave",           "Pending",  None, None,        None),
        (23, 7, "2026-03-17","2026-03-17", 1, "Personal work",          "Pending",  None, None,        None),
        (24, 8, "2026-03-20","2026-03-21", 2, "Home renovation",        "Rejected", 2,   "2026-03-19", None),
        (25, 3, "2026-03-24","2026-03-26", 3, "Planned vacation",       "Pending",  None, None,        None),
    ]
    cur.executemany("""
        INSERT INTO leave_requests(emp_id, leave_type_id, start_date, end_date, days_requested, reason, status, approved_by, approved_at, period_id)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, leaves)
    conn.commit()
    print(f"  [✓] Inserted {len(leaves)} leave requests")


def insert_payroll_records(conn):
    """Generate payroll for 30 employees for periods 23 (Jan 2026) and 24 (Feb 2026)."""
    cur = conn.cursor()
    cur.execute("SELECT emp_id, grade_id, basic_salary FROM employees WHERE status='Active' LIMIT 30")
    emps = cur.fetchall()

    payrolls = []
    random.seed(99)

    for period_id, working_days in [(22, 27), (23, 24), (24, 27)]:  # Jan-Mar 2026
        for emp in emps:
            emp_id, grade_id, basic = emp[0], emp[1], emp[2]
            days_absent = random.randint(0, 2)
            days_leave  = random.randint(0, 1)
            days_present = working_days - days_absent - days_leave
            p = calc_payroll(basic, grade_id, working_days, days_present, days_absent, conn)

            pay_date = {22:"2026-01-31", 23:"2026-02-28", 24:"2026-03-31"}[period_id]
            payrolls.append((
                emp_id, period_id, 31 if period_id==22 else (28 if period_id==23 else 31),
                working_days, days_present, days_absent, days_leave,
                p["basic"], p["hra"], p["da"], p["ta"], 0,
                p["gross"], p["pf_emp"], p["pf_er"], p["esi_emp"], p["esi_er"],
                p["pt"], p["tds"], 0, 0, p["total_ded"], p["net"],
                "Paid", pay_date, f"NEFT{period_id}{emp_id:03d}", ""
            ))

    cur.executemany("""
        INSERT OR IGNORE INTO payroll_records(
            emp_id, period_id, total_days, working_days, days_present, days_absent, days_leave,
            basic_salary, hra, da, transport_allow, other_allowances,
            gross_salary, pf_employee, pf_employer, esi_employee, esi_employer,
            professional_tax, income_tax_tds, loan_deduction, other_deductions,
            total_deductions, net_salary, status, payment_date, payment_ref, remarks
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, payrolls)
    conn.commit()
    print(f"  [✓] Inserted {len(payrolls)} payroll records")


def insert_salary_revisions(conn):
    revisions = [
        (3,  45000, 65000,  3,  4, "2024-04-01", "Annual Increment 2024",    2),
        (7,  75000, 88000,  4,  5, "2024-04-01", "Annual Increment 2024",    2),
        (11,115000,135000,  5,  6, "2024-04-01", "Promotion to Tech Lead",   23),
        (13,165000,185000,  6,  7, "2024-07-01", "Mid-Year Promotion",       23),
        (24,440000,480000, 10, 11, "2024-04-01", "Annual Increment 2024",    23),
        (30,240000,265000,  8,  9, "2024-10-01", "Performance Increment",    23),
        (2, 110000,125000,  5,  6, "2025-04-01", "Annual Increment 2025",    23),
        (8,  65000, 72000,  4,  4, "2025-04-01", "Annual Increment 2025",    11),
        (10, 88000, 95000,  4,  5, "2025-04-01", "Annual Increment 2025",    30),
        (14, 58000, 62000,  3,  4, "2025-04-01", "Annual Increment 2025",    2),
        (18, 92000, 98000,  4,  5, "2025-04-01", "Annual Increment 2025",    30),
        (19, 68000, 73000,  4,  4, "2025-04-01", "Annual Increment 2025",    11),
        (20, 80000, 86000,  4,  5, "2025-04-01", "Annual Increment 2025",    30),
        (27, 86000, 92000,  4,  5, "2025-04-01", "Annual Increment 2025",    27),
        (29, 82000, 88000,  4,  5, "2025-04-01", "Annual Increment 2025",    19),
        (5,  35000, 38000,  2,  3, "2025-07-01", "Mid-Year Revision",        2),
        (6,  26000, 28000,  2,  2, "2025-07-01", "Mid-Year Revision",        14),
        (12, 39000, 42000,  3,  3, "2025-07-01", "Mid-Year Revision",        2),
        (15, 62000, 68000,  3,  4, "2025-10-01", "Performance Recognition",  27),
        (23,300000,325000, 13, 13, "2025-10-01", "Retention Bonus Revision", 23),
        (1,  42000, 45000,  2,  3, "2025-04-01", "Annual Increment 2025",    2),
        (9,  41000, 44000,  2,  3, "2025-04-01", "Annual Increment 2025",    17),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO salary_revisions(emp_id, old_basic, new_basic, old_grade_id, new_grade_id,
                                     effective_date, reason, approved_by)
        VALUES(?,?,?,?,?,?,?,?)
    """, revisions)
    conn.commit()
    print(f"  [✓] Inserted {len(revisions)} salary revisions")


def insert_loans(conn):
    loans = [
        (1,  100000, "2024-06-01",  5000, 24, 6, 70000,  "Home renovation",    "Active"),
        (3,   50000, "2024-08-01",  2500, 24, 7, 32500,  "Medical emergency",  "Active"),
        (5,   30000, "2024-05-01",  3000, 12, 9,  9000,  "Vehicle repair",     "Active"),
        (7,  200000, "2024-01-01", 10000, 24,12,120000,  "Home loan advance",  "Active"),
        (9,   25000, "2024-10-01",  2500, 12, 3, 17500,  "Education fee",      "Active"),
        (11, 300000, "2024-03-01", 15000, 24, 6,210000,  "Property advance",   "Active"),
        (13, 500000, "2024-02-01", 25000, 24, 6,350000,  "Business expansion", "Active"),
        (15,  80000, "2024-07-01",  4000, 24, 6, 56000,  "Car repair",         "Active"),
        (17, 400000, "2023-08-01", 20000, 24,18,120000,  "Home purchase",      "Active"),
        (19,  60000, "2024-09-01",  3000, 24, 5, 45000,  "Personal need",      "Active"),
        (21,  20000, "2024-11-01",  2000, 12, 2, 16000,  "Medical",            "Active"),
        (23, 750000, "2024-04-01", 37500, 24, 6,525000,  "Real estate",        "Active"),
        (25,  40000, "2024-12-01",  4000, 12, 0, 40000,  "Two-wheeler",        "Active"),
        (27, 150000, "2024-06-01",  7500, 24, 7,105000,  "Home repair",        "Active"),
        (29, 100000, "2024-07-01",  5000, 24, 7, 65000,  "Personal loan",      "Active"),
        (2,   75000, "2023-10-01",  6250, 12,12,     0,  "Laptop purchase",    "Closed"),
        (4,   15000, "2024-03-01",  1500, 12,10,  3000,  "Medical emergency",  "Active"),
        (6,   18000, "2024-04-01",  1500, 12, 8,  6000,  "Course fee",         "Active"),
        (8,  120000, "2024-05-01",  6000, 24, 8, 72000,  "Home deposit",       "Active"),
        (10, 250000, "2024-01-01", 12500, 24,12,150000,  "Vehicle",            "Active"),
        (12,  35000, "2024-08-01",  3500, 12, 5, 17500,  "Emergency",          "Active"),
        (14,  90000, "2024-06-01",  4500, 24, 8, 54000,  "Home improvement",   "Active"),
    ]
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO employee_loans(emp_id, loan_amount, loan_date, emi_amount, total_emis, emis_paid, outstanding, purpose, status)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, loans)
    conn.commit()
    print(f"  [✓] Inserted {len(loans)} employee loans")


def run_all():
    print("\n" + "=" * 60)
    print("  INSERTING SAMPLE DATA")
    print("=" * 60)

    conn = get_conn()

    insert_departments(conn)
    insert_salary_grades(conn)
    insert_designations(conn)
    insert_employees(conn)
    insert_payroll_periods(conn)
    insert_leave_types(conn)
    insert_deduction_types(conn)
    insert_tax_slabs(conn)
    insert_attendance(conn)
    insert_leave_requests(conn)
    insert_payroll_records(conn)
    insert_salary_revisions(conn)
    insert_loans(conn)

    conn.close()

    print("\n[✓] All sample data inserted successfully!\n")


if __name__ == "__main__":
    run_all()
