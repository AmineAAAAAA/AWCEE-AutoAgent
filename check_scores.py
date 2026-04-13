"""Vérification des scores objectifs pour tous les agents AWCEE."""
import json
from pathlib import Path

AGENTS = {
    "marc":      {"label": "Marc Marcello",   "target": 0.85},
    "igor":      {"label": "Igor",            "target": 0.90},
    "marie":     {"label": "Marie (PAC)",     "target": 0.85},
    "lucas":     {"label": "Lucas Martin",    "target": 0.88},
    "alexandre": {"label": "Alexandre (DAF)", "target": 0.85},
    "general":   {"label": "Agent Général",   "target": 0.80},
}

print("=" * 55)
print("AWCEE AGENTS — SCORES DE PRODUCTION")
print("=" * 55)

all_pass = True
for agent_id, cfg in AGENTS.items():
    score_file = Path(f"jobs/{agent_id}/latest/score_summary.json")
    if not score_file.exists():
        print(f"{cfg['label']:<22}: ⚪ PAS DE DONNÉES")
        continue

    data  = json.loads(score_file.read_text())
    score = data.get("mean_score", 0)
    ok    = score >= cfg["target"]
    icon  = "✅" if ok else "❌"
    if not ok: all_pass = False

    print(f"{cfg['label']:<22}: {score:.2f} {icon} (objectif {cfg['target']})")

print("=" * 55)
print("RÉSULTAT GLOBAL:", "✅ TOUS EN PRODUCTION" if all_pass else "❌ AMÉLIORATION REQUISE")
