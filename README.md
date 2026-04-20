# Game Studio AI

A tiered multi-agent orchestrator that runs a full AI game studio pipeline from your terminal, browser, or native desktop window. Point it at a game project, pick a plan template, and a hierarchy of 28 specialized AI agents — from Creative Director down to QA Tester — collaborates to design features, generate levels, write dialogue, review code, and produce engine-ready sprite specifications.

**Human-in-the-loop gates** pause the pipeline at critical checkpoints so you stay in control of every decision that matters.

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> game-studio-ai
cd game-studio-ai
pip install -e ".[dev]"

# 2. Launch the web UI and configure everything there
python runner.py serve
# Open http://localhost:8000 → click "Setup" in the sidebar
# Add your API keys in the API Keys tab — they are saved to config/.env

# 3. Run your first plan from the dashboard
```

Or run as a **native desktop app** (no browser needed):

```bash
pip install -e ".[desktop]"
python runner.py desktop
```

Or configure via environment variables and use the CLI directly:

```bash
cp .env.example .env   # or use config/.env via the Setup page
# Edit .env — add your GITHUB_TOKEN or other provider key
python runner.py run --plan plans/templates/design_feature.yaml \
    --engine godot4 \
    --input "Add a wall-jump mechanic for the player character"
```

---

## Agent Hierarchy

The studio has 28 agents organized into 3 tiers. Tier 1 owns vision and strategy, Tier 2 leads departments, and Tier 3 does the detailed implementation work.

```text
                         ┌─────────────────────┐
             ┌───────────│  creative_director   │───────────┐
             │           │  (creative vision)   │           │
             │           └─────────────────────┘           │
             │                     │                        │
     ┌───────┴────────┐   ┌───────┴────────┐   ┌──────────┴──────────┐
     │  game_designer  │   │  art_director   │   │  audio_director     │
     │  (mechanics)    │   │  (visual style) │   │  (music & SFX)      │
     └───────┬────────┘   └───────┬────────┘   └──────────┬──────────┘
             │                     │                        │
  ┌──────────┼──────────┐         │                        │
  │          │          │   technical_artist          sound_designer
  │          │          │   (atlases, shaders)        (SFX implementation)
  │          │          │
systems_  level_     ux_designer
designer  designer   (UX, onboarding)
  │         │              │
economy_  world_     accessibility_
designer  builder    specialist
  │
prototyper


             ┌─────────────────────┐
             │ technical_director   │
             │ (architecture)       │
             └─────────┬───────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
     ┌─────┴──────┐       ┌───────┴────────┐
     │ lead_       │       │ (direct reports)│
     │ programmer  │       │                 │
     └─────┬──────┘       └────────────────┘
           │               performance_analyst
    ┌──────┼──────────┐    devops_engineer
    │      │          │    security_engineer
    │      │          │
gameplay_ engine_   ai_programmer
programmer programmer network_programmer
  tools_programmer   ui_programmer


             ┌─────────────────────┐
             │     producer        │
             │  (scope & risk)     │
             └─────────┬───────────┘
                       │
     ┌─────────┬───────┴───────┬────────────┐
     │         │               │            │
  qa_lead   release_      narrative_    (direct reports)
     │      manager       director      live_ops_designer
     │                       │          analytics_engineer
  qa_tester             ┌────┴────┐     community_manager
                        │         │
                     writer  localization_
                             lead
```

### All agents at a glance

<details>
<summary><strong>Tier 1 — Leadership</strong> (3 agents)</summary>

| Agent | Domain |
|---|---|
| `creative_director` | Creative vision and final approval |
| `technical_director` | Architecture, security, platform constraints |
| `producer` | Scope, coordination, risk management |

</details>

<details>
<summary><strong>Tier 2 — Department Leads</strong> (8 agents)</summary>

| Agent | Reports to | Domain |
|---|---|---|
| `game_designer` | creative_director | Mechanics and game design specs |
| `lead_programmer` | technical_director | Code standards and review |
| `art_director` | creative_director | Visual style and asset specs |
| `audio_director` | creative_director | Music and SFX direction |
| `narrative_director` | creative_director | Story, lore, dialogue |
| `qa_lead` | producer | Testing strategy |
| `release_manager` | producer | Build and deployment |
| `localization_lead` | narrative_director | Regional authenticity |

</details>

<details>
<summary><strong>Tier 3 — Specialists</strong> (17 agents)</summary>

| Agent | Reports to | Domain |
|---|---|---|
| `gameplay_programmer` | lead_programmer | Player controller, mechanics |
| `engine_programmer` | lead_programmer | Engine integration, autoloads |
| `ai_programmer` | lead_programmer | Enemy AI, pathfinding |
| `network_programmer` | lead_programmer | Multiplayer, sync |
| `tools_programmer` | lead_programmer | Dev tooling, pipelines |
| `ui_programmer` | lead_programmer | Menus, HUD |
| `systems_designer` | game_designer | Progression, economy systems |
| `level_designer` | game_designer | Level layout, wave composition |
| `economy_designer` | systems_designer | Scoring, drop rates, rewards |
| `technical_artist` | art_director | Sprite atlases, shaders, import |
| `sound_designer` | audio_director | SFX implementation |
| `writer` | narrative_director | Dialogue, UI copy |
| `world_builder` | level_designer | Props, art direction, dressing |
| `ux_designer` | game_designer | UX, onboarding, accessibility |
| `prototyper` | game_designer | Rapid mechanic validation |
| `qa_tester` | qa_lead | Functional testing, bug reports |
| `performance_analyst` | technical_director | Profiling, optimization |
| `devops_engineer` | technical_director | CI/CD, build pipelines |
| `security_engineer` | technical_director | OWASP audits, data protection |
| `accessibility_specialist` | ux_designer | WCAG compliance |
| `live_ops_designer` | producer | Events, post-launch content |
| `analytics_engineer` | producer | Telemetry, retention metrics |
| `community_manager` | producer | Player feedback, comms |

</details>

---

## Plan Templates

Plans are YAML files that define a pipeline of agent steps with gate checkpoints.

```yaml
task: design_feature
engine: null   # auto-detect or pass --engine
input: "Describe the feature here"

steps:
  - id: creative_review
    agent: creative_director
    tier: 1
    action: "Review the feature concept against creative vision."
    gate: human_review        # pauses for your approval
    validate_as: feature_design

  - id: game_design_spec
    agent: game_designer
    tier: 2
    action: "Write the full design spec."
    depends_on: [creative_review]
    gate: auto                # proceeds automatically
```

### Built-in templates

| Template | Pipeline |
|---|---|
| `design_feature.yaml` | creative_director → game_designer → systems_designer → qa_tester |
| `design_level.yaml` | game_designer → level_designer → world_builder → technical_director |
| `generate_sprites.yaml` | art_director → technical_artist → qa_tester |
| `code_review.yaml` | lead_programmer → engine_programmer → security_engineer → qa_tester |
| `write_dialogue.yaml` | narrative_director → writer → localization_lead → qa_tester |

### Gate types

| Gate | Behavior |
|---|---|
| `auto` | Always proceeds |
| `conditional` | Proceeds unless the agent output contains "REJECTED" |
| `human_review` | Pauses — requires your approval (CLI prompt or web UI) |

---

## Engine Support

| Engine | Detection marker | Sprite dimensions |
|---|---|---|
| `godot4` | `project.godot` | Player 48×64, Enemy 32×48, BG 768×144 |
| `unity` | `ProjectSettings/ProjectVersion.txt` or `*.sln` | Player 64×64, BG 1920×1080 |
| `unreal5` | `*.uproject` | Player 256×256, BG 3840×2160 |

Engine context is automatically injected into every agent prompt so agents give engine-appropriate advice.

---

## CLI Reference

```bash
# Run a plan
python runner.py run --plan <path> [--engine godot4|unity|unreal5] [--input "text"] [--dry-run]

# Resume an interrupted run
python runner.py resume <run-id>

# Auto-detect the engine in a project directory
python runner.py detect-engine /path/to/project

# Launch the web UI in a browser
python runner.py serve [--host 0.0.0.0] [--port 8080]

# Launch the web UI in a native desktop window
python runner.py desktop [--host 127.0.0.1] [--port 8000]

# List all registered agents
python runner.py list-agents

# List available plan templates
python runner.py list-plans

# List all supported LLM providers and models
python runner.py list-models
```

---

## Web UI & Desktop Mode

The interface is available as a **browser tab** (`serve`) or a **native desktop window** (`desktop`). Both use the same FastAPI + htmx UI — the desktop mode wraps it in a native OS window via [pywebview](https://pywebview.flowrl.com/).

```bash
# Browser mode
python runner.py serve
# Open http://localhost:8000

# Desktop mode (requires: pip install -e ".[desktop]")
python runner.py desktop
```

### Features

- **Dashboard** — start a run, pick a plan template and engine, view recent runs; shows a setup alert when configuration is missing
- **Run detail** — live-streamed agent output via Server-Sent Events, pipeline step indicators, gate approval panel
- **Sprite gallery** — review AI-generated sprites, approve (moves to `output/approved/`) or reject; includes a 4-step workflow explanation
- **Setup** (`/edit/config`) — unified configuration page with tabbed sections:
  - **Tiers** — assign a model to each tier; only models from providers with an API key are shown
  - **Sprites** — configure the image generation provider and model
  - **Providers** — view all configured providers; active (key set) vs inactive (no key) are visually distinguished
  - **API Keys** — enter API keys per provider; saved to `config/.env` and loaded immediately without restart
  - **Project** — set the game project path for engine auto-detection
  - **Full YAML** — raw `models.yaml` editor (CodeMirror 6 with textarea fallback)
- **Agents / Plans / Engines** — in-browser editors with CodeMirror 6 and textarea fallback

---

## Project Structure

```
game-studio-ai/
├── runner.py               # CLI entry point (typer)
├── pyproject.toml          # packaging, dependencies, pytest config
├── .env.example            # environment variable template
├── config/
│   ├── models.yaml         # tier → model mapping + provider catalog
│   ├── settings.yaml       # project path (written by Setup UI)
│   ├── .env                # API keys saved via Setup UI (git-ignored)
│   └── engines/
│       ├── godot4.yaml
│       ├── unity.yaml
│       └── unreal5.yaml
├── agents/
│   ├── tier1/              # creative_director, technical_director, producer
│   ├── tier2/              # 8 lead/director agents
│   └── tier3/              # 23 specialist agents
├── plans/
│   ├── templates/          # 5 built-in plan templates
│   └── active/             # plans in progress
├── src/
│   ├── models/             # LLM client (litellm) and model router
│   ├── orchestrator/       # plan executor, agent loader, gate, context
│   ├── validators/         # output schema validators
│   ├── state/              # SQLModel + SQLite persistence
│   ├── engines/            # engine detection and context loading
│   ├── sprites/            # spec builder, generator, post-processor
│   └── api/                # FastAPI + htmx web UI
├── tests/                  # pytest test suite
└── output/
    ├── sprites/            # generated sprite PNGs
    └── approved/           # approved sprites
```

---

## Configuration

### API Keys — Setup UI (recommended)

Open `http://localhost:8000` → **Setup** → **API Keys** tab. Enter your key next to each provider. Keys are saved to `config/.env` (git-ignored) and loaded into the environment immediately — no restart needed.

Providers without a key are marked **inactive** and their models are hidden from Tier dropdowns until you add a key.

### API Keys — environment variables (alternative)

You can also set keys as standard environment variables or in a root `.env` file:

```bash
cp .env.example .env
# Add your keys:
export GITHUB_TOKEN=your_token
export OPENAI_API_KEY=your_key
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | — | GitHub Models API token (free with Copilot) |
| `OPENAI_API_KEY` | — | OpenAI / DALL-E |
| `ANTHROPIC_API_KEY` | — | Claude models |
| `DEEPSEEK_API_KEY` | — | DeepSeek-V3, R1 |
| `MOONSHOT_API_KEY` | — | Kimi (up to 128K context) |
| `DASHSCOPE_API_KEY` | — | Qwen / Alibaba Cloud |
| `ZHIPUAI_API_KEY` | — | GLM-4 / Zhipu AI |
| `GOOGLE_API_KEY` | — | Gemini models |
| `MISTRAL_API_KEY` | — | Mistral AI |
| `TIER1_MODEL` | `github/gpt-4.1` | Runtime override for Tier 1 |
| `TIER2_MODEL` | `github/gpt-4.1-mini` | Runtime override for Tier 2 |
| `TIER3_MODEL` | `github/gpt-4.1-mini` | Runtime override for Tier 3 |
| `SPRITE_PROVIDER` | `stub` | `stub` \| `openai` \| `stable_diffusion` |
| `SD_API_URL` | `http://localhost:7860` | Stable Diffusion API URL |

### Supported LLM Providers

The project uses [litellm](https://github.com/BerriAI/litellm) for LLM routing, which means **any litellm-supported model works out of the box**. Set the appropriate API key and override the tier model:

| Provider | Env Key | Example models | Notes |
|---|---|---|---|
| **GitHub Models** | `GITHUB_TOKEN` | `github/gpt-4.1`, `github/gpt-4.1-mini` | Free with Copilot — **default** |
| **OpenAI** | `OPENAI_API_KEY` | `openai/gpt-4o`, `openai/gpt-4o-mini` | Also used for DALL-E sprites |
| **Anthropic** | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-4-20250514` | Claude models |
| **DeepSeek** | `DEEPSEEK_API_KEY` | `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner` | DeepSeek-V3 / R1 |
| **Moonshot / Kimi** | `MOONSHOT_API_KEY` | `moonshot/moonshot-v1-8k`, `moonshot/moonshot-v1-128k` | Up to 128K context |
| **DashScope / Qwen** | `DASHSCOPE_API_KEY` | `dashscope/qwen-max`, `dashscope/qwen-plus`, `dashscope/qwen-turbo` | Alibaba Cloud |
| **Zhipu AI / GLM** | `ZHIPUAI_API_KEY` | `zhipuai/glm-4-plus`, `zhipuai/glm-4-flash` | GLM-4 models, up to 1M context |
| **Google Gemini** | `GOOGLE_API_KEY` | `gemini/gemini-2.5-flash`, `gemini/gemini-2.5-pro` | 1M context |
| **Mistral** | `MISTRAL_API_KEY` | `mistral/mistral-large-latest` | Mistral AI |
| **Custom / OpenAI-compat** | `OPENAI_API_KEY` + `OPENAI_BASE_URL` | any | Yi, vLLM, Ollama, etc. |

**Quick example — switch to DeepSeek:**

```bash
export DEEPSEEK_API_KEY=your_key_here
export TIER1_MODEL=deepseek/deepseek-chat
export TIER2_MODEL=deepseek/deepseek-chat
export TIER3_MODEL=deepseek/deepseek-chat
python runner.py run --plan plans/templates/design_feature.yaml --input "Add a wall-jump mechanic"
```

Run `python runner.py list-models` to see all configured providers and their models.

### `config/models.yaml`

Controls tier-to-model routing, the provider catalog (with `env_key` per provider), and sprite generation defaults. All tier entries can be overridden by environment variables. Individual agents can also set `model_override` in their frontmatter. Edit this file directly in the **Full YAML** tab of the Setup page or in `config/models.yaml`.

---

## Tech Stack

| Layer | Library |
|---|---|
| LLM routing | [litellm](https://github.com/BerriAI/litellm) |
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) + [htmx 1.9](https://htmx.org/) |
| Desktop window | [pywebview](https://pywebview.flowrl.com/) (optional) |
| UI components | [DaisyUI 4](https://daisyui.com/) (MIT, CDN) + [Tailwind CSS](https://tailwindcss.com/) (CDN) |
| Templates | Jinja2 |
| In-browser editor | [CodeMirror 6](https://codemirror.net/) (ESM, `esm.sh`) with textarea fallback |
| Database | SQLModel + SQLite |
| CLI | [Typer](https://typer.tiangolo.com/) |
| Image generation | Pillow + DALL-E 3 / Stable Diffusion |
| Testing | pytest + pytest-asyncio |

---

## Running Tests

```bash
pytest tests/ -v
```

All tests pass without a live LLM connection — the test suite uses local fixtures and makes no API calls.

---

## Writing a Custom Agent

Create a markdown file in `agents/tier1/`, `agents/tier2/`, or `agents/tier3/`:

```markdown
---
name: my_agent
tier: 3
reports_to: lead_programmer
domain: my domain
---
You are the My Agent. [System prompt body follows here...]
```

The agent is immediately available to use in plan templates by name.

See [docs/agents.md](docs/agents.md) for the full agent authoring guide.
