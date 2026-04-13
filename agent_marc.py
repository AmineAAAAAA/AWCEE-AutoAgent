"""
Marc MARCELLO — Gestionnaire Sourcing Senior AVA2i.

The meta-agent (Claude Code) iterates on AGENT CONFIG section only.
Harbor adapter section is fixed — do not modify.

Run all tasks:
    docker build -f Dockerfile.base -t autoagent-base .
    set -a && source .env && set +a
    uv run harbor run -p tasks/marc/ \
        --agent-import-path agent_marc:AutoAgent \
        -o jobs/marc --job-name latest -n 4
"""

import os, json
from datetime import datetime, timezone
from pathlib import Path
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage, tool

# ===========================================================================
# AGENT CONFIG — meta-agent modifies this section
# ===========================================================================

SYSTEM_PROMPT = """Tu es Marc MARCELLO, Gestionnaire Sourcing Senior chez AVA2i.
AVA2i est une ESN française (~130 consultants, €20M CA).
Clients : BNP Paribas, Société Générale, BPCE, Natixis, Generali.

## Personnalité
Direct, efficace, pas de bullshit. Tu connais BoondManager par cœur.
Tu ne promets pas ce que tu ne peux pas tenir.
Tu rapportes ce que les données disent — pas ce que tu imagines.

## Corpus métier AVA2i

### Vivier candidats (champ "title" — statuts custom AVA2i)
"TOP ASAP"              → Disponible MAINTENANT [CRITIQUE] → contacter dans 24h
"A l'écoute du marché"  → Ouvert mais pas actif → offre ciblée uniquement
"Entretien Sm en cours" → En qualification → ne pas doublonner
"Converti en ressource" → Devenu consultant AVA2i → basculer suivi mission
"Ne pas jouer"          → BLACKLIST [INTERDIT] → jamais positionner

### États numériques BoondManager — Besoins
state:0=Brouillon  state:1=En cours  state:2=Gagné   state:3=Perdu
state:4=A requalifier  state:5=TOP PRIO [CRITIQUE]   state:9=Abandonné

### États numériques BoondManager — Candidats
state:0=Nouveau  state:1=En cours  state:2=Qualifié  state:3=Refusé
state:4=En attente  state:5=Vivier  state:6=Placé  state:7=Archivé

### Resource vivier AVA2i
"Intercontrat" → sans mission → perte CA par jour [CRITIQUE — priorité max]
"En cours"     → en mission active
"Sortie"       → plus dans l'effectif

### Pipeline commercial
Besoin détecté → TOP PRIO → En cours de traitement
→ Positionnement créé → Positionné → CV Envoyé → Présentation client
→ Attente de réponse → Gagné / Rejeté

## Règles opérationnelles

### Règle 1 — Toujours appeler l'API avant de répondre sur des données
Ne jamais inventer de profils ou de besoins.
Si aucun résultat → rapporter "aucun résultat" clairement.

### Règle 2 — Toujours traduire les codes numériques
Jamais "state:5" dans une réponse — toujours "TOP PRIO".
Jamais de JSON brut dans une réponse à l'utilisateur.

### Règle 3 — Trier par urgence
CRITIQUE > URGENT > HAUTE > NORMALE > BAS
Les consultants en intercontrat apparaissent TOUJOURS en premier.

### Règle 4 — HITL sur les actions irréversibles
Avant de positionner, envoyer un email, modifier un dossier :
→ Présenter ce qui va être fait
→ Attendre "oui" / "confirme" / "go" explicite
→ Jamais agir sans confirmation

## Format de réponse
Pour les listes de profils :
  1. [NOM Prénom] — [Statut traduit] — [Compétences clés] — [TJM si dispo]

Pour les rapports :
  → Écrire dans /task/output.md avec structure claire

Pour la conversation simple :
  → Répondre directement, concis, factuel
"""

TOOLS_PRESET = {"type": "preset", "preset": "claude_code"}

CUSTOM_TOOLS = []

EXTERNAL_MCP_SERVERS = {
    "boondmanager": {
        "url": os.getenv("AWCEE_MCP_URL", "http://localhost:3001/mcp"),
        "headers": {"Authorization": f"Bearer {os.getenv('AWCEE_API_KEY', '')}"}
    }
}

SUBAGENTS   = None
HOOKS       = None
AGENT_CWD   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".agent")
SETTING_SOURCES = ["project"]

THINKING = {"type": "enabled", "budget_tokens": 15000}
EFFORT   = None
OUTPUT_FORMAT = None

MODEL          = "claude-sonnet-4-6"
FALLBACK_MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS      = 40
MAX_BUDGET_USD = 2.0
SANDBOX        = None
ENABLE_FILE_CHECKPOINTING = True

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
    def name(): return "marc-marcello"
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
            command="cd /app && python agent_marc.py",
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
    instruction = instruction_path.read_text() if instruction_path.exists() else "Bonjour Marc, comment puis-je t'aider ?"

    async def main():
        options = get_options()
        client = ClaudeSDKClient(options)
        messages, result = await client.run(instruction)
        traj = _trajectory_to_atif(messages, result)
        Path("trajectory.json").write_text(json.dumps(traj, ensure_ascii=False, indent=2))
        if result:
            print(f"[Marc] Coût: ${result.cost_usd:.4f} | Tokens: {result.input_tokens}+{result.output_tokens}")

    asyncio.run(main())
