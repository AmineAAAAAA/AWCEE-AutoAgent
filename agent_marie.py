import asyncio
"""
Marie — Experte PAC 2023-2027, Telepac, Éco-régimes, MAEC.
The meta-agent (Claude Code) iterates on AGENT CONFIG section only.

Run all tasks:
    docker build -f Dockerfile.base -t autoagent-base .
    set -a && source .env && set +a
    uv run harbor run -p tasks/marie/ \
        --agent-import-path agent_marie:AutoAgent \
        -o jobs/marie --job-name latest -n 4
"""

import os, json
from datetime import datetime, timezone
from pathlib import Path
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage, tool

# ===========================================================================
# AGENT CONFIG — meta-agent modifies this section
# ===========================================================================

SYSTEM_PROMPT = """Tu es Marie, experte PAC (Politique Agricole Commune) 2023-2027.
Tu guides les agriculteurs pour leurs déclarations, formulaires et démarches.

## Expertise

### PAC 2023-2027
Déclaration annuelle sur Telepac (avant le 15 mai)
Numéro Pacage = 9 chiffres (identifiant DDT)
Surface admissible = surface déclarée éligible aux aides

### Éco-régimes — 3 voies possibles
1. BIODIVERSITÉ : ≥10% surface en éléments favorables (haies, bandes fleuries...)
2. CERTIFICATION : HVE niveau 3 ou Agriculture Biologique
3. PRATIQUES AGRO : couverture sols, rotations, légumineuses
Paiement 2026 : ~60-65 €/ha selon la voie
Une seule voie possible par exploitant

### MAEC (Mesures Agro-Environnementales et Climatiques)
Engagement 5 ans minimum
Cahier des charges strict par mesure
Compatibilité avec éco-régimes à vérifier

### BCAE (Bonnes Conditions Agricoles et Environnementales)
Conditionnalité obligatoire pour recevoir les aides :
BCAE 1 : maintien prairies permanentes
BCAE 4 : bandes tampons cours d'eau (min 3m)
BCAE 6 : couverture minimale sols en hiver
BCAE 7 : rotation des cultures (min 3 cultures si >10ha)
BCAE 8 : SAIE ≥4% surface arable

## Règles de guidage
- Une seule question à la fois (jamais de liste)
- Langage agriculteur — zéro jargon administratif
- Valider chaque réponse avant de passer à la suivante
- Rappeler les délais : PAC avant 15 mai, pénalités après
- HITL avant toute soumission définitive

## Format des fichiers produits
Pour les formulaires pré-remplis → /task/output_[formname].pdf
Pour les récapitulatifs → /task/output_summary.md
Pour les calculs éco-régimes → /task/output_ecoregimes.json
"""

TOOLS_PRESET = {"type": "preset", "preset": "claude_code"}

CUSTOM_TOOLS = []

EXTERNAL_MCP_SERVERS = {
    "awcee-agri": {
        "url": os.getenv("AWCEE_MCP_URL", "http://localhost:3001/mcp"),
        "headers": {"Authorization": f"Bearer {os.getenv('AWCEE_API_KEY', '')}"}
    }
}

SUBAGENTS   = None
HOOKS       = None
AGENT_CWD   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".agent")
SETTING_SOURCES = ["project"]

THINKING = {"type": "enabled", "budget_tokens": 12000}
EFFORT   = None
OUTPUT_FORMAT = None

MODEL          = "claude-sonnet-4-6"
FALLBACK_MODEL = None
MAX_TURNS      = 45
MAX_BUDGET_USD = 2.0
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
    def name(): return "marie"
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
            command="cd /app && python agent_marie.py",
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
        final["cost_usd"] = getattr(result_msg, "total_cost_usd", None) or getattr(result_msg, "cost_usd", None)
        final["total_input_tokens"] = getattr(result_msg, "input_tokens", None)
        final["total_output_tokens"] = getattr(result_msg, "output_tokens", None)

    if result_msg:
        u = getattr(result_msg, 'usage', None) or {}
        fm = {"total_prompt_tokens": getattr(u, 'input_tokens', None),
              "total_completion_tokens": getattr(u, 'output_tokens', None),
              "total_cost_usd": getattr(result_msg, 'total_cost_usd', None),
              "total_steps": len(steps),
              "extra": {"duration_ms": getattr(result_msg, 'duration_ms', 0), "num_turns": getattr(result_msg, 'num_turns', 0)}}
    else:
        fm = None

    return {"schema_version": "ATIF-v1.2", "session_id": getattr(result_msg, 'session_id', 'unknown') if result_msg else "unknown",
            "agent": {"name": "marie", "version": "1.0.0", "model_name": MODEL}, "steps": steps, "final_metrics": fm}


def _run_in_container():
    instruction = open("/task/instruction.md").read().strip()

    async def _run():
        opts = get_options()
        trajectory, result_msg = [], None
        async with ClaudeSDKClient(options=opts) as client:
            await client.query(instruction)
            async for msg in client.receive_response():
                trajectory.append(msg)
                if isinstance(msg, ResultMessage):
                    result_msg = msg
        return trajectory, result_msg

    trajectory, result_msg = asyncio.run(_run())
    atif = _trajectory_to_atif(trajectory, result_msg)
    traj_dir = Path("/logs/agent")
    traj_dir.mkdir(parents=True, exist_ok=True)
    (traj_dir / "trajectory.json").write_text(json.dumps(atif, indent=2))
    if result_msg:
        print(f"cost_usd={getattr(result_msg, 'total_cost_usd', 0) or 0:.4f}")


if __name__ == "__main__":
    _run_in_container()
