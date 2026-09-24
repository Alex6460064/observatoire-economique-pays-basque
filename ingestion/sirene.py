"""Ingestion des fichiers stock Sirene (INSEE, data.gouv.fr, format Parquet).

Choix (voir docs/decisions.md, ADR-0003) :
- lecture **distante** des Parquet par DuckDB (requêtes HTTP Range) : seules les colonnes
  utiles sont transférées (~570 Mo au lieu de 2,9 Go), filtrées sur les départements du
  périmètre ;
- **minimisation** : aucune colonne nominative ou d'adresse n'est extraite (ni nom, ni
  prénom, ni dénomination, ni voie). Le code commune suffit aux agrégats ;
- un stock déjà extrait n'est pas relu (clé = URL de la ressource, qui change à chaque
  publication mensuelle).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

import duckdb
from socle_territorial import geo, http
from socle_territorial.journal import Journal

from ingestion.config import Config

log = logging.getLogger(__name__)

COLONNES_ETABLISSEMENT = [
    "siren", "nic", "siret", "statutDiffusionEtablissement", "dateCreationEtablissement",
    "trancheEffectifsEtablissement", "anneeEffectifsEtablissement", "etablissementSiege",
    "codeCommuneEtablissement", "etatAdministratifEtablissement", "dateDebut",
    "activitePrincipaleEtablissement", "nomenclatureActivitePrincipaleEtablissement",
    "activitePrincipaleNAF25Etablissement", "caractereEmployeurEtablissement",
    "nombrePeriodesEtablissement", "dateDernierTraitementEtablissement",
]  # fmt: skip

COLONNES_UNITE_LEGALE = [
    "siren", "statutDiffusionUniteLegale", "unitePurgeeUniteLegale", "dateCreationUniteLegale",
    "categorieJuridiqueUniteLegale", "activitePrincipaleUniteLegale",
    "nomenclatureActivitePrincipaleUniteLegale", "activitePrincipaleNAF25UniteLegale",
    "etatAdministratifUniteLegale", "dateDebut", "nicSiegeUniteLegale", "categorieEntreprise",
    "trancheEffectifsUniteLegale", "caractereEmployeurUniteLegale", "economieSocialeSolidaireUniteLegale",
]  # fmt: skip


def trouver_stocks(dataset: str) -> dict[str, dict[str, str]]:
    """Repère les ressources Parquet « StockEtablissement » et « StockUniteLegale » courantes."""
    ds = http.get_json(f"https://www.data.gouv.fr/api/1/datasets/{dataset}/")
    motifs = {
        "etablissements": re.compile(r"^Sirene : Fichier StockEtablissement - .*\(format parquet\)$"),
        "unites_legales": re.compile(r"^Sirene : Fichier StockUniteLegale - .*\(format parquet\)$"),
        "liens_succession": re.compile(r"^Sirene : Fichier StockEtablissementLiensSuccession - .*\(format parquet\)$"),
    }
    out: dict[str, dict[str, str]] = {}
    for cle, motif in motifs.items():
        res = [r for r in ds["resources"] if motif.match(r["title"])]
        if len(res) != 1:
            raise ValueError(f"ressource Sirene {cle} : {len(res)} candidates (titres modifiés ?)")
        r = res[0]
        out[cle] = {"url": r["url"], "titre": r["title"], "millesime": r["last_modified"][:10]}
    return out


def _copier(con: duckdb.DuckDBPyConnection, requete: str, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".parquet.part")
    try:
        con.execute(f"copy ({requete}) to '{tmp.as_posix()}' (format parquet, compression zstd)")
        n = con.execute(f"select count(*) from read_parquet('{tmp.as_posix()}')").fetchone()[0]
        if n == 0:
            raise ValueError(f"extraction vide pour {dest.name} : filtre ou source anormale")
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)
    return n


def ingerer_sirene(cfg: Config, journal: Journal, departements: set[str], forcer: bool = False) -> None:
    dest = cfg.raw / "sirene"
    version_path = dest / "_version.json"
    stocks = trouver_stocks(cfg.sources["sirene_dataset"])
    deja = json.loads(version_path.read_text(encoding="utf-8")) if version_path.exists() else {}
    fichiers_ok = all((dest / f"{k}.parquet").exists() for k in stocks)
    meme_version = all(deja.get(k, {}).get("url") == v["url"] for k, v in stocks.items())
    deps = geo.valider_departements(departements)
    if meme_version and fichiers_ok and deja.get("departements") == deps and not forcer:
        with journal.extraction("sirene", millesime=stocks["etablissements"]["millesime"]) as e:
            e.details = {"inchange": True}
        log.info("Sirene : stock %s déjà extrait", stocks["etablissements"]["millesime"])
        return

    con = duckdb.connect()
    con.execute("install httpfs; load httpfs; set enable_progress_bar = false;")
    try:
        s = stocks["etablissements"]
        with journal.extraction("sirene_etablissements", url=s["url"], millesime=s["millesime"]) as e:
            cols = ", ".join(COLONNES_ETABLISSEMENT)
            filtre = " or ".join(f"starts_with(codeCommuneEtablissement, '{d}')" for d in deps)
            e.lignes = _copier(
                con, f"select {cols} from read_parquet('{s['url']}') where {filtre}", dest / "etablissements.parquet"
            )
            e.details = {"departements": deps}
        log.info("Sirene : %s établissements extraits", e.lignes)

        u = stocks["unites_legales"]
        with journal.extraction("sirene_unites_legales", url=u["url"], millesime=u["millesime"]) as e:
            cols = ", ".join(COLONNES_UNITE_LEGALE)
            etab = (dest / "etablissements.parquet").as_posix()
            e.lignes = _copier(
                con,
                f"select {cols} from read_parquet('{u['url']}') where siren in (select distinct siren from '{etab}')",
                dest / "unites_legales.parquet",
            )
        log.info("Sirene : %s unités légales extraites", e.lignes)

        li = stocks["liens_succession"]
        with journal.extraction("sirene_liens_succession", url=li["url"], millesime=li["millesime"]) as e:
            etab = (dest / "etablissements.parquet").as_posix()
            e.lignes = _copier(
                con,
                f"select * from read_parquet('{li['url']}') "
                f"where siretEtablissementSuccesseur in (select siret from '{etab}')",
                dest / "liens_succession.parquet",
            )
        log.info("Sirene : %s liens de succession extraits", e.lignes)
    finally:
        con.close()

    version_path.write_text(
        json.dumps({**stocks, "departements": deps, "extrait_le": date.today().isoformat()}, indent=2),
        encoding="utf-8",
    )
