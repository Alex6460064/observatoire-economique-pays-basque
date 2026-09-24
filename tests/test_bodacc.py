import json
from datetime import date

import httpx
import pytest
import respx

from ingestion.bodacc import aplatir, extraire_mois, id_avis_precedent, mois_a_extraire, sirens

# Annonce réelle (procédure collective, parution du 15/09/2026) réduite aux champs utiles,
# avec une personne physique fictive pour vérifier la minimisation.
ANNONCE = {
    "id": "A202601765232",
    "publicationavis": "A",
    "parution": "20260176",
    "dateparution": "2026-09-15",
    "numeroannonce": 5232,
    "typeavis": "annonce",
    "familleavis": "collective",
    "numerodepartement": "64",
    "tribunal": "Greffe du Tribunal Judiciaire de Bayonne",
    "ville": "BIARRITZ",
    "cp": "64200",
    "registre": ["894670793", "894 670 793"],
    "listepersonnes": json.dumps(
        {
            "personne": {
                "typePersonne": "pp",
                "nom": "DUPONT",
                "prenom": "Jean",
                "adresseSiegeSocial": {"nomVoie": "rue X", "ville": "BIARRITZ"},
            }
        }
    ),
    "jugement": json.dumps(
        {
            "famille": "Jugement d'ouverture",
            "nature": "Jugement d'ouverture de liquidation judiciaire",
            "date": "2026-09-08",
        }
    ),
    "acte": None,
    "parutionavisprecedent": None,
}


def test_aplatir_minimise_et_extrait():
    ligne = aplatir(ANNONCE)
    assert ligne["siren"] == "894670793" and ligne["nb_siren"] == 1
    assert ligne["type_personne"] == "pp"
    assert ligne["jugement_nature"] == "Jugement d'ouverture de liquidation judiciaire"
    assert ligne["jugement_date"] == "2026-09-08"
    # Aucune donnée nominative ni adresse ne doit survivre à l'aplatissement.
    serialise = json.dumps(ligne, ensure_ascii=False)
    for interdit in ("DUPONT", "Jean", "rue X"):
        assert interdit not in serialise


def test_aplatir_vente_et_liste_de_personnes():
    r = dict(
        ANNONCE,
        familleavis="vente",
        jugement=None,
        listepersonnes=json.dumps({"personne": [{"typePersonne": "pm"}, {"typePersonne": "pp"}]}),
        acte=json.dumps({"vente": {"categorieVente": "Achat d'un fonds par une personne morale"}}),
    )
    ligne = aplatir(r)
    assert ligne["type_personne"] == "pm"
    assert ligne["categorie_vente"] == "Achat d'un fonds par une personne morale"
    assert ligne["jugement_date"] is None


def test_aplatir_date_jugement_invalide_rejetee():
    r = dict(ANNONCE, jugement=json.dumps({"date": "08/09/2026"}))
    assert aplatir(r)["jugement_date"] is None


def test_sirens_dedoublonne_et_valide():
    assert sirens(["944047612", "944 047 612", "884586363", "884 586 363"]) == ["944047612", "884586363"]
    assert sirens(["12 34"]) == []
    assert sirens(None) == []


def test_id_avis_precedent():
    p = {
        "nomPublication": "BODACC B",
        "numeroParution": "20250104",
        "dateParution": "2025-05-31",
        "numeroAnnonce": "1525",
    }
    assert id_avis_precedent(json.dumps(p)) == "B202501041525"
    assert id_avis_precedent(None) is None
    assert id_avis_precedent({"nomPublication": "BODACC A"}) is None


def test_mois_a_extraire_incremental():
    manifeste = {
        "2026-06": {"extrait_le": "2026-07-10T06:00:00+00:00"},  # lu après clôture : clos
        "2026-07": {"extrait_le": "2026-08-02T06:00:00+00:00"},  # lu avant fin + 3 j : à relire
    }
    mois = mois_a_extraire(date(2026, 6, 1), date(2026, 9, 23), manifeste)
    assert mois == [date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1)]


def test_mois_a_extraire_forcer_relit_tout():
    manifeste = {"2026-08": {"extrait_le": "2026-09-20T00:00:00+00:00"}}
    assert mois_a_extraire(date(2026, 8, 1), date(2026, 9, 23), manifeste, forcer=True) == [
        date(2026, 8, 1), date(2026, 9, 1)]  # fmt: skip


@respx.mock
def test_extraire_mois_requete_filtree():
    route = respx.get("https://api.test/exports/json").mock(return_value=httpx.Response(200, json=[ANNONCE]))
    assert extraire_mois("https://api.test", date(2026, 9, 1), {"64"}) == [ANNONCE]
    where = route.calls.last.request.url.params["where"]
    assert "numerodepartement in ('64')" in where
    assert "dateparution >= date'2026-09-01'" in where and "dateparution < date'2026-10-01'" in where
    # Seuls les champs nécessaires sont demandés à l'API.
    assert "listepersonnes" in route.calls.last.request.url.params["select"]


@respx.mock
def test_extraire_mois_reessaie_sur_erreur_serveur(monkeypatch):
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda s: None)
    route = respx.get("https://api.test/exports/json").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=[])]
    )
    assert extraire_mois("https://api.test", date(2026, 9, 1), {"64"}) == []
    assert route.call_count == 2


def test_extraire_mois_refuse_un_code_departement_anormal():
    with pytest.raises(ValueError, match="département invalides"):
        extraire_mois("https://api.test", date(2026, 9, 1), {"64') or ('1'='1"})
