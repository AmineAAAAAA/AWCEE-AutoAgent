"""
Marc MARCELLO — Gestionnaire Sourcing Senior AVA2i.
The meta-agent (Claude Code) iterates on AGENT CONFIG section only.

Run: docker build -f Dockerfile.base -t autoagent-base .
     set -a && source .env && set +a
     uv run harbor run -p tasks/marc/ --agent-import-path agent_marc:AutoAgent -o jobs/marc --job-name latest -n 4
"""

import asyncio, os, json
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, ResultMessage, tool
from claude_agent_sdk.types import (
    AssistantMessage, UserMessage, TextBlock, ThinkingBlock,
    ToolUseBlock, ToolResultBlock,
)

# ===========================================================================
# AGENT CONFIG — meta-agent modifies this section
# ===========================================================================

SYSTEM_PROMPT = """Tu es Marc MARCELLO, Gestionnaire Sourcing Senior chez AVA2i.
AVA2i est une ESN francaise (~130 consultants, 20M EUR CA).
Clients : BNP Paribas, Societe Generale, BPCE, Natixis, Generali.

## Personnalite
Direct, efficace, pas de bullshit. Tu connais BoondManager par coeur.
Tu rapportes ce que les donnees disent — pas ce que tu imagines.

## Corpus metier AVA2i

### Vivier candidats (champ "title" — statuts custom AVA2i)
"TOP ASAP" = Disponible MAINTENANT [CRITIQUE] contacter dans 24h
"A l'ecoute du marche" = Ouvert mais pas actif
"Entretien Sm en cours" = En qualification — ne pas doublonner
"Converti en ressource" = Devenu consultant AVA2i
"Ne pas jouer" = BLACKLIST — jamais positionner

### Etats numeriques BoondManager — Besoins
state:0=Brouillon state:1=En cours state:2=Gagne state:3=Perdu
state:4=A requalifier state:5=TOP PRIO [CRITIQUE] state:9=Abandonne

### Etats numeriques BoondManager — Candidats
state:0=Nouveau state:1=En cours state:2=Qualifie state:3=Refuse
state:4=En attente state:5=Vivier state:6=Place state:7=Archive

### Resource vivier AVA2i
"Intercontrat" = sans mission = perte CA par jour [CRITIQUE]
"En cours" = en mission active
"Sortie" = plus dans l'effectif

## Regles operationnelles

1. TOUJOURS appeler l'API BoondManager avant de repondre sur des donnees.
   Ne jamais inventer de profils ou de besoins.
2. TOUJOURS traduire les codes numeriques. Jamais "state:5" — toujours "TOP PRIO".
3. Trier par urgence : CRITIQUE > URGENT > NORMAL > BAS.
   Les intercontrats apparaissent TOUJOURS en premier.
4. Si aucun resultat → rapporter "aucun resultat" clairement. N'invente rien.

## REGLE ABSOLUE — ECRITURE FICHIER

Tu DOIS TOUJOURS ecrire ta reponse dans /task/output.md.
Utilise l'outil Bash pour creer le fichier : echo "contenu" > /task/output.md
Ou utilise l'outil Write pour ecrire directement dans /task/output.md.
NE JAMAIS terminer sans avoir ecrit /task/output.md.
Verifie que le fichier existe avec : cat /task/output.md
"""

TOOLS_PRESET = {"type": "preset", "preset": "claude_code"}

# ── BOONDMANAGER TOOLS ────────────────────────────────────────

@tool(name="boondmanager_list_resources",
      description="Liste les consultants/resources AVA2i depuis BoondManager API.",
      input_schema={"keywords": str, "limit": int})
def boondmanager_list_resources(keywords: str = "", limit: int = 50) -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    url = f"{base}/resources?page[size]={int(limit)}"
    if keywords:
        url += f"&keywords={urllib.request.quote(str(keywords))}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        items = [{"id": i["id"], **i.get("attributes", {})} for i in data.get("data", [])]
        return json.dumps({"success": True, "count": len(items), "resources": items[:25]}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool(name="boondmanager_list_candidates",
      description="Liste les candidats depuis BoondManager API. Filtre par keywords.",
      input_schema={"keywords": str, "limit": int})
def boondmanager_list_candidates(keywords: str = "", limit: int = 50) -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    url = f"{base}/candidates?page[size]={int(limit)}"
    if keywords:
        url += f"&keywords={urllib.request.quote(str(keywords))}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        items = [{"id": i["id"], **i.get("attributes", {})} for i in data.get("data", [])]
        return json.dumps({"success": True, "count": len(items), "candidates": items[:25]}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool(name="boondmanager_list_needs",
      description="Liste les besoins clients (opportunities) ouverts depuis BoondManager.",
      input_schema={"limit": int})
def boondmanager_list_needs(limit: int = 50) -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    url = f"{base}/opportunities?page[size]={int(limit)}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        items = [{"id": i["id"], **i.get("attributes", {})} for i in data.get("data", [])]
        return json.dumps({"success": True, "count": len(items), "needs": items[:25]}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool(name="boondmanager_get_resource",
      description="Detail complet d'un consultant par son ID BoondManager.",
      input_schema={"resource_id": str})
def boondmanager_get_resource(resource_id: str) -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    req = urllib.request.Request(f"{base}/resources/{resource_id}")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return json.dumps({"success": True, "resource": {"id": data["data"]["id"], **data["data"].get("attributes", {})}}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool(name="boondmanager_get_need",
      description="Detail complet d'un besoin client par son ID BoondManager.",
      input_schema={"need_id": str})
def boondmanager_get_need(need_id: str) -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    req = urllib.request.Request(f"{base}/opportunities/{need_id}")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return json.dumps({"success": True, "need": {"id": data["data"]["id"], **data["data"].get("attributes", {})}}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool(name="boondmanager_list_positionings",
      description="Liste les positionnements (matchings consultant-besoin).",
      input_schema={"limit": int})
def boondmanager_list_positionings(limit: int = 50) -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    url = f"{base}/positionings?page[size]={int(limit)}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        items = [{"id": i["id"], **i.get("attributes", {})} for i in data.get("data", [])]
        return json.dumps({"success": True, "count": len(items), "positionings": items[:25]}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool(name="boondmanager_get_candidate",
      description="Detail complet d'un candidat par son ID BoondManager.",
      input_schema={"candidate_id": str})
def boondmanager_get_candidate(candidate_id: str) -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    req = urllib.request.Request(f"{base}/candidates/{candidate_id}")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return json.dumps({"success": True, "candidate": {"id": data["data"]["id"], **data["data"].get("attributes", {})}}, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool(name="boondmanager_create_positioning",
      description="Creer un positionnement consultant-besoin. ACTION IRREVERSIBLE — confirmer avant.",
      input_schema={"need_id": str, "resource_id": str, "note": str})
def boondmanager_create_positioning(need_id: str, resource_id: str, note: str = "Positionne via AWCEE") -> str:
    import urllib.request
    base = os.getenv("BOONDMANAGER_BASE_URL", "https://ui.boondmanager.com/api")
    token = os.getenv("BOONDMANAGER_TOKEN", "")
    body = json.dumps({"data": {"type": "positioning", "attributes": {"needId": need_id, "resourceId": resource_id, "comment": note}}}).encode()
    req = urllib.request.Request(f"{base}/positionings", data=body, method="POST")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return json.dumps({"success": True, "positioning_id": data.get("data", {}).get("id")})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

CUSTOM_TOOLS = [
    boondmanager_list_resources, boondmanager_list_candidates, boondmanager_list_needs,
    boondmanager_get_resource, boondmanager_get_need, boondmanager_get_candidate,
    boondmanager_list_positionings, boondmanager_create_positioning,
]

EXTERNAL_MCP_SERVERS = {}
SUBAGENTS = None
HOOKS = None
AGENT_CWD = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".agent")
SETTING_SOURCES = ["project"]

THINKING = {"type": "enabled", "budget_tokens": 15000}
EFFORT = None
OUTPUT_FORMAT = None
MODEL = "claude-sonnet-4-6"
FALLBACK_MODEL = "claude-haiku-4-5-20251001"
MAX_TURNS = 40
MAX_BUDGET_USD = 2.0
SANDBOX = None
ENABLE_FILE_CHECKPOINTING = True


def get_options() -> ClaudeAgentOptions:
    mcp = dict(EXTERNAL_MCP_SERVERS)
    if CUSTOM_TOOLS:
        from claude_agent_sdk import create_sdk_mcp_server
        mcp["tools"] = create_sdk_mcp_server("tools", tools=CUSTOM_TOOLS)
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT, tools=TOOLS_PRESET, mcp_servers=mcp,
        cwd=AGENT_CWD, agents=SUBAGENTS, hooks=HOOKS, setting_sources=SETTING_SOURCES,
        thinking=THINKING, effort=EFFORT, output_format=OUTPUT_FORMAT,
        model=MODEL, fallback_model=FALLBACK_MODEL,
        max_turns=MAX_TURNS, max_budget_usd=MAX_BUDGET_USD,
        sandbox=SANDBOX, enable_file_checkpointing=ENABLE_FILE_CHECKPOINTING,
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
            if text:
                steps.append(_step("user", text))
        elif isinstance(msg, AssistantMessage):
            texts, reasoning = [], None
            for b in msg.content:
                if isinstance(b, TextBlock): texts.append(b.text)
                elif isinstance(b, ThinkingBlock): reasoning = b.thinking
                elif isinstance(b, ToolUseBlock): pending[b.id] = b
            if texts or reasoning:
                steps.append(_step("agent", "\n".join(texts) or "(thinking)",
                    reasoning_content=reasoning, model_name=msg.model))

    for tu in pending.values():
        steps.append(_step("agent", f"Tool: {tu.name}",
            tool_calls=[{"tool_call_id": tu.id, "function_name": tu.name, "arguments": tu.input}]))

    if not steps:
        steps.append(_step("user", "(empty)"))

    fm = None
    if result_msg:
        fm = {"total_prompt_tokens": getattr(result_msg, 'input_tokens', None),
              "total_completion_tokens": getattr(result_msg, 'output_tokens', None),
              "total_cost_usd": getattr(result_msg, 'total_cost_usd', None),
              "total_steps": len(steps),
              "extra": {"duration_ms": getattr(result_msg, 'duration_ms', 0),
                        "num_turns": getattr(result_msg, 'num_turns', 0)}}

    return {"schema_version": "ATIF-v1.2",
            "session_id": getattr(result_msg, 'session_id', 'unknown') if result_msg else "unknown",
            "agent": {"name": "marc-marcello", "version": "1.0.0", "model_name": MODEL},
            "steps": steps, "final_metrics": fm}


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
        print(f"cost_usd={getattr(result_msg, 'total_cost_usd', 0) or 0:.4f} "
              f"turns={getattr(result_msg, 'num_turns', 0)} "
              f"duration_ms={getattr(result_msg, 'duration_ms', 0)}")


if __name__ == "__main__":
    _run_in_container()
