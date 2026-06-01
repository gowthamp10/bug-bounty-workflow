import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
from utils.logger import logger

@dataclass
class AgentState:
    domain: Optional[str] = None
    subdomains: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    live_hosts: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    completed_phases: List[int] = field(default_factory=list)
    current_phase: int = 0
    config: Dict[str, Any] = field(default_factory=dict)

    def save(self, filepath: str = "output/state.json"):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=4)
        logger.debug(f"State saved to {filepath}")

    @classmethod
    def load(cls, filepath: str = "output/state.json") -> Optional['AgentState']:
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None

class BaseAgent:
    def __init__(self, name: str, phase_id: int, dry_run: bool = False):
        self.name = name
        self.phase_id = phase_id
        self.dry_run = dry_run

    async def run(self, state: AgentState) -> AgentState:
        raise NotImplementedError("Agents must implement run()")

    def suggest_next_step(self, state: AgentState) -> Optional[tuple[int, str]]:
        """Returns (phase_id, reason) for the suggested next agent."""
        return None
