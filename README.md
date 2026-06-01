
=======
# Bug Bounty Agent Workflow

An automated bug-bounty workflow engine implemented in Python, designed for Linux-based environments. This tool automates five critical phases of security research and vulnerability discovery.

## 🚀 Project Overview

The engine is divided into 5 distinct phases:

### [Phase 1: HTTP Mechanics & Recon Automation] ➔ Build: Asset Discovery Engine
- **Tools:** `subfinder`, `httpx`, `waybackurls`, `gau`, `amass` (deep scan).
- **Features:** Concurrent domain discovery, liveness probing, deduplication, and automatic pipe to subsequent phases.
- **Output:** `output/live_hosts.txt` and domain-specific JSON/TXT files.

### [Phase 2: Auth & IDOR Broken Logic] ➔ Build: Context-Aware Authorization Tester
- **Features:** Automated cross-user matrix testing using multiple sessions from `config/sessions.yaml`.
- **Detection:** Signal-based detection (Status Code, Body Hash, Content-Length) for IDOR and Auth bypass.
- **Output:** `output/findings.json` (Unified Schema).

### [Phase 3: Server-Side Exploitation (SSRF)] ➔ Build: Out-of-Band (OOB) Interaction Monitor
- **Features:** Integration with `interact.sh` and optional local listener (`--local`).
- **Payloads:** Automatic injection into Headers, URL Params, and JSON bodies.
- **Monitoring:** Real-time polling for OOB interactions.

### [Phase 4: Modern Tech Stack (GraphQL/APIs)] ➔ Build: Schema Auditor & Endpoint Fuzzer
- **GraphQL:** Introspection auditing and field guessing (clairvoyance-style).
- **REST:** OpenAPI/Swagger parsing and active endpoint discovery/fuzzing.
- **Vulnerabilities:** Unauth access, method overrides, mass assignment.

### [Phase 5: Advanced Smuggling & Race Windows] ➔ Build: Concurrent HTTP/2 Request Engine
- **Techniques:** Single-packet race conditions, H2.CL and H2.TE desync probes.
- **Performance:** Async execution using `httpx` with HTTP/2 support.

---

## 🛠 Installation & Setup

### Prerequisites
- Python 3.8+
- Go (latest version recommended)
- Linux-based environment

### Quick Start
1. Clone the repository.
2. Run the setup script to install Go tools and Python dependencies:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
3. Configure your sessions in `config/sessions.yaml`.

---

## 📖 Usage

### Run All Phases (Pipeline)
```bash
python3 main.py --all -d example.com
```

### Run Specific Phase
```bash
python3 main.py --phase 1 -d example.com
python3 main.py --phase 2 --config config/sessions.yaml
python3 main.py --phase 5 -u https://api.example.com
```

### Options
- `--deep`: Enable deep discovery in Phase 1 (invokes `amass`).
- `--dry-run`: Print actions without sending requests.
- `--poll-interval <seconds>`: Set OOB polling interval (default: 10).

---

## 📁 Directory Structure
```
bug-bounty-agent/
├── setup.sh
├── requirements.txt
├── config/
│   └── sessions.yaml
├── core/
│   ├── phase1_discovery.py
│   ├── phase2_authz.py
│   ├── phase3_oob.py
│   ├── phase4_schema.py
│   └── phase5_http2.py
├── utils/
│   ├── logger.py
│   ├── output.py
│   └── wordlists/
└── main.py
```
>>>>>>> e4ac5a7 (Implement 5-phase bug-bounty workflow engine)
