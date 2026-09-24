"""Référentiels : communes du périmètre, communes des départements concernés, NAF rév. 2."""

from __future__ import annotations

import json
import logging

from python_calamine import CalamineWorkbook
from socle_territorial import geo, http
from socle_territorial.journal import Journal
from socle_territorial.stockage import ecrire_parquet

from ingestion.config import Config

log = logging.getLogger(__name__)


def ingerer_geo(cfg: Config, journal: Journal) -> set[str]:
    """Écrit les communes du périmètre et des départements concernés. Renvoie les départements."""
    dp = cfg.def_perimetre
    dest = cfg.raw / "geo"
    with journal.extraction("geo_communes", url=geo.GEO_API, millesime=cfg.aujourd_hui.isoformat()) as e:
        info_epci = geo.epci(dp["epci"])
        communes = geo.communes_epci(dp["epci"])
        if "communes" in dp:
            voulues = set(dp["communes"])
            absentes = voulues - {c["code_commune"] for c in communes}
            if absentes:
                raise ValueError(f"communes du sous-périmètre absentes de l'EPCI : {sorted(absentes)}")
            communes = [c for c in communes if c["code_commune"] in voulues]
        departements = sorted({c["code_departement"] for c in communes})
        n = ecrire_parquet(communes, dest / "communes_perimetre.parquet", geo.COLONNES_COMMUNE)
        dep_rows = [c for d in departements for c in geo.communes_departement(d)]
        ecrire_parquet(dep_rows, dest / "communes_departements.parquet", geo.COLONNES_COMMUNE)
        (dest / "perimetre.json").write_text(
            json.dumps(
                {
                    "code": cfg.perimetre,
                    "libelle": dp["libelle"],
                    "libelle_complement": dp["libelle_complement"],
                    "epci": info_epci,
                    "nb_communes": n,
                    "departements": departements,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        codes = {c["code_commune"] for c in communes}
        contours = geo.contours_epci(dp["epci"])
        contours["features"] = [f for f in contours["features"] if f["properties"]["code"] in codes]
        if len(contours["features"]) != n:
            raise ValueError(f"contours : {len(contours['features'])} communes pour {n} attendues")
        (dest / "contours.geojson").write_text(
            json.dumps(geo.simplifier(contours), separators=(",", ":")), encoding="utf-8"
        )
        e.lignes = n
        e.details = {"epci": dp["epci"], "departements": departements, "communes_departements": len(dep_rows)}
    log.info("géo : %s communes dans le périmètre %s", n, cfg.perimetre)
    return set(departements)


def _lire_liste_insee(path) -> list[tuple[str, str]]:
    """Listes NAF INSEE : 2 lignes de titre, puis en-tête ``Code | Libellé``."""
    lignes = CalamineWorkbook.from_path(str(path)).get_sheet_by_name("Feuil1").to_python()
    i = next(i for i, r in enumerate(lignes) if r and str(r[0]).strip() == "Code")
    return [(str(r[0]).strip(), str(r[1]).strip()) for r in lignes[i + 1 :] if r and str(r[0]).strip()]


def ingerer_naf(cfg: Config, journal: Journal) -> None:
    dest = cfg.raw / "naf"
    tmp = cfg.data_dir / "tmp"
    with journal.extraction("naf", url=cfg.sources["naf_niveaux"], millesime="NAF rév. 2 (2008)") as e:
        f5 = tmp / "naf2008_5_niveaux.xls"
        http.download(cfg.sources["naf_niveaux"], f5)
        lignes = CalamineWorkbook.from_path(str(f5)).get_sheet_by_name("naf2008_5_niveaux").to_python()
        if [str(h) for h in lignes[0][:5]] != ["NIV5", "NIV4", "NIV3", "NIV2", "NIV1"]:
            raise ValueError(f"en-tête NAF inattendu : {lignes[0]}")
        sous_classes = [
            {"code_naf": r[0], "code_groupe": r[2], "code_division": r[3], "code_section": r[4]}
            for r in lignes[1:]
            if r[0]
        ]
        n = ecrire_parquet(
            sous_classes,
            dest / "naf_niveaux.parquet",
            {"code_naf": "VARCHAR", "code_groupe": "VARCHAR", "code_division": "VARCHAR", "code_section": "VARCHAR"},
        )
        for niveau, url_cle in (("sections", "naf_sections"), ("divisions", "naf_divisions")):
            f = tmp / f"naf_{niveau}.xls"
            http.download(cfg.sources[url_cle], f)
            ecrire_parquet(
                [{"code": c, "libelle": lib} for c, lib in _lire_liste_insee(f)],
                dest / f"naf_{niveau}.parquet",
                {"code": "VARCHAR", "libelle": "VARCHAR"},
            )
        e.lignes = n
    log.info("NAF : %s sous-classes", n)
