from xwx.core import inventory


def _probe(label):
    return next(p for p in inventory.PROBES if p.label == label)


def test_command_substitutes_the_project():
    probe = _probe("Storage buckets")
    assert probe.command("proj-123") == [
        "gcloud",
        "storage",
        "buckets",
        "list",
        "--format=value(name)",
        "--project=proj-123",
    ]


def test_bq_probe_uses_its_own_project_flag():
    probe = _probe("BigQuery datasets")
    assert probe.binary == "bq"
    assert probe.command("proj-123") == [
        "bq",
        "--format=json",
        "--project_id=proj-123",
        "ls",
    ]


def test_every_probe_declares_the_project():
    for probe in inventory.PROBES:
        assert any("{project}" in arg for arg in probe.argv), probe.label


def test_short_name_trims_paths_and_service_accounts():
    assert inventory._short_name("projects/x/databases/(default)") == "(default)"
    assert inventory._short_name("api@proj.iam.gserviceaccount.com") == "api"
    assert inventory._short_name("my-bucket") == "my-bucket"


def test_bq_datasets_parses_json(monkeypatch):
    payload = '[{"datasetReference": {"datasetId": "raw"}}, {"id": "proj:staging"}]'
    monkeypatch.setattr(inventory.shell, "capture", lambda argv, **kw: payload)
    assert inventory._bq_datasets(["bq"]) == ["raw", "staging"]


def test_bq_datasets_empty_output_is_not_a_failure(monkeypatch):
    monkeypatch.setattr(inventory.shell, "capture", lambda argv, **kw: None)
    assert inventory._bq_datasets(["bq"]) == []


def test_bq_datasets_invalid_json_is_a_failure(monkeypatch):
    monkeypatch.setattr(inventory.shell, "capture", lambda argv, **kw: "not json")
    assert inventory._bq_datasets(["bq"]) is None


def test_scan_only_probes_enabled_apis(monkeypatch):
    seen = []

    def fake_lines(argv, **kwargs):
        seen.append(argv)
        return ["one", "two"]

    monkeypatch.setattr(inventory.shell, "capture_lines", fake_lines)
    found = inventory.scan("proj-123", ["storage.googleapis.com"])

    assert [f.label for f in found.findings] == ["Storage buckets"]
    assert found.findings[0].names == ("one", "two")
    assert found.findings[0].count == 2
    assert "Cloud Run" in found.skipped
    assert len(seen) == 1


def test_scan_marks_failed_probes_as_denied(monkeypatch):
    monkeypatch.setattr(inventory.shell, "capture_lines", lambda argv, **kw: None)
    found = inventory.scan("proj-123", ["storage.googleapis.com"])
    assert found.findings[0].denied is True
    assert found.findings[0].count == 0


def test_scan_without_any_enabled_api(monkeypatch):
    monkeypatch.setattr(inventory.shell, "capture_lines", lambda argv, **kw: [])
    found = inventory.scan("proj-123", [])
    assert found.findings == ()
    assert len(found.skipped) == len(inventory.PROBES)
