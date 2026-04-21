"""
TASK 02: Networking — API Data Transfer Simulation
Simulates HTTP/FTP data transfer, packet capture analysis,
and explains secure data flow for Payroll System.
"""
import http.server, socketserver, threading, urllib.request
import json, time, hashlib, base64, socket, ssl
from datetime import datetime
from pathlib import Path
import sqlite3

BASE = Path(__file__).parent
DB   = Path(__file__).parent.parent / "shared/database/payroll.db"
LOG  = BASE / "network_log.json"
PORT = 8765

# ── Payroll API Server ────────────────────────────────────────
PAYROLL_DATA_CACHE = {}

def get_payroll_data():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT pr.payroll_id, e.emp_code, e.first_name||' '||e.last_name name,
               d.dept_name, pr.gross_salary, pr.net_salary, pr.status,
               pp.period_name
        FROM payroll_records pr
        JOIN employees e ON pr.emp_id=e.emp_id
        JOIN departments d ON e.dept_id=d.dept_id
        JOIN payroll_periods pp ON pr.period_id=pp.period_id
        WHERE pr.period_id=24 LIMIT 10
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

class PayrollHTTPHandler(http.server.BaseHTTPRequestHandler):
    endpoints = {
        "/api/payroll":   lambda: get_payroll_data(),
        "/api/health":    lambda: {"status": "ok", "timestamp": datetime.now().isoformat()},
        "/api/employees": lambda: [{"id":1,"name":"Rajesh Kumar","dept":"HR"},
                                    {"id":2,"name":"Priya Sharma","dept":"HR"}],
    }

    def log_message(self, fmt, *args):
        pass  # Suppress default logging

    def do_GET(self):
        start = time.time()
        handler = self.endpoints.get(self.path)
        if handler:
            data = handler()
            body = json.dumps(data, default=str).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.send_header("X-Request-ID", hashlib.md5(f"{time.time()}".encode()).hexdigest()[:8])
            self.end_headers()
            self.wfile.write(body)
            _log_packet("HTTP GET", self.path, 200, len(body), time.time()-start)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = json.dumps({"received": len(body), "status": "created"}).encode()
        self.wfile.write(resp)
        _log_packet("HTTP POST", self.path, 201, content_length, 0)

# ── Packet Logger ─────────────────────────────────────────────
packets = []
def _log_packet(protocol, endpoint, status, size, latency_s):
    p = {
        "timestamp": datetime.now().isoformat(),
        "protocol": protocol,
        "endpoint": endpoint,
        "status_code": status,
        "payload_bytes": size,
        "latency_ms": round(latency_s * 1000, 2),
        "checksum": hashlib.md5(f"{endpoint}{status}{size}".encode()).hexdigest()[:8]
    }
    packets.append(p)
    return p

# ── FTP Simulation ─────────────────────────────────────────────
class FTPSimulator:
    """Simulates FTP-style file transfer operations."""
    def __init__(self, host="localhost", port=21):
        self.host = host; self.port = port
        self.transfer_log = []

    def simulate_connect(self):
        log = {"action":"CONNECT","host":self.host,"port":self.port,
               "status":"220 PayrollFTP Server Ready","ts":datetime.now().isoformat()}
        self.transfer_log.append(log)
        return log

    def simulate_upload(self, filename, data):
        size = len(data.encode())
        start = time.time()
        time.sleep(0.01)  # simulate transfer time
        latency = (time.time()-start)*1000
        log = {"action":"STOR","file":filename,"bytes":size,
               "status":"226 Transfer complete","latency_ms":round(latency,2),
               "ts":datetime.now().isoformat()}
        self.transfer_log.append(log)
        _log_packet("FTP STOR", f"/{filename}", 226, size, latency/1000)
        return log

    def simulate_download(self, filename):
        log = {"action":"RETR","file":filename,"status":"150 Opening data connection",
               "ts":datetime.now().isoformat()}
        self.transfer_log.append(log)
        return log

    def simulate_disconnect(self):
        log = {"action":"QUIT","status":"221 Goodbye","ts":datetime.now().isoformat()}
        self.transfer_log.append(log)
        return log

# ── Protocol Analysis ─────────────────────────────────────────
def analyze_protocols():
    return {
        "HTTP": {
            "port": 80, "secure_port": 443,
            "type": "Application Layer (L7)", "stateless": True,
            "payroll_use": "REST API for payroll data, employee records, reports",
            "security": "TLS/SSL encryption (HTTPS), JWT tokens, API keys",
            "methods": ["GET /api/payroll", "POST /api/payroll/generate",
                        "PATCH /api/employees/{id}/status"],
            "headers_used": ["Authorization: Bearer <JWT>",
                             "Content-Type: application/json",
                             "X-Request-ID: <uuid>"]
        },
        "FTP": {
            "port": 21, "data_port": 20,
            "type": "Application Layer (L7)", "stateful": True,
            "payroll_use": "Bulk CSV export of payroll registers, salary slips",
            "security": "FTPS (FTP over SSL) or SFTP (SSH-based)",
            "modes": ["Active (server connects to client)", "Passive (client connects)"],
            "commands": ["USER payroll_admin", "PASS ****", "STOR payroll_march.csv",
                         "RETR salary_report.csv", "QUIT"]
        },
        "TCP_IP": {
            "type": "Transport + Network Layer",
            "payroll_use": "Reliable delivery of payroll records between microservices",
            "features": ["Ordered delivery", "Error correction", "Flow control"],
            "port_range": "1024-65535 (ephemeral for clients)"
        },
        "TLS": {
            "version": "TLS 1.3",
            "payroll_use": "Encrypt PAN numbers, salary data, bank account info",
            "handshake": ["Client Hello", "Server Hello + Certificate",
                          "Key Exchange", "Finished (symmetric encryption)"],
            "cipher_suite": "TLS_AES_256_GCM_SHA384"
        }
    }

# ── Data Flow Explanation ──────────────────────────────────────
def explain_secure_data_flow():
    return """
╔══════════════════════════════════════════════════════════════╗
║     PAYROLL SYSTEM — SECURE DATA FLOW DIAGRAM                ║
╚══════════════════════════════════════════════════════════════╝

[HR Admin Browser]
        │  HTTPS (TLS 1.3)
        ▼
[Load Balancer / WAF]  ← blocks SQL injection, XSS
        │
        ▼
[Flask REST API Server]  ← validates JWT token
        │  Internal TCP (trusted network)
        ▼
[SQLite / PostgreSQL DB]  ← encrypted at rest (AES-256)
        │
        ├─── [Reports API] → HTTPS → [HR Dashboard]
        │
        ├─── [Payslip PDF] → SFTP → [Employee Portal]
        │
        └─── [Payroll Export] → S3 (HTTPS) → [Finance Dept]

SECURITY LAYERS:
  1. Network:    HTTPS/TLS 1.3, VPN tunneling
  2. Auth:       JWT Bearer tokens, API keys
  3. Transport:  Checksum verification, packet integrity
  4. Storage:    AES-256 encryption at rest
  5. Audit:      Every API call logged with IP + timestamp
"""

# ── Run Simulation ────────────────────────────────────────────
def run():
    print("="*60)
    print("  TASK 02: Networking — API & Protocol Simulation")
    print("="*60)

    # Start HTTP server in thread
    server = socketserver.TCPServer(("", PORT), PayrollHTTPHandler, bind_and_activate=False)
    server.allow_reuse_address = True
    server.server_bind(); server.server_activate()
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"\n[+] HTTP API Server started on port {PORT}")

    # Make HTTP requests
    print("\n── HTTP Request Simulation ──────────────────")
    for endpoint in ["/api/health", "/api/payroll", "/api/employees"]:
        try:
            start = time.time()
            with urllib.request.urlopen(f"http://localhost:{PORT}{endpoint}") as resp:
                data = json.loads(resp.read())
                lat  = (time.time()-start)*1000
                print(f"  GET {endpoint:20} → {resp.status} ({lat:.1f}ms)")
        except Exception as e:
            print(f"  GET {endpoint:20} → ERROR: {e}")

    # POST simulation
    req = urllib.request.Request(
        f"http://localhost:{PORT}/api/payroll",
        data=json.dumps({"action":"generate","period":"April 2026"}).encode(),
        headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        print(f"  POST /api/payroll          → {resp.status}")

    server.shutdown()

    # FTP simulation
    print("\n── FTP Transfer Simulation ──────────────────")
    ftp = FTPSimulator()
    print(f"  {ftp.simulate_connect()['status']}")
    r = ftp.simulate_upload("payroll_march2026.csv",
                            "emp_code,net_salary\nEMP001,62363.33\nEMP002,172166.67")
    print(f"  STOR {r['file']} → {r['status']} ({r['bytes']} bytes, {r['latency_ms']}ms)")
    r = ftp.simulate_download("salary_report.pdf")
    print(f"  RETR salary_report.pdf → {r['status']}")
    print(f"  {ftp.simulate_disconnect()['status']}")

    # Protocol analysis
    print("\n── Protocol Analysis ────────────────────────")
    protocols = analyze_protocols()
    for name, info in protocols.items():
        print(f"  {name}: {info.get('payroll_use','')[:60]}")

    # Secure data flow
    print(explain_secure_data_flow())

    # Packet capture summary
    print("\n── Captured Packets ─────────────────────────")
    print(f"  {'Protocol':<12} {'Endpoint':<25} {'Status':>6} {'Bytes':>8} {'Latency':>10}")
    print("  " + "-"*65)
    for p in packets:
        print(f"  {p['protocol']:<12} {p['endpoint']:<25} {p['status_code']:>6} {p['payload_bytes']:>8} {p['latency_ms']:>9.1f}ms")

    # Save results
    result = {"packets": packets, "protocols": protocols,
              "ftp_log": ftp.transfer_log, "timestamp": datetime.now().isoformat()}
    LOG.write_text(json.dumps(result, indent=2, default=str))
    print(f"\n✓ Network log saved: {LOG}")
    return result

if __name__ == "__main__":
    run()
