"""
Lucas MARTIN — Gestionnaire Sinistres Automobile Senior.
The meta-agent (Claude Code) iterates on AGENT CONFIG section only.

Run all tasks:
    docker build -f Dockerfile.base -t autoagent-base .
    set -a && source .env && set +a
    uv run harbor run -p tasks/lucas/ \
        --agent-import-path agent_lucas:AutoAgent \
        -o jobs/lucas --job-name latest -n 4
"""

import os, json
from datetime import datetime, timezone
from pathlib import Path
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage, tool

# ===========================================================================
# AGENT CONFIG — meta-agent modifies this section
# ===========================================================================

SYSTEM_PROMPT = """Tu es Lucas MARTIN, Gestionnaire Sinistres Automobile Senior.
14 ans d'expérience : Groupama, AXA, Maif.
BTS Assurance + Licence pro Gestion sinistres.

## Processus de traitement

### Phase 1 — Qualification
Collecter : N° contrat, date/lieu, circonstances, blessés ?, constat ?, PV police ?

### Phase 2 — Vérification contrat
Garanties applicables, franchise, exclusions, validité

### Phase 3 — Score fraude (calculer systématiquement)
Niveau 1 (+5 pts) : déclaration tardive, pas de constat, véhicule récemment assuré
Niveau 2 (+15 pts) : dommages incohérents, tiers ami/famille
Niveau 3 (+30 pts) : faux constat, documents falsifiés
0-19 : standard | 20-39 : surveillance | 40+ : cellule fraude

### Phase 4 — Orientation
Règlement direct / Expertise / VEI / Assistance / Cellule fraude

### Phase 5 — Chiffrage
Valeur vénale (méthode Argus), franchise, VEI si réparations > 80% VV

### Phase 6 — HITL ABSOLU
> 5 000 € → validation gestionnaire senior OBLIGATOIRE
VEI → validation OBLIGATOIRE
Jamais "indemnisation accordée" sans confirmation
Jamais "virement effectué" sans confirmation

## Cadre légal
Loi Badinter (1985), Code des assurances L113-2, L121-1, L211-27
IDA : dommages matériels ≤ 6 500 € HT entre assureurs
Délai offre : 90 jours sinistres matériels, 8 mois corporels

## Format des fichiers produits
Rapport sinistre → /task/output_rapport.md
Offre indemnisation → /task/output_offre.md
Score fraude → /task/output_fraude.json
"""

TOOLS_PRESET = {"type": "preset", "preset": "claude_code"}

CUSTOM_TOOLS = []

EXTERNAL_MCP_SERVERS = {}

SUBAGENTS   = None
HOOKS       = None
AGENT_CWD   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".agent")
SETTING_SOURCES = ["project"]

THINKING = {"type": "enabled", "budget_tokens": 10000}
EFFORT   = None
OUTPUT_FORMAT = None

MODEL          = "claude-sonnet-4-6"
FALLBACK_MODEL = None
MAX_TURNS      = 35
MAX_BUDGET_USD = 1.5
SANDBOX        = None
ENABLE_FILE_CHECKPOINTING = False

def get_options() -> ClaudeAgentOptions:
    mcp = dict(EXTERNAL_MCP_SERVERS)
    if CUSTOM_TOOLS:
        from claude_agent_sdk import create_sdk_mcp_server
        mcp["tools"] = create_sdk_mcp_server("tools", tools=CUSTOM_TOOLS)
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS_PRESET,
        mcp_servers=mcp,
        cwd=AGENT_CWD,
        agents=SUBAGENTS,
        hooks=HOOKS,
        setting_sources=SETTING_SOURCES,
        thinking=THINKING,
        effort=EFFORT,
        output_format=OUTPUT_FORMAT,
        model=MODEL,
        fallback_model=FALLBACK_MODEL,
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
        sandbox=SANDBOX,
        enable_file_checkpointing=ENABLE_FILE_CHECKPOINTING,
        permission_mode="bypassPermissions",
    )

# ===========================================================================
# HARBOR ADAPTER — fixed harness, do not modify
# ===========================================================================

from dotenv import dotenv_values
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

class AutoAgent(BaseAgent):
    SUPPORTS_ATIF = True

    def __init__(self, *args, extra_env=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra_env = dict(extra_env) if extra_env else {}

    @staticmethod
    def name(): return "lucas"
    def version(self): return "1.0.0"
    async def setup(self, environment): pass

    async def run(self, instruction, environment, context):
        await environment.exec(command="mkdir -p /task")
        instr_file = self.logs_dir / "instruction.md"
        instr_file.write_text(instruction)
        await environment.upload_file(source_path=instr_file, target_path="/task/instruction.md")
        env = {"IS_SANDBOX": "1", **dotenv_values()}
        env = {k: v for k, v in env.items() if v}
        env.update(self._extra_env)
        result = await environment.exec(
            command="cd /app && python agent_lucas.py",
            env=env, timeout_sec=600,
        )
        if result.stdout: (self.logs_dir / "agent_stdout.txt").write_text(result.stdout)
        if result.stderr: (self.logs_dir / "agent_stderr.txt").write_text(result.stderr)
        traj_path = self.logs_dir / "trajectory.json"
        if traj_path.exists():
            try:
                fm = json.loads(traj_path.read_text()).get("final_metrics", {})
                context.cost_usd = fm.get("total_cost_usd")
                context.n_input_tokens = fm.get("total_prompt_tokens", 0)
                context.n_output_tokens = fm.get("total_completion_tokens", 0)
                context.n_cache_tokens = fm.get("total_cached_tokens", 0)
            except Exception:
                pass

# ===========================================================================
# CONTAINER ENTRYPOINT — fixed harness, do not modify
# ===========================================================================

def _trajectory_to_atif(messages, result_msg):
    steps, step_id = [], 0
    now = datetime.now(timezone.utc).isoformat()
    pending = {}

    def _step(source, message, **kw):
        nonlocal step_id; step_id += 1
        s = {"step_id": step_id, "timestamp": now, "source": source, "message": message}
        s.update({k: v for k, v in kw.items() if v is not None})
        return s

    from claude_agent_sdk.types import (
        AssistantMessage, UserMessage, TextBlock, ThinkingBlock,
        ToolUseBlock, ToolResultBlock,
    )
    for msg in messages:
        if isinstance(msg, UserMessage):
            if isinstance(msg.content, list):
                all_tool_results = True
                for b in msg.content:
                    if isinstance(b, ToolResultBlock) and b.tool_use_id in pending:
                        tu = pending.pop(b.tool_use_id)
                        content = b.content if isinstance(b.content, str) else json.dumps(b.content) if b.content else ""
                        steps.append(_step("agent", f"Tool: {tu.name}",
                            tool_calls=[{"tool_call_id": tu.id, "function_name": tu.name, "arguments": tu.input}],
                            observation={"results": [{"source_call_id": tu.id, "content": content}]}))
                    else:
                        all_tool_results = False
                if all_tool_results:
                    continue
            text = msg.content if isinstance(msg.content, str) else str(msg.content)
            steps.append(_step("human", text))
        elif isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    steps.append(_step("agent", b.text))
                elif isinstance(b, ThinkingBlock):
                    steps.append(_step("agent", f"<thinking>{b.thinking}</thinking>"))
                elif isinstance(b, ToolUseBlock):
                    pending[b.id] = b

    final = {}
    if result_msg:
        final["cost_usd"] = result_msg.cost_usd
        final["total_input_tokens"] = result_msg.input_tokens
        final["total_output_tokens"] = result_msg.output_tokens

    return {"trajectory": steps, "final": final}


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    instruction_path = Path("/task/instruction.md")
    instruction = instruction_path.read_text() if instruction_path.exists() else "Bonjour Lucas, comment puis-je t'aider ?"

    async def main():
        options = get_options()
        client = ClaudeSDKClient(options)
        messages, result = await client.run(instruction)
        traj = _trajectory_to_atif(messages, result)
        Path("trajectory.json").write_text(json.dumps(traj, ensure_ascii=False, indent=2))
        if result:
            print(f"[Lucas] Coût: ${result.cost_usd:.4f} | Tokens: {result.input_tokens}+{result.output_tokens}")

    asyncio.run(main())
