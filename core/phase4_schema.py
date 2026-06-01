import asyncio
import httpx
import os
import json
import yaml
from utils.logger import logger, log_severity
from utils.output import save_finding

class SchemaAuditor:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.wordlist_path = "utils/wordlists/graphql_fields.txt"
        self.graphql_wordlist = []
        if os.path.exists(self.wordlist_path):
            with open(self.wordlist_path, "r") as f:
                self.graphql_wordlist = [line.strip() for line in f if line.strip()]

    async def audit_graphql(self, url):
        logger.info(f"[*] Auditing GraphQL endpoint: {url}")

        introspection_query = {"query": "{__schema{queryType{name}mutationType{name}subscriptionType{name}types{kind name description fields{name description args{name description type{kind name}}}}}}"}

        if self.dry_run:
            logger.info(f"[DRY RUN] Attempting introspection on {url}")
            return

        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            try:
                resp = await client.post(url, json=introspection_query)
                if resp.status_code == 200 and "__schema" in resp.text:
                    severity = "MEDIUM"
                    title = "GraphQL Introspection Enabled"
                    log_severity(severity, f"{title} at {url}")
                    save_finding(4, severity, url, title, "Full schema accessible via introspection")
                else:
                    logger.info(f"[-] Introspection disabled at {url}, falling back to field guessing.")
                    await self.guess_graphql_fields(url)
            except Exception as e:
                logger.error(f"Error auditing GraphQL {url}: {e}")

    async def guess_graphql_fields(self, url):
        if not self.graphql_wordlist:
            return

        logger.info(f"[*] Guessing fields for {url} using {len(self.graphql_wordlist)} items...")

        # Clairvoyance-style guessing: send a query with many fields and see if any are recognized
        # This is a simplified version.
        batch_size = 20
        for i in range(0, min(len(self.graphql_wordlist), 100), batch_size):
            batch = self.graphql_wordlist[i:i+batch_size]
            fields_str = " ".join(batch)
            query = {"query": f"{{ {fields_str} }}"}

            if self.dry_run:
                logger.debug(f"[DRY RUN] Testing GraphQL fields: {', '.join(batch)}")
                continue

            async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                try:
                    resp = await client.post(url, json=query)
                    # If any field exists, we might get a 200 or a specific error message
                    if resp.status_code == 200 or "Cannot query field" in resp.text:
                        # In a real tool, we would parse errors to find which fields DO exist
                        pass
                except Exception:
                    pass

    async def parse_swagger(self, url_or_path):
        logger.info(f"[*] Attempting to parse Swagger/OpenAPI: {url_or_path}")
        try:
            if url_or_path.startswith("http"):
                async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                    resp = await client.get(url_or_path)
                    content = resp.text
            else:
                with open(url_or_path, "r") as f:
                    content = f.read()

            try:
                spec = json.loads(content)
            except json.JSONDecodeError:
                spec = yaml.safe_load(content)

            paths = spec.get("paths", {})
            logger.info(f"[+] Found {len(paths)} paths in Swagger spec.")
            return paths
        except Exception as e:
            logger.error(f"Error parsing Swagger {url_or_path}: {e}")
            return {}

    async def fuzz_rest_api(self, base_url, swagger_url=None):
        logger.info(f"[*] Fuzzing REST API at {base_url}")

        targets = []
        if swagger_url:
            paths = await self.parse_swagger(swagger_url)
            for path in paths:
                targets.append(base_url.rstrip("/") + path)
        else:
            common_paths = ["/api/v1", "/api/v2", "/admin", "/internal", "/swagger.json", "/api-docs"]
            for path in common_paths:
                targets.append(base_url.rstrip("/") + path)

        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            for url in targets:
                if self.dry_run:
                    logger.info(f"[DRY RUN] Probing {url}")
                    continue

                try:
                    resp = await client.get(url)
                    if resp.status_code < 400:
                        severity = "INFO"
                        title = f"Discovered API Endpoint"
                        log_severity(severity, f"Found {url} ({resp.status_code})")
                        save_finding(4, severity, url, title, f"Status: {resp.status_code}")
                        await self.probe_method_override(url)
                except Exception:
                    pass

    async def probe_method_override(self, url):
        headers = {"X-HTTP-Method-Override": "PUT"}
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            try:
                resp = await client.post(url, headers=headers, json={"test": "data"})
                if resp.status_code == 200:
                    logger.debug(f"Potential Method Override supported at {url}")
            except Exception:
                pass

    async def run(self, targets, swagger_url=None):
        tasks = []
        for target in targets:
            if "graphql" in target.lower():
                tasks.append(self.audit_graphql(target))
            else:
                tasks.append(self.fuzz_rest_api(target, swagger_url=swagger_url))

        if tasks:
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url")
    parser.add_argument("-f", "--file")
    parser.add_argument("--swagger")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        with open(args.file, "r") as f:
            urls.extend([line.strip() for line in f if line.strip()])

    auditor = SchemaAuditor(dry_run=args.dry_run)
    asyncio.run(auditor.run(urls, swagger_url=args.swagger))
