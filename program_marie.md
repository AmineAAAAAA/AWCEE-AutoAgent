# AWCEE AutoAgent — Marie (PAC Expert)

Autonomous agent engineering. Meta-agent qui ameliore le harness de Marie.

## Directive

Construire Marie comme l'experte PAC la plus fiable pour les agriculteurs francais.
Guidage question par question, langage simple, zero jargon.

Objectif de score : >= 0.85 sur toutes les taches Harbor.

## Setup

1. Lire ce fichier, `agent_marie.py`
2. Lire tasks/marie/ — instruction.md + verifier.py
3. Initialiser results_marie.tsv si absent
4. **Premier run = baseline non modifiee.**

## Ce que tu peux modifier

Tout au-dessus de `# HARBOR ADAPTER` dans agent_marie.py.

## Axes d'amelioration

### 1. Tools de validation PAC
Tool `validate_pacage(numero)` qui verifie le format 9 chiffres.
Tool `check_eco_regime_eligibility(surface, certif)` qui calcule.

### 2. Langage agriculteur
Le verifier penalise le jargon administratif.
Marie doit parler comme une conseillere Chambre d'Agriculture.

### 3. Dates et delais
Toujours rappeler : PAC avant 15 mai, penalites apres.
Le verifier verifie la presence de la date.

## Contraintes

- MODEL = claude-sonnet-4-6
- MAX_BUDGET_USD = 2.0
- Langage simple obligatoire — zero code bureaucratique
- Numeros Pacage = exactement 9 chiffres

## NEVER STOP

Continue iterating until the human explicitly interrupts you.
