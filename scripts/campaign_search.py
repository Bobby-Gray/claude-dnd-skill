#!/usr/bin/env python3
"""
campaign_search.py — keyword search across campaign files.

Usage:
    python3 campaign_search.py -c <campaign> <keyword> [keyword2 ...]
    python3 campaign_search.py -c <campaign> <keyword> --files state,log,archive,world,npcs
    python3 campaign_search.py -c <campaign> <keyword> -C 4   # context lines (default 3)

Examples:
    python3 ~/.claude/skills/dnd/scripts/campaign_search.py -c my-campaign dragon
    python3 ~/.claude/skills/dnd/scripts/campaign_search.py -c my-campaign Vael letter --files log,archive
    python3 ~/.claude/skills/dnd/scripts/campaign_search.py -c test-campaign VARETH Kel

Returns: file name, nearest section heading, and matching lines with context.
Case-insensitive. Multiple keywords = AND (all must appear within the same block).
"""

import sys
import os
import argparse
import re

from paths import campaigns_dir as _campaigns_dir
CAMPAIGNS_DIR = str(_campaigns_dir())

FILE_MAP = {
    "state":   "state.md",
    "log":     "session-log.md",
    "archive": "session-log-archive.md",
    "world":   "world.md",
    "seeds":   "world-seeds.md",
    "npcs":    "npcs.md",
    "npcsfull":"npcs-full.md",
}
DEFAULT_FILES = ["state", "log", "archive", "world", "npcs"]


def find_section_heading(lines, match_idx):
    """Walk backwards from match_idx to find nearest ## or ### heading."""
    for i in range(match_idx, -1, -1):
        if lines[i].startswith("#"):
            return lines[i].strip()
    return "(no heading found)"


def search_file(filepath, keywords, context_lines=3):
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    results = []
    # Split into blocks of (context_lines*2+1) for AND matching
    # Strategy: find lines matching ALL keywords within a window of 20 lines
    window = 20
    matched_blocks = set()

    for i, line in enumerate(lines):
        if all(kw.lower() in line.lower() for kw in keywords):
            matched_blocks.add(i)
        # Multi-line AND: check if all keywords appear in a window around this line
        elif len(keywords) > 1:
            block_start = max(0, i - window // 2)
            block_end = min(len(lines), i + window // 2)
            block_text = "".join(lines[block_start:block_end]).lower()
            if all(kw.lower() in block_text for kw in keywords):
                # Find the line with the first keyword
                for j in range(block_start, block_end):
                    if keywords[0].lower() in lines[j].lower():
                        matched_blocks.add(j)
                        break

    for idx in sorted(matched_blocks):
        heading = find_section_heading(lines, idx)
        start = max(0, idx - context_lines)
        end = min(len(lines), idx + context_lines + 1)
        snippet = "".join(lines[start:end]).rstrip()
        results.append({
            "file": os.path.basename(filepath),
            "line": idx + 1,
            "heading": heading,
            "snippet": snippet,
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Search campaign files by keyword.")
    parser.add_argument("-c", "--campaign", required=True, help="Campaign name")
    parser.add_argument("keywords", nargs="+", help="Keywords to search (AND logic)")
    parser.add_argument(
        "--files",
        default=",".join(DEFAULT_FILES),
        help=f"Comma-separated file keys to search. Options: {', '.join(FILE_MAP.keys())}. Default: {','.join(DEFAULT_FILES)}",
    )
    parser.add_argument("-C", "--context", type=int, default=3, help="Context lines around match (default 3)")
    args = parser.parse_args()

    campaign_dir = os.path.join(CAMPAIGNS_DIR, args.campaign)
    if not os.path.isdir(campaign_dir):
        print(f"ERROR: Campaign directory not found: {campaign_dir}")
        sys.exit(1)

    file_keys = [k.strip() for k in args.files.split(",")]
    keywords = args.keywords

    print(f"Searching campaign: {args.campaign}")
    print(f"Keywords: {' AND '.join(keywords)}")
    print(f"Files: {', '.join(file_keys)}")
    print("=" * 60)

    total = 0
    for key in file_keys:
        filename = FILE_MAP.get(key)
        if not filename:
            print(f"  [unknown file key: {key}]")
            continue
        filepath = os.path.join(campaign_dir, filename)
        results = search_file(filepath, keywords, args.context)
        if results:
            for r in results:
                print(f"\n[{r['file']}  line {r['line']}]  {r['heading']}")
                print("-" * 40)
                print(r["snippet"])
                total += 1

    print("\n" + "=" * 60)
    if total == 0:
        print(f"No matches found for: {' AND '.join(keywords)}")
    else:
        print(f"{total} match(es) found.")


if __name__ == "__main__":
    main()
