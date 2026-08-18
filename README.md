# xwx-tools

A pip-installable command-line toolbox. One package, many commands — each script
ships as its own executable on your PATH.

| Command  | What it does |
| -------- | ------------ |
| `gcpuse` | Switch GCP context (gcloud CLI + Terraform ADC) by named configuration |

## Install

Recommended (isolated, without polluting your system Python):

```bash
pipx install xwx-tools
```

Or inside any virtualenv:

```bash
pip install xwx-tools
```

Upgrade with `pipx upgrade xwx-tools` (or `pip install -U xwx-tools`).

## gcpuse

Requires the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) on PATH.

```bash
gcpuse                       # which configuration / account / project am I on?
gcpuse --list                # list the available configurations (* = active)
gcpuse --projects            # list the projects visible to the current account (* = current)
gcpuse staging               # activate 'staging' and re-login (CLI + ADC)
gcpuse -p my-project-123     # switch project, same account, no re-login
gcpuse staging -p proj-123   # activate, re-login, then use that project
gcpuse staging --no-login    # only switch configuration, no login
gcpuse staging --no-adc      # CLI login, but leave the ADC alone
```

### Switching account vs. switching project

Two different jobs, two different commands:

- **`gcpuse <configuration>`** — different account (or a fresh set of credentials). It
  activates the configuration and re-runs both logins, which opens a browser.
- **`gcpuse -p <project-id>`** — different project under the *same* account. It only
  repoints the active configuration and realigns the ADC quota project. No browser, no
  re-authentication.

`gcpuse <name>` runs, in order:

1. `gcloud config configurations activate <name>`
2. `gcloud auth login` — CLI credentials
3. `gcloud auth application-default login` — ADC, which is what Terraform uses
4. `gcloud auth application-default set-quota-project <project of the configuration>`

`gcpuse -p <project-id>` runs:

1. `gcloud config set project <project-id>` on the active configuration
2. `gcloud auth application-default set-quota-project <project-id>`

Projects are shown as `Display Name (project-id)`. Resolving the display name needs the
Cloud Resource Manager API and permission to read the project; when that is unavailable
the bare project id is shown instead, and switching still works.

Exit codes: `0` success, `1` gcloud error (or unknown configuration), `127` gcloud not
installed, `130` cancelled with Ctrl-C.

### Creating a configuration

```bash
gcloud config configurations create staging
gcloud config set project my-staging-project
```

## Development

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

## Adding a new tool

1. Create `src/xwx/cli/mytool.py` with a `main(argv=None) -> int` function.
2. Register it in `pyproject.toml`:

   ```toml
   [project.scripts]
   mytool = "xwx.cli.mytool:main"
   ```

3. Anything reusable (process execution, terminal output, wrappers around external CLIs)
   belongs in `src/xwx/core/`.
4. Add tests under `tests/`, bump `__version__` in `src/xwx/__init__.py`, push a `vX.Y.Z`
   tag, and CI publishes it.

## Releasing

`.github/workflows/publish.yml` publishes to PyPI through
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) whenever a `v*` tag is
pushed. The trusted publisher is configured once on pypi.org → *Publishing* with owner
`welmends`, repository `xwx-tools`, workflow `publish.yml`, environment `pypi`.

```bash
# bump __version__ and CHANGELOG.md first
git tag v0.2.0 && git push origin v0.2.0
```

## License

MIT — see [LICENSE](LICENSE).
