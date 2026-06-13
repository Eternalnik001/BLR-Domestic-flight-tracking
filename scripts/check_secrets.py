#!/usr/bin/env python3
"""Block secrets from being committed.

Used as a git pre-commit hook (see .githooks/pre-commit) and runnable by hand:
    python scripts/check_secrets.py            # scan staged changes
    python scripts/check_secrets.py --all      # scan all tracked files

Exits non-zero (blocking the commit) if it finds a leaked key, a tracked .env,
or a Supabase *service_role* key shipped in the frontend.
"""
from __future__ import annotations

import re
import subprocess
import sys

# Files that must never be committed at all.
FORBIDDEN_PATHS = re.compile(r"(^|/)\.env$")

# High-signal secret shapes. The anon/publishable Supabase key is intentionally
# NOT here — it's public by design and safe in web/.
SECRET_PATTERNS = [
    ("Travelpayouts/SerpApi-style hex key", re.compile(r"\b[0-9a-f]{32,64}\b")),
    ("Resend API key",                      re.compile(r"\bre_[A-Za-z0-9_]{12,}\b")),
    ("Postgres URL with password",          re.compile(r"postgres(?:ql)?://[^:\s]+:[^@\s]+@")),
    ("AWS access key id",                   re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private key block",                   re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# A JWT whose payload role is service_role must never reach the frontend.
JWT = re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")

# Obvious documentation/placeholder values that aren't real secrets.
PLACEHOLDER = re.compile(
    r"(?i)(YOUR[-_ ]?PASSWORD|user:pass@|:password@|:pass@|example|xxxx+|<[^>]+>|\.\.\.|PASTE_)"
)
# Per-line escape hatch (detect-secrets convention) for intentional samples.
ALLOWLIST_MARK = "pragma: allowlist secret"


def _staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [f for f in out.splitlines() if f.strip()]


def _all_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f.strip()]


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def _is_service_role(token: str) -> bool:
    import base64
    import json
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role") == "service_role"
    except Exception:
        return False


def scan(files: list[str]) -> list[str]:
    findings: list[str] = []
    for path in files:
        if FORBIDDEN_PATHS.search(path):
            findings.append(f"{path}: .env files must never be committed")
            continue
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            if ALLOWLIST_MARK in line:
                continue
            for label, pat in SECRET_PATTERNS:
                m = pat.search(line)
                if m and not PLACEHOLDER.search(m.group(0)):
                    findings.append(f"{path}:{lineno}: looks like a {label}")
            for jwt in JWT.findall(line):
                if _is_service_role(jwt):
                    findings.append(f"{path}:{lineno}: contains a Supabase SERVICE_ROLE key (never ship this)")
    return findings


def main() -> int:
    files = _all_files() if "--all" in sys.argv else _staged_files()
    findings = scan(files)
    if findings:
        print("✖ secret-scan blocked the commit:\n")
        for f in findings:
            print("  -", f)
        print("\nMove secrets to .env (gitignored) or GitHub Actions secrets, then retry.")
        return 1
    print("✓ secret-scan clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
