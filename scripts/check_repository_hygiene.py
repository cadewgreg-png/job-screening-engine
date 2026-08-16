"""Reject tracked files that violate the repository's public-data boundary."""

from __future__ import annotations

from pathlib import PurePosixPath
import subprocess


BLOCKED_DIRECTORIES = frozenset(
    {
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "applications",
        "candidates",
        "data",
        "graphify-out",
        "htmlcov",
        "resumes",
        "venv",
    }
)
BLOCKED_FILENAMES = frozenset(
    {
        ".coverage",
        "id_ed25519",
        "id_rsa",
    }
)
BLOCKED_SUFFIXES = frozenset(
    {
        ".csv",
        ".db",
        ".jks",
        ".key",
        ".keystore",
        ".log",
        ".p12",
        ".pem",
        ".pfx",
        ".sqlite",
        ".sqlite3",
        ".tsv",
        ".xls",
        ".xlsx",
    }
)


def violation_reason(path: PurePosixPath) -> str | None:
    """Return the policy violated by a tracked path, if any."""

    lowered_parts = tuple(part.lower() for part in path.parts)
    if BLOCKED_DIRECTORIES.intersection(lowered_parts):
        return "local-data or generated directory"

    name = path.name.lower()
    if name in BLOCKED_FILENAMES:
        return "local or credential filename"
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "environment file"
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        return "sensitive or local-data file type"
    return None


def tracked_paths() -> tuple[PurePosixPath, ...]:
    """Read repository paths from Git without inspecting file contents."""

    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return tuple(
        PurePosixPath(raw.decode("utf-8"))
        for raw in result.stdout.split(b"\0")
        if raw
    )


def main() -> int:
    violations = [
        (path, reason)
        for path in tracked_paths()
        if (reason := violation_reason(path)) is not None
    ]
    if not violations:
        print("Repository hygiene check passed.")
        return 0

    print("Repository hygiene check failed. Remove these tracked files:")
    for path, reason in violations:
        print(f"- {path}: {reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
