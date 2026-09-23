"""Ingestion incrémentale du BODACC (API Opendatasoft de la DILA, sans clé).

- **Incrémental par mois de parution** : un mois dont la dernière extraction est
  postérieure à sa fin (+ marge) est « clos » et n'est plus relu. Le mois courant et
  les mois jamais extraits le sont à chaque run. ``--forcer`` relit tout (rejouabilité).
- **Minimisation à l'ingestion** : les annonces contiennent des noms de personnes
  physiques et des adresses. On ne conserve que les champs utiles aux agrégats
  (famille, dates, commune, SIREN pour la jointure Sirene, nature du jugement,
  catégorie de vente/création). Aucun nom, prénom, adresse ni texte libre n'est écrit
  sur disque.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from socle_territorial import http
from socle_territorial.journal import Journal
from socle_territorial.stockage import ecrire_parquet

from ingestion.config import Config, premier_du_mois

log = logging.getLogger(__name__)

FAMILLES = ("creation", "immatriculation", "vente", "collective", "radiation")
MARGE_CLOTURE = timedelta(days=3)

CHAMPS_API = (
    "id,publicationavis,parution,dateparution,numeroannonce,typeavis,familleavis,numerodepartement,"
    "tribunal,ville,cp,registre,listepersonnes,listeetablissements,jugement,acte,parutionavisprecedent"
)

COLONNES_BODACC = {
    "id": "VARCHAR",
    "publication": "VARCHAR",
    "numero_parution": "VARCHAR",
    "date_parution": "DATE",
    "numero_annonce": "INTEGER",
    "type_avis": "VARCHAR",
    "famille_avis": "VARCHAR",
    "departement": "VARCHAR",
    "tribunal": "VARCHAR",
    "ville": "VARCHAR",
    "code_postal": "VARCHAR",
    "siren": "VARCHAR",
    "nb_siren": "INTEGER",
    "type_personne": "VARCHAR",
    "jugement_famille": "VARCHAR",
    "jugement_nature": "VARCHAR",
    "jugement_date": "DATE",
    "categorie_vente": "VARCHAR",
    "categorie_creation": "VARCHAR",
    "id_avis_precedent": "VARCHAR",
    "activite": "VARCHAR",
}

ACTIVITES_VIDES = {"", "non precise", "non précisé", "neant", "néant", "sans activite", "sans activité"}
LONGUEUR_MAX_ACTIVITE = 300


def _json(v: Any) -> Any:
    if v in (None, ""):
        return {}
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return {}
    return v


def _premier(v: Any) -> dict[str, Any]:
    if isinstance(v, list):
        return v[0] if v and isinstance(v[0], dict) else {}
    return v if isinstance(v, dict) else {}


def _date(s: Any) -> str | None:
    """Les dates de jugement sont ``AAAA-MM-JJ`` ; tout autre format est rejeté (et compté en qualité)."""
    return s if isinstance(s, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None


def sirens(registre: Any) -> list[str]:
    """``registre`` alterne forme compacte et forme espacée : ``['894670793', '894 670 793', ...]``."""
    if not registre:
        return []
    vus = dict.fromkeys(re.sub(r"\D", "", str(x)) for x in registre)
    return [s for s in vus if len(s) == 9]


def id_avis_precedent(p: Any) -> str | None:
    """Reconstruit l'``id`` de l'annonce visée par un rectificatif/une annulation.

    ``id`` = lettre de publication + numéro de parution + numéro d'annonce, ex. ``A202601765232``.
    """
    p = _json(p)
    pub, par, num = p.get("nomPublication"), p.get("numeroParution"), p.get("numeroAnnonce")
    if not (pub and par and num):
        return None
    return f"{str(pub).strip()[-1]}{par}{int(num)}"


def activite(r: dict[str, Any]) -> str | None:
    """Description libre de l'activité (établissement, sinon personne), tronquée.

    Conservée pour l'attribution sectorielle des annonces sans code NAF (voir
    ``ingestion/jev.py``). Texte descriptif d'activité : ni nom, ni adresse.
    """
    etab = _premier(_json(r.get("listeetablissements")).get("etablissement"))
    personne = _premier(_json(r.get("listepersonnes")).get("personne"))
    for texte in (etab.get("activite"), personne.get("activite")):
        if isinstance(texte, str) and texte.strip().lower() not in ACTIVITES_VIDES:
            return re.sub(r"\s+", " ", texte).strip()[:LONGUEUR_MAX_ACTIVITE]
    return None


def aplatir(r: dict[str, Any]) -> dict[str, Any]:
    """Annonce API -> ligne minimisée. Fonction pure (testée unitairement)."""
    personne = _premier(_json(r.get("listepersonnes")).get("personne"))
    jugement = _json(r.get("jugement"))
    acte = _json(r.get("acte"))
    liste_siren = sirens(r.get("registre"))
    return {
        "id": r["id"],
        "publication": r.get("publicationavis"),
        "numero_parution": r.get("parution"),
        "date_parution": r.get("dateparution"),
        "numero_annonce": r.get("numeroannonce"),
        "type_avis": r.get("typeavis"),
        "famille_avis": r.get("familleavis"),
        "departement": r.get("numerodepartement"),
        "tribunal": r.get("tribunal"),
        "ville": r.get("ville"),
        "code_postal": r.get("cp"),
        "siren": liste_siren[0] if liste_siren else None,
        "nb_siren": len(liste_siren),
        "type_personne": personne.get("typePersonne"),
        "jugement_famille": jugement.get("famille"),
        "jugement_nature": jugement.get("nature"),
        "jugement_date": _date(jugement.get("date")),
        "categorie_vente": _premier(acte.get("vente")).get("categorieVente"),
        "categorie_creation": _premier(acte.get("creation")).get("categorieCreation"),
        "id_avis_precedent": id_avis_precedent(r.get("parutionavisprecedent")),
        "activite": activite(r),
    }


def mois_a_extraire(
    debut: date, aujourd_hui: date, manifeste: dict[str, dict[str, Any]], forcer: bool = False
) -> list[date]:
    """Mois (premier jour) à (re)lire : jamais lus, lus avant leur clôture, ou tous si ``forcer``."""
    out = []
    m = premier_du_mois(debut)
    courant = premier_du_mois(aujourd_hui)
    while m <= courant:
        fin = premier_du_mois(m, 1)
        info = manifeste.get(m.strftime("%Y-%m"))
        clos = info is not None and date.fromisoformat(info["extrait_le"][:10]) >= fin + MARGE_CLOTURE
        if forcer or not clos:
            out.append(m)
        m = fin
    return out


def extraire_mois(api: str, mois: date, departements: set[str]) -> list[dict[str, Any]]:
    fin = premier_du_mois(mois, 1)
    deps = ", ".join(f"'{d}'" for d in sorted(departements))
    fams = ", ".join(f"'{f}'" for f in FAMILLES)
    where = (
        f"numerodepartement in ({deps}) and familleavis in ({fams}) "
        f"and dateparution >= date'{mois.isoformat()}' and dateparution < date'{fin.isoformat()}'"
    )
    return http.get_json(f"{api}/exports/json", {"select": CHAMPS_API, "where": where})


def ingerer_bodacc(cfg: Config, journal: Journal, departements: set[str], forcer: bool = False) -> None:
    dest = cfg.raw / "bodacc"
    dest.mkdir(parents=True, exist_ok=True)
    manifeste_path = dest / "_manifest.json"
    manifeste = json.loads(manifeste_path.read_text(encoding="utf-8")) if manifeste_path.exists() else {}
    # Un manifeste qui référence un fichier disparu ne doit pas bloquer la relecture.
    manifeste = {m: v for m, v in manifeste.items() if (dest / f"annonces_{m}.parquet").exists()}
    a_lire = mois_a_extraire(cfg.debut_historique, cfg.aujourd_hui, manifeste, forcer)
    log.info("BODACC : %s mois à extraire", len(a_lire))
    for mois in a_lire:
        cle = mois.strftime("%Y-%m")
        with journal.extraction("bodacc", url=cfg.sources["bodacc_api"], millesime=cle) as e:
            brut = extraire_mois(cfg.sources["bodacc_api"], mois, departements)
            lignes = [aplatir(r) for r in brut]
            e.lignes = ecrire_parquet(lignes, dest / f"annonces_{cle}.parquet", COLONNES_BODACC)
        manifeste[cle] = {"extrait_le": datetime.now(UTC).isoformat(timespec="seconds"), "lignes": e.lignes}
        # Écrit après chaque mois : un run interrompu reprend là où il s'est arrêté.
        manifeste_path.write_text(json.dumps(dict(sorted(manifeste.items())), indent=2), encoding="utf-8")
        log.info("BODACC %s : %s annonces", cle, e.lignes)
