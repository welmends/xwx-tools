"""gcpuse — switch GCP context (gcloud CLI + Terraform ADC).

    gcpuse                 show the current configuration / account / project
    gcpuse <name>          activate a configuration and re-login (CLI + ADC)
    gcpuse -p <project>    switch project inside the active configuration
    gcpuse --list          list the available configurations
    gcpuse --projects      list the projects visible to the current account
    gcpuse --resources     list what exists inside the active project
"""

from __future__ import annotations

import argparse
import sys

from xwx import __version__
from xwx.core import gcloud, inventory, ui
from xwx.core.shell import CommandNotFound

PROG = "gcpuse"


def _print_configurations(names: list[str], active: str | None = None) -> None:
    if not names:
        ui.info("No configurations found.")
        ui.info("Create one with: gcloud config configurations create <name>")
        return
    ui.info("available configurations:")
    for name in names:
        marker = "* " if name == active else "  "
        line = f"  {marker}{name}"
        ui.info(ui.paint(line, "cyan") if name == active else line)


def _project_label(project_id: str | None) -> str | None:
    """``Display Name (project-id)`` when the name can be resolved."""
    if project_id is None:
        return None
    return gcloud.describe_project(project_id).label()


def _status() -> int:
    account = gcloud.account()
    if account is None:
        ui.info("GCP: no account logged in.")
        _print_configurations(gcloud.configurations(), gcloud.active_configuration())
        return 0

    ui.kv("GCP configuration", gcloud.active_configuration())
    ui.kv("GCP account", account)
    ui.kv("GCP project", _project_label(gcloud.project()))
    return 0


def _list_configurations() -> int:
    _print_configurations(gcloud.configurations(), gcloud.active_configuration())
    return 0


def _list_projects() -> int:
    projects = gcloud.projects()
    if not projects:
        ui.info("No projects visible to this account.")
        ui.info("Log in first with: gcpuse <configuration>")
        return 0
    current = gcloud.project()
    ui.info("available projects:")
    for project in projects:
        marker = "* " if project.project_id == current else "  "
        line = f"  {marker}{project.label()}"
        ui.info(ui.paint(line, "cyan") if project.project_id == current else line)
    return 0


# how many resource names to show before collapsing into "+N more"
_NAME_PREVIEW = 3


def _preview(names: tuple[str, ...]) -> str:
    shown = ", ".join(names[:_NAME_PREVIEW])
    extra = len(names) - _NAME_PREVIEW
    return f"{shown}, +{extra} more" if extra > 0 else shown


def _print_finding(finding: inventory.Finding, width: int) -> None:
    label = finding.label.ljust(width)
    if finding.denied:
        ui.info(f"  {label} {ui.paint('no access', 'yellow')}")
    elif finding.count == 0:
        ui.info(f"  {label} {ui.paint('-', 'dim')}")
    else:
        count = str(finding.count).rjust(3)
        ui.info(f"  {label} {count}  {ui.paint(_preview(finding.names), 'dim')}")


def _resources() -> int:
    """List what exists inside the active project."""
    if gcloud.account() is None:
        ui.error("no account logged in.")
        ui.info(f"Log in first with: {PROG} <configuration>")
        return 1

    project_id = gcloud.project()
    if project_id is None:
        ui.error("no project set on the active configuration.")
        ui.info(f"Pick one with: {PROG} -p <project-id>")
        return 1

    services = gcloud.enabled_services(project_id)
    if services is None:
        ui.error(f"could not list the enabled APIs of '{project_id}'.")
        ui.info("You may lack permission on this project, or it may not exist.")
        return 1

    billing = gcloud.billing_enabled(project_id)
    ui.kv("Project", _project_label(project_id))
    ui.kv("Billing", {True: "enabled", False: "disabled", None: "unknown"}[billing])
    ui.kv("Enabled APIs", str(len(services)))

    found = inventory.scan(project_id, services)
    ui.info("")
    if not found.findings:
        ui.info("No probeable service is enabled on this project.")
        return 0

    width = max(len(f.label) for f in found.findings)
    ui.info("resources")
    for finding in found.findings:
        _print_finding(finding, width)

    if found.skipped:
        ui.info("")
        ui.info(ui.paint(f"not probed (API off): {', '.join(found.skipped)}", "dim"))
    return 0


def _apply_project(project_id: str) -> None:
    """Point the active configuration at ``project_id`` and realign the ADC."""
    if gcloud.project_name(project_id) is None:
        ui.warn(
            f"could not verify project '{project_id}' "
            "(wrong id, or no permission to read it) — setting it anyway."
        )
    gcloud.set_project(project_id)


def _align_adc(project_id: str) -> None:
    if not gcloud.set_adc_quota_project(project_id):
        ui.warn(
            f"could not set the ADC quota project to '{project_id}'. "
            f"Run '{PROG} <configuration>' to create ADC credentials."
        )


def _summary(configuration: str | None) -> None:
    project_id = gcloud.project()
    ui.info("")
    ui.info(ui.paint(f"-> Active: {configuration or '(none)'}", "green", "bold"))
    ui.kv("  account", gcloud.account())
    ui.kv("  project", _project_label(project_id))


def _switch(
    name: str,
    *,
    do_login: bool,
    do_adc: bool,
    project_id: str | None = None,
) -> int:
    names = gcloud.configurations()
    if names and name not in names:
        ui.error(f"configuration '{name}' does not exist.")
        _print_configurations(names, gcloud.active_configuration())
        return 1

    gcloud.activate(name)

    if do_login:
        gcloud.auth_login()
    if do_adc:
        gcloud.auth_adc_login()
    if project_id is not None:
        _apply_project(project_id)

    current = gcloud.project()
    if current and (do_adc or project_id is not None):
        _align_adc(current)

    _summary(name)
    return 0


def _switch_project(project_id: str) -> int:
    """Switch project without touching credentials (same account, same config)."""
    if gcloud.account() is None:
        ui.error("no account logged in.")
        ui.info(f"Log in first with: {PROG} <configuration>")
        return 1

    _apply_project(project_id)
    _align_adc(project_id)
    _summary(gcloud.active_configuration())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Switch GCP context (gcloud CLI + Terraform ADC) by named configuration."
        ),
        epilog=(
            "examples:\n"
            f"  {PROG}                       status of the current configuration\n"
            f"  {PROG} staging               activate 'staging' and re-login (CLI + ADC)\n"
            f"  {PROG} -p my-project-123     switch project, same account, no re-login\n"
            f"  {PROG} staging -p proj-123   activate, re-login, then use that project\n"
            f"  {PROG} --list                list the available configurations\n"
            f"  {PROG} --projects            list the projects of the current account\n"
            f"  {PROG} --resources           list what exists inside the active project"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "configuration",
        nargs="?",
        help="name of the gcloud configuration to activate (omit to show the status)",
    )
    parser.add_argument(
        "-p",
        "--project",
        metavar="PROJECT_ID",
        help="switch to this project (no re-login when used on its own)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_configs",
        help="list the available configurations and exit",
    )
    parser.add_argument(
        "--projects",
        action="store_true",
        dest="list_projects",
        help="list the projects visible to the current account and exit",
    )
    parser.add_argument(
        "-r",
        "--resources",
        action="store_true",
        help="list what exists inside the active project (probes the enabled APIs)",
    )
    parser.add_argument(
        "--no-login",
        action="store_true",
        help="only activate the configuration, skipping every login",
    )
    parser.add_argument(
        "--no-adc",
        action="store_true",
        help="log in the CLI but skip the ADC (application-default) login",
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
            return _list_configurations()
        if args.list_projects:
            return _list_projects()

        if args.configuration is not None:
            code = _switch(
                args.configuration,
                do_login=not args.no_login,
                do_adc=not (args.no_login or args.no_adc),
                project_id=args.project,
            )
        elif args.project is not None:
            code = _switch_project(args.project)
        else:
            code = 0
        if code != 0:
            return code

        # --resources composes: switch first, then report on where you landed
        if args.resources:
            if args.configuration is not None or args.project is not None:
                ui.info("")
            return _resources()
        if args.configuration is None and args.project is None:
            return _status()
        return 0
    except CommandNotFound as exc:
        ui.error(str(exc))
        return 127
    except gcloud.GcloudError as exc:
        ui.error(str(exc))
        return 1
    except KeyboardInterrupt:
        ui.info("")
        ui.warn("cancelled.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
