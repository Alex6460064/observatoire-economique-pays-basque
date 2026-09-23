import pytest

from ingestion.jev import AUCUNE, Nomenclature, Reponse, criteres, decider, empreinte, mesurer

NOMENCLATURE = Nomenclature(
    libelles={"47": "Commerce de détail", "56": "Restauration", "55": "Hébergement", "49": "Transports terrestres"},
    section_de={"47": "G", "56": "I", "55": "I", "49": "H"},
)


def rep(division, confiance, **probas):
    return Reponse(division, confiance, probas, "jev-1.13.0")


def test_criteres_incluent_une_option_de_non_attribution():
    c = criteres(NOMENCLATURE)
    assert AUCUNE in c and set(NOMENCLATURE.libelles) <= set(c)


def test_decider_division_si_confiance_suffisante():
    d = decider(rep("56", 0.95, **{"56": 0.96, "55": 0.02, "47": 0.02}), NOMENCLATURE, 0.9, 0.8)
    assert (d.niveau, d.code_division, d.code_section) == ("division", "56", "I")


def test_decider_remonte_a_la_section_par_somme_des_probabilites():
    # Hésitation entre restauration et hébergement : la division est incertaine,
    # mais les deux sont dans la section I, dont la masse (0,9) suffit.
    d = decider(rep("56", 0.4, **{"56": 0.5, "55": 0.4, "47": 0.1}), NOMENCLATURE, 0.9, 0.8)
    assert (d.niveau, d.code_division, d.code_section) == ("section", None, "I")
    assert d.masse_section == pytest.approx(0.9)


def test_decider_rien_si_incertain_entre_sections():
    d = decider(rep("56", 0.3, **{"56": 0.45, "47": 0.4, "49": 0.15}), NOMENCLATURE, 0.9, 0.8)
    assert d.niveau == "aucun" and d.code_section is None


def test_decider_respecte_la_non_attribution():
    d = decider(rep(AUCUNE, 0.99, **{AUCUNE: 0.99, "47": 0.01}), NOMENCLATURE, 0.9, 0.8)
    assert d.niveau == "aucun"


def test_empreinte_change_avec_modele_et_texte():
    assert empreinte("boulangerie", "jev-1.13.0") != empreinte("boulangerie", "jev-1.14.0")
    assert empreinte("boulangerie", "jev-1.13.0") != empreinte("pâtisserie", "jev-1.13.0")
    assert empreinte("boulangerie", "jev-1.13.0") == empreinte("boulangerie", "jev-1.13.0")


def test_mesurer_compte_precision_par_niveau():
    reponses = {
        "a": rep("56", 0.95, **{"56": 0.97, "55": 0.03}),  # division juste
        "b": rep("47", 0.95, **{"47": 0.97, "56": 0.03}),  # division fausse (vrai : 56)
        "c": rep("55", 0.4, **{"55": 0.5, "56": 0.45, "47": 0.05}),  # section I juste
        "d": rep("49", 0.2, **{"49": 0.4, "47": 0.35, "56": 0.25}),  # non attribué
    }
    verite = {"a": ("56", "I"), "b": ("56", "I"), "c": ("56", "I"), "d": ("47", "G")}
    m = mesurer(reponses, verite, NOMENCLATURE, 0.9, 0.8)
    p = m["politique_retenue"]
    assert p["part_division"] == 0.5 and p["precision_division"] == 0.5
    assert p["part_section"] == 0.25 and p["precision_section"] == 1.0
    assert p["part_non_attribuee"] == 0.25
    assert p["precision_globale_attribuees"] == pytest.approx(0.667, abs=1e-3)
    assert m["division_forcee_juste"] == 0.25  # seul « a » a la bonne division en tête


def test_mesurer_refuse_un_echantillon_vide():
    with pytest.raises(ValueError):
        mesurer({}, {}, NOMENCLATURE, 0.9, 0.8)
