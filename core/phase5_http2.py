import asyncio
import httpx
from utils.logger import logger, log_severity
from utils.output import save_finding

class HTTP2Engine:
    def __init__(self, concurrency=20, dry_run=False):
        self.concurrency = concurrency
        self.dry_run = dry_run

    async def race_condition_test(self, url, count=10):
        logger.info(f"[*] Testing for race conditions at {url} with {count} concurrent requests.")

        if self.dry_run:
            logger.info(f"[DRY RUN] Sending {count} concurrent HTTP/2 requests to {url}")
            return

        # Using a single AsyncClient with HTTP/2 enabled.
        # While httpx doesn't give us low-level frame bundling control,
        # using a single client and asyncio.gather is the closest we get in standard Python libs.
        async with httpx.AsyncClient(http2=True, verify=False, timeout=20.0) as client:
            # We "warm up" the connection first
            try:
                await client.get(url)
            except Exception:
                pass

            tasks = [client.post(url, json={"action": "transfer", "amount": 1, "race": i}) for i in range(count)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            status_codes = [r.status_code for r in responses if isinstance(r, httpx.Response)]
            if len(set(status_codes)) > 1:
                severity = "MEDIUM"
                title = "Inconsistent Race Condition Responses"
                log_severity(severity, f"{title} at {url}: {set(status_codes)}")
                save_finding(5, severity, url, title, {"status_codes": list(set(status_codes))})

    async def h2_desync_probe(self, url):
        logger.info(f"[*] Probing for HTTP/2 desync (H2.CL / H2.TE) at {url}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Sending H2.CL and H2.TE desync probes to {url}")
            return

        async with httpx.AsyncClient(http2=True, verify=False, timeout=10.0) as client:
            # H2.CL probe: Content-Length header != DATA frame length
            try:
                # We send a body that is longer than CL
                resp = await client.post(url, headers={"Content-Length": "1"}, content="smuggle=true")
                if resp.status_code == 400:
                    logger.debug(f"H2.CL probe (Short CL) returned 400 for {url}")
            except Exception:
                pass

            # H2.TE probe: HTTP/2 with Transfer-Encoding
            try:
                resp = await client.post(url, headers={"Transfer-Encoding": "chunked"}, content="0\r\n\r\n")
                if resp.status_code == 200:
                    severity = "HIGH"
                    title = "Potential H2.TE Desync"
                    log_severity(severity, f"{title} at {url}")
                    save_finding(5, severity, url, title, "Backend accepted Transfer-Encoding over HTTP/2")
            except Exception:
                pass

    async def run_on_target(self, url):
        await self.h2_desync_probe(url)
        await self.race_condition_test(url)

    async def run(self, targets):
        # Apply concurrency limit at the target level
        semaphore = asyncio.Semaphore(self.concurrency)

        async def sem_run(target):
            async with semaphore:
                await self.run_on_target(target)

        tasks = [sem_run(target) for target in targets]
        if tasks:
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url")
    parser.add_argument("-f", "--file")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        with open(args.file, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    engine = HTTP2Engine(concurrency=args.concurrency, dry_run=args.dry_run)
    asyncio.run(engine.run(urls))
