"""Génère docs/dictionnaire.md depuis le manifeste dbt (descriptions) et l'entrepôt (types réels).

Le dictionnaire ne peut donc pas diverger du code : il est régénéré par ``obs documenter``.
"""

from __future__ import annotations

import json
from typing import Any

import duckdb

from ingestion.config import RACINE, Config

COUCHES = (
    ("staging", "Couche staging — sources renommées, typées, minimisées (vues)"),
    ("intermediate", "Couche intermédiaire — règles métier (tables)"),
    ("marts", "Couche marts — tables prêtes à l'analyse, source unique de l'export public"),
)

FICHIERS_PUBLIES = [
    ("indicateurs.csv", "Toutes les cases publiées, après secret statistique. Colonnes : `indicateur`, "
     "`type_periode` (mois | 12m), `periode` (AAAA-MM ; fin de fenêtre pour 12m), `geo` (code commune ou "
     "TOTAL), `niveau_secteur` (T tous | S section | D division | P type de procédure), `secteur`, `valeur` "
     "(vide si masquée), `secret` (p primaire | s secondaire), `provisoire` (0/1). Une case absente vaut 0."),
    ("communes.csv", "Communes du périmètre : code, nom, population, bassin BMO."),
    ("communes.geojson", "Contours simplifiés des communes (geo.api.gouv.fr)."),
    ("secteurs.csv", "Sections et divisions NAF rév. 2 (+ ZZ non déterminé, <section>_ND division non déterminée)."),
    ("mois.csv", "Mois publiés et statut par source (consolide | provisoire | non_couvert)."),
    ("bmo_familles.csv", "Projets BMO par bassin × année × famille de métiers."),
    ("bmo_metiers.csv", "Projets BMO par métier, dernier millésime."),
    ("bmo_recouvrement.json", "Recouvrement entre le périmètre et les bassins BMO."),
    ("meta.json", "Périmètre, période, sources avec millésime et date d'extraction."),
    ("qualite.json", "Fraîcheur, résultats des tests, métriques qualité, secret, évaluation Jev."),
    ("historique_*.csv", "Historique agrégé des runs (séries au total du périmètre, métriques qualité)."),
]  # fmt: skip


def _cellule(texte: str) -> str:
    """Texte sûr dans une cellule de tableau Markdown."""
    return " ".join(texte.split()).replace("|", "\\|")


def generer(cfg: Config) -> str:
    manifeste = json.loads((cfg.data_dir / "dbt" / "target" / "manifest.json").read_text(encoding="utf-8"))
    con = duckdb.connect(str(cfg.warehouse), read_only=True)
    try:
        types: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for schema, table, col, typ in con.execute(
            "select table_schema, table_name, column_name, data_type from information_schema.columns "
            "order by table_schema, table_name, ordinal_position"
        ).fetchall():
            types.setdefault((schema, table), []).append((col, typ))
    finally:
        con.close()

    modeles: dict[str, list[dict[str, Any]]] = {}
    for n in manifeste["nodes"].values():
        if n["resource_type"] == "model":
            modeles.setdefault(n["schema"], []).append(n)

    lignes = [
        "# Dictionnaire de données",
        "",
        "> Généré par `uv run obs documenter` depuis le manifeste dbt et l'entrepôt DuckDB. Ne pas modifier à la main.",
        "",
        "Chaîne : `raw` (Parquet, `obs ingerer`) → `staging` → `intermediate` → `marts` (dbt) → fichiers publiés "
        "(`obs exporter`, secret statistique).",
        "",
        "## Fichiers publiés (site/src/data)",
        "",
        "| Fichier | Contenu |",
        "|---|---|",
        *[f"| `{f}` | {_cellule(d)} |" for f, d in FICHIERS_PUBLIES],
        "",
    ]
    for schema, titre in COUCHES:
        lignes += [f"## {titre}", ""]
        for n in sorted(modeles.get(schema, []), key=lambda m: m["name"]):
            lignes += [f"### `{schema}.{n['name']}`", "", n.get("description") or "_(sans description)_", ""]
            desc = {c: v.get("description", "") for c, v in n.get("columns", {}).items()}
            cols = types.get((schema, n["name"]), [])
            if cols:
                lignes += ["| Colonne | Type | Description |", "|---|---|---|"]
                lignes += [f"| `{c}` | {t} | {_cellule(desc.get(c, ''))} |" for c, t in cols]
                lignes.append("")
    return "\n".join(lignes)


def documenter(cfg: Config) -> None:
    (RACINE / "docs" / "dictionnaire.md").write_text(generer(cfg), encoding="utf-8")
