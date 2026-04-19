# Agent Authoring Guide

Agents are markdown files with a YAML frontmatter block followed by the system prompt body.

## File location

```
agents/
├── tier1/    # creative_director, technical_director, producer
├── tier2/    # leads and directors
└── tier3/    # specialist implementers
```

## Format

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

## Required frontmatter fields

| Field | Type | Description |
|---|---|---|
| `name` | string | Snake_case agent name, matches the filename (without `.md`) |
| `tier` | int | 1, 2, or 3 |
| `reports_to` | string \| null | Parent agent name, or `null` for Tier 1 roots |
| `domain` | string | One-line description of expertise |

## Optional frontmatter fields

| Field | Type | Description |
|---|---|---|
| `model_override` | string | litellm model ID — overrides the tier default for this specific agent |

### `model_override` examples

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

## System prompt guidelines

- **Be specific about output format.** Agents that produce structured output (JSON, code, design specs) should include the exact format in their system prompt so the orchestrator can validate it.
- **Include a constraint section.** List the rules the agent must never break (e.g., no hardcoded values, 60-character dialogue limit).
- **Engine awareness.** The orchestrator injects engine context automatically, but agents can reference engine-specific patterns explicitly.
- **Tier 1 agents own decisions.** Their prompts should include APPROVED/REJECTED patterns since they are used as gates.

## Referencing a custom agent in a plan

Use the `name` field value exactly as the `agent` field in a plan step:

```yaml
steps:
  - id: my_step
    agent: my_agent
    tier: 2
    action: "Do something with my agent."
    gate: auto
```

## Editing agents in the web UI

Navigate to **Edit → Agents** in the sidebar. Each agent file is editable with a CodeMirror 6 editor (falls back to a plain textarea if the ESM import fails). Changes are saved immediately via `PUT /edit/agents/{tier}/{filename}`. The `model_override` field can also be set from the agent editor form.
