import asyncio
import os
from pathlib import Path
from core.agents import BaseAgent, AgentState
from utils.logger import logger
from utils.output import ensure_output_dir, write_list_to_file

class DiscoveryAgent(BaseAgent):
    def __init__(self, dry_run=False, deep=False, concurrency=5):
        super().__init__("Discovery", 1, dry_run)
        self.deep = deep
        self.concurrency = concurrency
        self.go_bin = os.path.join(os.path.expanduser("~"), "go", "bin")
        self.env = os.environ.copy()
        self.env["PATH"] = f"{self.go_bin}:{self.env.get('PATH', '')}"

    async def run_command(self, cmd, input_data=None):
        if self.dry_run:
            logger.debug(f"[DRY RUN] Executing: {' '.join(cmd)}")
            return ""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env
            )
            stdout, stderr = await process.communicate(input=input_data.encode() if input_data else None)
            return stdout.decode()
        except Exception as e:
            logger.error(f"Error running command {' '.join(cmd)}: {e}")
            return ""

    async def process_domain(self, domain, state):
        logger.info(f"[*] Discovering assets for {domain}...")

        # Subdomains
        subfinder_out = await self.run_command(["subfinder", "-d", domain, "-silent"])
        subdomains = set(subfinder_out.splitlines())
        if self.deep:
            amass_out = await self.run_command(["amass", "enum", "-d", domain, "-passive"])
            subdomains.update(amass_out.splitlines())

        # URLs
        wayback_out = await self.run_command(["waybackurls"], input_data=domain)
        gau_out = await self.run_command(["gau", "--subs", domain])
        urls = set(wayback_out.splitlines())
        urls.update(gau_out.splitlines())

        # Liveness
        live_hosts = []
        if subdomains:
            httpx_out = await self.run_command(["httpx", "-silent"], input_data="\n".join(subdomains))
            live_hosts = [line.strip() for line in httpx_out.splitlines() if line.strip()]

        return sorted(list(subdomains)), sorted(list(urls)), sorted(live_hosts)

    async def run(self, state: AgentState) -> AgentState:
        domains = []
        if state.domain:
            domains.append(state.domain)
        # Assuming state.config might have a domain file path or domains list
        if state.config.get("domain_file"):
            with open(state.config["domain_file"], "r") as f:
                domains.extend([line.strip() for line in f if line.strip()])

        if not domains:
            logger.error("No domains found to process in DiscoveryAgent")
            return state

        logger.info(f"[*] DiscoveryAgent starting for {len(domains)} domains (concurrency={self.concurrency})...")

        semaphore = asyncio.Semaphore(self.concurrency)
        async def sem_process(domain):
            async with semaphore:
                return await self.process_domain(domain, state)

        results = await asyncio.gather(*[sem_process(d) for d in domains])

        all_subdomains = set(state.subdomains)
        all_urls = set(state.urls)
        all_live_hosts = set(state.live_hosts)

        for subs, urls, live in results:
            all_subdomains.update(subs)
            all_urls.update(urls)
            all_live_hosts.update(live)

        state.subdomains = sorted(list(all_subdomains))
        state.urls = sorted(list(all_urls))
        state.live_hosts = sorted(list(all_live_hosts))

        state.completed_phases.append(1)
        state.save()
        return state

    def suggest_next_step(self, state: AgentState) -> tuple[int, str]:
        if state.live_hosts:
            return (2, f"Discovered {len(state.live_hosts)} live hosts → Authorization Tester recommended.")
        return (None, "")
