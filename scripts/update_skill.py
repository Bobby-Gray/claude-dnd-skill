"""
update_skill.py — check for and apply updates to the dnd skill from origin/main.

Usage:
    python3 update_skill.py            # check, show diff, prompt to pull
    python3 update_skill.py --check    # check only, no pull
    python3 update_skill.py --yes      # pull without prompting

Refuses to update if the working tree is dirty (protects local patches), and
uses --ff-only so it never silently merges divergent history.
"""
import argparse
import pathlib
import subprocess
import sys

SKILL_DIR = pathlib.Path("~/.claude/skills/dnd").expanduser()


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(SKILL_DIR), *args],
        capture_output=True, text=True, check=check,
    )


def _read_local_version() -> str:
    f = SKILL_DIR / "VERSION"
    if not f.exists():
        return "(no VERSION file — pre-1.6 baseline)"
    return f.read_text().strip()


def _read_remote_version(branch: str) -> str:
    """Read VERSION from origin/<branch> without checking it out."""
    try:
        r = git("show", f"origin/{branch}:VERSION", check=False)
        if r.returncode == 0:
            return r.stdout.strip()
        return "(no VERSION on remote)"
    except subprocess.CalledProcessError:
        return "(unreadable)"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="check only, do not pull")
    p.add_argument("--yes", action="store_true", help="pull without prompting")
    args = p.parse_args()

    if not (SKILL_DIR / ".git").exists():
        print(f"Skill at {SKILL_DIR} is not a git checkout.", file=sys.stderr)
        print(
            "Reinstall via: git clone https://github.com/Bobby-Gray/claude-dnd-skill "
            "~/.claude/skills/dnd",
            file=sys.stderr,
        )
        return 2

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    local_ver = _read_local_version()
    print(f"Skill location: {SKILL_DIR}  (branch: {branch}, version: {local_ver})")

    dirty = git("status", "--porcelain").stdout.strip()
    if dirty:
        print("Local changes detected — refusing to update:", file=sys.stderr)
        print(dirty, file=sys.stderr)
        print("\nCommit, stash, or discard your changes and re-run.", file=sys.stderr)
        return 3

    git("fetch", "--quiet", "origin", branch)
    local = git("rev-parse", "HEAD").stdout.strip()
    remote = git("rev-parse", f"origin/{branch}").stdout.strip()

    if local == remote:
        print(f"Up to date with origin/{branch} ({local[:7]}).")
        return 0

    behind = git("rev-list", "--count", f"HEAD..origin/{branch}").stdout.strip()
    log = git("log", "--oneline", f"HEAD..origin/{branch}").stdout.strip()
    remote_ver = _read_remote_version(branch)
    print(f"Local:  {local[:7]}  (version {local_ver})")
    print(f"Remote: {remote[:7]}  (version {remote_ver})")
    print(f"\n{behind} commits behind origin/{branch}:")
    print(log)
    if local_ver != remote_ver and not local_ver.startswith("("):
        print(f"\nVersion change: {local_ver} → {remote_ver}  "
              f"(see CHANGELOG.md after update for details)")

    if args.check:
        return 0

    if not args.yes:
        try:
            answer = input("\nPull now? (y/N) ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in {"y", "yes"}:
            print("Skipped.")
            return 0

    pull = git("pull", "--ff-only", "origin", branch, check=False)
    sys.stdout.write(pull.stdout)
    sys.stderr.write(pull.stderr)
    if pull.returncode != 0:
        print(
            "\nFast-forward failed — resolve manually with git in the skill directory.",
            file=sys.stderr,
        )
        return pull.returncode

    print(f"\nUpdated to {remote[:7]}. Restart Claude Code to load new skill files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
