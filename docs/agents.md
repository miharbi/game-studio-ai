# Agent Authoring Guide

Agents are markdown files with a YAML frontmatter block followed by the system prompt body. You can create and edit them from the **web UI** or directly on disk.

For initial project setup and your first run, start with [Project Quick Start](quick-start.md).

---

## Using the Web UI

Navigate to **Agents** in the sidebar. The page lists all agents grouped by tier.

- **Edit** — click any agent name to open it in the CodeMirror editor. The frontmatter fields (name, tier, reports_to, domain, model_override) are shown as form fields above the prompt body. Changes save immediately via `PUT /edit/agents/{tier}/{filename}`.
- **Create** — click **New Agent**, fill in the form, and save. The file is created under the correct `agents/tier{N}/` directory automatically.
- **Delete** — use the delete button on the agent detail page. This removes the markdown file from disk.

> If CodeMirror fails to load (e.g. no internet for the ESM CDN), the editor falls back to a plain textarea.

---

## Editing Files Directly

### File location

```text
agents/
├── tier1/    # creative_director, technical_director, producer
├── tier2/    # leads and directors
└── tier3/    # specialist implementers
```

### Format

```markdown
---
name: my_agent
tier: 2
reports_to: creative_director
domain: my specialized domain
model_override: github/gpt-4.1   # optional — overrides config/models.yaml for this agent
---
You are the My Agent. Write the full system prompt here.

Your responsibilities:
- ...

Your output format:
## Section heading
[description]
```

### Required frontmatter fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `name` | string | Snake_case agent name, matches the filename (without `.md`) |
| `tier` | int | 1, 2, or 3 |
| `reports_to` | string \| null | Parent agent name, or `null` for Tier 1 roots |
| `domain` | string | One-line description of expertise |

### Optional frontmatter fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `model_override` | string | litellm model ID — overrides the tier default for this specific agent |

#### `model_override` examples

Any [litellm-supported model](https://docs.litellm.ai/docs/providers) can be used:

```yaml
# OpenAI / GitHub
model_override: github/gpt-4.1
model_override: openai/gpt-4o

# Chinese providers
model_override: deepseek/deepseek-chat           # DeepSeek-V3
model_override: moonshot/moonshot-v1-128k         # Kimi 128K context
model_override: dashscope/qwen-max                # Qwen-Max (Alibaba)
model_override: zhipuai/glm-4-plus                # GLM-4 Plus (Zhipu)

# Others
model_override: anthropic/claude-sonnet-4-20250514
model_override: gemini/gemini-2.5-flash
model_override: mistral/mistral-large-latest
```

Run `python runner.py list-models` to see all pre-configured providers and model IDs.

---

## System Prompt Guidelines

- **Be specific about output format.** Agents that produce structured output (JSON, code, design specs) should include the exact format in their system prompt so the orchestrator can validate it.
- **Include a constraint section.** List the rules the agent must never break (e.g., no hardcoded values, 60-character dialogue limit).
- **Engine awareness.** The orchestrator injects engine context automatically, but agents can reference engine-specific patterns explicitly.
- **Spec file context.** When a project path is configured and the engine declares `spec_files`, the orchestrator injects relevant sections of those JSON files into each agent's system prompt. Each agent only receives the sections relevant to its role (e.g. `art_director` gets `art_style` + `characters` + `vfx`; `writer` gets `characters` + `audio`). Add a `## Game Spec` section near the top of the agent's body to tell it how to use that injected context.
- **Tier 1 agents own decisions.** Their prompts should include APPROVED/REJECTED patterns since they are used as gates.

---

## Referencing a Custom Agent in a Plan

Use the `name` field value exactly as the `agent` field in a plan step:

```yaml
steps:
  - id: my_step
    agent: my_agent
    tier: 2
    action: "Do something with my agent."
    gate: auto
```

> **Tip:** You can also create and wire up agents via the web UI — see [Using the Web UI](#using-the-web-ui) above.
