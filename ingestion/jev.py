"""Attribution sectorielle des annonces BODACC sans code NAF, avec Jev (TypeSafe).

Problème : ~7 % des événements BODACC du périmètre n'ont pas de secteur, faute de SIREN
retrouvé dans Sirene ou de code NAF rév. 2 sur l'unité légale. L'annonce contient pourtant
une description libre de l'activité (« livraison de repas à domicile à vélo »).

Recette (cookbook TypeSafe « Classification using confidence ») :
- **une** question ``Choice`` par annonce, dont les options sont les 88 divisions NAF
  (+ une option « non identifiable ») ;
- si la confiance du choix dépasse ``seuil_division``, on retient la division ;
- sinon on remonte la hiérarchie NAF **dans le code** : les probabilités des divisions
  sont sommées par section ; si la section la plus probable dépasse ``seuil_section``,
  on retient la section seule ; sinon l'annonce reste « non déterminée ».
Les seuils sont fixés par ``obs evaluer-jev`` sur des annonces dont le vrai code NAF est
connu par Sirene (vérité terrain), pas au jugé.

Garanties :
- **optionnel** : sans ``TYPESAFE_API_KEY``, le pipeline tourne et publie à l'identique
  (les annonces restent « non déterminées ») ;
- **minimisation** : seul le texte d'activité est envoyé, jamais de nom, SIREN ni adresse ;
- **reproductible** : modèle figé (``jev-1.13.0``), cache par annonce et version de question ;
- **traçable** : chaque attribution garde modèle, confiance et niveau ; la part des
  événements classés par Jev est publiée sur la page qualité.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from socle_territorial.journal import Journal
from socle_territorial.stockage import ecrire_parquet

from ingestion.config import RACINE, Config

log = logging.getLogger(__name__)

VERSION_QUESTION = "naf-division-v1"
AUCUNE = "ZZ"
INSTRUCTIONS = (
    "Le texte est la description de l'activité d'une entreprise, telle que publiée dans une "
    "annonce légale française (BODACC). Dans quelle division de la nomenclature d'activités "
    "française (NAF rév. 2) cette activité s'exerce-t-elle principalement ? Jugez l'activité "
    "réellement exercée, pas le statut juridique ni le mode de détention."
)
LIBELLE_AUCUNE = (
    "Aucune activité économique identifiable : texte générique, vide de sens ou décrivant "
    "seulement une forme juridique (holding sans précision, « toutes activités », etc.)"
)

COLONNES_CACHE = {
    "id_annonce": "VARCHAR",
    "empreinte": "VARCHAR",
    "modele": "VARCHAR",
    "division_proposee": "VARCHAR",
    "confiance": "DOUBLE",
    "section_proposee": "VARCHAR",
    "masse_section": "DOUBLE",
    "niveau": "VARCHAR",
    "code_division": "VARCHAR",
    "code_section": "VARCHAR",
    "classe_le": "VARCHAR",
}


@dataclass(frozen=True)
class Nomenclature:
    libelles: dict[str, str]
    """Code division -> libellé présenté au modèle."""
    section_de: dict[str, str]
    """Code division -> code section."""


@dataclass(frozen=True)
class Reponse:
    division: str
    confiance: float
    probabilites: dict[str, float]
    modele: str


@dataclass(frozen=True)
class Decision:
    niveau: str  # "division" | "section" | "aucun"
    code_division: str | None
    code_section: str | None
    section_proposee: str | None
    masse_section: float


def charger_nomenclature(cfg: Config) -> Nomenclature:
    raw = (cfg.raw / "naf").as_posix()
    lignes = duckdb.sql(
        f"""
        select distinct n.code_division, d.libelle as lib_div, n.code_section, s.libelle as lib_sec
        from read_parquet('{raw}/naf_niveaux.parquet') n
        join read_parquet('{raw}/naf_divisions.parquet') d on d.code = n.code_division
        join read_parquet('{raw}/naf_sections.parquet') s on s.code = n.code_section
        order by 1
        """
    ).fetchall()
    return Nomenclature(
        libelles={div: f"{lib_div} (section {sec} : {lib_sec})" for div, lib_div, sec, lib_sec in lignes},
        section_de={div: sec for div, _, sec, _ in lignes},
    )


def criteres(nomenclature: Nomenclature) -> dict[str, str]:
    return {**nomenclature.libelles, AUCUNE: LIBELLE_AUCUNE}


def decider(r: Reponse, nomenclature: Nomenclature, seuil_division: float, seuil_section: float) -> Decision:
    """Politique hiérarchique : division si sûr, section si la masse de la section suffit, sinon rien."""
    masses: dict[str, float] = defaultdict(float)
    for div, p in r.probabilites.items():
        if div in nomenclature.section_de:
            masses[nomenclature.section_de[div]] += p
    section, masse = max(masses.items(), key=lambda kv: kv[1]) if masses else (None, 0.0)
    if r.division == AUCUNE:
        return Decision("aucun", None, None, section, masse)
    if r.confiance >= seuil_division:
        return Decision("division", r.division, nomenclature.section_de[r.division], section, masse)
    if section is not None and masse >= seuil_section:
        return Decision("section", None, section, section, masse)
    return Decision("aucun", None, None, section, masse)


def empreinte(texte: str, modele: str) -> str:
    return hashlib.sha256(f"{VERSION_QUESTION}|{modele}|{texte}".encode()).hexdigest()[:16]


async def _classer_async(
    textes: dict[str, str], nomenclature: Nomenclature, modele: str, concurrence: int
) -> dict[str, Reponse]:
    from typesafe_sdk import AsyncTypeSafeClient, Choice

    question = Choice(instructions=INSTRUCTIONS, criteria=criteres(nomenclature))
    sem = asyncio.Semaphore(concurrence)
    out: dict[str, Reponse] = {}

    async with AsyncTypeSafeClient(model=modele, timeout=60.0) as client:

        async def un(cle: str, texte: str) -> None:
            async with sem:
                res = await client.system_one(state={"activite": texte}, questions={"division": question})
            a = res.answers["division"]
            out[cle] = Reponse(a.choice, float(a.confidence), dict(a.probabilities), res.model)

        await asyncio.gather(*(un(k, t) for k, t in textes.items()))
    return out


def classer(
    textes: dict[str, str], nomenclature: Nomenclature, modele: str, concurrence: int = 32
) -> dict[str, Reponse]:
    """Classe chaque texte (clé -> texte). Point d'injection unique pour les tests."""
    if not textes:
        return {}
    return asyncio.run(_classer_async(textes, nomenclature, modele, concurrence))


def chemin_cache(cfg: Config) -> Path:
    return cfg.raw / "enrichissement" / "secteurs_jev.parquet"


def assurer_cache(cfg: Config) -> None:
    """Le modèle dbt lit ce fichier : il doit exister, même vide (pipeline sans clé)."""
    if not chemin_cache(cfg).exists():
        ecrire_parquet([], chemin_cache(cfg), COLONNES_CACHE)


def _lire_cache(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cur = duckdb.sql(f"select * from read_parquet('{path.as_posix()}')")
    cols = cur.columns
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def enrichir(cfg: Config, journal: Journal, classeur=classer) -> int:
    """Classe les nouveaux événements sans secteur. Renvoie le nombre d'annonces ajoutées au cache."""
    assurer_cache(cfg)
    pj = cfg.brut["jev"]
    if not os.environ.get("TYPESAFE_API_KEY") and classeur is classer:
        log.warning("TYPESAFE_API_KEY absente : attribution sectorielle par Jev ignorée")
        return 0
    cache = _lire_cache(chemin_cache(cfg))
    connues = {(c["id_annonce"], c["empreinte"]) for c in cache}
    con = duckdb.connect(str(cfg.warehouse), read_only=True)
    try:
        candidats = con.execute(
            """
            select e.id_annonce, e.activite
            from intermediate.int_bodacc__evenements_localises e
            join marts.dim_communes c using (code_commune)
            where e.code_naf_sirene is null and e.activite is not null
              and e.evenement in ('immatriculation', 'radiation', 'cession', 'ouverture_procedure')
            """
        ).fetchall()
    finally:
        con.close()
    a_classer = {i: t for i, t in candidats if (i, empreinte(t, pj["modele"])) not in connues}
    log.info("Jev : %s candidats, %s à classer", len(candidats), len(a_classer))
    if not a_classer:
        return 0
    nomenclature = charger_nomenclature(cfg)
    with journal.extraction("jev_secteurs", millesime=f"{pj['modele']}/{VERSION_QUESTION}") as e:
        reponses = classeur(a_classer, nomenclature, pj["modele"], pj["concurrence"])
        maintenant = datetime.now(UTC).isoformat(timespec="seconds")
        nouveaux = []
        for id_annonce, rep in reponses.items():
            d = decider(rep, nomenclature, pj["seuil_division"], pj["seuil_section"])
            nouveaux.append(
                {
                    "id_annonce": id_annonce,
                    "empreinte": empreinte(a_classer[id_annonce], pj["modele"]),
                    "modele": rep.modele,
                    "division_proposee": rep.division,
                    "confiance": rep.confiance,
                    "section_proposee": d.section_proposee,
                    "masse_section": d.masse_section,
                    "niveau": d.niveau,
                    "code_division": d.code_division,
                    "code_section": d.code_section,
                    "classe_le": maintenant,
                }
            )
        garder = [c for c in cache if c["id_annonce"] not in reponses]
        ecrire_parquet(garder + nouveaux, chemin_cache(cfg), COLONNES_CACHE)
        e.lignes = len(nouveaux)
        e.details = {n: sum(1 for x in nouveaux if x["niveau"] == n) for n in ("division", "section", "aucun")}
    log.info("Jev : %s annonces classées %s", len(nouveaux), e.details)
    return len(nouveaux)


# --------------------------------------------------------------------------- évaluation


def evaluer(cfg: Config, n: int, graine: int = 42, classeur=classer) -> dict[str, Any]:
    """Mesure la politique sur des annonces dont le code NAF est connu par Sirene.

    Échantillon aléatoire reproductible d'événements publiés du périmètre, avec activité
    et code NAF Sirene. Le texte est classé comme s'il n'avait pas de NAF ; on compare.
    """
    pj = cfg.brut["jev"]
    nomenclature = charger_nomenclature(cfg)
    con = duckdb.connect(str(cfg.warehouse), read_only=True)
    try:
        lignes = con.execute(
            f"""
            select e.id_annonce, e.activite, s.code_division, s.code_section
            from intermediate.int_bodacc__evenements_localises e
            join marts.dim_communes c using (code_commune)
            join staging.stg_naf__secteurs s on s.code_naf = e.code_naf_sirene
            where e.activite is not null
              and e.evenement in ('immatriculation', 'radiation', 'cession', 'ouverture_procedure')
            -- tirage déterministe (reproductible quel que soit le parallélisme)
            order by md5(e.id_annonce || '{int(graine)}')
            limit {int(n)}
            """
        ).fetchall()
    finally:
        con.close()
    verite = {i: (div, sec) for i, _, div, sec in lignes}
    cache_eval = cfg.raw / "enrichissement" / "evaluation_cache.json"
    deja = json.loads(cache_eval.read_text(encoding="utf-8")) if cache_eval.exists() else {}
    textes = {i: t for i, t, _, _ in lignes}
    manquants = {i: t for i, t in textes.items() if empreinte(t, pj["modele"]) not in deja}
    for i, rep in classeur(manquants, nomenclature, pj["modele"], pj["concurrence"]).items():
        deja[empreinte(textes[i], pj["modele"])] = asdict(rep)
    cache_eval.parent.mkdir(parents=True, exist_ok=True)
    cache_eval.write_text(json.dumps(deja), encoding="utf-8")
    reponses = {i: Reponse(**deja[empreinte(t, pj["modele"])]) for i, t in textes.items()}
    return mesurer(reponses, verite, nomenclature, pj["seuil_division"], pj["seuil_section"])


def mesurer(
    reponses: dict[str, Reponse],
    verite: dict[str, tuple[str, str]],
    nomenclature: Nomenclature,
    seuil_division: float,
    seuil_section: float,
) -> dict[str, Any]:
    n = len(reponses)
    if n == 0:
        raise ValueError("échantillon d'évaluation vide")

    def politique(sd: float, ss: float) -> dict[str, Any]:
        compte = defaultdict(int)
        justes = defaultdict(int)
        for i, r in reponses.items():
            d = decider(r, nomenclature, sd, ss)
            compte[d.niveau] += 1
            div, sec = verite[i]
            if (d.niveau == "division" and d.code_division == div) or (d.niveau == "section" and d.code_section == sec):
                justes[d.niveau] += 1
        attribues = compte["division"] + compte["section"]
        return {
            "seuil_division": sd,
            "seuil_section": ss,
            "part_division": round(compte["division"] / n, 3),
            "precision_division": round(justes["division"] / compte["division"], 3) if compte["division"] else None,
            "part_section": round(compte["section"] / n, 3),
            "precision_section": round(justes["section"] / compte["section"], 3) if compte["section"] else None,
            "part_non_attribuee": round(compte["aucun"] / n, 3),
            "precision_globale_attribuees": round((justes["division"] + justes["section"]) / attribues, 3)
            if attribues
            else None,
        }

    division_forcee = sum(r.division == verite[i][0] for i, r in reponses.items()) / n
    section_forcee = sum(nomenclature.section_de.get(r.division) == verite[i][1] for i, r in reponses.items()) / n
    calibration = []
    for bas, haut in ((0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)):
        sel = [(i, r) for i, r in reponses.items() if bas <= r.confiance < haut]
        if sel:
            calibration.append(
                {
                    "confiance": f"[{bas:.1f} ; {min(haut, 1):.1f}{']' if haut > 1 else '['}",
                    "annonces": len(sel),
                    "division_juste": round(sum(r.division == verite[i][0] for i, r in sel) / len(sel), 3),
                }
            )
    grille = [politique(sd, ss) for sd in (0.5, 0.7, 0.8, 0.9) for ss in (0.6, 0.8, 0.9)]
    modeles = sorted({r.modele for r in reponses.values()})
    return {
        "echantillon": n,
        "modeles": modeles,
        "version_question": VERSION_QUESTION,
        "division_forcee_juste": round(division_forcee, 3),
        "section_forcee_juste": round(section_forcee, 3),
        "politique_retenue": politique(seuil_division, seuil_section),
        "calibration": calibration,
        "grille": grille,
        "evalue_le": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def ecrire_rapport(resultat: dict[str, Any], dest: Path = RACINE / "docs" / "evaluation_jev.md") -> None:
    r = resultat
    p = r["politique_retenue"]

    def pct(x: float | None) -> str:
        return "–" if x is None else f"{100 * x:.0f} %"

    lignes = [
        "# Évaluation de l'attribution sectorielle par Jev",
        "",
        f"> Généré par `uv run obs evaluer-jev` le {r['evalue_le'][:10]} — modèle {', '.join(r['modeles'])}, "
        f"question `{r['version_question']}`, échantillon de {r['echantillon']} annonces.",
        "",
        "**Protocole.** Échantillon aléatoire reproductible d'événements BODACC publiés du périmètre "
        "dont le code NAF est connu par Sirene (vérité terrain). Seul le texte d'activité est envoyé "
        "à Jev ; on compare sa réponse au code Sirene. Limite : le code Sirene (APE déclarée de "
        "l'unité légale) et l'activité décrite dans l'annonce peuvent légitimement différer.",
        "",
        "## Résultats",
        "",
        f"- Division la plus probable juste (sans politique) : **{pct(r['division_forcee_juste'])}**",
        f"- Section déduite juste (sans politique) : **{pct(r['section_forcee_juste'])}**",
        "",
        f"Politique retenue (division si confiance ≥ {p['seuil_division']}, "
        f"sinon section si sa masse ≥ {p['seuil_section']}) :",
        "",
        "| Niveau attribué | Part des annonces | Précision |",
        "|---|---|---|",
        f"| Division | {pct(p['part_division'])} | {pct(p['precision_division'])} |",
        f"| Section seule | {pct(p['part_section'])} | {pct(p['precision_section'])} |",
        f"| Non attribué | {pct(p['part_non_attribuee'])} | – |",
        f"| **Ensemble des attributions** | {pct(p['part_division'] + p['part_section'])} "
        f"| **{pct(p['precision_globale_attribuees'])}** |",
        "",
        "## Calibration : la confiance annonce-t-elle la justesse ?",
        "",
        "| Confiance | Annonces | Division juste |",
        "|---|---|---|",
        *[f"| {c['confiance']} | {c['annonces']} | {pct(c['division_juste'])} |" for c in r["calibration"]],
        "",
        "## Grille des seuils",
        "",
        "| Seuil division | Seuil section | Division (part / précision) | Section (part / précision) "
        "| Non attribué | Précision globale |",
        "|---|---|---|---|---|---|",
        *[
            f"| {g['seuil_division']} | {g['seuil_section']} | {pct(g['part_division'])} / "
            f"{pct(g['precision_division'])} | {pct(g['part_section'])} / {pct(g['precision_section'])} "
            f"| {pct(g['part_non_attribuee'])} | {pct(g['precision_globale_attribuees'])} |"
            for g in r["grille"]
        ],
        "",
    ]
    dest.write_text("\n".join(lignes), encoding="utf-8")
