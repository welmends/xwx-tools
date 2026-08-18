from xwx.core import gcloud


def test_config_get_traduz_unset_para_none(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: "(unset)")
    assert gcloud.config_get("project") is None


def test_config_get_devolve_valor(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: "meu-projeto")
    assert gcloud.config_get("project") == "meu-projeto"


def test_configurations_lista_nomes(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: "default\nstaging\n\nprod\n")
    assert gcloud.configurations() == ["default", "staging", "prod"]


def test_configurations_vazio(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: None)
    assert gcloud.configurations() == []


def test_activate_levanta_em_falha(monkeypatch):
    class Proc:
        returncode = 1

    monkeypatch.setattr(gcloud.shell, "run", lambda argv, **kw: Proc())
    try:
        gcloud.activate("nope")
    except gcloud.GcloudError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("esperava GcloudError")
