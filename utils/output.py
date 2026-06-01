import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

FINDINGS_FILE = "output/findings.json"

def ensure_output_dir(domain: str) -> Path:
    """Ensures the output directory for a specific domain exists."""
    path = Path(f"output/{domain}")
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_finding(phase: int, severity: str, url: str, title: str, evidence: Any):
    """Saves a finding to the unified findings.json file."""
    finding = {
        "phase": phase,
        "severity": severity,
        "url": url,
        "title": title,
        "evidence": evidence,
        "timestamp": datetime.now().isoformat()
    }

    findings = []
    if os.path.exists(FINDINGS_FILE):
        try:
            with open(FINDINGS_FILE, "r") as f:
                findings = json.load(f)
        except json.JSONDecodeError:
            findings = []

    findings.append(finding)

    # Ensure output dir exists for findings.json
    os.makedirs(os.path.dirname(FINDINGS_FILE), exist_ok=True)

    with open(FINDINGS_FILE, "w") as f:
        json.dump(findings, f, indent=4)

def write_list_to_file(filepath: str, items: list):
    """Writes a list of strings to a file, one per line."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        for item in items:
            f.write(f"{item}\n")

def append_to_live_hosts(host: str):
    """Appends a host to the global live_hosts.txt file."""
    live_hosts_path = "output/live_hosts.txt"
    os.makedirs(os.path.dirname(live_hosts_path), exist_ok=True)
    with open(live_hosts_path, "a") as f:
        f.write(f"{host}\n")
