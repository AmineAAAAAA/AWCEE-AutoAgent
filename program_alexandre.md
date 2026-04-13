# AWCEE AutoAgent — Alexandre (DAF)

Autonomous agent engineering. Meta-agent qui ameliore le harness d'Alexandre.

## Directive

Construire Alexandre comme le DAF virtuel le plus percutant pour un CODIR ESN.
1 page max, chiffre, decisionnel.

Objectif de score : >= 0.85 sur toutes les taches Harbor.

## Setup

1. Lire ce fichier, `agent_alexandre.py`
2. Lire `docs/boondmanager-glossary.md`
3. Lire tasks/alexandre/ — instruction.md + verifier.py
4. Initialiser results_alexandre.tsv si absent
5. **Premier run = baseline non modifiee.**

## Ce que tu peux modifier

Tout au-dessus de `# HARBOR ADAPTER` dans agent_alexandre.py.

## Axes d'amelioration

### 1. Tools calcul financier
Tool `calculate_intercontrat_cost(nb_consultants, avg_salary)`.
Tool `calculate_placement_rate(total, en_mission)`.
Tool `calculate_dso(factures)`.

### 2. Format CODIR
Le verifier verifie : < 300 mots, chiffres presents, recommandation.
Alexandre doit produire un brief executive, pas un rapport.

### 3. Multi-source
Croiser Pennylane (facturation) + BoondManager (activite).
Les donnees doivent etre coherentes.

## Contraintes

- MODEL = claude-sonnet-4-6
- MAX_BUDGET_USD = 3.0
- Brief CODIR = max 1 page = max 300 mots
- Toujours une recommandation actionnable

## NEVER STOP

Continue iterating until the human explicitly interrupts you.
