import asyncio
import httpx
from core.agents import BaseAgent, AgentState
from utils.logger import logger, log_severity
from utils.output import save_finding

class HTTP2Agent(BaseAgent):
    def __init__(self, dry_run=False, concurrency=20):
        super().__init__("HTTP2", 5, dry_run)
        self.concurrency = concurrency

    async def race_condition_test(self, url):
        logger.info(f"[*] Testing race conditions at {url}")
        if self.dry_run:
            logger.info(f"[DRY RUN] Race test on {url}")
            return
        async with httpx.AsyncClient(http2=True, verify=False, timeout=10.0) as client:
            tasks = [client.post(url, json={"race": i}) for i in range(10)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            codes = [r.status_code for r in responses if isinstance(r, httpx.Response)]
            if len(set(codes)) > 1:
                save_finding(5, "MEDIUM", url, "Race Condition Response Inconsistency", {"codes": list(set(codes))})

    async def h2_desync_probe(self, url):
        logger.info(f"[*] H2 Desync probe at {url}")
        if self.dry_run: return
        async with httpx.AsyncClient(http2=True, verify=False, timeout=10.0) as client:
            try:
                # H2.TE probe
                resp = await client.post(url, headers={"Transfer-Encoding": "chunked"}, content="0\r\n\r\n")
                if resp.status_code == 200:
                    save_finding(5, "HIGH", url, "Potential H2.TE Desync", "")
            except Exception: pass

    async def run(self, state: AgentState) -> AgentState:
        if not state.live_hosts:
            logger.warning("No live hosts for HTTP2Agent")
            return state

        logger.info(f"[*] HTTP2Agent starting on {len(state.live_hosts)} hosts...")
        for url in state.live_hosts:
            await self.h2_desync_probe(url)
            await self.race_condition_test(url)

        state.completed_phases.append(5)
        state.save()
        return state

    def suggest_next_step(self, state: AgentState) -> tuple[int, str]:
        return (None, "All phases completed. Review findings in output/findings.json")
