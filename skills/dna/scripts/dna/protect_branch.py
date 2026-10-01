"""DNA branch protection helper (manifest Law 9).

Marks the long-lived branches (`main`, `feat/<feature-slug>`) as protected so
direct pushes are blocked and merges happen only through `dna-close` pull
requests. Applies protection through the repository host API when a supported
CLI is available and falls back to printed manual instructions otherwise.

Providers:
    github — via the `gh` CLI (classic branch protection API).
    gitlab — via the `glab` CLI (protected branches API).
    manual — no API call; prints the exact manual steps.

Usage:
    python scripts/dna/protect_branch.py --feature my-feature
    python scripts/dna/protect_branch.py --branch main --branch feat/my-feature
    python scripts/dna/protect_branch.py --feature my-feature --check
    python scripts/dna/protect_branch.py --feature my-feature --dry-run
    python scripts/dna/protect_branch.py --feature my-feature --provider manual

Exit codes:
    0 — protection applied, already in place, or manual instructions printed
    1 — the host API call failed
    2 — environment error (not a git repository, no origin remote)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

from common import PROJECT_ROOT, now_iso, write_json  # type: ignore[import-not-found]

GITHUB_PROTECTION_PAYLOAD = {
    "required_status_checks": None,
    "enforce_admins": False,
    "required_pull_request_reviews": {
        "dismiss_stale_reviews": False,
        "require_code_owner_reviews": False,
        "required_approving_review_count": 0,
    },
    "restrictions": None,
    "allow_force_pushes": False,
    "allow_deletions": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", help="Feature slug; protects main + feat/<slug>.")
    parser.add_argument(
        "--branch",
        action="append",
        default=[],
        help="Branch to protect (repeatable).",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "github", "gitlab", "manual"],
        default="auto",
        help="Repository host; auto detects from the origin remote.",
    )
    parser.add_argument("--check", action="store_true", help="Only report current protection.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report path.")
    return parser.parse_args()


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def origin_path() -> tuple[str, str, str]:
    """Return (host, owner_path, web_url) parsed from the origin remote."""
    url = git("remote", "get-url", "origin")
    if url.startswith("git@"):
        host, _, path = url[4:].partition(":")
    else:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        path = parsed.path.lstrip("/")
    path = path.removesuffix(".git")
    if not host or not path:
        raise ValueError(f"cannot parse origin remote: {url}")
    return host, path, url


def detect_provider(host: str) -> str:
    if "github" in host:
        return "github"
    if "gitlab" in host:
        return "gitlab"
    return "manual"


def run(cmd: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        input=input_text,
    )


def branch_exists_locally(branch: str) -> bool:
    proc = run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"])
    return proc.returncode == 0


def github_state(owner_path: str, branch: str) -> tuple[str, str]:
    """Return (status, detail) for one GitHub branch."""
    ref = urllib.parse.quote(branch, safe="")
    proc = run(["gh", "api", f"repos/{owner_path}/branches/{ref}/protection"])
    if proc.returncode == 0:
        return "protected", "protection already configured"
    if "Branch not protected" in proc.stderr or "404" in proc.stderr:
        return "unprotected", "no protection configured"
    return "error", proc.stderr.strip() or proc.stdout.strip()


def github_apply(owner_path: str, branch: str, *, dry_run: bool) -> tuple[str, str]:
    ref = urllib.parse.quote(branch, safe="")
    payload = json.dumps(GITHUB_PROTECTION_PAYLOAD)
    cmd = [
        "gh",
        "api",
        "--method",
        "PUT",
        f"repos/{owner_path}/branches/{ref}/protection",
        "--input",
        "-",
    ]
    if dry_run:
        return "dry-run", " ".join(cmd) + " <<< " + payload
    proc = run(cmd, input_text=payload)
    if proc.returncode == 0:
        return "applied", "protection enabled (PR required, force push and deletion blocked)"
    return "error", proc.stderr.strip() or proc.stdout.strip()


def gitlab_apply(owner_path: str, branch: str, *, dry_run: bool) -> tuple[str, str]:
    project = urllib.parse.quote(owner_path, safe="")
    cmd = [
        "glab",
        "api",
        f"projects/{project}/protected_branches",
        "-X",
        "POST",
        "-f",
        f"name={branch}",
        "-f",
        "push_access_level=40",
        "-f",
        "merge_access_level=40",
    ]
    if dry_run:
        return "dry-run", " ".join(cmd)
    proc = run(cmd)
    if proc.returncode == 0:
        return "applied", "protected branch created (maintainers only)"
    stderr = proc.stderr.strip() or proc.stdout.strip()
    if "already protected" in stderr.lower() or "409" in stderr:
        return "protected", "protection already configured"
    return "error", stderr


def manual_hint(host: str, owner_path: str, branch: str) -> str:
    if "github" in host:
        return (
            f"GitHub UI: https://github.com/{owner_path}/settings/branches — "
            f"add a branch protection rule for '{branch}': require a pull request, "
            "block force pushes and deletions"
        )
    if "gitlab" in host:
        return (
            f"GitLab UI: https://{host}/{owner_path}/-/settings/repository — "
            f"add protected branch '{branch}' (maintainers only)"
        )
    return f"Protect branch '{branch}' in the repository host settings (no PR, no direct push)"


def main() -> int:
    args = parse_args()

    if not args.feature and not args.branch:
        print("ERROR: provide --feature or at least one --branch", file=sys.stderr)
        return 2

    branches = list(args.branch)
    if args.feature:
        branches = ["main", f"feat/{args.feature}", *branches]

    try:
        host, owner_path, remote = origin_path()
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    provider = args.provider
    if provider == "auto":
        provider = detect_provider(host)

    results = []
    exit_code = 0
    for branch in branches:
        if not branch_exists_locally(branch):
            results.append(
                {
                    "branch": branch,
                    "status": "warning",
                    "detail": "branch does not exist locally; protect it once it is pushed",
                }
            )
            continue

        if provider == "manual":
            status, detail = "manual", manual_hint(host, owner_path, branch)
        elif provider == "github":
            if shutil.which("gh") is None:
                status, detail = "manual", "gh CLI not found. " + manual_hint(host, owner_path, branch)
            elif args.check:
                status, detail = github_state(owner_path, branch)
            else:
                status, detail = github_apply(owner_path, branch, dry_run=args.dry_run)
        else:  # gitlab
            if shutil.which("glab") is None:
                status, detail = "manual", "glab CLI not found. " + manual_hint(host, owner_path, branch)
            else:
                status, detail = gitlab_apply(owner_path, branch, dry_run=args.dry_run)

        if status == "error":
            exit_code = 1
        results.append({"branch": branch, "status": status, "detail": detail})

    report = {
        "check": "protect_branch",
        "provider": provider,
        "remote": remote,
        "mode": "check" if args.check else "apply",
        "results": results,
        "checked_at": now_iso(),
    }
    if args.output:
        write_json(args.output, report)

    for item in results:
        print(f"{item['branch']}: {item['status']} — {item['detail']}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
