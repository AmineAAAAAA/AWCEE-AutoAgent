# AWCEE-AutoAgent

Architecture kevinrgu/autoagent pour les agents AWCEE.
Chaque agent = fichier Python avec CONFIG modifiable + HARBOR adapter fixe.

## Agents

| Agent | Fichier | Modele | Budget | Objectif |
|---|---|---|---|---|
| Marc Marcello (Sourcing) | agent_marc.py | sonnet | $2.0 | >= 0.85 |
| Igor (CEO Assistant) | agent_igor.py | opus | $5.0 | >= 0.90 |
| Marie (PAC Expert) | agent_marie.py | sonnet | $2.0 | >= 0.85 |
| Lucas Martin (Sinistres) | agent_lucas.py | sonnet | $1.5 | >= 0.88 |
| Alexandre (DAF) | agent_alexandre.py | sonnet | $3.0 | >= 0.85 |
| Agent General | agent_general.py | haiku | $0.3 | >= 0.80 |

## Quick start

```bash
cp .env.example .env   # remplir les cles
uv sync
docker build -f Dockerfile.base -t autoagent-base .

# Baseline Marc
uv run harbor run -p tasks/marc/ --agent-import-path agent_marc:AutoAgent -o jobs/marc --job-name baseline -n 4

# Lancer le meta-agent
# Dans Claude Code : "Read program_marc.md !"
```

## Boucle d'amelioration

1. Meta-agent lit program_X.md
2. Modifie AGENT CONFIG dans agent_X.py
3. Run Harbor benchmark
4. Score monte -> garde, score baisse -> rollback
5. Repete toute la nuit
