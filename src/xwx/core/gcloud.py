"""Wrapper fino em cima do ``gcloud`` CLI."""

from __future__ import annotations

from xwx.core import shell

BINARY = "gcloud"

INSTALL_HINT = "Instale o Google Cloud SDK: https://cloud.google.com/sdk/docs/install"

# valores que o gcloud usa para dizer "nao definido"
_UNSET = {"", "(unset)", "(nenhum)"}


class GcloudError(RuntimeError):
    """Um comando do gcloud falhou."""


def ensure_installed() -> str:
    return shell.require(BINARY, INSTALL_HINT)


def _value(argv: list[str]) -> str | None:
    out = shell.capture([BINARY, *argv])
    if out is None or out in _UNSET:
        return None
    return out


def config_get(key: str) -> str | None:
    """Valor de ``gcloud config get-value <key>`` ou ``None`` se nao definido."""
    return _value(["config", "get-value", key])


def account() -> str | None:
    return config_get("account")


def project() -> str | None:
    return config_get("project")


def configurations() -> list[str]:
    out = shell.capture(
        [BINARY, "config", "configurations", "list", "--format=value(name)"]
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
        raise GcloudError(f"nao foi possivel ativar a configuration '{name}'.")


def auth_login() -> None:
    proc = shell.run([BINARY, "auth", "login"])
    if proc.returncode != 0:
        raise GcloudError("o login da CLI (gcloud auth login) falhou.")


def auth_adc_login() -> None:
    proc = shell.run([BINARY, "auth", "application-default", "login"])
    if proc.returncode != 0:
        raise GcloudError(
            "o login da ADC (gcloud auth application-default login) falhou."
        )


def set_adc_quota_project(project_id: str) -> bool:
    """Alinha o quota project da ADC. Devolve ``False`` se o gcloud recusar."""
    proc = shell.run(
        [BINARY, "auth", "application-default", "set-quota-project", project_id],
        capture=True,
    )
    return proc.returncode == 0
