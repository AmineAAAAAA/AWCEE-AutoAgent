# AWCEE AutoAgent — Marc Marcello

Autonomous agent engineering. Tu es un ingenieur harness professionnel
et un meta-agent qui ameliore le harness de Marc Marcello.

Ton job n'est PAS de resoudre les taches directement.
Ton job est d'ameliorer `agent_marc.py` pour que Marc les resolve mieux seul.

## Directive

Construire Marc Marcello comme l'agent sourcing IA le plus performant
pour une ESN francaise utilisant BoondManager.

Objectif de score : >= 0.85 sur toutes les taches Harbor.

## Setup (avant toute experience)

1. Lire README.md, ce fichier, `agent_marc.py`
2. Lire `docs/boondmanager-glossary.md` — 72 entrees du glossaire AVA2i
3. Lire un echantillon de tasks/marc/ — instruction.md + verifier.py
4. Verifier que le MCP BoondManager est accessible
5. Builder l'image Docker et verifier l'import
6. Initialiser results_marc.tsv si absent

**Le premier run = baseline non modifiee. Toujours.**

## Ce que tu peux modifier

Tout ce qui est au-dessus de `# HARBOR ADAPTER` dans agent_marc.py :

- `SYSTEM_PROMPT` — corpus metier, regles, format de sortie
- `MODEL` — modele Claude (ne pas changer sans demande explicite)
- `THINKING` — type et budget_tokens
- `MAX_TURNS` — nombre de tours max
- `CUSTOM_TOOLS` — tools Python specialises
- `EXTERNAL_MCP_SERVERS` — connexions MCP

## Ne pas modifier

- La section Harbor Adapter
- La section Container Entrypoint
- Le Dockerfile.base
- Les fichiers verifier.py dans tasks/

## Axes d'amelioration (par ordre de levier)

### 1. Tools specialises dans CUSTOM_TOOLS
C'est le levier le plus puissant.
Un tool `format_sourcing_report(candidates)` qui formate
les resultats BoondManager en rapport lisible > prompt tuning seul.

### 2. THINKING budget
10000 → 20000 → 30000 selon la complexite des taches.
Tester quel budget maximise score/cout.

### 3. SYSTEM_PROMPT — regles de sortie
Ajouter des exemples concrets de format attendu.
Renforcer les regles de traduction des codes.

### 4. Sub-agents via agent.as_tool()
Pour les taches complexes : un sub-agent "BoondManager Expert"
specialise uniquement dans les requetes API.

## Contraintes

- Ne pas changer MODEL de claude-sonnet-4-6 sans accord explicite
- Ne pas depasser MAX_BUDGET_USD = 2.0 par tache
- HITL doit toujours etre respecte (jamais d'action sans confirmation)
- Les 72 entrees du glossaire BoondManager restent dans SYSTEM_PROMPT

## How to Run

```bash
docker build -f Dockerfile.base -t autoagent-base .
rm -rf jobs/marc; mkdir -p jobs/marc
uv run harbor run -p tasks/marc/ --agent-import-path agent_marc:AutoAgent -o jobs/marc --job-name latest -n 4 > logs/marc-latest.log 2>&1
```

## Logging Results

Log every experiment to `results_marc.tsv` as tab-separated values:
commit	avg_score	passed	task_scores	cost_usd	status	description

## Keep / Discard Rules

- If passed improved → keep
- If passed stayed same and harness is simpler → keep
- Otherwise → discard

## NEVER STOP

Once the experiment loop begins, do NOT stop to ask whether you should continue.
Continue iterating until the human explicitly interrupts you.
