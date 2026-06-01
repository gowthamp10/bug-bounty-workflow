import asyncio
import httpx
import yaml
import hashlib
import os
from core.agents import BaseAgent, AgentState
from utils.logger import logger, log_severity
from utils.output import save_finding

class AuthzAgent(BaseAgent):
    def __init__(self, dry_run=False, config_path="config/sessions.yaml"):
        super().__init__("Authz", 2, dry_run)
        self.config_path = config_path
        self.threshold = 50

    def get_client_for_session(self, session):
        headers = session.get("headers", {}).copy()
        if "tokens" in session:
            headers.update(session["tokens"])
        return httpx.AsyncClient(
            headers=headers,
            cookies=session.get("cookies", {}),
            follow_redirects=True,
            verify=False,
            timeout=10.0
        )

    async def run(self, state: AgentState) -> AgentState:
        if not state.live_hosts:
            logger.warning("No live hosts in state for AuthzAgent")
            return state

        sessions = []
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                sessions = yaml.safe_load(f) or []

        if len(sessions) < 2:
            logger.warning("AuthzAgent needs at least 2 sessions in config/sessions.yaml")
            return state

        # Session 0 is treated as the resource owner. All other sessions are
        # tested as potential attackers against Session 0's URLs.
        owner = sessions[0]
        attackers = sessions[1:]

        logger.info(f"[*] AuthzAgent starting on {len(state.live_hosts)} hosts...")

        for url in state.live_hosts:
            if self.dry_run:
                logger.info(f"[DRY RUN] Authz test on {url}")
                continue

            async with self.get_client_for_session(owner) as owner_client:
                try:
                    owner_resp = await owner_client.get(url)
                    if owner_resp.status_code >= 400: continue

                    for attacker in attackers:
                        async with self.get_client_for_session(attacker) as attacker_client:
                            attacker_resp = await attacker_client.get(url)

                            # Signals
                            status_match = owner_resp.status_code == attacker_resp.status_code
                            owner_hash = hashlib.sha256(owner_resp.content).hexdigest()
                            attacker_hash = hashlib.sha256(attacker_resp.content).hexdigest()
                            hash_match = owner_hash == attacker_hash

                            len_diff = abs(len(owner_resp.content) - len(attacker_resp.content))
                            len_similar = len_diff < self.threshold

                            # Logic as per specific instruction:
                            # Confirmed bypass = status diff AND body hash diff.
                            # Note: This is counter-intuitive for IDOR (usually similarity is the bypass),
                            # but follows the "Phase 2 code review fixes" instruction #4 in the addendum.
                            if (not status_match) and (not hash_match):
                                save_finding(2, "HIGH", url, "Confirmed IDOR (Signal Diff)", {"attacker": attacker["name"]})
                            elif (not status_match) or (not hash_match) or (not len_similar):
                                save_finding(2, "MEDIUM", url, "Potential IDOR (Signal Mismatch)", {"attacker": attacker["name"]})

                except Exception as e:
                    logger.debug(f"Authz error on {url}: {e}")

        state.completed_phases.append(2)
        state.save()
        return state

    def suggest_next_step(self, state: AgentState) -> tuple[int, str]:
        return (3, "In-depth interaction monitoring recommended to find SSRF/OOB vulnerabilities.")
