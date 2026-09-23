"""Ingestion BMO : millésimes annuels + composition communale des bassins d'emploi.

La logique de lecture est dans ``socle_territorial.bmo`` (partagée avec la piste 1) ;
ce module ne fait qu'orchestrer téléchargement, cache et journalisation.
"""

from __future__ import annotations

import json
import logging
from pathlib import PurePosixPath
from urllib.parse import urlparse

from socle_territorial import bmo, http
from socle_territorial.journal import Journal
from socle_territorial.stockage import ecrire_parquet

from ingestion.config import Config

log = logging.getLogger(__name__)


def ingerer_bmo(cfg: Config, journal: Journal, departements: set[str], forcer: bool = False) -> None:
    dest = cfg.raw / "bmo"
    tmp = cfg.data_dir / "tmp" / "bmo"
    manifeste_path = dest / "_manifest.json"
    manifeste = json.loads(manifeste_path.read_text(encoding="utf-8")) if manifeste_path.exists() else {}

    for m in bmo.lister_millesimes(cfg.p["bmo_annee_min"]):
        cle = str(m["annee"])
        sortie = dest / f"bmo_{cle}.parquet"
        if not forcer and sortie.exists() and manifeste.get(cle, {}).get("url") == m["url"]:
            continue
        with journal.extraction("bmo", url=m["url"], millesime=cle) as e:
            suffixe = PurePosixPath(urlparse(m["url"]).path).suffix or ".xlsx"
            fichier = tmp / f"bmo_{cle}{suffixe}"
            e.sha256 = http.download(m["url"], fichier)
            lignes = bmo.lire_bmo(fichier, departements)
            annees = {r["annee"] for r in lignes}
            if annees != {m["annee"]}:
                raise ValueError(f"BMO {cle} : années trouvées dans le fichier {annees}")
            e.lignes = ecrire_parquet(lignes, sortie, bmo.COLONNES_BMO)
        manifeste[cle] = {"url": m["url"], "sha256": e.sha256, "lignes": e.lignes}
        manifeste_path.write_text(json.dumps(manifeste, indent=2), encoding="utf-8")
        log.info("BMO %s : %s lignes", cle, e.lignes)

    url = cfg.p["bmo_bassins_url"]
    sortie = dest / "bassins_communes.parquet"
    if forcer or not sortie.exists() or manifeste.get("bassins", {}).get("url") != url:
        with journal.extraction("bmo_bassins", url=url) as e:
            fichier = tmp / "bassins.xlsx"
            e.sha256 = http.download(url, fichier)
            lignes = bmo.lire_bassins(fichier)
            e.millesime = str(lignes[0]["millesime_zonage"]) if lignes else None
            e.lignes = ecrire_parquet(lignes, sortie, bmo.COLONNES_BASSINS)
        manifeste["bassins"] = {"url": url, "sha256": e.sha256, "lignes": e.lignes, "millesime": e.millesime}
        manifeste_path.write_text(json.dumps(manifeste, indent=2), encoding="utf-8")
        log.info("Bassins BMO : %s communes", e.lignes)
