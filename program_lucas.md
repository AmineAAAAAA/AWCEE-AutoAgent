# AWCEE AutoAgent — Lucas Martin (Sinistres Auto)

Autonomous agent engineering. Meta-agent qui ameliore le harness de Lucas.

## Directive

Construire Lucas comme le gestionnaire sinistres auto le plus rigoureux.
Score fraude systematique, HITL > 5000 EUR, cadre legal Code assurances.

Objectif de score : >= 0.88 sur toutes les taches Harbor.

## Setup

1. Lire ce fichier, `agent_lucas.py`
2. Lire tasks/lucas/ — instruction.md + verifier.py
3. Initialiser results_lucas.tsv si absent
4. **Premier run = baseline non modifiee.**

## Ce que tu peux modifier

Tout au-dessus de `# HARBOR ADAPTER` dans agent_lucas.py.

## Axes d'amelioration

### 1. Tool score fraude structure
Tool `calculate_fraud_score(indicators)` avec grille 3 niveaux.
Retourne un JSON : {score, level, indicators, recommendation}.

### 2. Tool valeur venale Argus
Tool `estimate_vehicle_value(marque, modele, annee, km)`.
Methode Argus simplifiee.

### 3. HITL strict
Jamais "indemnisation accordee" sans confirmation.
Le verifier verifie ca explicitement.

## Contraintes

- MODEL = claude-sonnet-4-6
- MAX_BUDGET_USD = 1.5
- > 5000 EUR = validation obligatoire
- VEI = validation obligatoire
- Loi Badinter, IDA, Code assurances toujours cites

## NEVER STOP

Continue iterating until the human explicitly interrupts you.
