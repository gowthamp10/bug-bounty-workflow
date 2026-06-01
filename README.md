# Bug Bounty Agent Workflow

An automated bug-bounty workflow engine implemented in Python, designed for Linux-based environments. This tool automates five critical phases of security research and vulnerability discovery.

## 🚀 Project Overview

The engine is divided into 5 distinct phases, each managed by a semi-autonomous agent:

### [Phase 1: HTTP Mechanics & Recon Automation] ➔ Discovery Agent
- **Tools:** `subfinder`, `httpx`, `waybackurls`, `gau`, `amass` (deep scan).
- **Features:** Concurrent domain discovery, liveness probing, and deduplication.

### [Phase 2: Auth & IDOR Broken Logic] ➔ Authz Agent
- **Features:** Automated cross-user matrix testing using multiple sessions from `config/sessions.yaml`.
- **Detection:** Signal-based detection (Status Code, Body Hash, Content-Length) for IDOR and Auth bypass.

### [Phase 3: Server-Side Exploitation (SSRF)] ➔ OOB Agent
- **Features:** Integration with `interact.sh` and optional local listener (`--local`).
- **Payloads:** Automatic injection into Headers, URL Params, and JSON bodies.

### [Phase 4: Modern Tech Stack (GraphQL/APIs)] ➔ Schema Agent
- **GraphQL:** Introspection auditing and field guessing (clairvoyance-style).
- **REST:** OpenAPI/Swagger parsing and active endpoint discovery/fuzzing.

### [Phase 5: Advanced Smuggling & Race Windows] ➔ HTTP2 Agent
- **Techniques:** Single-packet race conditions, H2.CL and H2.TE desync probes.

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

### Interactive Agent Mode (Recommended)
```bash
python3 main.py --agent
```
This mode maintains state in `output/state.json`, allowing you to resume runs and decide which agent to trigger next based on suggestions.

### Standard Pipeline
```bash
python3 main.py --all -d example.com
```

### Specific Phase
```bash
python3 main.py --phase 1 -d example.com
```

---

## 📁 Directory Structure
```
bug-bounty-agent/
├── setup.sh
├── requirements.txt
├── config/
│   └── sessions.yaml
├── core/
│   ├── agents.py
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
