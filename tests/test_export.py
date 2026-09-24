from ingestion.export import vider_dossier


def test_vider_dossier_supprime_le_contenu_et_garde_le_dossier(tmp_path):
    dest = tmp_path / "data"
    (dest / "sous").mkdir(parents=True)
    (dest / "ancien.csv").write_text("x")
    (dest / "sous" / "f.json").write_text("{}")

    vider_dossier(dest)

    assert dest.is_dir()
    assert list(dest.iterdir()) == []


def test_vider_dossier_cree_le_dossier_absent(tmp_path):
    dest = tmp_path / "a" / "data"

    vider_dossier(dest)

    assert dest.is_dir()
