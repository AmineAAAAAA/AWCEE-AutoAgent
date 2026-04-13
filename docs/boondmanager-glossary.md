# Glossaire BoondManager AVA2i — 72 entrees

## Besoins (Opportunities) — Etats numeriques
| Code | Label brut | Label AVA2i | Urgence |
|---|---|---|---|
| 0 | Brouillon | Brouillon | BAS |
| 1 | En cours | En cours de traitement | NORMAL |
| 2 | Gagne | Gagne — consultant place | SUCCES |
| 3 | Perdu | Perdu — concurrent retenu | BAS |
| 4 | A requalifier | A requalifier avec le client | NORMAL |
| 5 | TOP PRIO | TOP PRIO — sourcer dans 24h | CRITIQUE |
| 9 | Abandonne | Abandonne — client a annule | BAS |

## Candidats (Candidates) — Etats numeriques
| Code | Label | Urgence |
|---|---|---|
| 0 | Nouveau | NORMAL |
| 1 | En cours | NORMAL |
| 2 | Qualifie | NORMAL |
| 3 | Refuse | BAS |
| 4 | En attente | NORMAL |
| 5 | Vivier | NORMAL |
| 6 | Place | SUCCES |
| 7 | Archive | BAS |

## Vivier Candidats — Statuts custom AVA2i (champ title)
| Statut title | Signification | Urgence | Action |
|---|---|---|---|
| TOP ASAP | Disponible MAINTENANT | CRITIQUE | Contacter dans 24h |
| A l'ecoute du marche | Ouvert mais pas actif | NORMAL | Offre ciblee uniquement |
| Entretien Sm en cours | En qualification | NORMAL | Ne pas doublonner |
| Converti en ressource | Devenu consultant AVA2i | INFO | Basculer suivi mission |
| Ne pas jouer | BLACKLIST | INTERDIT | Jamais positionner |

## Resources — Etats
| Code | Label | Urgence | Impact |
|---|---|---|---|
| 0 | Intercontrat | CRITIQUE | Perte CA par jour |
| 1 | En mission | NORMAL | CA actif |
| 2 | Sortie | BAS | Plus dans l'effectif |

## Pipeline Positionnements
Besoin detecte -> TOP PRIO -> En cours de traitement
-> Positionnement cree -> Positionne -> CV Envoye
-> Presentation client -> Attente reponse -> Gagne / Rejete

## Title Parser AVA2i
Les besoins AVA2i utilisent le champ TITLE comme statut custom.
- "TOP ASAP — MOE MUREX Fixed Income" -> status=TOP ASAP, urgency=CRITIQUE
- "TOP PRIO — Senior Java Trading" -> status=TOP PRIO, urgency=URGENT

## Regles pour les agents
1. TOUJOURS traduire les codes numeriques en labels lisibles
2. JAMAIS afficher "state:5" — afficher "TOP PRIO"
3. TOUJOURS trier par urgence (CRITIQUE > URGENT > NORMAL > BAS)
4. Les intercontrats apparaissent TOUJOURS en premier
5. "TOP ASAP" dans un titre = urgence absolue
6. "Ne pas jouer" = BLACKLIST — ne jamais proposer ce profil
