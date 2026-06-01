import asyncio
import httpx
import os
import json
import yaml
from core.agents import BaseAgent, AgentState
from utils.logger import logger, log_severity
from utils.output import save_finding

class SchemaAgent(BaseAgent):
    def __init__(self, dry_run=False, swagger_url=None):
        super().__init__("Schema", 4, dry_run)
        self.swagger_url = swagger_url
        self.wordlist_path = "utils/wordlists/graphql_fields.txt"
        self.graphql_wordlist = []
        if os.path.exists(self.wordlist_path):
            with open(self.wordlist_path, "r") as f:
                self.graphql_wordlist = [line.strip() for line in f if line.strip()]

    async def parse_swagger(self, url):
        logger.info(f"[*] Attempting to parse Swagger/OpenAPI spec from {url}")
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    try:
                        spec = resp.json()
                    except:
                        spec = yaml.safe_load(resp.text)

                    paths = spec.get("paths", {})
                    logger.info(f"[+] Found {len(paths)} endpoints in Swagger spec.")
                    return list(paths.keys())
        except Exception as e:
            logger.error(f"Failed to parse Swagger: {e}")
        return []

    async def audit_graphql(self, url):
        logger.info(f"[*] Auditing GraphQL: {url}")
        introspection_query = {"query": "{__schema{queryType{name}}}"}
        if self.dry_run:
            logger.debug(f"[DRY RUN] Introspection on {url}")
            return
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            try:
                resp = await client.post(url, json=introspection_query)
                if resp.status_code == 200 and "__schema" in resp.text:
                    save_finding(4, "MEDIUM", url, "GraphQL Introspection Enabled", "Schema accessible")
                else:
                    logger.info(f"[-] Introspection disabled for {url}, falling back to field guessing.")
                    # Batch guessing logic
                    batch = self.graphql_wordlist[:20]
                    await client.post(url, json={"query": f"{{ {' '.join(batch)} }}"})
            except Exception: pass

    async def run(self, state: AgentState) -> AgentState:
        if not state.live_hosts:
            logger.warning("No live hosts for SchemaAgent")
            return state

        swagger_endpoints = []
        if self.swagger_url:
            swagger_endpoints = await self.parse_swagger(self.swagger_url)

        logger.info(f"[*] SchemaAgent starting on {len(state.live_hosts)} hosts...")
        for url in state.live_hosts:
            if "graphql" in url.lower():
                await self.audit_graphql(url)
            else:
                # Fuzz common paths and discovered swagger paths
                targets = ["/api/v1", "/api/v2", "/swagger.json", "/api-docs"] + swagger_endpoints
                for p in targets:
                    target_url = url.rstrip("/") + (p if p.startswith("/") else "/" + p)
                    if self.dry_run:
                        logger.debug(f"[DRY RUN] Probing {target_url}")
                        continue
                    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                        try:
                            resp = await client.get(target_url)
                            if resp.status_code < 400:
                                save_finding(4, "INFO", target_url, "Discovered API Endpoint", f"Status: {resp.status_code}")
                        except Exception: pass

        state.completed_phases.append(4)
        state.save()
        return state

    def suggest_next_step(self, state: AgentState) -> tuple[int, str]:
        return (5, "Concurrent HTTP/2 request engine recommended to test for race conditions.")
