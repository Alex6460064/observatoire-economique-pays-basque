# Évaluation de l'attribution sectorielle par Jev

> Généré par `uv run obs evaluer-jev` le 2026-09-23 — modèle jev-1.13.0, question `naf-division-v1`, échantillon de 300 annonces.

**Protocole.** Échantillon aléatoire reproductible d'événements BODACC publiés du périmètre dont le code NAF est connu par Sirene (vérité terrain). Seul le texte d'activité est envoyé à Jev ; on compare sa réponse au code Sirene. Limite : le code Sirene (APE déclarée de l'unité légale) et l'activité décrite dans l'annonce peuvent légitimement différer.

## Résultats

- Division la plus probable juste (sans politique) : **62 %**
- Section déduite juste (sans politique) : **75 %**

Politique retenue (division si confiance ≥ 0.9, sinon section si sa masse ≥ 0.8) :

| Niveau attribué | Part des annonces | Précision |
|---|---|---|
| Division | 55 % | 84 % |
| Section seule | 20 % | 90 % |
| Non attribué | 24 % | – |
| **Ensemble des attributions** | 76 % | **86 %** |

## Calibration : la confiance annonce-t-elle la justesse ?

| Confiance | Annonces | Division juste |
|---|---|---|
| [0.3 ; 0.5[ | 28 | 21 % |
| [0.5 ; 0.7[ | 51 | 24 % |
| [0.7 ; 0.9[ | 54 | 56 % |
| [0.9 ; 1.0] | 167 | 83 % |

## Grille des seuils

| Seuil division | Seuil section | Division (part / précision) | Section (part / précision) | Non attribué | Précision globale |
|---|---|---|---|---|---|
| 0.5 | 0.6 | 88 % / 68 % | 2 % / 57 % | 9 % | 68 % |
| 0.5 | 0.8 | 88 % / 68 % | 0 % / 100 % | 11 % | 68 % |
| 0.5 | 0.9 | 88 % / 68 % | 0 % / – | 12 % | 68 % |
| 0.7 | 0.6 | 72 % / 78 % | 16 % / 68 % | 12 % | 76 % |
| 0.7 | 0.8 | 72 % / 78 % | 7 % / 86 % | 21 % | 79 % |
| 0.7 | 0.9 | 72 % / 78 % | 5 % / 80 % | 23 % | 78 % |
| 0.8 | 0.6 | 65 % / 81 % | 22 % / 70 % | 12 % | 78 % |
| 0.8 | 0.8 | 65 % / 81 % | 10 % / 87 % | 24 % | 82 % |
| 0.8 | 0.9 | 65 % / 81 % | 7 % / 85 % | 28 % | 82 % |
| 0.9 | 0.6 | 55 % / 84 % | 32 % / 77 % | 12 % | 81 % |
| 0.9 | 0.8 | 55 % / 84 % | 20 % / 90 % | 24 % | 86 % |
| 0.9 | 0.9 | 55 % / 84 % | 11 % / 91 % | 33 % | 85 % |
