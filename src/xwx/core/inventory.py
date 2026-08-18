"""Best-effort inventory of what exists inside a GCP project.

There is no single cheap call that lists every resource in a project (Cloud
Asset Inventory does that, but it needs its own API enabled and its own role).
So this module works the other way around: it asks which APIs the project has
enabled, then probes only the services that are actually on. A service whose
API is off cannot hold resources, so skipping it costs nothing and saves a
round trip that would otherwise fail.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple

from xwx.core import gcloud, shell

# how many probes may talk to Google at the same time
MAX_WORKERS = 8

# a probe is a listing, not a report — it should not take longer than this
PROBE_TIMEOUT = 45.0


def _lines(argv: Sequence[str]) -> list[str] | None:
    return shell.capture_lines(argv, env=gcloud.NO_PROMPT_ENV, timeout=PROBE_TIMEOUT)


def _bq_datasets(argv: Sequence[str]) -> list[str] | None:
    """``bq ls`` speaks JSON rather than gcloud's --format=value()."""
    out = shell.capture(argv, env=gcloud.NO_PROMPT_ENV, timeout=PROBE_TIMEOUT)
    if out is None:
        return []  # bq exits 0 with no output when there are no datasets
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return None
    names = []
    for entry in payload:
        ref = entry.get("datasetReference") or {}
        name = ref.get("datasetId") or entry.get("id")
        if name:
            names.append(str(name).split(":")[-1])
    return names


class Probe(NamedTuple):
    """One service worth listing, and how to list it."""

    label: str
    api: str
    argv: tuple[str, ...]  # "{project}" is substituted with the project id
    binary: str = gcloud.BINARY
    runner: Callable[[Sequence[str]], list[str] | None] = _lines

    def command(self, project_id: str) -> list[str]:
        return [self.binary, *(arg.format(project=project_id) for arg in self.argv)]


# Curated on purpose: the services people actually deploy into, each with a
# listing that is cheap and needs no region argument.
PROBES: tuple[Probe, ...] = (
    Probe("Compute instances", "compute.googleapis.com",
          ("compute", "instances", "list", "--format=value(name)", "--project={project}")),
    Probe("VPC networks", "compute.googleapis.com",
          ("compute", "networks", "list", "--format=value(name)", "--project={project}")),
    Probe("GKE clusters", "container.googleapis.com",
          ("container", "clusters", "list", "--format=value(name)", "--project={project}")),
    Probe("Cloud Run", "run.googleapis.com",
          ("run", "services", "list", "--format=value(metadata.name)", "--project={project}")),
    Probe("Cloud Functions", "cloudfunctions.googleapis.com",
          ("functions", "list", "--format=value(name)", "--project={project}")),
    Probe("Cloud SQL", "sqladmin.googleapis.com",
          ("sql", "instances", "list", "--format=value(name)", "--project={project}")),
    Probe("Storage buckets", "storage.googleapis.com",
          ("storage", "buckets", "list", "--format=value(name)", "--project={project}")),
    Probe("BigQuery datasets", "bigquery.googleapis.com",
          ("--format=json", "--project_id={project}", "ls"),
          binary="bq", runner=_bq_datasets),
    Probe("Firestore databases", "firestore.googleapis.com",
          ("firestore", "databases", "list", "--format=value(name)", "--project={project}")),
    Probe("Pub/Sub topics", "pubsub.googleapis.com",
          ("pubsub", "topics", "list", "--format=value(name)", "--project={project}")),
    Probe("Artifact Registry", "artifactregistry.googleapis.com",
          ("artifacts", "repositories", "list", "--format=value(name)", "--project={project}")),
    Probe("Secrets", "secretmanager.googleapis.com",
          ("secrets", "list", "--format=value(name)", "--project={project}")),
    Probe("Service accounts", "iam.googleapis.com",
          ("iam", "service-accounts", "list", "--format=value(email)", "--project={project}")),
    Probe("Cloud DNS zones", "dns.googleapis.com",
          ("dns", "managed-zones", "list", "--format=value(name)", "--project={project}")),
    Probe("Build triggers", "cloudbuild.googleapis.com",
          ("builds", "triggers", "list", "--format=value(name)", "--project={project}")),
)


class Finding(NamedTuple):
    """What one probe found."""

    label: str
    names: tuple[str, ...] = ()
    denied: bool = False  # the call failed: no permission, or the API misbehaved

    @property
    def count(self) -> int:
        return len(self.names)


class Inventory(NamedTuple):
    project_id: str
    services: tuple[str, ...]
    findings: tuple[Finding, ...]  # probes that ran, in PROBES order
    skipped: tuple[str, ...]  # labels whose API is disabled


def _short_name(value: str) -> str:
    """Trim the parts that are the same on every row and carry no information.

    ``projects/x/databases/y`` reads better as ``y``, and a service account is
    recognisable by its local part alone.
    """
    name = value.rsplit("/", 1)[-1]
    if name.endswith(".gserviceaccount.com"):
        return name.split("@", 1)[0]
    return name


def _probe(probe: Probe, project_id: str) -> Finding:
    names = probe.runner(probe.command(project_id))
    if names is None:
        return Finding(probe.label, denied=True)
    return Finding(probe.label, tuple(_short_name(name) for name in names))


def scan(project_id: str, services: Sequence[str]) -> Inventory:
    """Probe every service in ``services``, in parallel."""
    enabled = set(services)
    wanted = [probe for probe in PROBES if probe.api in enabled]
    skipped = tuple(probe.label for probe in PROBES if probe.api not in enabled)

    findings: tuple[Finding, ...] = ()
    if wanted:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            findings = tuple(pool.map(lambda p: _probe(p, project_id), wanted))

    return Inventory(project_id, tuple(services), findings, skipped)
