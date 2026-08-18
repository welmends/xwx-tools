import pytest

from xwx.cli import gcpuse


@pytest.fixture(autouse=True)
def gcloud_instalado(monkeypatch):
    monkeypatch.setattr(gcpuse.gcloud, "ensure_installed", lambda: "/usr/bin/gcloud")


def _fake_gcloud(monkeypatch, *, configs, active=None, account=None, project=None):
    calls = []
    g = gcpuse.gcloud
    monkeypatch.setattr(g, "configurations", lambda: list(configs))
    monkeypatch.setattr(g, "active_configuration", lambda: active)
    monkeypatch.setattr(g, "account", lambda: account)
    monkeypatch.setattr(g, "project", lambda: project)
    monkeypatch.setattr(g, "activate", lambda name: calls.append(("activate", name)))
    monkeypatch.setattr(g, "auth_login", lambda: calls.append(("login", None)))
    monkeypatch.setattr(g, "auth_adc_login", lambda: calls.append(("adc", None)))
    monkeypatch.setattr(
        g,
        "set_adc_quota_project",
        lambda p: (calls.append(("quota", p)), True)[1],
    )
    return calls


def test_status_sem_conta_lista_configurations(monkeypatch, capsys):
    _fake_gcloud(monkeypatch, configs=["default", "staging"])
    assert gcpuse.main([]) == 0
    out = capsys.readouterr().out
    assert "nenhuma conta logada" in out
    assert "staging" in out


def test_status_com_conta(monkeypatch, capsys):
    _fake_gcloud(
        monkeypatch,
        configs=["staging"],
        active="staging",
        account="eu@example.com",
        project="proj-123",
    )
    assert gcpuse.main([]) == 0
    out = capsys.readouterr().out
    assert "staging" in out
    assert "eu@example.com" in out
    assert "proj-123" in out


def test_list(monkeypatch, capsys):
    _fake_gcloud(monkeypatch, configs=["default", "prod"], active="prod")
    assert gcpuse.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "default" in out and "prod" in out


def test_switch_faz_activate_login_adc_e_quota(monkeypatch):
    calls = _fake_gcloud(
        monkeypatch, configs=["staging"], active="staging", project="proj-123"
    )
    assert gcpuse.main(["staging"]) == 0
    assert calls == [
        ("activate", "staging"),
        ("login", None),
        ("adc", None),
        ("quota", "proj-123"),
    ]


def test_switch_no_login_so_ativa(monkeypatch):
    calls = _fake_gcloud(monkeypatch, configs=["staging"], project="proj-123")
    assert gcpuse.main(["staging", "--no-login"]) == 0
    assert calls == [("activate", "staging")]


def test_switch_no_adc_pula_adc_e_quota(monkeypatch):
    calls = _fake_gcloud(monkeypatch, configs=["staging"], project="proj-123")
    assert gcpuse.main(["staging", "--no-adc"]) == 0
    assert calls == [("activate", "staging"), ("login", None)]


def test_configuration_inexistente(monkeypatch, capsys):
    calls = _fake_gcloud(monkeypatch, configs=["staging"])
    assert gcpuse.main(["typo"]) == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "typo" in err


def test_erro_do_gcloud_vira_exit_1(monkeypatch, capsys):
    _fake_gcloud(monkeypatch, configs=["staging"])

    def boom(name):
        raise gcpuse.gcloud.GcloudError("falhou feio")

    monkeypatch.setattr(gcpuse.gcloud, "activate", boom)
    assert gcpuse.main(["staging"]) == 1
    assert "falhou feio" in capsys.readouterr().err


def test_gcloud_ausente_vira_exit_127(monkeypatch, capsys):
    def boom():
        raise gcpuse.CommandNotFound("'gcloud' nao encontrado no PATH.")

    monkeypatch.setattr(gcpuse.gcloud, "ensure_installed", boom)
    assert gcpuse.main([]) == 127
    assert "gcloud" in capsys.readouterr().err
