from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Sequence

from tools.message_standards import validate_branch_name


def _run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _current_branch() -> str | None:
    result = _run_git("branch", "--show-current")
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "unable to determine current branch"
        )
    branch = result.stdout.strip()
    return branch or None


def _upstream_ref() -> str | None:
    result = _run_git(
        "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
    )
    if result.returncode != 0:
        return None
    upstream = result.stdout.strip()
    return upstream or None


def _current_head_sha() -> str:
    result = _run_git("rev-parse", "HEAD")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unable to resolve HEAD")
    return result.stdout.strip()


def _ensure_commit_available(commit_sha: str) -> None:
    result = _run_git("cat-file", "-e", f"{commit_sha}^{{commit}}")
    if result.returncode == 0:
        return
    raise RuntimeError(
        "required PR base commit is not available locally; fetch the base branch "
        "before pushing"
    )


def _load_open_pr_metadata() -> tuple[str, str, str] | None:
    if shutil.which("gh") is None:
        raise RuntimeError(
            "`gh` is required to validate open pull request metadata before push"
        )

    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            "--json",
            "title,body,baseRefOid",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "no pull requests found" in stderr.lower():
            return None
        raise RuntimeError(
            stderr or "unable to load pull request metadata with `gh pr view`"
        )

    payload = json.loads(result.stdout)
    title = payload.get("title")
    body = payload.get("body")
    base_ref_oid = payload.get("baseRefOid")
    if (
        not isinstance(title, str)
        or not isinstance(body, str)
        or not isinstance(base_ref_oid, str)
    ):
        raise RuntimeError("`gh pr view` returned incomplete pull request metadata")
    return title, body, base_ref_oid


def _validate_pr_metadata(
    *, branch_name: str, title: str, body: str, base_sha: str, head_sha: str
) -> int:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.validate_pr_metadata",
            "--branch-name",
            branch_name,
            "--title",
            title,
            "--body",
            body,
            "--base-sha",
            base_sha,
            "--head-sha",
            head_sha,
        ],
        check=False,
    ).returncode


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    branch = _current_branch()
    if branch is None:
        return 0

    try:
        branch_errors = validate_branch_name(branch)
        if branch_errors:
            raise RuntimeError("; ".join(branch_errors))
        if _upstream_ref() is None:
            return 0
        metadata = _load_open_pr_metadata()
        if metadata is None:
            return 0
        title, body, base_sha = metadata
        _ensure_commit_available(base_sha)
        return _validate_pr_metadata(
            branch_name=branch,
            title=title,
            body=body,
            base_sha=base_sha,
            head_sha=_current_head_sha(),
        )
    except RuntimeError as error:
        print(
            f"pre-push pull request metadata validation failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
