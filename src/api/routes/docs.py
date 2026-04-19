"""Docs viewer routes — serve markdown files from docs/ as rendered HTML pages."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/guide", tags=["Docs"])

_DOCS_DIR: Path = Path(__file__).resolve().parents[3] / "docs"

_DOC_META: dict[str, str] = {
    "agents": "Agent Authoring Guide",
    "plans": "Plan Schema Reference",
    "engines": "Engine Support Reference",
    "api": "API Reference",
}


@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def docs_index(request: Request) -> HTMLResponse:
    """Redirect bare /guide to the agents doc."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/guide/agents", status_code=302)


@router.get("/{name}", response_class=HTMLResponse, include_in_schema=False)
async def docs_page(name: str, request: Request) -> HTMLResponse:
    if name not in _DOC_META:
        raise HTTPException(404, f"Doc page '{name}' not found.")
    path = _DOCS_DIR / f"{name}.md"
    if not path.exists():
        raise HTTPException(404, f"Doc file not found: {name}.md")
    content = path.read_text()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="docs_page.html",
        context={
            "doc_name": name,
            "doc_title": _DOC_META[name],
            "markdown_content": content,
            "doc_nav": _DOC_META,
        },
    )
