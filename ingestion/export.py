"""Export des données publiques du site (``site/src/data``) depuis l'entrepôt DuckDB.

C'est la seule porte de sortie vers le public. Elle :
1. ne lit que la couche ``marts`` (aucun identifiant d'entreprise) ;
2. applique le secret statistique à chaque indicateur et **vérifie** le résultat ;
3. écrit les métadonnées de fraîcheur et de qualité affichées sur le site ;
4. ajoute un instantané à l'historique (séries agrégées et métriques qualité, sans
   donnée sensible) pour suivre les révisions et la qualité dans la durée.

Toute anomalie lève une exception : la CI ne publie pas.
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb
from socle_territorial.journal import Journal

from ingestion.config import RACINE, Config
from ingestion.cubes import TOTAL, Cube, Evenement, construire_cube, secretiser

log = logging.getLogger(__name__)

INDICATEURS = {
    "creations_etablissements": {"source": "sirene", "libelle": "Créations d'établissements"},
    "creations_entreprises": {"source": "sirene", "libelle": "Créations d'entreprises (nouvelles unités légales)"},
    "immatriculations_rcs": {"source": "bodacc", "libelle": "Immatriculations au RCS"},
    "radiations_rcs": {"source": "bodacc", "libelle": "Radiations du RCS"},
    "cessions": {"source": "bodacc", "libelle": "Ventes et cessions de fonds"},
    "defaillances": {"source": "bodacc", "libelle": "Ouvertures de procédures collectives"},
}
TYPES_PROCEDURE = ["liquidation", "redressement", "sauvegarde", "autre"]


def _ecrire_csv(path: Path, lignes: list[dict[str, Any]], colonnes: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


def _requete(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def cellules_publiques(indicateur: str, cube: Cube, provisoires: set[str]) -> list[dict[str, Any]]:
    """Cases à publier ; les zéros non masqués sont omis (le site les lit comme 0)."""
    out = []
    for (tp, p, g, niv, s), v in cube.valeurs.items():
        motif = cube.masque.get((tp, p, g, niv, s))
        if v == 0 and motif is None:
            continue
        out.append(
            {
                "indicateur": indicateur,
                "type_periode": tp,
                "periode": p,
                "geo": g,
                "niveau_secteur": niv,
                "secteur": s,
                "valeur": "" if motif else v,
                "secret": {"primaire": "p", "secondaire": "s"}.get(motif, ""),
                "provisoire": int(tp == "mois" and p in provisoires),
            }
        )
    return sorted(out, key=lambda r: (r["type_periode"], r["periode"], r["geo"], r["niveau_secteur"], r["secteur"]))


def exporter(cfg: Config) -> None:
    dest = cfg.export_dir
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    seuil = cfg.p["seuil_secret"]
    con = duckdb.connect(str(cfg.warehouse), read_only=True)
    try:
        communes = _requete(con, "select * from marts.dim_communes order by code_commune")
        secteurs = _requete(con, "select * from marts.dim_secteurs order by code_section, code_division")
        mois = _requete(con, "select * from marts.dim_mois order by mois")
        codes_communes = [c["code_commune"] for c in communes]
        sections = sorted({s["code_section"] for s in secteurs})
        div_par_section: dict[str, list[str]] = defaultdict(list)
        for s in secteurs:
            div_par_section[s["code_section"]].append(s["code_division"])

        toutes_cellules: list[dict[str, Any]] = []
        stats_secret = {}
        for ind, info in INDICATEURS.items():
            statut = f"statut_{info['source']}"
            publies = [m["mois"] for m in mois if m[statut] != "non_couvert"]
            consolides = [m["mois"] for m in mois if m[statut] == "consolide"]
            provisoires = {m["periode"] for m in mois if m[statut] == "provisoire"}
            ev = [
                Evenement(**r)
                for r in _requete(
                    con,
                    """select mois, code_commune, code_section, code_division, detail, valeur
                        from marts.fct_evenements_mensuels where indicateur = ?""",
                    [ind],
                )
            ]
            cube = construire_cube(
                ev, publies, consolides, codes_communes, sections, div_par_section,
                TYPES_PROCEDURE if ind == "defaillances" else None,
            )  # fmt: skip
            total_attendu = sum(e.valeur for e in ev)
            total_cube = sum(
                v for (tp, _, g, niv, _), v in cube.valeurs.items() if tp == "mois" and g == TOTAL and niv == "T"
            )
            if total_attendu != total_cube:
                raise AssertionError(f"{ind} : total cube {total_cube} != faits {total_attendu}")
            secretiser(cube, seuil)
            cellules = cellules_publiques(ind, cube, provisoires)
            toutes_cellules += cellules
            stats_secret[ind] = {
                "cases": len(cube.valeurs),
                "masquees_primaire": sum(1 for m in cube.masque.values() if m == "primaire"),
                "masquees_secondaire": sum(1 for m in cube.masque.values() if m == "secondaire"),
            }
            log.info("export %s : %s cases, %s masquées", ind, len(cube.valeurs), len(cube.masque))

        # Garde-fou final, indépendant du module de secret : aucune valeur publiée entre 1 et seuil-1.
        fuites = [c for c in toutes_cellules if c["valeur"] != "" and 0 < int(c["valeur"]) < seuil]
        if fuites:
            raise AssertionError(f"{len(fuites)} cases sous le seuil publiées, ex. {fuites[0]}")

        _ecrire_csv(
            dest / "indicateurs.csv",
            toutes_cellules,
            [
                "indicateur",
                "type_periode",
                "periode",
                "geo",
                "niveau_secteur",
                "secteur",
                "valeur",
                "secret",
                "provisoire",
            ],
        )
        _ecrire_csv(dest / "communes.csv", communes,
                    ["code_commune", "nom_commune", "population", "code_bassin_bmo", "libelle_bassin_bmo"])  # fmt: skip
        _ecrire_csv(dest / "secteurs.csv", secteurs,
                    ["code_section", "libelle_section", "code_division", "libelle_division"])  # fmt: skip
        _ecrire_csv(dest / "mois.csv", mois, ["periode", "statut_sirene", "statut_bodacc"])

        # BMO : déjà agrégé et secrétisé par France Travail.
        bmo_fam = _requete(con, "select * from marts.mart_bmo_familles order by annee, code_bassin, code_famille")
        _ecrire_csv(dest / "bmo_familles.csv", bmo_fam, list(bmo_fam[0].keys()) if bmo_fam else [])
        bmo_met = _requete(
            con,
            "select * exclude (projets_secret) from marts.mart_bmo_metiers "
            "where annee = (select max(annee) from marts.mart_bmo_metiers) order by projets desc nulls last",
        )
        _ecrire_csv(dest / "bmo_metiers.csv", bmo_met, list(bmo_met[0].keys()) if bmo_met else [])
        recouvrement = _requete(con, "select * from marts.mart_bmo_recouvrement order by code_bassin")
        for r in recouvrement:  # liste lisible seulement si courte
            if r["nb_communes_bassin_hors_perimetre"] > 20:
                r["communes_hors_perimetre"] = None
        _json(dest / "bmo_recouvrement.json", recouvrement)

        qualite_metriques = _requete(con, "select * from marts.mart_qualite_indicateurs order by source, metrique")
        derniere_parution = con.execute("select max(date_parution) from staging.stg_bodacc__annonces").fetchone()[0]
    finally:
        con.close()

    meta = construire_meta(cfg, mois, derniere_parution)
    _json(dest / "meta.json", meta)
    qualite = construire_qualite(cfg, qualite_metriques, stats_secret, seuil)
    _json(dest / "qualite.json", qualite)
    historiser(cfg, toutes_cellules, qualite_metriques, dest)
    publier_methodologie(dest.parent / "methodologie.md")
    shutil.copy(cfg.raw / "geo" / "contours.geojson", dest / "communes.geojson")
    log.info("export terminé : %s cases publiées dans %s", len(toutes_cellules), dest)


def construire_meta(cfg: Config, mois: list[dict[str, Any]], derniere_parution: date | None) -> dict[str, Any]:
    raw = cfg.raw
    perimetre = json.loads((raw / "geo" / "perimetre.json").read_text(encoding="utf-8"))
    sirene = json.loads((raw / "sirene" / "_version.json").read_text(encoding="utf-8"))
    bmo = json.loads((raw / "bmo" / "_manifest.json").read_text(encoding="utf-8"))
    journal = Journal(cfg.journal_path)
    dernier_bodacc = journal.derniere_reussie("bodacc")
    return {
        "genere_le": datetime.now(UTC).isoformat(timespec="seconds"),
        "date_reference": cfg.aujourd_hui.isoformat(),
        "seuil_secret": cfg.p["seuil_secret"],
        "perimetre": perimetre,
        "periode": {"debut": mois[0]["periode"], "fin": mois[-1]["periode"]},
        "indicateurs": INDICATEURS,
        "sources": {
            "sirene": {
                "nom": "Base Sirene des entreprises et de leurs établissements (INSEE)",
                "millesime": f"stock du {sirene['etablissements']['millesime']}",
                "extrait_le": sirene["extrait_le"],
                "licence": "Licence Ouverte / Etalab 2.0",
                "url": "https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/",
            },
            "bodacc": {
                "nom": "BODACC – annonces commerciales (DILA)",
                "millesime": f"parutions jusqu'au {derniere_parution}",
                "extrait_le": dernier_bodacc["fin"][:10] if dernier_bodacc else None,
                "licence": "Licence Ouverte / Etalab 2.0",
                "url": "https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/",
            },
            "bmo": {
                "nom": "Enquête Besoins en Main-d'Œuvre (France Travail)",
                "millesime": ", ".join(sorted(k for k in bmo if k.isdigit())),
                "extrait_le": _date_fichier(raw / "bmo" / "_manifest.json"),
                "licence": "Licence Ouverte (fr-lo)",
                "url": "https://www.data.gouv.fr/fr/datasets/enquete-besoins-en-main-doeuvre-bmo/",
            },
            "geo": {
                "nom": "API Découpage administratif (geo.api.gouv.fr)",
                "millesime": "COG en vigueur",
                "extrait_le": _date_fichier(raw / "geo" / "perimetre.json"),
                "licence": "Licence Ouverte / Etalab 2.0",
                "url": "https://geo.api.gouv.fr/decoupage-administratif",
            },
            "naf": {
                "nom": "Nomenclature d'activités française NAF rév. 2 (INSEE)",
                "millesime": "2008",
                "extrait_le": _date_fichier(raw / "naf" / "naf_niveaux.parquet"),
                "licence": "Licence Ouverte / Etalab 2.0",
                "url": "https://www.insee.fr/fr/information/2120875",
            },
        },
    }


def _date_fichier(p: Path) -> str | None:
    return date.fromtimestamp(p.stat().st_mtime).isoformat() if p.exists() else None


def construire_qualite(
    cfg: Config, metriques: list[dict[str, Any]], stats_secret: dict[str, Any], seuil: int
) -> dict[str, Any]:
    journal = Journal(cfg.journal_path).lire()
    fraicheur = {}
    for e in journal:
        f = fraicheur.setdefault(e["source"], {"source": e["source"]})
        if e["statut"] == "ok":
            f.update(derniere_reussite=e["fin"], millesime=e["millesime"], lignes=e["lignes"])
        else:
            f.update(dernier_echec=e["fin"], erreur=(e.get("erreur") or "")[:200])
    target = cfg.data_dir / "dbt" / "target"
    tests = _resultats_dbt(target / "run_results.json")
    fraicheur_dbt = _fraicheur_dbt(target / "sources.json")
    evaluation_path = RACINE / "docs" / "evaluation_jev.json"
    jev = None
    if evaluation_path.exists():
        ev = json.loads(evaluation_path.read_text(encoding="utf-8"))
        jev = {k: ev[k] for k in ("echantillon", "modeles", "version_question", "politique_retenue", "calibration",
                                  "division_forcee_juste", "evalue_le")}  # fmt: skip
    return {
        "genere_le": datetime.now(UTC).isoformat(timespec="seconds"),
        "evaluation_jev": jev,
        "fraicheur_extractions": sorted(fraicheur.values(), key=lambda x: x["source"]),
        "fraicheur_sources": fraicheur_dbt,
        "tests": tests,
        "metriques": metriques,
        "secret": {"seuil": seuil, "par_indicateur": stats_secret},
        "journal_recent": [
            {k: e.get(k) for k in ("source", "millesime", "statut", "lignes", "fin", "duree_s")} for e in journal[-60:]
        ],
    }


def _resultats_dbt(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"disponible": False}
    rr = json.loads(path.read_text(encoding="utf-8"))
    res = [r for r in rr["results"] if r["unique_id"].startswith("test.")]
    compte: dict[str, int] = defaultdict(int)
    for r in res:
        compte[r["status"]] += 1
    return {
        "disponible": True,
        "execute_le": rr["metadata"]["generated_at"],
        "compte": dict(compte),
        "non_ok": [
            {"test": r["unique_id"].split(".")[2], "statut": r["status"], "lignes": r.get("failures")}
            for r in res
            if r["status"] != "pass"
        ],
    }


def _fraicheur_dbt(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    return [
        {
            "source": r["unique_id"].split(".", 2)[2],
            "statut": r["status"],
            "donnee_la_plus_recente": r.get("max_loaded_at"),
            "age_jours": round(r["max_loaded_at_time_ago_in_s"] / 86400, 1)
            if r.get("max_loaded_at_time_ago_in_s")
            else None,
        }
        for r in d["results"]
    ]


def historiser(cfg: Config, cellules: list[dict[str, Any]], metriques: list[dict[str, Any]], dest: Path) -> None:
    """Ajoute un instantané daté à l'historique et en copie une version pour le site.

    Seules des séries au total du périmètre (déjà passées au secret) et des métriques
    qualité sont historisées : ces fichiers peuvent être versionnés publiquement.
    """
    hist = Path(cfg.historique_dir)
    jour = cfg.aujourd_hui.isoformat()
    series = [
        {"date_run": jour, **{k: c[k] for k in ("indicateur", "periode", "valeur", "provisoire")}}
        for c in cellules
        if c["type_periode"] == "mois" and c["geo"] == TOTAL and c["niveau_secteur"] == "T"
    ]
    qual = [{"date_run": jour, "metrique": m["metrique"], "valeur": m["valeur"]} for m in metriques]
    for nom, lignes, cols in (
        ("series_total.csv", series, ["date_run", "indicateur", "periode", "valeur", "provisoire"]),
        ("qualite.csv", qual, ["date_run", "metrique", "valeur"]),
    ):
        fichier = hist / nom
        existantes = []
        if fichier.exists():
            with fichier.open(encoding="utf-8", newline="") as f:
                existantes = [r for r in csv.DictReader(f) if r["date_run"] != jour]  # run rejoué : on remplace
        _ecrire_csv(fichier, existantes + lignes, cols)
        shutil.copy(fichier, dest / f"historique_{nom}")


def publier_methodologie(page: Path) -> None:
    """La page du site est générée depuis docs/methodologie.md : une seule version des définitions."""
    source = RACINE / "docs" / "methodologie.md"
    corps = source.read_text(encoding="utf-8")
    entete = "---\ntitle: Méthodologie\n---\n\n<!-- Généré depuis docs/methodologie.md : ne pas modifier ici. -->\n\n"
    page.write_text(entete + corps, encoding="utf-8")
