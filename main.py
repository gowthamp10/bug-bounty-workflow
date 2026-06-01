import asyncio
import argparse
import os
import sys
from utils.logger import logger, setup_logger
from core.phase1_discovery import AssetDiscoveryEngine
from core.phase2_authz import AuthzTester
from core.phase3_oob import OOBMonitor
from core.phase4_schema import SchemaAuditor
from core.phase5_http2 import HTTP2Engine

def parse_args():
    parser = argparse.ArgumentParser(description="Bug Bounty Agent Workflow Engine")

    # Global flags
    parser.add_argument("--all", action="store_true", help="Run all phases in a pipeline")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], help="Run a specific phase")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no actual requests)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Input options
    parser.add_argument("-d", "--domain", help="Target domain for Phase 1")
    parser.add_argument("-f", "--file", help="Target file (domains or URLs depending on phase)")
    parser.add_argument("-u", "--url", help="Target URL for specific phases")

    # Phase 1 options
    parser.add_argument("--deep", action="store_true", help="Enable deep discovery (amass) in Phase 1")

    # Phase 2 options
    parser.add_argument("--config", default="config/sessions.yaml", help="Sessions config file for Phase 2")

    # Phase 3 options
    parser.add_argument("--poll-interval", type=int, default=10, help="OOB polling interval (seconds)")
    parser.add_argument("--local", action="store_true", help="Enable local HTTP listener for Phase 3")

    # Phase 4 options
    parser.add_argument("--swagger", help="OpenAPI/Swagger spec URL or path for Phase 4")

    # Phase 5 options
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrency for Phase 5")

    return parser.parse_args()

async def main():
    args = parse_args()

    log_level = "DEBUG" if args.debug else "INFO"
    setup_logger(level=log_level)

    if args.dry_run:
        logger.info("[!] DRY RUN MODE ENABLED")

    live_hosts_file = "output/live_hosts.txt"

    # Pipeline mode precedence handling
    if args.all:
        if args.url or (args.file and args.phase is None):
            logger.warning("[!] Pipeline mode (--all) takes precedence. Input URL/File may be ignored for some phases.")

        if not args.domain and not args.file:
            logger.error("[-] Domain (-d) or domain list (-f) required for --all mode.")
            sys.exit(1)

        # Phase 1: Discovery
        logger.info("[*] --- Phase 1: Asset Discovery ---")
        p1 = AssetDiscoveryEngine(domain=args.domain, domain_file=args.file, deep=args.deep, dry_run=args.dry_run)
        await p1.run()

        # Load live hosts for subsequent phases
        targets = []
        if os.path.exists(live_hosts_file):
            with open(live_hosts_file, "r") as f:
                targets = [line.strip() for line in f if line.strip()]

        if not targets and not args.dry_run:
            logger.warning("[-] No live hosts found in Phase 1. Pipeline might stop.")

        # Phase 2: Authz
        logger.info("[*] --- Phase 2: Authorization Tester ---")
        p2 = AuthzTester(config_path=args.config, urls=targets, dry_run=args.dry_run)
        await p2.run()

        # Phase 3: OOB
        logger.info("[*] --- Phase 3: OOB Monitor ---")
        p3 = OOBMonitor(poll_interval=args.poll_interval, dry_run=args.dry_run, local_mode=args.local)
        await p3.run(target_urls=targets)

        # Phase 4: Schema
        logger.info("[*] --- Phase 4: Schema Auditor ---")
        p4 = SchemaAuditor(dry_run=args.dry_run)
        await p4.run(targets, swagger_url=args.swagger)

        # Phase 5: HTTP/2
        logger.info("[*] --- Phase 5: HTTP/2 Engine ---")
        p5 = HTTP2Engine(concurrency=args.concurrency, dry_run=args.dry_run)
        await p5.run(targets)

    elif args.phase:
        if args.phase == 1:
            p1 = AssetDiscoveryEngine(domain=args.domain, domain_file=args.file, deep=args.deep, dry_run=args.dry_run)
            await p1.run()
        elif args.phase == 2:
            targets = [args.url] if args.url else []
            if args.file:
                with open(args.file, "r") as f:
                    targets.extend([line.strip() for line in f if line.strip()])
            p2 = AuthzTester(config_path=args.config, urls=targets, dry_run=args.dry_run)
            await p2.run()
        elif args.phase == 3:
            targets = [args.url] if args.url else []
            if args.file:
                with open(args.file, "r") as f:
                    targets.extend([line.strip() for line in f if line.strip()])
            p3 = OOBMonitor(poll_interval=args.poll_interval, dry_run=args.dry_run, local_mode=args.local)
            await p3.run(target_urls=targets)
        elif args.phase == 4:
            targets = [args.url] if args.url else []
            if args.file:
                with open(args.file, "r") as f:
                    targets.extend([line.strip() for line in f if line.strip()])
            p4 = SchemaAuditor(dry_run=args.dry_run)
            await p4.run(targets, swagger_url=args.swagger)
        elif args.phase == 5:
            targets = [args.url] if args.url else []
            if args.file:
                with open(args.file, "r") as f:
                    targets.extend([line.strip() for line in f if line.strip()])
            p5 = HTTP2Engine(concurrency=args.concurrency, dry_run=args.dry_run)
            await p5.run(targets)
    else:
        logger.error("[-] Please specify --all or --phase <1-5>")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
