"""Point d'entrée du pipeline : ``uv run obs <commande>``.

    obs ingerer   [--source geo,naf,sirene,bodacc,bmo] [--forcer]
    obs transformer            # dbt build (modèles + tests) + fraîcheur des sources
    obs enrichir               # secteur des annonces sans NAF via Jev (optionnel, TYPESAFE_API_KEY)
    obs evaluer-jev [--n 300]  # mesure la politique Jev sur des annonces au NAF connu
    obs exporter               # agrégats publiables (secret statistique) -> site/src/data
    obs documenter             # régénère docs/dictionnaire.md (manifeste dbt + types réels)
    obs run                    # tout, dans l'ordre ; s'arrête au premier échec

Code de sortie non nul au moindre échec : la CI ne publie alors pas le site.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys

from socle_territorial.journal import Journal

from ingestion.config import RACINE, Config

log = logging.getLogger("obs")

SOURCES = ("geo", "naf", "sirene", "bodacc", "bmo")


def ingerer(cfg: Config, sources: list[str], forcer: bool) -> None:
    from ingestion import bmo, bodacc, referentiels, sirene

    journal = Journal(cfg.journal_path)
    perimetre_json = cfg.raw / "geo" / "perimetre.json"
    if "geo" in sources:
        departements = referentiels.ingerer_geo(cfg, journal)
    elif perimetre_json.exists():
        departements = set(json.loads(perimetre_json.read_text(encoding="utf-8"))["departements"])
    else:
        raise SystemExit("référentiel géographique absent : lancer d'abord `obs ingerer --source geo`")
    if "naf" in sources:
        referentiels.ingerer_naf(cfg, journal)
    if "sirene" in sources:
        sirene.ingerer_sirene(cfg, journal, departements, forcer)
    if "bodacc" in sources:
        bodacc.ingerer_bodacc(cfg, journal, departements, forcer)
    if "bmo" in sources:
        bmo.ingerer_bmo(cfg, journal, departements, forcer)


def env_dbt(cfg: Config) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        OBS_DATA_DIR=cfg.data_dir.as_posix(),
        OBS_PERIMETRE=cfg.perimetre,
        DBT_TARGET_PATH=(cfg.data_dir / "dbt" / "target").as_posix(),
        DBT_LOG_PATH=(cfg.data_dir / "dbt" / "logs").as_posix(),
        DBT_SEND_ANONYMOUS_USAGE_STATS="false",
    )
    return env


def dbt(cfg: Config, *args: str) -> None:
    cfg.warehouse.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["dbt", *args, "--project-dir", str(RACINE), "--profiles-dir", str(RACINE)]
    log.info("%s", " ".join(cmd))
    r = subprocess.run(cmd, env=env_dbt(cfg), cwd=RACINE, check=False)
    if r.returncode != 0:
        raise SystemExit(f"dbt {args[0]} en échec (code {r.returncode}) : publication bloquée")


def transformer(cfg: Config) -> None:
    from ingestion import jev

    jev.assurer_cache(cfg)  # source dbt présente même sans enrichissement
    dbt(cfg, "build", "--vars", json.dumps(cfg.dbt_vars()))
    dbt(cfg, "source", "freshness")


def enrichir(cfg: Config) -> int:
    from ingestion import jev

    return jev.enrichir(cfg, Journal(cfg.journal_path))


def evaluer_jev(cfg: Config, n: int) -> None:
    from ingestion import jev

    resultat = jev.evaluer(cfg, n)
    jev.ecrire_rapport(resultat)
    (cfg.raw / "enrichissement" / "evaluation.json").write_text(
        json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    p = resultat["politique_retenue"]
    log.info(
        "évaluation Jev (%s annonces) : division forcée juste %.0f %% ; "
        "politique : %.0f %% attribuées, précision %.0f %%",
        resultat["echantillon"],
        100 * resultat["division_forcee_juste"],
        100 * (p["part_division"] + p["part_section"]),
        100 * (p["precision_globale_attribuees"] or 0),
    )


def exporter(cfg: Config) -> None:
    from ingestion import export

    export.exporter(cfg)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
    for bavard in ("httpx", "httpx2", "typesafe_sdk"):
        logging.getLogger(bavard).setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="obs", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--perimetre", help="périmètre défini dans config/observatoire.yml")
    sub = parser.add_subparsers(dest="commande", required=True)
    p_ing = sub.add_parser("ingerer")
    p_ing.add_argument("--source", default=",".join(SOURCES))
    p_ing.add_argument("--forcer", action="store_true", help="ignore les caches et relit tout")
    sub.add_parser("transformer")
    sub.add_parser("enrichir")
    p_eval = sub.add_parser("evaluer-jev")
    p_eval.add_argument("--n", type=int, default=300, help="taille de l'échantillon évalué")
    sub.add_parser("exporter")
    sub.add_parser("documenter")
    p_run = sub.add_parser("run")
    p_run.add_argument("--forcer", action="store_true")
    a = parser.parse_args(argv)

    cfg = Config.charger(a.perimetre)
    log.info("périmètre=%s données=%s historique depuis %s", cfg.perimetre, cfg.data_dir, cfg.debut_historique)
    if a.commande == "ingerer":
        sources = [s.strip() for s in a.source.split(",") if s.strip()]
        inconnues = set(sources) - set(SOURCES)
        if inconnues:
            parser.error(f"sources inconnues : {sorted(inconnues)}")
        ingerer(cfg, sources, a.forcer)
    elif a.commande == "transformer":
        transformer(cfg)
    elif a.commande == "enrichir":
        enrichir(cfg)
    elif a.commande == "evaluer-jev":
        evaluer_jev(cfg, a.n)
    elif a.commande == "exporter":
        exporter(cfg)
    elif a.commande == "documenter":
        from ingestion import dictionnaire

        dictionnaire.documenter(cfg)
    elif a.commande == "run":
        ingerer(cfg, list(SOURCES), a.forcer)
        transformer(cfg)
        # L'enrichissement a besoin des modèles (annonces sans NAF) ; s'il ajoute des
        # attributions, on reconstruit pour qu'elles entrent dans les indicateurs.
        if enrichir(cfg):
            transformer(cfg)
        exporter(cfg)


if __name__ == "__main__":
    sys.exit(main())
