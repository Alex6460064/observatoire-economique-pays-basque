import itertools
import random

import pytest
from socle_territorial.secret import appliquer_secret, verifier_secret


def test_zero_et_valeurs_au_dessus_du_seuil_publiees():
    valeurs = {"a": 0, "b": 5, "c": 12}
    assert appliquer_secret(valeurs, [], seuil=5) == {}


def test_suppression_primaire():
    valeurs = {"a": 1, "b": 4, "c": 5}
    assert appliquer_secret(valeurs, [], seuil=5) == {"a": "primaire", "b": "primaire"}


def test_secondaire_empeche_le_calcul_par_difference():
    # a + b + c = total ; a seul masqué => total - b - c le révèle.
    valeurs = {"a": 2, "b": 7, "c": 30, "total": 39}
    rel = [["a", "b", "c", "total"]]
    masque = appliquer_secret(valeurs, rel, seuil=5)
    assert masque == {"a": "primaire", "b": "secondaire"}  # plus petite case non nulle
    assert verifier_secret(valeurs, masque, rel, seuil=5) == []


def test_secondaire_ignore_les_zeros_si_possible():
    valeurs = {"a": 3, "z": 0, "b": 9, "total": 12}
    masque = appliquer_secret(valeurs, [["a", "z", "b", "total"]], seuil=5)
    assert masque["b"] == "secondaire"
    assert "z" not in masque


def test_propagation_en_tableau_croise():
    # Tableau 2x2 + marges. x11 masqué en primaire force une case sur sa ligne,
    # qui force à son tour une case sur sa colonne, etc.
    v = {
        ("r1", "c1"): 2,
        ("r1", "c2"): 20,
        ("r1", "T"): 22,
        ("r2", "c1"): 15,
        ("r2", "c2"): 30,
        ("r2", "T"): 45,
        ("T", "c1"): 17,
        ("T", "c2"): 50,
        ("T", "T"): 67,
    }
    lignes = [[(r, c) for c in ("c1", "c2", "T")] for r in ("r1", "r2", "T")]
    colonnes = [[(r, c) for r in ("r1", "r2", "T")] for c in ("c1", "c2", "T")]
    rel = lignes + colonnes
    masque = appliquer_secret(v, rel, seuil=5)
    assert verifier_secret(v, masque, rel, seuil=5) == []
    assert masque[("r1", "c1")] == "primaire"
    assert len(masque) >= 4  # un rectangle complet est le minimum en 2D


def test_proprietes_sur_tableaux_aleatoires():
    rng = random.Random(42)
    for _ in range(200):
        nr, nc = rng.randint(1, 6), rng.randint(1, 6)
        cases = {(r, c): rng.choice([0, 0, 1, 2, 3, 4, 5, 8, 20]) for r in range(nr) for c in range(nc)}
        for r in range(nr):
            cases[(r, "T")] = sum(cases[(r, c)] for c in range(nc))
        for c in [*range(nc), "T"]:
            cases[("T", c)] = sum(cases[(r, c)] for r in range(nr))
        rel = [[(r, c) for c in [*range(nc), "T"]] for r in [*range(nr), "T"]]
        rel += [[(r, c) for r in [*range(nr), "T"]] for c in [*range(nc), "T"]]
        masque = appliquer_secret(cases, rel, seuil=5)
        assert verifier_secret(cases, masque, rel, seuil=5) == []


def test_relation_avec_case_inconnue():
    with pytest.raises(KeyError):
        appliquer_secret({"a": 1}, [["a", "b"]], seuil=5)


@pytest.mark.parametrize("seuil", [0, 1])
def test_seuil_invalide(seuil):
    with pytest.raises(ValueError):
        appliquer_secret({"a": 1}, [], seuil=seuil)


def test_verifier_detecte_une_fuite():
    v = {"a": 2, "b": 7, "total": 9}
    assert verifier_secret(v, {"a": "primaire"}, [["a", "b", "total"]], seuil=5)
    assert verifier_secret(v, {}, [], seuil=5)


def test_ordre_des_relations_sans_effet_sur_la_validite():
    v = {"a": 1, "b": 6, "c": 2, "d": 9, "t1": 7, "t2": 11, "u1": 3, "u2": 15, "tt": 18}
    rel = [
        ["a", "b", "t1"],
        ["c", "d", "t2"],
        ["a", "c", "u1"],
        ["b", "d", "u2"],
        ["t1", "t2", "tt"],
        ["u1", "u2", "tt"],
    ]
    for perm in itertools.permutations(rel):
        m = appliquer_secret(v, perm, seuil=5)
        assert verifier_secret(v, m, rel, seuil=5) == []
