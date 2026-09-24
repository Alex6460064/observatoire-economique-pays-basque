"""Complément récent au stock Sirene par l'API Sirene 3.11 (INSEE, clé du portail requise).

Choix (voir docs/decisions.md, ADR-0004) :
- **optionnel** : sans ``INSEE_API_KEY``, rien n'est appelé et le pipeline se comporte
  comme en V1 (stock mensuel seul) ;
- **fenêtre** : établissements du périmètre *traités* par l'INSEE depuis le dernier
  traitement présent dans le stock, et créés dans la fenêtre d'historique. Filtrer sur la
  seule date de création manquerait les enregistrements tardifs (établissement créé en
  juillet, enregistré en septembre) ;
- **même schéma que le stock** : les fichiers écrits ici sont fusionnés au stock en staging,
  la version API (plus récente) l'emporte ;
- **minimisation** : le paramètre ``champs`` limite la réponse aux colonnes utiles, aucun
  nom, prénom, dénomination ni adresse n'est demandé ;
- **quota** : une requête toutes les ``60 / sirene_api_requetes_minute`` secondes ; les 429
  sont réessayés par ``socle_territorial.http``.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import httpx
from socle_territorial import geo, http
from socle_territorial.journal import Journal
from socle_territorial.stockage import ecrire_parquet

from ingestion.config import Config

log = logging.getLogger(__name__)

TAILLE_PAGE = 1000  # maximum accepté par l'API
TAILLE_LOT = 100  # identifiants par requête `q=champ:(a OR b ...)`

# Mêmes colonnes et types que les extractions du stock (ingestion/sirene.py).
COLONNES_ETABLISSEMENT = {
    "siren": "VARCHAR",
    "nic": "VARCHAR",
    "siret": "VARCHAR",
    "statutDiffusionEtablissement": "VARCHAR",
    "dateCreationEtablissement": "DATE",
    "trancheEffectifsEtablissement": "VARCHAR",
    "anneeEffectifsEtablissement": "BIGINT",
    "etablissementSiege": "BOOLEAN",
    "codeCommuneEtablissement": "VARCHAR",
    "etatAdministratifEtablissement": "VARCHAR",
    "dateDebut": "DATE",
    "activitePrincipaleEtablissement": "VARCHAR",
    "nomenclatureActivitePrincipaleEtablissement": "VARCHAR",
    "activitePrincipaleNAF25Etablissement": "VARCHAR",
    "caractereEmployeurEtablissement": "VARCHAR",
    "nombrePeriodesEtablissement": "BIGINT",
    "dateDernierTraitementEtablissement": "TIMESTAMP",
}

COLONNES_UNITE_LEGALE = {
    "siren": "VARCHAR",
    "statutDiffusionUniteLegale": "VARCHAR",
    "unitePurgeeUniteLegale": "BOOLEAN",
    "dateCreationUniteLegale": "DATE",
    "categorieJuridiqueUniteLegale": "BIGINT",
    "activitePrincipaleUniteLegale": "VARCHAR",
    "nomenclatureActivitePrincipaleUniteLegale": "VARCHAR",
    "activitePrincipaleNAF25UniteLegale": "VARCHAR",
    "etatAdministratifUniteLegale": "VARCHAR",
    "dateDebut": "DATE",
    "nicSiegeUniteLegale": "VARCHAR",
    "categorieEntreprise": "VARCHAR",
    "trancheEffectifsUniteLegale": "VARCHAR",
    "caractereEmployeurUniteLegale": "VARCHAR",
    "economieSocialeSolidaireUniteLegale": "VARCHAR",
}

COLONNES_LIEN_SUCCESSION = {
    "siretEtablissementPredecesseur": "VARCHAR",
    "siretEtablissementSuccesseur": "VARCHAR",
    "dateLienSuccession": "DATE",
    "transfertSiege": "BOOLEAN",
    "continuiteEconomique": "BOOLEAN",
    "dateDernierTraitementLienSuccession": "TIMESTAMP",
}


class ClientSirene:
    def __init__(self, api: str, cle: str, requetes_minute: int) -> None:
        self.api = api
        self.entetes = {"X-INSEE-Api-Key-Integration": cle, "Accept": "application/json"}
        self.pause = 60 / requetes_minute

    def _get(self, chemin: str, params: dict[str, Any]) -> dict[str, Any] | None:
        time.sleep(self.pause)
        try:
            return http.get_json(f"{self.api}{chemin}", params, headers=self.entetes)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:  # l'API répond 404 quand rien ne correspond
                return None
            raise

    def paginer(self, chemin: str, liste: str, q: str, champs: str | None = None) -> Iterator[dict[str, Any]]:
        """Parcourt toutes les pages d'une recherche multicritères (pagination par curseur)."""
        curseur = "*"
        while True:
            params = {"q": q, "nombre": TAILLE_PAGE, "curseur": curseur}
            if champs:
                params["champs"] = champs
            page = self._get(chemin, params)
            if page is None:
                return
            yield from page[liste]
            suivant = page["header"].get("curseurSuivant")
            if not suivant or suivant == curseur:
                return
            curseur = suivant

    def par_lots(
        self, chemin: str, liste: str, champ: str, valeurs: list[str], champs: str | None = None
    ) -> Iterator[dict[str, Any]]:
        for i in range(0, len(valeurs), TAILLE_LOT):
            q = f"{champ}:({' OR '.join(valeurs[i : i + TAILLE_LOT])})"
            yield from self.paginer(chemin, liste, q, champs)


def _periode_courante(periodes: list[dict[str, Any]]) -> dict[str, Any]:
    return next((p for p in periodes if p.get("dateFin") is None), {})


def aplatir_etablissement(r: dict[str, Any]) -> dict[str, Any]:
    return {
        **{k: r.get(k) for k in COLONNES_ETABLISSEMENT},
        **_periode_courante(r.get("periodesEtablissement") or []),
        "codeCommuneEtablissement": (r.get("adresseEtablissement") or {}).get("codeCommuneEtablissement"),
    }


def aplatir_unite_legale(r: dict[str, Any]) -> dict[str, Any]:
    return {
        **{k: r.get(k) for k in COLONNES_UNITE_LEGALE},
        **_periode_courante(r.get("periodesUniteLegale") or []),
    }


def requete_etablissements(departements: set[str], depuis_traitement: date, debut_historique: date) -> str:
    communes = " OR ".join(f"codeCommuneEtablissement:{d}*" for d in geo.valider_departements(departements))
    return (
        f"({communes}) AND dateDernierTraitementEtablissement:[{depuis_traitement.isoformat()} TO *]"
        f" AND dateCreationEtablissement:[{debut_historique.isoformat()} TO *]"
    )


def dernier_traitement_stock(cfg: Config) -> date:
    stock = cfg.raw / "sirene" / "etablissements.parquet"
    if not stock.exists():
        raise SystemExit("stock Sirene absent : lancer d'abord `obs ingerer --source sirene`")
    with duckdb.connect() as con:
        (maxi,) = con.execute(
            "select max(dateDernierTraitementEtablissement) from read_parquet(?)", [stock.as_posix()]
        ).fetchone()
    return maxi.date()


def _complement_vide(dest: Path) -> None:
    """Fichiers vides au schéma du stock : les sources dbt restent lisibles, le stock seul compte."""
    shutil.rmtree(dest, ignore_errors=True)
    ecrire_parquet([], dest / "etablissements.parquet", COLONNES_ETABLISSEMENT)
    ecrire_parquet([], dest / "unites_legales.parquet", COLONNES_UNITE_LEGALE)
    ecrire_parquet([], dest / "liens_succession.parquet", COLONNES_LIEN_SUCCESSION)


def _indisponible(exc: httpx.HTTPError) -> bool:
    """Panne INSEE persistante après réessais (réseau, 5xx, quota). Les autres 4xx (clé
    refusée, requête invalide) sont une erreur de notre côté : elles doivent faire échouer le run."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


def _extraire(
    cfg: Config, journal: Journal, client: ClientSirene, departements: set[str], depuis: date, tmp: Path
) -> None:
    millesime = depuis.isoformat()
    with journal.extraction("sirene_api_etablissements", url=client.api, millesime=millesime) as e:
        q = requete_etablissements(departements, depuis, cfg.debut_historique)
        etabs = [
            aplatir_etablissement(r)
            for r in client.paginer("/siret", "etablissements", q, ",".join(COLONNES_ETABLISSEMENT))
        ]
        e.lignes = ecrire_parquet(etabs, tmp / "etablissements.parquet", COLONNES_ETABLISSEMENT)
        e.details = {"depuis_traitement": millesime}
    log.info("API Sirene : %s établissements traités depuis le %s", e.lignes, millesime)

    sirens = sorted({r["siren"] for r in etabs})
    with journal.extraction("sirene_api_unites_legales", url=client.api, millesime=millesime) as e:
        uls = client.par_lots("/siren", "unitesLegales", "siren", sirens, ",".join(COLONNES_UNITE_LEGALE))
        e.lignes = ecrire_parquet(
            (aplatir_unite_legale(r) for r in uls), tmp / "unites_legales.parquet", COLONNES_UNITE_LEGALE
        )
    log.info("API Sirene : %s unités légales", e.lignes)

    sirets = sorted({r["siret"] for r in etabs})
    with journal.extraction("sirene_api_liens_succession", url=client.api, millesime=millesime) as e:
        liens = client.par_lots(
            "/siret/liensSuccession",
            "liensSuccession",
            "siretEtablissementSuccesseur",
            sirets,
            ",".join(COLONNES_LIEN_SUCCESSION),
        )
        e.lignes = ecrire_parquet(liens, tmp / "liens_succession.parquet", COLONNES_LIEN_SUCCESSION)
    log.info("API Sirene : %s liens de succession", e.lignes)


def ingerer_sirene_api(cfg: Config, journal: Journal, departements: set[str]) -> None:
    dest = cfg.raw / "sirene_api"
    cle = os.environ.get("INSEE_API_KEY")
    if not cle:
        # Un complément d'un run précédent ne doit pas survivre à un stock plus récent.
        _complement_vide(dest)
        log.warning("INSEE_API_KEY absente : complément API Sirene ignoré (stock mensuel seul)")
        return

    client = ClientSirene(cfg.sources["sirene_api"], cle, cfg.p["sirene_api_requetes_minute"])
    depuis = dernier_traitement_stock(cfg)
    # Les trois fichiers vont ensemble : écrits dans un dossier temporaire, publiés d'un
    # bloc. Un échec en cours de route supprime aussi l'ancien complément, qui ne
    # correspondrait plus au stock.
    shutil.rmtree(dest, ignore_errors=True)
    tmp = dest.with_name("sirene_api.part")
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        _extraire(cfg, journal, client, departements, depuis, tmp)
    except httpx.HTTPError as exc:
        if not _indisponible(exc):
            raise
        # Repli sur le stock seul : chiffres exacts mais moins frais ; l'échec reste au journal.
        shutil.rmtree(tmp, ignore_errors=True)
        _complement_vide(dest)
        log.warning("API Sirene indisponible (%s) : stock mensuel seul pour ce run", exc)
        return
    tmp.rename(dest)
