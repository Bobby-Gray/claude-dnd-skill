"""
paths.py — canonical path resolution for DND campaign and character data.

All scripts that need to locate campaign or character files should import from
here rather than hardcoding ~/.claude/dnd/. Set DND_CAMPAIGN_ROOT to move your
data anywhere — iCloud, Dropbox, network share, etc. Defaults to ~/.claude/dnd.

Usage:
    from paths import campaigns_dir, characters_dir, campaign_dir, find_campaign

Environment:
    DND_CAMPAIGN_ROOT   Root of campaign data tree. Default: ~/.claude/dnd
                        Example: export DND_CAMPAIGN_ROOT=~/iCloud/dnd
"""

import os
import pathlib
import shutil
import sys

_DEFAULT_ROOT = pathlib.Path("~/.claude/dnd").expanduser()


def _root() -> pathlib.Path:
    """Return the configured data root, expanded and absolute."""
    raw = os.environ.get("DND_CAMPAIGN_ROOT", "")
    if raw.strip():
        return pathlib.Path(raw.strip()).expanduser().resolve()
    return _DEFAULT_ROOT


def campaigns_dir() -> pathlib.Path:
    """Return the campaigns directory under the configured root."""
    return _root() / "campaigns"


def characters_dir() -> pathlib.Path:
    """Return the global characters directory under the configured root."""
    return _root() / "characters"


def campaign_dir(name: str) -> pathlib.Path:
    """Return the directory for a specific campaign under the configured root."""
    return campaigns_dir() / name


def find_campaign(name: str) -> pathlib.Path:
    """Locate a campaign directory, with legacy fallback and optional migration.

    Resolution order:
    1. $DND_CAMPAIGN_ROOT/campaigns/<name>/  — configured root (or default)
    2. ~/.claude/dnd/campaigns/<name>/       — legacy default (only checked when
       DND_CAMPAIGN_ROOT is set to a *different* path)

    When a campaign is found at the legacy path and the configured root is custom,
    the campaign is copied to the configured root so subsequent sessions use the
    new location. The original is left in place (no files are deleted).

    Returns the path to the campaign directory (may not exist if not found anywhere).
    """
    configured = campaign_dir(name)
    if configured.exists():
        return configured

    # Only check legacy fallback if a custom root is configured
    custom_root = os.environ.get("DND_CAMPAIGN_ROOT", "").strip()
    if not custom_root:
        return configured  # no custom root — nothing to fall back to

    legacy = _DEFAULT_ROOT / "campaigns" / name
    if not legacy.exists():
        return configured  # not found in legacy location either

    # Found at legacy path — copy to configured root
    configured.parent.mkdir(parents=True, exist_ok=True)
    print(
        f"[paths] Campaign '{name}' found at legacy path {legacy}\n"
        f"[paths] Copying to {configured} (original kept in place)",
        file=sys.stderr,
    )
    shutil.copytree(str(legacy), str(configured))
    return configured


# ── Ruleset selection ─────────────────────────────────────────────────────
# A campaign declares its ruleset on the state.md header line,
# e.g.: "**Ruleset:** 2024". When unset (legacy campaigns) we default
# to 2014 — the historical ruleset of this skill.

import re as _re

VALID_RULESETS = ("2014", "2024")
DEFAULT_RULESET = "2014"

_RULESET_PAT = _re.compile(r"\*\*Ruleset:\*\*\s*(\d{4})", _re.IGNORECASE)


def campaign_ruleset(name: str) -> str:
    """Return the campaign's declared ruleset (e.g. '2014', '2024').

    Reads the state.md header. Falls back to DEFAULT_RULESET when the
    file is missing or the field is unset (legacy campaigns predating
    the ruleset field — they were 2014 by definition).
    """
    state = find_campaign(name) / "state.md"
    if not state.exists():
        return DEFAULT_RULESET
    try:
        text = state.read_text(errors="replace")
    except OSError:
        return DEFAULT_RULESET
    m = _RULESET_PAT.search(text)
    if not m:
        return DEFAULT_RULESET
    val = m.group(1).strip()
    return val if val in VALID_RULESETS else DEFAULT_RULESET


def srd_path(ruleset=None):
    """Return path to the SRD JSON for the given ruleset.

    `ruleset=None` returns the default (2014) path. The 2024 path is
    `dnd5e_srd_2024.json`. Caller is responsible for handling missing
    files (e.g. a campaign declares 2024 but the dataset hasn't been
    built yet — in that case, suggest `/dnd data sync --ruleset 2024`).
    """
    rs = ruleset or DEFAULT_RULESET
    if rs not in VALID_RULESETS:
        rs = DEFAULT_RULESET
    skill_data = pathlib.Path("~/.claude/skills/dnd/data").expanduser()
    fname = "dnd5e_srd_2024.json" if rs == "2024" else "dnd5e_srd.json"
    return skill_data / fname


# ── CLI passthrough ───────────────────────────────────────────────────────
# A few helpers are useful from shell too. Keep this minimal — paths.py is
# primarily an import surface.
if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "campaign-ruleset":
        print(campaign_ruleset(sys.argv[2]))
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "srd-path":
        rs = sys.argv[2] if len(sys.argv) >= 3 else None
        print(srd_path(rs))
        sys.exit(0)
    print(
        "usage:\n"
        "  python3 paths.py campaign-ruleset <campaign-name>\n"
        "  python3 paths.py srd-path [2014|2024]",
        file=sys.stderr,
    )
    sys.exit(2)
