# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [SemVer](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-08-18

### Added

- `gcpuse -r/--resources`: list what exists inside the active project. It reads the
  project's enabled APIs and probes only those services, in parallel, across a curated
  set (Compute, GKE, Cloud Run, Functions, Cloud SQL, Storage, BigQuery, Firestore,
  Pub/Sub, Artifact Registry, Secret Manager, IAM, Cloud DNS, Cloud Build), plus the
  billing status. Composes with switching: `gcpuse -p other --resources`.
- `xwx.core.inventory`, a probe table any future GCP tool can reuse.

### Fixed

- Non-interactive gcloud reads now run with prompts disabled and a timeout. gcloud offers
  to enable a disabled API interactively, which could otherwise hang a read forever.

## [0.2.0] - 2026-08-18

### Added

- `gcpuse -p/--project <id>`: switch project within the active configuration without
  re-authenticating, realigning the ADC quota project. Combines with a configuration
  (`gcpuse staging -p proj-123`).
- `gcpuse --projects`: list the projects visible to the current account, marking the
  current one.

### Changed

- Projects are now displayed as `Display Name (project-id)` instead of the bare id,
  falling back to the id when the name cannot be resolved.
- All code, help text, messages and documentation are now in en-US.

## [0.1.0] - 2026-08-18

### Added

- `gcpuse`: GCP context status, `--list`, and configuration switching with CLI + ADC
  login plus ADC quota project alignment.
- `--no-login` and `--no-adc` flags to switch configuration without re-authenticating.
- The `xwx` package layout (`xwx.cli` for commands, `xwx.core` for shared code) plus CI
  and PyPI publishing workflows.
