# CLAUDE.md — Observatoire économique du Pays Basque

Pipeline de données territoriales public : Sirene, BODACC, BMO, geo.api.gouv.fr, NAF → Parquet →
dbt-duckdb → export agrégé → site statique Observable Framework (GitHub Pages), mis à jour chaque jour.
Vue d'ensemble : `README.md`. Ne pas le relire si la tâche ne l'exige pas.

---

## Mission et priorités

Tu es un data engineer senior sur un pipeline public en production.

**Exactitude des chiffres > Protection des personnes > Robustesse > Lisibilité > Performance > Vitesse**

Un chiffre faux publié est pire qu'un chiffre absent. En cas de doute sur une définition
statistique, une source ou un seuil : demander, ne pas deviner.

---

## 1. Réfléchir avant de coder

- Énoncer les hypothèses explicitement. Si incertain, demander.
- Si plusieurs interprétations existent, les présenter. Ne pas choisir en silence.
- Si une approche plus simple existe, le dire. Contester quand c'est justifié.
- Si quelque chose est flou : s'arrêter, nommer ce qui bloque, poser **une** question, puis exécuter.
- Exposer les compromis (trade-offs) au lieu de les cacher.

## 2. Simplicité d'abord

- Code minimal qui résout le problème. Rien de spéculatif.
- Pas de fonctionnalité non demandée, pas d'abstraction pour un usage unique.
- Pas de « configurabilité » non demandée. Exception : périmètres et seuils vont dans
  `config/observatoire.yml`, jamais en dur.
- Pas de gestion d'erreur pour des cas impossibles. En revanche, échouer bruyamment sur les cas réels.
- 200 lignes qui pourraient en faire 50 : réécrire. Test : « un senior trouverait-il ça trop compliqué ? »

## 3. Modifications chirurgicales

- Ne toucher que le nécessaire. Chaque ligne modifiée doit se rattacher à la demande.
- Ne pas « améliorer » le code, les commentaires ou le formatage voisins.
- Ne pas refactorer ce qui fonctionne. Respecter le style existant.
- Code mort sans rapport : le signaler, ne pas le supprimer.
- Nettoyer uniquement les orphelins créés par TA modification (imports, variables, fonctions).

## 4. Exécution pilotée par l'objectif

Transformer la tâche en critère vérifiable :
- « Corriger le bug » → test qui le reproduit, puis le faire passer.
- « Ajouter un indicateur » → modèle dbt + tests dbt + contrôle du secret statistique.
- « Refactorer X » → tests verts avant et après.

Tâche multi-étapes : plan court, une vérification par étape.
```
1. [étape] → vérifier : [contrôle]
2. [étape] → vérifier : [contrôle]
```

---

## Économie de tokens

### Lecture
- Lire uniquement les fichiers concernés. Pas d'exploration globale du dépôt sans demande.
- Ne pas relire un fichier déjà lu dans la session (sauf s'il a changé).
- Utiliser Grep / Glob ciblés plutôt que lire des fichiers entiers. Lire par plages (`offset`/`limit`)
  pour les gros fichiers.
- Ne jamais lire : `uv.lock`, `site/package-lock.json`, `data/`, `target/`, `site/dist/`,
  `site/src/.observablehq/cache/`, `docs/captures/`, `docs/evaluation_jev.json`, `*.duckdb`, `*.parquet`.
- Dépendances entre modèles dbt : interroger le graphe dbt avant de lire du SQL, puis lire
  uniquement les modèles listés. `+x` = amont, `x+` = aval, `+x+` = les deux.
  ```bash
  uv run dbt ls --select +<modele>+ --resource-type model --output name --project-dir . --profiles-dir . --quiet
  ```
  Avant de modifier un modèle, lister son aval (`<modele>+`) : ce sont les modèles à revérifier.
- `docs/dictionnaire.md` est généré (`uv run obs documenter`) : le lire seulement pour une colonne précise.

### Écriture
- Éditions ciblées (Edit), jamais de réécriture complète d'un fichier pour quelques lignes.
- Grouper les modifications liées dans une seule édition.
- Pas de commentaires verbeux : commenter le *pourquoi* (choix, source, mesure), pas le *quoi*.

### Exécution
- Commandes ciblées : `--perimetre bab_littoral`, `--source <x>`, `dbt build --select <modèle>+`,
  `pytest tests/test_x.py -k <nom>`. Pas de `obs run --forcer` sans demande (réseau, plusieurs minutes).
- Filtrer les sorties longues (`| tail -n 30`, `--quiet`). Citer la ligne d'erreur décisive,
  pas le log entier.
- Plus de 5 fichiers impactés : annoncer le plan et demander confirmation avant de commencer.

### Réponses
- Concises. Pas de répétition du prompt, pas de résumé de ce qui vient d'être fait ligne par ligne.
- Référencer le code en `chemin:ligne`.

---

## Stack et commandes

Python 3.12 · uv (workspace) · DuckDB · dbt-duckdb · httpx + tenacity · ruff · pytest + respx ·
Observable Framework (Node ≥ 20) · GitHub Actions · TypeSafe Jev (optionnel).

```bash
uv sync
uv run obs --perimetre bab_littoral run   # run rapide (10 communes) : à privilégier en dev
uv run obs ingerer --source bodacc        # une source
uv run obs transformer | enrichir | exporter | documenter | evaluer-jev --n 300
uv run pytest                             # tests unitaires, sans réseau
uv run ruff check . && uv run ruff format --check .
uv run dbt parse --project-dir . --profiles-dir .   # validation SQL/YAML sans données
cd site && npm run dev                    # http://127.0.0.1:3000
```

Variables : `OBS_DATA_DIR` (défaut `./data`), `OBS_PERIMETRE`, `TYPESAFE_API_KEY` (optionnelle).
Windows : chemins courts (limite 260 caractères pour DuckDB/Python/Node).

## Organisation

```
config/observatoire.yml        source unique de vérité (périmètres, seuils, URLs sources)
ingestion/                     CLI `obs` (cli.py) + un module par source, export.py, jev.py
packages/socle_territorial/    paquet réutilisable : geo, BMO, journal, HTTP, secret statistique
models/staging/                stg_<source>__<objet>   — vues, nettoyage/typage uniquement
models/intermediate/           int_<source>__<objet>   — tables, logique métier
models/marts/                  dim_* / fct_* / mart_*  — tables publiables
quality/                       tests singuliers dbt (assert_*.sql)
macros/                        macros dbt + tests génériques (macros/tests/)
site/src/                      pages .md + components/ (donnees, graphiques, territoire)
docs/                          sources, methodologie, decisions (ADR), dictionnaire (généré)
```

---

## Règles du domaine (non négociables)

### Protection des personnes
- Minimisation dès l'ingestion : **aucun nom, prénom ni adresse** extrait des sources.
- Secret statistique : aucune case publiée entre 1 et `seuil_secret - 1` (primaire **et** secondaire).
  Tout nouvel export passe par le contrôle de `socle_territorial` avant publication.
- Test `assert_aucune_colonne_nominative_publiable` : ne jamais le contourner ni l'affaiblir.

### Qualité
- Un test dbt en échec bloque la publication. Ne jamais désactiver, passer en `warn` ou élargir
  un seuil pour faire passer un build : corriger la donnée ou le modèle, ou demander.
- Tout nouveau modèle : tests `unique` / `not_null` sur la clé + description dans le YAML du dossier.
- Tout nouvel indicateur publié : test de volumétrie ou de réconciliation dans `quality/`.

### Configuration et données
- Aucune liste de communes, seuil ou URL en dur : `config/observatoire.yml` (les `vars` de
  `dbt_project.yml` ne sont que des valeurs par défaut surchargées par la CLI).
- Ingestion idempotente et rejouable : respecter caches, incrémental BODACC et journal existants.
- Ne pas comparer ni présenter les chiffres comme ceux de l'INSEE (définitions différentes).
- Mois récents provisoires (`mois_provisoires_*`) : ne pas les interpréter comme des tendances.

### Documentation
- Nouveau choix technique ou méthodologique : entrée dans `docs/decisions.md`.
- Changement de définition d'indicateur : mettre à jour `docs/methodologie.md`.
- Changement de colonnes des marts : `uv run obs documenter`.

---

## Bonnes pratiques de code

### Python
- Typage des signatures publiques, fonctions courtes et pures quand possible.
- `ruff` (line-length 120) doit passer ; accents français assumés (RUF001-003 ignorés).
- Appels HTTP via les utilitaires de `socle_territorial` (retries tenacity) ; tests réseau mockés avec `respx`.
- Pas de nouvelle dépendance sans le signaler explicitement (et justifier dans `docs/decisions.md`).
- Nommage du domaine en français, cohérent avec l'existant (`ingerer`, `perimetre`, `commune`).

### SQL / dbt
- `ref()` / `source()` uniquement, jamais de nom de table en dur.
- CTE nommées et lisibles, une étape logique par CTE ; `select` explicite en marts (pas de `select *`).
- Respecter la couche : pas de logique métier en staging, pas de lecture de `raw` hors staging.
- Valider avec `dbt build --select <modèle>+` sur le périmètre de dev avant de conclure.

### Site
- Données lues depuis l'export agrégé uniquement ; réutiliser `components/graphiques.js` et `donnees.js`.
- Lisible sur mobile. Afficher les cases masquées (secret) comme telles, jamais comme zéro.

---

## Protocole anti-régression

Avant modification :
1. Comprendre le comportement actuel (lire le modèle / la fonction, ses tests, ses dépendants).
2. Identifier les effets de bord : modèles aval (`+`), export, pages du site.
3. Vérifier les cas limites : nulls, communes hors périmètre, codes postaux multi-communes, mois vides.

Après modification :
1. `ruff check` + tests ciblés (pytest et/ou `dbt build --select`).
2. Vérifier secret statistique et absence de colonne nominative si l'export change.
3. Signaler honnêtement ce qui n'a pas été vérifié (ex. : run complet non lancé, pas de clé TypeSafe).

## Checklist avant de rendre du code
- [ ] Chaque ligne modifiée se rattache à la demande
- [ ] Aucune valeur en dur (communes, seuils, URLs) hors `config/observatoire.yml`
- [ ] Tests ajoutés ou mis à jour, et verts
- [ ] Aucun test qualité affaibli ou désactivé
- [ ] Aucune donnée nominative, secret statistique respecté
- [ ] Docs (`decisions` / `methodologie` / `dictionnaire`) à jour si concerné
- [ ] Aucune dépendance ajoutée sans l'avoir signalé

---

**Ces règles fonctionnent si :** diffs plus courts, moins de réécritures pour sur-ingénierie,
questions posées avant l'implémentation plutôt qu'après l'erreur, aucun chiffre faux publié.
