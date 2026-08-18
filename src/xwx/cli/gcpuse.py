"""gcpuse — troca de contexto GCP (gcloud CLI + ADC do Terraform).

    gcpuse                mostra em qual configuration/conta/projeto voce esta
    gcpuse <nome>         ativa a configuration e refaz o login (CLI + ADC)
    gcpuse --list         lista as configurations disponiveis
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from xwx import __version__
from xwx.core import gcloud, ui
from xwx.core.shell import CommandNotFound

PROG = "gcpuse"


def _print_configurations(names: Sequence[str], active: str | None = None) -> None:
    if not names:
        ui.info("Nenhuma configuration encontrada.")
        ui.info("Crie uma com: gcloud config configurations create <nome>")
        return
    ui.info("configurations disponiveis:")
    for name in names:
        marker = "* " if name == active else "  "
        line = f"  {marker}{name}"
        ui.info(ui.paint(line, "cyan") if name == active else line)


def _status() -> int:
    account = gcloud.account()
    if account is None:
        ui.info("GCP: nenhuma conta logada.")
        _print_configurations(gcloud.configurations(), gcloud.active_configuration())
        return 0

    ui.kv("GCP configuration", gcloud.active_configuration())
    ui.kv("GCP conta", account)
    ui.kv("GCP projeto", gcloud.project())
    return 0


def _list() -> int:
    _print_configurations(gcloud.configurations(), gcloud.active_configuration())
    return 0


def _switch(name: str, *, do_login: bool, do_adc: bool) -> int:
    names = gcloud.configurations()
    if names and name not in names:
        ui.error(f"configuration '{name}' nao existe.")
        _print_configurations(names, gcloud.active_configuration())
        return 1

    gcloud.activate(name)

    if do_login:
        gcloud.auth_login()
    if do_adc:
        gcloud.auth_adc_login()

    project = gcloud.project()
    if project and do_adc and not gcloud.set_adc_quota_project(project):
        ui.warn(f"nao foi possivel definir o quota project da ADC como '{project}'.")

    ui.info("")
    ui.info(ui.paint(f"-> Ativo: {name}", "green", "bold"))
    ui.kv("  conta", gcloud.account())
    ui.kv("  projeto", project)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Troca de contexto GCP (gcloud CLI + ADC do Terraform) "
            "por configuration nomeada."
        ),
        epilog=(
            "exemplos:\n"
            f"  {PROG}                  status da configuration/conta/projeto atual\n"
            f"  {PROG} staging          ativa 'staging' e refaz login (CLI + ADC)\n"
            f"  {PROG} staging --no-login   so troca de configuration\n"
            f"  {PROG} --list           lista as configurations disponiveis"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "configuration",
        nargs="?",
        help="nome da configuration do gcloud a ativar (sem argumento: mostra o status)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_configs",
        help="lista as configurations disponiveis e sai",
    )
    parser.add_argument(
        "--no-login",
        action="store_true",
        help="apenas ativa a configuration, sem refazer login algum",
    )
    parser.add_argument(
        "--no-adc",
        action="store_true",
        help="faz o login da CLI, mas nao o da ADC (application-default)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s (xwx-tools) {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        gcloud.ensure_installed()

        if args.list_configs:
            return _list()
        if args.configuration is None:
            return _status()
        return _switch(
            args.configuration,
            do_login=not args.no_login,
            do_adc=not (args.no_login or args.no_adc),
        )
    except CommandNotFound as exc:
        ui.error(str(exc))
        return 127
    except gcloud.GcloudError as exc:
        ui.error(str(exc))
        return 1
    except KeyboardInterrupt:
        ui.info("")
        ui.warn("cancelado.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
