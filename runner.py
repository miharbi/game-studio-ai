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

_VENDOR_ASSETS: list[tuple[str, str]] = [
    # (filename in static/vendor/, source URL)
    # Note: Tailwind Play CDN (cdn.tailwindcss.com) behaves differently when served
    # from a non-CDN origin (dark-mode detection breaks). Always load it directly from CDN.
    ("daisyui.min.css", "https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css"),
    ("htmx.min.js", "https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js"),
    ("htmx-json-enc.js", "https://unpkg.com/htmx.org@1.9.12/dist/ext/json-enc.js"),
    ("marked.min.js", "https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"),
    ("sortable.min.js", "https://cdn.jsdelivr.net/npm/sortablejs@1/Sortable.min.js"),
    ("js-yaml.min.js", "https://cdn.jsdelivr.net/npm/js-yaml@4/dist/js-yaml.min.js"),
]


def _ensure_vendor_assets() -> None:
    """Download vendor CSS/JS files into static/vendor/ for offline desktop use.

    Files that already exist are skipped. Failures are silently ignored so the
    app falls back to CDN on the next request.
    """
    import httpx

    vendor_dir = Path(__file__).resolve().parent / "src" / "api" / "static" / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)

    missing = [(name, url) for name, url in _VENDOR_ASSETS if not (vendor_dir / name).exists()]
    if not missing:
        return

    import typer
    typer.echo(f"[desktop] Downloading {len(missing)} vendor asset(s) for offline use…")
    for filename, url in missing:
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=30)
            resp.raise_for_status()
            (vendor_dir / filename).write_bytes(resp.content)
            typer.echo(f"  ✓ {filename}")
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"  ✗ {filename} ({exc}) — will use CDN fallback")

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
    import os
    import threading
    import time

    # On Linux with NVIDIA drivers the pip-bundled Qt Mesa GLX conflicts with
    # the system GLX server. Disabling Qt's GLX/EGL integration for the xcb
    # platform plugin lets the window open while WebEngine still renders via
    # its own Chromium GPU path (or software fallback).
    os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")

    # Allow QtWebEngine's Chromium renderer to load CDN resources (CSS/JS).
    # Without --no-sandbox the sandboxed renderer process is blocked from
    # making network requests when GL integration is disabled.
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--no-sandbox --disable-gpu-sandbox",
    )

    # Download vendor assets so the UI works fully offline inside QtWebEngine.
    _ensure_vendor_assets()

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

    icon_path = str(Path(__file__).resolve().parent / "src" / "api" / "static" / "icon.png")

    window = webview.create_window("Game Studio AI", url, width=1280, height=800)

    def _set_icon():
        # Qt backend: set the window icon via QApplication
        try:
            from PyQt5.QtGui import QIcon
            from PyQt5.QtWidgets import QApplication
            app_qt = QApplication.instance()
            if app_qt:
                app_qt.setWindowIcon(QIcon(icon_path))
                window.native.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

    webview.start(func=_set_icon)


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
