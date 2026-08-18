import pytest

from xwx.cli import gcpuse
from xwx.core.gcloud import Project


@pytest.fixture(autouse=True)
def gcloud_installed(monkeypatch):
    monkeypatch.setattr(gcpuse.gcloud, "ensure_installed", lambda: "/usr/bin/gcloud")


def _fake_gcloud(
    monkeypatch,
    *,
    configs=(),
    active=None,
    account=None,
    project=None,
    names=None,
    projects=(),
    quota_ok=True,
):
    """Patch the gcloud wrapper and record the state-changing calls."""
    calls = []
    g = gcpuse.gcloud
    state = {"project": project}
    names = names or {}

    def set_project(project_id):
        calls.append(("set-project", project_id))
        state["project"] = project_id

    monkeypatch.setattr(g, "configurations", lambda: list(configs))
    monkeypatch.setattr(g, "active_configuration", lambda: active)
    monkeypatch.setattr(g, "account", lambda: account)
    monkeypatch.setattr(g, "project", lambda: state["project"])
    monkeypatch.setattr(g, "projects", lambda: list(projects))
    monkeypatch.setattr(g, "project_name", lambda pid: names.get(pid))
    monkeypatch.setattr(g, "describe_project", lambda pid: Project(pid, names.get(pid)))
    monkeypatch.setattr(g, "activate", lambda name: calls.append(("activate", name)))
    monkeypatch.setattr(g, "auth_login", lambda: calls.append(("login", None)))
    monkeypatch.setattr(g, "auth_adc_login", lambda: calls.append(("adc", None)))
    monkeypatch.setattr(g, "set_project", set_project)
    monkeypatch.setattr(
        g,
        "set_adc_quota_project",
        lambda p: (calls.append(("quota", p)), quota_ok)[1],
    )
    return calls


def test_status_without_account_lists_configurations(monkeypatch, capsys):
    _fake_gcloud(monkeypatch, configs=["default", "staging"])
    assert gcpuse.main([]) == 0
    out = capsys.readouterr().out
    assert "no account logged in" in out
    assert "staging" in out


def test_status_shows_project_name_and_id(monkeypatch, capsys):
    _fake_gcloud(
        monkeypatch,
        configs=["staging"],
        active="staging",
        account="me@example.com",
        project="proj-123",
        names={"proj-123": "My Project"},
    )
    assert gcpuse.main([]) == 0
    out = capsys.readouterr().out
    assert "staging" in out
    assert "me@example.com" in out
    assert "My Project (proj-123)" in out


def test_status_falls_back_to_id_when_name_unknown(monkeypatch, capsys):
    _fake_gcloud(
        monkeypatch,
        configs=["staging"],
        active="staging",
        account="me@example.com",
        project="proj-123",
    )
    assert gcpuse.main([]) == 0
    assert "proj-123" in capsys.readouterr().out


def test_list_configurations(monkeypatch, capsys):
    _fake_gcloud(monkeypatch, configs=["default", "prod"], active="prod")
    assert gcpuse.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "default" in out and "prod" in out


def test_list_projects_marks_the_current_one(monkeypatch, capsys):
    _fake_gcloud(
        monkeypatch,
        account="me@example.com",
        project="proj-123",
        projects=[Project("proj-123", "My Project"), Project("proj-456", "Other")],
    )
    assert gcpuse.main(["--projects"]) == 0
    out = capsys.readouterr().out
    assert "* My Project (proj-123)" in out
    assert "Other (proj-456)" in out


def test_list_projects_without_login(monkeypatch, capsys):
    _fake_gcloud(monkeypatch)
    assert gcpuse.main(["--projects"]) == 0
    assert "No projects visible" in capsys.readouterr().out


def test_switch_runs_activate_login_adc_and_quota(monkeypatch):
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


def test_switch_no_login_only_activates(monkeypatch):
    calls = _fake_gcloud(monkeypatch, configs=["staging"], project="proj-123")
    assert gcpuse.main(["staging", "--no-login"]) == 0
    assert calls == [("activate", "staging")]


def test_switch_no_adc_skips_adc_and_quota(monkeypatch):
    calls = _fake_gcloud(monkeypatch, configs=["staging"], project="proj-123")
    assert gcpuse.main(["staging", "--no-adc"]) == 0
    assert calls == [("activate", "staging"), ("login", None)]


def test_switch_with_project_overrides_the_configuration_project(monkeypatch):
    calls = _fake_gcloud(
        monkeypatch,
        configs=["staging"],
        active="staging",
        account="me@example.com",
        project="proj-123",
        names={"proj-999": "Nine"},
    )
    assert gcpuse.main(["staging", "-p", "proj-999"]) == 0
    assert calls == [
        ("activate", "staging"),
        ("login", None),
        ("adc", None),
        ("set-project", "proj-999"),
        ("quota", "proj-999"),
    ]


def test_project_only_switches_without_login(monkeypatch, capsys):
    calls = _fake_gcloud(
        monkeypatch,
        active="staging",
        account="me@example.com",
        project="proj-123",
        names={"proj-456": "Other"},
    )
    assert gcpuse.main(["-p", "proj-456"]) == 0
    assert calls == [("set-project", "proj-456"), ("quota", "proj-456")]
    out = capsys.readouterr().out
    assert "Other (proj-456)" in out
    assert "staging" in out


def test_project_switch_warns_when_project_cannot_be_verified(monkeypatch, capsys):
    _fake_gcloud(monkeypatch, active="staging", account="me@example.com")
    assert gcpuse.main(["-p", "typo-123"]) == 0
    assert "could not verify project 'typo-123'" in capsys.readouterr().err


def test_project_switch_requires_an_account(monkeypatch, capsys):
    calls = _fake_gcloud(monkeypatch, configs=["staging"])
    assert gcpuse.main(["-p", "proj-123"]) == 1
    assert calls == []
    assert "no account logged in" in capsys.readouterr().err


def test_quota_failure_only_warns(monkeypatch, capsys):
    _fake_gcloud(
        monkeypatch,
        active="staging",
        account="me@example.com",
        names={"proj-456": "Other"},
        quota_ok=False,
    )
    assert gcpuse.main(["-p", "proj-456"]) == 0
    assert "could not set the ADC quota project" in capsys.readouterr().err


def test_unknown_configuration(monkeypatch, capsys):
    calls = _fake_gcloud(monkeypatch, configs=["staging"])
    assert gcpuse.main(["typo"]) == 1
    assert calls == []
    assert "typo" in capsys.readouterr().err


def test_gcloud_error_becomes_exit_1(monkeypatch, capsys):
    _fake_gcloud(monkeypatch, configs=["staging"])

    def boom(name):
        raise gcpuse.gcloud.GcloudError("it broke")

    monkeypatch.setattr(gcpuse.gcloud, "activate", boom)
    assert gcpuse.main(["staging"]) == 1
    assert "it broke" in capsys.readouterr().err


def test_missing_gcloud_becomes_exit_127(monkeypatch, capsys):
    def boom():
        raise gcpuse.CommandNotFound("'gcloud' was not found on PATH.")

    monkeypatch.setattr(gcpuse.gcloud, "ensure_installed", boom)
    assert gcpuse.main([]) == 127
    assert "gcloud" in capsys.readouterr().err
