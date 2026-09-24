from datetime import date

import duckdb
import pytest
from socle_territorial.secret import verifier_secret

from ingestion.config import premier_du_mois
from ingestion.cubes import TOTAL, Evenement, construire_cube, fenetres, secretiser
from ingestion.export import _requete, cellules_publiques

MOIS = [premier_du_mois(date(2024, 1, 1), i) for i in range(30)]  # 2024-01 .. 2026-06
COMMUNES = ["64102", "64024", "64008"]
SECTIONS = ["G", "I", "ZZ"]
DIVISIONS = {"G": ["45", "47"], "I": ["55", "56"], "ZZ": ["ZZ"]}


def _ev(m, c, s, d, v, detail=None):
    return Evenement(m, c, s, d, detail, v)


def _jeu():
    ev = []
    for i, m in enumerate(MOIS):
        ev += [
            _ev(m, "64102", "G", "47", 20 + i % 5),
            _ev(m, "64102", "I", "56", 9),
            _ev(m, "64024", "I", "55", 6 + i % 3),
            _ev(m, "64008", "G", "45", 1 + i % 2),  # petite commune : toujours sous le seuil
        ]
        if i % 4 == 0:
            ev.append(_ev(m, "64024", "ZZ", "ZZ", 2))
    return ev


def test_premier_du_mois():
    assert premier_du_mois(date(2026, 1, 15), -1) == date(2025, 12, 1)
    assert premier_du_mois(date(2026, 12, 31), 1) == date(2027, 1, 1)


def test_fenetres_de_12_mois():
    w = fenetres(date(2026, 6, 1), date(2024, 1, 1))
    assert [x[0] for x in w] == ["2026-06", "2025-06"]
    assert w[0][1][0] == date(2025, 7, 1) and len(w[0][1]) == 12
    assert fenetres(date(2025, 6, 1), date(2025, 1, 1)) == []  # historique insuffisant


def test_cube_totaux_coherents():
    ev = _jeu()
    cube = construire_cube(ev, MOIS, MOIS, COMMUNES, SECTIONS, DIVISIONS)
    total = sum(e.valeur for e in ev)
    assert sum(v for k, v in cube.valeurs.items() if k[0] == "mois" and k[2] == TOTAL and k[3] == "T") == total
    for rel in cube.relations:  # chaque relation déclarée est une vraie égalité additive
        *parties, tot = rel
        assert sum(cube.valeurs[k] for k in parties) == cube.valeurs[tot], rel[-1]


def test_cube_secret_complet():
    cube = secretiser(construire_cube(_jeu(), MOIS, MOIS, COMMUNES, SECTIONS, DIVISIONS), seuil=5)
    assert verifier_secret(cube.valeurs, cube.masque, cube.relations, 5) == []
    # La petite commune est masquée chaque mois, et un autre case l'est aussi dans chaque mois.
    for m in MOIS:
        p = m.strftime("%Y-%m")
        assert ("mois", p, "64008", "T", "") in cube.masque
    # Les totaux du territoire restent publiés.
    assert all(("mois", m.strftime("%Y-%m"), TOTAL, "T", "") not in cube.masque for m in MOIS)


def test_cellules_publiques_sans_valeur_sous_seuil():
    cube = secretiser(construire_cube(_jeu(), MOIS, MOIS[:-2], COMMUNES, SECTIONS, DIVISIONS), seuil=5)
    cellules = cellules_publiques("x", cube, provisoires={"2026-05", "2026-06"})
    assert all(c["valeur"] == "" or int(c["valeur"]) >= 5 for c in cellules)
    assert all(c["valeur"] == "" for c in cellules if c["secret"])
    prov = {c["periode"] for c in cellules if c["provisoire"]}
    assert prov == {"2026-05", "2026-06"}


def test_types_de_procedure_somment_au_total():
    ev = [_ev(MOIS[0], "64102", "G", "47", 7, "liquidation"), _ev(MOIS[0], "64024", "I", "55", 3, "redressement")]
    types = ["liquidation", "redressement", "sauvegarde", "autre"]
    cube = construire_cube(ev, MOIS[:1], [], COMMUNES, SECTIONS, DIVISIONS, types)
    assert cube.valeurs[("mois", "2024-01", TOTAL, "P", "liquidation")] == 7
    assert any(r[-1] == ("mois", "2024-01", TOTAL, "T", "") and r[0][3] == "P" for r in cube.relations)


def test_secteur_inconnu_refuse():
    with pytest.raises(ValueError, match="hors référentiel"):
        construire_cube([_ev(MOIS[0], "64102", "Q", "86", 5)], MOIS, MOIS, COMMUNES, SECTIONS, DIVISIONS)


def test_requete_parametree_traite_la_valeur_comme_une_donnee():
    con = duckdb.connect()
    con.execute("create table t as select * from (values ('a', 1), ('b''c', 2)) v(indicateur, valeur)")
    assert _requete(con, "select valeur from t where indicateur = ?", ["b'c"]) == [{"valeur": 2}]
    assert _requete(con, "select valeur from t where indicateur = ?", ["a' or '1'='1"]) == []
