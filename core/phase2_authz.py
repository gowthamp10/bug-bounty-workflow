import asyncio
import httpx
import yaml
import hashlib
import os
from utils.logger import logger, log_severity
from utils.output import save_finding

class AuthzTester:
    def __init__(self, config_path=None, urls=None, dry_run=False, threshold=50):
        self.sessions = []
        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.sessions = yaml.safe_load(f) or []

        self.urls = urls or []
        self.dry_run = dry_run
        self.threshold = threshold

    def add_session(self, name, headers=None, cookies=None):
        self.sessions.append({
            "name": name,
            "headers": headers or {},
            "cookies": cookies or {}
        })

    def get_client_for_session(self, session):
        headers = session.get("headers", {}).copy()
        # Merge tokens into headers
        if "tokens" in session:
            headers.update(session["tokens"])

        return httpx.AsyncClient(
            headers=headers,
            cookies=session.get("cookies", {}),
            follow_redirects=True,
            verify=False,
            timeout=10.0
        )

    async def test_url(self, url, owner_session, other_sessions):
        async with self.get_client_for_session(owner_session) as owner_client:
            if self.dry_run:
                logger.info(f"[DRY RUN] Baseline request to {url} with owner {owner_session['name']}")
                owner_resp = None
            else:
                try:
                    owner_resp = await owner_client.get(url)
                except Exception as e:
                    logger.error(f"Error requesting baseline for {url}: {e}")
                    return

        if owner_resp and owner_resp.status_code >= 400:
            logger.debug(f"Skipping {url} as owner received {owner_resp.status_code}")
            return

        for attacker in other_sessions:
            if self.dry_run:
                logger.info(f"[DRY RUN] Attacking {url} with session {attacker['name']}")
                continue

            async with self.get_client_for_session(attacker) as attacker_client:
                try:
                    attacker_resp = await attacker_client.get(url)

                    # Comparison signals
                    status_match = owner_resp.status_code == attacker_resp.status_code

                    owner_hash = hashlib.sha256(owner_resp.content).hexdigest()
                    attacker_hash = hashlib.sha256(attacker_resp.content).hexdigest()
                    hash_match = owner_hash == attacker_hash

                    len_diff = abs(len(owner_resp.content) - len(attacker_resp.content))
                    len_similar = len_diff < self.threshold

                    if status_match and hash_match:
                        severity = "HIGH"
                        title = "Confirmed IDOR/Auth Bypass"
                        evidence = {
                            "owner": owner_session["name"],
                            "attacker": attacker["name"],
                            "status": owner_resp.status_code,
                            "len_diff": len_diff
                        }
                        log_severity(severity, f"{title} on {url} (Attacker: {attacker['name']})")
                        save_finding(2, severity, url, title, evidence)
                    elif status_match or hash_match or len_similar:
                        severity = "MEDIUM"
                        title = "Potential IDOR/Auth Bypass"
                        evidence = {
                            "owner": owner_session["name"],
                            "attacker": attacker["name"],
                            "signals": {
                                "status_match": status_match,
                                "hash_match": hash_match,
                                "len_similar": len_similar
                            },
                            "len_diff": len_diff
                        }
                        log_severity(severity, f"{title} on {url} (Attacker: {attacker['name']})")
                        save_finding(2, severity, url, title, evidence)

                except Exception as e:
                    logger.error(f"Error during attack on {url} with {attacker['name']}: {e}")

    async def run(self):
        if len(self.sessions) < 2:
            logger.warning("At least 2 sessions are required for cross-user matrix testing.")
            return

        logger.info(f"Starting Authz matrix testing on {len(self.urls)} URLs with {len(self.sessions)} sessions.")

        # Session 0 is treated as the resource owner. All other sessions are
        # tested as potential attackers against Session 0's URLs.
        owner = self.sessions[0]
        attackers = self.sessions[1:]

        tasks = []
        for url in self.urls:
            tasks.append(self.test_url(url, owner, attackers))

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/sessions.yaml")
    parser.add_argument("-u", "--url")
    parser.add_argument("-f", "--file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        with open(args.file, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    tester = AuthzTester(config_path=args.config, urls=urls, dry_run=args.dry_run)
    asyncio.run(tester.run())
