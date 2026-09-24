import json
from datetime import date

import duckdb
import httpx
import pytest
import respx
from socle_territorial.journal import Journal

from ingestion import sirene_api
from ingestion.config import Config
from ingestion.sirene_api import (
    COLONNES_ETABLISSEMENT,
    ClientSirene,
    aplatir_etablissement,
    aplatir_unite_legale,
    ingerer_sirene_api,
    requete_etablissements,
)

API = "https://api.test/api-sirene/3.11"

# Réponses réelles de l'API (24/09/2026) réduites, avec des champs nominatifs fictifs
# ajoutés pour vérifier la minimisation.
ETAB = {
    "siren": "100156231",
    "nic": "00019",
    "siret": "10015623100019",
    "statutDiffusionEtablissement": "O",
    "dateCreationEtablissement": "2026-01-22",
    "trancheEffectifsEtablissement": "NN",
    "anneeEffectifsEtablissement": None,
    "dateDernierTraitementEtablissement": "2026-09-18T14:08:21.989",
    "etablissementSiege": True,
    "nombrePeriodesEtablissement": 2,
    "activitePrincipaleNAF25Etablissement": "53.20G",
    "denominationUsuelleEtablissement": "BOULANGERIE DUPONT",
    "adresseEtablissement": {"codeCommuneEtablissement": "64129", "libelleVoieEtablissement": "RUE X"},
    "periodesEtablissement": [
        {
            "dateFin": None,
            "dateDebut": "2026-09-14",
            "etatAdministratifEtablissement": "A",
            "activitePrincipaleEtablissement": "53.20Z",
            "nomenclatureActivitePrincipaleEtablissement": "NAFRev2",
            "caractereEmployeurEtablissement": "N",
        },
        {
            "dateFin": "2026-09-13",
            "dateDebut": "2026-01-22",
            "etatAdministratifEtablissement": "A",
            "activitePrincipaleEtablissement": "62.01Z",
            "nomenclatureActivitePrincipaleEtablissement": "NAFRev2",
            "caractereEmployeurEtablissement": "N",
        },
    ],
}

UL = {
    "siren": "100156231",
    "statutDiffusionUniteLegale": "O",
    "dateCreationUniteLegale": "2026-01-22",
    "nomUniteLegale": "DUPONT",
    "prenom1UniteLegale": "Jean",
    "periodesUniteLegale": [
        {
            "dateFin": None,
            "dateDebut": "2026-09-14",
            "etatAdministratifUniteLegale": "A",
            "categorieJuridiqueUniteLegale": "1000",
            "activitePrincipaleUniteLegale": "53.20Z",
            "nomenclatureActivitePrincipaleUniteLegale": "NAFRev2",
            "nicSiegeUniteLegale": "00019",
        },
        {"dateFin": "2026-09-13", "dateDebut": "2026-01-22", "activitePrincipaleUniteLegale": "62.01Z"},
    ],
}

LIEN = {
    "siretEtablissementPredecesseur": "04638003600015",
    "siretEtablissementSuccesseur": "10015623100019",
    "dateLienSuccession": "2026-07-03",
    "transfertSiege": False,
    "continuiteEconomique": True,
    "dateDernierTraitementLienSuccession": "2026-09-01T16:00:47.003",
}


def page(liste, elements, curseur="*", suivant="*"):
    return {"header": {"statut": 200, "curseur": curseur, "curseurSuivant": suivant}, liste: elements}


@pytest.fixture(autouse=True)
def sans_attente(monkeypatch):
    monkeypatch.setattr("ingestion.sirene_api.time.sleep", lambda s: None)
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda s: None)


def test_aplatir_etablissement_periode_courante_et_minimisation():
    ligne = aplatir_etablissement(ETAB)
    assert ligne["codeCommuneEtablissement"] == "64129"
    assert ligne["activitePrincipaleEtablissement"] == "53.20Z"  # période en cours, pas l'ancienne
    assert ligne["dateDebut"] == "2026-09-14"
    serialise = json.dumps({k: ligne.get(k) for k in COLONNES_ETABLISSEMENT}, ensure_ascii=False)
    for interdit in ("DUPONT", "RUE X"):
        assert interdit not in serialise


def test_aplatir_unite_legale_periode_courante():
    ligne = aplatir_unite_legale(UL)
    assert ligne["activitePrincipaleUniteLegale"] == "53.20Z"
    assert ligne["nicSiegeUniteLegale"] == "00019"
    assert ligne["dateCreationUniteLegale"] == "2026-01-22"


def test_requete_etablissements_fenetre_de_traitement_et_de_creation():
    q = requete_etablissements({"64", "40"}, date(2026, 8, 31), date(2023, 9, 1))
    assert q == (
        "(codeCommuneEtablissement:40* OR codeCommuneEtablissement:64*)"
        " AND dateDernierTraitementEtablissement:[2026-08-31 TO *]"
        " AND dateCreationEtablissement:[2023-09-01 TO *]"
    )


def test_requete_etablissements_refuse_un_code_departement_anormal():
    with pytest.raises(ValueError, match="département invalides"):
        requete_etablissements({"64* OR *"}, date(2026, 8, 31), date(2023, 9, 1))


@respx.mock
def test_paginer_suit_le_curseur_avec_la_cle():
    route = respx.get(f"{API}/siret").mock(
        side_effect=[
            httpx.Response(200, json=page("etablissements", [ETAB], "*", "C1")),
            httpx.Response(200, json=page("etablissements", [ETAB], "C1", "C1")),
        ]
    )
    client = ClientSirene(API, "cle-test", 30)
    assert len(list(client.paginer("/siret", "etablissements", "q", "siret,siren"))) == 2
    assert [c.request.url.params["curseur"] for c in route.calls] == ["*", "C1"]
    requete = route.calls.last.request
    assert requete.headers["X-INSEE-Api-Key-Integration"] == "cle-test"
    assert requete.url.params["champs"] == "siret,siren"


@respx.mock
def test_paginer_404_signifie_aucun_resultat():
    respx.get(f"{API}/siret/liensSuccession").mock(return_value=httpx.Response(404, json={"header": {}}))
    client = ClientSirene(API, "cle-test", 30)
    assert list(client.paginer("/siret/liensSuccession", "liensSuccession", "q")) == []


@respx.mock
def test_paginer_reessaie_sur_quota_depasse():
    route = respx.get(f"{API}/siret").mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json=page("etablissements", []))]
    )
    assert list(ClientSirene(API, "cle-test", 30).paginer("/siret", "etablissements", "q")) == []
    assert route.call_count == 2


@respx.mock
def test_paginer_echoue_sur_cle_refusee():
    respx.get(f"{API}/siret").mock(return_value=httpx.Response(401))
    with pytest.raises(httpx.HTTPStatusError):
        list(ClientSirene(API, "mauvaise", 30).paginer("/siret", "etablissements", "q"))


@respx.mock
def test_par_lots_decoupe_les_identifiants(monkeypatch):
    monkeypatch.setattr(sirene_api, "TAILLE_LOT", 2)
    route = respx.get(f"{API}/siren").mock(return_value=httpx.Response(200, json=page("unitesLegales", [])))
    list(ClientSirene(API, "cle-test", 30).par_lots("/siren", "unitesLegales", "siren", ["a", "b", "c"]))
    assert [c.request.url.params["q"] for c in route.calls] == ["siren:(a OR b)", "siren:(c)"]


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("OBS_DATA_DIR", str(tmp_path))
    c = Config.charger("bab_littoral", aujourd_hui=date(2026, 9, 24))
    stock = c.raw / "sirene" / "etablissements.parquet"
    stock.parent.mkdir(parents=True)
    duckdb.execute(
        f"copy (select timestamp '2026-08-31 22:48:38' as dateDernierTraitementEtablissement) "
        f"to '{stock.as_posix()}' (format parquet)"
    )
    return c


@respx.mock
def test_ingerer_sans_cle_n_appelle_rien_et_ecrit_un_complement_vide(cfg, monkeypatch):
    monkeypatch.delenv("INSEE_API_KEY", raising=False)
    ancien = cfg.raw / "sirene_api" / "etablissements.parquet"
    ancien.parent.mkdir(parents=True)
    ancien.write_bytes(b"ancien")
    ingerer_sirene_api(cfg, Journal(cfg.journal_path), {"64"})
    assert not respx.calls
    # Fichiers vides mais au schéma du stock : la fusion en staging les lit sans cas particulier.
    etab = duckdb.sql(f"select * from '{ancien.as_posix()}'")
    assert etab.columns == list(COLONNES_ETABLISSEMENT)
    assert etab.fetchall() == []
    for f in ("unites_legales", "liens_succession"):
        assert duckdb.sql(f"select count(*) from '{(ancien.parent / f).as_posix()}.parquet'").fetchall() == [(0,)]


@respx.mock
def test_ingerer_ecrit_les_trois_fichiers_au_schema_du_stock(cfg, monkeypatch):
    monkeypatch.setenv("INSEE_API_KEY", "cle-test")
    monkeypatch.setitem(cfg.sources, "sirene_api", API)
    siret = respx.get(f"{API}/siret").mock(return_value=httpx.Response(200, json=page("etablissements", [ETAB])))
    respx.get(f"{API}/siren").mock(return_value=httpx.Response(200, json=page("unitesLegales", [UL])))
    respx.get(f"{API}/siret/liensSuccession").mock(
        return_value=httpx.Response(200, json=page("liensSuccession", [LIEN]))
    )

    ingerer_sirene_api(cfg, Journal(cfg.journal_path), {"64"})

    assert "dateDernierTraitementEtablissement:[2026-08-31 TO *]" in siret.calls.last.request.url.params["q"]
    dest = cfg.raw / "sirene_api"
    etab = duckdb.sql(f"select * from '{(dest / 'etablissements.parquet').as_posix()}'")
    assert etab.columns == list(COLONNES_ETABLISSEMENT)
    assert etab.fetchall()[0][:3] == ("100156231", "00019", "10015623100019")
    ul = duckdb.sql(f"select categorieJuridiqueUniteLegale from '{(dest / 'unites_legales.parquet').as_posix()}'")
    assert ul.fetchall() == [(1000,)]
    liens = duckdb.sql(f"select count(*) from '{(dest / 'liens_succession.parquet').as_posix()}'")
    assert liens.fetchall() == [(1,)]
    sources = [e["source"] for e in Journal(cfg.journal_path).lire()]
    assert sources == ["sirene_api_etablissements", "sirene_api_unites_legales", "sirene_api_liens_succession"]


@respx.mock
@pytest.mark.parametrize("reponse", [httpx.Response(503), httpx.Response(429), httpx.ConnectError("insee injoignable")])
def test_ingerer_api_indisponible_revient_au_stock_seul(cfg, monkeypatch, reponse):
    monkeypatch.setenv("INSEE_API_KEY", "cle-test")
    monkeypatch.setitem(cfg.sources, "sirene_api", API)
    respx.get(f"{API}/siret").mock(return_value=httpx.Response(200, json=page("etablissements", [ETAB])))
    respx.get(f"{API}/siren").mock(side_effect=reponse)

    ingerer_sirene_api(cfg, Journal(cfg.journal_path), {"64"})

    dest = cfg.raw / "sirene_api"
    for f in ("etablissements", "unites_legales", "liens_succession"):
        assert duckdb.sql(f"select count(*) from '{(dest / f).as_posix()}.parquet'").fetchall() == [(0,)]
    assert not dest.with_name("sirene_api.part").exists()
    statuts = [(e["source"], e["statut"]) for e in Journal(cfg.journal_path).lire()]
    assert statuts == [("sirene_api_etablissements", "ok"), ("sirene_api_unites_legales", "echec")]


@respx.mock
def test_ingerer_echec_partiel_ne_laisse_aucun_complement(cfg, monkeypatch):
    monkeypatch.setenv("INSEE_API_KEY", "cle-test")
    monkeypatch.setitem(cfg.sources, "sirene_api", API)
    ancien = cfg.raw / "sirene_api" / "unites_legales.parquet"
    ancien.parent.mkdir(parents=True)
    ancien.write_bytes(b"run precedent")
    respx.get(f"{API}/siret").mock(return_value=httpx.Response(200, json=page("etablissements", [ETAB])))
    respx.get(f"{API}/siren").mock(return_value=httpx.Response(401))

    with pytest.raises(httpx.HTTPStatusError):
        ingerer_sirene_api(cfg, Journal(cfg.journal_path), {"64"})

    # Ni les établissements du run courant seuls, ni les unités légales du run précédent.
    assert not (cfg.raw / "sirene_api").exists()
