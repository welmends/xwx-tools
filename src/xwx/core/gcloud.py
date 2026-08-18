"""A thin wrapper around the ``gcloud`` CLI."""

from __future__ import annotations

from typing import NamedTuple

from xwx.core import shell

BINARY = "gcloud"

INSTALL_HINT = "Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"

# gcloud offers to enable a disabled API interactively; a read must never block on
# that prompt, so every non-interactive call runs with prompts turned off.
NO_PROMPT_ENV = {"CLOUDSDK_CORE_DISABLE_PROMPTS": "1"}

# a single read should never hold the terminal hostage
READ_TIMEOUT = 30.0

# values gcloud uses to mean "not set"
_UNSET = {"", "(unset)", "(none)"}


class GcloudError(RuntimeError):
    """A gcloud command failed."""


class Project(NamedTuple):
    """A project as reported by ``gcloud projects list``."""

    project_id: str
    name: str | None = None

    def label(self) -> str:
        """``Display Name (project-id)``, or just the id when there is no name."""
        if self.name and self.name != self.project_id:
            return f"{self.name} ({self.project_id})"
        return self.project_id


def ensure_installed() -> str:
    return shell.require(BINARY, INSTALL_HINT)


def _value(argv: list[str]) -> str | None:
    out = shell.capture([BINARY, *argv], env=NO_PROMPT_ENV, timeout=READ_TIMEOUT)
    if out is None or out in _UNSET:
        return None
    return out


def config_get(key: str) -> str | None:
    """Value of ``gcloud config get-value <key>``, or ``None`` when unset."""
    return _value(["config", "get-value", key])


def account() -> str | None:
    return config_get("account")


def project() -> str | None:
    return config_get("project")


def configurations() -> list[str]:
    out = shell.capture(
        [BINARY, "config", "configurations", "list", "--format=value(name)"],
        env=NO_PROMPT_ENV,
        timeout=READ_TIMEOUT,
    )
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def active_configuration() -> str | None:
    return _value(
        [
            "config",
            "configurations",
            "list",
            "--filter=is_active=true",
            "--format=value(name)",
        ]
    )


def activate(name: str) -> None:
    proc = shell.run([BINARY, "config", "configurations", "activate", name])
    if proc.returncode != 0:
        raise GcloudError(f"could not activate configuration '{name}'.")


def auth_login() -> None:
    proc = shell.run([BINARY, "auth", "login"])
    if proc.returncode != 0:
        raise GcloudError("the CLI login (gcloud auth login) failed.")


def auth_adc_login() -> None:
    proc = shell.run([BINARY, "auth", "application-default", "login"])
    if proc.returncode != 0:
        raise GcloudError("the ADC login (gcloud auth application-default login) failed.")


def set_adc_quota_project(project_id: str) -> bool:
    """Align the ADC quota project. Returns ``False`` if gcloud refuses."""
    proc = shell.run(
        [BINARY, "auth", "application-default", "set-quota-project", project_id],
        capture=True,
    )
    return proc.returncode == 0


def set_project(project_id: str) -> None:
    """Set the project of the active configuration."""
    proc = shell.run([BINARY, "config", "set", "project", project_id], capture=True)
    if proc.returncode != 0:
        raise GcloudError(f"could not set the project to '{project_id}'.")


def project_name(project_id: str) -> str | None:
    """Display name of a project, or ``None`` when it cannot be resolved.

    Resolving needs the Cloud Resource Manager API and permission to read the
    project, so a ``None`` here means "unknown", never "does not exist".
    """
    return _value(["projects", "describe", project_id, "--format=value(name)"])


def describe_project(project_id: str) -> Project:
    """The project with its display name resolved (best effort)."""
    return Project(project_id, project_name(project_id))


def projects() -> list[Project]:
    """Projects visible to the current account, sorted by id."""
    out = shell.capture(
        [
            BINARY,
            "projects",
            "list",
            "--sort-by=projectId",
            "--format=value(projectId,name)",
        ],
        env=NO_PROMPT_ENV,
        timeout=READ_TIMEOUT,
    )
    if not out:
        return []
    found = []
    for line in out.splitlines():
        if not line.strip():
            continue
        project_id, _, name = line.partition("\t")
        found.append(Project(project_id.strip(), name.strip() or None))
    return found


def enabled_services(project_id: str | None = None) -> list[str] | None:
    """APIs enabled on the project, or ``None`` when they cannot be listed."""
    argv = [BINARY, "services", "list", "--enabled", "--format=value(config.name)"]
    if project_id:
        argv.append(f"--project={project_id}")
    return shell.capture_lines(argv, env=NO_PROMPT_ENV, timeout=READ_TIMEOUT)


def billing_enabled(project_id: str) -> bool | None:
    """Whether billing is active, or ``None`` when it cannot be read."""
    out = shell.capture(
        [
            BINARY,
            "billing",
            "projects",
            "describe",
            project_id,
            "--format=value(billingEnabled)",
        ],
        env=NO_PROMPT_ENV,
        timeout=READ_TIMEOUT,
    )
    if out is None:
        return None
    return out.strip().lower() == "true"
