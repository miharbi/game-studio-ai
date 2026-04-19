# Game Studio AI

A tiered multi-agent orchestrator that runs a full AI game studio pipeline from your terminal or browser. Point it at a game project, pick a plan template, and a hierarchy of specialized AI agents — from Creative Director down to QA Tester — collaborates to design features, generate levels, write dialogue, review code, and produce engine-ready sprite specifications.

**Human-in-the-loop gates** pause the pipeline at critical checkpoints so you stay in control of every decision that matters.

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> game-studio-ai
cd game-studio-ai
pip install -e ".[dev]"

# 2. Configure your LLM provider
cp .env.example .env
# Edit .env — add your GITHUB_TOKEN or other provider key

# 3. Run your first plan
python runner.py run --plan plans/templates/design_feature.yaml \
    --engine godot4 \
    --input "Add a wall-jump mechanic for the player character"

# 4. Or launch the web UI
python runner.py serve
# Open http://localhost:8000
```

---

## Agent Hierarchy

The studio has 28 agents organized into 3 tiers. Higher tiers own the creative and technical vision; lower tiers do the detailed implementation work.

| Tier | Role | Reports to | Domain |
|---|---|---|---|
| **1** | `creative_director` | — | Creative vision and final approval |
| **1** | `technical_director` | — | Architecture, security, platform constraints |
| **1** | `producer` | — | Scope, coordination, risk |
| **2** | `game_designer` | creative_director | Mechanics and game design specs |
| **2** | `lead_programmer` | technical_director | Code standards and review |
| **2** | `art_director` | creative_director | Visual style and asset specs |
| **2** | `audio_director` | creative_director | Music and SFX direction |
| **2** | `narrative_director` | creative_director | Story, lore, dialogue |
| **2** | `qa_lead` | producer | Testing strategy |
| **2** | `release_manager` | producer | Build and deployment |
| **2** | `localization_lead` | narrative_director | Regional authenticity |
| **3** | `gameplay_programmer` | lead_programmer | Player controller, mechanics |
| **3** | `engine_programmer` | lead_programmer | Engine integration, autoloads |
| **3** | `ai_programmer` | lead_programmer | Enemy AI, pathfinding |
| **3** | `network_programmer` | lead_programmer | Multiplayer, sync |
| **3** | `tools_programmer` | lead_programmer | Dev tooling, pipelines |
| **3** | `ui_programmer` | lead_programmer | Menus, HUD |
| **3** | `systems_designer` | game_designer | Progression, economy systems |
| **3** | `level_designer` | game_designer | Level layout, wave composition |
| **3** | `economy_designer` | systems_designer | Scoring, drop rates, rewards |
| **3** | `technical_artist` | art_director | Sprite atlases, shaders, import |
| **3** | `sound_designer` | audio_director | SFX implementation |
| **3** | `writer` | narrative_director | Dialogue, UI copy |
| **3** | `world_builder` | level_designer | Props, art direction, dressing |
| **3** | `ux_designer` | game_designer | UX, onboarding, accessibility |
| **3** | `prototyper` | game_designer | Rapid mechanic validation |
| **3** | `qa_tester` | qa_lead | Functional testing, bug reports |
| **3** | `performance_analyst` | technical_director | Profiling, optimization |
| **3** | `devops_engineer` | technical_director | CI/CD, build pipelines |
| **3** | `security_engineer` | technical_director | OWASP audits, data protection |
| **3** | `accessibility_specialist` | ux_designer | WCAG compliance |
| **3** | `live_ops_designer` | producer | Events, post-launch content |
| **3** | `analytics_engineer` | producer | Telemetry, retention metrics |
| **3** | `community_manager` | producer | Player feedback, comms |

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

# Launch the web UI
python runner.py serve [--host 0.0.0.0] [--port 8080]

# List all registered agents
python runner.py list-agents

# List available plan templates
python runner.py list-plans

# List all supported LLM providers and models
python runner.py list-models
```

---

## Web UI

The web interface provides:

- **Dashboard** — start a run, pick a plan template and engine, view recent runs
- **Run detail** — live-streamed agent output via Server-Sent Events, pipeline step indicators, gate approval panel
- **Sprite gallery** — review AI-generated sprites, approve (moves to `output/approved/`) or reject

```bash
python runner.py serve
# Open http://localhost:8000
```

---

## Project Structure

```
game-studio-ai/
├── runner.py               # CLI entry point (typer)
├── pyproject.toml          # packaging, dependencies, pytest config
├── .env.example            # environment variable template
├── config/
│   ├── models.yaml         # tier → model mapping
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

### Environment variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | required | GitHub Models API token |
| `TIER1_MODEL` | `github/gpt-4.1` | Model for Tier 1 agents |
| `TIER2_MODEL` | `github/gpt-4.1-mini` | Model for Tier 2 agents |
| `TIER3_MODEL` | `github/gpt-4.1-mini` | Model for Tier 3 agents |
| `SPRITE_PROVIDER` | `stub` | `stub` \| `openai` \| `stable_diffusion` |
| `OPENAI_API_KEY` | optional | Required if `SPRITE_PROVIDER=openai` |
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

Controls tier-to-model routing, the provider catalog, and sprite generation defaults. All tier entries can be overridden by environment variables. Individual agents can also set `model_override` in their frontmatter.

---

## Tech Stack

| Layer | Library |
|---|---|
| LLM routing | [litellm](https://github.com/BerriAI/litellm) |
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) + [htmx](https://htmx.org/) |
| Templates | Jinja2 |
| Database | SQLModel + SQLite |
| CLI | [Typer](https://typer.tiangolo.com/) |
| Image generation | Pillow + DALL-E 3 / Stable Diffusion |
| Testing | pytest + pytest-asyncio |

---

## Running Tests

```bash
pytest tests/ -v
```

All tests should pass without a live LLM connection — the test suite uses local fixtures and does not make API calls.

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
