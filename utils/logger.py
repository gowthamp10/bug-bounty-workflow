from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()

def setup_logger(name: str = "bug-bounty-agent", level: str = "INFO"):
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)]
    )
    return logging.getLogger(name)

logger = setup_logger()

def log_severity(severity: str, message: str):
    colors = {
        "CRITICAL": "bold red",
        "HIGH": "red",
        "MEDIUM": "orange3",
        "LOW": "yellow",
        "INFO": "green"
    }
    color = colors.get(severity.upper(), "white")
    console.print(f"[{color}][{severity.upper()}][/{color}] {message}")
