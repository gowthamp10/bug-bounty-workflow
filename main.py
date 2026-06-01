import asyncio
import argparse
import os
import sys
from utils.logger import logger, setup_logger, console
from core.agents import AgentState
from core.phase1_discovery import DiscoveryAgent
from core.phase2_authz import AuthzAgent
from core.phase3_oob import OOBAgent
from core.phase4_schema import SchemaAgent
from core.phase5_http2 import HTTP2Agent

def get_agent(phase_id, args):
    if phase_id == 1:
        return DiscoveryAgent(dry_run=args.dry_run, deep=args.deep)
    elif phase_id == 2:
        return AuthzAgent(dry_run=args.dry_run, config_path=args.config)
    elif phase_id == 3:
        return OOBAgent(dry_run=args.dry_run, poll_interval=args.poll_interval, local_mode=args.local)
    elif phase_id == 4:
        return SchemaAgent(dry_run=args.dry_run, swagger_url=args.swagger)
    elif phase_id == 5:
        return HTTP2Agent(dry_run=args.dry_run, concurrency=args.concurrency)
    return None

async def run_interactive(state, args):
    console.print("[bold cyan]--- Bug Bounty Agent Interactive Mode ---[/bold cyan]")

    while True:
        # Determine current agent to run
        if state.current_phase == 0:
            if not state.domain:
                state.domain = console.input("[yellow]Enter target domain (or leave blank if using -f): [/yellow]").strip()
            phase_to_run = 1
        else:
            # Suggest next phase
            current_agent = get_agent(state.current_phase, args)
            next_phase, reason = current_agent.suggest_next_step(state)

            if next_phase:
                console.print(f"\n[green]Suggestion:[/green] {reason}")
                choice = console.input(f"[bold white]Run Phase {next_phase} Agent? (y/n/q for quit): [/bold white]").lower()
                if choice == 'q': break
                if choice == 'y':
                    phase_to_run = next_phase
                else:
                    phase_input = console.input("[yellow]Enter phase number to run (1-5) or 'q' to quit: [/yellow]")
                    if phase_input == 'q': break
                    phase_to_run = int(phase_input)
            else:
                console.print(f"\n[bold green]{reason}[/bold green]")
                break

        agent = get_agent(phase_to_run, args)
        if agent:
            state.current_phase = phase_to_run
            state = await agent.run(state)
            state.save()
            console.print(f"\n[bold green]{agent.name} Agent completed.[/bold green]")
        else:
            console.print("[red]Invalid agent phase.[/red]")

async def main():
    parser = argparse.ArgumentParser(description="Bug Bounty Agent Workflow Engine")
    parser.add_argument("--all", action="store_true", help="Run all phases")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], help="Run a specific phase")
    parser.add_argument("--agent", action="store_true", help="Run in interactive agent mode")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("-d", "--domain")
    parser.add_argument("-f", "--file")
    parser.add_argument("-u", "--url")
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--config", default="config/sessions.yaml")
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--swagger")
    parser.add_argument("--concurrency", type=int, default=20)

    args = parser.parse_args()
    setup_logger(level="DEBUG" if args.debug else "INFO")

    state_loaded = AgentState.load()
    state = state_loaded or AgentState(domain=args.domain)
    if state.domain is None and args.domain:
        state.domain = args.domain
    if args.file:
        state.config["domain_file"] = args.file

    if args.agent:
        if state_loaded and state_loaded.completed_phases:
            console.print(f"[yellow]Detected existing state from previous run (Phases {state_loaded.completed_phases} completed).[/yellow]")
            resume = console.input("[bold white]Resume previous run? (y/n): [/bold white]").lower()
            if resume != 'y':
                state = AgentState(domain=args.domain)
                if args.file: state.config["domain_file"] = args.file
            else:
                state = state_loaded
        await run_interactive(state, args)
    elif args.all:
        for p in range(1, 6):
            agent = get_agent(p, args)
            state = await agent.run(state)
            state.save()
    elif args.phase:
        agent = get_agent(args.phase, args)
        if args.url and args.phase != 1:
            state.live_hosts = [args.url]
        state = await agent.run(state)
        state.save()
    else:
        logger.error("Please specify --agent, --all, or --phase <1-5>")

if __name__ == "__main__":
    asyncio.run(main())
