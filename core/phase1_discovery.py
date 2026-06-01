import asyncio
import subprocess
import os
from pathlib import Path
from utils.logger import logger, console
from utils.output import ensure_output_dir, write_list_to_file, append_to_live_hosts

class AssetDiscoveryEngine:
    def __init__(self, domain=None, domain_file=None, deep=False, dry_run=False):
        self.domains = []
        if domain:
            self.domains.append(domain)
        if domain_file:
            with open(domain_file, "r") as f:
                self.domains.extend([line.strip() for line in f if line.strip()])
        self.deep = deep
        self.dry_run = dry_run
        self.go_bin = os.path.join(os.path.expanduser("~"), "go", "bin")
        self.env = os.environ.copy()
        self.env["PATH"] = f"{self.go_bin}:{self.env.get('PATH', '')}"

    async def run_command(self, cmd, input_data=None):
        if self.dry_run:
            logger.info(f"[DRY RUN] Executing: {' '.join(cmd)}")
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
            if process.returncode != 0:
                logger.warning(f"Command {' '.join(cmd)} failed with exit code {process.returncode}")
                # logger.debug(f"Stderr: {stderr.decode()}")
            return stdout.decode()
        except Exception as e:
            logger.error(f"Error running command {' '.join(cmd)}: {e}")
            return ""

    async def discover_subdomains(self, domain):
        logger.info(f"Discovering subdomains for {domain}...")

        # Subfinder
        subfinder_out = await self.run_command(["subfinder", "-d", domain, "-silent"])
        subdomains = set(subfinder_out.splitlines())

        # Amass (Deep)
        if self.deep:
            logger.info(f"Running deep scan with amass for {domain}...")
            amass_out = await self.run_command(["amass", "enum", "-d", domain, "-passive"])
            subdomains.update(amass_out.splitlines())

        return subdomains

    async def discover_urls(self, domain):
        logger.info(f"Discovering URLs for {domain}...")

        # waybackurls
        wayback_out = await self.run_command(["waybackurls"], input_data=domain)

        # gau
        gau_out = await self.run_command(["gau", "--subs", domain])

        urls = set(wayback_out.splitlines())
        urls.update(gau_out.splitlines())
        return urls

    async def probe_liveness(self, subdomains):
        if not subdomains:
            return []

        logger.info(f"Probing liveness for {len(subdomains)} subdomains...")
        input_data = "\n".join(subdomains)
        httpx_out = await self.run_command(["httpx", "-silent", "-status-code", "-title"], input_data=input_data)

        live_hosts = []
        for line in httpx_out.splitlines():
            if line.strip():
                # httpx output with -status-code usually looks like: https://sub.domain.com [200] [Title]
                host = line.split(" ")[0]
                live_hosts.append(host)
        return live_hosts

    async def process_domain(self, domain):
        out_dir = ensure_output_dir(domain)

        # 1. Subdomains
        subdomains = await self.discover_subdomains(domain)
        write_list_to_file(str(out_dir / "subdomains.txt"), sorted(list(subdomains)))

        # 2. URLs
        urls = await self.discover_urls(domain)
        write_list_to_file(str(out_dir / "urls.txt"), sorted(list(urls)))

        # 3. Liveness
        live_hosts = await self.probe_liveness(list(subdomains))
        write_list_to_file(str(out_dir / "live_hosts.txt"), sorted(live_hosts))

        # 4. Global live hosts
        for host in live_hosts:
            append_to_live_hosts(host)

        logger.info(f"Finished processing {domain}. Found {len(subdomains)} subdomains, {len(urls)} URLs, and {len(live_hosts)} live hosts.")
        return live_hosts

    async def run(self):
        # Clear global live hosts if not dry run
        if not self.dry_run:
            live_hosts_path = "output/live_hosts.txt"
            if os.path.exists(live_hosts_path):
                os.remove(live_hosts_path)

        tasks = [self.process_domain(d) for d in self.domains]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--domain")
    parser.add_argument("-f", "--file")
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = AssetDiscoveryEngine(domain=args.domain, domain_file=args.file, deep=args.deep, dry_run=args.dry_run)
    asyncio.run(engine.run())
