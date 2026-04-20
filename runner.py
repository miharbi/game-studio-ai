#!/usr/bin/env python3
"""
Game Studio AI — CLI entry point.

Usage:
    python runner.py run --plan plans/templates/design_feature.yaml
    python runner.py run --plan plans/templates/design_level.yaml --engine godot4
    python runner.py resume <run_id>
    python runner.py detect-engine /path/to/project
    python runner.py serve
    python runner.py list-agents
    python runner.py list-plans
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv  # type: ignore[import]
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import typer
from typing import Optional

app = typer.Typer(
    name="studio",
    help="Game Studio AI — tiered multi-agent orchestrator for game development.",
    add_completion=False,
)


@app.command()
def run(
    plan: Path = typer.Option(..., "--plan", "-p", help="Path to plan YAML file."),
    engine: Optional[str] = typer.Option(
        None, "--engine", "-e", help="Engine override: godot4 | unity | unreal5"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print steps without calling LLMs."),
) -> None:
    """Execute a plan YAML through the agent pipeline."""
    from src.orchestrator.engine import PlanExecutor

    executor = PlanExecutor(plan_path=plan, engine_override=engine, dry_run=dry_run)
    executor.run()


@app.command()
def resume(
    run_id: str = typer.Argument(..., help="Run ID to resume."),
) -> None:
    """Resume an interrupted plan run from the last completed step."""
    from src.orchestrator.engine import PlanExecutor

    executor = PlanExecutor.from_run_id(run_id)
    executor.run()


@app.command(name="detect-engine")
def detect_engine(
    project_path: Path = typer.Argument(..., help="Path to the game project root."),
) -> None:
    """Auto-detect the game engine from project files."""
    from src.engines.detect import detect

    result = detect(project_path)
    if result:
        typer.echo(f"Detected engine: {result}")
    else:
        typer.echo("Engine not detected. Ensure the path contains project.godot, *.sln, or *.uproject.")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(8000, "--port", help="Port to bind."),
) -> None:
    """Start the web UI (FastAPI + htmx)."""
    import uvicorn

    typer.echo(f"Starting Game Studio AI at http://{host}:{port}")
    uvicorn.run("src.api.main:app", host=host, port=port, reload=True)


@app.command()
def desktop(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(8000, "--port", help="Port to bind."),
) -> None:
    """Launch the web UI in a native desktop window (requires pywebview)."""
    import threading
    import time

    try:
        import webview  # type: ignore[import]
    except ImportError:
        typer.echo('pywebview is not installed. Run: pip install -e ".[desktop]"')
        raise typer.Exit(1)

    import uvicorn
    import httpx

    url = f"http://{host}:{port}"

    def _start_server() -> None:
        uvicorn.run("src.api.main:app", host=host, port=port, log_level="warning")

    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # Wait for the server to be ready before opening the window.
    for _ in range(50):
        try:
            httpx.get(url, timeout=0.5)
            break
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(0.1)

    webview.create_window("Game Studio AI", url, width=1280, height=800)
    webview.start()


@app.command(name="list-agents")
def list_agents() -> None:
    """List all available agent definitions."""
    from src.orchestrator.agent_loader import AgentLoader

    loader = AgentLoader(Path(__file__).resolve().parent / "agents")
    agents = loader.list_all()
    for tier in sorted(agents.keys()):
        typer.echo(f"\nTier {tier}:")
        for agent in agents[tier]:
            typer.echo(f"  {agent.name:30s}  reports_to={agent.reports_to or '—'}")


@app.command(name="list-plans")
def list_plans() -> None:
    """List available plan templates."""
    templates_dir = Path(__file__).resolve().parent / "plans" / "templates"
    plans = sorted(templates_dir.glob("*.yaml"))
    if not plans:
        typer.echo("No plan templates found in plans/templates/")
        return
    for p in plans:
        typer.echo(f"  {p.name}")


@app.command(name="list-models")
def list_models() -> None:
    """List all supported LLM providers and their models from config/models.yaml."""
    from src.models.router import list_providers, get_model

    typer.echo("\nDefault tier models:")
    for tier in (1, 2, 3):
        typer.echo(f"  Tier {tier}: {get_model(tier)}")

    providers = list_providers()
    if not providers:
        typer.echo("\nNo providers configured in config/models.yaml")
        return

    typer.echo(f"\nSupported providers ({len(providers)}):\n")
    for name, info in providers.items():
        env_key = info.get("env_key", "?")
        typer.echo(f"  {name}  (env: {env_key})")
        for m in info.get("models", []):
            ctx = m.get("context_window", "?")
            note = m.get("note", "")
            typer.echo(f"    {m['id']:45s}  ctx={ctx:>10}  {note}")
        typer.echo("")


if __name__ == "__main__":
    app()
