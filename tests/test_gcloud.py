from xwx.core import gcloud


def test_config_get_maps_unset_to_none(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: "(unset)")
    assert gcloud.config_get("project") is None


def test_config_get_returns_value(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: "my-project")
    assert gcloud.config_get("project") == "my-project"


def test_configurations_lists_names(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: "default\nstaging\n\nprod\n")
    assert gcloud.configurations() == ["default", "staging", "prod"]


def test_configurations_empty(monkeypatch):
    monkeypatch.setattr(gcloud.shell, "capture", lambda argv: None)
    assert gcloud.configurations() == []


def test_activate_raises_on_failure(monkeypatch):
    class Proc:
        returncode = 1

    monkeypatch.setattr(gcloud.shell, "run", lambda argv, **kw: Proc())
    try:
        gcloud.activate("nope")
    except gcloud.GcloudError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected GcloudError")


def test_set_project_raises_on_failure(monkeypatch):
    class Proc:
        returncode = 1

    monkeypatch.setattr(gcloud.shell, "run", lambda argv, **kw: Proc())
    try:
        gcloud.set_project("proj-123")
    except gcloud.GcloudError as exc:
        assert "proj-123" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected GcloudError")


def test_projects_parses_id_and_name(monkeypatch):
    monkeypatch.setattr(
        gcloud.shell,
        "capture",
        lambda argv: "proj-123\tMy Project\nproj-456\t\n",
    )
    assert gcloud.projects() == [
        gcloud.Project("proj-123", "My Project"),
        gcloud.Project("proj-456", None),
    ]


def test_project_label_falls_back_to_id():
    assert gcloud.Project("proj-123", "My Project").label() == "My Project (proj-123)"
    assert gcloud.Project("proj-123", None).label() == "proj-123"
    assert gcloud.Project("proj-123", "proj-123").label() == "proj-123"
